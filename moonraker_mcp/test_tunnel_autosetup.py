"""Isolated automatic tunnel setup tests; uses no network or real credentials."""
import json
import os
import stat
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tunnel_autosetup import provision_from_options
from tunnel_provision import ProvisionError


class TunnelAutoSetupTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.vendor = self.root / "vendor"
        self.vendor.write_bytes(b"test-binary")
        self.options = self.root / "options.json"
        self.key = self.root / "tunnel" / "api-key"
        self.binary = self.root / "tunnel" / "bin" / "tunnel-client"
        self.uid = os.getuid()
    def tearDown(self):
        self.temp.cleanup()
    def settings(self, key):
        self.options.write_text(json.dumps({"openai_tunnel_api_key": key}))
    def test_fresh_install_without_terminal(self):
        self.settings("restricted-test-credential-123")
        self.assertIn("ready", provision_from_options(self.root, self.vendor, self.uid))
        self.assertEqual(self.key.read_bytes(), b"restricted-test-credential-123")
        self.assertEqual(self.binary.read_bytes(), b"test-binary")
        self.assertEqual(stat.S_IMODE(self.key.stat().st_mode), 0o600)
        self.assertEqual(stat.S_IMODE(self.binary.stat().st_mode), 0o700)
    def test_existing_dev4_key_preserved_when_option_empty(self):
        self.settings("legacy-test-credential-123")
        provision_from_options(self.root, self.vendor, self.uid)
        self.settings("")
        provision_from_options(self.root, self.vendor, self.uid)
        self.assertEqual(self.key.read_bytes(), b"legacy-test-credential-123")
    def test_key_rotation_from_home_assistant(self):
        self.settings("previous-test-credential-123")
        provision_from_options(self.root, self.vendor, self.uid)
        self.settings("rotated-test-credential-987")
        provision_from_options(self.root, self.vendor, self.uid)
        self.assertEqual(self.key.read_bytes(), b"rotated-test-credential-987")
    def test_fresh_install_and_restart_with_password_field(self):
        """Full first-run experience: no downloaded ZIP or terminal provision."""
        self.settings("new-user-test-restricted-key-123")
        provision_from_options(self.root, self.vendor, self.uid)
        first_binary = self.binary.read_bytes()
        first_key = self.key.read_bytes()
        # A Supervisor restart with unchanged private options must be idempotent.
        provision_from_options(self.root, self.vendor, self.uid)
        self.assertEqual(self.binary.read_bytes(), first_binary)
        self.assertEqual(self.key.read_bytes(), first_key)
        self.assertEqual(stat.S_IMODE(self.key.stat().st_mode), 0o600)
        self.assertEqual(stat.S_IMODE(self.binary.stat().st_mode), 0o700)

    def test_invalid_new_password_does_not_destroy_valid_existing_key(self):
        self.settings("original-safe-secret-key-123")
        provision_from_options(self.root, self.vendor, self.uid)
        self.settings("invalid" + chr(10) + "secret-password")
        with self.assertRaises(ProvisionError):
            provision_from_options(self.root, self.vendor, self.uid)
        self.assertEqual(self.key.read_bytes(), b"original-safe-secret-key-123")

    def test_rotation_preserves_private_mode_and_new_key_only(self):
        self.settings("first-secret-for-rotation-123")
        provision_from_options(self.root, self.vendor, self.uid)
        self.settings("new-secret-for-rotation-456")
        provision_from_options(self.root, self.vendor, self.uid)
        self.assertEqual(self.key.read_bytes(), b"new-secret-for-rotation-456")
        self.assertEqual(stat.S_IMODE(self.key.stat().st_mode), 0o600)
        self.assertEqual(self.key.stat().st_uid, self.uid)
        # A restart must not bring back the retired credential.
        provision_from_options(self.root, self.vendor, self.uid)
        self.assertNotIn(b"first-secret", self.key.read_bytes())

    def test_symlinked_options_refused(self):
        payload = self.root / "payload.json"
        payload.write_text(json.dumps({"openai_tunnel_api_key": "fake-key-123456"}))
        self.options.symlink_to(payload)
        with self.assertRaisesRegex(ProvisionError, "trusted Home Assistant"):
            provision_from_options(self.root, self.vendor, self.uid)

    def test_symlinked_client_refused(self):
        self.settings("new-user-test-restricted-key-123")
        (self.root / "tunnel" / "bin").mkdir(parents=True)
        self.binary.symlink_to(self.vendor)
        with self.assertRaisesRegex(ProvisionError, "symbolic-link tunnel client"):
            provision_from_options(self.root, self.vendor, self.uid)

    def test_oversized_secret_rejected_without_leaking_value(self):
        self.settings("X" * 8193)
        with self.assertRaises(ProvisionError) as raised:
            provision_from_options(self.root, self.vendor, self.uid)
        self.assertNotIn("XXX", str(raised.exception))

    def test_missing_key_fails_closed(self):
        self.settings("")
        with self.assertRaisesRegex(ProvisionError, "Configure OpenAI"):
            provision_from_options(self.root, self.vendor, self.uid)
    def test_symlink_key_refused(self):
        self.settings("restricted-test-credential-123")
        (self.root / "tunnel").mkdir()
        self.key.symlink_to(self.vendor)
        with self.assertRaisesRegex(ProvisionError, "symbolic-link"):
            provision_from_options(self.root, self.vendor, self.uid)
    def test_invalid_key_never_leaks_into_exception(self):
        self.settings("test-key-with-newline" + chr(10) + "secret")
        with self.assertRaises(ProvisionError) as raised:
            provision_from_options(self.root, self.vendor, self.uid)
        self.assertNotIn("secret", str(raised.exception))
    def test_insecure_existing_permissions_rejected(self):
        self.settings("restricted-test-credential-123")
        provision_from_options(self.root, self.vendor, self.uid)
        os.chmod(self.binary, 0o777)
        with self.assertRaisesRegex(ProvisionError, "Insecure tunnel client"):
            provision_from_options(self.root, self.vendor, self.uid)

if __name__ == "__main__":
    unittest.main()
