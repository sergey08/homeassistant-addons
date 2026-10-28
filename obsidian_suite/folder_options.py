"""Safely save this app's own vault_path through the Home Assistant Supervisor API."""
import json
import os
from pathlib import Path
from urllib.request import Request, urlopen
from vault_selection import select_vault


def save_local_vault(path: str, *, token=None, root=Path("/share"), endpoint="http://supervisor/addons/self/options"):
    selected = select_vault(path, root / "default", root)
    token = token if token is not None else os.environ.get("SUPERVISOR_TOKEN", "")
    if not token:
        raise RuntimeError("Supervisor API token unavailable")
    data = json.dumps({"options": {"storage_mode": "local", "vault_path": str(selected)}}).encode()
    req = Request(endpoint, data=data, headers={
        "Authorization": "Bearer " + token,
        "Content-Type": "application/json",
    }, method="POST")
    with urlopen(req, timeout=8) as response:
        result = json.load(response)
    if result.get("result") != "ok":
        raise RuntimeError("Supervisor rejected configuration change")
    return str(selected)
