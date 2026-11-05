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
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from moonraker_files import FileAccessError, list_gcodes, gcode_metadata, gcode_preview
from moonraker_status import connection_status, public_printer_info, public_server_info, public_temperature_store
from tool_policy import PolicyError, authorize_call, extend_allowed, filter_tools, load_allowed

ALLOWED_METHODS = frozenset((
    "initialize", "notifications/initialized", "ping", "tools/list", "tools/call", "server/discover"
))
MAX_BODY = 1024 * 1024
MAX_TOOL_ARGUMENTS = 16 * 1024
FORWARD_HEADERS = ("Mcp-Session-Id", "MCP-Protocol-Version")
LOCAL_STATUS_TOOL = "moonraker_connection_status"
PRIVACY_SAFE_PRINTER_INFO = "moonraker_printer_info"
PRIVACY_SAFE_SERVER_INFO = "moonraker_server_info"
PRIVACY_SAFE_TEMPERATURE_STORE = "moonraker_temperature_store"
LOCAL_STATUS_DEFINITION = {
    "name": LOCAL_STATUS_TOOL,
    "description": ("Check whether Moonraker is reachable and Klippy is ready. "
                    "Use before printer queries; an unreachable printer may be switched off "
                    "or disconnected. Read-only; never powers on the printer."),
    "inputSchema": {"type": "object", "properties": {}, "additionalProperties": False},
}

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
MODERN_PROTOCOL = "2026-07-28"
# A newer client may propose 2025-11-25 during initialize. Negotiate back
# to the upstream-compatible 2025-06-18; do not claim 2025-11-25 support.
CLIENT_INITIALIZE_VERSIONS = SUPPORTED_PROTOCOL_VERSIONS | {"2025-11-25"}


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


def modern_request(message):
    """Recognize the new per-request protocol while keeping legacy strict."""
    if not isinstance(message, dict):
        return False
    params = message.get("params", {})
    if not isinstance(params, dict):
        return False
    meta = params.get("_meta")
    return isinstance(meta, dict) and meta.get("io.modelcontextprotocol/protocolVersion") == MODERN_PROTOCOL


def validate_modern_meta(message):
    """Only known protocol metadata is used; never forward client metadata upstream."""
    params = message.get("params")
    if not isinstance(params, dict):
        raise PolicyError("Modern MCP requires request parameters")
    meta = params.get("_meta")
    if not isinstance(meta, dict) or meta.get("io.modelcontextprotocol/protocolVersion") != MODERN_PROTOCOL:
        raise PolicyError("Unsupported modern MCP protocol")
    info = meta.get("io.modelcontextprotocol/clientInfo")
    caps = meta.get("io.modelcontextprotocol/clientCapabilities")
    if (not isinstance(info, dict) or not isinstance(info.get("name"), str)
            or not info["name"] or not isinstance(info.get("version"), str)
            or not info["version"] or not isinstance(caps, dict)):
        raise PolicyError("Invalid modern MCP client metadata")


def modern_discovery(request):
    """Local, read-only discovery: upstream has no modern discovery operation."""
    return {"jsonrpc": "2.0", "id": request["id"], "result": {
        "resultType": "complete",
        "supportedVersions": [MODERN_PROTOCOL],
        "capabilities": {"tools": {}},
        "_meta": {"io.modelcontextprotocol/serverInfo": {
            "name": "moonraker-mcp-gateway", "version": "0.1.0-dev9"}},
        "ttlMs": 0,
        "cacheScope": "private",
    }}


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
    modern = modern_request(message)
    if method == "server/discover" or modern:
        validate_modern_meta(message)
    if method == "server/discover":
        if set(message["params"]) != {"_meta"}:
            raise PolicyError("Unexpected discovery parameters")
    if method in ("ping", "notifications/initialized") and message.get("params", {}) != ({"_meta": message["params"]["_meta"]} if modern else {}):
        raise PolicyError("Unexpected parameters for MCP method")
    if method == "tools/list":
        params = message.get("params", {})
        if set(params) - ({"cursor", "_meta"} if modern else {"cursor"}) or ("cursor" in params and
                (not isinstance(params["cursor"], str) or not 0 < len(params["cursor"]) <= 512)):
            raise PolicyError("Invalid MCP tools/list cursor")
    if method == "initialize":
        params = message.get("params")
        if not isinstance(params, dict) or params.get("protocolVersion") not in CLIENT_INITIALIZE_VERSIONS:
            raise PolicyError("Unsupported MCP protocol version")
        if not isinstance(params.get("capabilities"), dict) or not isinstance(params.get("clientInfo"), dict):
            raise PolicyError("Invalid MCP initialize parameters")
        client_info = params["clientInfo"]
        if (not isinstance(client_info.get("name"), str) or not client_info["name"] or
                not isinstance(client_info.get("version"), str) or not client_info["version"]):
            raise PolicyError("Invalid MCP client identity")
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
        if name in LOCAL_FILE_TOOLS or name == LOCAL_STATUS_TOOL:
            schema = (LOCAL_STATUS_DEFINITION if name == LOCAL_STATUS_TOOL
                      else LOCAL_FILE_TOOLS[name])["inputSchema"]
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
        server_info = result["serverInfo"]
        if (not isinstance(server_info.get("name"), str) or not server_info["name"] or
                not isinstance(server_info.get("version"), str) or not server_info["version"]):
            raise PolicyError("Invalid upstream MCP server identity")
        if "instructions" in result and not isinstance(result["instructions"], str):
            raise PolicyError("Invalid upstream MCP instructions")
        # Advertise only the capability implemented by this gateway. The
        # upstream may expose resources, prompts, logging or notifications that
        # this read-only HTTP facade intentionally does not implement.
        # Always advertise tools, including the gateway's local opt-in tools.
        # Do not advertise listChanged because this facade does not forward
        # notifications/tools/list_changed.
        sanitized = {key: value for key, value in result.items()
                     if key not in ("instructions", "capabilities")}
        sanitized["capabilities"] = {"tools": {}}
        return dict(response, result=sanitized)
    if method == "tools/call":
        result = response.get("result")
        if not isinstance(result, dict) or not isinstance(result.get("content"), list):
            raise PolicyError("Invalid upstream MCP tool result")
        if "isError" in result and not isinstance(result["isError"], bool):
            raise PolicyError("Invalid upstream MCP tool error flag")
        for item in result["content"]:
            if not isinstance(item, dict) or not isinstance(item.get("type"), str):
                raise PolicyError("Invalid upstream MCP content item")
            if item["type"] not in ("text", "image", "audio", "resource_link", "resource"):
                raise PolicyError("Unsupported upstream MCP content type")
            if item["type"] == "text" and not isinstance(item.get("text"), str):
                raise PolicyError("Invalid upstream MCP text content")
            if item["type"] in ("image", "audio"):
                if (not isinstance(item.get("data"), str) or
                        not isinstance(item.get("mimeType"), str) or
                        not item["mimeType"]):
                    raise PolicyError("Invalid upstream MCP binary content")
            if item["type"] == "resource_link":
                if not isinstance(item.get("uri"), str) or not isinstance(item.get("name"), str):
                    raise PolicyError("Invalid upstream MCP resource link")
            if item["type"] == "resource":
                resource = item.get("resource")
                if not isinstance(resource, dict) or not isinstance(resource.get("uri"), str):
                    raise PolicyError("Invalid upstream MCP embedded resource")
                if not isinstance(resource.get("text"), str) and not isinstance(resource.get("blob"), str):
                    raise PolicyError("Invalid upstream MCP embedded resource content")
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
    # Local file names are reserved: ignore upstream definitions and never
    # forward calls to them. This also supports upstreams with matching names.
    local_tools = (([LOCAL_STATUS_DEFINITION] if LOCAL_STATUS_TOOL in allowed else []) +
                   [tool for name, tool in LOCAL_FILE_TOOLS.items() if name in allowed]
                   if cursor is None else [])
    response["result"] = dict(result, tools=[tool for tool in filter_tools(result.get("tools"), allowed)
                                                   if tool["name"] not in LOCAL_FILE_TOOLS and tool["name"] != LOCAL_STATUS_TOOL] + local_tools)
    for tool in response["result"]["tools"]:
        if tool["name"] == PRIVACY_SAFE_PRINTER_INFO:
            tool["description"] = ("Read printer state and software version only. "
                                   "Hostnames, CPU details and internal paths are withheld.")
        if tool["name"] == PRIVACY_SAFE_SERVER_INFO:
            tool["description"] = ("Read Moonraker version and Klippy connectivity only. "
                                   "Component lists and warning details are withheld.")
        if tool["name"] == PRIVACY_SAFE_TEMPERATURE_STORE:
            tool["description"] = ("Read at most the 120 most recent samples per heater series. "
                                   "Custom sensor names are anonymized.")
    return response


class NoRedirect(urllib.request.HTTPRedirectHandler):
    """Do not follow upstream redirects with MCP authorization headers."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


UPSTREAM_OPENER = urllib.request.build_opener(NoRedirect)

def initialize_legacy_upstream(upstream_url, token):
    """Initialize a private upstream session for one modern stateless request.

    Never reuse an unauthenticated client-provided session ID. The pinned
    upstream requires initialize -> initialized before tools/list or calls.
    """
    headers = {"Authorization": "Bearer " + token,
               "Content-Type": "application/json",
               "Accept": "application/json, text/event-stream"}
    initial = {"jsonrpc": "2.0", "id": "_gateway_init",
               "method": "initialize",
               "params": {"protocolVersion": "2025-06-18",
                          "capabilities": {},
                          "clientInfo": {"name": "moonraker-mcp-compat",
                                         "version": "0.1.0-dev7"}}}
    req = urllib.request.Request(upstream_url, data=json.dumps(initial).encode(),
                                 headers=headers)
    with UPSTREAM_OPENER.open(req, timeout=12) as response:
        raw = response.read(MAX_BODY + 1)
        if len(raw) > MAX_BODY:
            raise PolicyError("Upstream initialize reply too large")
        content_type = response.headers.get("Content-Type", "").split(";", 1)[0].lower().strip()
        if content_type == "text/event-stream":
            lines = raw.decode("utf-8").splitlines()
            events = [line[5:].lstrip(" ") for line in lines if line.startswith("data:")]
            if len(events) != 1 or any(line and not line.startswith(
                    ("data:", "event:", "id:", "retry:", ":")) for line in lines):
                raise PolicyError("Invalid upstream initialization SSE")
            raw = events[0].encode()
        elif content_type != "application/json":
            raise PolicyError("Invalid upstream initialization response type")
        result = validate_reply(initial, strict_json_loads(raw))
        if "error" in result:
            raise PolicyError("Upstream initialization rejected")
        info = result["result"]
        if (not isinstance(info, dict)
                or info.get("protocolVersion") not in SUPPORTED_PROTOCOL_VERSIONS
                or not isinstance(info.get("capabilities"), dict)
                or not isinstance(info.get("serverInfo"), dict)):
            raise PolicyError("Invalid upstream initialization data")
        session = response.headers.get("Mcp-Session-Id")
        if session:
            session = validate_mcp_header(session)
    if session:
        headers["Mcp-Session-Id"] = session
    headers["MCP-Protocol-Version"] = "2025-06-18"
    notification = {"jsonrpc": "2.0", "method": "notifications/initialized"}
    req = urllib.request.Request(upstream_url, data=json.dumps(notification).encode(),
                                 headers=headers)
    with UPSTREAM_OPENER.open(req, timeout=12) as response:
        if response.status not in (200, 202, 204):
            raise PolicyError("Upstream initialization acknowledgment failed")
        response.read(MAX_BODY + 1)
    return session




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

    def file_tool_error(self, request_id, message):
        return self.reply(200, {"jsonrpc": "2.0", "id": request_id,
                                "result": {"content": [{"type": "text", "text": message}],
                                           "isError": True}})

    def do_POST(self):
        # The official MCP SDK sends an Origin header even for a local HTTP
        # client. Accept only a syntactically valid, same-authority Origin.
        # Never reflect an arbitrary Origin or add permissive CORS headers.
        origins = self.headers.get_all("Origin", [])
        hosts = self.headers.get_all("Host", [])
        if len(origins) > 1 or len(hosts) != 1:
            return self.reply(403, {"error": "Invalid request origin"})
        if origins:
            try:
                parsed = urllib.parse.urlsplit(origins[0])
                host = hosts[0]
                valid = (
                    parsed.scheme in ("http", "https")
                    and parsed.netloc
                    and parsed.hostname
                    and parsed.username is None
                    and parsed.password is None
                    and not parsed.path and not parsed.query and not parsed.fragment
                    and parsed.netloc.lower() == host.lower()
                    and (parsed.scheme == "https" or parsed.hostname in ("localhost", "127.0.0.1", "::1"))
                )
            except ValueError:
                valid = False
            if not valid:
                return self.reply(403, {"error": "Origin is not permitted"})
        if self.path not in ("/", "/mcp"):
            return self.reply(404, {"error": "Not found"})
        if len(self.headers.get_all("Authorization", [])) != 1:
            return self.reply(401, {"error": "Unauthorized"})
        authorization = self.headers.get("Authorization", "")
        if not hmac.compare_digest(authorization, "Bearer " + self.token):
            return self.reply(401, {"error": "Unauthorized"})
        try:
            for header in ("Content-Length", "Content-Type", "Accept", "Mcp-Session-Id", "MCP-Protocol-Version"):
                if len(self.headers.get_all(header, [])) > 1:
                    return self.reply(400, {"error": "Duplicate HTTP header"})
            # This gateway only returns JSON to MCP clients. Do not send a
            # representation the client explicitly refuses.
            accept = self.headers.get("Accept", "*/*")
            # Honor explicit q=0 refusals, including wildcard overrides.
            qualities = {}
            for item in accept.split(","):
                segments = [part.strip().lower() for part in item.split(";")]
                media = segments[0]
                if not media:
                    continue
                quality = 1.0
                for parameter in segments[1:]:
                    if parameter.startswith("q="):
                        try:
                            quality = float(parameter[2:])
                        except ValueError:
                            quality = 0.0
                        if not 0.0 <= quality <= 1.0:
                            quality = 0.0
                qualities[media] = max(qualities.get(media, 0.0), quality)
            json_quality = next((qualities[media] for media in
                                 ("application/json", "application/*", "*/*")
                                 if media in qualities), 0.0)
            if json_quality <= 0:
                return self.reply(406, {"error": "MCP gateway requires JSON response acceptance"})
            content_type = self.headers.get("Content-Type", "").split(";", 1)[0].strip().lower()
            if content_type != "application/json":
                return self.reply(415, {"error": "MCP POST requires application/json"})
            length = int(self.headers.get("Content-Length", "-1"))
            if not 0 <= length <= MAX_BODY:
                return self.reply(413, {"error": "Invalid request size"})
            message = strict_json_loads(self.rfile.read(length))
            method = check_message(message, self.allowed)
            protocol_version = self.headers.get("MCP-Protocol-Version")
            permitted_versions = (CLIENT_INITIALIZE_VERSIONS if method == "initialize"
                                  else SUPPORTED_PROTOCOL_VERSIONS | {MODERN_PROTOCOL})
            if protocol_version and protocol_version not in permitted_versions:
                return self.reply(400, {"error": "Unsupported MCP protocol version"})
            if method == "initialize" and protocol_version and protocol_version != message["params"]["protocolVersion"]:
                return self.reply(400, {"error": "MCP protocol version header does not match initialize request"})
            if method == "server/discover":
                if protocol_version and protocol_version != MODERN_PROTOCOL:
                    return self.reply(400, {"error": "Discovery protocol version mismatch"})
                return self.reply(200, modern_discovery(message))
            is_modern = modern_request(message)
            if is_modern and protocol_version and protocol_version != MODERN_PROTOCOL:
                return self.reply(400, {"error": "Modern protocol version mismatch"})
            # Validate session/protocol headers before any local file-tool dispatch.
            # Local tools do not traverse the upstream forwarding path.
            validated_headers = {}
            for key in FORWARD_HEADERS:
                value = self.headers.get(key)
                if value:
                    validated_headers[key] = validate_mcp_header(value)
            if method == "tools/call" and message["params"]["name"] == PRIVACY_SAFE_TEMPERATURE_STORE:
                result = public_temperature_store(os.environ["MOONRAKER_URL"],
                                                  os.environ.get("MOONRAKER_API_KEY", ""))
                output = {"content": [{"type": "text",
                                       "text": json.dumps(result, ensure_ascii=False)}],
                          "isError": False}
                if is_modern:
                    output["resultType"] = "complete"
                return self.reply(200, {"jsonrpc": "2.0", "id": message["id"], "result": output})
            if method == "tools/call" and message["params"]["name"] == PRIVACY_SAFE_SERVER_INFO:
                result = public_server_info(os.environ["MOONRAKER_URL"],
                                            os.environ.get("MOONRAKER_API_KEY", ""))
                output = {"content": [{"type": "text",
                                       "text": json.dumps(result, ensure_ascii=False)}],
                          "isError": False}
                if is_modern:
                    output["resultType"] = "complete"
                return self.reply(200, {"jsonrpc": "2.0", "id": message["id"], "result": output})
            if method == "tools/call" and message["params"]["name"] == PRIVACY_SAFE_PRINTER_INFO:
                result = public_printer_info(os.environ["MOONRAKER_URL"],
                                             os.environ.get("MOONRAKER_API_KEY", ""))
                output = {"content": [{"type": "text",
                                       "text": json.dumps(result, ensure_ascii=False)}],
                          "isError": False}
                if is_modern:
                    output["resultType"] = "complete"
                return self.reply(200, {"jsonrpc": "2.0", "id": message["id"], "result": output})
            if method == "tools/call" and message["params"]["name"] == LOCAL_STATUS_TOOL:
                result = connection_status(os.environ["MOONRAKER_URL"],
                                           os.environ.get("MOONRAKER_API_KEY", ""))
                response_result = {"content": [{"type": "text",
                                                "text": json.dumps(result, ensure_ascii=False)}],
                                   "isError": False}
                if is_modern:
                    response_result["resultType"] = "complete"
                return self.reply(200, {"jsonrpc": "2.0", "id": message["id"],
                                        "result": response_result})
            if method == "tools/call" and message["params"]["name"] in LOCAL_FILE_TOOLS:
                name = message["params"]["name"]
                args = message["params"].get("arguments", {})
                try:
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
                except urllib.error.HTTPError as exc:
                    error_text = ("Moonraker file not found" if exc.code == 404
                                  else "Moonraker file service unavailable")
                    return self.file_tool_error(message["id"], error_text)
                except (urllib.error.URLError, TimeoutError):
                    return self.file_tool_error(message["id"], "Moonraker file service unavailable")
                file_result = {"content": [{"type": "text",
                                            "text": json.dumps(result, ensure_ascii=False)}],
                               "isError": False}
                if is_modern:
                    file_result["resultType"] = "complete"
                return self.reply(200, {"jsonrpc": "2.0", "id": message["id"],
                                        "result": file_result})
            headers = {
                "Authorization": "Bearer " + self.token,
                "Content-Type": "application/json",
                "Accept": "application/json, text/event-stream",
            }
            headers.update(validated_headers)
            upstream_message = message
            if is_modern:
                # Translate modern stateless request metadata to the pinned
                # legacy upstream. Preserve method and arguments, never widen
                # the allowlist or forward untrusted metadata.
                upstream_message = dict(message, params={
                    key: value for key, value in message.get("params", {}).items()
                    if key != "_meta"
                })
                headers.pop("MCP-Protocol-Version", None)
                headers.pop("Mcp-Session-Id", None)
            if method == "initialize" and message["params"]["protocolVersion"] == "2025-11-25":
                upstream_message = dict(message, params=dict(
                    message["params"], protocolVersion="2025-06-18"))
                if "MCP-Protocol-Version" in headers:
                    headers["MCP-Protocol-Version"] = "2025-06-18"
            try:
                if is_modern and method in ("tools/list", "tools/call", "ping"):
                    # A fresh legacy session for each modern stateless request.
                    # The upstream refuses tools/list before initialization.
                    local_session = initialize_legacy_upstream(self.upstream, self.token)
                    if local_session:
                        headers["Mcp-Session-Id"] = local_session
                    headers["MCP-Protocol-Version"] = "2025-06-18"
                req = urllib.request.Request(
                    self.upstream, data=json.dumps(upstream_message).encode(), headers=headers
                )
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
                    media_type = content_type.split(";", 1)[0].strip().lower()
                    if media_type == "text/event-stream":
                        # The pinned upstream emits standard SSE event/id fields.
                        # Permit them while requiring exactly one JSON-RPC data line.
                        lines = raw.decode("utf-8").splitlines()
                        events = [line[5:].lstrip(" ") for line in lines
                                  if line.startswith("data:")]
                        if (len(events) != 1 or
                                any(line and not line.startswith(("data:", "event:", "id:", "retry:", ":"))
                                    for line in lines)):
                            raise PolicyError("Unsupported upstream SSE response")
                        raw = events[0].encode("utf-8")
                    elif media_type != "application/json":
                        raise PolicyError("Unsupported upstream content type")
                    parsed = filter_reply(method, validate_reply(message, strict_json_loads(raw)), self.allowed,
                                          message.get("params", {}).get("cursor") if method == "tools/list" else None)
                    extra = {}
                    session = upstream.headers.get("Mcp-Session-Id")
                    if session:
                        extra["Mcp-Session-Id"] = validate_mcp_header(session)
                    if is_modern and "result" in parsed and method in ("tools/list", "tools/call"):
                        parsed = dict(parsed, result=dict(parsed["result"], resultType="complete"))
                        extra.pop("Mcp-Session-Id", None)
                    return self.reply(200, parsed, extra)
            except (urllib.error.URLError, TimeoutError):
                return self.reply(502, {"error": "Upstream unavailable"})
            except urllib.error.HTTPError as exc:
                return self.reply(502, {"error": "Upstream MCP error", "status": exc.code})
            except (PolicyError, ValueError, TypeError, UnicodeError):
                # Invalid upstream protocol data is a gateway failure, not a client denial.
                return self.reply(502, {"error": "Invalid upstream MCP response"})
        except urllib.error.HTTPError as exc:
            # File API errors must not reveal Moonraker URLs, API keys or bodies.
            if exc.code == 404:
                return self.reply(404, {"error": "Moonraker file not found"})
            return self.reply(502, {"error": "Moonraker file service unavailable"})
        except (urllib.error.URLError, TimeoutError):
            return self.reply(502, {"error": "Moonraker file service unavailable"})
        except (PolicyError, FileAccessError, ValueError, TypeError, UnicodeError) as exc:
            return self.reply(403, {"error": str(exc)})
        except Exception:
            self.log_error("MCP upstream communication failed")
            return self.reply(502, {"error": "Upstream unavailable"})

    def reject_unsupported_method(self):
        authorization = self.headers.get_all("Authorization", [])
        if len(authorization) != 1 or not hmac.compare_digest(
                authorization[0], "Bearer " + self.token):
            return self.reply(401, {"error": "Unauthorized"})
        return self.reply(405, {"error": "Only POST is supported"},
                          {"Allow": "POST"})

    def do_OPTIONS(self):
        self.reject_unsupported_method()

    def do_PUT(self):
        self.reject_unsupported_method()

    def do_PATCH(self):
        self.reject_unsupported_method()


    def do_HEAD(self):
        # A HEAD response must never include a body.
        authorization = self.headers.get_all("Authorization", [])
        authorized = (len(authorization) == 1 and hmac.compare_digest(
            authorization[0], "Bearer " + self.token))
        self.send_response(405 if authorized else 401)
        self.send_header("Content-Length", "0")
        self.send_header("Cache-Control", "no-store")
        if authorized:
            self.send_header("Allow", "POST")
        self.end_headers()

    def do_GET(self):
        self.reject_unsupported_method()

    def do_DELETE(self):
        self.reject_unsupported_method()


if __name__ == "__main__":
    Handler.allowed = extend_allowed(load_allowed(), json.loads(os.environ.get("MCP_ALLOWED_PROFILES", "[]")))
    Handler.token = os.environ["MCP_HTTP_TOKEN"]
    if not Handler.token:
        raise SystemExit("MCP_HTTP_TOKEN must not be empty")
    ThreadingHTTPServer(("0.0.0.0", 8765), Handler).serve_forever()
