"""Independent LiveSync preflight must not invoke sync or leak secrets."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from client_sync_engine import preflight
from server import app


class IndependentPreflightTests(unittest.TestCase):
    def test_storage_overlap_blocks_without_side_effects(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            cfg = {"editor_storage_mode": "livesync"}
            status = preflight(cfg, vault=root/"vault", database=root/"vault"/"db",
                               mcp_vault=root/"remote", cli=root/"missing")
            self.assertFalse(status["independent_of_mcp"])
            self.assertFalse(status["eligible_for_isolated_sync_test"])
            self.assertIn("storage_not_isolated", status["blocking_reasons"])
            self.assertFalse((root/"vault").exists())

    def test_mcp_vault_cannot_be_own_vault(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            status = preflight({"editor_storage_mode": "livesync"},
                               vault=root/"shared", database=root/"db",
                               mcp_vault=root/"shared", cli=root/"missing")
            self.assertFalse(status["independent_of_mcp"])

    def test_readiness_has_no_mutation_and_no_credentials(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            db = root/"db"
            (db/".livesync").mkdir(parents=True)
            (db/".livesync"/"settings.json").write_text('{"password":"secret"}')
            cli = root/"index.cjs"
            cli.write_text("pinned")
            cfg={"editor_storage_mode": "livesync", "couchdb_password": "secret"}
            with patch("livesync_cli_bridge.validate_remote_configuration",
                       return_value={"configuration_complete": True}):
                out = preflight(cfg, vault=root/"vault", database=db,
                                mcp_vault=root/"mcp", cli=cli)
            self.assertTrue(out["eligible_for_isolated_sync_test"])
            self.assertFalse(out["sync_active"])
            self.assertFalse(out["remote_writes_enabled"])
            self.assertNotIn("secret", json.dumps(out))
            self.assertFalse((root/"vault").exists())

    def test_http_preflight_reports_current_shared_compat_mode_as_blocked(self):
        with patch("server.options", return_value={"editor_storage_mode": "mcp_shared"}):
            result = app.test_client().get("/api/livesync-cli/independent-preflight")
        self.assertEqual(result.status_code, 200)
        self.assertIn("independent_mode_not_selected", result.json["blocking_reasons"])
        self.assertFalse(result.json["sync_active"])
        self.assertEqual(result.headers["Cache-Control"], "no-store")


if __name__ == "__main__":
    unittest.main()
