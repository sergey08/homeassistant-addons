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

if __name__ == "__main__":
    unittest.main()
