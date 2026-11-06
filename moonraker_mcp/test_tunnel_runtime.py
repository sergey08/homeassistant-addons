"""Printer-free security tests for the loopback tunnel authentication bridge."""
import http.server
import json
import threading
import unittest
import urllib.error
import urllib.request
from unittest import mock

import tunnel_runtime


class FakeGateway(http.server.BaseHTTPRequestHandler):
    last_auth = None
    last_body = None

    def do_POST(self):
        type(self).last_auth = self.headers.get("Authorization")
        type(self).last_body = self.rfile.read(int(self.headers["Content-Length"]))
        payload = b'{"jsonrpc":"2.0","id":1,"result":{}}'
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def log_message(self, *_args):
        pass


class TestTunnelBridge(unittest.TestCase):
    def setUp(self):
        self.backend = http.server.ThreadingHTTPServer(("127.0.0.1", 0), FakeGateway)
        self.frontend = http.server.ThreadingHTTPServer(("127.0.0.1", 0), tunnel_runtime.Bridge)
        self.backend_thread = threading.Thread(target=self.backend.serve_forever, daemon=True)
        self.frontend_thread = threading.Thread(target=self.frontend.serve_forever, daemon=True)
        self.backend_thread.start()
        self.frontend_thread.start()
        self.url = "http://127.0.0.1:%d/mcp" % self.frontend.server_port
        self.backend_url = "http://127.0.0.1:%d/mcp" % self.backend.server_port
        self.patch = mock.patch.object(tunnel_runtime, "UPSTREAM", self.backend_url)
        self.patch.start()
        tunnel_runtime.Bridge.token = "secret-internal-only"
        FakeGateway.last_auth = None
        FakeGateway.last_body = None

    def tearDown(self):
        self.frontend.shutdown()
        self.backend.shutdown()
        self.frontend.server_close()
        self.backend.server_close()
        self.frontend_thread.join(timeout=3)
        self.backend_thread.join(timeout=3)
        self.patch.stop()

    def send(self, path="/mcp", origin=None, host="127.0.0.1:8767"):
        headers = {"Content-Type": "application/json", "Host": host}
        if origin is not None:
            headers["Origin"] = origin
        req = urllib.request.Request(
            self.url if path == "/mcp" else self.url.replace("/mcp", path),
            data=b'{"jsonrpc":"2.0","id":1,"method":"ping"}', headers=headers)
        return urllib.request.urlopen(req, timeout=3)

    def test_only_loopback_bridge_injects_token(self):
        with self.send() as response:
            self.assertEqual(response.status, 200)
            self.assertEqual(json.loads(response.read())["result"], {})
            self.assertIsNone(response.headers.get("Access-Control-Allow-Origin"))
        self.assertEqual(FakeGateway.last_auth, "Bearer secret-internal-only")
        self.assertIn(b'"method":"ping"', FakeGateway.last_body)

    def test_rejects_browser_origin_and_unexpected_host(self):
        for values in ({"origin": "https://evil.example"}, {"host": "evil.example:8767"},
                       {"host": "127.0.0.1:12345"}):
            with self.subTest(values=values):
                with self.assertRaises(urllib.error.HTTPError) as raised:
                    self.send(**values)
                self.assertEqual(raised.exception.code, 403)
                raised.exception.read()
        self.assertIsNone(FakeGateway.last_auth)

    def test_other_path_cannot_reach_gateway(self):
        with self.assertRaises(urllib.error.HTTPError) as raised:
            self.send(path="/admin")
        self.assertEqual(raised.exception.code, 404)
        raised.exception.read()
        self.assertIsNone(FakeGateway.last_auth)


if __name__ == "__main__":
    unittest.main()
