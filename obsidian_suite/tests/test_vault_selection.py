import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from vault_selection import select_vault


class VaultSelectionTests(unittest.TestCase):
    def test_default_keeps_old_vault(self):
        with tempfile.TemporaryDirectory() as d:
            default = Path(d) / "old" / "vault"
            self.assertEqual(select_vault("", default), default)

    def test_existing_markdown_folder_accepted(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d) / "share"
            vault = root / "notes"
            vault.mkdir(parents=True)
            self.assertEqual(select_vault(str(vault), Path(d) / "old", root), vault.resolve())

    def test_escape_and_symlinks_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d) / "share"
            root.mkdir()
            outside = Path(d) / "private"
            outside.mkdir()
            (root / "link").symlink_to(outside, target_is_directory=True)
            (root / "inside").mkdir()
            bad = [str(outside), str(root), str(root / "link"), str(root / "missing"), "relative/path", str(root / "inside" / ".." / ".." / "private")]
            for entry in bad:
                with self.subTest(path=entry), self.assertRaises((ValueError, FileNotFoundError)):
                    select_vault(entry, root / "default", root)


if __name__ == "__main__":
    unittest.main()
