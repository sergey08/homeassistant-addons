"""Disposable backup recovery: no revision overwrites and leaf-first only."""
import json
import tempfile
import unittest
from copy import deepcopy
from pathlib import Path
from unittest.mock import Mock
from test_livesync_isolated_backup import fixture, PASS, SALT, REV, PATH
from livesync_isolated_backup import (
    BackupRejected, _checksum, create_verified_snapshot, preflight_restore_snapshot)
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

    def test_legacy_signed_backup_keeps_working(self):
        legacy = deepcopy(self.backup)
        legacy["schema"] = 1
        legacy["snapshot"]["path"] = PATH
        legacy["sha256"] = _checksum(legacy["snapshot"])
        self.backup_id = store_signed_backup(
            self.root, legacy, self.key, isolated_test=True)["backup_id"]

        result = preflight_restore_snapshot(
            legacy, legacy["snapshot"]["parent"], PASS, SALT, isolated_test=True)
        self.assertEqual(result["status"], "verified_no_change_required")
        self.assertEqual(self.restore()["confirmed_leaves"], 3)

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

    def test_concurrent_leaf_creation_is_not_overwritten(self):
        """Another writer wins after preflight; no overwrite or parent PUT."""
        leaf_id = self.backup["snapshot"]["leaves"][0]["_id"]
        original_put = self.db.put

        def competing_put(doc):
            if doc["_id"] == leaf_id:
                self.db.docs[leaf_id] = {"_id": leaf_id,
                                         "_rev": "1-" + "e" * 32,
                                         "type": "leaf", "e_": True,
                                         "data": "%=other-writer"}
            return original_put(doc)

        with self.assertRaises(DisposableRestoreError) as error:
            restore_to_empty_disposable_database(
                self.root, self.backup_id, self.key,
                self.db.list_ids, self.db.read, competing_put,
                PASS, SALT, isolated_test=True, disposable_database=True)
        self.assertEqual(error.exception.phase, "leaf_uncertain")
        self.assertEqual(self.db.docs[leaf_id]["data"], "%=other-writer")
        self.assertNotIn(self.backup["snapshot"]["parent"]["_id"], self.db.docs)

    def test_parent_acknowledgement_loss_never_retries(self):
        """Even a successful server-side create can have an uncertain result."""
        original_put = self.db.put
        parent_id = self.backup["snapshot"]["parent"]["_id"]

        def lost_ack(doc):
            result = original_put(doc)
            if doc["_id"] == parent_id:
                raise TimeoutError("lost-disposable-ack")
            return result

        with self.assertRaises(DisposableRestoreError) as error:
            restore_to_empty_disposable_database(
                self.root, self.backup_id, self.key,
                self.db.list_ids, self.db.read, lost_ack,
                PASS, SALT, isolated_test=True, disposable_database=True)
        self.assertEqual(error.exception.phase, "parent_uncertain")
        self.assertEqual(self.db.puts.count(parent_id), 1)
        self.assertIn(parent_id, self.db.docs)

    def test_leaf_revision_change_after_readback_prevents_success(self):
        snapshot = self.backup["snapshot"]
        leaf_id = snapshot["leaves"][0]["_id"]
        parent_id = snapshot["parent"]["_id"]

        def competing_put(doc):
            result = self.db.put(doc)
            if doc["_id"] == parent_id:
                # A concurrent writer keeps the ciphertext but changes its revision.
                self.db.docs[leaf_id]["_rev"] = "2-" + "e" * 32
            return result

        with self.assertRaises(DisposableRestoreError) as error:
            restore_to_empty_disposable_database(
                self.root, self.backup_id, self.key,
                self.db.list_ids, self.db.read, competing_put, PASS, SALT,
                isolated_test=True, disposable_database=True)
        self.assertEqual(error.exception.phase, "parent_uncertain")
        self.assertEqual(str(error.exception.__cause__), "restored_leaf_changed")
        self.assertEqual(self.db.puts, [leaf["_id"] for leaf in snapshot["leaves"]] + [parent_id])

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

    def test_signed_backup_with_unexpected_documents_is_rejected_before_access(self):
        extra_leaf = {**self.backup["snapshot"]["leaves"][0], "_id": "h:+unreferenced"}
        for reason in ("unexpected_backup_leaves", "unsupported_backup_parent_attachments"):
            with self.subTest(reason=reason):
                backup = deepcopy(self.backup)
                snapshot = backup["snapshot"]
                if reason == "unexpected_backup_leaves":
                    snapshot["leaves"].append(extra_leaf)
                else:
                    snapshot["parent"]["_attachments"] = {
                        "extra.txt": {"content_type": "text/plain", "data": "ZXh0cmE="}}
                backup["sha256"] = _checksum(snapshot)
                backup_id = store_signed_backup(
                    self.root, backup, self.key, isolated_test=True)["backup_id"]

                target = Mock()
                with self.assertRaisesRegex(UnsafeWrite, reason):
                    restore_to_empty_disposable_database(
                        self.root, backup_id, self.key,
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
