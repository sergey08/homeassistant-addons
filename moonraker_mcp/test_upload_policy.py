"""Offline permission regression tests; no printer or Home Assistant access."""
import unittest
from pathlib import Path
from tool_policy import OPTIONAL_PROFILES, PolicyError, authorize_call, extend_allowed

HERE = Path(__file__).resolve().parent
UPLOAD = "moonraker_safe_gcode_upload"

class UploadPolicyTests(unittest.TestCase):
    def test_upload_is_not_in_read_only_default(self):
        from tool_policy import load_allowed
        self.assertNotIn(UPLOAD, load_allowed())

    def test_upload_requires_explicit_profile(self):
        self.assertNotIn(UPLOAD, extend_allowed(frozenset(), []))
        self.assertIn(UPLOAD, extend_allowed(frozenset(), ["gcode_upload"]))
        with self.assertRaises(PolicyError):
            authorize_call(UPLOAD, extend_allowed(frozenset(), []))

    def test_upload_local_tool_schema(self):
        from gateway import LOCAL_FILE_TOOLS, LOCAL_PRINT_WRITE_TOOLS, RESERVED_UPLOAD_TOOL, LOCAL_UPLOAD_DEFINITION, check_message
        self.assertEqual(RESERVED_UPLOAD_TOOL, UPLOAD)
        self.assertNotIn(UPLOAD, LOCAL_FILE_TOOLS)
        self.assertNotIn(UPLOAD, LOCAL_PRINT_WRITE_TOOLS)
        self.assertEqual(LOCAL_UPLOAD_DEFINITION['inputSchema']['required'], ['filename', 'sha256', 'confirmation'])

    def test_upload_defaults_off_and_requires_master_write_gate(self):
        config = (HERE / "config.yaml").read_text()
        runtime = (HERE / "run.sh").read_text()
        self.assertIn("  allow_gcode_upload: false", config)
        self.assertIn("  allow_gcode_upload: bool", config)
        self.assertIn('["gcode_upload", .allow_gcode_upload]', runtime)
        self.assertIn('.[0] != "gcode_upload"', runtime)
        self.assertIn('$master or', runtime)

if __name__ == "__main__":
    unittest.main()
