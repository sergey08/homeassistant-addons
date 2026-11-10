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

    def test_job_queue_requires_explicit_opt_in(self):
        with self.assertRaises(policy.PolicyError):
            policy.authorize_call("moonraker_jobqueue_status", self.allowed)
        opted_in = policy.extend_allowed(self.allowed, ["jobqueue"])
        self.assertTrue(policy.authorize_call("moonraker_jobqueue_status", opted_in))
        self.assertEqual(len(opted_in), len(self.allowed) + 1)

    def test_spoolman_inventory_requires_opt_in_and_remains_read_only(self):
        with self.assertRaises(policy.PolicyError):
            policy.authorize_call("moonraker_spoolman_inventory", self.allowed)
        allowed = policy.extend_allowed(self.allowed, ["spoolman"])
        self.assertTrue(policy.authorize_call("moonraker_spoolman_inventory", allowed))
        self.assertFalse("moonraker_spoolman_set_spool" in allowed)
        self.assertFalse("moonraker_spoolman_proxy" in allowed)

    def test_u1_status_is_explicitly_opt_in_and_read_only(self):
        for name in ("moonraker_print_snapshot", "moonraker_filament_slots"):
            with self.assertRaises(policy.PolicyError):
                policy.authorize_call(name, self.allowed)
        opted_in = policy.extend_allowed(self.allowed, ["u1_status"])
        self.assertEqual(len(opted_in), len(self.allowed) + 2)
        for name in ("moonraker_print_snapshot", "moonraker_filament_slots"):
            self.assertTrue(policy.authorize_call(name, opted_in))
        for name in ("moonraker_print_start", "moonraker_print_cancel",
                     "moonraker_gcode_script", "moonraker_power_on"):
            self.assertNotIn(name, opted_in)

    def test_each_print_write_tool_requires_individual_opt_in(self):
        mappings = {
            "print_pause": "moonraker_safe_print_pause",
            "print_resume": "moonraker_safe_print_resume",
            "print_cancel": "moonraker_safe_print_cancel",
            "print_start": "moonraker_safe_print_start",
        }
        for profile, tool in mappings.items():
            with self.subTest(profile=profile):
                selected = policy.extend_allowed(self.allowed, [profile])
                self.assertIn(tool, selected)
                for other in set(mappings.values()) - {tool}:
                    self.assertNotIn(other, selected)
                self.assertNotIn("moonraker_gcode_script", selected)
                self.assertNotIn("moonraker_power_on", selected)

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
            {"name": "moonraker_printer_info", "inputSchema": {"type": "object"}},
            {"name": "moonraker_gcode_script", "inputSchema": {"type": "object"}},
            {"name": "moonraker_new_future_tool", "inputSchema": {"type": "object"}},
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
