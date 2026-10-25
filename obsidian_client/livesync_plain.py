"""Read-only decoding of synthetic, unencrypted LiveSync text notes.

Never accepts encrypted, compressed, binary, deleted or conflicted records.
No CouchDB requests or file writes are performed here.
"""

MAX_CHUNKS = 512
MAX_CONTENT = 2_000_000


class UnsupportedNote(ValueError):
    """LiveSync representation needs unsupported decoding or unsafe metadata."""


def decode_plain_note(parent, chunks):
    """Decode one fully supplied plaintext note and its ordered leaf chunks."""
    if not isinstance(parent, dict) or parent.get("type") != "plain":
        raise UnsupportedNote("unsupported_type")
    path = parent.get("path")
    if not isinstance(path, str) or not path.endswith(".md") or not path or path.startswith("/") or "\\" in path or any(part in ("", ".", "..") for part in path.split("/")):
        raise UnsupportedNote("invalid_path")
    if parent.get("deleted") or parent.get("_deleted") or parent.get("_conflicts"):
        raise UnsupportedNote("deleted_or_conflicted")
    if parent.get("e_") or path.startswith(("f:", "/\\:")):
        raise UnsupportedNote("encrypted_or_obfuscated")
    if parent.get("eden") or parent.get("compressed") or parent.get("encrypted"):
        raise UnsupportedNote("unsupported_encoding")
    ids = parent.get("children", [])
    if not isinstance(ids, list) or len(ids) > MAX_CHUNKS or not all(isinstance(v, str) and v for v in ids) or len(ids) != len(set(ids)):
        raise UnsupportedNote("invalid_children")
    if not isinstance(chunks, dict):
        raise UnsupportedNote("invalid_chunks")
    if ids:
        parts = []
        for child_id in ids:
            if not isinstance(child_id, str) or child_id not in chunks:
                raise UnsupportedNote("missing_chunk")
            doc = chunks[child_id]
            if not isinstance(doc, dict) or doc.get("type") != "leaf" or doc.get("e_") or doc.get("_deleted") or doc.get("_conflicts") or doc.get("compressed") or doc.get("encrypted"):
                raise UnsupportedNote("unsupported_chunk")
            part = doc.get("data")
            if not isinstance(part, str) or part.startswith("e_"):
                raise UnsupportedNote("unsupported_chunk_data")
            parts.append(part)
    else:
        if "data" not in parent:
            raise UnsupportedNote("missing_inline_data")
        data = parent["data"]
        if isinstance(data, str):
            parts = [data]
        elif isinstance(data, list) and all(isinstance(v, str) for v in data):
            parts = data
        else:
            raise UnsupportedNote("unsupported_inline_data")
    body = "".join(parts)
    if len(body.encode("utf-8")) > MAX_CONTENT:
        raise UnsupportedNote("content_too_large")
    return {"path": path, "content": body}
