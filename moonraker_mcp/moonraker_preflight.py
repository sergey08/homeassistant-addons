"""Read-only filament preflight; never invents a T0-T3 ↔ Spoolman link.

A client supplies explicit per-tool planned grams and spool IDs that a human
has verified. No NFC/colour heuristic is accepted as proof of an assignment.
No writes, printer starts, inventory changes or automatic consumption.
"""
import math
from moonraker_spoolman import list_spoolman_inventory

TOOLS = frozenset(("T0", "T1", "T2", "T3"))
MAX_GRAMS = 10000
MARGIN_FRACTION = 0.10
MARGIN_GRAMS = 10.0


class PreflightError(ValueError):
    pass


def validate_plan(requirements_g, spool_ids):
    if not isinstance(requirements_g, dict) or not requirements_g or len(requirements_g) > 4:
        raise PreflightError("Provide planned grams for one to four tools")
    if not isinstance(spool_ids, dict) or len(spool_ids) > 4:
        raise PreflightError("Spool assignments must be an object")
    if not set(requirements_g).issubset(TOOLS) or not set(spool_ids).issubset(TOOLS):
        raise PreflightError("Only T0, T1, T2 and T3 are supported")
    if not set(spool_ids).issubset(requirements_g):
        raise PreflightError("Unexpected spool assignment without a planned weight")
    for key, value in requirements_g.items():
        if type(value) not in (int, float) or not math.isfinite(value) or not (0 < value <= MAX_GRAMS):
            raise PreflightError("Planned grams must be finite positive numbers")
    ids = list(spool_ids.values())
    if any(type(i) is not int or i <= 0 for i in ids) or len(set(ids)) != len(ids):
        raise PreflightError("Spool IDs must be distinct positive integers")
    return True


def evaluate_preflight(requirements_g, spool_ids, inventory):
    """Evaluate human-provided mappings only. Unknowns never produce a pass."""
    validate_plan(requirements_g, spool_ids)
    if not isinstance(inventory, dict) or not isinstance(inventory.get("spools"), list):
        raise PreflightError("Spoolman inventory unavailable")
    by_id = {x.get("id"): x for x in inventory["spools"] if isinstance(x, dict) and type(x.get("id")) is int}
    results = []
    for tool in sorted(requirements_g):
        required = float(requirements_g[tool])
        reserve = max(MARGIN_GRAMS, required * MARGIN_FRACTION)
        planned_with_reserve = round(required + reserve, 2)
        spool_id = spool_ids.get(tool)
        spool = by_id.get(spool_id) if spool_id is not None else None
        remaining = spool.get("remaining_weight_g") if spool is not None else None
        if spool_id is None:
            result = "unknown_mapping"
        elif spool is None:
            result = "spool_not_found"
        elif spool.get("archived") is True:
            result = "archived_spool"
        elif type(remaining) not in (float, int) or not math.isfinite(remaining) or remaining < 0:
            result = "unknown_remaining"
        elif remaining < planned_with_reserve:
            result = "insufficient"
        else:
            result = "sufficient"
        results.append({
            "tool": tool,
            "supplied_spool_id": spool_id,
            "required_g": round(required, 2),
            "reserve_g": round(reserve, 2),
            "required_with_reserve_g": planned_with_reserve,
            "remaining_g": remaining if type(remaining) in (int, float) and math.isfinite(remaining) else None,
            "assessment": result,
        })
    return {
        "can_confirm_sufficient": bool(results) and all(x["assessment"] == "sufficient" for x in results),
        "results": results,
        "mapping_source": "user_supplied_not_verified_by_printer",
        "requirements_source": "user_supplied_slicer_estimates",
        "safety_note": (
            "Read-only estimate. Confirm each physical T0-T3 spool assignment, "
            "material/color and slicer weight before printing. No print is started."
        ),
    }


def check_preflight(moonraker_url, api_key, requirements_g, spool_ids, opener=None):
    validate_plan(requirements_g, spool_ids)
    inventory = list_spoolman_inventory(moonraker_url, api_key, opener)
    return evaluate_preflight(requirements_g, spool_ids, inventory)
