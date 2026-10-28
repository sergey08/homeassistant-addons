"""Select only a preexisting Markdown vault in the mounted /share tree."""
from pathlib import Path


def select_vault(configured_vault: str, default_vault: Path, shared_root: Path = Path("/share")) -> Path:
    if not configured_vault or not configured_vault.strip():
        return default_vault
    root = shared_root.resolve(strict=True)
    vault = Path(configured_vault.strip())
    if ".." in vault.parts or "." in vault.parts:
        raise ValueError("Relative navigation segments are not allowed in vault_path")
    if not vault.is_absolute() or vault == shared_root or not vault.is_dir() or vault.is_symlink():
        raise ValueError("Vault must be an existing real subdirectory of /share")
    resolved = vault.resolve(strict=True)
    if resolved == root or not resolved.is_relative_to(root):
        raise ValueError("Vault path is outside /share")
    cursor = root
    for part in vault.relative_to(shared_root).parts:
        cursor = cursor / part
        if cursor.is_symlink():
            raise ValueError("Symlinked parent directories are not allowed")
    return resolved


def select_storage(options: dict, default_vault: Path, shared_root: Path = Path("/share")) -> tuple[str, Path, bool]:
    """Resolve mode and folder; never start LiveSync while in local mode.

    Missing mode preserves 0.2.2 behavior. The original enable_livesync
    option remains authoritative for installations that already use it.
    """
    mode = str(options.get("storage_mode", "livesync")).strip()
    if mode not in ("livesync", "local"):
        raise ValueError("Invalid storage_mode")
    if mode == "local":
        path = str(options.get("vault_path", "")).strip()
        if not path:
            raise ValueError("Local mode requires vault_path inside /share")
        return mode, select_vault(path, default_vault, shared_root), False
    return mode, default_vault, bool(options.get("enable_livesync", False))
