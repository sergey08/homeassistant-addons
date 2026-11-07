"""Manual sync intent is classification only; no network writes."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from client_sync_baseline import digest, establish_baseline
from client_manual_sync_decision import decide_manual_sync, SyncBlocked
from private_markdown_vault import save_note
from server import app


class DecisionTests(unittest.TestCase):
    def test_candidates_and_conflict(self):
        original = digest("base")
        cases = [
            ("base", "base", "none", "unchanged"),
            ("base", "local", "upload_candidate", "local_changed"),
            ("remote", "base", "download_candidate", "remote_changed"),
            ("new", "new", "acknowledge_candidate", "same_result_both_changed"),
            ("remote", "local", "block", "conflict_both_changed"),
            ("remote", None, "block", "local_missing"),
        ]
        for remote, local, action, state in cases:
            with self.subTest(state=state):
                p = decide_manual_sync(original, remote, local, remote_verified=True)
                self.assertEqual((p["action"], p["sync_state"]), (action, state))
                self.assertFalse(p["write_authorized"])
                self.assertFalse(p["remote_write_enabled"])
                self.assertFalse(p["safe_to_auto_merge"])

    def test_unknown_ancestry_does_not_authorize_write(self):
        p = decide_manual_sync(None, "remote", "local", remote_verified=True)
        self.assertEqual(p["action"], "block")
        self.assertEqual(p["reason"], "no_common_ancestor")

    def test_unverified_remote_fails_closed(self):
        with self.assertRaisesRegex(SyncBlocked, "remote_snapshot_not_verified"):
            decide_manual_sync(digest("base"), "remote", "local")


class PreflightAPITests(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.path = "Test.md"
        self.vault = str(self.root / "vault")
        self.baselines = str(self.root / "baselines")
        for name, value in (("_PRIVATE_VAULT", self.vault),
                            ("_PRIVATE_BASELINES", self.baselines)):
            p = patch("server." + name, value)
            p.start()
            self.addCleanup(p.stop)
        self.options = patch("server.options", return_value={"editor_storage_mode": "private"})
        self.options.start()
        self.addCleanup(self.options.stop)

    def test_verified_plan_does_not_touch_notes(self):
        establish_baseline(self.baselines, self.path, "base", "base")
        save_note(self.vault, str(self.root / "backups"), self.path, "local", "create")
        with patch("server.read_encrypted_note", return_value=("base", None)) as fetch:
            response = self.client.get("/api/remote/manual-sync-plan?path=Test.md")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json["action"], "upload_candidate")
        self.assertFalse(response.json["execute_supported"])
        self.assertFalse(response.json["write_authorized"])
        self.assertFalse(response.json["remote_write_enabled"])
        self.assertEqual((self.root / "vault" / self.path).read_text(), "local")
        self.assertEqual(response.headers.get("Cache-Control"), "no-store")
        fetch.assert_called_once_with("Test.md", verify_revision=True)

    def test_remote_unverified_fails(self):
        with patch("server.read_encrypted_note", return_value=(None, "changed")):
            response = self.client.get("/api/remote/manual-sync-plan?path=Test.md")
        self.assertEqual(response.status_code, 409)

    def test_cross_storage_mode_denied_before_remote(self):
        with patch("storage_selection.select_storage",
                   return_value={"mode": "mcp_shared", "independent_of_mcp": False}), \
             patch("server.read_encrypted_note") as fetch:
            response = self.client.get("/api/remote/manual-sync-plan?path=Test.md")
        self.assertEqual(response.status_code, 409)
        fetch.assert_not_called()


if __name__ == "__main__":
    unittest.main()
