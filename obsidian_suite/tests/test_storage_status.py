import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from onboarding import collect_status, render_page


class StorageStatusTests(unittest.TestCase):
    def test_legacy_path_is_reported_without_note_contents(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            data, legacy = root / "data", root / "app_configs"
            data.mkdir()
            vault = legacy / "vault"
            vault.mkdir(parents=True)
            (vault / "private.md").write_text("do not expose this text")
            (data / "options.json").write_text(json.dumps({
                "storage_mode": "livesync", "enable_livesync": True
            }))
            status = collect_status(data=data, legacy=legacy)
            self.assertEqual(status["vault_location"], str(vault))
            self.assertEqual(status["vault_origin"], "legacy app config")
            html = render_page(status)
            self.assertIn(str(vault), html)
            self.assertNotIn("do not expose this text", html)

    def test_private_default_is_reported(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            data = root / "data"
            data.mkdir()
            status = collect_status(data=data, legacy=root / "no_legacy")
            self.assertEqual(status["vault_origin"], "add-on private data")
            self.assertEqual(status["vault_location"], str(data / "vault"))

    def test_default_local_folder_is_reported_without_creating_it(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            data, legacy = root / "data", root / "app_configs"
            data.mkdir()
            config = root / "config"
            config.mkdir()
            (legacy / "vault").mkdir(parents=True)
            (data / "options.json").write_text(json.dumps({
                "storage_mode": "Local - default", "enable_livesync": True
            }))
            status = collect_status(data=data, legacy=legacy, app_config=config)
            self.assertEqual(status["vault_origin"], "app public configuration")
            self.assertEqual(status["vault_location"], str(config / "local-vault"))
            self.assertFalse(status["sync_enabled"])
            self.assertFalse((config / "local-vault").exists())

    def test_bad_config_does_not_claim_selected_vault(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            data = root / "data"
            data.mkdir()
            (data / "options.json").write_text(json.dumps({"storage_mode": "invalid"}))
            status = collect_status(data=data, legacy=root / "legacy")
            self.assertEqual(status["vault_location"], "not available")
            self.assertFalse(status["vault"])


if __name__ == "__main__":
    unittest.main()
