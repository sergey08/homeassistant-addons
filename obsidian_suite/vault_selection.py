"""Select Markdown vaults and initialize the default local vault."""
from contextlib import suppress
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


def initialize_local_vault(vault: Path) -> None:
    try:
        vault.mkdir()
    except FileExistsError:
        if vault.is_symlink() or not vault.is_dir():
            raise ValueError(f"Default local vault must be a real directory: {vault}")
        return

    welcome = vault / "Bienvenida.md"
    try:
        with welcome.open("x", encoding="utf-8") as note:
            try:
                note.write(
                    "# Welcome / Bienvenida\n\n"
                    "Your local vault is ready. Create Markdown notes in this folder.\n\n"
                    "Tu bóveda local está lista. Crea tus notas Markdown en esta carpeta.\n"
                )
                note.flush()
            except OSError:
                with suppress(OSError):
                    welcome.unlink()
                raise
    except OSError:
        with suppress(OSError):
            vault.rmdir()
        raise


def select_storage(options: dict, default_vault: Path, shared_root: Path = Path("/share"),
                   *, app_config: Path = Path("/config"), initialize_local: bool = False) -> tuple[str, Path, bool]:
    """Resolve mode and folder; never start LiveSync while in local mode.

    Missing mode preserves 0.2.2 behavior. The original enable_livesync
    option remains authoritative for installations that already use it.
    """
    mode = str(options.get("storage_mode", "livesync")).strip()
    if mode == "Local - Personal folder path":
        mode = "local"
    if mode not in ("livesync", "local", "Local - default"):
        raise ValueError("Invalid storage_mode")
    if mode == "Local - default":
        vault = app_config / "local-vault"
        if initialize_local:
            initialize_local_vault(vault)
        return mode, vault, False
    if mode == "local":
        path = str(options.get("vault_path", "")).strip()
        if not path:
            raise ValueError("Local mode requires vault_path inside /share")
        return mode, select_vault(path, default_vault, shared_root), False
    shared = str(options.get("livesync_shared_vault_path", "")).strip()
    if shared:
        if not options.get("enable_livesync", False):
            raise ValueError("Shared LiveSync vault requires enable_livesync")
        selected = select_vault(shared, default_vault, shared_root)
        if not any(selected.rglob("*.md")):
            raise ValueError("Shared LiveSync vault has no Markdown files; migrate first")
        return mode, selected, True
    return mode, default_vault, bool(options.get("enable_livesync", False))
