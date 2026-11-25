# Nod browser HA transport — implementation checklist

Validated: exact upstream worker, separate container firewall, TLS 1.2 ECDHE-PSK and real browser requests over TLS, including separate-container tests (e61d849644acf342d9ac7fc42f19ffbe96b0a859, run 45589407329). The test's temporary firewall exception and synthetic key are NOT production provisioning.

## Production requirements (before enabling the channel)

- Default disabled on both apps. Existing server must still run and use MCP if the browser is unavailable. No host ports, Docker socket, host network or new Supervisor API permissions.
- Provision an independently generated random 32-byte key through each app's password configuration, never in Git, command arguments, logs or chat. Separate gateway UID from Chromium. Root-owned /data/options.json must not be readable or replaceable by Chromium; use a dedicated private browser data subdirectory, not ownership of the entire /data mount. Keep the gateway key in a separate private runtime directory, not the worker's home or browser data.
- Put the upstream control socket in a dedicated directory with controlled group access for the gateway only, not in a shared profiles directory. Reuse upstream worker with a minimal exact-anchored socket permissions patch; verify file ownership, socket permissions and both process privilege drops. The gateway and worker must have no effective or bounding capabilities and no-new-privileges.
- Resolve the configured HA server internal hostname at startup, before opening a listener. Reject non-private, multiple or unexpected addresses; permit only one IPv4 peer. If its address changes, fail closed and restart/re-resolve; do not allow a whole subnet as a fallback. Browser accepts port 9592 only from this peer, and only established response packets from that port can go back. TLS still authenticates the peer; no plaintext fallback.
- Check DNS on HA OS. Public navigation must resolve public names while still blocking direct LAN access; do not silently open the entire HA private DNS network. Verify against HA OS's actual resolver and prefer public DNS when supported.
- Use upstream BrowserBridgeLauncher with a fixed Node client executable, no arbitrary shell, no Docker socket, no model-controlled host or key. Test stdout/stderr/exit/cancellation and streaming. Keep source patch exact and fail if upstream changes.
- Test actual packaged apps together in CI: wrong key, plaintext, other peer, private destination, browser cannot read key or modify config, worker and gateway capabilities, file streaming, cancel/disconnect and restart. Then protected HA deployment, real public site and harmless private destination check. No stable release without user approval.

## Español

El canal entre contenedores ya está validado con datos ficticios. Antes de activarlo en HA, separar usuario del proceso navegador y usuario de pasarela, proteger la clave, restringir el cortafuegos a un único servidor, comprobar DNS real, conservar el servidor operativo si el navegador falla y verificar el paquete completo. No abrir puertos del host ni desactivar protección. Las versiones instaladas dev.7 (servidor) y dev.2 (navegador) permanecen sin cambios.
