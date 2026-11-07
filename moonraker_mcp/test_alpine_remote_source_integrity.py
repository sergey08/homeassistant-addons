"""Offline regression tests for per-source partial audit evidence."""
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import urllib.error

from alpine_remote_source_integrity import COMMIT, audit, verify_one


class RemoteAlpineAuditTests(unittest.TestCase):
    def manifest(self, folder):
        items = [{"file": f"source-{i}.tar.gz", "url": "https://ftp.gnu.org/gnu/readline/a",
                  "sha512": hashlib.sha512(b"valid").hexdigest(),
                  "status": "PENDING_DOWNLOAD_SHA512"} for i in range(11)]
        p = Path(folder) / "manifest.json"
        p.write_text(json.dumps({"aports_commit": COMMIT,
                                 "purpose": "SOURCE_INTEGRITY_EVIDENCE_NOT_LICENSE_APPROVAL",
                                 "items": items}))
        return p

    def test_partial_failure_does_not_erase_success(self):
        with tempfile.TemporaryDirectory() as directory:
            manifest = self.manifest(directory)
            state = {"i": 0}
            def side_effect(item):
                state["i"] += 1
                if state["i"] == 3:
                    raise urllib.error.URLError("offline")
                return {"file": item["file"], "url": item["url"],
                        "sha512": item["sha512"], "bytes": 5,
                        "status": "VERIFIED_SHA512"}
            with patch("alpine_remote_source_integrity.verify_one", side_effect=side_effect):
                result = audit(manifest)
            self.assertEqual(result["verified_remote_sha512"], 10)
            self.assertEqual(result["unverified"], 1)
            self.assertFalse(result["complete"])
            self.assertFalse(result["license_approved"])
            self.assertEqual(result["items"][2]["status"], "UNVERIFIED")
            self.assertEqual(len(result["items"]), 11)

    def test_missing_source_never_marks_complete(self):
        with tempfile.TemporaryDirectory() as directory:
            manifest = self.manifest(directory)
            with patch("alpine_remote_source_integrity.verify_one",
                       side_effect=OSError("network unavailable")):
                result = audit(manifest)
            self.assertEqual(result["verified_remote_sha512"], 0)
            self.assertEqual(result["unverified"], 11)
            self.assertFalse(result["complete"])

    def test_invalid_or_duplicate_inventory_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            manifest = self.manifest(directory)
            data = json.loads(manifest.read_text())
            data["items"][1]["file"] = data["items"][0]["file"]
            manifest.write_text(json.dumps(data))
            with self.assertRaises(ValueError):
                audit(manifest)

    def test_official_distfiles_fallback_keeps_original_digest(self):
        item = {"file": "apk-tools-v2.14.13.tar.gz",
                "url": "https://gitlab.alpinelinux.org/alpine/apk-tools/-/archive/v2.14.13/apk-tools-v2.14.13.tar.gz",
                "sha512": "a" * 128}
        with patch("alpine_remote_source_integrity._hash_download",
                   side_effect=[OSError("GitLab unavailable"),
                                {"file": item["file"], "status": "VERIFIED_SHA512",
                                 "sha512": item["sha512"],
                                 "url": "https://distfiles.alpinelinux.org/distfiles/v3.22/" + item["file"],
                                 "bytes": 300}]) as get:
            record = verify_one(item)
        self.assertEqual(get.call_count, 2)
        self.assertEqual(get.call_args_list[0].args[1], item["sha512"])
        self.assertEqual(get.call_args_list[1].args[1], item["sha512"])
        self.assertEqual(record["status"], "VERIFIED_SHA512")

    def test_fallback_failure_never_verifies_file(self):
        item = {"file": "ca-certificates-20261020.tar.bz2",
                "url": "https://gitlab.alpinelinux.org/alpine/ca-certificates/-/archive/20261020/ca-certificates-20261020.tar.bz2",
                "sha512": "b" * 128}
        with patch("alpine_remote_source_integrity._hash_download",
                   side_effect=ValueError("SHA-512 mismatch")) as get:
            with self.assertRaises(ValueError):
                verify_one(item)
            self.assertEqual(get.call_count, 2)

    def test_non_https_host_rejected_before_download(self):
        item = {"file": "x", "url": "http://ftp.gnu.org/gnu/a", "sha512": "0" * 128}
        with self.assertRaises(ValueError):
            verify_one(item)


if __name__ == "__main__":
    unittest.main()
