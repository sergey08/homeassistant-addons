"""Read-only chunk-reference audit for complete DISPOSABLE test snapshots.

This module never contacts a server or deletes records. Its candidate labels
are meaningful only if the caller supplies a complete isolated snapshot.
A real LiveSync vault may have other references and replication in flight.
"""
from livesync_write_preflight import UnsafeWrite
from livesync_revision_contract import RevisionConflict, require_matching_revision


def _require_valid_optional_revision(document):
    if "_rev" in document:
        try:
            require_matching_revision(document["_rev"], document["_rev"])
        except RevisionConflict as exc:
            raise UnsafeWrite("invalid_snapshot_revision") from exc


def audit_disposable_chunk_references(parents, leaves, *, isolated_test=False,
                                      snapshot_complete=False):
    """Report candidate unreferenced chunks and missing referenced chunks.

    Requires an explicitly complete disposable snapshot; never authorizes
    garbage collection or operations against a real vault.
    """
    if isolated_test is not True or snapshot_complete is not True:
        raise UnsafeWrite("complete_disposable_snapshot_required")
    if not isinstance(parents, (list, tuple)) or not isinstance(leaves, (list, tuple)):
        raise UnsafeWrite("invalid_snapshot_collection")

    referenced=set()
    leaf_ids=set()
    seen_parents=set()
    for parent in parents:
        if not isinstance(parent, dict) or parent.get("type") not in ("plain","newnote"):
            raise UnsafeWrite("unsupported_parent_document")
        parent_id=parent.get("_id")
        children=parent.get("children")
        if (not isinstance(parent_id,str) or not parent_id or
                parent_id.startswith("h:") or parent_id in seen_parents or
                not isinstance(children,(list,tuple))):
            raise UnsafeWrite("invalid_parent_snapshot")
        _require_valid_optional_revision(parent)
        seen_parents.add(parent_id)
        if "_attachments" in parent:
            raise UnsafeWrite("attachments_not_supported")
        if parent.get("_deleted") or parent.get("deleted") or "_conflicts" in parent:
            raise UnsafeWrite("unsafe_parent_snapshot")
        parent_chunks=set()
        for chunk_id in children:
            if not isinstance(chunk_id,str) or not chunk_id.startswith("h:+") or len(chunk_id)<=3:
                raise UnsafeWrite("invalid_chunk_reference")
            if chunk_id in parent_chunks:
                raise UnsafeWrite("duplicate_parent_chunk_reference")
            parent_chunks.add(chunk_id)
            referenced.add(chunk_id)
    for leaf in leaves:
        if not isinstance(leaf,dict) or leaf.get("type")!="leaf":
            raise UnsafeWrite("unsupported_leaf_document")
        leaf_id=leaf.get("_id")
        if (not isinstance(leaf_id,str) or not leaf_id.startswith("h:+") or
                len(leaf_id)<=3 or
                leaf_id in leaf_ids or leaf_id in seen_parents):
            raise UnsafeWrite("invalid_leaf_snapshot")
        _require_valid_optional_revision(leaf)
        # These disposable encrypted leaves are created once, never updated.
        # A later generation indicates an unsupported overwrite history.
        if "_rev" in leaf and not leaf["_rev"].startswith("1-"):
            raise UnsafeWrite("overwritten_leaf_snapshot")
        if "_attachments" in leaf:
            raise UnsafeWrite("attachments_not_supported")
        if leaf.get("_deleted") or leaf.get("deleted") or "_conflicts" in leaf:
            raise UnsafeWrite("unsafe_leaf_snapshot")
        leaf_ids.add(leaf_id)
    return {
        "unreferenced_leaf_candidates":tuple(sorted(leaf_ids-referenced)),
        "missing_referenced_leaf_ids":tuple(sorted(referenced-leaf_ids)),
        "deletion_permitted":False,
        "scope":"disposable_snapshot_only",
    }
