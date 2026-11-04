"""Offline conflict-checked LiveSync parent update plan; never writes to CouchDB.

The caller must obtain the full current note plaintext and matching revision
from an authoritative, fresh snapshot. The plan does not bypass or enable the
remote-writes feature flag. Only single-chunk legacy xxhash64 notes supported.
"""
import hashlib
from livesync_crypto import encrypt_hkdf_string
from livesync_chunk_identity import legacy_chunk_id, js_utf16_code_units
from livesync_write_preflight import validate_update_snapshot, UnsafeWrite
from livesync_revision_contract import prepare_conditional_document

def prepare_isolated_note_update(path, proposed_content, existing_parent,
                                 current_content, expected_revision,
                                 expected_content_sha256, passphrase,
                                 pbkdf2_salt_b64, *, modified_millis,
                                 remote_writes_enabled=False):
    if remote_writes_enabled is not False:
        raise UnsafeWrite("remote_writes_forbidden")
    if not isinstance(existing_parent, dict) or existing_parent.get("type")!="plain":
        raise UnsafeWrite("unsupported_parent")
    if (existing_parent.get("_deleted") or existing_parent.get("deleted")
            or existing_parent.get("_conflicts")):
        raise UnsafeWrite("deleted_or_conflicted_parent")
    # Production LiveSync can store encrypted parent path metadata. The
    # isolated builder only supports the verified plaintext parent format.
    # Never infer an encrypted parent ID or try to write it with this plan.
    stored_path = existing_parent.get("path")
    if isinstance(stored_path, str) and stored_path.startswith("/\\:%="):
        raise UnsafeWrite("encrypted_parent_write_not_supported")
    if existing_parent.get("_id") != path.lower() or stored_path != path:
        raise UnsafeWrite("parent_identity_mismatch")
    if len(existing_parent.get("children", [])) != 1:
        raise UnsafeWrite("multichunk_update_not_supported")
    if not isinstance(modified_millis,int) or isinstance(modified_millis,bool) or modified_millis<0:
        raise UnsafeWrite("invalid_timestamp")
    current_mtime=existing_parent.get("mtime")
    if type(current_mtime) is not int or current_mtime<0:
        raise UnsafeWrite("invalid_modification_time")
    if modified_millis<current_mtime:
        raise UnsafeWrite("backdated_update")
    validate_update_snapshot(path,proposed_content,expected_revision,
                             existing_parent.get("_rev"),expected_content_sha256,
                             current_content)
    if not proposed_content or js_utf16_code_units(proposed_content)>1000:
        raise UnsafeWrite("unsupported_chunk_count")
    if not isinstance(passphrase,str) or not passphrase:
        raise UnsafeWrite("missing_passphrase")
    old_leaf="h:"+legacy_chunk_id(current_content,passphrase)
    if existing_parent["children"]!=[old_leaf]:
        raise UnsafeWrite("old_chunk_identity_mismatch")
    leaf_id="h:"+legacy_chunk_id(proposed_content,passphrase)
    # The isolated protocol creates fresh leaves; verified chunk reuse is
    # unsupported, including unchanged content and hash collisions.
    if leaf_id == old_leaf:
        raise UnsafeWrite("unchanged_chunk_identity")
    leaf={"_id":leaf_id,"type":"leaf","e_":True,
          "data":encrypt_hkdf_string(proposed_content,passphrase,pbkdf2_salt_b64)}
    candidate=dict(existing_parent)
    candidate.update({"children":[leaf_id],"size":len(proposed_content.encode("utf-8")),
                      "mtime":modified_millis})
    parent=prepare_conditional_document(existing_parent,candidate,expected_revision)
    return {"leaf":leaf,"parent":parent,"write_order":("leaf","parent"),
            "expected_parent_revision":expected_revision,
            "expected_old_content_sha256":hashlib.sha256(current_content.encode()).hexdigest()}
