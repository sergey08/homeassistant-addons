"""Verify GNU Readline 8.2 numbered upstream patches from pinned Alpine recipe.

Scope: 13 dynamically sourced patches only. No execution, no credentials,
no redistribution-license approval. HTTPS downloads are size-limited.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import sys
from urllib.request import urlopen

APORTS_COMMIT = "2235ae248c31ea48a9df764becdfecc2a85b4f31"
SOURCE_BASE = "https://ftp.gnu.org/gnu/readline/readline-8.2-patches/"
PATCH_COUNT = 13
MAX_BYTES = 2 * 1024 * 1024
CHECKSUM_PATTERN = re.compile(r"^([0-9a-f]{128})\s+(readline82-(\d{3})\.patch)$", re.M)


def audit(recipe_path):
    text = recipe_path.read_text(encoding="utf-8")
    if "pkgver=8.2.13" not in text or "pkgrel=1" not in text:
        raise ValueError("Unexpected pinned Readline version")
    block = re.search(r'^sha512sums="([\s\S]*?)"\s*$', text, re.M)
    if not block:
        raise ValueError("Missing Alpine checksums")
    matches = CHECKSUM_PATTERN.findall(block.group(1))
    if len(matches) != PATCH_COUNT:
        raise ValueError(f"Expected 13 upstream patches, got {len(matches)}")
    verified = []
    for index, (expected, filename, num) in enumerate(matches, 1):
        if int(num) != index:
            raise ValueError(f"Unexpected patch order: {filename}")
        # APKBUILD defines local alias filename.patch::URL-without-extension.
        url = SOURCE_BASE + filename.removesuffix(".patch")
        with urlopen(url, timeout=45) as response:
            if response.geturl() != url:
                raise ValueError(f"Unexpected redirect for {filename}")
            data = response.read(MAX_BYTES + 1)
        if len(data) > MAX_BYTES or not data:
            raise ValueError(f"Invalid payload size: {filename}")
        actual = hashlib.sha512(data).hexdigest()
        if actual != expected:
            raise ValueError(f"SHA-512 mismatch: {filename}")
        verified.append({"name": filename, "sha512": actual, "url": url, "bytes": len(data)})
    return {
        "scope": "GNU_READLINE_8_2_PATCHES_ONLY",
        "aports_commit": APORTS_COMMIT,
        "source_recipe": "main/readline/APKBUILD",
        "verified_remote_sha512": len(verified),
        "other_remote_entries_not_verified_by_this_script": 11,
        "license_approved": False,
        "verified": verified,
    }


def main():
    p = argparse.ArgumentParser()
    p.add_argument("recipe", type=Path)
    p.add_argument("report", type=Path)
    args = p.parse_args()
    try:
        report = audit(args.recipe)
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    except (ValueError, OSError, TimeoutError) as exc:
        print(f"GNU PATCH INTEGRITY BLOCKED: {exc}", file=sys.stderr)
        return 1
    print(f"Verified {report['verified_remote_sha512']} external GNU Readline patches; no license clearance")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
