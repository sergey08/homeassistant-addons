# Nod Workspace experimental diagnostic

Workspace dev.2 is offline by default. Optional TLS-PSK transport accepts only the configured Nod Server peer. The worker supports two fixed synthetic programs (print 42 and cancellable sleep); it does not accept caller commands or enable agent tasks. Both sides require a separate random 256-bit hexadecimal key, different from Browser and HTTPS credentials. No host ports, Docker socket, HA mounts or Supervisor API are used. The unprivileged worker cannot read the transport key. CI tests authentication failures, cancellation, recovery, private-network blocking, persistence and the packaged Server diagnostic.

Enable `remote_enabled`, provision `remote_key` privately and set `server_host` to the installed Nod Server hostname. On Server dev.12, use `workspace_probe_enabled`, `workspace_key` and `workspace_host`. Never paste keys into chat or logs. This is a bounded diagnostic, not the upstream command execution protocol. Disable the diagnostic options to return to offline mode; data persists.

## Español

Workspace dev.2 funciona sin red por defecto. El transporte opcional TLS-PSK acepta únicamente al Nod Server configurado. El proceso admite dos programas sintéticos fijos (imprimir 42 y espera cancelable); no acepta órdenes del solicitante ni habilita tareas del agente. Ambos extremos necesitan una clave hexadecimal aleatoria propia de 256 bits, diferente de las credenciales del navegador y HTTPS. No utiliza puertos del host, socket Docker, montajes HA ni API Supervisor. El proceso sin privilegios no puede leer la clave. CI comprueba rechazo de autenticación, cancelación, recuperación, bloqueo de red privada, persistencia y diagnóstico desde el paquete de Server.

Activa `remote_enabled`, configura `remote_key` de forma privada y usa el hostname del Server en `server_host`. En Server dev.12 configura `workspace_probe_enabled`, `workspace_key` y `workspace_host`. No copies claves al chat ni a registros. Es un diagnóstico limitado; todavía no implementa el protocolo original de ejecución de órdenes. Desactiva las opciones de diagnóstico para volver al modo sin red; los datos se conservan.
