"""Pure, isolated-only encrypted/obfuscated LiveSync CAS update planner.

No transport, no filesystem writes, no production remote writes. The stored
parent and matching plaintext MUST come from the same fresh trusted snapshot.
"""
import hashlib
from livesync_chunk_identity import legacy_chunk_id, js_utf16_code_units
from livesync_crypto import encrypt_hkdf_string
from livesync_encrypted_metadata_fixture import (
    decode_parent_metadata_fixture, encode_parent_metadata_fixture)
from livesync_encrypted_parent_snapshot import validate_encrypted_parent_snapshot
from livesync_obfuscated_parent_identity import legacy_obfuscated_parent_id
from livesync_revision_contract import prepare_conditional_document
from livesync_write_preflight import UnsafeWrite, validate_update_snapshot


def prepare_obfuscated_encrypted_update(
    path, proposed_content, stored_parent, current_content, expected_revision,
    expected_content_sha256, passphrase, pbkdf2_salt_b64, *,
    modified_millis, case_insensitive=True, remote_writes_enabled=False,
    id_derivation_key=None,
):
    if remote_writes_enabled is not False:
        raise UnsafeWrite("production_writes_forbidden")
    if not isinstance(passphrase,str) or not passphrase:
        raise UnsafeWrite("missing_passphrase")
    if type(modified_millis) is not int or modified_millis < 0:
        raise UnsafeWrite("invalid_timestamp")
    if not isinstance(current_content,str) or not current_content:
        raise UnsafeWrite("invalid_current_content")
    if not isinstance(proposed_content,str) or not proposed_content:
        raise UnsafeWrite("invalid_proposed_content")
    if js_utf16_code_units(proposed_content)>1000 or js_utf16_code_units(current_content)>1000:
        raise UnsafeWrite("multichunk_unsupported")
    if not isinstance(stored_parent,dict):
        raise UnsafeWrite("invalid_parent")
    if stored_parent.get("_id") != legacy_obfuscated_parent_id(
        path,passphrase,case_insensitive=case_insensitive,
        id_derivation_key=id_derivation_key):
        raise UnsafeWrite("obfuscated_identity_mismatch")
    decoded=decode_parent_metadata_fixture(
        stored_parent.get("path"),passphrase,pbkdf2_salt_b64)
    validated=validate_encrypted_parent_snapshot(
        stored_parent,decoded,path,expected_revision)
    validate_update_snapshot(path,proposed_content,expected_revision,
        validated["_rev"],expected_content_sha256,current_content)
    old_leaf="h:"+legacy_chunk_id(current_content,passphrase)
    if validated["children"]!=(old_leaf,):
        raise UnsafeWrite("old_leaf_identity_mismatch")
    if decoded["size"] != len(current_content.encode("utf-8")):
        raise UnsafeWrite("old_size_mismatch")
    if type(decoded["ctime"]) is not int or decoded["ctime"]<0:
        raise UnsafeWrite("invalid_creation_time")
    if type(decoded["mtime"]) is not int or decoded["mtime"]<0:
        raise UnsafeWrite("invalid_modification_time")
    if modified_millis < decoded["mtime"]:
        raise UnsafeWrite("backdated_update")
    new_leaf_id="h:"+legacy_chunk_id(proposed_content,passphrase)
    # This protocol only creates fresh leaves; reusing an existing identity
    # needs a separate verified reuse protocol, even for unchanged content.
    if new_leaf_id == old_leaf:
        raise UnsafeWrite("unchanged_chunk_identity")
    leaf={"_id":new_leaf_id,"type":"leaf","e_":True,
          "data":encrypt_hkdf_string(proposed_content,passphrase,pbkdf2_salt_b64)}
    metadata=encode_parent_metadata_fixture(path,[new_leaf_id],passphrase,
        pbkdf2_salt_b64,ctime=decoded["ctime"],mtime=modified_millis,
        size=len(proposed_content.encode("utf-8")))
    parent=dict(stored_parent)
    parent.update({key:metadata[key] for key in ("path","children","ctime","mtime","size")})
    parent=prepare_conditional_document(stored_parent,parent,expected_revision)
    return {"leaf":leaf,"parent":parent,"write_order":("leaf","parent"),
            "expected_parent_revision":expected_revision,
            "expected_old_content_sha256":hashlib.sha256(
                current_content.encode("utf-8")).hexdigest(),
            "write_supported":False}
