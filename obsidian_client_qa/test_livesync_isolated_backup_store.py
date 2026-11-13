"""Signed isolated backup storage: append-only, tamper-evident and fail-closed."""
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from test_livesync_isolated_backup import fixture, PASS, SALT, REV, PATH
from livesync_isolated_backup import create_verified_snapshot, preflight_restore_snapshot, BackupRejected
from livesync_isolated_backup_store import store_signed_backup, read_signed_backup
from livesync_write_preflight import UnsafeWrite

SECRET = bytes(range(32))
OTHER_SECRET = bytes(reversed(range(32)))


class SignedBackupStoreTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name) / "private-backups"
        self.parent, leaves = fixture()
        self.backup = create_verified_snapshot(
            self.parent, leaves, PATH, REV, PASS, SALT,
            isolated_test=True)["backup"]

    def store(self, backup=None):
        return store_signed_backup(
            self.root, backup if backup is not None else self.backup,
            SECRET, isolated_test=True)

    def load(self, backup_id, secret=SECRET):
        return read_signed_backup(self.root, backup_id, secret, isolated_test=True)

    def test_persist_authenticated_and_separate_key(self):
        result = self.store()
        self.assertTrue(result["durable"])
        self.assertTrue(result["immutable"])
        self.assertFalse(result["restore_enabled"])
        stored = self.load(result["backup_id"])
        self.assertTrue(stored["authenticated"])
        self.assertEqual(stored["backup"], self.backup)
        self.assertFalse(stored["remote_writes_enabled"])
        self.assertNotIn(SECRET.hex(), str(self.root.joinpath(result["backup_id"] + ".json").read_text()))
        restored = preflight_restore_snapshot(stored["backup"], self.parent,
                                              PASS, SALT, isolated_test=True)
        self.assertEqual(restored["status"], "verified_no_change_required")
        self.assertEqual(self.root.stat().st_mode & 0o077, 0)
        self.assertEqual(next(self.root.iterdir()).stat().st_mode & 0o077, 0)

    def test_two_backups_do_not_replace_prior_backup(self):
        first = self.store()
        first_path = self.root / (first["backup_id"] + ".json")
        original = first_path.read_bytes()
        second = self.store()
        self.assertNotEqual(first["backup_id"], second["backup_id"])
        self.assertEqual(first_path.read_bytes(), original)
        self.assertEqual(len(list(self.root.glob("*.json"))), 2)

    def test_wrong_key_cannot_read(self):
        result = self.store()
        with self.assertRaisesRegex(BackupRejected, "backup_authentication_failed"):
            self.load(result["backup_id"], OTHER_SECRET)

    def test_tampering_is_detected(self):
        result = self.store()
        path = self.root / (result["backup_id"] + ".json")
        record = json.loads(path.read_text())
        record["backup"]["snapshot"]["parent"]["path"] = "changed"
        path.write_text(json.dumps(record))
        with self.assertRaisesRegex(BackupRejected, "backup_authentication_failed"):
            self.load(result["backup_id"])

    def test_snapshot_checksum_must_be_valid_before_persisting(self):
        broken = json.loads(json.dumps(self.backup))
        broken["snapshot"]["parent"]["path"] = "changed"
        with self.assertRaisesRegex(BackupRejected, "backup_checksum_mismatch"):
            self.store(broken)
        self.assertFalse(self.root.exists())

    def test_backup_key_is_required(self):
        with self.assertRaisesRegex(BackupRejected, "separate_backup_key_required"):
            store_signed_backup(self.root, self.backup, b"short",
                                isolated_test=True)
        self.assertFalse(self.root.exists())

    def test_symlink_directory_and_file_rejected(self):
        foreign = Path(self.tmp.name) / "foreign"
        foreign.mkdir()
        foreign.chmod(0o700)
        self.root.symlink_to(foreign, target_is_directory=True)
        with self.assertRaisesRegex(BackupRejected, "unsafe_backup_directory"):
            self.store()
        self.root.unlink()
        result = self.store()
        path = self.root / (result["backup_id"] + ".json")
        path.unlink()
        path.symlink_to(foreign / "target")
        with self.assertRaises(BackupRejected):
            self.load(result["backup_id"])

    def test_world_readable_directory_blocked(self):
        self.root.mkdir(mode=0o700)
        self.root.chmod(0o755)
        with self.assertRaisesRegex(BackupRejected, "insecure_backup_directory"):
            self.store()

    def test_malformed_identifier_rejected(self):
        self.root.mkdir(mode=0o700)
        with self.assertRaisesRegex(BackupRejected, "invalid_backup_id"):
            self.load("../../private")
        with self.assertRaisesRegex(BackupRejected, "invalid_backup_id"):
            self.load("A" * 32)

    def test_production_gate_denies_without_creating_files(self):
        for kwargs in ({}, {"isolated_test": True, "remote_writes_enabled": True}):
            with self.assertRaises(UnsafeWrite):
                store_signed_backup(self.root, self.backup, SECRET, **kwargs)
        self.assertFalse(self.root.exists())
        result = self.store()
        for kwargs in ({}, {"isolated_test": True, "remote_writes_enabled": True}):
            with self.assertRaises(UnsafeWrite):
                read_signed_backup(self.root, result["backup_id"], SECRET, **kwargs)


if __name__ == "__main__":
    unittest.main()
