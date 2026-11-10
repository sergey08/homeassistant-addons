"""Fail-closed stable-release documentation gate for dependency license reviews.

This does NOT decide whether redistribution is lawful. It checks that every
component of the exact CycloneDX inventory has a component-specific, reviewed
attribution record and that the records belong to the current SBOM.
"""
import argparse
import hashlib
import json
from pathlib import Path


def canonical_sbom_sha256(sbom):
    """Stable across JSON whitespace and key ordering, unlike a ZIP checksum."""
    return hashlib.sha256(json.dumps(sbom, sort_keys=True, ensure_ascii=False,
                                     separators=(",", ":")).encode("utf-8")).hexdigest()


def assess(sbom, manifest):
    if sbom.get("bomFormat") != "CycloneDX" or not isinstance(sbom.get("components"), list):
        raise ValueError("Invalid CycloneDX SBOM")
    components = sbom["components"]
    ids = [item.get("bom-ref") for item in components if isinstance(item, dict)]
    if len(ids) != len(components) or any(not isinstance(i, str) or not i for i in ids):
        raise ValueError("Missing SBOM references")
    if len(ids) != len(set(ids)):
        raise ValueError("Duplicate SBOM references")
    if manifest.get("sbom_sha256") != canonical_sbom_sha256(sbom):
        return False, ["Review manifest does not match this exact SBOM"]
    reviews = manifest.get("reviews")
    if not isinstance(reviews, list):
        return False, ["Missing component-specific reviews"]
    by_id = {}
    for record in reviews:
        if not isinstance(record, dict) or not isinstance(record.get("bom_ref"), str):
            raise ValueError("Invalid review record")
        ref = record["bom_ref"]
        if ref in by_id:
            raise ValueError("Duplicate component review: " + ref)
        by_id[ref] = record
    issues = []
    for ref in ids:
        entry = by_id.get(ref)
        if entry is None:
            issues.append("Unreviewed SBOM component: " + ref)
            continue
        if (entry.get("status") != "REVIEWED"
                or not isinstance(entry.get("license_evidence"), str)
                or not entry["license_evidence"].strip()
                or not isinstance(entry.get("notice_obligations"), str)
                or not entry["notice_obligations"].strip()
                or not isinstance(entry.get("reviewer"), str)
                or not entry["reviewer"].strip()):
            issues.append("Incomplete attribution review: " + ref)
    extras = sorted(set(by_id) - set(ids))
    if extras:
        issues.append("Reviews refer to components absent from SBOM")
    return not issues, issues


def main():
    ap = argparse.ArgumentParser(description="Check exact-version license attribution review coverage")
    ap.add_argument("sbom", type=Path)
    ap.add_argument("review_manifest", type=Path)
    args = ap.parse_args()
    try:
        sbom = json.loads(args.sbom.read_text(encoding="utf-8"))
        manifest = json.loads(args.review_manifest.read_text(encoding="utf-8"))
        ok, issues = assess(sbom, manifest)
    except (OSError, ValueError, TypeError, json.JSONDecodeError) as exc:
        print("BLOCKED: malformed or missing review evidence:", type(exc).__name__)
        return 1
    for issue in issues[:20]:
        print("BLOCKED:", issue)
    if not ok:
        print("License documentation review incomplete; stable release blocked")
        return 1
    print("Attribution documentation complete for current SBOM; independent legal approval still required")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
