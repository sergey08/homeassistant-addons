"""Safety tests for write preflight; no database access."""
import unittest
from livesync_write_preflight import validate_write_request, UnsafeWrite

class TestWritePreflight(unittest.TestCase):
    def test_create(self):
        result = validate_write_request("Viajes/Indonesia.md", "# Indonesia", None, creating=True)
        self.assertEqual(result["operation"], "create")
        self.assertEqual(result["bytes"], len("# Indonesia".encode("utf-8")))

    def test_update_requires_revision(self):
        with self.assertRaises(UnsafeWrite):
            validate_write_request("Nota.md", "texto", None)
        result = validate_write_request("Nota.md", "texto", "2-" + "a" * 32)
        self.assertEqual(result["operation"], "update")

    def test_rejects_unsafe_paths(self):
        for path in ("../secreto.md", "/absoluta.md", "A//nota.md",
                     "A/./nota.md", "A/../nota.md", ".oculta.md",
                     "A/.oculta/nota.md", "A\\nota.md", "A\x00nota.md",
                     "nota.txt", ""):
            with self.subTest(path=repr(path)), self.assertRaises(UnsafeWrite):
                validate_write_request(path, "texto", None, creating=True)

    def test_rejects_invalid_revision(self):
        for revision in ("", "1-bad", "0-" + "a" * 32, "1-" + "g" * 32):
            with self.subTest(revision=revision), self.assertRaises(UnsafeWrite):
                validate_write_request("Nota.md", "texto", revision)

    def test_rejects_overlarge_content(self):
        with self.assertRaises(UnsafeWrite):
            validate_write_request("Nota.md", "a" * 2_000_001, None, creating=True)

    def test_create_does_not_accept_revision(self):
        with self.assertRaises(UnsafeWrite):
            validate_write_request("Nota.md", "texto", "1-" + "a" * 32, creating=True)

if __name__ == "__main__":
    unittest.main()
