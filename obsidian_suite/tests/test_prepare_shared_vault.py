import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from prepare_shared_vault import prepare


class SafeBackupCopyTests(unittest.TestCase):
    def test_dry_run_does_not_write_anything(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            src, backup, shared = (root / n for n in ("source", "backup", "shared"))
            src.mkdir()
            (src / "note.md").write_text("# original")
            report = prepare(src, backup, shared)
            self.assertEqual(report["mode"], "dry_run")
            self.assertFalse(backup.exists())
            self.assertFalse(shared.exists())

    def test_verified_copies_include_hidden_files(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            src, backup, shared = (root / n for n in ("source", "backup", "shared"))
            (src / ".obsidian").mkdir(parents=True)
            (src / "note.md").write_text("# original")
            (src / ".obsidian" / "app.json").write_text('{"x":1}')
            report = prepare(src, backup, shared, execute=True)
            self.assertEqual(report["status"], "verified")
            self.assertEqual((backup / "note.md").read_text(), "# original")
            self.assertEqual((shared / ".obsidian" / "app.json").read_text(), '{"x":1}')
            self.assertEqual((src / "note.md").read_text(), "# original")

    def test_existing_destination_is_not_overwritten(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            src, backup, shared = (root / n for n in ("source", "backup", "shared"))
            src.mkdir()
            (src / "note.md").write_text("original")
            backup.mkdir()
            (backup / "keep").write_text("existing")
            with self.assertRaisesRegex(ValueError, "must not already exist"):
                prepare(src, backup, shared, execute=True)
            self.assertEqual((backup / "keep").read_text(), "existing")
            self.assertFalse(shared.exists())

    def test_nested_paths_and_symlinks_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            src = root / "source"
            src.mkdir()
            (src / "note.md").write_text("content")
            with self.assertRaisesRegex(ValueError, "contain"):
                prepare(src, src / "nested", root / "shared")
            (src / "linked.md").symlink_to(src / "note.md")
            with self.assertRaisesRegex(ValueError, "Symlink"):
                prepare(src, root / "backup", root / "shared")


if __name__ == "__main__":
    unittest.main()
