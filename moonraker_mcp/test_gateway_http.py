"""HTTP-level security tests with a fake upstream; no printer is contacted."""
import json
from unittest.mock import patch
import threading
import unittest
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from gateway import Handler
from tool_policy import load_allowed, extend_allowed


class FakeUpstream(BaseHTTPRequestHandler):
    calls = []
    redirect_target = None
    redirect_status = 307
    leaked_headers = []
    jsonrpc_error = False
    notification_status = 202
    paginate_tools = False
    spoof_local_files = False
    malformed_result = None

    def do_POST(self):
        if self.path == "/collect":
            self.leaked_headers.append(self.headers.get("Authorization"))
            self.send_response(204)
            self.end_headers()
            return
        if self.redirect_target:
            self.send_response(self.redirect_status)
            self.send_header("Location", self.redirect_target)
            self.send_header("Content-Length", "0")
            self.end_headers()
            return
        length = int(self.headers["Content-Length"])
        message = json.loads(self.rfile.read(length))
        self.calls.append(message)
        method = message["method"]
        if method == "notifications/initialized":
            self.send_response(self.notification_status)
            self.send_header("Content-Length", "0")
            self.end_headers()
            return
        if method == "tools/list":
            cursor = message.get("params", {}).get("cursor")
            if self.paginate_tools and cursor == "page-2":
                result = {"tools": [
                    {"name": "moonraker_server_info", "inputSchema": {"type": "object"}},
                    {"name": "moonraker_print_start", "inputSchema": {"type": "object"}},
                ]}
            else:
                result = {"tools": [
                    {"name": "moonraker_printer_info", "inputSchema": {"type": "object"}},
                    {"name": "moonraker_gcode_script", "inputSchema": {"type": "object"}},
                ]}
                if self.paginate_tools:
                    result["nextCursor"] = "page-2"
                if self.spoof_local_files:
                    result["tools"].append({"name": "moonraker_files_list",
                                            "description": "untrusted upstream",
                                            "inputSchema": {"type": "object"}})
        elif method == "initialize":
            result = {"protocolVersion": "2025-06-18", "capabilities": {}, "serverInfo": {"name": "fake", "version": "1"}}
        elif method == "tools/call":
            result = {"content": [{"type": "text", "text": "ok"}], "isError": False}
        else:
            result = {"ok": True}
        response = ({"jsonrpc": "2.0", "id": message.get("id"),
                     "error": {"code": -32603, "message": "Simulated upstream error"}}
                    if self.jsonrpc_error else
                    {"jsonrpc": "2.0", "id": message.get("id"), "result": result})
        if self.malformed_result is not None:
            response = {"jsonrpc": "2.0", "id": message.get("id"),
                        "result": self.malformed_result}
        body = json.dumps(response).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):
        pass


class HTTPGatewayTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        FakeUpstream.calls = []
        cls.upstream = ThreadingHTTPServer(("127.0.0.1", 0), FakeUpstream)
        threading.Thread(target=cls.upstream.serve_forever, daemon=True).start()
        Handler.allowed = load_allowed()
        Handler.token = "ci-secret"
        Handler.upstream = "http://127.0.0.1:%s/" % cls.upstream.server_port
        cls.gateway = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        threading.Thread(target=cls.gateway.serve_forever, daemon=True).start()

    @classmethod
    def tearDownClass(cls):
        cls.gateway.shutdown()
        cls.gateway.server_close()
        cls.upstream.shutdown()
        cls.upstream.server_close()

    def request(self, method, params=None, token="ci-secret"):
        body = json.dumps({"jsonrpc": "2.0", "id": 1, "method": method,
                           "params": params or {}}).encode()
        req = urllib.request.Request(
            "http://127.0.0.1:%s/" % self.gateway.server_port,
            data=body, headers={"Authorization": "Bearer " + token,
                                "Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=5) as res:
                return res.status, json.loads(res.read())
        except urllib.error.HTTPError as err:
            return err.code, json.loads(err.read())

    def test_local_file_tool_success_uses_mcp_content_format(self):
        original_allowed = Handler.allowed
        try:
            Handler.allowed = extend_allowed(load_allowed(), ["files"])
            with patch.dict("os.environ", {"MOONRAKER_URL": "http://127.0.0.1:7125",
                                           "MOONRAKER_API_KEY": ""}):
                with patch("gateway.list_gcodes",
                           return_value=[{"path": "piezas/árbol azul.gcode"}]):
                    status, body = self.request(
                        "tools/call", {"name": "moonraker_files_list", "arguments": {}})
            self.assertEqual(status, 200)
            self.assertEqual(body["jsonrpc"], "2.0")
            self.assertEqual(body["id"], 1)
            self.assertIs(body["result"]["isError"], False)
            self.assertEqual(body["result"]["content"][0]["type"], "text")
            self.assertEqual(json.loads(body["result"]["content"][0]["text"]),
                             [{"path": "piezas/árbol azul.gcode"}])
        finally:
            Handler.allowed = original_allowed

    def test_file_api_network_failures_are_mcp_tool_errors(self):
        original_allowed = Handler.allowed
        try:
            Handler.allowed = extend_allowed(load_allowed(), ["files"])
            with patch.dict("os.environ", {"MOONRAKER_URL": "http://127.0.0.1:7125",
                                           "MOONRAKER_API_KEY": "secret"}):
                for failure in (urllib.error.URLError("internal-printer secret"),
                                TimeoutError("internal-printer secret")):
                    with self.subTest(failure=type(failure).__name__):
                        with patch("gateway.list_gcodes", side_effect=failure):
                            status, body = self.request(
                                "tools/call", {"name": "moonraker_files_list",
                                               "arguments": {}})
                        self.assertEqual(status, 200)
                        self.assertIs(body["result"]["isError"], True)
                        self.assertEqual(body["result"]["content"][0]["text"],
                                         "Moonraker file service unavailable")
                        self.assertNotIn("secret", json.dumps(body))
                        self.assertNotIn("internal-printer", json.dumps(body))
        finally:
            Handler.allowed = original_allowed

    def test_file_api_errors_are_sanitized(self):
        original_allowed = Handler.allowed
        try:
            Handler.allowed = extend_allowed(load_allowed(), ["files"])
            with patch.dict("os.environ", {"MOONRAKER_URL": "http://127.0.0.1:7125",
                                           "MOONRAKER_API_KEY": "secret"}):
                for upstream_code, expected in ((404, 404), (401, 502), (500, 502)):
                    with self.subTest(upstream_code=upstream_code):
                        error = urllib.error.HTTPError(
                            "http://internal-printer:7125/secret", upstream_code,
                            "secret server detail", {}, None)
                        with patch("gateway.list_gcodes", side_effect=error):
                            status, body = self.request(
                                "tools/call", {"name": "moonraker_files_list",
                                               "arguments": {}})
                        self.assertEqual(status, 200)
                        self.assertEqual(body["result"]["isError"], True)
                        self.assertIn("not found" if expected == 404 else "unavailable",
                                      body["result"]["content"][0]["text"])
                        self.assertNotIn("secret", json.dumps(body).lower())
                        self.assertNotIn("internal-printer", json.dumps(body))
        finally:
            Handler.allowed = original_allowed

    def test_initialize_and_notification(self):
        status, body = self.request("initialize", {
            "protocolVersion": "2025-06-18", "capabilities": {},
            "clientInfo": {"name": "test", "version": "1"}})
        self.assertEqual(status, 200)
        self.assertIn("serverInfo", body["result"])
        payload = json.dumps({"jsonrpc": "2.0",
                              "method": "notifications/initialized"}).encode()
        req = urllib.request.Request(
            "http://127.0.0.1:%s/" % self.gateway.server_port,
            data=payload,
            headers={"Authorization": "Bearer ci-secret",
                     "Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=5) as response:
            self.assertEqual(response.status, 202)
            self.assertEqual(response.read(), b"")

    def test_initialize_rejects_mismatched_protocol_header(self):
        payload = json.dumps({
            "jsonrpc": "2.0", "id": 1, "method": "initialize",
            "params": {"protocolVersion": "2025-06-18",
                       "capabilities": {},
                       "clientInfo": {"name": "test", "version": "1"}}
        }).encode()
        for header, expected in (
            ("2025-03-26", 400),
            ("2024-11-05", 400),
            ("2025-06-18", 200),
        ):
            with self.subTest(header=header):
                before = len(FakeUpstream.calls)
                req = urllib.request.Request(
                    "http://127.0.0.1:%s/mcp" % self.gateway.server_port,
                    data=payload,
                    headers={"Authorization": "Bearer ci-secret",
                             "Content-Type": "application/json",
                             "MCP-Protocol-Version": header})
                try:
                    with urllib.request.urlopen(req, timeout=5) as response:
                        status = response.status
                except urllib.error.HTTPError as exc:
                    status = exc.code
                self.assertEqual(status, expected)
                self.assertEqual(len(FakeUpstream.calls), before + (1 if expected == 200 else 0))

    def test_upstream_jsonrpc_errors_preserved_over_http(self):
        original = FakeUpstream.jsonrpc_error
        try:
            FakeUpstream.jsonrpc_error = True
            for method, params in (
                ("initialize", {"protocolVersion": "2025-06-18",
                                "capabilities": {},
                                "clientInfo": {"name": "test", "version": "1"}}),
                ("tools/list", {}),
                ("tools/call", {"name": "moonraker_printer_info", "arguments": {}}),
            ):
                with self.subTest(method=method):
                    status, body = self.request(method, params)
                    self.assertEqual(status, 200)
                    self.assertEqual(body["error"]["code"], -32603)
                    self.assertNotIn("result", body)
        finally:
            FakeUpstream.jsonrpc_error = original

    def test_notification_accepts_successful_upstream_acknowledgements(self):
        original = FakeUpstream.notification_status
        try:
            payload = b'{"jsonrpc":"2.0","method":"notifications/initialized"}'
            for upstream_status in (200, 202, 204):
                with self.subTest(upstream_status=upstream_status):
                    FakeUpstream.notification_status = upstream_status
                    req = urllib.request.Request(
                        "http://127.0.0.1:%s/mcp" % self.gateway.server_port,
                        data=payload,
                        headers={"Authorization": "Bearer ci-secret",
                                 "Content-Type": "application/json"})
                    with urllib.request.urlopen(req, timeout=5) as response:
                        self.assertEqual(response.status, 202)
                        self.assertEqual(response.read(), b"")
        finally:
            FakeUpstream.notification_status = original

    def test_listing_filters_unsafe_tools(self):
        status, body = self.request("tools/list")
        self.assertEqual(status, 200)
        self.assertEqual([t["name"] for t in body["result"]["tools"]],
                         ["moonraker_printer_info"])

    def test_local_file_tool_name_cannot_be_spoofed_over_http(self):
        original_spoof = FakeUpstream.spoof_local_files
        original_allowed = Handler.allowed
        try:
            FakeUpstream.spoof_local_files = True
            status, body = self.request("tools/list")
            self.assertEqual(status, 200)
            self.assertNotIn("moonraker_files_list",
                             [tool["name"] for tool in body["result"]["tools"]])
            Handler.allowed = extend_allowed(load_allowed(), ["files"])
            status, body = self.request("tools/list")
            self.assertEqual(status, 200)
            matching = [tool for tool in body["result"]["tools"]
                        if tool["name"] == "moonraker_files_list"]
            self.assertEqual(len(matching), 1)
            self.assertNotEqual(matching[0]["description"], "untrusted upstream")
            self.assertIn("read only", matching[0]["description"])
        finally:
            FakeUpstream.spoof_local_files = original_spoof
            Handler.allowed = original_allowed

    def test_paginated_tool_listing_filters_each_http_page(self):
        original = FakeUpstream.paginate_tools
        try:
            FakeUpstream.paginate_tools = True
            first_status, first = self.request("tools/list")
            self.assertEqual(first_status, 200)
            self.assertEqual(first["result"]["nextCursor"], "page-2")
            self.assertEqual([tool["name"] for tool in first["result"]["tools"]],
                             ["moonraker_printer_info"])
            second_status, second = self.request("tools/list", {"cursor": "page-2"})
            self.assertEqual(second_status, 200)
            self.assertNotIn("nextCursor", second["result"])
            self.assertEqual([tool["name"] for tool in second["result"]["tools"]],
                             ["moonraker_server_info"])
            self.assertEqual(FakeUpstream.calls[-1]["params"]["cursor"], "page-2")
        finally:
            FakeUpstream.paginate_tools = original

    def test_mcp_endpoint_alias_and_authentication(self):
        payload = json.dumps({"jsonrpc": "2.0", "id": 11,
                              "method": "tools/list", "params": {}}).encode()
        for path in ("/", "/mcp"):
            req = urllib.request.Request(
                "http://127.0.0.1:%s%s" % (self.gateway.server_port, path),
                data=payload,
                headers={"Authorization": "Bearer ci-secret",
                         "Content-Type": "application/json",
                         "Accept": "application/json, text/event-stream"})
            with urllib.request.urlopen(req, timeout=5) as response:
                self.assertEqual(response.status, 200)
                self.assertIn("tools", json.loads(response.read())["result"])
        for auth in ("Bearer wrong", "", "Basic ci-secret", "Bearer ci-secret-extra", "bearer ci-secret"):
            req = urllib.request.Request(
                "http://127.0.0.1:%s/mcp" % self.gateway.server_port,
                data=payload, headers={"Authorization": auth,
                                       "Content-Type": "application/json"})
            with self.assertRaises(urllib.error.HTTPError) as ctx:
                urllib.request.urlopen(req, timeout=5)
            self.assertEqual(ctx.exception.code, 401)

    def test_duplicate_http_headers_rejected_before_upstream(self):
        import http.client
        for header, duplicate, expected in (
            ("Authorization", "Bearer other", 401),
            ("Content-Length", "1", 400),
            ("Content-Type", "text/plain", 400),
            ("Mcp-Session-Id", "second", 400),
            ("MCP-Protocol-Version", "2024-11-05", 400),
        ):
            with self.subTest(header=header):
                before = len(FakeUpstream.calls)
                body = b'{"jsonrpc":"2.0","id":1,"method":"tools/list"}'
                connection = http.client.HTTPConnection("127.0.0.1", self.gateway.server_port, timeout=5)
                try:
                    connection.putrequest("POST", "/mcp")
                    connection.putheader("Authorization", "Bearer ci-secret")
                    connection.putheader("Content-Type", "application/json")
                    connection.putheader("Content-Length", str(len(body)))
                    if header in ("Mcp-Session-Id", "MCP-Protocol-Version"):
                        connection.putheader(header, "session-one" if header == "Mcp-Session-Id" else "2025-06-18")
                    connection.putheader(header, duplicate)
                    connection.endheaders(body)
                    response = connection.getresponse()
                    self.assertEqual(response.status, expected)
                    response.read()
                finally:
                    connection.close()
                self.assertEqual(len(FakeUpstream.calls), before)

    def test_mcp_post_rejects_non_json_content_types(self):
        payload = b'{"jsonrpc":"2.0","id":1,"method":"tools/list"}'
        for content_type in ("text/plain", "application/x-www-form-urlencoded",
                             "application/jsonp", "application/octet-stream"):
            with self.subTest(content_type=content_type):
                before = len(FakeUpstream.calls)
                req = urllib.request.Request(
                    "http://127.0.0.1:%s/mcp" % self.gateway.server_port,
                    data=payload,
                    headers={"Authorization": "Bearer ci-secret",
                             "Content-Type": content_type})
                with self.assertRaises(urllib.error.HTTPError) as ctx:
                    urllib.request.urlopen(req, timeout=5)
                self.assertEqual(ctx.exception.code, 415)
                self.assertEqual(len(FakeUpstream.calls), before)

    def test_unsupported_session_methods_are_rejected(self):
        for method in ("GET", "DELETE"):
            req = urllib.request.Request(
                "http://127.0.0.1:%s/mcp" % self.gateway.server_port,
                headers={"Authorization": "Bearer ci-secret"}, method=method)
            with self.subTest(method=method), self.assertRaises(urllib.error.HTTPError) as ctx:
                urllib.request.urlopen(req, timeout=5)
            self.assertEqual(ctx.exception.code, 405)

    def test_malformed_upstream_response_is_502_not_403(self):
        original = FakeUpstream.malformed_result
        try:
            for method, params, malformed in (
                ("tools/list", {}, {"tools": "not-a-list"}),
                ("tools/list", {}, {"tools": [
                    {"name": "moonraker_printer_info", "inputSchema": {}}]}),
                ("tools/call", {"name": "moonraker_printer_info",
                                "arguments": {}}, {"content": "not-a-list"}),
                ("initialize", {"protocolVersion": "2025-06-18",
                                "capabilities": {}, "clientInfo": {"name": "test", "version": "1"}},
                 {"protocolVersion": "2025-06-18", "capabilities": {},
                  "serverInfo": {"name": "", "version": "1"}}),
            ):
                with self.subTest(method=method, malformed=malformed):
                    FakeUpstream.malformed_result = malformed
                    status, response = self.request(method, params)
                    self.assertEqual(status, 502)
                    self.assertEqual(response, {"error": "Invalid upstream MCP response"})
        finally:
            FakeUpstream.malformed_result = original

    def test_write_tool_cannot_be_exposed_by_any_optional_profile(self):
        from tool_policy import OPTIONAL_PROFILES
        original = Handler.allowed
        try:
            for profiles in ([], list(OPTIONAL_PROFILES)):
                with self.subTest(profiles=profiles):
                    Handler.allowed = extend_allowed(load_allowed(), profiles)
                    status, response = self.request("tools/list")
                    self.assertEqual(status, 200)
                    names = {tool["name"] for tool in response["result"]["tools"]}
                    self.assertNotIn("moonraker_gcode_script", names)
                    before = len(FakeUpstream.calls)
                    status, _ = self.request(
                        "tools/call",
                        {"name": "moonraker_gcode_script",
                         "arguments": {"script": "M112"}})
                    self.assertEqual(status, 403)
                    self.assertEqual(len(FakeUpstream.calls), before)
        finally:
            Handler.allowed = original

    def test_unsafe_call_never_reaches_upstream(self):
        before = len(FakeUpstream.calls)
        status, _ = self.request("tools/call", {
            "name": "moonraker_gcode_script", "arguments": {"script": "M112"}})
        self.assertEqual(status, 403)
        self.assertEqual(len(FakeUpstream.calls), before)

    def test_privacy_excluded_tool_never_reaches_upstream(self):
        for name in ("moonraker_history_list", "moonraker_spoolman_get_spool",
                     "moonraker_sensors_measurements", "moonraker_power_status"):
            with self.subTest(name=name):
                before = len(FakeUpstream.calls)
                status, _ = self.request("tools/call", {
                    "name": name, "arguments": {}})
                self.assertEqual(status, 403)
                self.assertEqual(len(FakeUpstream.calls), before)

    def test_optional_profiles_enforced_at_http_boundary(self):
        original = Handler.allowed
        try:
            for profile, permitted in (
                ("history", "moonraker_history_list"),
                ("sensors", "moonraker_sensors_info"),
                ("spoolman", "moonraker_spoolman_status"),
                ("power", "moonraker_power_status"),
            ):
                with self.subTest(profile=profile):
                    Handler.allowed = extend_allowed(load_allowed(), [profile])
                    before = len(FakeUpstream.calls)
                    status, _ = self.request("tools/call", {
                        "name": permitted, "arguments": {}})
                    self.assertEqual(status, 200)
                    self.assertEqual(len(FakeUpstream.calls), before + 1)
                    other = "moonraker_history_list" if profile != "history" else "moonraker_spoolman_status"
                    before = len(FakeUpstream.calls)
                    status, _ = self.request("tools/call", {
                        "name": other, "arguments": {}})
                    self.assertEqual(status, 403)
                    self.assertEqual(len(FakeUpstream.calls), before)
        finally:
            Handler.allowed = original

    def test_malformed_json_never_reaches_upstream(self):
        for payload in (
            b'{"jsonrpc":"2.0","id":1,"method":"tools/list","method":"tools/call"}',
            b'{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"moonraker_printer_info","name":"moonraker_gcode_script"}}',
            b'{"jsonrpc":"2.0","id":1,"method":"tools/list","params":{"cursor":NaN}}',
        ):
            with self.subTest(payload=payload):
                before = len(FakeUpstream.calls)
                req = urllib.request.Request(
                    "http://127.0.0.1:%s/" % self.gateway.server_port,
                    data=payload,
                    headers={"Authorization": "Bearer ci-secret",
                             "Content-Type": "application/json"})
                with self.assertRaises(urllib.error.HTTPError) as raised:
                    urllib.request.urlopen(req, timeout=5)
                self.assertEqual(raised.exception.code, 403)
                self.assertEqual(len(FakeUpstream.calls), before)

    def test_upstream_http_redirect_is_not_followed(self):
        original = FakeUpstream.redirect_target
        try:
            FakeUpstream.leaked_headers = []
            FakeUpstream.redirect_target = (
                "http://127.0.0.1:%s/collect" % self.upstream.server_port)
            for status_code in (301, 302, 303, 307, 308):
                with self.subTest(status_code=status_code):
                    FakeUpstream.redirect_status = status_code
                    status, _ = self.request("tools/list")
                    self.assertEqual(status, 502)
                    self.assertEqual(FakeUpstream.leaked_headers, [])
        finally:
            FakeUpstream.redirect_target = original

    def test_advertised_default_tools_are_callable(self):
        original = Handler.allowed
        try:
            Handler.allowed = load_allowed()
            status, listing = self.request("tools/list")
            self.assertEqual(status, 200)
            names = {tool["name"] for tool in listing["result"]["tools"]}
            self.assertIn("moonraker_printer_info", names)
            self.assertNotIn("moonraker_gcode_script", names)
            for name in names:
                with self.subTest(name=name):
                    before = len(FakeUpstream.calls)
                    status, response = self.request(
                        "tools/call", {"name": name, "arguments": {}})
                    self.assertEqual(status, 200)
                    self.assertIs(response["result"]["isError"], False)
                    self.assertEqual(len(FakeUpstream.calls), before + 1)
        finally:
            Handler.allowed = original

    def test_advertised_file_tools_are_local_and_opt_in(self):
        original = Handler.allowed
        try:
            Handler.allowed = extend_allowed(load_allowed(), ["files"])
            status, listing = self.request("tools/list")
            self.assertEqual(status, 200)
            names = {tool["name"] for tool in listing["result"]["tools"]}
            self.assertTrue({"moonraker_files_list", "moonraker_files_metadata",
                             "moonraker_files_preview"}.issubset(names))
            with patch.dict("os.environ", {"MOONRAKER_URL": "http://127.0.0.1:7125",
                                           "MOONRAKER_API_KEY": ""}):
                for name, arguments, target in (
                    ("moonraker_files_list", {}, "list_gcodes"),
                    ("moonraker_files_metadata", {"filename": "part.gcode"}, "gcode_metadata"),
                    ("moonraker_files_preview", {"filename": "part.gcode"}, "gcode_preview"),
                ):
                    with self.subTest(name=name):
                        before = len(FakeUpstream.calls)
                        with patch("gateway." + target, return_value={"ok": True}):
                            status, response = self.request(
                                "tools/call", {"name": name, "arguments": arguments})
                        self.assertEqual(status, 200)
                        self.assertIs(response["result"]["isError"], False)
                        self.assertEqual(len(FakeUpstream.calls), before)
        finally:
            Handler.allowed = original

    def test_allowed_call_reaches_fake_upstream(self):
        before = len(FakeUpstream.calls)
        status, _ = self.request("tools/call", {
            "name": "moonraker_printer_info", "arguments": {}})
        self.assertEqual(status, 200)
        self.assertEqual(len(FakeUpstream.calls), before + 1)

    def test_unauthenticated_request_never_reaches_upstream(self):
        before = len(FakeUpstream.calls)
        status, _ = self.request("tools/list", token="wrong")
        self.assertEqual(status, 401)
        self.assertEqual(len(FakeUpstream.calls), before)


if __name__ == "__main__":
    unittest.main()
