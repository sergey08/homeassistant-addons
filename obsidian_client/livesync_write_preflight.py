"""Conservative, side-effect-free LiveSync write preflight.

No network requests or persistence. A candidate is rejected unless all basic
integrity constraints are satisfied. This does not establish wire compatibility.
"""
import hashlib
import re

MAX_NOTE_BYTES = 2_000_000
MAX_PATH_LENGTH = 1024

class UnsafeWrite(ValueError):
    pass

def validate_write_request(path, content, expected_revision, *, creating=False):
    if not isinstance(path, str) or len(path) > MAX_PATH_LENGTH or not path.endswith(".md"):
        raise UnsafeWrite("invalid_path")
    if path.startswith("/") or "\\" in path or any(ord(ch) < 32 or ord(ch) == 127 for ch in path):
        raise UnsafeWrite("invalid_path")
    if any(part in ("", ".", "..") or part.startswith(".") or part.endswith((" ", ".")) for part in path.split("/")):
        raise UnsafeWrite("invalid_path")
    if not isinstance(content, str):
        raise UnsafeWrite("invalid_content")
    encoded = content.encode("utf-8")
    if len(encoded) > MAX_NOTE_BYTES:
        raise UnsafeWrite("content_too_large")
    if creating:
        if expected_revision is not None:
            raise UnsafeWrite("unexpected_revision")
    elif not isinstance(expected_revision, str) or not re.fullmatch(r"[1-9][0-9]*-[0-9a-fA-F]{32}", expected_revision):
        raise UnsafeWrite("revision_required")
    return {"path": path, "bytes": len(encoded),
            "sha256": hashlib.sha256(encoded).hexdigest(),
            "operation": "create" if creating else "update"}
