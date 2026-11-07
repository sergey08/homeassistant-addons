"""Fresh-install mode selection with no legacy provisioned vault or credentials."""
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from vault_selection import select_storage


class CleanInstallTests(unittest.TestCase):
    def test_local_fresh_install_needs_only_existing_share_folder(self):
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            share = base / "share"
            notes = share / "new-vault"
            notes.mkdir(parents=True)
            default = base / "data" / "vault"  # not created: no legacy installation
            selected = select_storage({
                "storage_mode": "local", "vault_path": str(notes),
                "enable_livesync": True, "enable_tunnel": False,
            }, default, share)
            self.assertEqual(selected, ("local", notes.resolve(), False))
            self.assertFalse(default.exists())
            self.assertEqual(list(notes.iterdir()), [])

    def test_fresh_local_without_folder_is_rejected_not_created(self):
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            share = base / "share"
            share.mkdir()
            folder = share / "missing"
            with self.assertRaises((ValueError, FileNotFoundError)):
                select_storage({"storage_mode": "local", "vault_path": str(folder)},
                               base / "data" / "vault", share)
            self.assertFalse(folder.exists())

    def test_create_default_local_vault_only_on_start_and_preserve_edits(self):
        with tempfile.TemporaryDirectory() as temp:
            share = Path(temp)
            vault = share / "obsidian-vault"
            default = share / "unused"
            options = {"storage_mode": "local", "create_local_vault": True, "enable_livesync": True}

            with self.assertRaises(ValueError):
                select_storage(options, default, share)
            self.assertFalse(vault.exists())

            expected = ("local", vault.resolve(), False)
            self.assertEqual(select_storage(options, default, share, initialize_local=True), expected)
            welcome = vault / "Bienvenida.md"
            self.assertIn("Tu bóveda local está lista", welcome.read_text(encoding="utf-8"))
            welcome.write_text("Edited", encoding="utf-8")
            self.assertEqual(select_storage(options, default, share, initialize_local=True), expected)
            self.assertEqual(welcome.read_text(encoding="utf-8"), "Edited")

    def test_create_custom_local_vault_and_reuse_existing_without_seeding(self):
        with tempfile.TemporaryDirectory() as temp:
            share = Path(temp)
            existing = share / "notes"
            existing.mkdir()
            default = share / "unused"
            options = {"storage_mode": "local", "create_local_vault": True}
            self.assertEqual(
                select_storage({**options, "vault_path": str(existing)}, default, share, initialize_local=True),
                ("local", existing.resolve(), False),
            )
            self.assertEqual(list(existing.iterdir()), [])

            vault = existing / "new vault"
            self.assertEqual(
                select_storage({**options, "vault_path": str(vault)}, default, share, initialize_local=True),
                ("local", vault.resolve(), False),
            )
            self.assertTrue((vault / "Bienvenida.md").is_file())

    def test_create_rejects_paths_outside_share_and_symlinks(self):
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            share = base / "share"
            share.mkdir()
            outside = base / "private"
            outside.mkdir()
            link = share / "link"
            link.symlink_to(outside, target_is_directory=True)
            for path in (share, outside / "new", share / "../private/new", link, link / "new"):
                with self.subTest(path=path), self.assertRaises(ValueError):
                    select_storage({"storage_mode": "local", "create_local_vault": True, "vault_path": str(path)},
                                   base / "default", share, initialize_local=True)
            self.assertEqual(list(outside.iterdir()), [])

    def test_fresh_livesync_uses_data_vault_and_is_disabled_until_configured(self):
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            default = base / "data" / "vault"
            mode, vault, sync = select_storage({
                "storage_mode": "livesync", "vault_path": "",
                "enable_livesync": False, "enable_tunnel": False, "create_local_vault": True,
            }, default, base / "share", initialize_local=True)
            self.assertEqual((mode, vault, sync), ("livesync", default, False))
            self.assertFalse(default.exists())
            self.assertFalse((base / "share").exists())


if __name__ == "__main__":
    unittest.main()
