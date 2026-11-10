"""Generate an unapproved, exact-SBOM attribution worksheet for humans.

The output is explicitly NOT a license approval. No SPDX identifiers or
redistribution duties are fabricated from automatic scanner classifications.
"""
import argparse
import csv
import json
from pathlib import Path

from license_release_gate import canonical_sbom_sha256


HEADERS = ("bom_ref", "name", "version", "purl", "detected_license_metadata",
           "status", "license_evidence", "notice_obligations", "reviewer")


def make_worksheet(sbom):
    if sbom.get("bomFormat") != "CycloneDX":
        raise ValueError("Expected CycloneDX inventory")
    components = sbom.get("components")
    if not isinstance(components, list) or not components:
        raise ValueError("Missing SBOM components")
    refs = set()
    records = []
    for item in components:
        if not isinstance(item, dict):
            raise ValueError("Malformed component")
        ref = item.get("bom-ref")
        if not isinstance(ref, str) or not ref or ref in refs:
            raise ValueError("Missing or duplicate component ref")
        refs.add(ref)
        licenses = item.get("licenses", [])
        if not isinstance(licenses, list):
            raise ValueError("Malformed detected licenses")
        records.append({
            "bom_ref": ref,
            "name": str(item.get("name") or ""),
            "version": str(item.get("version") or ""),
            "purl": str(item.get("purl") or ""),
            "detected_license_metadata": json.dumps(licenses, ensure_ascii=False,
                                                     separators=(",", ":")),
            "status": "PENDING",
            "license_evidence": "",
            "notice_obligations": "",
            "reviewer": "",
        })
    return sorted(records, key=lambda r: (r["name"], r["version"], r["bom_ref"]))


def write_worksheet(sbom, output):
    rows = make_worksheet(sbom)
    output.mkdir(parents=True, exist_ok=True)
    with (output / "license-human-review-worksheet.csv").open(
            "w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=HEADERS)
        writer.writeheader()
        writer.writerows(rows)
    pending = {"sbom_sha256": canonical_sbom_sha256(sbom),
               "purpose": "WORKSHEET_ONLY_NOT_APPROVED",
               "reviews": [
                   {"bom_ref": row["bom_ref"],
                    "status": "PENDING",
                    "license_evidence": "",
                    "notice_obligations": "",
                    "reviewer": ""}
                   for row in rows]}
    (output / "license-review-pending.json").write_text(
        json.dumps(pending, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return pending


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("sbom", type=Path)
    ap.add_argument("output", type=Path)
    args = ap.parse_args()
    pending = write_worksheet(json.loads(args.sbom.read_text(encoding="utf-8")),
                              args.output)
    print("Generated", len(pending["reviews"]), "PENDING license reviews. No approvals created.")


if __name__ == "__main__":
    main()
