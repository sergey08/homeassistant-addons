"""Isolated-only encrypted snapshot backup and fail-closed restoration preflight.

No network connections, filesystem writes or remote restore implementation.
The sealed manifest retains original ciphertext (not plaintext) plus SHA-256
digest of a canonical detached snapshot. Hashes detect accidental corruption
but do NOT authenticate who created a manifest: use trusted storage/permissions.
"""
import hashlib
import hmac
import json
from copy import deepcopy

from livesync_multichunk_audit import assemble_encrypted_chunks, ChunkAuditError
from livesync_encrypted_metadata_fixture import decode_parent_metadata_fixture
from livesync_write_preflight import UnsafeWrite
from livesync_revision_contract import require_matching_revision, RevisionConflict

MAX_BACKUP_BYTES = 3_000_000


class BackupRejected(ValueError):
    pass


def _canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":"), allow_nan=False).encode("utf-8")


def _checksum(value):
    return hashlib.sha256(_canonical(value)).hexdigest()


def create_verified_snapshot(parent, leaves, path, expected_revision,
                             passphrase, salt_b64, *, isolated_test=False,
                             remote_writes_enabled=False):
    """Return detached, validated encrypted backup, never writing files or DB."""
    if isolated_test is not True or remote_writes_enabled is not False:
        raise UnsafeWrite("isolated_backup_only")
    if not isinstance(parent, dict) or not isinstance(leaves, dict):
        raise BackupRejected("invalid_snapshot")
    parent, leaves = deepcopy(parent), deepcopy(leaves)
    try:
        result = assemble_encrypted_chunks(parent, leaves, path,
                                           expected_revision, passphrase, salt_b64)
        metadata = decode_parent_metadata_fixture(parent.get("path"),
                                                  passphrase, salt_b64)
        ids = metadata.get("children")
        if set(leaves) != set(ids):
            raise BackupRejected("unexpected_or_missing_leaves")
        if (parent.get("_attachments") is not None or parent.get("_conflicts")
                or parent.get("_deleted") or parent.get("deleted")):
            raise BackupRejected("unsupported_parent_state")
        if any(not isinstance(leaves[x].get("_rev"), str)
               or leaves[x].get("_attachments") is not None
               for x in ids):
            raise BackupRejected("unverified_leaf_revision")
        for child_id in ids:
            # Read-back validation requires CouchDB revisions on every leaf.
            require_matching_revision(leaves[child_id]["_rev"],
                                      leaves[child_id]["_rev"])
        snapshot = {"parent": parent, "leaves": [leaves[x] for x in ids],
                    "path": path, "parent_revision": expected_revision}
        if len(_canonical(snapshot)) > MAX_BACKUP_BYTES:
            raise BackupRejected("backup_too_large")
        sealed = {"schema": 1, "kind": "isolated_encrypted_snapshot",
                  "snapshot": snapshot, "sha256": _checksum(snapshot)}
        return {"backup": sealed, "verified_chunks": result["chunks"],
                "verified_bytes": result["bytes"], "remote_writes_enabled": False,
                "restore_enabled": False}
    except (ChunkAuditError, RevisionConflict, ValueError, TypeError, KeyError,
            UnicodeError, OverflowError) as exc:
        raise BackupRejected("snapshot_verification_failed") from exc


def preflight_restore_snapshot(backup, current_parent, passphrase, salt_b64, *,
                               isolated_test=False, remote_writes_enabled=False):
    """Validate ciphertext backup before any future manually reviewed restore.

    Current parent MUST still have same revision and identical ciphertext.
    A newer revision is always rejected. This never creates a restore PUT.
    """
    if isolated_test is not True or remote_writes_enabled is not False:
        raise UnsafeWrite("isolated_restore_preflight_only")
    if not isinstance(backup, dict) or set(backup) != {
            "schema", "kind", "snapshot", "sha256"}:
        raise BackupRejected("invalid_backup_format")
    if backup["schema"] != 1 or backup["kind"] != "isolated_encrypted_snapshot":
        raise BackupRejected("unsupported_backup")
    snapshot = backup["snapshot"]
    if (not isinstance(snapshot, dict) or not isinstance(backup["sha256"], str)
            or len(backup["sha256"]) != 64):
        raise BackupRejected("invalid_backup_format")
    try:
        if len(_canonical(snapshot)) > MAX_BACKUP_BYTES:
            raise BackupRejected("backup_too_large")
        if not hmac.compare_digest(_checksum(snapshot), backup["sha256"]):
            raise BackupRejected("backup_integrity_mismatch")
        parent = snapshot["parent"]
        leaves = snapshot["leaves"]
        if (not isinstance(leaves, list) or not 1 <= len(leaves) <= 512
                or any(not isinstance(x, dict) or not isinstance(x.get("_id"), str)
                       for x in leaves)):
            raise BackupRejected("invalid_backup_leaves")
        leaf_map = {leaf["_id"]: leaf for leaf in leaves}
        if len(leaf_map) != len(leaves):
            raise BackupRejected("duplicate_backup_leaves")
        assemble_encrypted_chunks(parent, leaf_map, snapshot["path"],
                                  snapshot["parent_revision"], passphrase, salt_b64)
        if not isinstance(current_parent, dict):
            raise BackupRejected("current_parent_missing")
        require_matching_revision(snapshot["parent_revision"],
                                  current_parent.get("_rev"))
        if current_parent != parent:
            raise BackupRejected("current_parent_diverged")
    except BackupRejected:
        raise
    except (ChunkAuditError, RevisionConflict, ValueError, TypeError, KeyError,
            UnicodeError, OverflowError) as exc:
        raise BackupRejected("restore_preflight_failed") from exc
    return {"status": "verified_no_change_required", "restore_enabled": False,
            "remote_writes_enabled": False, "automatic_restore": False,
            "parent_revision": snapshot["parent_revision"],
            "verified_chunks": len(leaves),
            "next_step": "manual_review_and_separate_cas_restore_protocol"}
