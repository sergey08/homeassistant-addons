"""Produce a review queue of SBOM components with missing license metadata.

This reports uncertainty without assigning inferred licenses or automatically
clearing redistribution requirements. Only public package metadata is emitted.
"""
import argparse
import csv
import json
from collections import Counter
from pathlib import Path


FIELDS = ("ecosystem", "name", "version", "purl", "component_type",
          "bom_ref", "reason", "review_status")


def ecosystem(component):
    purl = component.get("purl") or ""
    if isinstance(purl, str) and purl.startswith("pkg:"):
        kind = purl[4:].split("/", 1)[0].split("@", 1)[0]
        if kind in ("golang", "apk", "generic", "oci"):
            return kind
        return "other-purl"
    return "no-purl"


def missing_licenses(components):
    if not isinstance(components, list):
        raise ValueError("SBOM components must be an array")
    rows = []
    seen = set()
    for item in components:
        if not isinstance(item, dict):
            raise ValueError("Invalid SBOM component")
        identifier = item.get("bom-ref")
        if not isinstance(identifier, str) or not identifier or identifier in seen:
            raise ValueError("Missing or duplicate SBOM component reference")
        seen.add(identifier)
        licenses = item.get("licenses")
        if licenses is not None and not isinstance(licenses, list):
            raise ValueError("Unexpected license metadata")
        if licenses:
            continue
        name = item.get("name")
        if not isinstance(name, str) or not name:
            raise ValueError("Missing component name")
        version = item.get("version")
        purl = item.get("purl")
        row = dict(ecosystem=ecosystem(item), name=name,
                   version=version if isinstance(version, str) else "",
                   purl=purl if isinstance(purl, str) else "",
                   component_type=str(item.get("type", "")),
                   bom_ref=identifier,
                   reason="SBOM contains no license metadata",
                   review_status="PENDING")
        rows.append(row)
    return sorted(rows, key=lambda r: (r["ecosystem"], r["name"], r["version"], r["bom_ref"]))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("sbom", type=Path)
    parser.add_argument("output_directory", type=Path)
    args = parser.parse_args()
    document = json.loads(args.sbom.read_text())
    if document.get("bomFormat") != "CycloneDX":
        raise ValueError("Unexpected SBOM format")
    components = document.get("components")
    queue = missing_licenses(components)
    args.output_directory.mkdir(parents=True, exist_ok=True)
    with (args.output_directory / "license-review-queue.csv").open(
            "w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(queue)
    counts = dict(sorted(Counter(row["ecosystem"] for row in queue).items()))
    summary = {"components": len(components), "missing_license_metadata": len(queue),
               "by_ecosystem": counts,
               "interpretation": "Missing SBOM metadata does not imply unlicensed software",
               "release_status": "NOT_CLEARED"}
    (args.output_directory / "license-review-summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False) + "\n")
    print(json.dumps(summary, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
