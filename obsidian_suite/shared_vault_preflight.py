#!/usr/bin/env python3
"""Read-only verification for a planned MCP LiveSync Markdown vault migration.

No copy, move, delete, restart, CouchDB connection or configuration write.
Run with source and destination AFTER a separate, backed-up copy.
"""
import argparse
import hashlib
import json
from pathlib import Path


def snapshot(root):
    root = Path(root)
    if not root.is_absolute() or root.is_symlink() or not root.is_dir():
        raise ValueError("Vault must be an existing absolute real directory")
    base = root.resolve(strict=True)
    files = {}
    for item in base.rglob("*"):
        rel = item.relative_to(base).as_posix()
        if item.is_symlink():
            raise ValueError(f"Symlink not supported: {rel}")
        if not item.is_file():
            if not item.is_dir():
                raise ValueError(f"Unsupported file type: {rel}")
            continue
        if not item.resolve(strict=True).is_relative_to(base):
            raise ValueError(f"Outside vault: {rel}")
        digest = hashlib.sha256()
        with item.open("rb") as stream:
            for block in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(block)
        files[rel] = (item.stat().st_size, digest.hexdigest())
    return files


def compare(source, destination):
    origin = snapshot(source)
    target = snapshot(destination)
    missing = sorted(set(origin) - set(target))
    unexpected = sorted(set(target) - set(origin))
    modified = sorted(p for p in origin.keys() & target.keys() if origin[p] != target[p])
    return {
        "status": "identical" if not (missing or unexpected or modified) else "different",
        "source_files": len(origin),
        "destination_files": len(target),
        "missing": missing,
        "unexpected": unexpected,
        "different_content": modified,
        "markdown_files": sum(p.lower().endswith(".md") for p in origin),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", help="Original MCP vault, absolute path")
    parser.add_argument("destination", help="Prepared shared vault, absolute path")
    args = parser.parse_args()
    try:
        if Path(args.source).resolve() == Path(args.destination).resolve():
            raise ValueError("Source and destination must be different directories")
        report = compare(args.source, args.destination)
    except (OSError, ValueError) as exc:
        print(json.dumps({"status": "error", "message": str(exc)}, ensure_ascii=False))
        return 2
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["status"] == "identical" and report["markdown_files"] > 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
