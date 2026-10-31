"""Safety tests for write preflight; no database access."""
import unittest
import hashlib
from livesync_write_preflight import validate_write_request, validate_update_snapshot, UnsafeWrite

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
                     "nota.txt", "", "a\n.md", "a\t.md", "A /nota.md", "A./nota.md"):
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

class TestOptimisticSnapshot(unittest.TestCase):
    def setUp(self):
        self.rev = "4-" + "a" * 32
        self.base = "# Nota\\nOriginal"
        self.digest = hashlib.sha256(self.base.encode("utf-8")).hexdigest()

    def check(self, **overrides):
        args = dict(path="Viajes/Nota.md", proposed_content="# Nota\\nNuevo",
                    expected_revision=self.rev, current_revision=self.rev,
                    expected_content_sha256=self.digest, current_content=self.base)
        args.update(overrides)
        return validate_update_snapshot(**args)

    def test_matching_snapshot(self):
        self.assertEqual(self.check()["operation"], "update")

    def test_revision_conflict(self):
        with self.assertRaisesRegex(UnsafeWrite, "revision_conflict"):
            self.check(current_revision="5-" + "b" * 32)

    def test_content_conflict_even_if_revision_matches(self):
        with self.assertRaisesRegex(UnsafeWrite, "content_conflict"):
            self.check(current_content="# Edited elsewhere")

    def test_invalid_hash_fails_closed(self):
        with self.assertRaisesRegex(UnsafeWrite, "expected_hash_invalid"):
            self.check(expected_content_sha256="INVALID")

    def test_invalid_current_revision_fails_closed(self):
        with self.assertRaisesRegex(UnsafeWrite, "current_revision_invalid"):
            self.check(current_revision=None)


if __name__ == "__main__":
    unittest.main()
