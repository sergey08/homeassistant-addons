"""Isolated-only LiveSync encrypted multi-leaf, parent-last CAS protocol.

Not a production writer: injected transport only and explicit disposable-test
gate. Acknowledgements are verified, and failure never triggers retries or
deletions. No CouchDB URLs or secrets are accepted by this module.
"""
from copy import deepcopy

from livesync_crypto import decrypt_hkdf_string
from livesync_encrypted_metadata_fixture import decode_parent_metadata_fixture
from livesync_encrypted_parent_snapshot import validate_encrypted_parent_snapshot
from livesync_revision_contract import (
    require_confirmed_create_response,
    require_confirmed_put_response,
    require_matching_revision,
)
from livesync_write_preflight import UnsafeWrite


class IncompleteMultichunkCommit(ValueError):
    def __init__(self, phase, confirmed_chunks):
        self.phase = phase
        self.confirmed_chunks = confirmed_chunks
        super().__init__("isolated_multichunk_commit_incomplete")


def commit_isolated_multichunk_plan(
        plan, put_document, read_document, passphrase, pbkdf2_salt_b64, *,
        isolated_test=False, remote_writes_enabled=False):
    """Create all NEW encrypted leaves then CAS the existing encrypted parent.

    A failed/ambiguous leaf or parent leaves old parent references untouched
    unless CouchDB already accepted the parent; caller must inspect state.
    """
    if isolated_test is not True or remote_writes_enabled is not False:
        raise UnsafeWrite("isolated_commit_only")
    if not callable(put_document) or not callable(read_document):
        raise UnsafeWrite("transport_required")
    if not isinstance(plan, dict) or plan.get("write_supported") is not False:
        raise UnsafeWrite("untrusted_plan")
    plan = deepcopy(plan)
    parent = plan.get("parent")
    leaves = plan.get("leaves")
    expected_revision = plan.get("expected_parent_revision")
    path = plan.get("path")
    if (not isinstance(parent, dict) or not isinstance(leaves, list)
            or not 2 <= len(leaves) <= 512 or not isinstance(path, str)):
        raise UnsafeWrite("invalid_multichunk_plan")
    if parent.get("_rev") is None:
        raise UnsafeWrite("parent_create_not_supported")
    require_matching_revision(expected_revision, parent["_rev"])
    if (parent.get("type") != "plain" or parent.get("children") != []
            or parent.get("data") is not None
            or parent.get("_attachments") is not None):
        raise UnsafeWrite("invalid_encrypted_parent")
    if (parent.get("_deleted") or parent.get("deleted")
            or parent.get("_conflicts")):
        raise UnsafeWrite("conflicted_or_deleted_parent")
    try:
        metadata = decode_parent_metadata_fixture(
            parent.get("path"), passphrase, pbkdf2_salt_b64)
        checked = validate_encrypted_parent_snapshot(
            parent, metadata, path, expected_revision)
    except Exception as exc:
        raise UnsafeWrite("unverified_parent_metadata") from exc

    ids = [doc.get("_id") if isinstance(doc, dict) else None for doc in leaves]
    if ids != list(checked["children"]) or len(set(ids)) != len(ids):
        raise UnsafeWrite("parent_leaf_mismatch")
    for leaf in leaves:
        if (leaf.get("type") != "leaf" or leaf.get("e_") is not True
                or not isinstance(leaf.get("_id"), str)
                or not leaf["_id"].startswith("h:+")
                or not isinstance(leaf.get("data"), str)
                or not leaf["data"].startswith("%=")
                or leaf.get("_rev") is not None
                or leaf.get("_attachments") is not None
                or leaf.get("_deleted") or leaf.get("deleted")
                or leaf.get("_conflicts")):
            raise UnsafeWrite("invalid_encrypted_leaf")
        if leaf["_id"] == parent.get("_id"):
            raise UnsafeWrite("document_identity_collision")
    # The new encrypted metadata must have zeroed outer fields.
    if any(parent.get(k) != 0 for k in ("ctime", "mtime", "size")):
        raise UnsafeWrite("unencrypted_parent_fields")
    # Confirm that all leaf plaintext chunks match encrypted parent size
    # before sending a single document to the isolated transport.
    try:
        total_bytes = sum(len(decrypt_hkdf_string(
            leaf["data"], passphrase, pbkdf2_salt_b64).encode("utf-8"))
            for leaf in leaves)
    except Exception as exc:
        raise UnsafeWrite("unverified_leaf_ciphertext") from exc
    if total_bytes != metadata.get("size") or total_bytes > 2_000_000:
        raise UnsafeWrite("chunk_total_size_mismatch")
    confirmed = 0
    for leaf in leaves:
        try:
            status, reply = put_document(deepcopy(leaf))
            revision = require_confirmed_create_response(status, reply, leaf["_id"])
            fetched = read_document(leaf["_id"])
            if (not isinstance(fetched, dict)
                    or fetched.get("_id") != leaf["_id"]
                    or fetched.get("_rev") != revision
                    or fetched.get("type") != "leaf"
                    or fetched.get("e_") is not True
                    or fetched.get("data") != leaf["data"]):
                raise ValueError("leaf_readback_mismatch")
            confirmed += 1
        except Exception as exc:
            raise IncompleteMultichunkCommit("leaf_uncertain", confirmed) from exc
    try:
        status, reply = put_document(deepcopy(parent))
        revision = require_confirmed_put_response(
            status, reply, parent["_id"], expected_revision)
    except Exception as exc:
        raise IncompleteMultichunkCommit("parent_uncertain", confirmed) from exc
    return {"status": "committed_in_disposable_test_only",
            "parent_revision": revision, "confirmed_chunks": confirmed,
            "remote_writes_enabled": False}
