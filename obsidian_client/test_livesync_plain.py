"""Synthetic fixtures only; no network, vault, or CouchDB access."""
import unittest
from livesync_plain import decode_plain_note, UnsupportedNote


class PlainNoteTests(unittest.TestCase):
    def test_ordered_chunks(self):
        note = {"type": "plain", "path": "Travel/Example.md", "children": ["b", "a"]}
        chunks = {"a": {"type": "leaf", "data": "world"}, "b": {"type": "leaf", "data": "Hello "}}
        self.assertEqual(decode_plain_note(note, chunks), {"path": "Travel/Example.md", "content": "Hello world"})

    def test_inline_plain(self):
        self.assertEqual(
            decode_plain_note({"type": "plain", "path": "Example.md", "data": "# Note"}, {}),
            {"path": "Example.md", "content": "# Note"})

    def test_rejects_missing_chunk(self):
        with self.assertRaises(UnsupportedNote):
            decode_plain_note({"type": "plain", "path": "A.md", "children": ["absent"]}, {})

    def test_rejects_path_traversal(self):
        with self.assertRaises(UnsupportedNote):
            decode_plain_note({"type": "plain", "path": "../A.md", "data": "x"}, {})

    def test_rejects_encrypted_payload(self):
        with self.assertRaises(UnsupportedNote):
            decode_plain_note({"type": "plain", "path": "A.md", "children": ["a"]},
                              {"a": {"type": "leaf", "data": "e_encrypted"}})

    def test_rejects_conflicts(self):
        with self.assertRaises(UnsupportedNote):
            decode_plain_note({"type": "plain", "path": "A.md", "_conflicts": ["2-x"]}, {})

    def test_rejects_binary_notes(self):
        with self.assertRaises(UnsupportedNote):
            decode_plain_note({"type": "newnote", "path": "A.md"}, {})



    def test_rejects_missing_inline_data(self):
        with self.assertRaises(UnsupportedNote):
            decode_plain_note({"type": "plain", "path": "Empty.md"}, {})

    def test_allows_intentionally_empty_note(self):
        self.assertEqual(
            decode_plain_note({"type": "plain", "path": "Empty.md", "data": ""}, {}),
            {"path": "Empty.md", "content": ""})

    def test_rejects_nonstring_child_ids(self):
        with self.assertRaises(UnsupportedNote):
            decode_plain_note({"type": "plain", "path": "A.md", "children": [123]}, {})

    def test_rejects_conflicted_chunks(self):
        with self.assertRaises(UnsupportedNote):
            decode_plain_note({"type": "plain", "path": "A.md", "children": ["x"]},
                              {"x": {"type": "leaf", "data": "text", "_conflicts": ["2-abc"]}})


    def test_rejects_compressed_parent(self):
        with self.assertRaises(UnsupportedNote):
            decode_plain_note({"type": "plain", "path": "A.md", "compressed": True, "data": "x"}, {})

    def test_rejects_encrypted_chunk_flag(self):
        with self.assertRaises(UnsupportedNote):
            decode_plain_note({"type": "plain", "path": "A.md", "children": ["c"]},
                              {"c": {"type": "leaf", "data": "x", "encrypted": True}})


    def test_rejects_nonempty_note_with_missing_chunk_references(self):
        with self.assertRaises(UnsupportedNote):
            decode_plain_note({"type": "plain", "path": "Lost.md", "size": 50, "children": [], "data": ""}, {})


    def test_rejects_livesync_logical_deletion(self):
        with self.assertRaises(UnsupportedNote):
            decode_plain_note({"type": "plain", "path": "Deleted.md",
                               "deleted": True, "data": "old content"}, {})

    def test_rejects_pouchdb_tombstone(self):
        with self.assertRaises(UnsupportedNote):
            decode_plain_note({"type": "plain", "path": "Deleted.md",
                               "_deleted": True, "data": "old content"}, {})

    def test_preserves_order_and_does_not_modify_documents(self):
        from copy import deepcopy
        parent = {"type": "plain", "path": "Demo/Test.md", "children": ["second", "first"]}
        chunks = {"first": {"type": "leaf", "data": "B"},
                  "second": {"type": "leaf", "data": "A"}}
        snapshot = deepcopy((parent, chunks))
        result = decode_plain_note(parent, chunks)
        self.assertEqual(result["content"], "AB")
        self.assertEqual((parent, chunks), snapshot)


    def test_upstream_shaped_plain_metadata_with_eden(self):
        # Synthetic shape from public LiveSync schema, not a production fixture.
        parent = {"_id": "f:example", "type": "plain", "datatype": "plain",
                  "path": "Notes/Example.md", "children": ["h:first", "h:second"],
                  "eden": {}, "size": 11, "deleted": False}
        chunks = {"h:first": {"_id": "h:first", "type": "leaf", "data": "Hello "},
                  "h:second": {"_id": "h:second", "type": "leaf", "data": "world"}}
        self.assertEqual(decode_plain_note(parent, chunks)["content"], "Hello world")


    def test_rejects_document_shell_reported_upstream(self):
        # Sanitised metadata shape from upstream issue #1065; no note content.
        shell = {"_id": "f:example", "type": "plain", "path": "/\\:obfuscated",
                 "children": [], "size": 0, "ctime": 0, "mtime": 0, "eden": {}}
        with self.assertRaises(UnsupportedNote):
            decode_plain_note(shell, {})

    def test_rejects_encrypted_leaf_from_upstream_issue(self):
        parent = {"type": "plain", "path": "Example.md", "children": ["h:+example"]}
        chunks = {"h:+example": {"type": "leaf", "data": "opaque", "e_": True}}
        with self.assertRaises(UnsupportedNote):
            decode_plain_note(parent, chunks)


    def test_plain_text_array_with_upstream_metadata_fields(self):
        note = {"_id": "daily/note.md", "type": "plain", "datatype": "plain",
                "path": "daily/note.md", "data": ["First line\\n", "Second line\\n"],
                "mtime": 1740000000000, "ctime": 1740000000000,
                "children": [], "eden": {}}
        note["size"] = len("".join(note["data"]).encode("utf-8"))
        self.assertEqual(decode_plain_note(note, {})["content"], "First line\\nSecond line\\n")


    def test_rejects_encrypted_h_plus_chunk_identifier(self):
        parent = {"type": "plain", "path": "Demo/Test.md", "children": ["h:+encrypted"]}
        chunks = {"h:+encrypted": {"type": "leaf", "data": "opaque"}}
        with self.assertRaises(UnsupportedNote):
            decode_plain_note(parent, chunks)


    def test_upstream_reported_empty_parent_shell_is_not_a_note(self):
        # Upstream issue #1065: an empty f: metadata shell may coexist with
        # uploaded h: chunks. These must not be presented as empty Markdown.
        parent = {"_id": "f:example", "type": "plain",
                  "path": "Docs/ShouldNotAppear.md", "size": 0,
                  "children": [], "eden": {}, "mtime": 0, "ctime": 0}
        chunks = {"h:orphan": {"type": "leaf", "data": "orphaned content"}}
        with self.assertRaises(UnsupportedNote):
            decode_plain_note(parent, chunks)


    def test_rejects_size_mismatch(self):
        note = {"type": "plain", "path": "Example.md", "data": "Hello", "size": 20}
        with self.assertRaises(UnsupportedNote):
            decode_plain_note(note, {})

    def test_validates_utf8_size_of_unicode_note(self):
        note = {"type": "plain", "path": "Example.md", "data": "á", "size": 2}
        self.assertEqual(decode_plain_note(note, {})["content"], "á")


    def test_chunked_utf8_size_inconsistency_is_rejected(self):
        note = {"type": "plain", "path": "Notes/Unicode.md",
                "children": ["h:one", "h:two"], "size": 3}
        chunks = {"h:one": {"type": "leaf", "data": "á"},
                  "h:two": {"type": "leaf", "data": "€"}}
        with self.assertRaises(UnsupportedNote):
            decode_plain_note(note, chunks)

    def test_chunked_utf8_size_matching_is_accepted(self):
        note = {"type": "plain", "path": "Notes/Unicode.md",
                "children": ["h:one", "h:two"], "size": 5}
        chunks = {"h:one": {"type": "leaf", "data": "á"},
                  "h:two": {"type": "leaf", "data": "€"}}
        self.assertEqual(decode_plain_note(note, chunks)["content"], "á€")

if __name__ == "__main__":
    unittest.main()
