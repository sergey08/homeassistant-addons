"""Obsidian Client storage selection, independent of the Obsidian MCP add-on.

LiveSync mode reserves an independent Markdown vault, local database and
settings directory. It does not launch synchronization; remote sync must be
implemented and verified separately before it can be advertised as ready.
"""
from pathlib import Path

PRIVATE_VAULT = Path("/data/obsidian-client-markdown")
LOCAL_VAULT = PRIVATE_VAULT  # retain existing notes when upgrading from 'private'
LIVESYNC_VAULT = Path("/data/obsidian-client-livesync-vault")
LIVESYNC_DATABASE = Path("/data/livesync-client")
LIVESYNC_SETTINGS = LIVESYNC_DATABASE / ".livesync"
MCP_SHARED_VAULT = Path("/share/obsidian-shared-vault")

class StorageSelectionError(ValueError):
    pass


def select_storage(config, *, private_vault=LOCAL_VAULT,
                   livesync_vault=LIVESYNC_VAULT,
                   livesync_database=LIVESYNC_DATABASE,
                   shared_vault=MCP_SHARED_VAULT):
    mode = str(config.get("editor_storage_mode", "private")).strip()
    if mode in ("private", "local"):
        return {"mode": "local", "vault": str(private_vault),
                "sync_engine": "disabled", "remote_synced": False,
                "independent_of_mcp": True}
    if mode == "livesync":
        if (Path(livesync_vault).resolve(strict=False)
                == Path(livesync_database).resolve(strict=False)):
            raise StorageSelectionError("livesync_vault_database_overlap")
        return {"mode": "livesync", "vault": str(livesync_vault),
                "database": str(livesync_database),
                "sync_engine": "not_implemented", "remote_synced": False,
                "independent_of_mcp": True}
    if mode == "mcp_shared":
        root = Path(shared_vault)
        if not root.is_dir() or root.is_symlink() or root.resolve(strict=True) != root:
            raise StorageSelectionError("mcp_shared_vault_unavailable")
        return {"mode": "mcp_shared", "vault": str(root),
                "sync_engine": "external_mcp", "remote_synced": False,
                "independent_of_mcp": False}
    raise StorageSelectionError("unsupported_editor_storage_mode")
