"""Regression tests for Obsidian Client's independent storage-mode contract."""
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from storage_selection import select_storage, StorageSelectionError


class StorageModesTests(unittest.TestCase):
    def test_legacy_private_and_new_local_preserve_existing_vault(self):
        for mode in ("private", "local"):
            state = select_storage({"editor_storage_mode": mode})
            self.assertEqual(state["mode"], "local")
            self.assertEqual(state["vault"], "/data/obsidian-client-markdown")
            self.assertTrue(state["independent_of_mcp"])
            self.assertEqual(state["sync_engine"], "disabled")

    def test_livesync_mode_has_private_vault_and_database_but_is_not_ready(self):
        state = select_storage({"editor_storage_mode": "livesync"})
        self.assertEqual(state["vault"], "/data/obsidian-client-livesync-vault")
        self.assertEqual(state["database"], "/data/livesync-client")
        self.assertNotEqual(state["vault"], state["database"])
        self.assertEqual(state["sync_engine"], "not_implemented")
        self.assertFalse(state["remote_synced"])
        self.assertTrue(state["independent_of_mcp"])

    def test_shared_compatibility_mode_requires_existing_directory(self):
        with tempfile.TemporaryDirectory() as root:
            vault = Path(root) / "shared"
            vault.mkdir()
            state = select_storage({"editor_storage_mode": "mcp_shared"}, shared_vault=vault)
            self.assertFalse(state["independent_of_mcp"])
            self.assertEqual(state["sync_engine"], "external_mcp")
            with self.assertRaisesRegex(StorageSelectionError, "unavailable"):
                select_storage({"editor_storage_mode": "mcp_shared"}, shared_vault=Path(root) / "missing")

    def test_invalid_mode_and_overlapping_database_are_rejected(self):
        with self.assertRaisesRegex(StorageSelectionError, "unsupported"):
            select_storage({"editor_storage_mode": "unsupported"})
        with self.assertRaisesRegex(StorageSelectionError, "overlap"):
            select_storage({"editor_storage_mode": "livesync"},
                           livesync_vault="/tmp/same", livesync_database="/tmp/same")


if __name__ == "__main__":
    unittest.main()
