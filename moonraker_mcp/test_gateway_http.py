"""HTTP-level security tests with a fake upstream; no printer is contacted."""
import json
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
            self.send_response(202)
            self.send_header("Content-Length", "0")
            self.end_headers()
            return
        if method == "tools/list":
            result = {"tools": [
                {"name": "moonraker_printer_info", "inputSchema": {}},
                {"name": "moonraker_gcode_script", "inputSchema": {}},
            ]}
        elif method == "initialize":
            result = {"serverInfo": {"name": "fake", "version": "1"}}
        else:
            result = {"ok": True}
        body = json.dumps({"jsonrpc": "2.0", "id": message.get("id"), "result": result}).encode()
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

    def test_listing_filters_unsafe_tools(self):
        status, body = self.request("tools/list")
        self.assertEqual(status, 200)
        self.assertEqual([t["name"] for t in body["result"]["tools"]],
                         ["moonraker_printer_info"])

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
