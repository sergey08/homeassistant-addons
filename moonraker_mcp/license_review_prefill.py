"""Prepare exact-SBOM evidence hints for human license reviewers.

No status transitions or legal claims: every component stays PENDING.
"""
import argparse
import csv
import json
from collections import defaultdict
from pathlib import Path
from urllib.parse import unquote


def _load_rows(path, required):
    with path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        if not set(required).issubset(set(reader.fieldnames or [])):
            raise ValueError("Unexpected source evidence columns")
        return list(reader)


def reconcile(pending, go_rows, alpine_rows):
    if pending.get("purpose") != "WORKSHEET_ONLY_NOT_APPROVED":
        raise ValueError("Expected unapproved SBOM worksheet")
    reviews = pending.get("reviews")
    if not isinstance(reviews, list) or not reviews:
        raise ValueError("No license review items")
    go = defaultdict(list)
    for row in go_rows:
        if row.get("bom_ref"):
            go[row["bom_ref"]].append(row)
    apk = defaultdict(list)
    for row in alpine_rows:
        apk[(row.get("package"), row.get("version"))].append(row)
    result = []
    seen = set()
    for record in reviews:
        ref = record.get("bom_ref")
        if not isinstance(ref, str) or not ref or ref in seen:
            raise ValueError("Invalid or duplicate SBOM component")
        seen.add(ref)
        if record.get("status") != "PENDING":
            raise ValueError("Refusing already-approved or mutated review")
        matched = go.get(ref, [])
        file_hints = sorted({
            f'{r["license_file"]} sha256:{r["license_sha256"]}'
            for r in matched
            if r.get("source_status") == "SOURCE_LICENSE_FILES_FOUND"
            and r.get("license_file") and r.get("license_sha256")
        })
        # Percent-encoded PURL names (e.g. libstdc%2B%2B) must match their
        # decoded APK package names without broad substring matching.
        apk_hints = []
        apk_name_version = unquote(ref.split("?", 1)[0].rsplit("/", 1)[-1]) if ref.startswith("pkg:apk/") else ""
        for (name, version), candidates in apk.items():
            if (name and version and len(candidates) == 1
                    and apk_name_version == name + "@" + version):
                apk_hints.append({
                    "package": name,
                    "version": version,
                    "declared_expression": candidates[0].get("license_expression", ""),
                    "review_category": candidates[0].get("review_category", "")
                })
        result.append({
            "bom_ref": ref,
            "status": "PENDING",
            "go_source_files": file_hints,
            "go_source_status": sorted({r.get("source_status", "") for r in matched}),
            "alpine_metadata": apk_hints,
            "human_review_required": True
        })
    return {
        "sbom_sha256": pending.get("sbom_sha256"),
        "purpose": "EVIDENCE_HINTS_ONLY_NOT_LICENSE_APPROVAL",
        "reviewer_approved": False,
        "components": result
    }


def main():
    p = argparse.ArgumentParser()
    p.add_argument("pending", type=Path)
    p.add_argument("go_evidence", type=Path)
    p.add_argument("alpine_review", type=Path)
    p.add_argument("output", type=Path)
    args = p.parse_args()
    pending = json.loads(args.pending.read_text(encoding="utf-8"))
    rows_go = _load_rows(args.go_evidence, {"bom_ref", "license_file", "license_sha256", "source_status"})
    rows_apk = _load_rows(args.alpine_review, {"package", "version", "license_expression", "review_category"})
    obj = reconcile(pending, rows_go, rows_apk)
    args.output.write_text(json.dumps(obj, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print("Evidence hints prepared for", len(obj["components"]), "components; all remain PENDING.")


if __name__ == "__main__":
    main()
