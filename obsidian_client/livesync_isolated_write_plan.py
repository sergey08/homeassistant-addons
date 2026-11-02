"""Side-effect-free construction of a *single-chunk* LiveSync create candidate.

This module does not contact CouchDB or register a remote-write endpoint.
All callers must separately validate remote settings and use create-only
CouchDB semantics. Only the legacy encrypted xxHash64 mode verified in CI
is represented. This is not an interface for production writes.
"""
from livesync_chunk_identity import js_utf16_code_units, legacy_chunk_id
from livesync_crypto import encrypt_hkdf_string
from livesync_write_preflight import validate_write_request, UnsafeWrite

MAX_SINGLE_CHUNK_UNITS = 1000


def prepare_isolated_note_create(path, content, passphrase, pbkdf2_salt_b64,
                                 *, created_millis, remote_writes_enabled=False):
    """Build detached leaf/parent documents; no I/O, no mutation.

    Deliberately fails closed on multiple-chunk notes and production
    remote writes. The target database must be disposable and loopback.
    """
    if remote_writes_enabled is not False:
        raise UnsafeWrite("remote_writes_forbidden_in_isolated_builder")
    validate_write_request(path, content, None, creating=True)
    if not isinstance(created_millis, int) or isinstance(created_millis, bool) or created_millis < 0:
        raise UnsafeWrite("invalid_timestamp")
    if not content or js_utf16_code_units(content) > MAX_SINGLE_CHUNK_UNITS:
        raise UnsafeWrite("unsupported_chunk_count")
    if not isinstance(passphrase, str) or not passphrase:
        raise UnsafeWrite("missing_passphrase")
    parent_id = path.lower()
    leaf_id = "h:" + legacy_chunk_id(content, passphrase)
    leaf = {"_id": leaf_id, "type": "leaf", "e_": True,
            "data": encrypt_hkdf_string(content, passphrase, pbkdf2_salt_b64)}
    parent = {"_id": parent_id, "type": "plain", "path": path,
              "children": [leaf_id], "size": len(content.encode("utf-8")),
              "ctime": created_millis, "mtime": created_millis, "eden": {}}
    return {"leaf": leaf, "parent": parent, "write_order": ("leaf", "parent")}
