# Moonraker MCP — isolated safe-print beta acceptance

**Status:** checklist only; no release, installation or printer operation authorized.
Stable `0.1.4` remains untouched.

## Before creating a beta
- [ ] Both GitHub CI workflows pass on the same branch HEAD.
- [ ] Confirm the optional upload profile is disabled by default.
- [ ] Confirm `enable_write_actions=false`, `allow_gcode_upload=false`, and `allow_print_start=false` in the beta's initial options.
- [ ] Review all diff files against stable; no unexpected changes to read-only tools or tunnel credentials.
- [ ] Confirm AMD64 and ARM64 image builds, source provenance, and license review.
- [ ] Use a separate test add-on slug and isolated `/data` volume; never overwrite the stable add-on or its configuration.

## Offline validation (no printer)
- [ ] With both write gates off, staging directory is not created and housekeeping is not launched.
- [ ] With only one gate on, neither upload nor staging is authorized.
- [ ] With both gates on, staging is private (0700, UID/GID 65534).
- [ ] Stage two chunks; verify final SHA-256 and reject mismatch, symlinks and oversized chunks.
- [ ] Verify abort requires `CONFIRM_ABORT_STAGE` and cannot delete completed G-code.
- [ ] Verify housekeeping removes only valid incomplete files older than seven days; never removes active, unknown or published files.
- [ ] Verify no HTTP request to Moonraker is made during staging, abort or cleanup.
- [ ] Verify simulated upload sends `print=false`; no print-start action is exercised.

## Isolated beta validation (requires separate approval)
- [ ] Confirm beta add-on identity, volume isolation, network binding and authentication.
- [ ] Start with read-only profile and inspect the MCP tool catalog.
- [ ] Test staging and cleanup with synthetic G-code; verify permissions and quotas.
- [ ] Stop and restart the beta; ensure no automatic printing or unexpected upload.
- [ ] Review logs for secrets, stack traces, excessive growth and failure handling.
- [ ] Obtain explicit approval before any real upload to Snapmaker U1.
- [ ] Do **not** enable print-start during this phase.

## Rollback
Stop/remove only the isolated beta add-on; preserve stable `0.1.4` and its data. Do not delete printer files or issue a print command.
