"""Read-only, fail-closed inspection after interrupted isolated multi-chunk CAS.

Compares an observed CouchDB parent and all candidate leaves with the original
encrypted plan. Never retries, deletes documents, or authorizes a new commit.
No network client here; injected readers are allowed ONLY in disposable tests.
"""
from livesync_encrypted_metadata_fixture import decode_parent_metadata_fixture
from livesync_revision_contract import require_matching_revision
from livesync_write_preflight import UnsafeWrite

MAX_LEAVES = 512


def inspect_interrupted_multichunk(plan, read_document, passphrase, salt_b64, *,
                                   isolated_test=False, remote_writes_enabled=False):
    if isolated_test is not True or remote_writes_enabled is not False:
        raise UnsafeWrite("isolated_inspection_only")
    if not callable(read_document) or not isinstance(plan, dict) or plan.get("write_supported") is not False:
        raise UnsafeWrite("untrusted_inspection")
    parent = plan.get("parent")
    leaves = plan.get("leaves")
    expected_revision = plan.get("expected_parent_revision")
    path = plan.get("path")
    if (not isinstance(parent, dict) or not isinstance(leaves, list)
            or not 2 <= len(leaves) <= MAX_LEAVES or not isinstance(path, str)):
        raise UnsafeWrite("invalid_inspection_plan")
    require_matching_revision(expected_revision, parent.get("_rev"))
    ids = [leaf.get("_id") if isinstance(leaf, dict) else None for leaf in leaves]
    if (any(not isinstance(x, str) or not x.startswith("h:+") for x in ids)
            or len(set(ids)) != len(ids)
            or any(not isinstance(leaf.get("data"), str) for leaf in leaves)):
        raise UnsafeWrite("invalid_leaf_reference")
    try:
        expected_meta = decode_parent_metadata_fixture(parent["path"], passphrase, salt_b64)
    except Exception as exc:
        raise UnsafeWrite("invalid_expected_metadata") from exc
    if expected_meta.get("path") != path or expected_meta.get("children") != ids:
        raise UnsafeWrite("expected_parent_leaf_mismatch")

    # Read parent first and last. If it changes during inspection, nothing is
    # classified as complete; concurrent replication may still be occurring.
    try:
        before = read_document(parent["_id"])
        actual = [read_document(ident) for ident in ids]
        after = read_document(parent["_id"])
    except Exception:
        return _report("unknown", "snapshot_unavailable", [], len(leaves))
    if (not isinstance(before, dict) or not isinstance(after, dict)
            or before != after or before.get("_id") != parent["_id"]):
        return _report("unknown", "concurrent_or_incomplete_parent_read", [], len(leaves))

    states = []
    for ident, expected, observed in zip(ids, leaves, actual):
        if observed is None:
            states.append("missing")
        elif (not isinstance(observed, dict)
              or observed.get("_id") != ident
              or observed.get("type") != "leaf"
              or observed.get("e_") is not True
              or observed.get("_deleted") or observed.get("_conflicts")
              or observed.get("data") != expected["data"]):
            states.append("mismatch")
        else:
            states.append("verified")
    if (before.get("_deleted") or before.get("deleted") or before.get("_conflicts")
            or before.get("type") != "plain"):
        return _report("unknown", "conflicted_or_deleted_parent", states, len(leaves))

    try:
        observed_meta = decode_parent_metadata_fixture(before["path"], passphrase, salt_b64)
    except Exception:
        return _report("unknown", "parent_metadata_not_verified", states, len(leaves))
    if observed_meta.get("path") != path:
        return _report("unknown", "parent_path_changed", states, len(leaves))

    # Ciphertext and decrypted metadata must BOTH match the intended plan.
    if (before.get("path") == parent.get("path")
            and observed_meta == expected_meta
            and before.get("_rev") != expected_revision):
        # Acknowledgement may be missing, but complete current references are
        # proven only after all newly created leaves are read back exactly.
        if all(s == "verified" for s in states):
            return _report("committed", "parent_references_verified_leaves",
                           states, len(leaves))
        return _report("unknown", "parent_points_to_unverified_leaves",
                       states, len(leaves))

    if before.get("_rev") == expected_revision:
        # The parent was not visibly updated. Leaves could be orphaned,
        # referenced by historical revisions, or still in replication.
        if before.get("path") == parent.get("path"):
            return _report("unknown", "revision_did_not_advance", states, len(leaves))
        return _report("not_committed", "old_parent_revision_remains",
                       states, len(leaves))
    return _report("conflict", "parent_changed_to_other_revision",
                   states, len(leaves))


def _report(state, reason, states, count):
    return {
        "state": state, "reason": reason,
        "confirmed_leaves": sum(s == "verified" for s in states),
        "missing_leaves": sum(s == "missing" for s in states),
        "mismatched_leaves": sum(s == "mismatch" for s in states),
        "expected_leaf_count": count,
        "automatic_retry": False, "automatic_cleanup": False,
        "safe_to_delete": False, "remote_writes_enabled": False,
        "resolution": "manual_review_required",
    }
