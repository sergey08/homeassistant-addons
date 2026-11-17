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
