"""Safety and functionality tests for explicit local-only LiveSync saves."""
import unittest
from unittest.mock import patch
from server import app
from livesync_cli_bridge import CLIUnavailable


class LocalSaveTests(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()
        self.url = "/api/livesync-cli/local-save"
        self.payload = {"mode": "create", "path": "Notes/New.md", "content": "# Hello"}

    def post(self, payload=None, **kwargs):
        return self.client.post(self.url, json=self.payload if payload is None else payload, **kwargs)

    def test_disabled_by_default(self):
        with patch("server.options", return_value={}):
            response = self.post()
        self.assertEqual(response.status_code, 403)

    def test_create_writes_only_to_local_adapter(self):
        with patch("server.options", return_value={"livesync_cli_enabled": True}):
            with patch("livesync_cli_bridge.safe_create_local_note", return_value=True) as create:
                response = self.post()
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.json["remote_synced"])
        create.assert_called_once()

    def test_update_requires_expected_content(self):
        payload = {**self.payload, "mode": "update", "expected_content": "# Before"}
        with patch("server.options", return_value={"livesync_cli_enabled": True}):
            with patch("livesync_cli_bridge.safe_update_local_note", return_value=True) as update:
                response = self.post(payload)
        self.assertEqual(response.status_code, 200)
        update.assert_called_once()

    def test_conflict_does_not_report_success(self):
        with patch("server.options", return_value={"livesync_cli_enabled": True}):
            with patch("livesync_cli_bridge.safe_create_local_note", side_effect=CLIUnavailable("cli_note_already_exists")):
                response = self.post()
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.json["error"], "cli_note_already_exists")

    def test_cross_origin_blocked(self):
        with patch("server.options", return_value={"livesync_cli_enabled": True}):
            with patch("livesync_cli_bridge.safe_create_local_note") as create:
                response = self.post(headers={"Origin": "https://malicious.example"})
        self.assertEqual(response.status_code, 403)
        create.assert_not_called()

    def test_ingress_proxy_origin_allowed_with_same_origin_fetch_metadata(self):
        with patch("server.options", return_value={"livesync_cli_enabled": True}):
            with patch("livesync_cli_bridge.safe_create_local_note", return_value=True):
                response = self.post(headers={
                    "Origin": "https://casamedia.duckdns.org:8123",
                    "Sec-Fetch-Site": "same-origin",
                })
        self.assertEqual(response.status_code, 200)

    def test_cross_site_fetch_metadata_blocked(self):
        with patch("server.options", return_value={"livesync_cli_enabled": True}):
            with patch("livesync_cli_bridge.safe_create_local_note") as create:
                response = self.post(headers={"Sec-Fetch-Site": "cross-site"})
        self.assertEqual(response.status_code, 403)
        create.assert_not_called()

    def test_update_rejects_missing_expected_content(self):
        payload = {**self.payload, "mode": "update"}
        with patch("server.options", return_value={"livesync_cli_enabled": True}):
            with patch("livesync_cli_bridge.safe_update_local_note", side_effect=ValueError("invalid_expected_content")) as update:
                response = self.post(payload)
        self.assertEqual(response.status_code, 400)
        update.assert_called_once()

    def test_local_saves_share_one_process_lock(self):
        from server import _local_save_lock
        self.assertTrue(hasattr(_local_save_lock, "acquire"))
        self.assertTrue(hasattr(_local_save_lock, "release"))

    def test_invalid_path_blocked(self):
        with patch("server.options", return_value={"livesync_cli_enabled": True}):
            with patch("livesync_cli_bridge.safe_create_local_note") as create:
                response = self.post({**self.payload, "path": "../secret.md"})
        self.assertEqual(response.status_code, 400)
        create.assert_not_called()


if __name__ == "__main__":
    unittest.main()
