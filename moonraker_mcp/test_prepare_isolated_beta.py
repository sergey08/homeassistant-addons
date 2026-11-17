"""Offline beta build-context isolation tests."""
import tempfile
import unittest
from pathlib import Path
from prepare_isolated_beta import prepare, BETA_SLUG

class BetaIsolationTests(unittest.TestCase):
    def test_creates_separate_beta_without_mutating_stable(self):
        source = Path(__file__).resolve().parent
        before = (source / "config.yaml").read_bytes()
        with tempfile.TemporaryDirectory() as temp:
            target = Path(temp) / BETA_SLUG
            prepare(target)
            beta = (target / "config.yaml").read_text()
            self.assertIn('slug: "' + BETA_SLUG + '"', beta)
            self.assertIn('version: "0.1.5-beta.1"', beta)
            self.assertIn('  enable_write_actions: false', beta)
            self.assertIn('  allow_gcode_upload: false', beta)
            self.assertIn('  allow_print_start: false', beta)
            self.assertIn('  enable_tunnel: false', beta)
            self.assertTrue((target / "Dockerfile").exists())
            self.assertTrue((target / "staging_housekeeper.py").exists())
            self.assertEqual((source / "config.yaml").read_bytes(), before)
            with self.assertRaises(FileExistsError):
                prepare(target)

    def test_rejects_wrong_directory_name(self):
        with tempfile.TemporaryDirectory() as temp:
            with self.assertRaises(ValueError):
                prepare(Path(temp) / "moonraker_mcp")

if __name__ == "__main__":
    unittest.main()
