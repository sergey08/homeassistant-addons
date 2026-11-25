# Nod Browser — experimental preflight

Optional isolated browser worker for Nod on Home Assistant OS (amd64). Builds the upstream browser at the same pinned revision as the native server. It is not a usable browser integration yet: it has no published port, no Ingress and no connection to Nod Server.

The app requires NET_ADMIN solely to install an IPv4/IPv6 firewall in its own container network namespace. Host networking, host PID/IPC, Docker access and Supervisor/Home Assistant API access are disabled. Startup fails if firewall configuration fails. The worker runs as uid 1000 with its Linux capabilities removed and no-new-privileges enabled. Persistent browser data belongs to this app alone. No server database or vault is mounted. This is an experimental defense in depth; actual Supervisor restrictions, memory use and startup must still be verified on HA OS.

Do not disable protection to make it start. Do not expose a port or share the worker's data directory. The next phase is a narrowly scoped, authenticated and encrypted internal transport; it is not implemented here.

## Español

Aplicación experimental independiente para el navegador oficial de Nod. No tiene puertos publicados, Ingress ni conexión con Nod Server. NET_ADMIN se usa únicamente durante el arranque para instalar el cortafuegos en la red propia del contenedor. Después se eliminan las capacidades del proceso navegador y se activa no-new-privileges. No utiliza socket Docker, red del host, API de Supervisor ni datos privados del servidor Nod. Si falla el cortafuegos, no arranca Chromium. Pendiente validar en Home Assistant OS real; no desactivar protección. Todavía no permite navegar desde Nod.
