# Changelog — Obsidian MCP for Home Assistant (Beta)

## 0.2.7-beta.1 (optional beta add-on)

**This is a separate optional beta add-on** (`slug: obsidian_suite_beta`).

- Appears in Home Assistant next to the stable **Obsidian MCP for Home Assistant** (0.2.6).
- Does **not** replace or auto-update the stable install.
- Adds optional remote MCP authentication for Grok and other remote MCP clients.
- New options (default off): `enable_remote_mcp`, `remote_mcp_api_key`.
- Local connections remain unauthenticated so the OpenAI ChatGPT tunnel still works.
- Uses its own persistent path: `/app_configs/obsidian_bridge_beta` (does not share vault/tunnel files with the stable add-on by default).

### Important

- Do **not** enable the same OpenAI tunnel ID on stable and beta at the same time.
- Do **not** run two LiveSync writers against the same CouchDB vault.
- Install this beta only if you want to test Grok / remote MCP access.

## Based on stable 0.2.6

See the stable add-on changelog for prior history.
