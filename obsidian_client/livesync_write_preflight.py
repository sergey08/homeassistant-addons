"""Conservative, side-effect-free LiveSync write preflight.

No network requests or persistence. A candidate is rejected unless all basic
integrity constraints are satisfied. This does not establish wire compatibility.
"""
import hashlib
import re
import unicodedata

MAX_NOTE_BYTES = 2_000_000
MAX_PATH_LENGTH = 1024

class UnsafeWrite(ValueError):
    pass

def validate_write_request(path, content, expected_revision, *, creating=False):
    if not isinstance(path, str) or len(path) > MAX_PATH_LENGTH or not path.endswith(".md"):
        raise UnsafeWrite("invalid_path")
    if path.startswith("/") or "\\" in path or any(ord(ch) < 32 or ord(ch) == 127 for ch in path):
        raise UnsafeWrite("invalid_path")
    if unicodedata.normalize("NFC", path) != path or any(unicodedata.category(ch) in ("Cf", "Cs") for ch in path):
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


def validate_update_snapshot(path, proposed_content, expected_revision,
                             current_revision, expected_content_sha256,
                             current_content):
    """Offline optimistic-concurrency guard; never writes or contacts CouchDB.

    The caller must obtain both current_revision and current_content from a
    fresh, authoritative snapshot. This function alone does not make a remote
    write safe: the final CouchDB write must use compare-and-swap via _rev.
    """
    candidate = validate_write_request(path, proposed_content, expected_revision)
    if not isinstance(current_revision, str) or not re.fullmatch(
            r"[1-9][0-9]*-[0-9a-fA-F]{32}", current_revision):
        raise UnsafeWrite("current_revision_invalid")
    if not isinstance(expected_content_sha256, str) or not re.fullmatch(
            r"[0-9a-f]{64}", expected_content_sha256):
        raise UnsafeWrite("expected_hash_invalid")
    if not isinstance(current_content, str):
        raise UnsafeWrite("current_content_invalid")
    if expected_revision != current_revision:
        raise UnsafeWrite("revision_conflict")
    digest = hashlib.sha256(current_content.encode("utf-8")).hexdigest()
    if digest != expected_content_sha256:
        raise UnsafeWrite("content_conflict")
    return candidate
