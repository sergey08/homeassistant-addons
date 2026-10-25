"""Extract one synthetic/test-only LiveSync note from an offline CouchDB dump.

English: no network access; never run with production data.
Español: sin acceso a red; no utilizar con datos de producción.
Input is a CouchDB _all_docs?include_docs=true JSON export from an ISOLATED test
database. Writes one fixture with only requested note and referenced chunks.
"""
import json
import sys
from pathlib import Path

from livesync_plain import decode_plain_note

MAX_DUMP = 8_000_000
MAX_PARENT_CHUNKS = 512
ALLOWED_PARENT_KEYS = {"_id", "type", "datatype", "path", "children",
                       "size", "deleted", "_deleted", "_conflicts",
                       "e_", "encrypted", "compressed", "eden"}
ALLOWED_CHUNK_KEYS = {"_id", "type", "data", "deleted", "_deleted",
                      "_conflicts", "e_", "encrypted", "compressed"}


def make_fixture(export, note_path, original_content):
    """Fail closed unless exactly one note and its chunks are complete."""
    if not isinstance(export, dict) or not isinstance(export.get("rows"), list):
        raise ValueError("invalid_export")
    if not isinstance(note_path, str) or not isinstance(original_content, str):
        raise ValueError("invalid_expected")
    rows = export["rows"]
    if len(rows) > 5000:
        raise ValueError("too_many_documents")
    docs = {}
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError("invalid_row")
        doc = row.get("doc")
        if not isinstance(doc, dict) or not isinstance(doc.get("_id"), str):
            continue
        if doc["_id"] in docs:
            raise ValueError("duplicate_id")
        docs[doc["_id"]] = doc
    matching = [doc for doc in docs.values()
                if doc.get("path") == note_path and doc.get("type") == "plain"]
    if len(matching) != 1:
        raise ValueError("missing_or_ambiguous_parent")
    parent = matching[0]
    children = parent.get("children", [])
    if not isinstance(children, list) or len(children) > MAX_PARENT_CHUNKS:
        raise ValueError("invalid_children")
    selected = {}
    for child_id in children:
        if not isinstance(child_id, str) or child_id not in docs:
            raise ValueError("missing_child")
        selected[child_id] = {key: value for key, value in docs[child_id].items()
                              if key in ALLOWED_CHUNK_KEYS}
    safe_parent = {key: value for key, value in parent.items()
                   if key in ALLOWED_PARENT_KEYS}
    fixture = {"parent": safe_parent, "chunks": selected,
               "expected": {"path": note_path, "content": original_content}}
    if decode_plain_note(safe_parent, selected) != fixture["expected"]:
        raise ValueError("content_mismatch")
    return fixture


def main(argv):
    if len(argv) != 5:
        print("Usage / Uso: python extract_test_fixture.py DUMP.json PATH.md CONTENT.txt OUT.json")
        return 2
    source, path, original, output = map(Path, [argv[1], argv[2], argv[3], argv[4]])
    if source.stat().st_size > MAX_DUMP:
        print("FAIL / FALLO: oversized export")
        return 1
    try:
        exported = json.loads(source.read_text(encoding="utf-8"))
        content = original.read_text(encoding="utf-8")
        fixture = make_fixture(exported, str(path), content)
        if output.exists():
            raise ValueError("output_already_exists")
        output.write_text(json.dumps(fixture, ensure_ascii=False, indent=2), encoding="utf-8")
    except (OSError, ValueError, TypeError) as exc:
        print("FAIL / FALLO:", type(exc).__name__)
        return 1
    print("PASS / CORRECTO: isolated fixture created / muestra aislada creada")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
