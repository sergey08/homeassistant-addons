"""CouchDB revision-safe transport for future LiveSync writes.

Only accepts a pre-encoded, externally validated LiveSync document. It never
constructs or guesses LiveSync IDs, encrypted metadata, chunks or attachments.
"""
import base64
import json
import re
from urllib.error import HTTPError
from urllib.parse import quote
from urllib.request import Request, build_opener, HTTPRedirectHandler

class RevisionConflict(Exception):
    pass

class UnsafeDocument(Exception):
    pass

class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None

def put_revision_checked(base_url, database, username, password, document,
                         *, expected_revision=None, creating=False, opener=None, wire_validator=None):
    """Single-document conditional PUT; caller must separately validate LiveSync wire format.

    Requires a validated, trusted document from a compatible encoder.
    Create uses If-None-Match: *; updates require both _rev and If-Match.
    """
    # Fail closed: the caller must provide a proven LiveSync wire-format validator.
    # A CouchDB conditional PUT alone does not guarantee Obsidian compatibility.
    if not callable(wire_validator):
        raise UnsafeDocument("livesync_wire_validator_required")
    if not isinstance(base_url, str) or base_url.rstrip("/") != "http://db21ed7f-obsidian-syncserver-ssl:5984":
        raise UnsafeDocument("unsupported_connection")
    if not isinstance(database, str) or not re.fullmatch(r"[A-Za-z0-9_.-]+", database):
        raise UnsafeDocument("invalid_database")
    if not isinstance(document, dict) or not isinstance(document.get("_id"), str):
        raise UnsafeDocument("missing_document_id")
    doc_id = document["_id"]
    if len(doc_id) > 512 or not doc_id or doc_id.startswith("_") or any(c in doc_id for c in "\x00\r\n"):
        raise UnsafeDocument("invalid_document_id")
    if creating:
        if expected_revision is not None or "_rev" in document:
            raise UnsafeDocument("unexpected_revision")
    else:
        if not isinstance(expected_revision, str) or not re.fullmatch(r"[1-9][0-9]*-[0-9a-fA-F]{32}", expected_revision):
            raise UnsafeDocument("revision_required")
        if document.get("_rev") != expected_revision:
            raise UnsafeDocument("revision_mismatch")
    try:
        if wire_validator(document) is not True:
            raise UnsafeDocument("livesync_wire_validation_failed")
    except UnsafeDocument:
        raise
    except Exception:
        raise UnsafeDocument("livesync_wire_validation_failed") from None
    raw = json.dumps(document, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    if len(raw) > 2_500_000:
        raise UnsafeDocument("document_too_large")
    headers = {"Content-Type": "application/json", "Accept": "application/json"}
    if username:
        headers["Authorization"] = "Basic " + base64.b64encode((username + ":" + (password or "")).encode()).decode()
    if creating:
        headers["If-None-Match"] = "*"
    else:
        headers["If-Match"] = '"' + expected_revision + '"'
    target = base_url.rstrip("/") + "/" + quote(database, safe="") + "/" + quote(doc_id, safe="")
    client = opener if opener is not None else build_opener(NoRedirect())
    try:
        with client.open(Request(target, data=raw, headers=headers, method="PUT"), timeout=12) as response:
            body = response.read(8193)
            if len(body) > 8192:
                raise UnsafeDocument("response_too_large")
            result = json.loads(body)
    except HTTPError as exc:
        if exc.code in (409, 412):
            raise RevisionConflict("revision_conflict") from None
        raise
    if not isinstance(result, dict) or result.get("ok") is not True or result.get("id") != doc_id:
        raise UnsafeDocument("unexpected_response")
    return {"id": result["id"], "rev": result.get("rev")}
