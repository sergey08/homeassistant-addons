"""Fresh-install preflight must not require LiveSync or tunnel credentials in Local mode."""
import contextlib
import importlib.util
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

MOD = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("obsidian_preflight_test", MOD / "preflight.py")
preflight = importlib.util.module_from_spec(spec)
spec.loader.exec_module(preflight)


class FirstRunPreflightTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.data = self.root / "data"
        self.data.mkdir()
        self.share = self.root / "share"
        self.share.mkdir()
        self.vault = self.share / "new-markdown"
        self.vault.mkdir()

    def run_preflight(self, options):
        (self.data / "options.json").write_text(json.dumps(options), encoding="utf-8")
        output = io.StringIO()
        with patch.object(preflight, "OWNED", self.data), \
             patch.object(preflight, "LEGACY", self.root / "missing-legacy"), \
             patch.object(preflight, "BASE", self.data), \
             contextlib.redirect_stdout(output):
            preflight.main()
        return output.getvalue()

    def test_local_without_livesync_or_tunnel(self):
        result = self.run_preflight({
            "storage_mode": "local",
            "vault_path": str(self.vault),
            "enable_livesync": False,
            "enable_tunnel": False,
        })
        # Validation is against the mounted /share; the host temp path is outside it.
        # Check that the report does not falsely require network services.
        self.assertIn("[DISABLED] LiveSync", result)
        self.assertIn("[DISABLED] OpenAI tunnel", result)
        self.assertNotIn("Tunnel executable", result)
        self.assertFalse((self.data / "settings").exists())

    def test_fresh_livesync_staged_before_credentials(self):
        result = self.run_preflight({
            "storage_mode": "livesync",
            "enable_livesync": False,
            "enable_tunnel": False,
        })
        self.assertIn("[DISABLED] LiveSync", result)
        self.assertIn("[DISABLED] OpenAI tunnel", result)
        self.assertFalse((self.data / "vault").exists())

    def test_enabled_unprovisioned_livesync_reports_missing_settings(self):
        result = self.run_preflight({
            "storage_mode": "livesync",
            "enable_livesync": True,
            "enable_tunnel": False,
        })
        self.assertIn("[SETUP REQUIRED] LiveSync settings", result)
        self.assertFalse((self.data / "settings").exists())


if __name__ == "__main__":
    unittest.main()
