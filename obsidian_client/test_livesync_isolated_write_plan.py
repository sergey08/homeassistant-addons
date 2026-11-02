"""Fail-closed tests for side-effect-free LiveSync create candidate."""
import base64
import unittest

from livesync_crypto import decrypt_hkdf_string
from livesync_chunk_identity import legacy_chunk_id
from livesync_isolated_write_plan import prepare_isolated_note_create
from livesync_write_preflight import UnsafeWrite

SALT = base64.b64encode(b"disposable-ci-salt").decode()
PASS = "disposable-only-passphrase"


class IsolatedWritePlanTests(unittest.TestCase):
    def test_creation_encrypted_and_content_addressed(self):
        content = "# Example\nOne note 🌍\n"
        plan = prepare_isolated_note_create(
            "Tests/Example.md", content, PASS, SALT, created_millis=1730000000000)
        self.assertEqual(plan["write_order"], ("leaf", "parent"))
        self.assertEqual(plan["parent"]["_id"], "tests/example.md")
        self.assertEqual(plan["parent"]["path"], "Tests/Example.md")
        self.assertEqual(plan["parent"]["children"], [plan["leaf"]["_id"]])
        self.assertEqual(plan["leaf"]["_id"], "h:" + legacy_chunk_id(content, PASS))
        self.assertEqual(plan["parent"]["size"], len(content.encode("utf-8")))
        self.assertEqual(decrypt_hkdf_string(plan["leaf"]["data"], PASS, SALT), content)
        self.assertEqual(plan["parent"]["eden"], {})
        self.assertNotIn("_rev", plan["parent"])

    def test_deterministic_id_randomized_ciphertext(self):
        first = prepare_isolated_note_create("One.md", "text", PASS, SALT, created_millis=1)
        second = prepare_isolated_note_create("Two.md", "text", PASS, SALT, created_millis=2)
        self.assertEqual(first["leaf"]["_id"], second["leaf"]["_id"])
        self.assertNotEqual(first["leaf"]["data"], second["leaf"]["data"])

    def test_forbids_production_and_multichunk(self):
        for kwargs in ({"remote_writes_enabled": True}, {"remote_writes_enabled": 1}):
            with self.assertRaises(UnsafeWrite):
                prepare_isolated_note_create("Test.md", "content", PASS, SALT,
                                             created_millis=1, **kwargs)
        with self.assertRaises(UnsafeWrite):
            prepare_isolated_note_create("Test.md", "a" * 1001, PASS, SALT,
                                         created_millis=1)
        with self.assertRaises(UnsafeWrite):
            prepare_isolated_note_create("Test.md", "", PASS, SALT, created_millis=1)
        with self.assertRaises(UnsafeWrite):
            prepare_isolated_note_create("../unsafe.md", "note", PASS, SALT,
                                         created_millis=1)
        with self.assertRaises(UnsafeWrite):
            prepare_isolated_note_create("Test.md", "note", PASS, SALT,
                                         created_millis=True)


if __name__ == "__main__":
    unittest.main()
