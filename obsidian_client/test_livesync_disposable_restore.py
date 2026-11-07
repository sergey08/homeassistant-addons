"""Disposable backup recovery: no revision overwrites and leaf-first only."""
import json
import tempfile
import unittest
from copy import deepcopy
from pathlib import Path
from unittest.mock import Mock
from test_livesync_isolated_backup import fixture, PASS, SALT, REV, PATH
from livesync_isolated_backup import BackupRejected, _checksum, create_verified_snapshot
from livesync_isolated_backup_store import store_signed_backup
from livesync_disposable_restore import (
    restore_to_empty_disposable_database, DisposableRestoreError)
from livesync_write_preflight import UnsafeWrite


class FakeEmptyDB:
    def __init__(self):
        self.docs = {}
        self.puts = []
        self.fail_leaf = None
        self.conflict_parent = False

    def list_ids(self):
        return sorted(self.docs)

    def read(self, ident):
        result = self.docs.get(ident)
        return deepcopy(result) if result is not None else None

    def put(self, doc):
        ident = doc["_id"]
        self.puts.append(ident)
        if ident in self.docs or (self.conflict_parent and doc["type"] == "plain"):
            return 409, {"error": "conflict"}
        if ident == self.fail_leaf:
            raise TimeoutError("disposable-test-timeout")
        revision = "1-" + "a" * 32
        self.docs[ident] = {**deepcopy(doc), "_rev": revision}
        return 201, {"ok": True, "id": ident, "rev": revision}


class RestoreTests(unittest.TestCase):
    def setUp(self):
        parent, leaves = fixture()
        self.backup = create_verified_snapshot(
            parent, leaves, PATH, REV, PASS, SALT,
            isolated_test=True)["backup"]
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name) / "backups"
        self.key = bytes(range(32))
        self.backup_id = store_signed_backup(
            self.root, self.backup, self.key, isolated_test=True)["backup_id"]
        self.db = FakeEmptyDB()

    def restore(self):
        return restore_to_empty_disposable_database(
            self.root, self.backup_id, self.key,
            self.db.list_ids, self.db.read, self.db.put, PASS, SALT,
            isolated_test=True, disposable_database=True)

    def test_restores_new_revisions_and_verified_content(self):
        result = self.restore()
        self.assertEqual(result["confirmed_leaves"], 3)
        self.assertEqual(result["status"], "restored_in_empty_disposable_database_only")
        self.assertFalse(result["restore_to_production_enabled"])
        self.assertEqual(self.db.puts, [x["_id"] for x in self.backup["snapshot"]["leaves"]]
                         + [self.backup["snapshot"]["parent"]["_id"]])

    def test_nonempty_database_rejected_before_any_put(self):
        self.db.docs["unrelated"] = {"_id": "unrelated"}
        with self.assertRaisesRegex(UnsafeWrite, "target_database_not_empty"):
            self.restore()
        self.assertEqual(self.db.puts, [])

    def test_stale_backup_cannot_overwrite_existing_document(self):
        self.db.docs[self.backup["snapshot"]["parent"]["_id"]] = {
            "_id": self.backup["snapshot"]["parent"]["_id"], "_rev": "8-" + "f" * 32}
        with self.assertRaises(UnsafeWrite):
            self.restore()
        self.assertEqual(self.db.puts, [])

    def test_leaf_timeout_never_writes_parent(self):
        self.db.fail_leaf = self.backup["snapshot"]["leaves"][1]["_id"]
        with self.assertRaises(DisposableRestoreError) as error:
            self.restore()
        self.assertEqual(error.exception.phase, "leaf_uncertain")
        self.assertNotIn(self.backup["snapshot"]["parent"]["_id"], self.db.puts)

    def test_parent_conflict_leaves_unmodified_backup_chunks(self):
        self.db.conflict_parent = True
        with self.assertRaises(DisposableRestoreError) as error:
            self.restore()
        self.assertEqual(error.exception.phase, "parent_uncertain")
        self.assertEqual(len(self.db.docs), 3)
        self.assertNotIn(self.backup["snapshot"]["parent"]["_id"], self.db.docs)

    def test_recomputed_checksum_cannot_bypass_backup_authentication(self):
        path = self.root / (self.backup_id + ".json")
        record = json.loads(path.read_text(encoding="utf-8"))
        backup = record["backup"]
        # Alter a valid historical revision without changing any ciphertext.
        backup["snapshot"]["leaves"][0]["_rev"] = "99-" + "f" * 32
        backup["sha256"] = _checksum(backup["snapshot"])
        path.write_text(json.dumps(record), encoding="utf-8")

        target = Mock()
        with self.assertRaisesRegex(BackupRejected, "backup_authentication_failed"):
            restore_to_empty_disposable_database(
                self.root, self.backup_id, self.key,
                target.list_ids, target.read, target.put, PASS, SALT,
                isolated_test=True, disposable_database=True)
        self.assertEqual(target.mock_calls, [])

    def test_no_production_or_unqualified_recovery(self):
        for kwargs in (
            {"isolated_test": False, "disposable_database": True},
            {"isolated_test": True, "disposable_database": False},
            {"isolated_test": True, "disposable_database": True,
             "remote_writes_enabled": True}):
            with self.assertRaisesRegex(UnsafeWrite, "disposable_restore_only"):
                restore_to_empty_disposable_database(
                    self.root, self.backup_id, self.key,
                    self.db.list_ids, self.db.read, self.db.put, PASS, SALT, **kwargs)
        self.assertEqual(self.db.puts, [])


if __name__ == "__main__":
    unittest.main()
