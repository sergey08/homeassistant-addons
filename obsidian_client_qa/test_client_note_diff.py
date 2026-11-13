"""Read-only diff regression tests with isolated private storage."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from client_note_diff import compare_lines, DiffUnavailable, MAX_DIFF_LINES
from client_sync_baseline import digest
from server import app


class DiffAlgorithmTests(unittest.TestCase):
    def test_identical(self):
        self.assertEqual(compare_lines("Igual\n", "Igual\n")["diff"], "")
        self.assertFalse(compare_lines("Igual", "Igual")["different"])

    def test_direction_of_changes(self):
        result = compare_lines("Antiguo\n", "Nuevo\n")
        self.assertTrue(result["different"])
        self.assertIn("-Antiguo", result["diff"])
        self.assertIn("+Nuevo", result["diff"])
        self.assertFalse(result["truncated"])

    def test_markup_is_data(self):
        result = compare_lines("A\n", "<script>alert(1)</script>\n")
        self.assertIn("+<script>alert(1)</script>", result["diff"])

    def test_missing_local_and_oversized_blocked(self):
        with self.assertRaises(DiffUnavailable):
            compare_lines("nota", None)
        with self.assertRaises(DiffUnavailable):
            compare_lines("a" * 256001, "")

    def test_max_diff_lines(self):
        a = "".join("A%d\n" % i for i in range(1300))
        b = "".join("B%d\n" % i for i in range(1300))
        result = compare_lines(a, b)
        self.assertTrue(result["truncated"])
        self.assertLessEqual(result["lines"], MAX_DIFF_LINES)


class DiffEndpointTests(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.vault = str(Path(self.temp.name) / "vault")
        self.baselines = str(Path(self.temp.name) / "baselines")
        for key, value in (("_PRIVATE_VAULT", self.vault), ("_PRIVATE_BASELINES", self.baselines)):
            p = patch("server." + key, value)
            p.start()
            self.addCleanup(p.stop)

    def call(self, path="Test.md"):
        return self.client.get("/api/remote/diff-local?path=" + path)

    def test_shared_mode_refused_before_fetch(self):
        with patch("server.options", return_value={"editor_storage_mode": "mcp_shared"}), \
             patch("storage_selection.select_storage", return_value={"independent_of_mcp": False, "mode": "mcp_shared"}), \
             patch("server.read_encrypted_note") as fetch:
            response = self.call()
        self.assertEqual(response.status_code, 409)
        fetch.assert_not_called()

    def test_invalid_path_refused_before_fetch(self):
        with patch("server.options", return_value={"editor_storage_mode": "private"}), \
             patch("server.read_encrypted_note") as fetch:
            response = self.call("..%2Fescape.md")
        self.assertEqual(response.status_code, 409)
        fetch.assert_not_called()

    def test_remote_revision_unverified_fails_closed(self):
        target = Path(self.vault) / "Test.md"
        target.parent.mkdir(parents=True)
        target.write_text("LOCAL\n")
        with patch("server.options", return_value={"editor_storage_mode": "private"}), \
             patch("server.read_encrypted_note", return_value=(None, "changed")) as fetch:
            response = self.call()
        self.assertEqual(response.status_code, 409)
        fetch.assert_called_once_with("Test.md", verify_revision=True)

    def test_diff_only_reads_private_note(self):
        target = Path(self.vault) / "Test.md"
        target.parent.mkdir(parents=True)
        target.write_text("LOCAL\n")
        with patch("server.options", return_value={"editor_storage_mode": "private"}), \
             patch("server.read_encrypted_note", return_value=("REMOTE\n", None)) as fetch:
            response = self.call()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json["sync_state"], "no_baseline")
        self.assertTrue(response.json["different"])
        self.assertFalse(response.json["remote_write_enabled"])
        self.assertFalse(response.json["merge_enabled"])
        self.assertEqual(response.headers["Cache-Control"], "no-store")
        self.assertIn("+LOCAL", response.json["diff"])
        self.assertEqual(target.read_text(), "LOCAL\n")
        fetch.assert_called_once_with("Test.md", verify_revision=True)

    def test_missing_private_note_rejected(self):
        with patch("server.options", return_value={"editor_storage_mode": "private"}), \
             patch("server.read_encrypted_note", return_value=("REMOTE", None)):
            response = self.call()
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.json["error"], "local_copy_required")


if __name__ == "__main__":
    unittest.main()
