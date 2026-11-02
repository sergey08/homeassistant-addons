"""Guarded CouchDB commit protocol for disposable integration tests only.

No HTTP client is created here. An injected transport must expose put(doc)
and return (status, response). Production writes are deliberately forbidden.
"""
from livesync_revision_contract import RevisionConflict, require_successful_put
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
    leaf,parent=plan.get("leaf"),plan.get("parent")
    if not isinstance(leaf,dict) or not isinstance(parent,dict):
        raise UnsafeWrite("invalid_write_plan")
    if leaf.get("type")!="leaf" or leaf.get("e_") is not True:
        raise UnsafeWrite("unencrypted_leaf")
    if parent.get("type")!="plain" or parent.get("children")!=[leaf.get("_id")]:
        raise UnsafeWrite("parent_leaf_mismatch")
    if not isinstance(leaf.get("_id"),str) or not leaf["_id"].startswith("h:+"):
        raise UnsafeWrite("invalid_chunk_id")
    if not isinstance(parent.get("_id"),str) or not parent["_id"]:
        raise UnsafeWrite("invalid_parent_id")
    for kind,document in (("leaf",leaf),("parent",parent)):
        status,response=put_document(dict(document))
        require_successful_put(status,response)
    return {"status":"committed_in_disposable_test_only",
            "parent_id":parent["_id"]}
