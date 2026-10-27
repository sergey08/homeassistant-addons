#!/usr/bin/env python3
"""Manage the three Obsidian services without shell interpolation."""
import json
import os
import signal
import subprocess
from preflight import main as check_prerequisites
import sys
import time
import socket
from pathlib import Path

LEGACY_BASE = Path("/app_configs/obsidian_bridge")
DATA = Path("/data")
BASE = LEGACY_BASE if (LEGACY_BASE / "vault").is_dir() else DATA
CHILDREN = {}
STOPPING = False


def stop_all(*_args):
    global STOPPING
    STOPPING = True
    for name, proc in reversed(list(CHILDREN.items())):
        if proc.poll() is None:
            print(f"Stopping {name}", flush=True)
            proc.terminate()


signal.signal(signal.SIGTERM, stop_all)
signal.signal(signal.SIGINT, stop_all)


def start(name, argv, cwd=None, env=None):
    proc = subprocess.Popen(argv, cwd=cwd, env=env)
    CHILDREN[name] = proc
    print(f"Started {name} (pid={proc.pid})", flush=True)


def required(path, executable=False):
    if not path.is_file() or (executable and not os.access(path, os.X_OK)):
        raise RuntimeError(f"Missing required {'executable' if executable else 'file'}: {path}")
    return str(path)


def main():
    options = json.loads((DATA / "options.json").read_text(encoding="utf-8"))
    configured_vault = str(options.get("vault_path", "")).strip()
    if configured_vault:
        shared_root = Path("/share").resolve(strict=True)
        vault = Path(configured_vault)
        if not vault.is_absolute() or vault == Path("/share"):
            raise RuntimeError("vault_path must be an existing subfolder of /share")
        if not vault.is_dir() or vault.is_symlink():
            raise RuntimeError("Configured vault must be an existing real directory")
        vault = vault.resolve(strict=True)
        if not vault.is_relative_to(shared_root) or vault == shared_root:
            raise RuntimeError("Configured vault must stay inside /share")
    else:
        vault = BASE / "vault"
    trash = BASE / "mcp-trash"
    # Do not follow unexpected symbolic links when preparing persistent storage.
    for folder in ((trash,) if configured_vault else (vault, trash)):
        if folder.is_symlink():
            raise RuntimeError(f"Managed storage path must not be a symbolic link: {folder}")
        folder.mkdir(parents=True, exist_ok=True)
        if not folder.is_dir():
            raise RuntimeError(f"Managed storage path is not a directory: {folder}")
    print(f"Using persistent vault at {vault}", flush=True)
    check_prerequisites()
    for target, source in (("/vault", vault), ("/trash", trash)):
        p = Path(target)
        if p.is_symlink():
            if p.resolve() != source.resolve():
                raise RuntimeError(f"Unexpected link at {target}")
        elif p.exists():
            raise RuntimeError(f"Path already exists: {target}")
        else:
            p.symlink_to(source, target_is_directory=True)

    start("onboarding", ["/opt/venv/bin/python", "/opt/obsidian/onboarding.py"])
    start("mcp", ["/opt/venv/bin/python", "/opt/obsidian/server.py"])
    if options.get("enable_livesync", True):
        settings = BASE / "settings/livesync-operativo.json"
        required(settings)
        interval = int(options.get("livesync_interval", 60))
        if not 30 <= interval <= 3600:
            raise RuntimeError("Invalid LiveSync interval")
        # Docker-based LiveSync CLI uses LIVESYNC_DB_PATH to select its database.
        # Keep its PouchDB database distinct from the Markdown vault.
        db_path = BASE / "livesync-db"
        db_path.mkdir(parents=True, exist_ok=True)
        start("livesync", [
            "/usr/local/bin/livesync-cli", "--settings", str(settings),
            "--vault", str(vault), "--interval", str(interval)
        ], cwd=DATA, env={**os.environ, "LIVESYNC_DB_PATH": str(db_path)})
    if options.get("enable_tunnel", True):
        deadline = time.monotonic() + 30
        while time.monotonic() < deadline:
            if CHILDREN["mcp"].poll() is not None:
                raise RuntimeError("MCP server exited before becoming ready")
            try:
                with socket.create_connection(("127.0.0.1", 8765), timeout=1):
                    print("MCP TCP endpoint is ready", flush=True)
                    break
            except OSError:
                time.sleep(0.5)
        else:
            raise RuntimeError("MCP server did not become ready within 30 seconds")
        tunnel_id = str(options.get("tunnel_id", "")).strip()
        if not tunnel_id:
            raise RuntimeError("Tunnel ID is required when tunnel is enabled")
        binary = required(BASE / "tunnel/bin/tunnel-client", executable=True)
        key = required(BASE / "tunnel/api-key")
        run_dir = BASE / "tunnel/run"
        run_dir.mkdir(parents=True, exist_ok=True)
        start("tunnel", [
            binary, "run",
            "--control-plane.tunnel-id", tunnel_id,
            "--control-plane.api-key", "file:" + key,
            "--mcp.server-url", "channel=main,url=http://127.0.0.1:8765/mcp",
            "--health.listen-addr", "127.0.0.1:0",
            "--health.url-file", str(run_dir / "health.url")
        ])
    while not STOPPING:
        for name, proc in CHILDREN.items():
            code = proc.poll()
            if code is not None:
                print(f"ERROR: {name} exited with code {code}; stopping all services", flush=True)
                stop_all()
                break
        time.sleep(2)
    for proc in CHILDREN.values():
        if proc.poll() is None:
            try:
                proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait()
    return 1 if any(p.returncode for p in CHILDREN.values()) else 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as error:
        print(f"ERROR: {error}", file=sys.stderr, flush=True)
        stop_all()
        sys.exit(1)
