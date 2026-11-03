"""Fail-closed MCP tool policy for the future HTTP gateway.

This module does not expose a network service. Until a gateway uses it on
both tools/list and tools/call, the add-on MUST NOT be deployed.
"""
import json
from pathlib import Path

POLICY_PATH = Path(__file__).with_name("read_only_allowlist.json")


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
