"""Verify explicitly inventoried Alpine remote source bytes against SHA-512.

Manual audit only; never considers a network failure a successful check and
never claims license approval. Downloads are streamed and not executed.
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


def audit(manifest_path):
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    items = manifest.get("items")
    if manifest.get("aports_commit") != COMMIT or not isinstance(items, list) or len(items) != 11:
        raise ValueError("Wrong pinned Alpine inventory")
    if len({item.get("file") for item in items}) != len(items):
        raise ValueError("Duplicate file identity")
    verified = []
    for item in items:
        name, url, expected = item["file"], item["url"], item["sha512"]
        u = urlparse(url)
        if u.scheme != "https" or u.hostname not in ALLOWED_HOSTS:
            raise ValueError("Unexpected download host")
        if not isinstance(expected, str) or len(expected) != 128 or any(c not in "0123456789abcdef" for c in expected):
            raise ValueError("Invalid expected checksum")
        sha = hashlib.sha512()
        count = 0
        with urlopen(Request(url, headers={"User-Agent": "MoonrakerMCP-SourceAudit/0.1"}), timeout=90) as response:
            final = urlparse(response.geturl())
            # Some source hosts serve archives via their CDN; allow only
            # HTTPS redirects and still require exact checksum matching.
            if final.scheme != "https":
                raise ValueError(f"Non-HTTPS redirect for {name}")
            while True:
                data = response.read(CHUNK)
                if not data:
                    break
                count += len(data)
                if count > MAX_BYTES:
                    raise ValueError(f"Source exceeds size cap: {name}")
                sha.update(data)
        actual = sha.hexdigest()
        if not count or actual != expected:
            raise ValueError(f"SHA-512 mismatch or empty file: {name}")
        verified.append({"file": name, "sha512": actual, "bytes": count, "url": url})
        print(f"OK: {name} ({count} bytes)", flush=True)
    return {
        "aports_commit": COMMIT,
        "scope": "REMOTE_ALPINE_SOURCE_BYTES_ONLY",
        "license_approved": False,
        "verified_remote_sha512": len(verified),
        "items": verified,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("manifest", type=Path)
    parser.add_argument("report", type=Path)
    args = parser.parse_args()
    try:
        result = audit(args.manifest)
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print(f"REMOTE SOURCE AUDIT BLOCKED: {type(exc).__name__}: {exc}", flush=True)
        return 1
    print("All 11 SHA512 checks passed. This does NOT approve license redistribution.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
