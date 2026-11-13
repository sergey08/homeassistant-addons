"""Converged baseline acknowledgement must be safe, private and reversible."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from client_sync_baseline import (BaselineError, digest, establish_baseline,
                                  advance_baseline, load_baseline)
from private_markdown_vault import save_note
from server import app


class BaselineAdvanceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = str(Path(self.temp.name) / "baselines")
        self.history = str(Path(self.temp.name) / "history")
        self.path = "Folder/Test.md"
        establish_baseline(self.root, self.path, "old", "old")

    def test_advance_requires_convergence_and_backs_up_original(self):
        old_hash = digest("old")
        result = advance_baseline(self.root, self.history, self.path,
                                  old_hash, "new", "new")
        self.assertTrue(result["updated"])
        self.assertEqual(load_baseline(self.root, self.path), digest("new"))
        backups = list(Path(self.history).rglob("*.json"))
        self.assertEqual(len(backups), 1)
        self.assertIn(old_hash, backups[0].name)
        self.assertIn(old_hash, backups[0].read_text())

    def test_concurrent_revision_conflict_does_not_replace(self):
        with self.assertRaisesRegex(BaselineError, "baseline_revision_conflict"):
            advance_baseline(self.root, self.history, self.path,
                             digest("wrong"), "new", "new")
        self.assertEqual(load_baseline(self.root, self.path), digest("old"))

    def test_different_copies_do_not_replace(self):
        with self.assertRaisesRegex(BaselineError, "copies_not_identical"):
            advance_baseline(self.root, self.history, self.path,
                             digest("old"), "remote", "local")
        self.assertEqual(load_baseline(self.root, self.path), digest("old"))

    def test_missing_baseline_does_not_create_new_one(self):
        with self.assertRaises(BaselineError):
            advance_baseline(self.root, self.history, "missing.md",
                             digest("old"), "new", "new")
        self.assertIsNone(load_baseline(self.root, "missing.md"))

    def test_replay_with_old_revision_rejected(self):
        advance_baseline(self.root, self.history, self.path, digest("old"),
                         "new", "new")
        with self.assertRaisesRegex(BaselineError, "baseline_revision_conflict"):
            advance_baseline(self.root, self.history, self.path, digest("old"),
                             "other", "other")

    def test_identical_baseline_is_idempotent_no_history(self):
        result = advance_baseline(self.root, self.history, self.path,
                                  digest("old"), "old", "old")
        self.assertFalse(result["updated"])
        self.assertFalse(Path(self.history).exists())


class AdvanceAPIContracts(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.vault = str(Path(self.temp.name) / "vault")
        self.baselines = str(Path(self.temp.name) / "baselines")
        self.backups = str(Path(self.temp.name) / "baseline-backups")
        self.path = "Test.md"
        for name, value in (
            ("_PRIVATE_VAULT", self.vault),
            ("_PRIVATE_BASELINES", self.baselines),
        ):
            p = patch("server." + name, value)
            p.start()
            self.addCleanup(p.stop)
        self.options = patch("server.options", return_value={"editor_storage_mode": "private"})
        self.options.start()
        self.addCleanup(self.options.stop)

    def request_advance(self, **extra_headers):
        headers = {"X-Obsidian-Client-Action": "advance-baseline", **extra_headers}
        return self.client.post("/api/remote/advance-baseline",
            json={"path": self.path, "expected_baseline_sha256": digest("old"),
                  "expected_content_sha256": digest("new")}, headers=headers)

    def test_header_required_before_remote_read(self):
        with patch("server.read_encrypted_note") as fetch:
            response = self.client.post("/api/remote/advance-baseline",
                json={"path": self.path, "expected_baseline_sha256": digest("old"),
                      "expected_content_sha256": digest("new")})
        self.assertEqual(response.status_code, 403)
        fetch.assert_not_called()

    def test_cross_site_blocked_before_remote_read(self):
        with patch("server.read_encrypted_note") as fetch:
            response = self.request_advance(**{"Sec-Fetch-Site": "cross-site"})
        self.assertEqual(response.status_code, 403)
        fetch.assert_not_called()

    def test_remote_change_blocked(self):
        with patch("server.read_encrypted_note", return_value=("changed", None)) as fetch:
            response = self.request_advance()
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.json["error"], "remote_content_changed")
        fetch.assert_called_once_with(self.path, verify_revision=True)

    def test_shared_storage_rejected(self):
        with patch("storage_selection.select_storage",
                   return_value={"independent_of_mcp": False, "mode": "mcp_shared"}), \
             patch("server.read_encrypted_note") as fetch:
            response = self.request_advance()
        self.assertEqual(response.status_code, 409)
        fetch.assert_not_called()

    def test_verified_converged_copies_advance_metadata_only(self):
        establish_baseline(self.baselines, self.path, "old", "old")
        save_note(self.vault, str(Path(self.temp.name) / "markdown-backups"),
                  self.path, "new", "create")
        with patch("server.read_encrypted_note", return_value=("new", None)), \
             patch("client_sync_baseline.advance_baseline", wraps=advance_baseline) as updater, \
             patch("server._PRIVATE_BASELINES", self.baselines):
            # Patch the backup path only by intercepting the safe pure helper.
            original = advance_baseline
            def isolated_update(root, _backup, path, old, remote, local):
                return original(root, self.backups, path, old, remote, local)
            updater.side_effect = isolated_update
            response = self.request_advance()
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json["updated"])
        self.assertFalse(response.json["remote_write_enabled"])
        self.assertEqual(load_baseline(self.baselines, self.path), digest("new"))
        self.assertEqual((Path(self.vault) / self.path).read_text(), "new")


if __name__ == "__main__":
    unittest.main()
