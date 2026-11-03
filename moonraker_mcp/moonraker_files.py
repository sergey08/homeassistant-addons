"""Read-only Moonraker file API helpers used by the MCP gateway.

Moonraker API: GET /server/files/list and /server/files/metadata.
Only G-code listing and metadata are supported in this first stage.
"""
import json
import urllib.parse
import urllib.request

MAX_RESPONSE_BYTES = 1024 * 1024
ALLOWED_ROOTS = frozenset(("gcodes",))


class FileAccessError(ValueError):
    pass


def validate_root(root):
    if not isinstance(root, str) or root not in ALLOWED_ROOTS:
        raise FileAccessError("File root is not permitted")
    return root


def validate_filename(filename):
    if not isinstance(filename, str) or not filename or len(filename) > 512:
        raise FileAccessError("Invalid filename")
    if filename.startswith(("/", "\\")) or "\\" in filename or "\x00" in filename:
        raise FileAccessError("Invalid filename")
    # Reject percent escapes to prevent ambiguous double-decoding by proxies.
    if "%" in filename:
        raise FileAccessError("Percent-encoded filenames are not permitted")
    if any(part in ("", ".", "..") for part in filename.split("/")):
        raise FileAccessError("Invalid filename")
    if any(ord(char) < 32 or ord(char) == 127 for char in filename):
        raise FileAccessError("Invalid filename")
    return filename


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    """Do not forward Moonraker credentials to a redirect destination."""
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise FileAccessError("Moonraker redirect refused")


def validate_base_url(base_url):
    """Require a fixed Moonraker origin; never accept embedded credentials or paths."""
    if not isinstance(base_url, str):
        raise FileAccessError("Invalid Moonraker base URL")
    parsed = urllib.parse.urlsplit(base_url)
    if (parsed.scheme not in ("http", "https") or not parsed.hostname
            or parsed.username or parsed.password or parsed.query or parsed.fragment
            or parsed.path not in ("", "/")):
        raise FileAccessError("Invalid Moonraker base URL")
    try:
        parsed.port
    except ValueError as exc:
        raise FileAccessError("Invalid Moonraker port") from exc
    return base_url.rstrip("/")


def _read_json(url, api_key="", opener=None):
    parsed = urllib.parse.urlsplit(url)
    if parsed.scheme not in ("http", "https") or not parsed.hostname or parsed.username or parsed.password:
        raise FileAccessError("Invalid Moonraker URL")
    headers = {"Accept": "application/json"}
    if api_key:
        headers["X-Api-Key"] = api_key
    req = urllib.request.Request(url, headers=headers, method="GET")
    if opener is None:
        opener = urllib.request.build_opener(_NoRedirect()).open
    with opener(req, timeout=10) as response:
        raw = response.read(MAX_RESPONSE_BYTES + 1)
    if len(raw) > MAX_RESPONSE_BYTES:
        raise FileAccessError("Moonraker response too large")
    try:
        data = json.loads(raw)
    except (ValueError, UnicodeError) as exc:
        raise FileAccessError("Invalid Moonraker JSON response") from exc
    if not isinstance(data, dict) or "result" not in data:
        raise FileAccessError("Unexpected Moonraker response")
    return data["result"]


def list_gcodes(base_url, api_key="", opener=None):
    url = validate_base_url(base_url) + "/server/files/list?" + urllib.parse.urlencode({"root": validate_root("gcodes")})
    return _read_json(url, api_key, opener)


def gcode_metadata(base_url, filename, api_key="", opener=None):
    filename = validate_filename(filename)
    url = validate_base_url(base_url) + "/server/files/metadata?" + urllib.parse.urlencode({"filename": filename})
    return _read_json(url, api_key, opener)


MAX_GCODE_PREVIEW_BYTES = 16 * 1024


def gcode_preview(base_url, filename, api_key="", opener=None):
    """Return a bounded UTF-8 prefix of a G-code file, never config files.

    Moonraker serves raw files at GET /server/files/gcodes/<relative-path>.
    This intentionally does not support arbitrary roots or full downloads.
    """
    filename = validate_filename(filename)
    if not filename.lower().endswith((".gcode", ".gco")):
        raise FileAccessError("Only G-code previews are permitted")
    base_url = validate_base_url(base_url)
    encoded = "/".join(urllib.parse.quote(part, safe="") for part in filename.split("/"))
    url = base_url.rstrip("/") + "/server/files/gcodes/" + encoded
    headers = {"Accept": "application/octet-stream", "Range": f"bytes=0-{MAX_GCODE_PREVIEW_BYTES - 1}"}
    if api_key:
        headers["X-Api-Key"] = api_key
    req = urllib.request.Request(url, headers=headers, method="GET")
    if opener is None:
        opener = urllib.request.build_opener(_NoRedirect()).open
    with opener(req, timeout=10) as response:
        raw = response.read(MAX_GCODE_PREVIEW_BYTES + 1)
    if len(raw) > MAX_GCODE_PREVIEW_BYTES:
        raise FileAccessError("G-code preview exceeds maximum size")
    if b"\x00" in raw:
        raise FileAccessError("Binary content is not permitted")
    return {"filename": filename, "preview": raw.decode("utf-8", errors="replace"),
            "max_bytes": MAX_GCODE_PREVIEW_BYTES}
