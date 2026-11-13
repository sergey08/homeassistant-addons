"""Sanitized LiveSync fixture summaries / Resúmenes saneados de pruebas LiveSync.

No network access. Does not include document contents, paths, IDs or credentials.
"""
import json
import sys
from collections import Counter
from pathlib import Path

MAX_DOCS = 100
MAX_FILE_BYTES = 3_000_000

def describe(doc):
    if not isinstance(doc, dict):
        raise ValueError("document_must_be_object")
    # Field names are reduced to a fixed allowlist: unknown/custom fields are
    # counted, never output verbatim (they can themselves contain private data).
    known = {"_id", "_rev", "type", "path", "data", "children", "size",
             "deleted", "_deleted", "_conflicts", "encrypted", "compressed", "e_"}
    fields = sorted(k for k in known if k in doc)
    children = doc.get("children")
    return {
        "fields": fields,
        "other_field_count": sum(k not in known for k in doc),
        "type_category": doc.get("type") if doc.get("type") in ("plain", "leaf", "newnote") else "other_or_missing",
        "has_children": isinstance(children, list),
        "child_count": min(len(children), 10000) if isinstance(children, list) else None,
        "encrypted_marker": bool(doc.get("encrypted") or doc.get("e_")),
        "compressed_marker": bool(doc.get("compressed")),
        "deleted_marker": bool(doc.get("deleted") or doc.get("_deleted")),
        "conflicted_marker": bool(doc.get("_conflicts")),
        "has_data": "data" in doc,
        "data_kind": type(doc["data"]).__name__ if "data" in doc else "absent",
    }

def summarize(records):
    if isinstance(records, dict) and isinstance(records.get("rows"), list):
        records = [r.get("doc") for r in records["rows"] if isinstance(r, dict) and isinstance(r.get("doc"), dict)]
    if not isinstance(records, list) or len(records) > MAX_DOCS:
        raise ValueError("expected_list_of_at_most_100_documents")
    descriptions = [describe(d) for d in records]
    group = Counter(json.dumps(x, sort_keys=True) for x in descriptions)
    return {"schema_version": 1, "document_count": len(descriptions),
            "shapes": [{"summary": json.loads(k), "count": v}
                       for k, v in sorted(group.items())]}

def main():
    if len(sys.argv) != 2:
        raise SystemExit("Usage / Uso: python fixture_schema.py test_documents.json")
    file = Path(sys.argv[1])
    if file.stat().st_size > MAX_FILE_BYTES:
        raise SystemExit("File too large / Archivo demasiado grande")
    data = json.loads(file.read_text(encoding="utf-8"))
    print(json.dumps(summarize(data), indent=2, ensure_ascii=False))

if __name__ == "__main__":
    main()
