"""Strict LiveSync encrypted metadata validator; pure and side-effect free.

Only accepts a narrow observed shape. No assumption that this can encode writes.
"""
from livesync_write_preflight import validate_write_request, UnsafeWrite

class UnsupportedMetadata(ValueError):
    pass

def validate_encrypted_parent(metadata, requested_path):
    if not isinstance(metadata, dict):
        raise UnsupportedMetadata("metadata_not_object")
    if metadata.get("path") != requested_path:
        raise UnsupportedMetadata("path_mismatch")
    try:
        validate_write_request(requested_path, "", None, creating=True)
    except UnsafeWrite:
        raise UnsupportedMetadata("invalid_path") from None
    if metadata.get("deleted") or metadata.get("_deleted") or metadata.get("_conflicts"):
        raise UnsupportedMetadata("deleted_or_conflicted")
    children = metadata.get("children")
    if (not isinstance(children, list) or not children or len(children) > 512
            or any(not isinstance(child, str) or not 0 < len(child) < 256 for child in children)
            or len(set(children)) != len(children)):
        raise UnsupportedMetadata("invalid_children")
    size = metadata.get("size")
    if size is not None and (type(size) is not int or size < 0 or size > 2_000_000):
        raise UnsupportedMetadata("invalid_size")
    return tuple(children)
