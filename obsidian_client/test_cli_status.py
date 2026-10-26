"""Ensure CLI status is honest and never triggers remote writes."""
import unittest
from unittest.mock import patch
import server


class CLIStatusTests(unittest.TestCase):
    def setUp(self):
        self.client = server.app.test_client()

    @patch("livesync_cli_bridge.validate_cli_installation", return_value=("/opt/livesync-cli/dist/index.cjs", "/data/livesync-client"))
    @patch("server.options", return_value={"livesync_cli_enabled": False})
    def test_disabled_is_not_remote_ready(self, _options, _validate):
        result = self.client.get("/api/livesync-cli/status")
        self.assertEqual(result.status_code, 200)
        self.assertFalse(result.json["enabled"])
        self.assertFalse(result.json["remote_writes_enabled"])
        self.assertFalse(result.json["remote_sync_configured"])
        self.assertNotIn("local_database_ready", result.json)

    @patch("livesync_cli_bridge.validate_cli_installation", return_value=("/opt/livesync-cli/dist/index.cjs", "/data/livesync-client"))
    @patch("server.options", return_value={"livesync_cli_enabled": True})
    def test_enabled_does_not_imply_sync(self, _options, _validate):
        result = self.client.get("/api/livesync-cli/status")
        self.assertTrue(result.json["installed"])
        self.assertEqual(result.json["status"], "awaiting_remote_configuration")
        self.assertFalse(result.json["remote_writes_enabled"])


if __name__ == "__main__":
    unittest.main()
