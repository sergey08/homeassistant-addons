import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from shared_vault_preflight import compare, snapshot


class SharedVaultPreflightTests(unittest.TestCase):
    def test_identical_vaults_include_hidden_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            src, dst = Path(tmp) / "source", Path(tmp) / "destination"
            for folder in (src, dst):
                (folder / "nested").mkdir(parents=True)
                (folder / "nested" / "n.md").write_text("hello", encoding="utf-8")
                (folder / ".obsidian").mkdir()
                (folder / ".obsidian" / "app.json").write_text("{}", encoding="utf-8")
            report = compare(src, dst)
            self.assertEqual(report["status"], "identical")
            self.assertEqual(report["source_files"], 2)
            self.assertEqual(report["markdown_files"], 1)

    def test_missing_modified_extra_detected(self):
        with tempfile.TemporaryDirectory() as tmp:
            src, dst = Path(tmp) / "source", Path(tmp) / "destination"
            src.mkdir()
            dst.mkdir()
            (src / "note.md").write_text("correct")
            (dst / "note.md").write_text("wrong")
            (src / "missing.md").write_text("missing")
            (dst / "extra.md").write_text("extra")
            report = compare(src, dst)
            self.assertEqual(report["status"], "different")
            self.assertEqual(report["missing"], ["missing.md"])
            self.assertEqual(report["unexpected"], ["extra.md"])
            self.assertEqual(report["different_content"], ["note.md"])

    def test_symlink_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            src = Path(tmp) / "vault"
            src.mkdir()
            (src / "link.md").symlink_to(Path(tmp) / "elsewhere")
            with self.assertRaisesRegex(ValueError, "Symlink"):
                snapshot(src)


if __name__ == "__main__":
    unittest.main()
