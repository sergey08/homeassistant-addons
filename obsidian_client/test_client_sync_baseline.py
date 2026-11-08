"""Baseline classification and private enrollment regression tests."""
import tempfile
import unittest
from unittest.mock import patch
from client_sync_baseline import (BaselineError, classify, digest,
                                  establish_baseline, load_baseline)
from server import app


class BaselineLogicTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = self.tmp.name

    def test_three_way_cases(self):
        base = digest("A")
        cases = [
            ("A", "A", "unchanged"),
            ("B", "A", "remote_changed"),
            ("A", "B", "local_changed"),
            ("B", "B", "same_result_both_changed"),
            ("B", "C", "conflict_both_changed"),
            ("B", None, "local_missing"),
        ]
        for remote, local, state in cases:
            with self.subTest(state=state):
                self.assertEqual(classify(base, remote, local)["sync_state"], state)

    def test_no_baseline_must_not_infer_direction(self):
        result = classify(None, "remote", "local")
        self.assertEqual(result["sync_state"], "no_baseline")
        self.assertIsNone(result["remote_changed"])

    def test_enroll_identical_once_and_never_replace(self):
        result = establish_baseline(self.root, "Folder/Test.md", "same", "same")
        self.assertTrue(result["created"])
        self.assertEqual(load_baseline(self.root, "Folder/Test.md"), digest("same"))
        self.assertFalse(establish_baseline(self.root, "Folder/Test.md", "same", "same")["created"])
        with self.assertRaises(BaselineError):
            establish_baseline(self.root, "Folder/Test.md", "other", "other")
        self.assertEqual(load_baseline(self.root, "Folder/Test.md"), digest("same"))

    def test_mismatch_does_not_write(self):
        with self.assertRaises(BaselineError):
            establish_baseline(self.root, "x.md", "remote", "local")
        self.assertIsNone(load_baseline(self.root, "x.md"))

    def test_paths_cannot_escape_private_metadata(self):
        for path in ("../x.md", "/absolute.md", ".hidden.md", "a/../x.md"):
            with self.subTest(path=path), self.assertRaises(BaselineError):
                load_baseline(self.root, path)


class BaselineAPIContracts(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()

    def test_explicit_action_required(self):
        with patch("server.options", return_value={"editor_storage_mode": "private"}):
            response = self.client.post("/api/remote/establish-baseline",
                                        json={"path": "x.md", "expected_sha256": digest("x")})
        self.assertEqual(response.status_code, 403)

    def test_shared_mode_refused_before_remote_access(self):
        with patch("server.options", return_value={"editor_storage_mode": "mcp_shared"}), \
             patch("storage_selection.select_storage", return_value={"mode": "mcp_shared", "independent_of_mcp": False}), \
             patch("server.read_encrypted_note") as remote:
            response = self.client.post("/api/remote/establish-baseline",
                json={"path": "x.md", "expected_sha256": digest("x")},
                headers={"X-Obsidian-Client-Action": "establish-baseline"})
        self.assertEqual(response.status_code, 409)
        remote.assert_not_called()

    def test_cross_origin_denied(self):
        response = self.client.post("/api/remote/establish-baseline",
            json={"path": "x.md", "expected_sha256": digest("x")},
            headers={"X-Obsidian-Client-Action": "establish-baseline",
                     "Sec-Fetch-Site": "cross-site", "Origin": "https://example.org"})
        self.assertEqual(response.status_code, 403)


if __name__ == "__main__":
    unittest.main()
