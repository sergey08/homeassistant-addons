"""Offline synthetic tests: never contact a remote vault."""
import unittest
from livesync_revision_contract import (
    RevisionConflict, prepare_conditional_document, require_successful_put,
)

class TestConditionalRevisionContract(unittest.TestCase):
    def setUp(self):
        self.rev = "7-" + "a" * 32
        self.original = {"_id": "synthetic-note", "_rev": self.rev, "type": "plain"}
        self.updated = {"_id": "synthetic-note", "_rev": self.rev, "type": "plain", "children": ["synthetic-leaf"]}

    def test_same_revision_prepares_nonmutating_candidate(self):
        candidate = prepare_conditional_document(self.original, self.updated, self.rev)
        self.assertEqual(candidate, self.updated)
        self.assertIsNot(candidate, self.updated)
        self.assertNotIn("children", self.original)

    def test_stale_revision_is_rejected(self):
        with self.assertRaisesRegex(RevisionConflict, "revision_conflict"):
            prepare_conditional_document(self.original, self.updated, "6-" + "b" * 32)

    def test_changed_document_identity_is_rejected(self):
        with self.assertRaisesRegex(RevisionConflict, "identity_or_revision_changed"):
            prepare_conditional_document(self.original, dict(self.updated, _id="other"), self.rev)

    def test_changed_body_revision_is_rejected(self):
        with self.assertRaisesRegex(RevisionConflict, "identity_or_revision_changed"):
            prepare_conditional_document(self.original, dict(self.updated, _rev="8-" + "b" * 32), self.rev)

    def test_delete_is_rejected(self):
        with self.assertRaisesRegex(RevisionConflict, "deletion_not_supported"):
            prepare_conditional_document(self.original, dict(self.updated, deleted=True), self.rev)

    def test_conflict_never_returns_success(self):
        with self.assertRaisesRegex(RevisionConflict, "remote_revision_conflict"):
            require_successful_put(409, {"error": "conflict"})

    def test_success_must_be_explicit(self):
        self.assertTrue(require_successful_put(201, {"ok": True}))
        with self.assertRaises(RevisionConflict):
            require_successful_put(201, {"ok": False})
        with self.assertRaises(RevisionConflict):
            require_successful_put(500, {"ok": True})

if __name__ == "__main__":
    unittest.main()
