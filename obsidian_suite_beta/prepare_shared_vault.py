#!/usr/bin/env python3
"""Prepare separate backup and shared-vault copies without modifying the source.

IMPORTANT: stop MCP/LiveSync and all writers first. This utility deliberately
does not stop services or activate any new Home Assistant options.
Default invocation only validates and prints intended actions.
"""
import argparse
import json
import shutil
from pathlib import Path

from shared_vault_preflight import compare, snapshot


def prepare(source, backup, shared, execute=False):
    source, backup, shared = map(Path, (source, backup, shared))
    roots = [p.resolve(strict=False) for p in (source, backup, shared)]
    if len(set(roots)) != 3:
        raise ValueError("The three directories must be distinct")
    if source.is_symlink() or not source.is_dir():
        raise ValueError("Source must be an existing non-symlink directory")
    # Prohibit destination nesting (including a destination inside the source).
    for a in roots:
        for b in roots:
            if a != b and (a.is_relative_to(b) or b.is_relative_to(a)):
                raise ValueError("Directories must not contain each other")
    if backup.exists() or backup.is_symlink() or shared.exists() or shared.is_symlink():
        raise ValueError("Backup and shared destinations must not already exist")
    if backup.parent.resolve(strict=True) == shared.parent.resolve(strict=True):
        pass
    source_before = snapshot(source)  # rejects symlinks and special files
    if not any(p.lower().endswith(".md") for p in source_before):
        raise ValueError("Source contains no Markdown notes")
    result = {"mode": "execute" if execute else "dry_run",
              "source": str(source), "backup": str(backup), "shared": str(shared),
              "source_files": len(source_before),
              "markdown_notes": sum(p.lower().endswith(".md") for p in source_before)}
    if not execute:
        return result
    shutil.copytree(source, backup, symlinks=False)
    backup_report = compare(source, backup)
    if backup_report["status"] != "identical":
        raise RuntimeError("Backup mismatch; shared vault not created")
    # Guard against source edits during the copy.
    if snapshot(source) != source_before:
        raise RuntimeError("Source changed while backup was made; shared vault not created")
    shutil.copytree(source, shared, symlinks=False)
    shared_report = compare(source, shared)
    if shared_report["status"] != "identical" or snapshot(source) != source_before:
        raise RuntimeError("Shared vault verification failed; do not activate it")
    result.update(status="verified", backup_files=backup_report["destination_files"],
                  shared_files=shared_report["destination_files"])
    return result


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("source")
    ap.add_argument("backup")
    ap.add_argument("shared")
    ap.add_argument("--execute", action="store_true",
                    help="Explicitly copy; do not use while any vault writer is running")
    args = ap.parse_args()
    try:
        result = prepare(args.source, args.backup, args.shared, execute=args.execute)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except (OSError, ValueError, RuntimeError) as exc:
        print(json.dumps({"status": "error", "message": str(exc)}, ensure_ascii=False))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
