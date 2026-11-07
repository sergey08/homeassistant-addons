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
                "storage_mode": "Local - Personal folder path", "vault_path": str(notes),
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

    def test_default_local_vault_uses_app_config_even_with_a_legacy_vault(self):
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            app_config = base / "config"
            app_config.mkdir()
            vault = app_config / "local-vault"
            legacy = base / "legacy" / "vault"
            legacy.mkdir(parents=True)
            options = {
                "storage_mode": "Local - default",
                "vault_path": str(base / "share" / "personal"),
                "enable_livesync": True,
            }

            expected = ("Local - default", vault, False)
            self.assertEqual(select_storage(options, legacy, app_config=app_config), expected)
            self.assertFalse(vault.exists())

            self.assertEqual(select_storage(options, legacy, app_config=app_config, initialize_local=True), expected)
            self.assertEqual(list(legacy.iterdir()), [])
            welcome = vault / "Bienvenida.md"
            self.assertIn("Tu bóveda local está lista", welcome.read_text(encoding="utf-8"))
            welcome.write_text("Edited", encoding="utf-8")
            self.assertEqual(select_storage(options, legacy, app_config=app_config, initialize_local=True), expected)
            self.assertEqual(welcome.read_text(encoding="utf-8"), "Edited")

    def test_default_local_vault_rejects_symlink(self):
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            existing = base / "existing"
            existing.mkdir()
            (base / "local-vault").symlink_to(existing, target_is_directory=True)
            with self.assertRaisesRegex(ValueError, "real directory"):
                select_storage({"storage_mode": "Local - default"}, base / "vault",
                               app_config=base, initialize_local=True)
            self.assertEqual(list(existing.iterdir()), [])

    def test_fresh_livesync_uses_data_vault_and_is_disabled_until_configured(self):
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            default = base / "data" / "vault"
            mode, vault, sync = select_storage({
                "storage_mode": "livesync", "vault_path": "",
                "enable_livesync": False, "enable_tunnel": False,
            }, default, base / "share", app_config=base, initialize_local=True)
            self.assertEqual((mode, vault, sync), ("livesync", default, False))
            self.assertFalse(default.exists())
            self.assertFalse((base / "local-vault").exists())


if __name__ == "__main__":
    unittest.main()
