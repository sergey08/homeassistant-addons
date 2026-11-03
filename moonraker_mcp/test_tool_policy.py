import importlib.util
import json
import pathlib
import unittest

BASE = pathlib.Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("tool_policy", BASE / "tool_policy.py")
policy = importlib.util.module_from_spec(spec)
spec.loader.exec_module(policy)


class ToolPolicyTests(unittest.TestCase):
    def setUp(self):
        self.allowed = policy.load_allowed()

    def test_allows_safe_status(self):
        self.assertTrue(policy.authorize_call("moonraker_printer_info", self.allowed))

    def test_blocks_control_even_when_admin_disabled(self):
        for name in (
            "moonraker_gcode_script", "moonraker_print_start",
            "moonraker_print_cancel", "moonraker_firmware_restart",
            "moonraker_emergency_stop", "moonraker_power_on",
            "moonraker_files_delete", "moonraker_spoolman_set_spool",
        ):
            with self.subTest(name=name):
                with self.assertRaises(policy.PolicyError):
                    policy.authorize_call(name, self.allowed)

    def test_blocks_unknown_future_tool(self):
        with self.assertRaises(policy.PolicyError):
            policy.authorize_call("moonraker_new_future_tool", self.allowed)

    def test_rejects_non_string_and_empty_names(self):
        for name in (None, "", 123, {}, []):
            with self.assertRaises(policy.PolicyError):
                policy.authorize_call(name, self.allowed)

    def test_filters_listing(self):
        tools = [
            {"name": "moonraker_printer_info", "inputSchema": {}},
            {"name": "moonraker_gcode_script", "inputSchema": {}},
            {"name": "moonraker_new_future_tool", "inputSchema": {}},
        ]
        self.assertEqual(
            [t["name"] for t in policy.filter_tools(tools, self.allowed)],
            ["moonraker_printer_info"],
        )

    def test_malformed_listing_rejected(self):
        with self.assertRaises(policy.PolicyError):
            policy.filter_tools(None, self.allowed)


if __name__ == "__main__":
    unittest.main()
