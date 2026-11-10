"""Opt-in MCP file tools tests; no printer required."""
import unittest
from unittest.mock import patch
from gateway import LOCAL_FILE_TOOLS, check_message, filter_reply
from tool_policy import PolicyError, extend_allowed, load_allowed


class FileToolPolicyTests(unittest.TestCase):
    def setUp(self):
        self.base = load_allowed()

    def test_files_are_not_enabled_by_default(self):
        for name in LOCAL_FILE_TOOLS:
            with self.assertRaises(PolicyError):
                check_message({"jsonrpc": "2.0", "id": 1, "method": "tools/call",
                               "params": {"name": name, "arguments": {}}}, self.base)

    def test_files_opt_in_exposes_three_tools(self):
        allowed = extend_allowed(self.base, ["files"])
        reply = filter_reply("tools/list", {"jsonrpc": "2.0", "id": 1,
                            "result": {"tools": []}}, allowed)
        self.assertEqual({x["name"] for x in reply["result"]["tools"]}, set(LOCAL_FILE_TOOLS) | {"moonraker_connection_status"})
        for name in LOCAL_FILE_TOOLS:
            arguments = {} if name == "moonraker_files_list" else {"filename": "test.gcode"}
            self.assertEqual(check_message({"jsonrpc": "2.0", "id": 1, "method": "tools/call",
                             "params": {"name": name, "arguments": arguments}}, allowed), "tools/call")

    def test_file_arguments_are_strictly_validated(self):
        allowed = extend_allowed(self.base, ["files"])
        invalid = (
            ("moonraker_files_list", {"filename": "x.gcode"}),
            ("moonraker_files_metadata", {}),
            ("moonraker_files_metadata", {"filename": 42}),
            ("moonraker_files_preview", {"filename": None}),
            ("moonraker_files_preview", {"filename": "x.gcode", "root": "config"}),
        )
        for name, arguments in invalid:
            with self.subTest(name=name, arguments=arguments), self.assertRaises(PolicyError):
                check_message({"jsonrpc": "2.0", "id": 1, "method": "tools/call",
                               "params": {"name": name, "arguments": arguments}}, allowed)
        for name in ("moonraker_files_preview", "moonraker_files_metadata"):
            self.assertEqual(check_message({"jsonrpc": "2.0", "id": 1, "method": "tools/call",
                             "params": {"name": name, "arguments": {"filename": "x.gcode"}}}, allowed),
                             "tools/call")

    def test_files_profile_does_not_enable_other_profiles(self):
        allowed = extend_allowed(self.base, ["files"])
        with self.assertRaises(PolicyError):
            check_message({"jsonrpc": "2.0", "id": 1, "method": "tools/call",
                           "params": {"name": "moonraker_objects_query", "arguments": {}}}, allowed)

    def test_file_tools_have_restrictive_schemas(self):
        for tool in LOCAL_FILE_TOOLS.values():
            self.assertFalse(tool["inputSchema"]["additionalProperties"])


if __name__ == "__main__":
    unittest.main()
