"""Optional local-only authentication bridge for OpenAI tunnel-client.

The tunnel connects to localhost:8767. This bridge injects the add-on's
private bearer token when forwarding to the filtered gateway on :8765.
It never contacts the unfiltered upstream or the printer directly.
"""
import http.server
import os
import subprocess
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path

PORT = 8767
UPSTREAM = "http://127.0.0.1:8765/mcp"
ALLOWED_HEADERS = ("Accept", "Content-Type", "MCP-Protocol-Version", "Mcp-Session-Id")
RETURN_HEADERS = ("Content-Type", "Mcp-Session-Id", "MCP-Protocol-Version", "Allow")
MAX_LENGTH = 1024 * 1024


class Bridge(http.server.BaseHTTPRequestHandler):
    token = ""
    protocol_version = "HTTP/1.1"

    def log_message(self, *_args):
        # No request headers or secrets in logs.
        pass

    def handle_request(self):
        if self.path != "/mcp":
            return self.respond(404, b"")
        # The tunnel-client is the only supported peer of this loopback
        # listener; reject browser-originated requests including DNS rebinding.
        if (self.headers.get_all("Origin", []) or
                self.headers.get_all("Host", []) not in
                (["127.0.0.1:8767"], ["localhost:8767"])):
            return self.respond(403, b"")
        length = self.headers.get("Content-Length")
        if self.command == "POST":
            if length is None or not length.isdecimal() or int(length) > MAX_LENGTH:
                return self.respond(413, b"")
            body = self.rfile.read(int(length))
        else:
            body = None
        headers = {"Authorization": "Bearer " + self.token}
        for name in ALLOWED_HEADERS:
            values = self.headers.get_all(name, [])
            if len(values) > 1:
                return self.respond(400, b"")
            if values:
                headers[name] = values[0]
        req = urllib.request.Request(UPSTREAM, data=body, headers=headers, method=self.command)
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        try:
            with opener.open(req, timeout=20) as response:
                status, payload, response_headers = response.status, response.read(MAX_LENGTH + 1), response.headers
        except urllib.error.HTTPError as exc:
            status, payload, response_headers = exc.code, exc.read(MAX_LENGTH + 1), exc.headers
        except (OSError, urllib.error.URLError):
            return self.respond(502, b"")
        if len(payload) > MAX_LENGTH:
            return self.respond(502, b"")
        return self.respond(status, payload,
                            {name: response_headers[name] for name in RETURN_HEADERS if name in response_headers})

    def respond(self, status, body, headers=None):
        self.send_response(status)
        for name, value in (headers or {}).items():
            self.send_header(name, value)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(body)

    do_POST = handle_request
    do_GET = handle_request
    do_DELETE = handle_request


def run():
    token = os.environ.get("MCP_HTTP_TOKEN", "")
    tunnel_id = os.environ.get("MCP_TUNNEL_ID", "")
    binary = Path("/data/tunnel/bin/tunnel-client")
    api_key = Path("/data/tunnel/api-key")
    if not token or not tunnel_id or not binary.is_file() or not os.access(binary, os.X_OK) or not api_key.is_file():
        raise SystemExit("Tunnel enabled but ID, client binary or private key is missing")
    if api_key.stat().st_mode & 0o077:
        raise SystemExit("Tunnel API key permissions must deny group/other access")
    for _ in range(60):
        try:
            with urllib.request.build_opener(urllib.request.ProxyHandler({})).open(
                urllib.request.Request(UPSTREAM, method="HEAD"), timeout=1
            ) as _resp:
                break
        except urllib.error.HTTPError as exc:
            if exc.code == 401:
                break
        except (OSError, urllib.error.URLError):
            time.sleep(0.5)
    else:
        raise SystemExit("MCP gateway not ready")
    Bridge.token = token
    server = http.server.ThreadingHTTPServer(("127.0.0.1", PORT), Bridge)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        process = subprocess.run([
            str(binary), "run",
            "--control-plane.tunnel-id", tunnel_id,
            "--control-plane.api-key", "file:" + str(api_key),
            "--mcp.server-url", "channel=main,url=http://127.0.0.1:8767/mcp",
            "--health.listen-addr", "127.0.0.1:0",
            "--health.url-file", "/data/tunnel/health.url",
        ], check=False)
        raise SystemExit(process.returncode or "Tunnel client terminated unexpectedly")
    finally:
        server.shutdown()


if __name__ == "__main__":
    run()
