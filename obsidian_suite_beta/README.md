# Obsidian MCP for Home Assistant (Beta)

**Optional beta add-on** — appears alongside the stable *Obsidian MCP for Home Assistant*.

| | Stable | This beta |
|---|---|---|
| Name | Obsidian MCP for Home Assistant | Obsidian MCP for Home Assistant (Beta) |
| Slug | `obsidian_suite` | `obsidian_suite_beta` |
| Version | 0.2.6 | 0.2.7-beta.1 |
| Remote MCP (Grok) | No | Yes (optional, with API key) |
| Persistent data | `/app_configs/obsidian_bridge` | `/app_configs/obsidian_bridge_beta` |

## What is new

- Optional authenticated remote MCP endpoint for **Grok** (and other MCP clients).
- Bearer token auth for non-local requests; local OpenAI tunnel remains unaffected.
- All existing tools, LiveSync and ChatGPT tunnel features from 0.2.6.

## Install

1. Ensure the repository is added in Home Assistant.
2. In the App Store you should see **two** entries; install **Obsidian MCP for Home Assistant (Beta)** when you want to test.
3. Configure vault / LiveSync / tunnel as needed (this beta uses a separate data folder by default).
4. To use Grok: enable `enable_remote_mcp`, set `remote_mcp_api_key`, expose the endpoint with HTTPS, then add a Custom connector on grok.com.

Full documentation: [DOCS.md](DOCS.md)

**Do not run stable and beta with the same tunnel ID or the same LiveSync vault writer at the same time.**
