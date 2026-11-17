"""Create a separate, local beta build context; never modifies the stable add-on."""
from pathlib import Path
import argparse
import shutil
import stat

SOURCE = Path(__file__).resolve().parent
BETA_SLUG = "moonraker_mcp_safeprint_beta"
BETA_VERSION = "0.1.5-beta.1"

def prepare(destination):
    destination = Path(destination).resolve()
    if destination == SOURCE.resolve() or SOURCE.resolve() in destination.parents:
        raise ValueError("Beta destination must be outside stable source")
    if destination.exists():
        raise FileExistsError("Refusing to overwrite existing beta destination")
    if destination.name != BETA_SLUG:
        raise ValueError("Beta directory must match isolated slug")
    # Only tracked runtime/build assets are copied. Never copy secrets, data or
    # arbitrary files that happen to be present in a developer checkout.
    assets = [
        "config.yaml", "Dockerfile", "run.sh", "gateway.py", "tool_policy.py",
        "moonraker_files.py", "moonraker_staging.py", "moonraker_chunk_staging.py",
        "staging_housekeeper.py", "moonraker_upload.py", "moonraker_spoolman.py",
        "moonraker_snapshot.py", "moonraker_print_control.py", "moonraker_status.py",
        "read_only_allowlist.json", "tunnel_runtime.py", "tunnel_provision.py",
        "tunnel_autosetup.py", "THIRD_PARTY_NOTICES_EN_ES.md",
        "THIRD_PARTY_SOURCE_ACCESS_EN_ES.md",
    ]
    assets += [str(p.relative_to(SOURCE)) for p in (SOURCE / "licenses").rglob("*") if p.is_file()]
    for relative in assets:
        source = SOURCE / relative
        if source.is_symlink() or not source.is_file() or not stat.S_ISREG(source.stat().st_mode):
            raise ValueError("Unsafe or missing beta source asset: " + relative)
    destination.mkdir(parents=False)
    for relative in assets:
        target = destination / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(SOURCE / relative, target)
    config = destination / "config.yaml"
    value = config.read_text()
    for old, new in [
        ('name: "Moonraker MCP"', 'name: "Moonraker MCP Safe Print BETA"'),
        ('version: "0.1.4"', 'version: "' + BETA_VERSION + '"'),
        ('slug: "moonraker_mcp"', 'slug: "' + BETA_SLUG + '"'),
    ]:
        if value.count(old) != 1:
            raise ValueError("Unexpected source config; review beta manually")
        value = value.replace(old, new, 1)
    for flag in ("enable_write_actions", "allow_gcode_upload", "allow_print_start", "enable_tunnel"):
        if '  ' + flag + ': false' not in value:
            raise ValueError("Unsafe default for " + flag)
    config.write_text(value)
    return destination

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("destination", help="Nonexistent path ending in " + BETA_SLUG)
    args = parser.parse_args()
    print(prepare(args.destination))
