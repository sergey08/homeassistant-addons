"""Restrictive MCP HTTP gateway for Moonraker (DEV).

Only selected JSON-RPC methods are forwarded. tools/list is filtered and
tools/call is independently authorized. No unauthenticated upstream access.
"""
import json
import hmac
import os
import re
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from moonraker_files import FileAccessError, list_gcodes, gcode_metadata, gcode_preview
from tool_policy import PolicyError, authorize_call, extend_allowed, filter_tools, load_allowed

ALLOWED_METHODS = frozenset((
    "initialize", "notifications/initialized", "ping", "tools/list", "tools/call"
))
MAX_BODY = 1024 * 1024
MAX_TOOL_ARGUMENTS = 16 * 1024
FORWARD_HEADERS = ("Mcp-Session-Id", "MCP-Protocol-Version")
LOCAL_FILE_TOOLS = {
    "moonraker_files_list": {
        "name": "moonraker_files_list",
        "description": "List G-code files on Moonraker (read only, opt-in).",
        "inputSchema": {"type": "object", "properties": {}, "additionalProperties": False},
    },
    "moonraker_files_preview": {
        "name": "moonraker_files_preview",
        "description": "Read up to 16 KiB from the start of a G-code file (read only, opt-in).",
        "inputSchema": {"type": "object", "properties": {
            "filename": {"type": "string"}}, "required": ["filename"], "additionalProperties": False},
    },
    "moonraker_files_metadata": {
        "name": "moonraker_files_metadata",
        "description": "Get metadata of one G-code file (read only, opt-in).",
        "inputSchema": {"type": "object", "properties": {
            "filename": {"type": "string"}}, "required": ["filename"], "additionalProperties": False},
    },
}
SAFE_HEADER_VALUE = re.compile(r"^[A-Za-z0-9._-]{1,128}$")
SUPPORTED_PROTOCOL_VERSIONS = frozenset(("2025-03-26", "2025-06-18"))


def validate_mcp_header(value):
    if not isinstance(value, str) or not SAFE_HEADER_VALUE.fullmatch(value):
        raise PolicyError("Invalid MCP session or protocol header")
    return value


def _unique_json_object(pairs):
    obj = {}
    for key, value in pairs:
        if key in obj:
            raise PolicyError("Duplicate JSON field")
        obj[key] = value
    return obj


def _reject_json_constant(value):
    raise PolicyError("Invalid JSON constant")


def strict_json_loads(payload):
    return json.loads(payload, object_pairs_hook=_unique_json_object,
                      parse_constant=_reject_json_constant)


def check_message(message, allowed):
    if not isinstance(message, dict) or message.get("jsonrpc") != "2.0":
        raise PolicyError("Invalid JSON-RPC request")
    if any(key not in ("jsonrpc", "id", "method", "params") for key in message):
        raise PolicyError("Unexpected JSON-RPC request fields")
    if "id" in message and (isinstance(message["id"], bool) or not isinstance(message["id"], (str, int))):
        raise PolicyError("Invalid JSON-RPC id")
    method = message.get("method")
    if method not in ALLOWED_METHODS:
        raise PolicyError("MCP method is not permitted")
    if method == "notifications/initialized" and "id" in message:
        raise PolicyError("MCP notification must not have an id")
    if method != "notifications/initialized" and "id" not in message:
        raise PolicyError("MCP request must have an id")
    if "params" in message and not isinstance(message["params"], dict):
        raise PolicyError("MCP params must be an object")
    if method in ("ping", "notifications/initialized") and message.get("params", {}) != {}:
        raise PolicyError("Unexpected parameters for MCP method")
    if method == "tools/list":
        params = message.get("params", {})
        if set(params) - {"cursor"} or ("cursor" in params and
                (not isinstance(params["cursor"], str) or not 0 < len(params["cursor"]) <= 512)):
            raise PolicyError("Invalid MCP tools/list cursor")
    if method == "initialize":
        params = message.get("params")
        if not isinstance(params, dict) or params.get("protocolVersion") not in SUPPORTED_PROTOCOL_VERSIONS:
            raise PolicyError("Unsupported MCP protocol version")
        if not isinstance(params.get("capabilities"), dict) or not isinstance(params.get("clientInfo"), dict):
            raise PolicyError("Invalid MCP initialize parameters")
    if method == "tools/call":
        params = message.get("params")
        if not isinstance(params, dict):
            raise PolicyError("Missing tool arguments")
        if any(key not in ("name", "arguments", "_meta") for key in params):
            raise PolicyError("Unexpected tools/call parameters")
        if "arguments" in params and not isinstance(params["arguments"], dict):
            raise PolicyError("Tool arguments must be an object")
        arguments = params.get("arguments", {})
        if len(json.dumps(arguments).encode("utf-8")) > MAX_TOOL_ARGUMENTS:
            raise PolicyError("Tool arguments too large")
        authorize_call(params.get("name"), allowed)
        name = params.get("name")
        if name in LOCAL_FILE_TOOLS:
            schema = LOCAL_FILE_TOOLS[name]["inputSchema"]
            required = set(schema.get("required", []))
            permitted = set(schema.get("properties", {}))
            if set(arguments) != required or not set(arguments).issubset(permitted):
                raise PolicyError("Invalid file tool arguments")
            for key in required:
                if not isinstance(arguments[key], str):
                    raise PolicyError("Invalid file tool argument type")
    return method


def validate_reply(request, response):
    """Reject malformed or unrelated JSON-RPC replies from upstream."""
    if not isinstance(response, dict) or response.get("jsonrpc") != "2.0":
        raise PolicyError("Invalid upstream JSON-RPC response")
    if "id" not in response or type(response["id"]) is not type(request.get("id")) or response["id"] != request.get("id"):
        raise PolicyError("Upstream JSON-RPC response id mismatch")
    if any(key not in ("jsonrpc", "id", "result", "error") for key in response):
        raise PolicyError("Unexpected upstream JSON-RPC response fields")
    if ("result" in response) == ("error" in response):
        raise PolicyError("Invalid upstream JSON-RPC result/error")
    if "error" in response:
        error = response["error"]
        if not isinstance(error, dict) or isinstance(error.get("code"), bool) or not isinstance(error.get("code"), int) or not isinstance(error.get("message"), str):
            raise PolicyError("Invalid upstream JSON-RPC error")
    return response


def filter_reply(method, response, allowed, cursor=None):
    # A valid JSON-RPC error has no result; preserve it for the MCP client.
    if "error" in response:
        return response
    if method == "initialize":
        result = response.get("result")
        if not isinstance(result, dict) or result.get("protocolVersion") not in SUPPORTED_PROTOCOL_VERSIONS:
            raise PolicyError("Unsupported upstream MCP protocol version")
        if not isinstance(result.get("capabilities"), dict) or not isinstance(result.get("serverInfo"), dict):
            raise PolicyError("Invalid upstream MCP initialize response")
        return response
    if method != "tools/list":
        return response
    if not isinstance(response, dict) or not isinstance(response.get("result"), dict):
        raise PolicyError("Invalid tools/list response")
    result = response["result"]
    if any(key not in ("tools", "nextCursor") for key in result):
        raise PolicyError("Unexpected tools/list result fields")
    if "nextCursor" in result and (not isinstance(result["nextCursor"], str) or
                                   not 0 < len(result["nextCursor"]) <= 512):
        raise PolicyError("Invalid upstream tools/list cursor")
    response = dict(response)
    local_tools = ([tool for name, tool in LOCAL_FILE_TOOLS.items() if name in allowed]
                   if cursor is None else [])
    response["result"] = dict(result, tools=filter_tools(result.get("tools"), allowed) + local_tools)
    return response


class NoRedirect(urllib.request.HTTPRedirectHandler):
    """Do not follow upstream redirects with MCP authorization headers."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


UPSTREAM_OPENER = urllib.request.build_opener(NoRedirect)


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
        if len(self.headers.get_all("Authorization", [])) != 1:
            return self.reply(401, {"error": "Unauthorized"})
        authorization = self.headers.get("Authorization", "")
        if not hmac.compare_digest(authorization, "Bearer " + self.token):
            return self.reply(401, {"error": "Unauthorized"})
        try:
            for header in ("Content-Length", "Content-Type", "Mcp-Session-Id", "MCP-Protocol-Version"):
                if len(self.headers.get_all(header, [])) > 1:
                    return self.reply(400, {"error": "Duplicate HTTP header"})
            content_type = self.headers.get("Content-Type", "").split(";", 1)[0].strip().lower()
            if content_type != "application/json":
                return self.reply(415, {"error": "MCP POST requires application/json"})
            length = int(self.headers.get("Content-Length", "-1"))
            if not 0 <= length <= MAX_BODY:
                return self.reply(413, {"error": "Invalid request size"})
            message = strict_json_loads(self.rfile.read(length))
            method = check_message(message, self.allowed)
            protocol_version = self.headers.get("MCP-Protocol-Version")
            if protocol_version and protocol_version not in SUPPORTED_PROTOCOL_VERSIONS:
                return self.reply(400, {"error": "Unsupported MCP protocol version"})
            if method == "initialize" and protocol_version and protocol_version != message["params"]["protocolVersion"]:
                return self.reply(400, {"error": "MCP protocol version header does not match initialize request"})
            if method == "tools/call" and message["params"]["name"] in LOCAL_FILE_TOOLS:
                name = message["params"]["name"]
                args = message["params"].get("arguments", {})
                if name == "moonraker_files_list":
                    if args:
                        raise PolicyError("Unexpected file list arguments")
                    result = list_gcodes(os.environ["MOONRAKER_URL"], os.environ.get("MOONRAKER_API_KEY", ""))
                else:
                    if set(args) != {"filename"}:
                        raise PolicyError("Expected only filename")
                    if name == "moonraker_files_preview":
                        result = gcode_preview(os.environ["MOONRAKER_URL"], args["filename"],
                                               os.environ.get("MOONRAKER_API_KEY", ""))
                    else:
                        result = gcode_metadata(os.environ["MOONRAKER_URL"], args["filename"],
                                                os.environ.get("MOONRAKER_API_KEY", ""))
                return self.reply(200, {"jsonrpc": "2.0", "id": message["id"],
                                        "result": {"content": [{"type": "text",
                                                               "text": json.dumps(result)}]}})
            headers = {
                "Authorization": "Bearer " + self.token,
                "Content-Type": "application/json",
                "Accept": "application/json, text/event-stream",
            }
            for key in FORWARD_HEADERS:
                value = self.headers.get(key)
                if value:
                    headers[key] = validate_mcp_header(value)
            req = urllib.request.Request(
                self.upstream, data=json.dumps(message).encode(), headers=headers
            )
            try:
                with UPSTREAM_OPENER.open(req, timeout=25) as upstream:
                    raw = upstream.read(MAX_BODY + 1)
                    if len(raw) > MAX_BODY:
                        raise PolicyError("Upstream response too large")
                    if method == "notifications/initialized":
                        # Notifications have no JSON-RPC id and never expect a response.
                        # Accept a successful upstream acknowledgement without parsing
                        # an unrelated response body as a JSON-RPC reply.
                        self.send_response(202)
                        self.send_header("Content-Length", "0")
                        self.send_header("Cache-Control", "no-store")
                        self.end_headers()
                        return
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
                    parsed = filter_reply(method, validate_reply(message, strict_json_loads(raw)), self.allowed,
                                          message.get("params", {}).get("cursor") if method == "tools/list" else None)
                    extra = {}
                    session = upstream.headers.get("Mcp-Session-Id")
                    if session:
                        extra["Mcp-Session-Id"] = validate_mcp_header(session)
                    return self.reply(200, parsed, extra)
            except urllib.error.HTTPError as exc:
                return self.reply(502, {"error": "Upstream MCP error", "status": exc.code})
        except (PolicyError, FileAccessError, ValueError, TypeError, UnicodeError) as exc:
            return self.reply(403, {"error": str(exc)})
        except Exception:
            self.log_error("MCP upstream communication failed")
            return self.reply(502, {"error": "Upstream unavailable"})

    def do_GET(self):
        self.reply(405, {"error": "Only POST is supported"})

    def do_DELETE(self):
        self.reply(405, {"error": "Only POST is supported"})


if __name__ == "__main__":
    Handler.allowed = extend_allowed(load_allowed(), json.loads(os.environ.get("MCP_ALLOWED_PROFILES", "[]")))
    Handler.token = os.environ["MCP_HTTP_TOKEN"]
    if not Handler.token:
        raise SystemExit("MCP_HTTP_TOKEN must not be empty")
    ThreadingHTTPServer(("0.0.0.0", 8765), Handler).serve_forever()
