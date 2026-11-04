"""Guarded CouchDB commit protocol for disposable integration tests only.

No HTTP client is created here. An injected transport must expose put(doc)
and return (status, response). Production writes are deliberately forbidden.
"""
from copy import deepcopy

from livesync_revision_contract import (RevisionConflict, require_successful_put,
                                       require_confirmed_put_response, require_confirmed_create_response,
                                       require_matching_revision)
from livesync_write_preflight import UnsafeWrite


def commit_isolated_plan(plan, put_document, *, isolated_test=False,
                         remote_writes_enabled=False):
    """Perform leaf-first, parent-last commit through test-only transport.

    Never retry stale parent revisions. A failed parent leaves at most an
    orphan leaf, which is safer than losing the previous note revision.
    """
    if isolated_test is not True or remote_writes_enabled is not False:
        raise UnsafeWrite("isolated_commit_only")
    if not callable(put_document):
        raise UnsafeWrite("transport_required")
    if not isinstance(plan,dict) or plan.get("write_order")!=("leaf","parent"):
        raise UnsafeWrite("invalid_write_plan")
    # Validate and commit one private snapshot. A transport callback may hold
    # an external reference to the caller's plan and mutate it between PUTs.
    plan=deepcopy(plan)
    leaf,parent=plan.get("leaf"),plan.get("parent")
    if not isinstance(leaf,dict) or not isinstance(parent,dict):
        raise UnsafeWrite("invalid_write_plan")
    if leaf.get("type")!="leaf" or leaf.get("e_") is not True:
        raise UnsafeWrite("unencrypted_leaf")
    if not isinstance(leaf.get("data"),str) or not leaf["data"].startswith("%="):
        raise UnsafeWrite("invalid_encrypted_leaf_payload")
    if parent.get("type")!="plain" or parent.get("children")!=[leaf.get("_id")]:
        raise UnsafeWrite("parent_leaf_mismatch")
    if not isinstance(leaf.get("_id"),str) or not leaf["_id"].startswith("h:+"):
        raise UnsafeWrite("invalid_chunk_id")
    if not isinstance(parent.get("_id"),str) or not parent["_id"]:
        raise UnsafeWrite("invalid_parent_id")
    # A leaf is always newly created; never overwrite an existing chunk.
    if "_rev" in leaf:
        raise UnsafeWrite("leaf_update_not_supported")
    if leaf["_id"] == parent["_id"]:
        raise UnsafeWrite("parent_leaf_identity_collision")
    # Never commit tombstones or documents with unresolved conflicts.
    for document in (leaf,parent):
        if (document.get("_deleted") or document.get("deleted")
                or document.get("_conflicts")):
            raise UnsafeWrite("deleted_or_conflicted_document")
    # Reject malformed CAS revisions before creating an orphan leaf.
    if "_rev" in parent:
        require_matching_revision(parent["_rev"], parent["_rev"])
    # A planner-provided expected revision must describe this exact parent.
    # Check before creating a leaf, avoiding a known-stale CAS attempt.
    if "expected_parent_revision" in plan:
        require_matching_revision(plan["expected_parent_revision"], parent.get("_rev"))
    for kind,document in (("leaf",leaf),("parent",parent)):
        # Isolate nested metadata from mutations by an injected test transport.
        status,response=put_document(deepcopy(document))
        if kind == "parent" and document.get("_rev") is not None:
            require_confirmed_put_response(status,response,document["_id"],
                                           document["_rev"])
        else:
            require_confirmed_create_response(status,response,document["_id"])
    return {"status":"committed_in_disposable_test_only",
            "parent_id":parent["_id"]}
