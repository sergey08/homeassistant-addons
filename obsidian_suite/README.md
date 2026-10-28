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


## Local Markdown folder (0.2.3 development)

Select `storage_mode: local` and set `vault_path` to an **existing** directory under `/share`, e.g. `/share/my-markdown-vault`. The application does not start LiveSync in local mode, even if an old `enable_livesync` option was previously enabled. MCP reads and writes Markdown files directly. No CouchDB or LiveSync is required for this local-only workflow.

- Leave `storage_mode: livesync` (default) to preserve the existing production vault and LiveSync behavior. `vault_path` is ignored in this mode.
- Use only a directory you own and intentionally grant the agent read/write access to. The agent can modify Markdown notes there.
- `vault_path` cannot point outside `/share`, to `/share` itself, or to a symlink.
- Back up your Markdown folder before enabling writes.
- This setting is not available in the stable 0.2.2 build.

### Language-natural ChatGPT usage and migration checklist

The same MCP tools work in both modes. In Home Assistant **Configuration**, select `storage_mode=local`, set `vault_path` to an existing subfolder of `/share`, leave `enable_livesync=false`, and enable the tunnel only after stopping the other app using the same tunnel ID. Save and restart the app. Never run two tunnel clients with one ID.

Before replacing a working 0.2.2 install: back up the vault and add-on configuration, verify the current tunnel credentials remain provisioned, then test `list_notes`, `read_note`, `write_note`, and `search_notes` against disposable local notes. To return to LiveSync, set `storage_mode=livesync`, keep the existing persistent LiveSync vault and settings, and enable `enable_livesync` as appropriate. Avoid running two LiveSync writers at once. The Ingress page is for diagnostics, not an alternative configuration form.

On the experimental local development add-on, tunnel credential files are read from an existing provisioned app's read-only mounted configuration; no keys are copied into the Markdown vault. Do not delete the provisioned stable app during testing.

CI validation: the regression workflow is registered on the repository default branch so pull requests can be checked before merging.
