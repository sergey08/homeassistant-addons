import unittest
from gateway import check_message, filter_reply, validate_reply, validate_mcp_header, strict_json_loads
from tool_policy import PolicyError, load_allowed, extend_allowed, filter_tools


class GatewayTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.allowed = load_allowed()

    def test_upstream_redirect_does_not_forward_bearer_token(self):
        import urllib.error
        import urllib.request
        from gateway import NoRedirect, UPSTREAM_OPENER
        request = urllib.request.Request(
            "http://127.0.0.1:8766/",
            headers={"Authorization": "Bearer confidential-token"},
            data=b'{"jsonrpc":"2.0","id":1,"method":"ping"}',
        )
        redirect = NoRedirect()
        for code in (301, 302, 303, 307, 308):
            with self.subTest(code=code):
                self.assertIsNone(redirect.redirect_request(
                    request, None, code, "Redirect",
                    {"Location": "https://untrusted.example/collect"},
                    "https://untrusted.example/collect",
                ))
        self.assertTrue(any(isinstance(handler, NoRedirect)
                            for handler in UPSTREAM_OPENER.handlers))

    def test_initialize_requires_supported_protocol_and_client_fields(self):
        for version in ("2025-03-26", "2025-06-18"):
            self.assertEqual(check_message({
                "jsonrpc": "2.0", "id": 1, "method": "initialize",
                "params": {"protocolVersion": version, "capabilities": {},
                           "clientInfo": {"name": "test", "version": "1"}}
            }, self.allowed), "initialize")
        for params in (
            {},
            {"protocolVersion": "2024-11-05", "capabilities": {}, "clientInfo": {}},
            {"protocolVersion": "2025-06-18", "capabilities": [] , "clientInfo": {}},
            {"protocolVersion": "2025-06-18", "capabilities": {}, "clientInfo": "client"},
        ):
            with self.subTest(params=params), self.assertRaises(PolicyError):
                check_message({"jsonrpc": "2.0", "id": 1, "method": "initialize",
                               "params": params}, self.allowed)

    def test_upstream_jsonrpc_errors_are_preserved_for_mcp_client(self):
        response = {"jsonrpc": "2.0", "id": 1,
                    "error": {"code": -32603, "message": "Upstream unavailable"}}
        for method in ("initialize", "tools/list", "tools/call"):
            with self.subTest(method=method):
                self.assertEqual(filter_reply(method, response, self.allowed), response)

    def test_initialize_upstream_version_is_validated(self):
        base = {"jsonrpc": "2.0", "id": 1, "result": {
            "protocolVersion": "2025-06-18", "capabilities": {},
            "serverInfo": {"name": "fake", "version": "1"}}}
        self.assertEqual(filter_reply("initialize", base, self.allowed), base)
        for version in ("2024-11-05", None, 123):
            invalid = {"jsonrpc": "2.0", "id": 1, "result": {
                **base["result"], "protocolVersion": version}}
            with self.subTest(version=version), self.assertRaises(PolicyError):
                filter_reply("initialize", invalid, self.allowed)

    def test_initialize_rejects_invalid_server_identity(self):
        base = {"jsonrpc": "2.0", "id": 1, "result": {
            "protocolVersion": "2025-06-18", "capabilities": {},
            "serverInfo": {"name": "moonraker", "version": "1"}}}
        for info in ({}, {"name": "", "version": "1"},
                     {"name": "moonraker", "version": None},
                     {"name": 42, "version": "1"}):
            with self.subTest(info=info), self.assertRaises(PolicyError):
                filter_reply("initialize", {**base, "result": {
                    **base["result"], "serverInfo": info}}, self.allowed)
        with self.assertRaises(PolicyError):
            filter_reply("initialize", {**base, "result": {
                **base["result"], "instructions": ["invalid"]}}, self.allowed)
        valid = {**base, "result": {**base["result"], "instructions": "Read-only tools"}}
        self.assertEqual(filter_reply("initialize", valid, self.allowed), valid)

    def test_upstream_tool_call_content_validation(self):
        base = {"jsonrpc": "2.0", "id": 1}
        valid = {**base, "result": {"content": [
            {"type": "text", "text": "printer ready"}], "isError": False}}
        self.assertEqual(filter_reply("tools/call", valid, self.allowed), valid)
        for result in (
            {}, {"content": {}}, {"content": ["text"]},
            {"content": [{"type": "text", "text": None}]},
            {"content": [{"text": "missing type"}]},
            {"content": [{"type": "unknown", "payload": "untrusted"}]},
            {"content": [], "isError": "false"},
        ):
            with self.subTest(result=result), self.assertRaises(PolicyError):
                filter_reply("tools/call", {**base, "result": result}, self.allowed)

    def test_upstream_binary_and_resource_content_validation(self):
        base = {"jsonrpc": "2.0", "id": 1}
        valid_items = (
            {"type": "image", "data": "aGVsbG8=", "mimeType": "image/png"},
            {"type": "audio", "data": "aGVsbG8=", "mimeType": "audio/wav"},
            {"type": "resource_link", "uri": "file:///test", "name": "test"},
            {"type": "resource", "resource": {"uri": "file:///test", "text": "data"}},
        )
        for item in valid_items:
            with self.subTest(item=item):
                reply = {**base, "result": {"content": [item]}}
                self.assertEqual(filter_reply("tools/call", reply, self.allowed), reply)
        invalid_items = (
            {"type": "image", "data": 123, "mimeType": "image/png"},
            {"type": "audio", "data": "AA=="},
            {"type": "resource_link", "uri": "file:///test"},
            {"type": "resource", "resource": {"uri": "file:///test"}},
        )
        for item in invalid_items:
            with self.subTest(item=item), self.assertRaises(PolicyError):
                filter_reply("tools/call", {**base, "result": {"content": [item]}},
                             self.allowed)

    def test_visible_tool_schema_and_duplicate_names(self):
        valid = {"name": "moonraker_printer_info", "inputSchema": {"type": "object"}}
        self.assertEqual(filter_tools([valid], self.allowed), [valid])
        for invalid in (
            {"name": "moonraker_printer_info"},
            {"name": "moonraker_printer_info", "inputSchema": {}},
            {"name": "moonraker_printer_info", "inputSchema": {"type": "array"}},
            {"name": "moonraker_printer_info", "inputSchema": {"type": "object"},
             "description": 123},
        ):
            with self.subTest(tool=invalid), self.assertRaises(PolicyError):
                filter_tools([invalid], self.allowed)
        with self.assertRaises(PolicyError):
            filter_tools([valid, valid], self.allowed)

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

    def test_upstream_jsonrpc_errors_require_valid_structure(self):
        request = {"jsonrpc": "2.0", "id": 9, "method": "ping"}
        self.assertEqual(validate_reply(request, {
            "jsonrpc": "2.0", "id": 9,
            "error": {"code": -32601, "message": "Method not found"}
        })["error"]["code"], -32601)
        for error in (None, [], {}, {"code": True, "message": "invalid"},
                      {"code": "404", "message": "invalid"},
                      {"code": -32601}, {"code": -32601, "message": 5}):
            with self.subTest(error=error), self.assertRaises(PolicyError):
                validate_reply(request, {"jsonrpc": "2.0", "id": 9, "error": error})

    def test_upstream_tool_list_rejects_unknown_result_fields(self):
        response = {"jsonrpc": "2.0", "id": 9,
                    "result": {"tools": [], "extra": "unexpected"}}
        with self.assertRaises(PolicyError):
            filter_reply("tools/list", response, self.allowed)

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
            ("tools/list", {"cursor": 123}, True),
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

    def test_klipper_objects_require_explicit_opt_in(self):
        names = ("moonraker_objects_list", "moonraker_objects_query")
        enabled = extend_allowed(self.allowed, ["objects"])
        for name in names:
            message = {"jsonrpc": "2.0", "id": 1, "method": "tools/call",
                       "params": {"name": name, "arguments": {}}}
            with self.subTest(name=name), self.assertRaises(PolicyError):
                check_message(message, self.allowed)
            self.assertEqual(check_message(message, enabled), "tools/call")

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
            {"name": "moonraker_printer_info", "inputSchema": {"type": "object"}},
            {"name": "moonraker_print_start", "inputSchema": {"type": "object"}},
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
            [{"name": "moonraker_printer_info", "inputSchema": {"type": "object"}}, {"name": "moonraker_printer_info", "inputSchema": {"type": "object"}}],
            [{"name": "moonraker_printer_info", "inputSchema": {"type": "object"}}, {"name": "moonraker_gcode_script", "inputSchema": {"type": "object"}},
             {"name": "moonraker_gcode_script", "inputSchema": {"type": "object"}}],
            [{"name": "moonraker_printer_info", "inputSchema": {"type": "object"}}, {"description": "no name"}],
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
        self.assertEqual(len(self.allowed), 5)
        for name in excluded:
            with self.subTest(name=name), self.assertRaises(PolicyError):
                check_message({"jsonrpc": "2.0", "id": 1, "method": "tools/call",
                               "params": {"name": name, "arguments": {}}},
                              self.allowed)
        listed = [{"name": name} for name in excluded]
        self.assertEqual(filter_reply(
            "tools/list", {"result": {"tools": listed}}, self.allowed
        )["result"]["tools"], [])

    def test_optional_profiles_require_explicit_opt_in(self):
        self.assertEqual(len(self.allowed), 5)
        self.assertEqual(extend_allowed(self.allowed, []), self.allowed)
        history = extend_allowed(self.allowed, ["history"])
        self.assertEqual(len(history), 8)
        self.assertIn("moonraker_history_job", history)
        self.assertNotIn("moonraker_spoolman_status", history)
        all_profiles = extend_allowed(
            self.allowed, ["history", "sensors", "spoolman", "power"])
        self.assertEqual(len(all_profiles), 14)
        self.assertEqual(len(extend_allowed(self.allowed, ["objects", "history", "sensors", "spoolman", "power"])), 16)
        for invalid in (["admin"], ["history", "admin"], "history", [None]):
            with self.subTest(invalid=invalid), self.assertRaises(PolicyError):
                extend_allowed(self.allowed, invalid)

    def test_session_header_validation(self):
        self.assertEqual(validate_mcp_header("session_123-abc.def"), "session_123-abc.def")
        self.assertEqual(validate_mcp_header("2025-06-18"), "2025-06-18")
        for invalid in ("", "a" * 129, "line\r\nInjected: yes",
                        "has space", "semi;colon", "\\u2603", None):
            with self.subTest(value=invalid), self.assertRaises(PolicyError):
                validate_mcp_header(invalid)

    def test_strict_json_rejects_duplicate_fields_and_nonfinite_values(self):
        for payload in (
            '{"jsonrpc":"2.0","jsonrpc":"1.0","id":1}',
            '{"params":{"name":"safe","name":"unsafe"}}',
            '{"value":NaN}', '{"value":Infinity}', '{"value":-Infinity}',
        ):
            with self.subTest(payload=payload), self.assertRaises(PolicyError):
                strict_json_loads(payload)
        self.assertEqual(strict_json_loads('{"id":1,"params":{"ok":true}}'),
                         {"id":1,"params":{"ok":True}})

    def test_upstream_cannot_impersonate_local_file_tools(self):
        for name in ("moonraker_files_list", "moonraker_files_metadata",
                     "moonraker_files_preview"):
            with self.subTest(name=name):
                response = {"result": {"tools": [{"name": name, "description": "upstream"}]}}
                disabled = filter_reply("tools/list", response, self.allowed)
                self.assertEqual(disabled["result"]["tools"], [])
                enabled = filter_reply("tools/list", response,
                                       extend_allowed(self.allowed, ["files"]))
                names = [tool["name"] for tool in enabled["result"]["tools"]]
                self.assertEqual(names.count(name), 1)
                self.assertNotIn("upstream", [tool.get("description") for tool in enabled["result"]["tools"]])

    def test_pagination_preserves_cursor_and_filters_every_page(self):
        response = {"result": {"tools": [{"name": "moonraker_printer_info", "inputSchema": {"type": "object"}},
                                          {"name": "moonraker_gcode_script", "inputSchema": {"type": "object"}}],
                               "nextCursor": "page-2"}}
        filtered = filter_reply("tools/list", response, self.allowed)
        self.assertEqual(filtered["result"]["nextCursor"], "page-2")
        self.assertEqual([tool["name"] for tool in filtered["result"]["tools"]],
                         ["moonraker_printer_info"])
        enabled = extend_allowed(self.allowed, ["files"])
        first = filter_reply("tools/list", response, enabled)
        later = filter_reply("tools/list", response, enabled, cursor="page-2")
        self.assertEqual(len(first["result"]["tools"]), 4)
        self.assertEqual(len(later["result"]["tools"]), 1)
        for cursor in ("", 3, "a" * 513):
            with self.subTest(cursor=cursor), self.assertRaises(PolicyError):
                check_message({"jsonrpc": "2.0", "id": 1, "method": "tools/list",
                               "params": {"cursor": cursor}}, self.allowed)
        for cursor in ("", 3, "a" * 513):
            with self.subTest(nextCursor=cursor), self.assertRaises(PolicyError):
                filter_reply("tools/list", {"result": {"tools": [], "nextCursor": cursor}},
                             self.allowed)


if __name__ == "__main__":
    unittest.main()
