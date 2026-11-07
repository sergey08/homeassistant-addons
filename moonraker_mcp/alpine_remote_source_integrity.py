"""Audit 11 pinned Alpine remote sources, preserving partial evidence.

The audit never treats missing downloads as verified and never provides legal
redistribution approval. All downloads are streamed and discarded after hashing.
"""
import argparse
import hashlib
import json
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import Request, urlopen

COMMIT = "2235ae248c31ea48a9df764becdfecc2a85b4f31"
MAX_BYTES = 250 * 1024 * 1024
ALLOWED_HOSTS = {
    "salsa.debian.org", "gitlab.alpinelinux.org", "busybox.net",
    "ftp.gnu.org", "gcc.gnu.org", "musl.libc.org",
    "dev.gentoo.org", "github.com",
}
CHUNK = 1024 * 1024


def verify_one(item):
    name, url, expected = item["file"], item["url"], item["sha512"]
    parsed = urlparse(url)
    if parsed.scheme != "https" or parsed.hostname not in ALLOWED_HOSTS:
        raise ValueError("Unexpected download host")
    if (not isinstance(expected, str) or len(expected) != 128
            or any(c not in "0123456789abcdef" for c in expected)):
        raise ValueError("Invalid expected checksum")
    digest = hashlib.sha512()
    size = 0
    with urlopen(Request(url, headers={"User-Agent": "MoonrakerMCP-SourceAudit/0.1"}), timeout=90) as response:
        if urlparse(response.geturl()).scheme != "https":
            raise ValueError("Non-HTTPS redirect")
        while True:
            part = response.read(CHUNK)
            if not part:
                break
            size += len(part)
            if size > MAX_BYTES:
                raise ValueError("Source exceeds size cap")
            digest.update(part)
    if not size:
        raise ValueError("Empty source archive")
    if digest.hexdigest() != expected:
        raise ValueError("SHA-512 mismatch")
    return {"file": name, "url": url, "sha512": digest.hexdigest(), "bytes": size, "status": "VERIFIED_SHA512"}


def audit(manifest_path):
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    items = manifest.get("items")
    if (manifest.get("aports_commit") != COMMIT
            or manifest.get("purpose") != "SOURCE_INTEGRITY_EVIDENCE_NOT_LICENSE_APPROVAL"
            or not isinstance(items, list) or len(items) != 11):
        raise ValueError("Wrong pinned Alpine inventory")
    if len({item.get("file") for item in items}) != 11:
        raise ValueError("Duplicate file identity")
    report = []
    for item in items:
        name = item.get("file", "unknown")
        try:
            record = verify_one(item)
            print(f"OK: {name} ({record['bytes']} bytes)", flush=True)
        except (OSError, ValueError, KeyError, TypeError, TimeoutError) as exc:
            # Preserve which URL failed, without accepting the source.
            record = {"file": name, "url": item.get("url"),
                      "status": "UNVERIFIED", "error_type": type(exc).__name__}
            print(f"UNVERIFIED: {name} ({type(exc).__name__})", flush=True)
        report.append(record)
    count = sum(r["status"] == "VERIFIED_SHA512" for r in report)
    return {"aports_commit": COMMIT, "scope": "REMOTE_ALPINE_SOURCE_BYTES_ONLY",
            "license_approved": False, "complete": count == 11,
            "verified_remote_sha512": count, "unverified": 11-count, "items": report}


def main():
    p = argparse.ArgumentParser()
    p.add_argument("manifest", type=Path)
    p.add_argument("report", type=Path)
    args = p.parse_args()
    try:
        result = audit(args.manifest)
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print(f"REMOTE SOURCE AUDIT BLOCKED: {type(exc).__name__}", flush=True)
        return 1
    print(f"Remote SHA512 checks: {result['verified_remote_sha512']}/11. No license approval.")
    return 0 if result["complete"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
