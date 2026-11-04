# Moonraker MCP — read-only tool audit (DEV)

Audit date: 2026-11-03. Source inspected: `lexfrei/mcp-raker` Go handlers under `internal/tools/`, including the **exact OCI-labelled source revision** `0caea7c31a0780462331e9031e3bf0f435d190ed` (upstream version `0.2.0`). The pinned image digest `sha256:cdfbb9b4ead2b3f8a253eb55c1996a69cfdbc17088cc111b7d265d8b71f7090e` was pulled in GitHub Actions run 144; its OCI source, revision and version labels match this reference. **OCI labels alone are not cryptographic build provenance or a reproducible-build proof.**

The HTTP gateway enforces an explicit allowlist of **5 default upstream names plus 11 explicitly opt-in upstream names**, and **3 additional local file tools** behind `enable_files` (19 maximum), and rejects calls to other names before forwarding to the loopback-only upstream. This review describes the handler behavior seen in source; it is **not a security certification**.

| Allowed MCP tool | Observed upstream action |
| --- | --- |
| moonraker_mcp_version | Returns local version information; no Moonraker HTTP request |
| moonraker_server_info | GET /server/info |
| moonraker_printer_info | GET /printer/info |
| moonraker_objects_list | GET /printer/objects/list |
| moonraker_objects_query | GET /printer/objects/query, constructed from requested object names and fields |
| moonraker_temperature_store | GET /server/temperature_store |
| moonraker_history_list | GET /server/history/list |
| moonraker_history_job | GET /server/history/job |
| moonraker_history_totals | GET /server/history/totals |
| moonraker_jobqueue_status | GET /server/job_queue/status |
| moonraker_power_status | GET /machine/device_power/device |
| moonraker_sensors_info | GET /machine/sensors/info |
| moonraker_sensors_list | GET /machine/sensors/list |
| moonraker_sensors_measurements | GET /machine/sensors/measurements |
| moonraker_spoolman_status | GET /server/spoolman/status |
| moonraker_spoolman_get_spool | GET /server/spoolman/spool_id |

### Remaining risks / Riesgos pendientes

1. OCI metadata ties the pinned image to the audited revision, but independently verify build provenance/attestation if available; labels are self-reported and upstream main can change independently.
2. Review each tool's input schema and restrict sensitive object names, sensor identifiers, job IDs and unusually large requests where needed.
3. GET requests can expose printer metadata, print history and Spoolman inventory. Review privacy implications.
4. Validate MCP sessions, SSE behavior, token handling, timeout and denial of unsupported methods with the intended client.
5. Verify the add-on under Home Assistant Supervisor on amd64 before installation; no real printer commands should be run.
6. The gateway is intentionally limited to a subset of MCP Streamable HTTP; remote HTTPS and secure network access are not yet implemented.

**Do not deploy or publish this DEV add-on.**

### Data exposure review / Revisión de datos expuestos

The gateway currently forwards tool results without field-level redaction. The bearer token therefore grants access to **all returned fields** of each permitted tool. The classifications below are conservative and must be validated with representative Moonraker responses before deployment.

| Exposure category | Tools | Data to inspect before deployment |
| --- | --- | --- |
| Low / operational | `moonraker_mcp_version`, `moonraker_printer_info`, `moonraker_temperature_store` | Software version, printer state, temperatures; verify device and host identifiers in actual responses |
| Medium / environment | `moonraker_server_info`, `moonraker_objects_list`, `moonraker_objects_query`, `moonraker_power_status`, `moonraker_sensors_info`, `moonraker_sensors_list`, `moonraker_sensors_measurements` | Host and device metadata, configured object names, sensor/device identifiers, possible paths |
| Medium / personal or business context | `moonraker_jobqueue_status`, `moonraker_history_list`, `moonraker_history_job`, `moonraker_history_totals`, `moonraker_spoolman_status`, `moonraker_spoolman_get_spool` | Print filenames, job timing, inventory IDs and spool metadata |

**Deployment gate:** do not expose this add-on beyond a trusted network or configure it as a ChatGPT connector until the user approves the information that may be disclosed. Consider a smaller default allowlist and optional feature groups (history, sensors, Spoolman) after inspecting actual payloads. HTTP read-only behavior does not guarantee privacy.

**Testing note:** the 1 MiB upstream-response cap is a transport limit, not a data-redaction mechanism. Authentication, logs and remote TLS configuration need independent review.

### Optional profile configuration validation

The add-on defaults all six optional profile switches (`files`, `objects`, `history`, `sensors`, `spoolman`, `power`) to `false`. Startup now rejects non-boolean values rather than treating strings or numbers as permission flags. Missing optional fields remain disabled for backward compatibility. A malformed configuration must prevent gateway startup; never silently broaden the allowlist.

### Klipper object-query privacy decision (implemented in DEV)

The default profile **does not expose** `moonraker_objects_list` or `moonraker_objects_query`. Both require the explicit Home Assistant option `enable_objects: true`. The gateway enforces this policy on both `tools/list` and `tools/call`; CI includes denial tests for the default and history-enabled profiles. The object-query tool can still return caller-selected Klipper fields when enabled. This opt-in is a privacy boundary, **not field-level redaction**.

**Privacy caveat:** `moonraker_jobqueue_status` is enabled by default and may disclose queued filenames even when the optional history profile is disabled. A read-only queue query is not necessarily low-sensitivity. For any future remote ChatGPT connection, inspect its real payload and obtain explicit consent; consider making job-queue access opt-in before deployment.\n\nThe five default tools are `moonraker_mcp_version`, `moonraker_server_info`, `moonraker_printer_info`, `moonraker_temperature_store`, and `moonraker_jobqueue_status`. With `history` enabled there are 8; with all optional profiles except `objects` there are 14; with all five optional profiles there are 16.

**Remaining deployment gate:** verify representative responses and explicit user approval before exposing even default status data to external MCP clients.

### Local file API audit (DEV, 2026-11-03)

Unlike the 16 upstream tools in the table, `moonraker_files_list`, `moonraker_files_metadata`, and `moonraker_files_preview` are **implemented locally** in the Python gateway. All require `enable_files: true`. Their HTTP endpoints are GET-only and limited to Moonraker's `gcodes` root. The preview returns at most 16 KiB, rejects NUL bytes, refuses redirects, and restricts extensions to `.gcode`/`.gco`. Filename validation rejects absolute paths, traversal segments, control characters, backslashes, and percent escapes. API-key headers must never be forwarded on redirects. The HTTP request's tool arguments must match each tool's schema.

These restrictions are **not** a guarantee that file names or G-code comments contain no sensitive information. No arbitrary config-root access, file modification, upload, deletion or full download is available. In particular, `printer.cfg` and other configuration files are **not accessible through this profile**.

**Deployment gate:** inspect representative G-code metadata and preview responses for sensitive comments before enabling `files`; do not expose file access to external clients merely because the calls are read-only.
