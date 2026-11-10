"""Opt-in, restricted Moonraker print operations; never used during CI.

All control calls require a named tool, matching confirmation phrase, and a
fresh read of Klipper's current state before posting to a fixed endpoint.
No arbitrary HTTP paths, G-code, filenames with traversal or upload/delete.
"""
import json
import urllib.error
import urllib.parse
import urllib.request

from moonraker_files import FileAccessError, _NoRedirect, validate_base_url, validate_filename, _read_json

class PrintControlError(ValueError):
    pass

ACTIONS = {
    "pause": {"allowed": frozenset(("printing",)), "endpoint": "/printer/print/pause"},
    "resume": {"allowed": frozenset(("paused",)), "endpoint": "/printer/print/resume"},
    "cancel": {"allowed": frozenset(("printing", "paused")), "endpoint": "/printer/print/cancel"},
    "start": {"allowed": frozenset(("standby", "complete", "cancelled")), "endpoint": "/printer/print/start"},
}
MAX_RESPONSE_BYTES = 16384


def _state(base, key, opener):
    # Klipper ready + print_stats state must both be present. Fail closed.
    try:
        response = _read_json(base + "/printer/objects/query?webhooks&print_stats", key, opener)
    except (FileAccessError, ValueError) as exc:
        raise PrintControlError("Printer state unavailable") from exc
    if not isinstance(response, dict) or not isinstance(response.get("status"), dict):
        raise PrintControlError("Printer state unavailable")
    status = response["status"]
    webhooks = status.get("webhooks")
    stats = status.get("print_stats")
    if not isinstance(webhooks, dict) or webhooks.get("state") != "ready":
        raise PrintControlError("Klipper not ready")
    if not isinstance(stats, dict) or not isinstance(stats.get("state"), str):
        raise PrintControlError("Print state unavailable")
    return stats


def execute_print_action(moonraker_url, moonraker_api_key, action, confirmation,
                         filename=None, expected_filename=None, opener=None):
    """Execute exactly one allowed control action after validating fresh state.

    Confirmation is a second explicit argument, not proof of user consent;
    clients must still obtain human approval before calling a write tool.
    """
    if type(action) is not str or action not in ACTIONS:
        raise PrintControlError("Unsupported print action")
    if confirmation != "CONFIRM_" + action.upper():
        raise PrintControlError("Explicit action confirmation required")
    if action == "start":
        try:
            filename = validate_filename(filename)
        except FileAccessError as exc:
            raise PrintControlError("Invalid G-code filename") from exc
        if not filename.lower().endswith((".gcode", ".gco")):
            raise PrintControlError("Only G-code print files are permitted")
        if expected_filename is not None:
            raise PrintControlError("Unexpected expected filename")
    elif filename is not None:
        raise PrintControlError("Unexpected filename")
    if action == "cancel":
        try:
            expected_filename = validate_filename(expected_filename)
        except FileAccessError as exc:
            raise PrintControlError("Expected current filename is required") from exc
    elif expected_filename is not None:
        raise PrintControlError("Unexpected expected filename")
    try:
        base = validate_base_url(moonraker_url)
    except FileAccessError as exc:
        raise PrintControlError("Invalid Moonraker URL") from exc
    if opener is None:
        opener = urllib.request.build_opener(_NoRedirect()).open

    stats = _state(base, moonraker_api_key, opener)
    state = stats["state"]
    if state not in ACTIONS[action]["allowed"]:
        raise PrintControlError("Printer state does not allow requested action")
    if action == "cancel" and stats.get("filename") != expected_filename:
        raise PrintControlError("Current print does not match expected filename")
    # Verify that the exact requested G-code exists *before* starting; an
    # arbitrary filename supplied by an MCP client is never enough.
    if action == "start":
        try:
            metadata_url = base + "/server/files/metadata?" + urllib.parse.urlencode({"filename": filename})
            metadata = _read_json(metadata_url, moonraker_api_key, opener)
        except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError,
                FileAccessError, ValueError, UnicodeError) as exc:
            raise PrintControlError("Requested G-code could not be verified") from exc
        if not isinstance(metadata, dict) or not isinstance(metadata.get("size"), (int, float)) or metadata["size"] <= 0:
            raise PrintControlError("G-code metadata missing or empty")
    endpoint = ACTIONS[action]["endpoint"]
    if action == "start":
        endpoint += "?" + urllib.parse.urlencode({"filename": filename})
    headers = {"Accept": "application/json"}
    if moonraker_api_key:
        headers["X-Api-Key"] = moonraker_api_key
    req = urllib.request.Request(base + endpoint, data=b"", headers=headers, method="POST")
    with opener(req, timeout=10) as response:
        raw = response.read(MAX_RESPONSE_BYTES + 1)
    if len(raw) > MAX_RESPONSE_BYTES:
        raise PrintControlError("Printer response too large")
    try:
        parsed = json.loads(raw)
    except (ValueError, UnicodeError) as exc:
        raise PrintControlError("Invalid Moonraker response") from exc
    if not isinstance(parsed, dict) or parsed.get("result") != "ok":
        raise PrintControlError("Moonraker did not confirm operation")
    return {"accepted": True, "action": action, "previous_state": state,
            "note": "Moonraker accepted request; verify current printer state before claiming completion"}
