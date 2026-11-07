"""Verify pinned Alpine aports auxiliary files against APKBUILD SHA-512 entries.

This is an *integrity* check, not license approval. Remote source archives and
dynamically downloaded patches remain UNVERIFIED and must be reviewed separately.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import sys

APORTS_COMMIT = "2235ae248c31ea48a9df764becdfecc2a85b4f31"
FAMILIES = (
    "alpine-baselayout", "apk-tools", "busybox", "ca-certificates",
    "gdbm", "gcc", "musl", "readline", "pax-utils", "xz",
)
EXPECTED_LOCAL_FILES = 142
EXPECTED_EXTERNAL_FILES = 24
SHA_RE = re.compile(r"^([0-9a-f]{128})[ \t]+(\S+)[ \t]*$", re.M)
BLOCK_RE = re.compile(r'^sha512sums="([\s\S]*?)"\s*$', re.M)


def audit(root):
    reports = []
    checked = 0
    remote = 0
    for family in FAMILIES:
        folder = root / "main" / family
        recipe = folder / "APKBUILD"
        if not recipe.is_file():
            raise ValueError(f"Missing recipe for {family}")
        content = recipe.read_text(encoding="utf-8")
        block = BLOCK_RE.search(content)
        if not block:
            raise ValueError(f"Missing sha512sums for {family}")
        values = SHA_RE.findall(block.group(1))
        total_lines = [line for line in block.group(1).splitlines() if line.strip()]
        if not values or len(values) != len(total_lines):
            raise ValueError(f"Unrecognized SHA-512 entry in {family}")
        found, missing = 0, []
        for digest, filename in values:
            # No paths outside the exact source directory may be checked.
            if filename != Path(filename).name or filename.startswith("."):
                raise ValueError(f"Unsafe source name in {family}: {filename}")
            file = folder / filename
            if not file.exists():
                missing.append(filename)
                continue
            if not file.is_file() or file.is_symlink():
                raise ValueError(f"Non-regular local source: {family}/{filename}")
            actual = hashlib.sha512(file.read_bytes()).hexdigest()
            if actual != digest:
                raise ValueError(f"SHA-512 mismatch: {family}/{filename}")
            found += 1
        reports.append({
            "family": family, "checksum_entries": len(values),
            "local_sha512_verified": found,
            "external_source_entries_unverified": missing,
        })
        checked += found
        remote += len(missing)
    if checked != EXPECTED_LOCAL_FILES or remote != EXPECTED_EXTERNAL_FILES:
        raise ValueError(f"Unexpected source inventory: {checked} local, {remote} external")
    return {
        "aports_commit": APORTS_COMMIT,
        "scope": "PINNED_APORTS_LOCAL_AUXILIARY_FILES_ONLY",
        "license_approved": False,
        "source_archives_verified": False,
        "local_files_sha512_verified": checked,
        "external_entries_unverified": remote,
        "families": reports,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("aports_tree", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    try:
        report = audit(args.aports_tree)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    except (ValueError, OSError) as exc:
        print(f"ALPINE SOURCE INTEGRITY BLOCKED: {exc}", file=sys.stderr)
        return 1
    print(f"Local Alpine SHA-512 checks: {report['local_files_sha512_verified']} OK; "
          f"{report['external_entries_unverified']} external entries UNVERIFIED; "
          "NO LICENSE APPROVAL")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
