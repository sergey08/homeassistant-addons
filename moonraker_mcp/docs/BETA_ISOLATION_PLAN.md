# Safe-print beta — isolation plan (not deployed)

The stable Home Assistant add-on remains `moonraker_mcp` version `0.1.4`.
Do not change its `slug`, `version`, `/data`, existing settings or exposed port.

## Proposed isolated add-on
- New add-on directory and **different slug**, e.g. `moonraker_mcp_safeprint_beta`, with its own `config.yaml`, `Dockerfile`, `run.sh`, Python modules and build context.
- Version must be an explicit prerelease identifier, distinct from stable `0.1.4`.
- Do not expose or map the same host port as the stable add-on. Default `ports: {8765/tcp: null}` and `enable_tunnel: false`; inspect container and host port mapping before activation.
- Supervisor must allocate an independent `/data` for the new slug. Do not mount `/addon_configs/moonraker_mcp`, stable backups, tokens or staging into beta.
- Default `enable_write_actions: false`, `allow_gcode_upload: false`, `allow_print_start: false`; no print-start tests.
- Do not copy existing API keys, MCP bearer tokens or tunnel credentials. Generate dedicated test credentials if an isolated test later requires them.
- Confirm a separate Docker image/build context includes the new housekeeping module, pinned dependencies and notices.
- Run both CI suites and an isolated image build before proposing installation.
- Initial tests must be offline and use synthetic G-code. Any live printer upload requires a separate user approval.

## Release gate
This document **does not** create an installable beta. Do not publish a prerelease or add a second add-on until isolation and build context have been reviewed and accepted. Keep the draft PR open.
