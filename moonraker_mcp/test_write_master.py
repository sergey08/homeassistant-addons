"""Exercise the actual run.sh jq authorization filter with synthetic options.

No printer connection is made.
"""
import json
import pathlib
import re
import shutil
import subprocess
import tempfile
import unittest

BASE = pathlib.Path(__file__).resolve().parent
SCRIPT = (BASE / "run.sh").read_text(encoding="utf-8")
MATCH = re.search(
    r'MCP_ALLOWED_PROFILES="\$\(jq -ecr --argjson master "\$MCP_WRITE_ENABLED" \'([^\']+)\' "\$OPTIONS"\)"',
    SCRIPT,
)
MASTER_MATCH = re.search(
    r'MCP_WRITE_ENABLED="\$\(jq -er \'([^\']+)\' "\$OPTIONS"\)"',
    SCRIPT,
)

@unittest.skipUnless(shutil.which("jq"), "jq not installed in this environment")
class WriteMasterTests(unittest.TestCase):
    def test_filters_are_present(self):
        self.assertIsNotNone(MATCH)
        self.assertIsNotNone(MASTER_MATCH)

    def apply(self, options):
        with tempfile.TemporaryDirectory() as directory:
            path = pathlib.Path(directory) / "options.json"
            path.write_text(json.dumps(options), encoding="utf-8")
            master = subprocess.run(
                ["jq", "-er", MASTER_MATCH.group(1), str(path)],
                text=True, capture_output=True,
            )
            if master.returncode:
                return master, None
            profiles = subprocess.run(
                ["jq", "-ecr", "--argjson", "master", master.stdout.strip(),
                 MATCH.group(1), str(path)],
                text=True, capture_output=True,
            )
            if profiles.returncode:
                return master, profiles
            return master, json.loads(profiles.stdout)

    def test_all_individual_flags_on_master_off_still_read_only(self):
        _, profiles = self.apply({
            "enable_write_actions": False,
            "allow_print_pause": True, "allow_print_resume": True,
            "allow_print_cancel": True, "allow_print_start": True,
            "enable_u1_status": True, "enable_spoolman": True,
        })
        self.assertEqual(profiles, ["spoolman", "u1_status"])

    def test_independent_write_flags_require_master(self):
        _, profiles = self.apply({
            "enable_write_actions": True,
            "allow_print_pause": True, "allow_print_resume": False,
            "allow_print_cancel": False, "allow_print_start": False,
        })
        self.assertEqual(profiles, ["print_pause"])

    def test_missing_master_defaults_to_off(self):
        _, profiles = self.apply({"allow_print_start": True})
        self.assertEqual(profiles, [])

    def test_invalid_master_type_rejected(self):
        master, profiles = self.apply({"enable_write_actions": "true", "allow_print_start": True})
        self.assertNotEqual(master.returncode, 0)
        self.assertIsNone(profiles)

    def test_invalid_individual_type_rejected(self):
        master, profiles = self.apply({"enable_write_actions": True, "allow_print_start": "true"})
        self.assertEqual(master.returncode, 0)
        self.assertNotEqual(profiles.returncode, 0)

if __name__ == "__main__":
    unittest.main()
