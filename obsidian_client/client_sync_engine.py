"""Fail-closed, read-only preflight for the Client's OWN LiveSync engine.

The Client and MCP must never share a local vault or CLI database.
No CLI subprocess, remote write, local file creation, or settings installation
is performed here. Remote synchronization remains disabled until tested.
"""
from pathlib import Path

CLIENT_VAULT = Path("/data/obsidian-client-livesync-vault")
CLIENT_DB = Path("/data/livesync-client")
MCP_SHARED = Path("/share/obsidian-shared-vault")
CLI_BIN = Path("/opt/livesync-cli/dist/index.cjs")


def _overlap(a, b):
    a, b = Path(a).resolve(strict=False), Path(b).resolve(strict=False)
    return a == b or a in b.parents or b in a.parents


def preflight(config, *, vault=CLIENT_VAULT, database=CLIENT_DB,
              mcp_vault=MCP_SHARED, cli=CLI_BIN):
    """Return finite, safe status tokens, never credentials or document content."""
    from livesync_cli_bridge import validate_remote_configuration
    mode = str(config.get("editor_storage_mode", "private"))
    safe_paths = all(Path(p).is_absolute() and not Path(p).is_symlink()
                     for p in (vault, database))
    independent = (safe_paths and not _overlap(vault, database)
                   and not _overlap(vault, mcp_vault)
                   and not _overlap(database, mcp_vault))
    # Existing local settings need no secrets returned in the browser.
    db = Path(database)
    settings = db / ".livesync" / "settings.json"
    settings_ready = (db.is_dir() and not db.is_symlink()
                      and settings.is_file() and not settings.is_symlink())
    cli_ready = Path(cli).is_file() and not Path(cli).is_symlink()
    remote = validate_remote_configuration(config)
    complete = bool(remote.get("configuration_complete", False))
    reasons = []
    if mode != "livesync":
        reasons.append("independent_mode_not_selected")
    if not independent:
        reasons.append("storage_not_isolated")
    if not cli_ready:
        reasons.append("official_cli_unavailable")
    if not settings_ready:
        reasons.append("local_settings_missing")
    if not complete:
        reasons.append("remote_configuration_incomplete")
    return {
        "mode": mode,
        "independent_of_mcp": bool(independent),
        "official_cli_present": bool(cli_ready),
        "own_database_present": bool(db.is_dir()),
        "own_settings_present": bool(settings_ready),
        "remote_configuration_complete": complete,
        "eligible_for_isolated_sync_test": not reasons,
        "sync_active": False,
        "remote_writes_enabled": False,
        "blocking_reasons": reasons,
    }


def write_safety_status(config):
    """Describe the write gate without enabling any transport or remote writes.

    CI validates disposable encrypted round trips, not authorization to write
    to the user's CouchDB. This deliberately reports the pending production
    compatibility and recovery requirements, independent of configuration.
    """
    return {
        "independent_of_mcp": config.get("editor_storage_mode", "private") in ("private", "local"),
        "production_remote_writes_enabled": False,
        "manual_bidirectional_sync_enabled": False,
        "automatic_sync_enabled": False,
        "supported_operations": ["remote_read", "private_import", "private_edit",
                                 "compare", "diff", "baseline_acknowledge"],
        "write_gate": "closed",
        "isolated_tests": "run_in_github_actions",
        "isolated_commit_recovery": "manual_inspection_required_on_ambiguous_results",
        "multichunk_readonly_audit": "isolated_tests_only",
        "isolated_multichunk_cas": "leaf_readback_before_parent_cas_test_only",
        "orphan_cleanup_enabled": False,
        "production_blockers": [
            "live_wire_format_variants_not_exhaustively_validated",
            "multi_chunk_transaction_and_orphan_recovery",
            "remote_revision_race_and_conflict_resolution",
            "remote_write_backup_and_restore_protocol",
            "orphan_leaf_inspection_and_safe_cleanup",
            "end_to_end_roundtrip_across_supported_clients",
        ],
    }
