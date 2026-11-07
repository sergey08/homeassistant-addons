"""Safe manual synchronization decision; no transport and no note writes.

The decision requires a trusted local baseline and a freshly verified remote
snapshot. It never treats an arbitrary match as proof of common ancestry.
"""
from client_sync_baseline import classify, digest, BaselineError


class SyncBlocked(ValueError):
    pass


def decide_manual_sync(baseline_sha256, remote_content, local_content, *,
                       remote_verified=False, remote_revision=None):
    if remote_verified is not True:
        raise SyncBlocked("remote_snapshot_not_verified")
    if not isinstance(remote_revision, str) or len(remote_revision) > 120:
        raise SyncBlocked("remote_revision_unavailable")
    try:
        state = classify(baseline_sha256, remote_content, local_content)
    except BaselineError as exc:
        raise SyncBlocked("invalid_baseline") from exc
    status = state["sync_state"]
    decisions = {
        "no_baseline": ("block", "no_common_ancestor"),
        "local_missing": ("block", "missing_private_copy"),
        "unchanged": ("none", "already_identical"),
        "local_changed": ("upload_candidate", "requires_cas_and_backup"),
        "remote_changed": ("download_candidate", "requires_local_cas_and_backup"),
        "same_result_both_changed": ("acknowledge_candidate", "matching_new_ancestor"),
        "conflict_both_changed": ("block", "manual_resolution_required"),
    }
    action, reason = decisions[status]
    return {
        "sync_state": status,
        "action": action,
        "reason": reason,
        "requires_confirmation": action not in ("block", "none"),
        "requires_review": status == "conflict_both_changed",
        "remote_sha256": digest(remote_content),
        "local_sha256": digest(local_content) if local_content is not None else None,
        "baseline_sha256": baseline_sha256,
        # Candidates are never execution authorization.
        "write_authorized": False,
        "remote_write_enabled": False,
        "safe_to_auto_merge": False,
    }
