"""Select only a preexisting Markdown vault in the mounted /share tree."""
from pathlib import Path


def select_vault(configured_vault: str, default_vault: Path, shared_root: Path = Path("/share")) -> Path:
    if not configured_vault or not configured_vault.strip():
        return default_vault
    root = shared_root.resolve(strict=True)
    vault = Path(configured_vault.strip())
    if not vault.is_absolute() or vault == shared_root or not vault.is_dir() or vault.is_symlink():
        raise ValueError("Vault must be an existing real subdirectory of /share")
    resolved = vault.resolve(strict=True)
    if resolved == root or not resolved.is_relative_to(root):
        raise ValueError("Vault path is outside /share")
    return resolved
