"""Remote library is read-only, explicit and independent of MCP."""
import unittest
from unittest.mock import patch
from server import app


class IndependentLibraryTests(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()

    def test_disabled_cli_refuses_remote_browser(self):
        with patch("server.options", return_value={"livesync_cli_enabled": False}):
            response = self.client.get("/remote/library")
        self.assertEqual(response.status_code, 409)

    def test_library_page_has_explicit_read_action_not_automatic_fetch(self):
        with patch("server.options", return_value={"livesync_cli_enabled": True}):
            response = self.client.get("/remote/library")
        body = response.get_data(as_text=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn('id="load"', body)
        self.assertIn('button.addEventListener("click"', body)
        self.assertIn('../api/remote/encrypted-notes', body)
        self.assertIn('../api/remote/note-content?path=', body)
        self.assertIn('method:"GET"', body)
        self.assertNotIn('remote-preview', body)
        self.assertIn('textContent=path', body)
        self.assertIn('content.textContent=note.content', body)
        self.assertIn('id="edit-action" hidden', body)
        self.assertIn('id="compare-local"', body)
        self.assertIn('id="show-diff"', body)
        self.assertIn("../api/remote/diff-local?path=", body)
        self.assertIn("diffResult.textContent=changes.different", body)
        for key in ("local_changed", "remote_changed", "conflict_both_changed", "same_result_both_changed", "local_missing", "no_baseline", "unchanged"):
            self.assertIn(key + ':"', body)
        self.assertIn("data.sync_state", body)
        self.assertIn("data.remote_write_enabled===false", body)
        self.assertIn('id="import-private"', body)
        self.assertIn('../api/remote/import-private', body)
        self.assertIn('X-Obsidian-Client-Action":"import-private', body)
        self.assertIn('../api/remote/compare-local?path=', body)
        self.assertIn('diverged_unknown_origin', body)
        self.assertIn('editLink.href="../remote/edit?path="+encodeURIComponent(path)', body)
        self.assertIn('typeof note.content!=="string"', body)
        self.assertIn("let selectionVersion=0;", body)
        self.assertIn("if(currentSelection!==selectionVersion)return;", body)
        self.assertIn("No modifica CouchDB ni sincroniza las notas.", body)
        self.assertNotIn("mcp_shared", body)
        self.assertNotIn("/share/obsidian-shared-vault", body)
        self.assertEqual(response.headers.get("Cache-Control"), "no-store")

    def test_existing_remote_preview_requires_explicit_action_header(self):
        with patch("server.options", return_value={"livesync_cli_enabled": True}):
            response = self.client.post("/api/livesync-cli/remote-preview", json={})
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json["error"], "missing_action_header")


if __name__ == "__main__":
    unittest.main()
