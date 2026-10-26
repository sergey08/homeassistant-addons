"""No-network tests for CouchDB conditional writes."""
import json
import unittest
from urllib.error import HTTPError
from couchdb_cas import put_revision_checked, RevisionConflict, UnsafeDocument

BASE = "http://db21ed7f-obsidian-syncserver-ssl:5984"
REV = "2-" + "a" * 32

class Response:
    def __init__(self, doc_id):
        self.doc_id = doc_id
    def __enter__(self): return self
    def __exit__(self, *args): return False
    def read(self, limit):
        return json.dumps({"ok": True, "id": self.doc_id, "rev": "3-" + "b" * 32}).encode()

class FakeOpener:
    def __init__(self, fail=None): self.request = None; self.fail = fail
    def open(self, request, timeout):
        self.request = request
        if self.fail:
            raise HTTPError(request.full_url, self.fail, "conflict", {}, None)
        return Response(json.loads(request.data)["_id"])

class TestConditionalPut(unittest.TestCase):
    def test_create_is_conditional(self):
        opener = FakeOpener()
        result = put_revision_checked(BASE, "notes", "", "", {"_id": "test:1"}, creating=True, opener=opener, wire_validator=lambda doc: True)
        self.assertEqual(result["id"], "test:1")
        self.assertEqual(opener.request.get_header("If-none-match"), "*")

    def test_update_requires_matching_revision(self):
        opener = FakeOpener()
        put_revision_checked(BASE, "notes", "", "", {"_id": "test:1", "_rev": REV},
                             expected_revision=REV, opener=opener, wire_validator=lambda doc: True)
        self.assertEqual(opener.request.get_header("If-match"), '"' + REV + '"')
        with self.assertRaises(UnsafeDocument):
            put_revision_checked(BASE, "notes", "", "", {"_id": "test:1", "_rev": REV},
                                 expected_revision="3-" + "b" * 32, opener=opener, wire_validator=lambda doc: True)

    def test_conflict_is_not_silent(self):
        with self.assertRaises(RevisionConflict):
            put_revision_checked(BASE, "notes", "", "", {"_id": "test:1", "_rev": REV},
                                 expected_revision=REV, opener=FakeOpener(fail=409), wire_validator=lambda doc: True)

    def test_missing_or_failed_validator_blocks_write(self):
        opener = FakeOpener()
        with self.assertRaises(UnsafeDocument):
            put_revision_checked(BASE, "notes", "", "", {"_id": "test:1"}, creating=True, opener=opener)
        self.assertIsNone(opener.request)
        with self.assertRaises(UnsafeDocument):
            put_revision_checked(BASE, "notes", "", "", {"_id": "test:1"}, creating=True,
                                 opener=opener, wire_validator=lambda doc: False)
        self.assertIsNone(opener.request)

    def test_wrong_target_rejected(self):
        with self.assertRaises(UnsafeDocument):
            put_revision_checked("https://example.com", "notes", "", "", {"_id": "test:1"}, creating=True, wire_validator=lambda doc: True)

if __name__ == "__main__":
    unittest.main()
