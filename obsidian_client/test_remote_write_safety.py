"""CI-only remote-write readiness gates; no real database writes."""
import unittest
from unittest.mock import patch
from client_sync_engine import write_safety_status
from server import app


class WriteSafetyTests(unittest.TestCase):
    def test_private_mode_does_not_enable_production_writes(self):
        status = write_safety_status({"editor_storage_mode": "private"})
        self.assertTrue(status["independent_of_mcp"])
        self.assertFalse(status["production_remote_writes_enabled"])
        self.assertFalse(status["manual_bidirectional_sync_enabled"])
        self.assertFalse(status["automatic_sync_enabled"])
        self.assertEqual(status["write_gate"], "closed")
        self.assertGreaterEqual(len(status["production_blockers"]), 4)

    def test_livesync_mode_is_not_implicit_authorization(self):
        status = write_safety_status({"editor_storage_mode": "livesync"})
        self.assertFalse(status["production_remote_writes_enabled"])
        self.assertEqual(status["write_gate"], "closed")

    def test_status_endpoint_must_not_expose_credentials_or_write(self):
        with patch("server.options", return_value={
            "editor_storage_mode": "private",
            "couchdb_password": "test-secret-should-not-leak",
            "livesync_e2ee_passphrase": "test-e2ee-should-not-leak"}), \
            patch("server.read_encrypted_note") as read:
            response = app.test_client().get("/api/remote/write-safety")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["Cache-Control"], "no-store")
        self.assertFalse(response.json["production_remote_writes_enabled"])
        self.assertNotIn("test-secret-should-not-leak", response.get_data(as_text=True))
        self.assertNotIn("test-e2ee-should-not-leak", response.get_data(as_text=True))
        read.assert_not_called()


if __name__ == "__main__":
    unittest.main()
