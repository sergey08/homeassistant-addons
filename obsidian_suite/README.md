# Obsidian MCP for Home Assistant

**One Home Assistant add-on for private ChatGPT access to Obsidian notes and optional LiveSync replication.**

## Features

The add-on combines three supervised processes:

1. **Markdown MCP Server**: list, search, read, create, append, rename and recoverably delete Markdown files in a local Obsidian vault.
2. **OpenAI Secure MCP Tunnel**: connect an authorized ChatGPT workspace to the local MCP endpoint without public port forwarding.
3. **Self-hosted LiveSync CLI**: synchronize that vault with an existing CouchDB-backed Obsidian LiveSync setup.

It reuses files in Home Assistant's persistent `/app_configs/obsidian_bridge` directory. The MCP server starts before the tunnel client.

## Recommended companion add-on

If you need a local CouchDB backend in Home Assistant, we recommend **[Obsidian Sync Server SSL by alexbelgium](https://github.com/alexbelgium/hassio-addons/tree/master/obsidian_syncserver_ssl)**. Install it separately from [alexbelgium's add-on repository](https://github.com/alexbelgium/hassio-addons), configure CouchDB credentials and trusted HTTPS certificates, then connect the Self-hosted LiveSync plugin in Obsidian. This does not automatically prepare the local MCP vault or the OpenAI tunnel. See the [full requirements and setup guide](DOCS.md#recommended-home-assistant-obsidian-server).

## Requirements

- **Home Assistant OS or Supervised (amd64)** with access to add-on installation.
- **An existing Markdown Obsidian vault stored on Home Assistant**, at `/app_configs/obsidian_bridge/vault`.
- **A working CouchDB / Self-hosted LiveSync server** (for example an independently installed Obsidian Sync Server add-on) and a valid LiveSync CLI settings file, if LiveSync is enabled. Installing this add-on does **not** install CouchDB, the Obsidian client app, or the sync server.
- **An authorized OpenAI tunnel ID, tunnel-client binary and runtime key**, if the tunnel is enabled.
- **A compatible ChatGPT workspace** with permission to use the tunnel.

The current release supports existing, provisioned installations. **A fresh installation requires manually placing the vault, LiveSync settings and tunnel credentials in their documented private locations.** Do not start two LiveSync writers against the same vault or two clients sharing the same tunnel identity.

See [complete Documentation](DOCS.md), the [Changelog](CHANGELOG.md), and the [OpenAI Secure MCP Tunnel guide](https://developers.openai.com/api/docs/guides/secure-mcp-tunnels).


## Local Markdown folder (experimental 0.2.3-dev1)

Select `storage_mode: local` and set `vault_path` to an **existing** directory under `/share`, e.g. `/share/my-markdown-vault`, The application does not start LiveSync in local mode, even if an old `enable_livesync` option was previously enabled. MCP reads and writes Markdown files directly. No CouchDB or LiveSync is required for this local-only workflow.

- Leave `storage_mode: livesync` (default) to preserve the existing production vault and LiveSync behavior. `vault_path` is ignored in this mode.
- Use only a directory you own and intentionally grant the agent read/write access to. The agent can modify Markdown notes there.
- `vault_path` cannot point outside `/share`, to `/share` itself, or to a symlink.
- Back up your Markdown folder before enabling writes.
- This setting is not available in the stable 0.2.2 build.
