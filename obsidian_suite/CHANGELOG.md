# Changelog

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
