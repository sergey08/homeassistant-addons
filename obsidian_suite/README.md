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

- **Home Assistant with Supervisor and access to add-on installation** on AMD64 (`amd64`) or ARM64 (`aarch64`).
- **A Markdown vault accessible to the add-on**: an existing provisioned vault at `/app_configs/obsidian_bridge/vault` for LiveSync, **or** an existing directory below `/share` for Local mode.
- **Only for LiveSync mode:** a working CouchDB / Self-hosted LiveSync server (for example an independently installed Obsidian Sync Server add-on) and a valid LiveSync CLI settings file. Installing this add-on does **not** install CouchDB, the Obsidian client app, or the sync server.
- **An authorized OpenAI tunnel ID, tunnel-client binary and runtime key**, if the tunnel is enabled.
- **A compatible ChatGPT workspace** with permission to use the tunnel.

The current release supports existing, provisioned installations. **A fresh LiveSync installation requires manually provisioning the vault and LiveSync settings; Local mode supports both existing and new Markdown folders. Tunnel credentials must be provisioned separately if the ChatGPT tunnel is enabled.** Do not start two LiveSync writers against the same vault or two clients sharing the same tunnel identity.

See [complete Documentation](DOCS.md), the [Changelog](CHANGELOG.md), and the [OpenAI Secure MCP Tunnel guide](https://developers.openai.com/api/docs/guides/secure-mcp-tunnels).


## Choose your storage mode

In **Home Assistant → Settings → Apps → Obsidian MCP for Home Assistant → Configuration**, choose where the MCP tools work.

| Storage mode | Folder | Configuration |
|---|---|---|
| `livesync` | Existing LiveSync vault | Enable LiveSync to synchronize with CouchDB |
| **Local - Personal folder path** | Existing personal Markdown folder under `/share` | Enter its full path in `vault_path` |
| `Local - default` | `/config/local-vault`, included in backups that contain this app | Select the mode and start or restart the app |

Both local modes work without CouchDB and ignore the LiveSync switch. The ChatGPT tunnel is optional in all modes.

### Option 1 — LiveSync (your existing Obsidian vault)

This is the best option when you already use **Obsidian + Self-hosted LiveSync + CouchDB** and want ChatGPT to work with the *same* notes as your desktop or mobile Obsidian.

1. Select **Storage mode → livesync**.
2. **Leave Local Markdown folder (`vault_path`) empty.** It is not a path to your CouchDB server and you do not need to enter the existing LiveSync vault path.
3. Enable **LiveSync** and retain your existing LiveSync configuration and CouchDB credentials.
4. Enable the **ChatGPT tunnel** if you want to access your notes from ChatGPT.
5. Save and restart the add-on if you changed these settings.

The add-on uses its previously provisioned vault under `/app_configs/obsidian_bridge/vault`. LiveSync mirrors changes between that vault and CouchDB. **Changing to Local mode does not migrate or synchronize files between the two modes.**

### Option 2 — Personal local folder

Select **Storage mode → Local - Personal folder path**, enter the existing directory in **Local - Personal folder path**, then save and start or restart the app. Use a real subdirectory of `/share`. Home Assistant handles the shared folder separately from app backups.

### Option 3 — Default local folder

Select **Storage mode → Local - default**, then save and start or restart the app. It creates `/config/local-vault` with a bilingual `Bienvenida.md` on the first start. Future starts reuse your notes. Over Samba, open the `app_configs` share, then the folder ending in `_obsidian_suite` and its `local-vault` subfolder. Home Assistant includes this folder when the backup includes the app.

If you had selected `local` before upgrading, select **Local - Personal folder path** and save. Keep your existing path.

### Switching modes safely

- **LiveSync → Local:** back up your notes, select **Local - Personal folder path** and specify your existing folder, or select `Local - default`, then save and restart. This does **not** move the LiveSync vault.
- **Local → LiveSync:** select `livesync`, clear `vault_path`, enable LiveSync and restart. The original synchronized vault and CouchDB settings are reused.
- **Never run two add-ons using the same OpenAI tunnel ID simultaneously, nor two LiveSync writers on the same vault.** Stop the experimental instance before starting the production tunnel.
- The add-on's **Configuration** tab is the source of truth for these settings; the Ingress page provides diagnostics, not another configuration form.

For setup details and backups, see [the full documentation](DOCS.md). The storage-mode option requires **version 0.2.3 or later**.


## Shared Markdown vault with Obsidian Client (experimental; opt-in only)

The existing MCP LiveSync installation continues to use its legacy vault by default.
For a future deployment with the independent Obsidian Client, both add-ons can
mount the same dedicated directory under `/share`. The **MCP is the only
LiveSync process**. The Client must **not** run its own synchronization.

The experimental MCP configuration key `livesync_shared_vault_path` remains
empty by default. To opt in, an operator must first back up the existing MCP
vault, stop any processes writing to it, copy/migrate its Markdown files to
`/share/obsidian-shared-vault`, verify contents and permissions, then point
the MCP to that path with `storage_mode=livesync` and `enable_livesync=true`.
A missing or empty shared directory is intentionally rejected. Never enable
the Client's `mcp_shared` mode until the MCP has been restarted and its
LiveSync synchronization with CouchDB has been verified using a disposable
test note. There is **no automatic migration or production activation** in
this change. Switching the MCP back to its previous vault does not copy notes
back; preserve backups and coordinate writes across both add-ons.


### Read-only migration verification (no production changes)

Before enabling the shared vault, **make an external backup** and stop both add-ons
and any other local writers. Identify the actual original vault and its
settings from the running MCP; do not assume every installation uses the
legacy path. Copy the entire directory to the proposed shared location
using a separately reviewed backup/copy procedure. Include hidden files.

The included verifier reads only the two paths and compares each file's
relative name, size and SHA-256 digest, including hidden files:

```sh
python3 shared_vault_preflight.py /absolute/path/to/original/vault /share/obsidian-shared-vault
```

Exit 0 means identical snapshots and at least one Markdown file;
exit 1 means missing, extra, modified or no Markdown files; exit 2
means invalid input or an unsafe filesystem entry. It refuses symbolic
links, including broken links. **It never migrates files, starts LiveSync,
writes settings, or connects to CouchDB.**

Once the snapshots match, an operator must verify the MCP's effective
selected vault and the LiveSync CLI settings, then activate the new
path with a coordinated restart. Test one disposable Markdown note
round-trip via CouchDB and Obsidian, and test stale-write conflict
handling. Only then enable `editor_storage_mode=mcp_shared` for the
independent Obsidian Client. Preserve the original backup for rollback.
A file snapshot is not proof of a successful LiveSync replication.


### Safe offline copy tool (dry-run by default)

The `prepare_shared_vault.py` utility prepares *two separate new copies*
of an existing Markdown vault: a backup and a shared working copy.
**Neither the source nor any existing destination is overwritten.**
It is not a live migration: stop the MCP add-on, its LiveSync CLI process
and any other local writers before `--execute`. Preserve your separate
CouchDB backups. Run from a machine with access to the effective source
path and destination mounts:

```sh
python3 prepare_shared_vault.py \
  /app_configs/obsidian_bridge/vault \
  /share/obsidian-migration-backup-YYYYMMDD \
  /share/obsidian-shared-vault

# Only after reviewing dry-run output, stopping writers and confirming
# that neither destination exists:
python3 prepare_shared_vault.py \
  /app_configs/obsidian_bridge/vault \
  /share/obsidian-migration-backup-YYYYMMDD \
  /share/obsidian-shared-vault --execute
```

The backup and shared copies include hidden files and are compared against
the original by relative filename, byte count and SHA-256. If the source
changes while copying, the tool fails, leaves existing copied files alone
for inspection, and does **not** change HA options or start the MCP.
This does not eliminate LiveSync-specific conflicts: verify a disposable
round-trip with CouchDB and PC/Android before enabling the Client writer.
