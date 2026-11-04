"""Safety and functionality tests for explicit local-only LiveSync saves."""
import unittest
from unittest.mock import patch
from pathlib import Path
import tempfile
from server import app


class LocalSaveTests(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()
        self.url = "/api/livesync-cli/local-save"
        self.payload = {"mode": "create", "path": "Notes/New.md", "content": "# Hello"}
        self.tempdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tempdir.cleanup)
        self.vault = Path(self.tempdir.name) / "vault"
        self.backups = Path(self.tempdir.name) / "backups"
        for attr, value in (("_PRIVATE_VAULT", str(self.vault)),
                            ("_PRIVATE_BACKUPS", str(self.backups))):
            guard = patch("server." + attr, value)
            guard.start()
            self.addCleanup(guard.stop)

    def post(self, payload=None, **kwargs):
        headers = {"X-Obsidian-Client-Action": "local-save", **kwargs.pop("headers", {})}
        return self.client.post(self.url, json=self.payload if payload is None else payload, headers=headers, **kwargs)

    def test_create_and_update_private_markdown(self):
        created = self.post()
        self.assertEqual(created.status_code, 200)
        self.assertFalse(created.json["remote_synced"])
        self.assertEqual(self.client.get(
            "/api/livesync-cli/local-note?path=Notes/New.md").json["content"], "# Hello")
        updated = self.post({**self.payload, "mode": "update",
                             "expected_content": "# Hello", "content": "# Updated"})
        self.assertEqual(updated.status_code, 200)
        self.assertEqual(self.client.get(
            "/api/livesync-cli/local-note?path=Notes/New.md").json["content"], "# Updated")
        self.assertEqual(len(list(self.backups.rglob("New.md"))), 1)

    def test_write_requires_custom_action_header(self):
        response = self.client.post(self.url, json=self.payload)
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json["error"], "missing_action_header")

    def test_conflict_does_not_report_success(self):
        self.assertEqual(self.post().status_code, 200)
        self.assertEqual(self.post().status_code, 409)
        self.assertEqual(self.post().json["error"], "note_exists")
        conflict = self.post({**self.payload, "mode": "update",
                              "expected_content": "# Old", "content": "# Clobbered"})
        self.assertEqual(conflict.status_code, 409)
        self.assertEqual(conflict.json["error"], "revision_conflict")
        self.assertEqual(self.client.get(
            "/api/livesync-cli/local-note?path=Notes/New.md").json["content"], "# Hello")

    def test_cross_origin_blocked(self):
        self.assertEqual(self.post(headers={"Origin": "https://malicious.example"}).status_code, 403)

    def test_ingress_proxy_origin_allowed_with_same_origin_fetch_metadata(self):
        response = self.post(headers={
            "Origin": "https://example.invalid",
            "Sec-Fetch-Site": "same-origin",
        })
        self.assertEqual(response.status_code, 200)

    def test_cross_site_fetch_metadata_blocked(self):
        response = self.post(headers={"Sec-Fetch-Site": "cross-site"})
        self.assertEqual(response.status_code, 403)

    def test_update_rejects_missing_expected_content(self):
        self.assertEqual(self.post().status_code, 200)
        response = self.post({**self.payload, "mode": "update", "content": "# Revised"})
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.json["error"], "expected_content_required")

    def test_addon_uses_single_worker_for_local_save_lock(self):
        from pathlib import Path
        dockerfile = (Path(__file__).resolve().parent / "Dockerfile").read_text()
        self.assertIn('--workers 1', dockerfile)
        self.assertIn('--threads 4', dockerfile)

    def test_local_saves_share_one_process_lock(self):
        from server import _local_save_lock
        self.assertTrue(hasattr(_local_save_lock, "acquire"))
        self.assertTrue(hasattr(_local_save_lock, "release"))

    def test_setup_page_only_exposes_status_and_explicit_actions(self):
        with patch("server.options", return_value={"livesync_cli_enabled": True}):
            response = self.client.get("/livesync/setup")
        body = response.get_data(as_text=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn("connection-check", body)
        self.assertIn("configure-local", body)
        self.assertIn("confirm(", body)
        self.assertNotIn("couchdb_password", body)
        self.assertNotIn("livesync_e2ee_passphrase", body)

    def test_setup_page_requires_cli_enabled(self):
        with patch("server.options", return_value={}):
            response = self.client.get("/livesync/setup")
        self.assertEqual(response.status_code, 200)
        self.assertNotIn('id="install"', response.get_data(as_text=True))

    def test_remote_preview_is_explicit_and_isolated(self):
        config = {"livesync_cli_enabled": True}
        with patch("server.options", return_value=config):
            with patch("livesync_cli_bridge.fetch_remote_to_disposable_database",
                       return_value={"note_count": 1, "paths": ["Test.md"],
                                     "remote_writes_enabled": False,
                                     "persistent_local_modified": False}) as preview:
                denied = self.client.post("/api/livesync-cli/remote-preview")
                self.assertEqual(denied.status_code, 403)
                preview.assert_not_called()
                allowed = self.client.post("/api/livesync-cli/remote-preview",
                    headers={"X-Obsidian-Client-Action": "remote-preview"})
        self.assertEqual(allowed.status_code, 200)
        self.assertEqual(allowed.json["paths"], ["Test.md"])
        self.assertFalse(allowed.json["persistent_local_modified"])
        preview.assert_called_once_with(config, note_path=None)

    def test_connection_check_never_writes_or_syncs(self):
        config = {
            "livesync_cli_enabled": True,
            "couchdb_url": "https://localhost:6984",
            "couchdb_database": "notes",
            "couchdb_username": "user",
            "couchdb_password": "secret",
            "livesync_encryption_enabled": True,
            "livesync_e2ee_passphrase": "phrase",
        }
        from unittest.mock import MagicMock
        connection = MagicMock()
        connection.__enter__.return_value.status = 200
        with patch("server.options", return_value=config):
            with patch("server.build_opener") as opener:
                opener.return_value.open.return_value = connection
                response = self.client.get("/api/livesync-cli/connection-check")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json["status"], "database_reachable")
        self.assertFalse(response.json["encryption_verified"])
        self.assertFalse(response.json["remote_writes_enabled"])
        args, kwargs = opener.return_value.open.call_args
        self.assertEqual(args[0].get_method(), "HEAD")

    def test_connection_check_rejects_unconfigured(self):
        with patch("server.options", return_value={"livesync_cli_enabled": True}):
            with patch("server.build_opener") as opener:
                response = self.client.get("/api/livesync-cli/connection-check")
        self.assertEqual(response.status_code, 409)
        opener.assert_not_called()

    def test_configure_local_requires_explicit_action(self):
        with patch("server.options", return_value={"livesync_cli_enabled": True}):
            with patch("livesync_cli_bridge.install_official_cli_settings") as install:
                response = self.client.post("/api/livesync-cli/configure-local")
        self.assertEqual(response.status_code, 403)
        install.assert_not_called()

    def test_configure_local_rejects_incomplete_settings(self):
        with patch("server.options", return_value={"livesync_cli_enabled": True}):
            with patch("livesync_cli_bridge.install_official_cli_settings") as install:
                response = self.client.post(
                    "/api/livesync-cli/configure-local",
                    headers={"X-Obsidian-Client-Action": "configure-local"},
                )
        self.assertEqual(response.status_code, 409)
        install.assert_not_called()

    def test_configure_local_installs_without_sync(self):
        config = {
            "livesync_cli_enabled": True,
            "couchdb_url": "https://localhost:6984",
            "couchdb_database": "notes",
            "couchdb_username": "user",
            "couchdb_password": "secret",
            "livesync_encryption_enabled": True,
            "livesync_e2ee_passphrase": "phrase",
        }
        with patch("server.options", return_value=config):
            with patch("livesync_cli_bridge.install_official_cli_settings",
                       return_value={"installed": True, "remote_synced": False,
                                     "remote_writes_enabled": False}) as install:
                response = self.client.post(
                    "/api/livesync-cli/configure-local",
                    headers={"X-Obsidian-Client-Action": "configure-local"},
                )
        self.assertEqual(response.status_code, 201)
        self.assertFalse(response.json["remote_synced"])
        install.assert_called_once()

    def test_local_read_requires_existing_note(self):
        response = self.client.get("/api/livesync-cli/local-note?path=Notes/New.md")
        self.assertEqual(response.status_code, 404)

    def test_local_read_returns_content_without_remote_sync(self):
        self.assertEqual(self.post().status_code, 200)
        response = self.client.get("/api/livesync-cli/local-note?path=Notes/New.md")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json["content"], "# Hello")
        self.assertFalse(response.json["remote_synced"])

    def test_invalid_path_blocked(self):
        response = self.post({**self.payload, "path": "../secret.md"})
        self.assertEqual(response.status_code, 400)
        self.assertFalse((self.vault.parent / "secret.md").exists())


if __name__ == "__main__":
    unittest.main()
