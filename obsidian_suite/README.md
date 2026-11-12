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

| Storage mode | How to set it up | Where the notes are stored |
| --- | --- | --- |
| `livesync` | Enable **Enable LiveSync** and use your existing Self-hosted LiveSync settings and CouchDB server. Fill in **LiveSync shared vault path** only if you already use a shared vault under `/share`. | The existing LiveSync vault, synchronized with CouchDB. |
| **Local - default** | Leave both path fields empty. Save and restart. The app creates the vault with `Bienvenida.md` the first time. | `/config/local-vault` inside the app. It is included when Home Assistant backs up the app and is accessible through Samba at `app_configs/<app-id>/local-vault`. |
| **Local - Personal folder path** | Enter the full path of an existing folder under `/share` in **Local - Personal folder path**. Save and restart. | Your chosen Markdown folder. Include `share` in your Home Assistant backup to back up these notes. |

Both local modes work without CouchDB. Changing modes leaves notes in their original locations. If you previously saved `local`, select **Local - Personal folder path** when updating and keep the path you already use.

### Switching modes safely

- **LiveSync → Local:** back up your notes, select **Local - Personal folder path** and specify your existing folder, or select `Local - default`, then save and restart. This does **not** move the LiveSync vault.
- **Local → LiveSync:** select `livesync`, clear `vault_path`, enable LiveSync and restart. The original synchronized vault and CouchDB settings are reused.
- **Never run two add-ons using the same OpenAI tunnel ID simultaneously, nor two LiveSync writers on the same vault.** Stop the experimental instance before starting the production tunnel.
- The add-on's **Configuration** tab is the source of truth for these settings; the Ingress page provides diagnostics, not another configuration form.

For setup details and backups, see [the full documentation](DOCS.md). The storage-mode option requires **version 0.2.3 or later**.


## Modos de almacenamiento

En **Ajustes → Aplicaciones → Obsidian MCP for Home Assistant → Configuración**, elige un modo en **Storage mode**.

| Storage mode | Cómo se configura | Dónde quedan las notas |
| --- | --- | --- |
| `livesync` | Activa **Enable LiveSync** y utiliza tu configuración de Self-hosted LiveSync y tu servidor CouchDB. Rellena **LiveSync shared vault path** solo si ya usas una bóveda compartida bajo `/share`. | En la bóveda existente de LiveSync, sincronizada con CouchDB. |
| **Local - default** | Deja vacíos los dos campos de ruta. Guarda y reinicia. La aplicación crea la bóveda con `Bienvenida.md` la primera vez. | En `/config/local-vault` dentro de la aplicación. Se incluye al respaldar la aplicación en Home Assistant y está accesible por Samba en `app_configs/<id-de-la-app>/local-vault`. |
| **Local - Personal folder path** | Introduce en **Local - Personal folder path** la ruta completa a una carpeta existente bajo `/share`. Guarda y reinicia. | En la carpeta Markdown que elijas. Incluye `share` en la copia de Home Assistant para respaldar estas notas. |

Ambos modos locales funcionan sin CouchDB. Al cambiar de modo, las notas permanecen en su ubicación original. Si tenías guardado `local`, al actualizar selecciona **Local - Personal folder path** y conserva tu ruta actual.

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
