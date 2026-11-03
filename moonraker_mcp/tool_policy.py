"""Fail-closed MCP tool policy for the future HTTP gateway.

This module does not expose a network service. Until a gateway uses it on
both tools/list and tools/call, the add-on MUST NOT be deployed.
"""
import json
from pathlib import Path

POLICY_PATH = Path(__file__).with_name("read_only_allowlist.json")
OPTIONAL_PROFILES = {
    "files": frozenset(("moonraker_files_list", "moonraker_files_metadata")),
    "objects": frozenset(("moonraker_objects_list", "moonraker_objects_query")),
    "history": frozenset(("moonraker_history_list", "moonraker_history_job", "moonraker_history_totals")),
    "sensors": frozenset(("moonraker_sensors_info", "moonraker_sensors_list", "moonraker_sensors_measurements")),
    "spoolman": frozenset(("moonraker_spoolman_status", "moonraker_spoolman_get_spool")),
    "power": frozenset(("moonraker_power_status",)),
}


def extend_allowed(base, profiles):
    """Explicit opt-in only; unknown profiles fail closed."""
    if not isinstance(profiles, list) or any(not isinstance(p, str) or p not in OPTIONAL_PROFILES for p in profiles):
        raise PolicyError("Unknown optional read-only profile")
    allowed = set(base)
    for profile in profiles:
        allowed.update(OPTIONAL_PROFILES[profile])
    return frozenset(allowed)



class PolicyError(ValueError):
    pass


def load_allowed(path=POLICY_PATH):
    policy = json.loads(Path(path).read_text(encoding="utf-8"))
    if policy.get("policy_version") != 1:
        raise PolicyError("Unsupported policy version")
    names = policy.get("allowed_tools")
    if not isinstance(names, list) or not names or any(
        not isinstance(n, str) or not n.startswith("moonraker_") for n in names
    ):
        raise PolicyError("Invalid tool allowlist")
    if len(names) != len(set(names)):
        raise PolicyError("Duplicate tools in allowlist")
    return frozenset(names)


def filter_tools(tools, allowed):
    """Only explicitly allowed tools can appear in tools/list."""
    if not isinstance(tools, list):
        raise PolicyError("Malformed upstream tools/list response")
    seen = set()
    visible = []
    for tool in tools:
        if not isinstance(tool, dict) or not isinstance(tool.get("name"), str):
            raise PolicyError("Malformed upstream tool entry")
        name = tool["name"]
        if name in seen:
            raise PolicyError("Duplicate upstream tool name")
        seen.add(name)
        if name in allowed:
            visible.append(tool)
    return visible


def authorize_call(name, allowed):
    """Enforce again on tools/call, never rely on hiding tool descriptions."""
    if not isinstance(name, str) or name not in allowed:
        raise PolicyError("Tool is not permitted by read-only policy")
    return True
