"""Offline synthetic tests: never contact a remote vault."""
import unittest
from livesync_revision_contract import (
    RevisionConflict, prepare_conditional_document, require_successful_put,
    require_confirmed_put_response,
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

class TestCouchDbPutAcknowledgement(unittest.TestCase):
    def setUp(self):
        self.doc_id = "f:synthetic-parent"
        self.rev = "7-" + "a" * 32
        self.new_rev = "8-" + "b" * 32
        self.ack = {"ok": True, "id": self.doc_id, "rev": self.new_rev}

    def test_valid_ack_returns_new_revision(self):
        self.assertEqual(
            require_confirmed_put_response(201, self.ack, self.doc_id, self.rev),
            self.new_rev)
        self.assertEqual(
            require_confirmed_put_response(202, self.ack, self.doc_id, self.rev),
            self.new_rev)

    def test_conflict_is_never_accepted(self):
        with self.assertRaisesRegex(RevisionConflict, "remote_revision_conflict"):
            require_confirmed_put_response(
                409, {"error": "conflict"}, self.doc_id, self.rev)

    def test_incorrect_identity_or_revision_rejected(self):
        cases = [
            ({"ok": True, "id": "other", "rev": self.new_rev},
             "remote_document_identity_mismatch"),
            ({"ok": True, "id": self.doc_id}, "invalid_remote_revision"),
            ({"ok": True, "id": self.doc_id, "rev": self.rev},
             "unexpected_revision_generation"),
            ({"ok": True, "id": self.doc_id, "rev": "9-" + "c" * 32},
             "unexpected_revision_generation"),
            ({"ok": True, "id": self.doc_id, "rev": "8-invalid"},
             "invalid_remote_revision"),
        ]
        for ack, reason in cases:
            with self.subTest(ack=ack), self.assertRaisesRegex(RevisionConflict, reason):
                require_confirmed_put_response(201, ack, self.doc_id, self.rev)

    def test_malformed_ack_fails_closed(self):
        for status, ack in [
            (200, self.ack), (500, self.ack), (201, None),
            (201, {"ok": False, "id": self.doc_id, "rev": self.new_rev}),
            (201, ["not", "a", "document"]),
        ]:
            with self.subTest(status=status, ack=ack), self.assertRaises(RevisionConflict):
                require_confirmed_put_response(status, ack, self.doc_id, self.rev)

    def test_invalid_expected_id_or_previous_revision(self):
        with self.assertRaises(RevisionConflict):
            require_confirmed_put_response(201, self.ack, "", self.rev)
        with self.assertRaises(RevisionConflict):
            require_confirmed_put_response(201, self.ack, self.doc_id, "invalid")

if __name__ == "__main__":
    unittest.main()
