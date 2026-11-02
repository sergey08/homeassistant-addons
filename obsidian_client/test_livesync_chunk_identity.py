"""Regression tests for LiveSync's JavaScript chunk framing semantics."""
import unittest
from livesync_chunk_identity import js_utf16_code_units, legacy_xxhash64_input


class ChunkIdentityInputTests(unittest.TestCase):
    def test_ascii_length(self):
        self.assertEqual(js_utf16_code_units("ABC"), 3)
        self.assertEqual(legacy_xxhash64_input("ABC", "mock"), b"ABC-mock-3")

    def test_non_bmp_uses_two_js_code_units(self):
        self.assertEqual(js_utf16_code_units("A🌍B"), 4)
        self.assertEqual(legacy_xxhash64_input("A🌍B", "x"), "A🌍B-x-4".encode())

    def test_combining_character_is_not_normalized(self):
        self.assertEqual(js_utf16_code_units("e\u0301"), 2)
        self.assertEqual(legacy_xxhash64_input("e\u0301", "x"), "e\u0301-x-2".encode())

    def test_reject_nonstrings(self):
        with self.assertRaises(TypeError):
            js_utf16_code_units(None)


if __name__ == "__main__":
    unittest.main()
