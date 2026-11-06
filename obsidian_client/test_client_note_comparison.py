"""Read-only Client comparison safety tests."""
import unittest
from unittest.mock import patch
from client_note_comparison import compare_note_contents
from server import app


PRIVATE = {"editor_storage_mode": "private"}


class ComparisonUnitTests(unittest.TestCase):
    def test_remote_only(self):
        result = compare_note_contents("Remote", None)
        self.assertEqual(result["state"], "remote_only")
        self.assertFalse(result["safe_to_auto_merge"])

    def test_identical(self):
        result = compare_note_contents("Español ☀️", "Español ☀️")
        self.assertEqual(result["state"], "identical")
        self.assertTrue(result["identical"])

    def test_different_does_not_claim_direction(self):
        result = compare_note_contents("remote", "local")
        self.assertEqual(result["state"], "diverged_unknown_origin")
        self.assertFalse(result["safe_to_auto_merge"])
        self.assertNotEqual(result["remote_sha256"], result["local_sha256"])

    def test_invalid_content(self):
        with self.assertRaises(ValueError):
            compare_note_contents(None, "local")


class ComparisonEndpointTests(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()

    def test_rejects_shared_mode_before_remote_fetch(self):
        with patch("server.options", return_value={"editor_storage_mode": "mcp_shared"}), \
             patch("server.read_encrypted_note") as fetch:
            response = self.client.get("/api/remote/compare-local?path=Test.md")
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.json["error"], "independent_local_mode_required")
        fetch.assert_not_called()

    def test_unsafe_path_does_not_fetch_remote(self):
        with patch("server.options", return_value=PRIVATE), \
             patch("server.read_encrypted_note") as fetch:
            response = self.client.get("/api/remote/compare-local?path=../bad.md")
        self.assertEqual(response.status_code, 400)
        fetch.assert_not_called()

    def test_remote_failed_is_fail_closed(self):
        with patch("server.options", return_value=PRIVATE), \
             patch("server.read_encrypted_note", return_value=(None, "stale")):
            response = self.client.get("/api/remote/compare-local?path=Test.md")
        self.assertEqual(response.status_code, 409)
        self.assertTrue(response.json["read_only"])

    def test_remote_only_when_local_missing(self):
        from private_markdown_vault import LocalVaultError
        with patch("server.options", return_value=PRIVATE), \
             patch("server.read_encrypted_note", return_value=("remote", None)) as fetch, \
             patch("private_markdown_vault.read_note", side_effect=LocalVaultError("note_not_found")):
            response = self.client.get("/api/remote/compare-local?path=Test.md")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json["state"], "remote_only")
        self.assertFalse(response.json["remote_write_enabled"])
        self.assertFalse(response.json["baseline_available"])
        fetch.assert_called_once_with("Test.md", verify_revision=True)
