"""Narrow, read-only Spoolman inventory retrieval via Moonraker's proxy.

The *outer* HTTP POST is required by Moonraker's proxy endpoint, but the
hard-coded inner Spoolman method is GET. No caller-supplied path/method/body.
Never forwards arbitrary fields or large inventory payloads to the MCP client.
"""
import json
import math
import urllib.error
import urllib.request

from moonraker_files import FileAccessError, _NoRedirect, validate_base_url

MAX_RESPONSE_BYTES = 256 * 1024
MAX_SPOOLS = 100
MAX_NAME_LENGTH = 100


class SpoolmanReadError(ValueError):
    pass


def _safe_text(value):
    if not isinstance(value, str):
        return None
    value = "".join(ch for ch in value if ch.isprintable()).strip()
    return value[:MAX_NAME_LENGTH]


def _safe_nonnegative(value):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    if not math.isfinite(value) or value < 0:
        return None
    return round(value, 2)


def _clean_spool(spool):
    if not isinstance(spool, dict):
        raise SpoolmanReadError("Invalid Spoolman spool record")
    spool_id = spool.get("id")
    if isinstance(spool_id, bool) or not isinstance(spool_id, int) or spool_id < 0:
        raise SpoolmanReadError("Invalid Spoolman spool identifier")
    filament = spool.get("filament")
    filament = filament if isinstance(filament, dict) else {}
    vendor = filament.get("vendor")
    vendor = vendor if isinstance(vendor, dict) else {}
    output = {
        "id": spool_id,
        "archived": spool.get("archived") is True,
        "filament": {
            "name": _safe_text(filament.get("name")),
            "material": _safe_text(filament.get("material")),
            "vendor": _safe_text(vendor.get("name")),
            "color_hex": _safe_text(filament.get("color_hex")),
        },
        "remaining_weight_g": _safe_nonnegative(spool.get("remaining_weight")),
        "used_weight_g": _safe_nonnegative(spool.get("used_weight")),
        "initial_weight_g": _safe_nonnegative(spool.get("initial_weight")),
    }
    return output


def list_spoolman_inventory(moonraker_url, moonraker_api_key="", opener=None):
    """List max 100 spools, using only Spoolman GET /v1/spool via Moonraker.

    Reuses existing Moonraker configuration. Never accepts an arbitrary
    URL, spool path, or method from the MCP caller. Never exposes raw data.
    """
    try:
        base = validate_base_url(moonraker_url)
    except FileAccessError as exc:
        raise SpoolmanReadError("Invalid Moonraker URL") from exc

    payload = json.dumps({
        "request_method": "GET",
        "path": "/v1/spool",
        "use_v2_response": True,
    }, separators=(",", ":")).encode("utf-8")
    headers = {"Content-Type": "application/json", "Accept": "application/json"}
    if moonraker_api_key:
        headers["X-Api-Key"] = moonraker_api_key
    req = urllib.request.Request(base + "/server/spoolman/proxy",
                                 data=payload, headers=headers, method="POST")
    if opener is None:
        opener = urllib.request.build_opener(_NoRedirect()).open
    with opener(req, timeout=10) as response:
        raw = response.read(MAX_RESPONSE_BYTES + 1)
    if len(raw) > MAX_RESPONSE_BYTES:
        raise SpoolmanReadError("Spoolman response too large")
    try:
        result = json.loads(raw)
    except (ValueError, UnicodeError) as exc:
        raise SpoolmanReadError("Invalid Spoolman response") from exc
    if not isinstance(result, dict):
        raise SpoolmanReadError("Unexpected Moonraker proxy response")
    # HTTP Moonraker wraps JSON-RPC result in 'result'.
    body = result.get("result")
    if not isinstance(body, dict) or body.get("error") is not None:
        raise SpoolmanReadError("Spoolman unavailable or returned an error")
    spools = body.get("response")
    if not isinstance(spools, list):
        raise SpoolmanReadError("Spoolman inventory is not a list")
    # Fail closed on oversized arrays: do not silently claim a complete list.
    if len(spools) > MAX_SPOOLS:
        raise SpoolmanReadError("Spoolman inventory exceeds 100 spools")
    inventory = [_clean_spool(spool) for spool in spools]
    return {"count": len(inventory), "spools": inventory}
