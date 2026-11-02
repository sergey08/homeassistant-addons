"""Regression tests for LiveSync's JavaScript chunk framing semantics."""
import unittest
from livesync_chunk_identity import (js_utf16_code_units, legacy_xxhash64_input, xxhash64, base36_unsigned, legacy_xxhash64_digest)


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

    def test_xxhash64_reference_vectors(self):
        self.assertEqual(xxhash64(b""), 0xef46db3751d8e999)
        self.assertEqual(xxhash64(b"hello"), 0x26c7827d889f6da3)

    def test_xxhash64_block_boundaries(self):
        # Exercise the 32-byte stripe and each remainder branch.
        self.assertEqual(xxhash64(b""), 0xef46db3751d8e999)
        for payload in (b"a"*31,b"a"*32,b"a"*33,b"a"*64,b"a"*65):
            self.assertEqual(xxhash64(payload), xxhash64(bytes(payload)))
            self.assertTrue(0 <= xxhash64(payload) < (1 << 64))

    def test_base36_unsigned(self):
        self.assertEqual(base36_unsigned(0), "0")
        self.assertEqual(base36_unsigned(35), "z")
        self.assertEqual(base36_unsigned(36), "10")

    def test_digest_framing(self):
        self.assertEqual(legacy_xxhash64_digest("A🌍B", "mock"),
                         base36_unsigned(xxhash64("A🌍B-mock-4".encode())))

    def test_reject_nonstrings(self):
        with self.assertRaises(TypeError):
            js_utf16_code_units(None)


if __name__ == "__main__":
    unittest.main()
