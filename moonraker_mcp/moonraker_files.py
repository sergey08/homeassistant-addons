"""Read-only Moonraker file API helpers. Not exposed as MCP tools yet.

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
    if any(part in ("", ".", "..") for part in filename.split("/")):
        raise FileAccessError("Invalid filename")
    if any(ord(char) < 32 or ord(char) == 127 for char in filename):
        raise FileAccessError("Invalid filename")
    return filename


def _read_json(url, api_key="", opener=None):
    parsed = urllib.parse.urlsplit(url)
    if parsed.scheme not in ("http", "https") or not parsed.hostname or parsed.username or parsed.password:
        raise FileAccessError("Invalid Moonraker URL")
    headers = {"Accept": "application/json"}
    if api_key:
        headers["X-Api-Key"] = api_key
    req = urllib.request.Request(url, headers=headers, method="GET")
    if opener is None:
        opener = urllib.request.urlopen
    with opener(req, timeout=10) as response:
        raw = response.read(MAX_RESPONSE_BYTES + 1)
    if len(raw) > MAX_RESPONSE_BYTES:
        raise FileAccessError("Moonraker response too large")
    data = json.loads(raw)
    if not isinstance(data, dict) or "result" not in data:
        raise FileAccessError("Unexpected Moonraker response")
    return data["result"]


def list_gcodes(base_url, api_key="", opener=None):
    url = base_url.rstrip("/") + "/server/files/list?" + urllib.parse.urlencode({"root": validate_root("gcodes")})
    return _read_json(url, api_key, opener)


def gcode_metadata(base_url, filename, api_key="", opener=None):
    filename = validate_filename(filename)
    url = base_url.rstrip("/") + "/server/files/metadata?" + urllib.parse.urlencode({"filename": filename})
    return _read_json(url, api_key, opener)
