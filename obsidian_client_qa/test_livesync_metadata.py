"""Tests for encrypted LiveSync metadata validation."""
import unittest
from livesync_metadata import validate_encrypted_parent, UnsupportedMetadata

class TestEncryptedParent(unittest.TestCase):
    def test_valid(self):
        self.assertEqual(validate_encrypted_parent(
            {"path":"Notas/Hola.md","children":["chunk1","chunk2"],"size":9},
            "Notas/Hola.md"), ("chunk1","chunk2"))

    def test_rejects_invalid_shapes(self):
        bad = [
            {"path":"Notas/Hola.md","children":[]},
            {"path":"Notas/Hola.md","children":["x","x"]},
            {"path":"Notas/Hola.md","children":[""]},
            {"path":"Notas/Hola.md","children":["x"],"size":-1},
            {"path":"Notas/Hola.md","children":["x"],"size":True},
            {"path":"Notas/Hola.md","children":["x"],"deleted":True},
            {"path":"Otro.md","children":["x"]},
        ]
        for item in bad:
            with self.subTest(item=item), self.assertRaises(UnsupportedMetadata):
                validate_encrypted_parent(item, "Notas/Hola.md")

if __name__ == "__main__":
    unittest.main()
