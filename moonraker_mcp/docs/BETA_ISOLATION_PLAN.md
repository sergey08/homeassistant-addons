# Safe-print beta — isolation plan (not deployed)

The stable Home Assistant add-on remains `moonraker_mcp` version `0.1.4`.
Do not change its `slug`, `version`, `/data`, existing settings or exposed port.

## Generated isolated add-on (build context only)
- `prepare_isolated_beta.py` generates a separate temporary build context with slug `moonraker_mcp_safeprint_beta` and version `0.1.5-beta.1`. It copies only allowlisted runtime assets; no existing data or credentials are copied.
- Version must be an explicit prerelease identifier, distinct from stable `0.1.4`.
- Do not expose or map the same host port as the stable add-on. Default `ports: {8765/tcp: null}` and `enable_tunnel: false`; inspect container and host port mapping before activation.
- Supervisor must allocate an independent `/data` for the new slug. Do not mount `/addon_configs/moonraker_mcp`, stable backups, tokens or staging into beta.
- Default `enable_write_actions: false`, `allow_gcode_upload: false`, `allow_print_start: false`; no print-start tests.
- Do not copy existing API keys, MCP bearer tokens or tunnel credentials. Generate dedicated test credentials if an isolated test later requires them.
- Confirm a separate Docker image/build context includes the new housekeeping module, pinned dependencies and notices.
- CI on commit `eecda22` passed both workflow suites, including isolated Docker builds for AMD64 and ARM64, fail-closed startup checks, and offline policy/staging tests. Repeat CI on the final branch HEAD before installation.
- Initial tests must be offline and use synthetic G-code. Any live printer upload requires a separate user approval.

## Release gate
The build context and Docker images have been validated in CI, but **no beta has been published or installed**. Do not publish a prerelease or add a second add-on until isolation and build context have been reviewed and accepted. Keep the draft PR open.

## CI artifact verified (17 November 2026)
- Both workflows succeeded for commit `bc3331e86833713a17f47864fafc03c0caf4206d`.
- GitHub Actions run [44171847262](https://github.com/sergey08/homeassistant-addons/actions/runs/44171847262) produced artifact `moonraker-safeprint-beta-context` (artifact ID `14368047475`, SHA-256 digest `f2b6e610b504d4c6f215d62c037b5f61e3454f2f5c3860b246f9a2e4af0f6d5e`), expiring 24 November 2026.
- This is a **build-context archive**, not an installed Supervisor app, container registry image or GitHub release. It must not be presented as a deployable release.

## Catalog deployment gate
- Home Assistant Supervisor discovers add-on directories from a repository's configured branch. A generated archive in CI does **not** automatically appear in the catalog.
- **Never install the current development branch as a replacement source for the existing stable add-on**: it also contains the stable `moonraker_mcp` directory. Avoid accidental update/replacement of v0.1.4.
- For a safe catalog entry, review a change that adds **only** the new top-level `moonraker_mcp_safeprint_beta/` directory to the existing repository's catalog branch, preserving `moonraker_mcp/` byte-for-byte. Keep its own slug, isolated Supervisor `/data`, `boot: manual`, `8765/tcp: null`, and all write/tunnel flags false.
- Require a reviewed diff and successful CI before merging that catalog-only addition. The PR #136 itself remains draft and must not be merged wholesale to distribute the beta.
- Once the independent entry is visible, inspect its slug, version, default options and port mappings **before** installing or starting it. Stop/remove only the beta for rollback.
