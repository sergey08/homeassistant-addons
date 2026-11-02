"""Read-only encrypted LiveSync parent snapshot validation.

For future CAS use: keep the stored ciphertext, CouchDB _id and _rev
unaltered. This module neither creates writes nor guesses parent IDs.
"""
from livesync_metadata import validate_encrypted_parent, UnsupportedMetadata
from livesync_revision_contract import require_matching_revision, RevisionConflict
from livesync_write_preflight import UnsafeWrite


def validate_encrypted_parent_snapshot(stored, decrypted, requested_path,
                                       expected_revision):
    if not isinstance(stored, dict) or not isinstance(decrypted, dict):
        raise UnsafeWrite("invalid_parent_snapshot")
    if stored.get("type") not in ("plain", "newnote"):
        raise UnsafeWrite("unsupported_parent_type")
    doc_id = stored.get("_id")
    if not isinstance(doc_id, str) or not doc_id or len(doc_id) > 1024:
        raise UnsafeWrite("invalid_parent_id")
    encrypted_path = stored.get("path")
    if not isinstance(encrypted_path, str) or not encrypted_path.startswith("/\\:%="):
        raise UnsafeWrite("unencrypted_parent_not_supported")
    if stored.get("_deleted") or stored.get("deleted") or stored.get("_conflicts"):
        raise UnsafeWrite("deleted_or_conflicted_parent")
    try:
        revision = require_matching_revision(expected_revision, stored.get("_rev"))
        children = validate_encrypted_parent(decrypted, requested_path)
    except (RevisionConflict, UnsupportedMetadata) as exc:
        raise UnsafeWrite("invalid_encrypted_snapshot") from exc
    if stored.get("data") is not None:
        raise UnsafeWrite("unexpected_parent_data")
    return {"_id":doc_id, "_rev":revision, "encrypted_path":encrypted_path,
            "path":requested_path, "children":children,
            "write_supported":False}
