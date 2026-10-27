import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from vault_selection import select_vault, select_storage


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

    def test_storage_modes_and_upgrade_compatibility(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d) / "share"
            folder = root / "my-vault"
            folder.mkdir(parents=True)
            original = Path(d) / "existing-vault"
            cases = [
                ({}, ("livesync", original, False)),
                ({"enable_livesync": True}, ("livesync", original, True)),
                ({"storage_mode": "livesync", "enable_livesync": True, "vault_path": str(folder)},
                 ("livesync", original, True)),
                ({"storage_mode": "local", "enable_livesync": True, "vault_path": str(folder)},
                 ("local", folder.resolve(), False)),
            ]
            for options, expected in cases:
                with self.subTest(options=options):
                    self.assertEqual(select_storage(options, original, root), expected)
            for options in ({"storage_mode": "unknown"}, {"storage_mode": "local"},
                            {"storage_mode": "local", "vault_path": str(root / "missing")}):
                with self.subTest(rejected=options), self.assertRaises((ValueError, FileNotFoundError)):
                    select_storage(options, original, root)

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
