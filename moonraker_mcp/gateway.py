"""Restrictive MCP HTTP gateway for Moonraker (DEV).

Only selected JSON-RPC methods are forwarded. tools/list is filtered and
tools/call is independently authorized. No unauthenticated upstream access.
"""
import json
import os
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from tool_policy import PolicyError, authorize_call, filter_tools, load_allowed

ALLOWED_METHODS = frozenset((
    "initialize", "notifications/initialized", "ping", "tools/list", "tools/call"
))
MAX_BODY = 1024 * 1024
FORWARD_HEADERS = ("Mcp-Session-Id", "MCP-Protocol-Version")


def check_message(message, allowed):
    if not isinstance(message, dict) or message.get("jsonrpc") != "2.0":
        raise PolicyError("Invalid JSON-RPC request")
    method = message.get("method")
    if method not in ALLOWED_METHODS:
        raise PolicyError("MCP method is not permitted")
    if method == "tools/call":
        params = message.get("params")
        if not isinstance(params, dict):
            raise PolicyError("Missing tool arguments")
        authorize_call(params.get("name"), allowed)
    return method


def filter_reply(method, response, allowed):
    if method != "tools/list":
        return response
    if not isinstance(response, dict) or not isinstance(response.get("result"), dict):
        raise PolicyError("Invalid tools/list response")
    result = response["result"]
    if "nextCursor" in result:
        raise PolicyError("Paginated tool listings not supported")
    response = dict(response)
    response["result"] = dict(result, tools=filter_tools(result.get("tools"), allowed))
    return response


class Handler(BaseHTTPRequestHandler):
    allowed = frozenset()
    token = ""
    upstream = "http://127.0.0.1:8766/"

    def reply(self, status, payload, extra=None):
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        for key, value in (extra or {}).items():
            self.send_header(key, value)
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):
        if self.path not in ("/", "/mcp"):
            return self.reply(404, {"error": "Not found"})
        if self.headers.get("Authorization") != "Bearer " + self.token:
            return self.reply(401, {"error": "Unauthorized"})
        try:
            length = int(self.headers.get("Content-Length", "-1"))
            if not 0 <= length <= MAX_BODY:
                return self.reply(413, {"error": "Invalid request size"})
            message = json.loads(self.rfile.read(length))
            method = check_message(message, self.allowed)
            headers = {
                "Authorization": "Bearer " + self.token,
                "Content-Type": "application/json",
                "Accept": "application/json, text/event-stream",
            }
            for key in FORWARD_HEADERS:
                value = self.headers.get(key)
                if value:
                    headers[key] = value
            req = urllib.request.Request(
                self.upstream, data=json.dumps(message).encode(), headers=headers
            )
            try:
                with urllib.request.urlopen(req, timeout=25) as upstream:
                    raw = upstream.read(MAX_BODY + 1)
                    if len(raw) > MAX_BODY:
                        raise PolicyError("Upstream response too large")
                    content_type = upstream.headers.get("Content-Type", "")
                    if "text/event-stream" in content_type:
                        events = [
                            line[6:].strip() for line in raw.decode().splitlines()
                            if line.startswith("data:")
                        ]
                        if len(events) != 1:
                            raise PolicyError("Unsupported upstream SSE response")
                        raw = events[0].encode()
                    elif "application/json" not in content_type:
                        raise PolicyError("Unsupported upstream content type")
                    if not raw.strip() and method == "notifications/initialized":
                        self.send_response(202)
                        self.send_header("Content-Length", "0")
                        self.end_headers()
                        return
                    parsed = filter_reply(method, json.loads(raw), self.allowed)
                    extra = {}
                    session = upstream.headers.get("Mcp-Session-Id")
                    if session:
                        extra["Mcp-Session-Id"] = session
                    return self.reply(200, parsed, extra)
            except urllib.error.HTTPError as exc:
                return self.reply(502, {"error": "Upstream MCP error", "status": exc.code})
        except (PolicyError, ValueError, TypeError, UnicodeError) as exc:
            return self.reply(403, {"error": str(exc)})
        except Exception:
            self.log_error("MCP upstream communication failed")
            return self.reply(502, {"error": "Upstream unavailable"})

    def do_GET(self):
        self.reply(405, {"error": "Only POST is supported"})

    def do_DELETE(self):
        self.reply(405, {"error": "Only POST is supported"})


if __name__ == "__main__":
    Handler.allowed = load_allowed()
    Handler.token = os.environ["MCP_HTTP_TOKEN"]
    if not Handler.token:
        raise SystemExit("MCP_HTTP_TOKEN must not be empty")
    ThreadingHTTPServer(("0.0.0.0", 8765), Handler).serve_forever()
