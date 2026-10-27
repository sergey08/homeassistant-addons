# Fresh installation (experimental development branch)

This branch is **not a release**. Do not install it on an active vault without backups and a rollback plan.

## For users of alexbelgium Obsidian Sync Server SSL

1. Install and configure the separate [Obsidian Sync Server SSL](https://github.com/alexbelgium/hassio-addons/tree/master/obsidian_syncserver_ssl) add-on and verify syncing from two Obsidian clients using the Self-hosted LiveSync plugin. Other compatible CouchDB setups can also work.
2. Install this MCP add-on **with tunnel and LiveSync disabled**. It creates its owned `/data/vault` and `/data/mcp-trash` folders on first start, while older installations with the existing `obsidian_bridge/vault` continue using the legacy location.
3. Import a Self-hosted LiveSync setup URI from a trusted Obsidian client using the **upstream CLI setup command** (no synchronization performed by `setup`):
   `livesync-cli /data --settings /data/settings/livesync-operativo.json setup "obsidian://setuplivesync?settings=..."`
   This is a **reference command, not an automated wizard**. Handle the setup URI like a password: it can contain private synchronization details. It can be exposed in shell history or process lists; do not paste it into public Issues, screenshots or chat logs. Confirm compatibility with the installed CLI version before using it.
4. Validate HTTPS certificate trust and configuration; then enable LiveSync. Keep any other LiveSync CLI writer stopped.
5. Configure the OpenAI Secure MCP Tunnel separately (official executable + private runtime key + tunnel ID), then enable the tunnel and test a read-only MCP call.

## Current limitations

- The CLI setup URI import, credentials storage, and validation are **not yet integrated into the Home Assistant Configuration UI**.
- The add-on cannot safely infer an encrypted LiveSync setup from CouchDB URL/password alone; use a setup URI exported by a configured Obsidian client.
- There is currently no remote connectivity or encrypted-data compatibility test in the UI.
- The tunnel client binary is still private, manually provisioned, and not bundled.
- Existing working installations are not changed by commits in this feature branch.
- Do not use destructive CLI commands such as `fetch --force` or `rebuild --force` as part of onboarding.

## Diagnostics

The experimental helper `preflight.py` reports which expected files exist without printing secrets or modifying notes. A successful preflight is **not** evidence that replication works: test against a disposable vault first.

### Next engineering work

A secure first-run wizard must allow setup URI import without leaking secrets via URL parameters, command arguments, logs, or shell history; confirm target database and TLS trust; validate before enabling sync; and preserve existing installation rollback.

## Read-only Home Assistant onboarding page (experimental)

This development branch includes a **Home Assistant Ingress** status page. Open the add-on's **Open Web UI** action to see whether the local vault, trash, LiveSync settings, tunnel executable, key file and tunnel ID are present. Missing prerequisites appear as `Not configured`.

- The page deliberately **does not accept setup URIs, passwords or API keys**.
- It never displays private credentials, tunnel IDs, vault note contents or configuration values.
- It is not a CouchDB connectivity test: `Ready` only means the required files/options are present.
- Do not expose its port independently; access is intended only through Home Assistant's authenticated Ingress proxy.
- The page remains in the feature branch until its Ingress behavior and security are tested on a clean HA OS instance.

## Experimental Ingress JSON import form

The **Open Web UI** page now has a one-time form for users who already possess a trusted **LiveSync CLI settings JSON file**. Paste its exact JSON contents into the form; the private data is stored at `/data/settings/livesync-operativo.json` on clean installs (or the legacy location on migrated installs) with restrictive permissions. An existing settings file cannot be overwritten.

**Important:** This is *not* an importer for the `obsidian://setuplivesync?settings=...` URI, nor does it construct valid encrypted settings from a CouchDB URL/password. The CLI URI importer remains **unwired** because it could leak the secret URI through the process command line. Never paste a setup URI into the JSON form.

The JSON form checks structural validity only. It does **not** verify compatibility of fields, encryption, CouchDB permissions, TLS or safe synchronization. Do not enable LiveSync until a clean test setup has been verified. Treat settings JSON as a secret and keep backups; it is never echoed by the UI or written to logs intentionally.

The form is protected by a session-lifetime anti-CSRF token and meant to be accessed exclusively via authenticated Home Assistant Ingress. Do not forward port 8099.

## OpenAI Secure MCP Tunnel: new users

The runtime tunnel API key can now be stored in the add-on's authenticated **Open Web UI** using a one-time form; the key is not echoed or overwritten. It is stored as a private file, separate from your Markdown vault.

To complete setup:

1. In your **own** OpenAI Platform organization, open [Tunnel settings](https://platform.openai.com/settings/organization/tunnels) and create/obtain a tunnel ID and restricted runtime API key. Tunnel permissions and ChatGPT workspace associations must allow that tunnel. Keep the key private.
2. Obtain the current official `tunnel-client` binary from [openai/tunnel-client releases](https://github.com/openai/tunnel-client/releases/latest). Verify its publisher, target Linux/amd64 architecture, version and checksums/signatures against the upstream release instructions **before** provisioning. Do not copy binaries from another user's add-on or download unaudited executable assets.
3. The add-on currently expects the executable at its own persistent `tunnel/bin/tunnel-client` location (or legacy add-on config for existing installs); automatic download and verification are **not implemented**. Do not enable the tunnel until the verified executable is installed.
4. Open the experimental add-on's Web UI and enter your runtime key; set your tunnel ID under Home Assistant add-on Configuration.
5. Only after all checks pass, enable the tunnel and restart the add-on. Check readiness and tool discovery from ChatGPT using an appropriate private custom MCP app.

This feature is still experimental, and an API key by itself is **not** sufficient for automatic tunnel access. Inbound port forwarding is unnecessary for Secure MCP Tunnel; outbound HTTPS to the OpenAI control plane is required.

**Official documentation:** https://developers.openai.com/api/docs/guides/secure-mcp-tunnels

## Offline tunnel binary import (experimental)

The add-on image now contains `/opt/obsidian/tunnel_installer.py`, a **local-only helper** for a ZIP archive and matching SHA256SUMS.txt. It does not fetch software from arbitrary URLs and is deliberately not available as an unaudited web upload.

**Security boundary:** a matching checksum proves only that the archive matches the supplied manifest. Users must independently verify that both came from the authentic OpenAI release and check available signed provenance. A user-supplied ZIP and user-supplied checksum file are not sufficient to establish trusted origin.

This helper is presently library code, not a Home Assistant configuration UI action. Installation from a fresh Home Assistant Supervisor session and verification of the official release artifact format remain to be tested. Never enable the tunnel solely because the binary appears in the first-run checklist.
