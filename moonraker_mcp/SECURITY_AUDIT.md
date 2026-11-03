# Moonraker MCP — read-only tool audit (DEV)

Audit date: 2026-11-03. Source inspected: `lexfrei/mcp-raker` Go handlers under `internal/tools/` (current default branch; **not yet verified against pinned image digest**).

The HTTP gateway enforces an explicit allowlist of 16 names, and rejects calls to other names before forwarding to the loopback-only upstream. This review describes the handler behavior seen in source; it is **not a security certification**.

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

1. Confirm that the pinned upstream image corresponds to the audited source revision. Upstream main can change independently.
2. Review each tool's input schema and restrict sensitive object names, sensor identifiers, job IDs and unusually large requests where needed.
3. GET requests can expose printer metadata, print history and Spoolman inventory. Review privacy implications.
4. Validate MCP sessions, SSE behavior, token handling, timeout and denial of unsupported methods with the intended client.
5. Verify the add-on under Home Assistant Supervisor on amd64 before installation; no real printer commands should be run.
6. The gateway is intentionally limited to a subset of MCP Streamable HTTP; remote HTTPS and secure network access are not yet implemented.

**Do not deploy or publish this DEV add-on.**
