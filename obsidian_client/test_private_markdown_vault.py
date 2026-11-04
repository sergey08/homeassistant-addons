import hashlib
import tempfile
import unittest
from pathlib import Path

from private_markdown_vault import LocalVaultError, read_note, save_note, list_notes


class PrivateMarkdownVaultTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.vault = Path(self.tmp.name) / "vault"
        self.backups = Path(self.tmp.name) / "backups"

    def test_create_update_revision_and_backup(self):
        first = save_note(self.vault, self.backups, "Folder/nota.md", "uno", "create")
        self.assertFalse(first["remote_synced"])
        original = read_note(self.vault, "Folder/nota.md")
        self.assertEqual(original["content"], "uno")
        result = save_note(self.vault, self.backups, "Folder/nota.md", "dos", "update",
                           expected_sha256=original["sha256"])
        self.assertEqual(result["sha256"], hashlib.sha256(b"dos").hexdigest())
        self.assertEqual(read_note(self.vault, "Folder/nota.md")["content"], "dos")
        snapshots = list(self.backups.rglob("nota.md"))
        self.assertEqual(len(snapshots), 1)
        self.assertEqual(snapshots[0].read_text(), "uno")

    def test_stale_write_does_not_modify_file_or_backup(self):
        save_note(self.vault, self.backups, "x.md", "actual", "create")
        with self.assertRaisesRegex(LocalVaultError, "revision_conflict"):
            save_note(self.vault, self.backups, "x.md", "stale", "update",
                      expected_sha256=hashlib.sha256(b"anterior").hexdigest())
        self.assertEqual(read_note(self.vault, "x.md")["content"], "actual")
        self.assertFalse(self.backups.exists())

    def test_existing_create_is_rejected(self):
        save_note(self.vault, self.backups, "x.md", "original", "create")
        with self.assertRaisesRegex(LocalVaultError, "note_exists"):
            save_note(self.vault, self.backups, "x.md", "overwrite", "create")
        self.assertEqual(read_note(self.vault, "x.md")["content"], "original")

    def test_path_traversal_and_symlink_rejected(self):
        for name in ("../escape.md", "/tmp/escape.md", ".hidden.md",
                     "x.txt", "folder/../escape.md", "folder\\note.md"):
            with self.subTest(name=name), self.assertRaises(LocalVaultError):
                save_note(self.vault, self.backups, name, "text", "create")
        self.vault.mkdir(exist_ok=True)
        (self.vault / "link").symlink_to(self.backups, target_is_directory=True)
        with self.assertRaisesRegex(LocalVaultError, "symlink_not_allowed"):
            save_note(self.vault, self.backups, "link/trap.md", "unsafe", "create")

    def test_list_only_private_safe_markdown(self):
        save_note(self.vault, self.backups, "Notes/first.md", "safe", "create")
        (self.vault / ".hidden.md").write_text("hidden")
        (self.vault / "Notes" / "link.md").symlink_to(self.vault / "Notes" / "first.md")
        self.assertEqual(list_notes(self.vault), ["Notes/first.md"])

    def test_invalid_revision_and_content(self):
        save_note(self.vault, self.backups, "x.md", "ok", "create")
        with self.assertRaisesRegex(LocalVaultError, "expected_revision_required"):
            save_note(self.vault, self.backups, "x.md", "changed", "update")
        with self.assertRaisesRegex(LocalVaultError, "note_too_large"):
            save_note(self.vault, self.backups, "huge.md", "x" * 2_000_001, "create")


if __name__ == "__main__":
    unittest.main()
