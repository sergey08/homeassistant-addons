"""Encrypted backups cannot authorize writes or overwrite newer revisions."""
import base64
import copy
import unittest

from livesync_crypto import encrypt_hkdf_string
from livesync_encrypted_metadata_fixture import encode_parent_metadata_fixture
from livesync_isolated_backup import (
    BackupRejected, create_verified_snapshot, preflight_restore_snapshot)
from livesync_write_preflight import UnsafeWrite

PASS = "ci-isolated-only"
SALT = base64.b64encode(b"ci-backup-metadata-salt").decode()
REV = "2-" + "a" * 32
PATH = "Tests/Encrypted.md"


def fixture():
    parts = ["Uno ", "dos 🌍", "\n"]
    ids = ["h:+test-" + str(x) for x in range(len(parts))]
    metadata = encode_parent_metadata_fixture(
        PATH, ids, PASS, SALT,
        ctime=100, mtime=200, size=len("".join(parts).encode("utf-8")))
    parent = {"_id": "encrypted-test-parent", "_rev": REV, "type": "plain",
              "path": metadata["path"], "children": [],
              "ctime": 0, "mtime": 0, "size": 0}
    leaves = {ident: {"_id": ident, "_rev": "1-" + "b" * 32,
                      "type": "leaf", "e_": True,
                      "data": encrypt_hkdf_string(part, PASS, SALT)}
              for ident, part in zip(ids, parts)}
    return parent, leaves


class BackupVerificationTests(unittest.TestCase):
    def make_backup(self):
        parent, leaves = fixture()
        backup = create_verified_snapshot(parent, leaves, PATH, REV, PASS, SALT,
                                          isolated_test=True)
        return parent, leaves, backup

    def test_roundtrip_preserves_encrypted_documents(self):
        parent, leaves, result = self.make_backup()
        self.assertEqual(result["verified_chunks"], 3)
        self.assertFalse(result["restore_enabled"])
        manifest = result["backup"]
        self.assertEqual(manifest["snapshot"]["parent"], parent)
        self.assertEqual(
            [item["_id"] for item in manifest["snapshot"]["leaves"]],
            list(leaves))
        self.assertNotIn("Uno dos", str(manifest))
        inspection = preflight_restore_snapshot(
            manifest, parent, PASS, SALT, isolated_test=True)
        self.assertEqual(inspection["status"], "verified_no_change_required")
        self.assertFalse(inspection["automatic_restore"])

    def test_tampered_chunk_detected_even_if_checksum_still_matches_old(self):
        parent, leaves, result = self.make_backup()
        backup = copy.deepcopy(result["backup"])
        backup["snapshot"]["leaves"][0]["data"] = "%=bad"
        with self.assertRaisesRegex(BackupRejected, "backup_integrity_mismatch"):
            preflight_restore_snapshot(backup, parent, PASS, SALT,
                                       isolated_test=True)

    def test_parent_advanced_revision_cannot_be_overwritten(self):
        parent, leaves, result = self.make_backup()
        changed = {**parent, "_rev": "3-" + "d" * 32}
        with self.assertRaisesRegex(BackupRejected, "restore_preflight_failed"):
            preflight_restore_snapshot(result["backup"], changed, PASS, SALT,
                                       isolated_test=True)

    def test_changed_parent_ciphertext_even_same_revision_rejected(self):
        parent, leaves, result = self.make_backup()
        changed = {**parent, "path": "some-new-ciphertext"}
        with self.assertRaisesRegex(BackupRejected, "current_parent_diverged"):
            preflight_restore_snapshot(result["backup"], changed, PASS, SALT,
                                       isolated_test=True)

    def test_missing_or_extra_leaf_blocked(self):
        parent, leaves = fixture()
        leaves.pop(next(iter(leaves)))
        with self.assertRaises(BackupRejected):
            create_verified_snapshot(parent, leaves, PATH, REV, PASS, SALT,
                                     isolated_test=True)
        parent, leaves = fixture()
        leaves["h:+extra"] = {"_id": "h:+extra", "_rev": "1-" + "b" * 32,
                              "type": "leaf", "e_": True, "data": "%=bad"}
        with self.assertRaises(BackupRejected):
            create_verified_snapshot(parent, leaves, PATH, REV, PASS, SALT,
                                     isolated_test=True)

    def test_wrong_passphrase_blocked(self):
        parent, leaves = fixture()
        with self.assertRaises(BackupRejected):
            create_verified_snapshot(parent, leaves, PATH, REV, "wrong", SALT,
                                     isolated_test=True)

    def test_production_gate_always_closed(self):
        parent, leaves = fixture()
        for opts in ({}, {"isolated_test": True, "remote_writes_enabled": True}):
            with self.assertRaises(UnsafeWrite):
                create_verified_snapshot(parent, leaves, PATH, REV, PASS, SALT,
                                         **opts)
        _, _, result = self.make_backup()
        for opts in ({}, {"isolated_test": True, "remote_writes_enabled": True}):
            with self.assertRaises(UnsafeWrite):
                preflight_restore_snapshot(result["backup"], parent, PASS, SALT,
                                           **opts)


if __name__ == "__main__":
    unittest.main()
