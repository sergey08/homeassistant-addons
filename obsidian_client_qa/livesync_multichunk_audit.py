"""Pure, bounded and read-only audit of encrypted LiveSync chunk snapshots.

A missing current reference is NOT evidence that deletion is safe: old
revisions, concurrent replication and other clients may still need a leaf.
This module never contacts CouchDB, writes data, or suggests automatic GC.
"""
from livesync_crypto import decrypt_hkdf_string, UnsupportedEncryption
from livesync_encrypted_metadata_fixture import decode_parent_metadata_fixture
from livesync_encrypted_parent_snapshot import validate_encrypted_parent_snapshot
from livesync_write_preflight import UnsafeWrite

MAX_CHUNKS = 512
MAX_NOTE_BYTES = 2_000_000
MAX_DOCS = 2000


class ChunkAuditError(ValueError):
    pass


def assemble_encrypted_chunks(stored_parent, leaf_docs, requested_path,
                              expected_revision, passphrase, salt_b64):
    """Validate current parent and decrypt ordered leaves; no writes."""
    if not isinstance(leaf_docs, dict) or len(leaf_docs) > MAX_CHUNKS:
        raise ChunkAuditError("invalid_leaf_snapshot")
    try:
        metadata = decode_parent_metadata_fixture(
            stored_parent.get("path"), passphrase, salt_b64)
        parent = validate_encrypted_parent_snapshot(
            stored_parent, metadata, requested_path, expected_revision)
    except (UnsafeWrite, UnsupportedEncryption, ValueError, TypeError, AttributeError) as exc:
        raise ChunkAuditError("invalid_parent_snapshot") from exc
    children = parent["children"]
    if len(children) > MAX_CHUNKS or any(
            not isinstance(cid, str) or not cid.startswith("h:+")
            for cid in children):
        raise ChunkAuditError("unsupported_chunk_identity")
    parts = []
    total = 0
    for cid in children:
        leaf = leaf_docs.get(cid)
        if (not isinstance(leaf, dict) or leaf.get("_id") != cid
                or leaf.get("type") != "leaf" or leaf.get("e_") is not True
                or leaf.get("_deleted") or leaf.get("_conflicts")
                or leaf.get("_attachments") is not None):
            raise ChunkAuditError("missing_or_invalid_leaf")
        try:
            content = decrypt_hkdf_string(leaf.get("data"), passphrase, salt_b64)
        except (UnsupportedEncryption, ValueError, TypeError) as exc:
            raise ChunkAuditError("unverified_leaf") from exc
        total += len(content.encode("utf-8"))
        if total > MAX_NOTE_BYTES:
            raise ChunkAuditError("note_too_large")
        parts.append(content)
    if metadata.get("size") != total:
        raise ChunkAuditError("byte_count_mismatch")
    return {"content": "".join(parts), "bytes": total, "chunks": len(children),
            "remote_write_enabled": False, "write_supported": False}


def audit_unreferenced_leaves(leaf_docs, current_parent_references, *,
                              complete_snapshot=False):
    """Identify only candidates for human review, never deletion eligibility.

    The caller must supply ALL relevant current parent references; this does
    not inspect historical CouchDB revisions or concurrent clients.
    """
    if complete_snapshot is not True:
        raise ChunkAuditError("complete_snapshot_required")
    if (not isinstance(leaf_docs, dict) or len(leaf_docs) > MAX_DOCS
            or not isinstance(current_parent_references, (set, tuple, list))
            or len(current_parent_references) > MAX_DOCS * MAX_CHUNKS):
        raise ChunkAuditError("snapshot_too_large_or_invalid")
    referenced = set(current_parent_references)
    if any(not isinstance(x, str) or not x.startswith("h:+") for x in referenced):
        raise ChunkAuditError("invalid_parent_reference")
    candidates = []
    for key, leaf in leaf_docs.items():
        if (not isinstance(key, str) or not key.startswith("h:+")
                or not isinstance(leaf, dict) or leaf.get("_id") != key
                or leaf.get("type") != "leaf" or leaf.get("e_") is not True
                or leaf.get("_deleted") or leaf.get("_conflicts")):
            raise ChunkAuditError("invalid_leaf_document")
        if key not in referenced:
            candidates.append(key)
    return {"unreferenced_current_count": len(candidates),
            "candidate_ids": sorted(candidates),
            "safe_to_delete": False,
            "delete_supported": False,
            "requires_historical_revision_and_replication_review": True,
            "remote_write_enabled": False}
