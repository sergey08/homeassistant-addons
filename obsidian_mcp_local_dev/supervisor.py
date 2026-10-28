#!/usr/bin/env python3
"""Manage the three Obsidian services without shell interpolation."""
import json
import os
import signal
import subprocess
from preflight import main as check_prerequisites
from vault_selection import select_storage
import sys
import time
import socket
from pathlib import Path

LEGACY_BASE = Path("/data")
DATA = Path("/data")
BASE = DATA
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
    mode, vault, run_livesync = select_storage(options, BASE / "vault")
    configured_vault = mode == "local"
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
    if run_livesync:
        raise RuntimeError("LiveSync is disabled in this isolated development app")
    if False:
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
    if options.get("enable_tunnel", False):
        deadline = time.monotonic() + 30
        while time.monotonic() < deadline:
            if CHILDREN["mcp"].poll() is not None:
                raise RuntimeError("MCP server exited before tunnel readiness")
            try:
                with socket.create_connection(("127.0.0.1", 8765), timeout=1):
                    break
            except OSError:
                time.sleep(0.5)
        else:
            raise RuntimeError("MCP not ready")
        tunnel_id = str(options.get("tunnel_id", "")).strip()
        if not tunnel_id:
            raise RuntimeError("Tunnel ID required")
        # Existing production provisioned credentials are mounted read-only.
        # The development app writes only its own runtime files to /data.
        credentials = Path("/app_configs/obsidian_bridge/tunnel")
        binary = required(credentials / "bin/tunnel-client", executable=True)
        key = required(credentials / "api-key")
        run_dir = DATA / "tunnel/run"
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
