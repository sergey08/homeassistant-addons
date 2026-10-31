"""Fail-closed CouchDB revision contract for future isolated LiveSync writes.

This module performs no HTTP calls. A real write must pass _rev in the
document body, use the same revision read for validation, and treat 409 as
a conflict; never retry with a newly fetched revision automatically.
"""
import re

_REV = re.compile(r"[1-9][0-9]*-[0-9a-fA-F]{32}\\Z")

class RevisionConflict(ValueError):
    pass


def require_matching_revision(expected_revision, observed_revision):
    if not isinstance(expected_revision, str) or not _REV.fullmatch(expected_revision):
        raise RevisionConflict("invalid_expected_revision")
    if not isinstance(observed_revision, str) or not _REV.fullmatch(observed_revision):
        raise RevisionConflict("invalid_observed_revision")
    if expected_revision != observed_revision:
        raise RevisionConflict("revision_conflict")
    return observed_revision


def prepare_conditional_document(original, replacement, expected_revision):
    """Return a new candidate body; do not mutate either input."""
    if not isinstance(original, dict) or not isinstance(replacement, dict):
        raise RevisionConflict("invalid_document")
    document_id = original.get("_id")
    if not isinstance(document_id, str) or not document_id:
        raise RevisionConflict("invalid_document_id")
    revision = require_matching_revision(expected_revision, original.get("_rev"))
    if replacement.get("_id") != document_id or replacement.get("_rev") != revision:
        raise RevisionConflict("identity_or_revision_changed")
    if replacement.get("_deleted") or replacement.get("deleted"):
        raise RevisionConflict("deletion_not_supported")
    return dict(replacement)


def require_successful_put(status_code, response):
    """Do not reinterpret conflicts as successful writes."""
    if status_code == 409:
        raise RevisionConflict("remote_revision_conflict")
    if status_code not in (201, 202) or not isinstance(response, dict) or response.get("ok") is not True:
        raise RevisionConflict("remote_write_not_confirmed")
    return True
