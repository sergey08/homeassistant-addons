# Changelog

## 0.2.7

### English

| Storage mode | How to set it up | Where the notes are stored |
| --- | --- | --- |
| `livesync` | Enable **Enable LiveSync** and use your existing Self-hosted LiveSync settings and CouchDB server. Fill in **LiveSync shared vault path** only if you already use a shared vault under `/share`. | The existing LiveSync vault, synchronized with CouchDB. |
| **Local - default** | Leave both path fields empty. Save and restart. The app creates the vault with `Bienvenida.md` the first time. | `/config/local-vault` inside the app. It is included when Home Assistant backs up the app and is accessible through Samba at `app_configs/<app-id>/local-vault`. |
| **Local - Personal folder path** | Enter the full path of an existing folder under `/share` in **Local - Personal folder path**. Save and restart. | Your chosen Markdown folder. Include `share` in your Home Assistant backup to back up these notes. |

Both local modes work without CouchDB. Changing modes leaves notes in their original locations. If you previously saved `local`, select **Local - Personal folder path** when updating and keep the path you already use.

### Español

| Storage mode | Cómo se configura | Dónde quedan las notas |
| --- | --- | --- |
| `livesync` | Activa **Enable LiveSync** y utiliza tu configuración de Self-hosted LiveSync y tu servidor CouchDB. Rellena **LiveSync shared vault path** solo si ya usas una bóveda compartida bajo `/share`. | En la bóveda existente de LiveSync, sincronizada con CouchDB. |
| **Local - default** | Deja vacíos los dos campos de ruta. Guarda y reinicia. La aplicación crea la bóveda con `Bienvenida.md` la primera vez. | En `/config/local-vault` dentro de la aplicación. Se incluye al respaldar la aplicación en Home Assistant y está accesible por Samba en `app_configs/<id-de-la-app>/local-vault`. |
| **Local - Personal folder path** | Introduce en **Local - Personal folder path** la ruta completa a una carpeta existente bajo `/share`. Guarda y reinicia. | En la carpeta Markdown que elijas. Incluye `share` en la copia de Home Assistant para respaldar estas notas. |

Ambos modos locales funcionan sin CouchDB. Al cambiar de modo, las notas permanecen en su ubicación original. Si tenías guardado `local`, al actualizar selecciona **Local - Personal folder path** y conserva tu ruta actual.

## 0.2.6

- Supports Home Assistant on AMD64 and ARM64 using the same multi-platform LiveSync CLI image.
- Verifies Linux AMD64 and ARM64 OpenAI tunnel packages against their official SHA256 manifests and the running architecture.
- Tests both architectures with disposable vaults and an isolated CouchDB instance.
- Verified store installation and basic MCP startup on an AMD64 Lenovo and an ARM64 Raspberry Pi. The device checks ran with LiveSync and the tunnel disabled.

## 0.2.5 — 2026-11-05

- Adds opt-in LiveSync Markdown vault under `/share` for future shared use with Obsidian Client.
- Coordinates MCP note edits with the Client using a cooperative file lock, including revision guards.
- Adds read-only effective vault path diagnostics in Home Assistant Ingress.
- Includes dry-run-first backup and shared-vault verification utilities with SHA-256 comparison.
- **No automatic migration**: the original LiveSync vault, CouchDB settings and tunnel remain in use by default. Do not activate the shared mode until the existing vault is backed up and offline migration is verified.


## 0.2.3 — 2026-10-28

- Adds selectable LiveSync and local Markdown storage modes in Home Assistant's native Configuration tab.
- Keeps existing LiveSync vault and tunnel configuration compatible with the 0.2.2 installation.
- Adds validated local vault paths, atomic Markdown writes, guarded revisions and regression tests.
- Verified upgrade to the 0.2.3 release candidate with the user's CouchDB LiveSync, active tunnel and read access to 51 notes.
- Does not remove or migrate existing notes; the experimental add-on remains separate until explicitly retired.

## 0.2.2 — 2026-10-26

- Preserves the `obsidian_suite` add-on identity, existing Home Assistant options and persistent vault paths.
- Adds guided initial setup and read-only CouchDB diagnostics.
- Adds isolated MCP Markdown CRUD and recoverable deletion regression tests.
- Uses exclusive temporary files for atomic note replacement.
- Adds CI checks for two-client encrypted LiveSync replication and compatibility with the 0.2.1 installation.
- Verified in-place upgrade from 0.2.1 to 0.2.2 on Home Assistant with unchanged tunnel and LiveSync options; tested MCP read/write and bidirectional replication with Obsidian desktop.
- Excludes the experimental `obsidian_preview` package from the stable repository.

## 0.2.0 — 2026-10-25

- Replaced Preview name with Obsidian MCP Suite.
- Added English and Spanish configuration field labels and help descriptions.
- Reworked Home Assistant Documentation with a complete Secure MCP Tunnel setup guide.
- Documented runtime API key and binary provisioning, persistent vault paths, migration and rollback.
- Added per-app README and improved the repository overview.
- Service runtime unchanged from 0.1.1.

## 0.1.1 — 2026-10-25

- Wait for the MCP TCP endpoint before starting the tunnel.
- Verified MCP tool access and LiveSync synchronization after migration.

## 0.1.0 — 2026-10-25

- Initial unified suite for MCP, tunnel and LiveSync.
