"""Read-only bounded Snapmaker/Klipper print status and four-slot filament snapshot.

No write APIs, no G-code. Only a fixed set of objects is queried from
Moonraker. Private NFC UIDs, absolute paths and arbitrary macro variables
are deliberately not returned.
"""
import math
import urllib.parse

from moonraker_files import FileAccessError, _read_json, validate_base_url

ALLOWED_STATES = frozenset(("standby", "printing", "paused", "complete", "cancelled", "error"))
MAX_NAME = 180


class SnapshotError(ValueError):
    pass


def _finite(value, minimum=0, maximum=10**9):
    if type(value) not in (float, int) or not math.isfinite(value) or not minimum <= value <= maximum:
        return None
    return round(value, 3)


def _label(value, maximum=MAX_NAME):
    if type(value) is not str:
        return None
    return "".join(ch for ch in value if ch.isprintable())[:maximum]


def _progress(value):
    n = _finite(value, 0, 1)
    return round(n * 100, 1) if n is not None else None


def _color(value):
    if type(value) is not int or not 0 <= value <= 0xFFFFFFFF:
        return None
    return f"{value & 0xFFFFFF:06X}"


def normalize_print_status(status):
    if not isinstance(status, dict):
        raise SnapshotError("Invalid Klipper status")
    ps = status.get("print_stats")
    sd = status.get("virtual_sdcard")
    disp = status.get("display_status")
    head = status.get("toolhead")
    if not all(isinstance(obj, dict) for obj in (ps, sd, disp, head)):
        raise SnapshotError("Missing print status objects")
    raw_state = ps.get("state")
    state = raw_state if raw_state in ALLOWED_STATES else "unknown"
    info = ps.get("info")
    info = info if isinstance(info, dict) else {}
    active_tool = head.get("extruder")
    if active_tool not in ("extruder", "extruder1", "extruder2", "extruder3"):
        active_tool = None
    return {
        "state": state,
        "filename": _label(ps.get("filename")),
        "active_tool": {"extruder": "T0", "extruder1": "T1",
                        "extruder2": "T2", "extruder3": "T3"}.get(active_tool),
        "print_duration_s": _finite(ps.get("print_duration")),
        "total_duration_s": _finite(ps.get("total_duration")),
        "filament_used_raw": _finite(ps.get("filament_used")),
        "current_layer": _finite(info.get("current_layer"), 0, 100000),
        "total_layers": _finite(info.get("total_layer"), 0, 100000),
        "display_progress_pct": _progress(disp.get("progress")),
        "file_progress_pct": _progress(sd.get("progress")),
        "file_active": sd.get("is_active") is True,
        "eta_seconds": None,
        "eta_note": "ETA unavailable without a reliable slicer estimate; display/file progress may differ",
    }


def normalize_filament_slots(status):
    if not isinstance(status, dict):
        raise SnapshotError("Invalid Klipper status")
    fd = status.get("filament_detect")
    if not isinstance(fd, dict) or not isinstance(fd.get("info"), list):
        return {"available": False, "slots": [], "reason": "filament_detect unavailable"}
    info = fd["info"]
    states = fd.get("state")
    if len(info) != 4 or not all(isinstance(item, dict) for item in info):
        raise SnapshotError("Invalid four-slot filament data")
    slots = []
    for index, item in enumerate(info):
        raw_state = (states[index] if isinstance(states, list) and len(states) == 4
                     and type(states[index]) is int else None)
        slots.append({
            "slot": f"T{index}",
            "material": _label(item.get("MAIN_TYPE"), 50),
            "subtype": _label(item.get("SUB_TYPE"), 50),
            "manufacturer": _label(item.get("MANUFACTURER"), 80),
            "color_hex": _color(item.get("ARGB_COLOR")),
            "detection_state_raw": raw_state,
            "spoolman_id": None,
        })
    return {
        "available": True,
        "slots": slots,
        "spoolman_mapping_note": (
            "Moonraker's single active Spoolman spool ID is not a verified "
            "mapping of the four physical T0-T3 slots"),
    }


def read_status(moonraker_url, moonraker_api_key="", opener=None):
    try:
        base = validate_base_url(moonraker_url)
    except FileAccessError as exc:
        raise SnapshotError("Invalid Moonraker URL") from exc
    # Fixed object names, no client-controlled requests or arbitrary fields.
    names = ("print_stats", "virtual_sdcard", "display_status", "toolhead", "filament_detect")
    url = base + "/printer/objects/query?" + "&".join(urllib.parse.quote(name, safe="") for name in names)
    data = _read_json(url, moonraker_api_key, opener)
    if not isinstance(data, dict) or not isinstance(data.get("status"), dict):
        raise SnapshotError("Missing Moonraker status payload")
    return data["status"]


def print_snapshot(url, key="", opener=None):
    return normalize_print_status(read_status(url, key, opener))


def filament_slots(url, key="", opener=None):
    return normalize_filament_slots(read_status(url, key, opener))
