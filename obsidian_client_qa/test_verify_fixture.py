"""Offline fixture verifier tests / Pruebas aisladas del verificador."""
import unittest
from verify_fixture import verify
from livesync_plain import UnsupportedNote


class FixtureVerifierTests(unittest.TestCase):
    def test_good_synthetic_fixture(self):
        fixture = {
            "parent": {"type": "plain", "path": "Demo/Hello.md",
                       "children": ["h:a"], "size": 5},
            "chunks": {"h:a": {"type": "leaf", "data": "Hello"}},
            "expected": {"path": "Demo/Hello.md", "content": "Hello"}
        }
        self.assertTrue(verify(fixture))

    def test_mismatched_fixture_fails(self):
        fixture = {
            "parent": {"type": "plain", "path": "Demo/Hello.md",
                       "data": "Hello", "size": 5},
            "chunks": {},
            "expected": {"path": "Demo/Hello.md", "content": "Wrong"}
        }
        with self.assertRaises(AssertionError):
            verify(fixture)

    def test_invalid_fixture_fields_rejected(self):
        with self.assertRaises(ValueError):
            verify({"parent": {}, "chunks": {}, "expected": {}, "credentials": "not allowed"})


if __name__ == "__main__":
    unittest.main()
