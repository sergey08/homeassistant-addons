"""Manual remote-to-private pull: isolated files, no CouchDB writes."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from client_sync_baseline import digest, load_baseline, establish_baseline
from private_markdown_vault import read_note, save_note
from server import app


class PrivatePullTests(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        root = Path(self.tmp.name)
        self.path = "Folder/Note.md"
        self.vault = str(root / "vault")
        self.backups = str(root / "markdown-backups")
        self.baselines = str(root / "baselines")
        self.baseline_backups = str(root / "baseline-backups")
        for key, value in (
            ("_PRIVATE_VAULT", self.vault),
            ("_PRIVATE_BACKUPS", self.backups),
            ("_PRIVATE_BASELINES", self.baselines),
            ("_PRIVATE_BASELINE_BACKUPS", self.baseline_backups),
        ):
            patcher = patch("server." + key, value)
            patcher.start()
            self.addCleanup(patcher.stop)
        options_patch = patch("server.options", return_value={"editor_storage_mode": "private"})
        options_patch.start()
        self.addCleanup(options_patch.stop)
        save_note(self.vault, self.backups, self.path, "base", "create")
        establish_baseline(self.baselines, self.path, "base", "base")

    def pull(self, remote="remote", old="base", expected_remote=None, headers=None):
        data = {
            "path": self.path,
            "expected_baseline_sha256": digest(old),
            "expected_local_sha256": digest(old),
            "expected_remote_sha256": expected_remote or digest(remote),
        }
        return self.client.post("/api/remote/pull-private", json=data,
            headers=({"X-Obsidian-Client-Action": "pull-private"}
                     if headers is None else headers))

    def test_success_updates_only_private_and_preserves_both_backups(self):
        with patch("server.read_encrypted_note", return_value=("remote", None)) as read:
            response = self.pull()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json["status"], "pulled_private")
        self.assertTrue(response.json["baseline_updated"])
        self.assertTrue(response.json["local_backup_created"])
        self.assertFalse(response.json["remote_write_enabled"])
        self.assertEqual(read_note(self.vault, self.path)["content"], "remote")
        self.assertEqual(load_baseline(self.baselines, self.path), digest("remote"))
        saved = list(Path(self.backups).rglob("*.md"))
        self.assertEqual(len(saved), 1)
        self.assertEqual(saved[0].read_text(), "base")
        history = list(Path(self.baseline_backups).rglob("*.json"))
        self.assertEqual(len(history), 1)
        self.assertIn(digest("base"), history[0].read_text())
        read.assert_called_once_with(self.path, verify_revision=True)

    def test_local_changed_blocks_without_backup_or_write(self):
        save_note(self.vault, self.backups, self.path, "local draft", "update",
                  expected_sha256=digest("base"))
        with patch("server.read_encrypted_note", return_value=("remote", None)):
            response = self.pull()
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.json["error"], "local_or_baseline_changed")
        self.assertEqual(read_note(self.vault, self.path)["content"], "local draft")
        self.assertEqual(load_baseline(self.baselines, self.path), digest("base"))

    def test_changed_remote_rejected(self):
        with patch("server.read_encrypted_note", return_value=("different", None)):
            response = self.pull()
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.json["error"], "remote_content_changed")
        self.assertEqual(read_note(self.vault, self.path)["content"], "base")

    def test_missing_action_header_never_fetches(self):
        with patch("server.read_encrypted_note") as fetch:
            response = self.pull(headers={})
        self.assertEqual(response.status_code, 403)
        fetch.assert_not_called()

    def test_cross_site_never_fetches(self):
        with patch("server.read_encrypted_note") as fetch:
            response = self.pull(headers={"X-Obsidian-Client-Action": "pull-private",
                                          "Sec-Fetch-Site": "cross-site"})
        self.assertEqual(response.status_code, 403)
        fetch.assert_not_called()

    def test_missing_baseline_blocks(self):
        (Path(self.baselines) / next(Path(self.baselines).glob("*.json")).name).unlink()
        with patch("server.read_encrypted_note", return_value=("remote", None)):
            response = self.pull()
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.json["error"], "local_or_baseline_changed")
        self.assertEqual(read_note(self.vault, self.path)["content"], "base")

    def test_remote_unverified_blocks(self):
        with patch("server.read_encrypted_note", return_value=(None, "stale")):
            response = self.pull()
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.json["error"], "remote_snapshot_not_verified")

    def test_invalid_direction_blocks_before_remote(self):
        with patch("server.read_encrypted_note") as fetch:
            response = self.pull(remote="base")
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.json["error"], "unsafe_pull_direction")
        fetch.assert_not_called()

    def test_non_independent_storage_rejected(self):
        with patch("storage_selection.select_storage",
                   return_value={"mode": "mcp_shared", "independent_of_mcp": False}), \
             patch("server.read_encrypted_note") as fetch:
            response = self.pull()
        self.assertEqual(response.status_code, 409)
        fetch.assert_not_called()

    def test_metadata_failure_retains_new_copy_and_old_baseline(self):
        with patch("server.read_encrypted_note", return_value=("remote", None)), \
             patch("client_sync_baseline.advance_baseline",
                   side_effect=__import__("client_sync_baseline").BaselineError("test")):
            response = self.pull()
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.json["error"], "baseline_advance_after_pull_failed")
        self.assertTrue(response.json["local_updated"])
        self.assertEqual(read_note(self.vault, self.path)["content"], "remote")
        self.assertEqual(load_baseline(self.baselines, self.path), digest("base"))
        self.assertEqual(len(list(Path(self.backups).rglob("*.md"))), 1)


if __name__ == "__main__":
    unittest.main()
