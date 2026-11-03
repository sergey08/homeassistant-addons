import unittest
from gateway import check_message, filter_reply, validate_reply
from tool_policy import PolicyError, load_allowed


class GatewayTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.allowed = load_allowed()

    def test_upstream_reply_validation(self):
        request = {"jsonrpc": "2.0", "id": 9, "method": "ping"}
        valid = {"jsonrpc": "2.0", "id": 9, "result": {}}
        self.assertEqual(validate_reply(request, valid), valid)
        for invalid in (
            [{"jsonrpc": "2.0", "id": 9, "result": {}}],
            {"jsonrpc": "2.0", "id": 8, "result": {}},
            {"jsonrpc": "2.0", "id": 9.0, "result": {}},
            {"jsonrpc": "2.0", "id": 9, "result": {}, "extra": "unexpected"},
            {"jsonrpc": "1.0", "id": 9, "result": {}},
            {"jsonrpc": "2.0", "id": 9, "result": {}, "error": {}},
            {"jsonrpc": "2.0", "id": 9},
        ):
            with self.subTest(invalid=invalid), self.assertRaises(PolicyError):
                validate_reply(request, invalid)

    def test_notification_and_request_ids(self):
        self.assertEqual(
            check_message({"jsonrpc": "2.0", "method": "notifications/initialized"},
                          self.allowed),
            "notifications/initialized",
        )
        for message in (
            {"jsonrpc": "2.0", "id": 1, "method": "notifications/initialized"},
            {"jsonrpc": "2.0", "method": "tools/list"},
            {"jsonrpc": "2.0", "id": 1, "method": "ping", "params": []},
        ):
            with self.subTest(message=message), self.assertRaises(PolicyError):
                check_message(message, self.allowed)

    def test_unexpected_method_params_blocked(self):
        for method, params, has_id in (
            ("ping", {"command": "restart"}, True),
            ("tools/list", {"cursor": "unexpected"}, True),
            ("notifications/initialized", {"command": "restart"}, False),
        ):
            message = {"jsonrpc": "2.0", "method": method, "params": params}
            if has_id:
                message["id"] = 1
            with self.subTest(method=method), self.assertRaises(PolicyError):
                check_message(message, self.allowed)

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

    def test_malformed_arguments_blocked(self):
        for arguments in (None, "M112", ["M112"], 123):
            with self.subTest(arguments=arguments):
                with self.assertRaises(PolicyError):
                    check_message({"jsonrpc": "2.0", "id": 1, "method": "tools/call",
                                   "params": {"name": "moonraker_printer_info",
                                              "arguments": arguments}}, self.allowed)

    def test_extra_fields_blocked(self):
        for request in (
            {"jsonrpc": "2.0", "id": 1, "method": "tools/list", "unexpected": True},
            {"jsonrpc": "2.0", "id": True, "method": "tools/list"},
            {"jsonrpc": "2.0", "id": 1, "method": "tools/call",
             "params": {"name": "moonraker_printer_info", "arguments": {},
                        "extra": "ignored"}},
        ):
            with self.subTest(request=request):
                with self.assertRaises(PolicyError):
                    check_message(request, self.allowed)

    def test_oversized_tool_arguments_blocked(self):
        with self.assertRaises(PolicyError):
            check_message({"jsonrpc": "2.0", "id": 1, "method": "tools/call",
                           "params": {"name": "moonraker_objects_query",
                                      "arguments": {"objects": {"x": ["a" * 17000]}}}},
                          self.allowed)

    def test_duplicate_and_malformed_upstream_tools_rejected(self):
        from tool_policy import filter_tools
        for tools in (
            [{"name": "moonraker_printer_info"}, {"name": "moonraker_printer_info"}],
            [{"name": "moonraker_printer_info"}, {"name": "moonraker_gcode_script"},
             {"name": "moonraker_gcode_script"}],
            [{"name": "moonraker_printer_info"}, {"description": "no name"}],
        ):
            with self.subTest(tools=tools), self.assertRaises(PolicyError):
                filter_tools(tools, self.allowed)

    def test_privacy_sensitive_tools_disabled_by_default(self):
        excluded = (
            "moonraker_history_list", "moonraker_history_job",
            "moonraker_history_totals", "moonraker_power_status",
            "moonraker_sensors_info", "moonraker_sensors_list",
            "moonraker_sensors_measurements", "moonraker_spoolman_status",
            "moonraker_spoolman_get_spool",
        )
        self.assertEqual(len(self.allowed), 7)
        for name in excluded:
            with self.subTest(name=name), self.assertRaises(PolicyError):
                check_message({"jsonrpc": "2.0", "id": 1, "method": "tools/call",
                               "params": {"name": name, "arguments": {}}},
                              self.allowed)
        listed = [{"name": name} for name in excluded]
        self.assertEqual(filter_reply(
            "tools/list", {"result": {"tools": listed}}, self.allowed
        )["result"]["tools"], [])

    def test_pagination_rejected(self):
        with self.assertRaises(PolicyError):
            filter_reply("tools/list", {"result": {"tools": [], "nextCursor": "x"}},
                         self.allowed)


if __name__ == "__main__":
    unittest.main()
