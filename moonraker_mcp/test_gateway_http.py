"""HTTP-level security tests with a fake upstream; no printer is contacted."""
import json
import threading
import unittest
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from gateway import Handler
from tool_policy import load_allowed


class FakeUpstream(BaseHTTPRequestHandler):
    calls = []

    def do_POST(self):
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

    def test_unsafe_call_never_reaches_upstream(self):
        before = len(FakeUpstream.calls)
        status, _ = self.request("tools/call", {
            "name": "moonraker_gcode_script", "arguments": {"script": "M112"}})
        self.assertEqual(status, 403)
        self.assertEqual(len(FakeUpstream.calls), before)

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
