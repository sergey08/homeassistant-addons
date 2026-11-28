# Nod native preflight

Experimental amd64-only Home Assistant app. It compiles upstream Nod at revision `6670bc233b6b7dddaa75b25b89b4a89f0e92bcac` and checks its authenticated health endpoint against PostgreSQL 17. Both services listen only on loopback, run as separate unprivileged users and remain running after the health check. Version dev.2 stores data and generated credentials under the app's private `/data/nod-native-v1` directory. CI checks database and key persistence across container replacement. Dev.3 adds a read-only Ingress status page, not the original Nod UI. Only the Supervisor ingress source 172.30.32.2 is accepted. Dev.4 adds an optional dedicated HTTPS UI, disabled by default, with no mapped port by default. No host Docker socket, additional permissions, browser or workspace. The current dev.14 status and validation are described below; the version-specific setup sections also retain historical validation notes. Upstream Nod is Apache-2.0 licensed by n8n GmbH; its license is included in the image.

## Dev.14: real task runtime connected

Server dev.14 connects the remote Workspace launcher to Nod's original command workspace and agent runtime. The actual composition and a real model-driven task have been validated on Home Assistant with Workspace dev.3 and Browser dev.4. The task opened the public IANA Example Domains page, returned a screenshot and attached a synthetic text file.

- Enable `workspace_runtime_enabled` on Server and `command_enabled` on Workspace to use general task commands. Defaults remain disabled.
- Browser tools retain upstream task/background gating: ask Nod to create and execute a task; ordinary conversation does not register the browser tool.
- Connected CLI execution remains unavailable. Commands are offline in the dedicated Workspace; public browsing runs through the separate Browser.
- `workspace_runtime_probe_enabled` is an optional synthetic end-to-end startup diagnostic requiring runtime and browser to be enabled. Disable it after validation; it is not needed for normal tasks.
- The runtime forwards the original pinned supervisor with verified hashes, real task-directory creation, cancellation, a 10-minute command timeout and a 16 MiB output limit.
- Per-process limits and a shared executor UID are not aggregate cgroup CPU/RAM limits or separate security principals per task. Those limitations and upstream upgrade validation remain open.

All six CI workflows passed for functional commit `671bf1265833b3b9ea7227f15de5c25a2eec097a`. The installed HA configuration keeps runtime enabled and automatic diagnostics disabled. Supervisor protection remains enabled, with no host Docker socket, host network or new published ports. This is an experimental branch, not a stable release.

### Español

La dev.14 conecta el Workspace remoto con las herramientas reales del agente. En HA se ha completado una tarea real que abrió IANA con el navegador, mostró la captura y adjuntó `prueba_nod.txt` con `Nod Workspace OK`.

Activa `workspace_runtime_enabled` en Server y `command_enabled` en Workspace para las órdenes generales de tareas (desactivados por defecto). El navegador conserva la condición original de ejecución en tareas: pide crear y ejecutar una tarea; no se registra en una conversación ordinaria. Las CLI conectadas siguen deshabilitadas. Las órdenes del Workspace no tienen acceso a Internet; la consulta pública usa el Browser separado.

El diagnóstico `workspace_runtime_probe_enabled` es opcional, requiere runtime y navegador activos y debe desactivarse tras la comprobación. La instalación validada conserva el runtime activo y los diagnósticos automáticos desactivados. Los límites por proceso y el usuario compartido no sustituyen límites agregados de CPU/RAM ni aislamiento por usuario entre tareas. Continúa siendo experimental, con protección Supervisor activa.

## Historical version-specific setup

## Dev.4 optional HTTPS setup

Use a dedicated DNS hostname (not the HA hostname) resolving locally to the HA host. Provision a trusted matching certificate and private key as `nod-fullchain.pem` and `nod-privkey.pem` in the app-specific configuration directory. Set `https_origin`, `lan_cidr` (private IPv4 /24 to /32), and an independent random `https_access_token` of at least 43 URL-safe characters. Enable HTTPS and map container port 8443 to the port in the configured origin. Do not forward the port on the router. Never paste tokens into logs or chat. An untrusted certificate must not be used to enter credentials. TLS runs as a separate unprivileged user; the original upstream authentication is retained. Webhooks and WebSocket upgrades are disabled in this experimental relay. Browser/workspace and actual model sign-in remain unverified. To roll back, disable HTTPS and remove the port mapping; the stored database and original keys remain intact.

## Español

Aplicación experimental amd64. Arranque nativo de Nod y PostgreSQL 17 con usuarios separados, sin QEMU, KVM, socket Docker del host, permisos adicionales ni puertos publicados. La dev.2 conserva datos y claves en el almacenamiento privado de la aplicación y mantiene los servicios arrancados después de comprobar su salud. La dev.3 añade un panel de estado de solo lectura mediante Ingress; no es la interfaz original de Nod. La dev.4 añade la opción de interfaz HTTPS con nombre DNS independiente, certificado de confianza y token aleatorio propio (mínimo 43 caracteres); está desactivada y sin puerto publicado por defecto. Configura los archivos nod-fullchain.pem y nod-privkey.pem en la carpeta privada de configuración de la aplicación, el origen y la red permitida, y mapea el puerto 8443 solo después de configurar DNS y certificado. No redirijas el puerto en el router. No introduzcas credenciales con un certificado no fiable. Para revertir, desactiva HTTPS y elimina el mapeo. Todavía faltan validar la sesión del modelo, navegador y espacio de trabajo.

## Dev.5 experimental HA panel

With the dedicated HTTPS URL already working, set `ha_embed_origin` to the exact HTTPS origin of Home Assistant, including its port if non-default. Leave it empty to disable embedding. The panel uses a separate-origin sandboxed iframe and does not forward Home Assistant credentials. Login inside the frame requires the existing Nod token and a browser that can confirm partitioned-cookie support. The standalone URL and strict cookie remain independent. Browser verification uses synthetic credentials and distinct HTTPS sites; the deployed HA frontend, real model calls, OAuth popups, raw attachment downloads and mobile compatibility still require validation. Browser/workspace/webhooks remain outside this change. Do not expose the port on the router.

### Español

La dev.5 permite configurar el origen HTTPS exacto de Home Assistant mediante `ha_embed_origin` (vacío = desactivado). La interfaz se carga en un iframe aislado, sin transferir credenciales de HA. El usuario inicia sesión con el token propio de Nod en un navegador compatible con cookies particionadas. El acceso independiente se conserva. Quedan pendientes las pruebas con HA real, modelos, ventanas OAuth, adjuntos y dispositivos móviles. No abrir puertos en el router.

## Dev.13: optional upstream Workspace diagnostic

The synthetic diagnostic can now use the pinned original `runWorkspaceCommand` supervisor through a separate TLS client launcher. Enable `workspace_command_probe_enabled` on Server and `command_enabled` on Workspace dev.3 only to run the synthetic checks. It verifies streaming, stdout/stderr/exit frames, Unicode input, cancellation with child-process confirmation, time/output limits, synthetic document files, recovery after a lost transport and rejection of a symlink task directory. The launcher is deliberately not wired into runtime agent tools. Connected CLIs remain unavailable. Per-process limits are not aggregate container CPU/RAM limits; resource and task-isolation checks remain required before enabling real agent tasks.

### Español

El diagnóstico sintético puede usar el supervisor original fijado de `runWorkspaceCommand` mediante un launcher TLS independiente. Activa `workspace_command_probe_enabled` en Server y `command_enabled` en Workspace dev.3 para ejecutar las pruebas sintéticas. Comprueba salida por partes, tramas de salida normal/error/final, entrada Unicode, cancelación con confirmación de procesos hijos, límites de tiempo/salida, archivos de documentos ficticios, recuperación tras perder el transporte y rechazo de directorios de tarea con enlaces simbólicos. El launcher todavía no está conectado a las herramientas del agente. Las CLI conectadas siguen deshabilitadas. Los límites por proceso no son límites agregados de CPU/RAM del contenedor; falta validar recursos y aislamiento antes de habilitar tareas reales del agente.
