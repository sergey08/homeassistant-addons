"""Conservative recovery diagnostics for isolated LiveSync CAS commits.

This wrapper never retries, deletes an orphan leaf or modifies the parent
after an ambiguous acknowledgement. It is exclusively for disposable tests.
No note content, document IDs or credentials are included in results.
"""
from livesync_isolated_commit import commit_isolated_plan
from livesync_write_preflight import UnsafeWrite


def inspect_isolated_commit(plan, put_document, *, isolated_test=False,
                            remote_writes_enabled=False):
    if isolated_test is not True or remote_writes_enabled is not False:
        raise UnsafeWrite("isolated_commit_only")
    if not callable(put_document):
        raise UnsafeWrite("transport_required")
    attempted = []
    confirmed = []

    def observed_put(document):
        # Only an isolated callback, never an HTTP connection constructed here.
        kind = document.get("type")
        attempted.append(kind)
        result = put_document(document)
        # A successful transport response alone is not sufficient to confirm
        # the write. The commit validator checks identity and revision later.
        return result

    try:
        result = commit_isolated_plan(plan, observed_put,
                                      isolated_test=True,
                                      remote_writes_enabled=False)
    except (Exception,) as exc:
        if not attempted:
            # Validation fails before any transport attempt.
            return {"status": "preflight_blocked", "remote_state": "unchanged",
                    "recovery": "correct_plan_without_writing", "retry_automatic": False,
                    "remote_writes_enabled": False}
        if attempted == ["leaf"]:
            return {"status": "incomplete", "remote_state": "leaf_uncertain",
                    "recovery": "inspect_leaf_before_any_retry",
                    "retry_automatic": False, "remote_writes_enabled": False}
        return {"status": "incomplete", "remote_state": "parent_uncertain",
                "recovery": "read_parent_revision_and_children_then_review_orphan_leaf",
                "retry_automatic": False, "remote_writes_enabled": False}
    return {"status": "committed_in_disposable_test_only",
            "remote_state": "parent_confirmed",
            "recovery": "none", "retry_automatic": False,
            "remote_writes_enabled": False}
