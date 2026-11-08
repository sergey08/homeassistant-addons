"""End-to-end private import API tests; all files remain in temporary dirs."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from client_sync_baseline import digest, load_baseline
from private_markdown_vault import read_note
from server import app


class PrivateImportTests(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.vault = str(Path(self.tmp.name) / "vault")
        self.backups = str(Path(self.tmp.name) / "backups")
        self.baselines = str(Path(self.tmp.name) / "baselines")
        self.config = patch("server.options", return_value={"editor_storage_mode": "private"})
        self.config.start()
        self.addCleanup(self.config.stop)
        for key, val in (("_PRIVATE_VAULT", self.vault),
                         ("_PRIVATE_BACKUPS", self.backups),
                         ("_PRIVATE_BASELINES", self.baselines)):
            p = patch("server." + key, val)
            p.start()
            self.addCleanup(p.stop)
        self.path = "Pruebas/Nota.md"

    def call(self, expected=None, headers=None):
        return self.client.post("/api/remote/import-private",
            json={"path": self.path, "expected_sha256": expected or digest("Remote")},
            headers=headers if headers is not None
                else {"X-Obsidian-Client-Action": "import-private"})

    def test_import_creates_private_note_and_baseline_once(self):
        with patch("server.read_encrypted_note", return_value=("Remote", None)) as reader:
            response = self.call()
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json["status"], "imported_private")
        self.assertFalse(response.json["remote_write_enabled"])
        self.assertEqual(read_note(self.vault, self.path)["content"], "Remote")
        self.assertEqual(load_baseline(self.baselines, self.path), digest("Remote"))
        reader.assert_called_once_with(self.path, verify_revision=True)

    def test_missing_action_header_never_fetches(self):
        with patch("server.read_encrypted_note") as reader:
            response = self.call(headers={})
        self.assertEqual(response.status_code, 403)
        reader.assert_not_called()

    def test_remote_changed_does_not_create_note_or_baseline(self):
        with patch("server.read_encrypted_note", return_value=("Updated", None)):
            response = self.call()
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.json["error"], "remote_content_changed")
        self.assertFalse((Path(self.vault) / self.path).exists())
        self.assertIsNone(load_baseline(self.baselines, self.path))

    def test_unverified_remote_does_not_import(self):
        with patch("server.read_encrypted_note", return_value=(None, "stale")):
            response = self.call()
        self.assertEqual(response.status_code, 409)
        self.assertFalse((Path(self.vault) / self.path).exists())

    def test_second_import_never_overwrites_existing_local(self):
        with patch("server.read_encrypted_note", return_value=("Remote", None)):
            first = self.call()
            second = self.call()
        self.assertEqual(first.status_code, 201)
        self.assertEqual(second.status_code, 409)
        self.assertEqual(read_note(self.vault, self.path)["content"], "Remote")

    def test_rejects_existing_local_note_even_without_baseline(self):
        target = Path(self.vault) / self.path
        target.parent.mkdir(parents=True)
        target.write_text("Unsynced private draft")
        with patch("server.read_encrypted_note", return_value=("Remote", None)):
            response = self.call()
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.json["error"], "local_note_exists")
        self.assertEqual(target.read_text(), "Unsynced private draft")

    def test_invalid_path_does_not_fetch_remote(self):
        self.path = "../unsafe.md"
        with patch("server.read_encrypted_note") as reader:
            response = self.call()
        self.assertEqual(response.status_code, 409)
        reader.assert_not_called()

    def test_cross_origin_rejected(self):
        with patch("server.read_encrypted_note") as reader:
            response = self.call(headers={
                "X-Obsidian-Client-Action": "import-private",
                "Sec-Fetch-Site": "cross-site",
                "Origin": "https://example.invalid"})
        self.assertEqual(response.status_code, 403)
        reader.assert_not_called()


if __name__ == "__main__":
    unittest.main()
