# Moonraker MCP Safe Print BETA — Changelog

## 0.1.5-beta.7 (candidate)

- Print-control POST connection timeouts and lost replies are explicitly reported as **outcome unknown**, rather than as a confirmed failed operation.
- **No automatic retries** of start, pause, resume or cancel after an uncertain response. Inspect the printer state and active filename before deciding on any new action.
- Added offline regression coverage for a timed-out resume operation, ensuring only one POST is attempted.
- Supervised Snapmaker U1 validation: G-code upload integrity (637 bytes, SHA-256 checked on both ends), START, PAUSE and CANCEL verified. RESUME returned TimeoutError, while a later snapshot showed `printing`; this is consistent with a delayed or lost confirmation, but is not proof of the underlying cause.
- Safe defaults preserved: all write controls disabled until separately opted in; human authorization required for each physical action.

**Not yet validated:** a clean end-to-end RESUME acknowledgment on the installed beta. Do not assume a failed response means the printer did not act.

## 0.1.5-beta.6

- Prior isolated beta used for supervised G-code staging/upload and initial print-control tests.
