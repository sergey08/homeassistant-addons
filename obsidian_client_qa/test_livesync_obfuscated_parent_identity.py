"""Offline legacy path-ID derivation fixture tests."""
import hashlib
import unittest
from livesync_obfuscated_parent_identity import legacy_obfuscated_parent_id
from livesync_write_preflight import UnsafeWrite

class LegacyParentIdentityTests(unittest.TestCase):
    def test_nested_sha256_fixture(self):
        path="Notes/Example.md"
        password="disposable-only"
        inner=hashlib.sha256(password.encode()).hexdigest()
        expected="f:"+hashlib.sha256((inner+":"+path.lower()).encode()).hexdigest()
        self.assertEqual(legacy_obfuscated_parent_id(path,password),expected)
        self.assertEqual(len(expected),66)
    def test_case_mode_matters(self):
        low=legacy_obfuscated_parent_id("Notes/Example.md","test")
        high=legacy_obfuscated_parent_id("Notes/Example.md","test",case_insensitive=False)
        self.assertNotEqual(low,high)
    def test_rejects_unsupported_keyed_derivation(self):
        with self.assertRaisesRegex(UnsafeWrite,"keyed_id_derivation_not_supported"):
            legacy_obfuscated_parent_id("Notes/Example.md","test",id_derivation_key="secret")
    def test_rejects_unsafe_path(self):
        with self.assertRaises(UnsafeWrite):
            legacy_obfuscated_parent_id("../unsafe.md","test")

if __name__=="__main__":
    unittest.main()
