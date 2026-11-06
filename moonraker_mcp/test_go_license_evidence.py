"""Offline regression tests for conservative Go module license evidence."""
import csv
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from go_license_evidence import collect, license_files, module_from_purl


class GoLicenseEvidenceTests(unittest.TestCase):
    def test_purl_exact_versions(self):
        self.assertEqual(module_from_purl(
            "pkg:golang/golang.org/x/text@v0.41.0", "v0.41.0"),
            ("golang.org/x/text", "v0.41.0"))
        self.assertEqual(module_from_purl(
            "pkg:golang/github.com/example/module@v0.0.0-20261001010203-abcd1234",
            "v0.0.0-20261001010203-abcd1234"),
            ("github.com/example/module", "v0.0.0-20261001010203-abcd1234"))
        for purl, v in (
            ("pkg:golang/../evil@v1.2.3", "v1.2.3"),
            ("pkg:golang/github.com/e/x@v1.2.3", "v1.2.4"),
            ("pkg:golang/github.com/e/x@latest", "latest"),
            ("pkg:npm/example@1.0.0", "1.0.0"),
        ):
            with self.subTest(purl=purl):
                with self.assertRaises(ValueError):
                    module_from_purl(purl, v)

    def test_source_files_are_hashed_but_not_classified(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "source"
            source.mkdir()
            (source / "LICENSE").write_text("For testing only")
            (source / "NOTICE").write_text("A sample notice")
            (source / "LICENSE.link").symlink_to(source / "NOTICE")
            self.assertEqual(len(license_files(source)), 2)
            payload = json.dumps({"Path": "golang.org/x/text", "Version": "v0.41.0",
                                  "Dir": str(source), "Sum": "h1:synthetic"}).encode()
            class FakeResult:
                returncode = 0
                stdout = payload.decode()
            queue = [{"ecosystem": "golang", "name": "golang.org/x/text",
                      "version": "v0.41.0", "purl": "pkg:golang/golang.org/x/text@v0.41.0",
                      "bom_ref": "go-1"}]
            with patch("go_license_evidence.subprocess.run", return_value=FakeResult()) as runner:
                summary = collect(queue, root / "out")
            self.assertEqual(summary["statuses"], {"SOURCE_LICENSE_FILES_FOUND": 1})
            rows = list(csv.DictReader((root / "out/go-license-evidence.csv").open()))
            self.assertEqual({r["license_file"] for r in rows}, {"LICENSE", "NOTICE"})
            self.assertTrue(all(len(r["license_sha256"]) == 64 for r in rows))
            self.assertEqual(len(runner.call_args.args[0]), 5)
            self.assertFalse(summary["release_clearance"])

    def test_unavailable_source_stays_pending(self):
        with tempfile.TemporaryDirectory() as tmp:
            queue = [{"ecosystem": "golang", "name": "example.com/a",
                      "version": "v1.0.0", "purl": "pkg:golang/example.com/a@v1.0.0",
                      "bom_ref": "go-1"},
                     {"ecosystem": "no-purl", "name": "unidentified", "bom_ref": "x-2"}]
            class Failed:
                returncode = 1
                stdout = ""
            with patch("go_license_evidence.subprocess.run", return_value=Failed()):
                summary = collect(queue, Path(tmp))
            self.assertEqual(summary["statuses"], {"MANUAL_REVIEW": 2})


if __name__ == "__main__":
    unittest.main()
