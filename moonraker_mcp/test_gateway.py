import unittest
from gateway import check_message, filter_reply
from tool_policy import PolicyError, load_allowed


class GatewayTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.allowed = load_allowed()

    def test_status_call_allowed(self):
        self.assertEqual(
            check_message({"jsonrpc": "2.0", "id": 1, "method": "tools/call",
                           "params": {"name": "moonraker_printer_info", "arguments": {}}},
                          self.allowed),
            "tools/call",
        )

    def test_gcode_blocked(self):
        with self.assertRaises(PolicyError):
            check_message({"jsonrpc": "2.0", "id": 2, "method": "tools/call",
                           "params": {"name": "moonraker_gcode_script",
                                      "arguments": {"script": "M112"}}}, self.allowed)

    def test_unknown_methods_blocked(self):
        for method in ("resources/read", "prompts/get", "completion/complete", "custom/admin"):
            with self.subTest(method=method):
                with self.assertRaises(PolicyError):
                    check_message({"jsonrpc": "2.0", "method": method}, self.allowed)

    def test_batches_blocked(self):
        with self.assertRaises(PolicyError):
            check_message([{"jsonrpc": "2.0", "method": "tools/list"}], self.allowed)

    def test_filter_listing(self):
        response = {"jsonrpc": "2.0", "id": 3, "result": {"tools": [
            {"name": "moonraker_printer_info"},
            {"name": "moonraker_print_start"},
        ]}}
        result = filter_reply("tools/list", response, self.allowed)
        self.assertEqual([x["name"] for x in result["result"]["tools"]],
                         ["moonraker_printer_info"])

    def test_pagination_rejected(self):
        with self.assertRaises(PolicyError):
            filter_reply("tools/list", {"result": {"tools": [], "nextCursor": "x"}},
                         self.allowed)


if __name__ == "__main__":
    unittest.main()
