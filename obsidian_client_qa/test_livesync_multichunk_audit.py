"""Read-only multi-chunk and candidate-orphan safety tests."""
import base64
import unittest
from unittest.mock import patch

from livesync_multichunk_audit import (
    ChunkAuditError, assemble_encrypted_chunks, audit_unreferenced_leaves)
from livesync_encrypted_metadata_fixture import encode_parent_metadata_fixture
from livesync_crypto import encrypt_hkdf_string

PASSWORD = "disposable-only"
SALT = base64.b64encode(b"disposable-test-salt").decode()
PATH = "Sandbox/Multi.md"
REV = "1-" + "a" * 32


def fixture(chunks=("Hola ", "🌍", "\n"), size=None):
    ids = ["h:+test" + str(i) for i in range(len(chunks))]
    size = len("".join(chunks).encode("utf-8")) if size is None else size
    meta = encode_parent_metadata_fixture(PATH, ids, PASSWORD, SALT,
            ctime=100, mtime=200, size=size)
    parent = {"_id": "f:synthetic", "_rev": REV, "type": "plain",
              "path": meta["path"], "children": [], "size": 0}
    leaves = {
        cid: {"_id": cid, "type": "leaf", "e_": True,
              "data": encrypt_hkdf_string(chunk, PASSWORD, SALT)}
        for cid, chunk in zip(ids, chunks)
    }
    return parent, leaves


class MultichunkTests(unittest.TestCase):
    def test_ordered_multichunk_utf8_and_unicode(self):
        parent, leaves = fixture()
        result = assemble_encrypted_chunks(parent, leaves, PATH, REV, PASSWORD, SALT)
        self.assertEqual(result["content"], "Hola 🌍\n")
        self.assertEqual(result["chunks"], 3)
        self.assertEqual(result["bytes"], len("Hola 🌍\n".encode("utf-8")))
        self.assertFalse(result["remote_write_enabled"])

    def test_missing_leaf_fails_closed(self):
        parent, leaves = fixture()
        del leaves["h:+test1"]
        with self.assertRaisesRegex(ChunkAuditError, "missing_or_invalid_leaf"):
            assemble_encrypted_chunks(parent, leaves, PATH, REV, PASSWORD, SALT)

    def test_wrong_passphrase_and_tampered_leaf(self):
        parent, leaves = fixture()
        with self.assertRaises(ChunkAuditError):
            assemble_encrypted_chunks(parent, leaves, PATH, REV, "wrong", SALT)
        leaves["h:+test1"]["data"] = "%=invalid"
        with self.assertRaisesRegex(ChunkAuditError, "unverified_leaf"):
            assemble_encrypted_chunks(parent, leaves, PATH, REV, PASSWORD, SALT)

    def test_expected_byte_size_and_revision_enforced(self):
        parent, leaves = fixture(size=999)
        with self.assertRaisesRegex(ChunkAuditError, "byte_count_mismatch"):
            assemble_encrypted_chunks(parent, leaves, PATH, REV, PASSWORD, SALT)
        parent, leaves = fixture()
        with self.assertRaisesRegex(ChunkAuditError, "invalid_parent_snapshot"):
            assemble_encrypted_chunks(parent, leaves, PATH, "2-" + "b" * 32,
                                      PASSWORD, SALT)

    def test_too_many_leaves_rejected_before_decrypt(self):
        parent, leaves = fixture()
        leaves.update({"h:+extra" + str(n): {} for n in range(520)})
        with patch("livesync_multichunk_audit.decrypt_hkdf_string") as decrypt:
            with self.assertRaisesRegex(ChunkAuditError, "invalid_leaf_snapshot"):
                assemble_encrypted_chunks(parent, leaves, PATH, REV, PASSWORD, SALT)
            decrypt.assert_not_called()


class OrphanAuditTests(unittest.TestCase):
    def setUp(self):
        self.leaves = {
            "h:+used": {"_id": "h:+used", "type": "leaf", "e_": True},
            "h:+unreferenced": {"_id": "h:+unreferenced", "type": "leaf", "e_": True},
        }

    def test_only_reports_candidates_never_deletion(self):
        report = audit_unreferenced_leaves(self.leaves, ["h:+used"],
                                           complete_snapshot=True)
        self.assertEqual(report["unreferenced_current_count"], 1)
        self.assertEqual(report["candidate_ids"], ["h:+unreferenced"])
        self.assertFalse(report["safe_to_delete"])
        self.assertFalse(report["delete_supported"])
        self.assertTrue(report["requires_historical_revision_and_replication_review"])
        self.assertFalse(report["remote_write_enabled"])

    def test_incomplete_snapshot_is_not_an_orphan_claim(self):
        with self.assertRaisesRegex(ChunkAuditError, "complete_snapshot_required"):
            audit_unreferenced_leaves(self.leaves, [], complete_snapshot=False)

    def test_invalid_reference_and_docs_fail(self):
        with self.assertRaisesRegex(ChunkAuditError, "invalid_parent_reference"):
            audit_unreferenced_leaves(self.leaves, ["not-a-leaf"],
                                      complete_snapshot=True)
        corrupt = dict(self.leaves)
        corrupt["h:+unreferenced"] = {"_id": "other", "type": "leaf", "e_": True}
        with self.assertRaisesRegex(ChunkAuditError, "invalid_leaf_document"):
            audit_unreferenced_leaves(corrupt, ["h:+used"],
                                      complete_snapshot=True)


if __name__ == "__main__":
    unittest.main()
