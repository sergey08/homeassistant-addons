#!/usr/bin/env python3
"""Non-destructive first-run diagnostics. Never print credential contents."""
import json
import os
from pathlib import Path
from vault_selection import select_storage

OWNED = Path("/data")
LEGACY = Path("/app_configs/obsidian_bridge")
BASE = LEGACY if (LEGACY / "vault").is_dir() else OWNED

def status(label, ok, hint):
    print(f"[{'OK' if ok else 'SETUP REQUIRED'}] {label}" + ("" if ok else f" — {hint}"))

def main():
    config = OWNED / "options.json"
    try:
        options = json.loads(config.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        options = {}
    try:
        mode, vault, sync_enabled = select_storage(options, BASE / "vault")
        status(f"Vault directory ({mode})", vault.is_dir(), "Check the configured folder")
    except (ValueError, OSError) as exc:
        status("Vault directory", False, str(exc))
        sync_enabled = False
    status("Private trash", (BASE / "mcp-trash").is_dir(), "Created automatically on first start")
    if sync_enabled:
        settings = BASE / "settings/livesync-operativo.json"
        status("LiveSync settings", settings.is_file() and settings.stat().st_size > 0,
               "Import a Self-hosted LiveSync setup URI before enabling sync")
        # Do not attempt authentication or a remote sync from a diagnostic command.
    else:
        print("[DISABLED] LiveSync: local mode or sync disabled")
    if options.get("enable_tunnel", False):
        binary = BASE / "tunnel/bin/tunnel-client"
        key = BASE / "tunnel/api-key"
        status("Tunnel executable", binary.is_file() and os.access(binary, os.X_OK),
               "Provision the official client binary")
        status("Tunnel key file", key.is_file() and key.stat().st_size > 0,
               "Provision a runtime key privately")
        status("Tunnel ID", bool(str(options.get("tunnel_id", "")).strip()),
               "Set the ID in the add-on Configuration tab")
    else:
        print("[DISABLED] OpenAI tunnel: configure a runtime key and tunnel ID first")
    print("Preflight is read-only; no remote database or vault notes were modified.")

if __name__ == "__main__":
    main()
