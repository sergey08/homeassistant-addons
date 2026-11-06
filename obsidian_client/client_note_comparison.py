"""Read-only comparison of a private Markdown copy and a verified LiveSync note.

The comparison is not a three-way merge: without a shared baseline,
different hashes indicate divergence but not which side changed.
"""
from hashlib import sha256


def compare_note_contents(remote_content, local_content):
    if not isinstance(remote_content, str):
        raise ValueError("invalid_remote_content")
    if local_content is not None and not isinstance(local_content, str):
        raise ValueError("invalid_local_content")
    remote_hash = sha256(remote_content.encode("utf-8")).hexdigest()
    if local_content is None:
        return {"state": "remote_only", "local_exists": False,
                "identical": False, "remote_sha256": remote_hash,
                "local_sha256": None, "safe_to_auto_merge": False}
    local_hash = sha256(local_content.encode("utf-8")).hexdigest()
    same = remote_hash == local_hash
    return {"state": "identical" if same else "diverged_unknown_origin",
            "local_exists": True, "identical": same,
            "remote_sha256": remote_hash, "local_sha256": local_hash,
            "safe_to_auto_merge": same}
