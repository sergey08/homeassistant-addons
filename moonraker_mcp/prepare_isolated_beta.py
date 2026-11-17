"""Create a separate, local beta build context; never modifies the stable add-on."""
from pathlib import Path
import argparse
import shutil

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
    shutil.copytree(SOURCE, destination, ignore=shutil.ignore_patterns(
        "__pycache__", "*.pyc", ".pytest_cache", ".DS_Store"))
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
