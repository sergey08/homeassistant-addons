"""Mode switching must never move or modify real vault notes."""
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from vault_selection import select_storage


class ModeSwitchTests(unittest.TestCase):
    def test_switching_storage_is_non_destructive(self):
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            share = base / "share"
            local = share / "notes"
            local.mkdir(parents=True)
            real = base / "legacy" / "vault"
            real.mkdir(parents=True)
            real_note = real / "real.md"
            local_note = local / "local.md"
            real_note.write_text("Real LiveSync note", encoding="utf-8")
            local_note.write_text("Local Markdown note", encoding="utf-8")
            mode, vault, sync = select_storage(
                {"enable_livesync": True}, real, share)
            self.assertEqual((mode, vault, sync), ("livesync", real, True))
            mode, vault, sync = select_storage(
                {"storage_mode": "local", "vault_path": str(local), "enable_livesync": True}, real, share)
            self.assertEqual((mode, vault, sync), ("local", local.resolve(), False))
            self.assertEqual(real_note.read_text(), "Real LiveSync note")
            self.assertEqual(local_note.read_text(), "Local Markdown note")
            mode, vault, sync = select_storage(
                {"storage_mode": "livesync", "vault_path": str(local), "enable_livesync": True}, real, share)
            self.assertEqual((mode, vault, sync), ("livesync", real, True))
            self.assertEqual(real_note.read_text(), "Real LiveSync note")
            self.assertEqual(local_note.read_text(), "Local Markdown note")

if __name__ == "__main__":
    unittest.main()
