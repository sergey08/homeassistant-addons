# Moonraker MCP — Installation and configuration / Instalación y configuración

> **Development preview (DEV11, 2026-11-06).** Do not merge into `main` or publish a stable release until release gates below are complete. English first, Spanish second.

**Second-system acceptance / Prueba independiente:** [Clean HA OS installation and recovery acceptance checklist](./CLEAN_INSTALL_ACCEPTANCE_EN_ES.md). This is a planned second-system test, not a claim that it has already passed.

## English — Install without terminal commands

### What this add-on does

Moonraker MCP hosts a restricted, read-only MCP server for a Moonraker-compatible 3D printer. Home Assistant runs the server; queries go **directly to Moonraker**, not through Home Assistant entities. A separate optional outbound **OpenAI Secure MCP Tunnel** allows ChatGPT to reach the private MCP server without opening router ports. The MCP server still runs locally with the tunnel disabled.

### Requirements

- Home Assistant OS / Supervisor on **amd64 (x86-64)** for this development version. arm64 is not yet supported because the pinned official OpenAI tunnel client has only been validated for amd64.
- A reachable Moonraker instance (typically port 7125) and its API key if configured.
- A ChatGPT account/workspace with access to custom MCP servers and OpenAI Secure MCP Tunnel, and permissions to create/manage your own tunnel in OpenAI Platform. Availability depends on account and workspace settings.
- A **unique** strong MCP HTTP bearer token. Do not reuse your printer API key, OpenAI API key or other service tokens.

### 1. Add the development repository and install

The DEV preview lives in the **same** GitHub repository as the other SeRgEY Home Assistant apps, but is served from its separate branch:

`https://github.com/sergey08/homeassistant-addons#dev/moonraker-mcp-dev2`

In Home Assistant, navigate to **Settings → Apps → App Store → ⋮ → Repositories**, enter that exact URL, refresh the store, and install **Moonraker MCP (DEV)** from the branch-specific SeRgEY catalog. Installing this branch does **not** install or overwrite the stable repository's other apps. Do not install another local copy simultaneously unless you know which instance is running.

### 2. Fill in Home Assistant → Moonraker MCP (DEV) → Configuration

| Setting | Enter | Notes |
| --- | --- | --- |
| `moonraker_url` | e.g. `http://printer.local:7125` | Use the real local API endpoint, **not** the Fluidd page address if that page uses a different port |
| `moonraker_api_key` | Your own Moonraker API key | Optional only when Moonraker does not require it |
| `mcp_http_token` | A new long, randomly generated secret | Required; separate from every other credential |
| `enable_tunnel` | **Off** initially | Leave disabled until your local settings are ready |
| `tunnel_id` | Your own `tunnel_...` ID | Created in OpenAI Platform |
| `openai_tunnel_api_key` | Your own **restricted** OpenAI Platform API key | Protected password field; new installs need this to enable the tunnel |
| All other `enable_*` options | **Off** initially | These expose more data; enable only after reviewing privacy implications |

Do **not** paste any of these secrets into a support request, screenshot, ChatGPT conversation or GitHub issue. Home Assistant's password widget hides text from casual viewing; it is still stored as a protected application option and an administrator of Home Assistant can access the configuration. Protect Supervisor backups appropriately.

### 3. Create your own OpenAI tunnel and restricted key

Open the official OpenAI Platform tunnel administration screen at `https://platform.openai.com/settings/organization/tunnels`. Create a tunnel dedicated to this printer. Copy **only** its ID to `tunnel_id`.

In `https://platform.openai.com/settings/organization/api-keys`, generate an **independent restricted API key** for the tunnel, with only the permissions required by the platform for the tunnel (currently **Tunnels: Read + Use** where offered). Enter that key in `openai_tunnel_api_key` in the **Home Assistant UI**. Do not paste it into terminal commands and do not reuse another MCP tunnel's key.

DEV11 bundles the official pinned `tunnel-client` for amd64 in the add-on image. The add-on automatically provisions a private executable and token file when tunnel access is enabled. **New users do not need to install a ZIP or run Docker commands.**

### 4. Start the app and enable the tunnel

1. Save the configuration with `enable_tunnel: false`, then start the add-on. It should remain running, even if the printer is currently switched off.
2. Verify `moonraker_url` and API-key settings if Moonraker is reachable. When the printer is off or the network fails, `moonraker_connection_status` reports `offline_or_unreachable`; this does **not** establish whether the printer has power.
3. Change only `enable_tunnel` to **On**, save and **restart** the app.
4. In the add-on logs, look for `tunnel-client started` and `mcp session initialized`. Do not disclose private keys when sharing diagnostic logs.
5. Leave **8765/tcp unpublished** in the Home Assistant Network configuration. Do not forward router ports.

### 5. Register the server with ChatGPT

Open **Settings → Plugins → Add → Custom MCP server** (menu labels vary by client). Select **Tunnel**, pick the tunnel you created for Moonraker, choose **No authentication** for the MCP endpoint **behind the tunnel**, then create the plugin. This does **not** mean the tunnel is publicly unauthenticated: the outbound OpenAI tunnel uses your restricted API key and an internal authenticated bridge uses the separate MCP bearer token.

The actual DEV11 installation was verified from ChatGPT using **all five read-only tools** through the private tunnel. This is a test of an existing installation, **not** a clean first-install test on another Home Assistant. Other accounts/workspaces may behave differently. **Never expose the raw gateway port** to mimic this flow.

### What ChatGPT can read by default

- `moonraker_connection_status`: printer online / unavailable / not ready / credentials rejected.
- `moonraker_mcp_version`: upstream MCP server version.
- `moonraker_printer_info`: validated Klippy state and firmware/software version only; no host paths or CPU information.
- `moonraker_server_info`: Moonraker version, API version and Klippy connection/readiness only; no component lists or warnings.
- `moonraker_temperature_store`: up to 120 recent numeric readings per sensor series, with nonstandard sensor names anonymized.

The DEV11 default tools deliberately suppress hostnames and filesystem paths, but still reveal machine availability, versions and limited temperature activity. The default profile has **no G-code execution, print start/stop, power control, upload, deletion, full file access, or Home Assistant administration**.

### Troubleshooting / safety

| Symptom | Check |
| --- | --- |
| Printer offline in ChatGPT | Printer power, network and Moonraker URL; the MCP gateway may remain online |
| `authentication_error` | Moonraker API key and permissions |
| Tunnel disabled or exits on startup | Ensure tunnel ID and restricted OpenAI key are filled in; check private file permissions and logs |
| ChatGPT cannot add the server | Verify tunnel selection, account/workspace access, and the app's running status; review logs without disclosing credentials |
| Add-on needs terminal intervention | Report as a DEV usability bug; a clean DEV11 install should not require manual provisioning |

## Español — Instalación sin utilizar el terminal

### Qué hace el complemento

Moonraker MCP ofrece un servidor MCP de **solo lectura** para impresoras 3D compatibles con Moonraker. Se ejecuta en Home Assistant, pero **consulta directamente Moonraker**, sin pasar por las entidades de Home Assistant. El túnel privado opcional de OpenAI permite que ChatGPT acceda al MCP mediante una conexión saliente sin abrir puertos del router. El MCP también puede ejecutarse localmente sin túnel.

### Requisitos

- Home Assistant OS / Supervisor en **amd64 (x86-64)** para esta versión DEV. arm64 sigue pendiente de verificar.
- Moonraker accesible desde la red local y su clave API cuando se requiera.
- Acceso en ChatGPT a servidores MCP personalizados y a OpenAI Secure MCP Tunnel, sujeto a las opciones de la cuenta o espacio de trabajo.
- Un token MCP nuevo, largo y aleatorio, distinto de cualquier otra clave.

### 1. Añadir el catálogo DEV e instalar

En **Ajustes → Aplicaciones → Tienda de aplicaciones → ⋮ → Repositorios**, añade:

`https://github.com/sergey08/homeassistant-addons#dev/moonraker-mcp-dev2`

Actualiza la tienda e instala **Moonraker MCP (DEV)** desde el catálogo SeRgEY correspondiente a esa rama. Es el **mismo repositorio GitHub** que el resto de nuestras aplicaciones, pero el sufijo `#rama` selecciona el catálogo de desarrollo. No es necesario crear otro repositorio ni copiar archivos al complemento local.

### 2. Configurar desde Home Assistant, sin comandos

En **Moonraker MCP (DEV) → Configuración**, introduce:

| Opción | Qué poner |
| --- | --- |
| `moonraker_url` | Dirección de la API de Moonraker, por ejemplo `http://printer.local:7125`, no confundir con la web de Fluidd |
| `moonraker_api_key` | Clave de Moonraker, si se necesita |
| `mcp_http_token` | Contraseña nueva, aleatoria y exclusiva del gateway MCP |
| `enable_tunnel` | **Desactivado** inicialmente |
| `tunnel_id` | ID `tunnel_...` creado en la plataforma OpenAI |
| `openai_tunnel_api_key` | Clave restringida de OpenAI Platform para el túnel |
| Resto de opciones `enable_*` | **Desactivadas**, salvo autorización específica |

**Nunca publiques claves ni capturas con contraseñas visibles.** El campo de contraseña de Home Assistant evita que se vean en pantalla, pero un administrador del sistema puede acceder a las opciones almacenadas: protege las copias de seguridad.

### 3. Crear túnel y clave propios

En `https://platform.openai.com/settings/organization/tunnels`, crea un túnel exclusivo para esta impresora y copia su identificador en `tunnel_id`.

En `https://platform.openai.com/settings/organization/api-keys`, crea una clave **Restricted** con los permisos mínimos necesarios para usar ese túnel (opciones **Tunnels Read + Use** cuando estén disponibles). Copia la clave **directamente en el campo protegido** `openai_tunnel_api_key` de Home Assistant. No es necesario abrir terminal, usar Docker ni descargar el cliente OpenAI: DEV11 ya lo incluye y aprovisiona automáticamente al activar el túnel.

### 4. Arrancar y comprobar

Guarda primero la configuración con el túnel desactivado y arranca el complemento. Después activa `enable_tunnel`, guarda y **reinicia**. En el registro deben aparecer `tunnel-client started` y `mcp session initialized`. Deja el puerto **8765 sin publicar** y no abras puertos del router.

Si Moonraker no responde, ChatGPT podrá indicar que la impresora **podría estar apagada o desconectada**, pero no puede saber con certeza si está apagada o si falla la red.

### 5. Añadir el MCP a ChatGPT

Abre **Configuración → Complementos → Añadir → Servidor MCP personalizado**, selecciona **Túnel**, elige tu túnel y usa **Sin autenticación** para el endpoint MCP *interno al túnel*. El túnel se autentica por separado y el gateway sigue protegido por su propio token.

En nuestra prueba DEV11 real se descubrieron las cinco herramientas de lectura y se realizaron consultas desde ChatGPT a la Snapmaker U1. Eso no implica que todas las cuentas de ChatGPT tengan la misma función habilitada.

### Permisos y limitaciones

Por defecto solo se consultan conectividad, versión del MCP, información de Moonraker, información de Klippy y temperaturas almacenadas. Se mantienen desactivadas las consultas opcionales de ficheros G-code, historial, sensores, inventario Spoolman, energía y objetos Klipper. En DEV11, el estado de servidor e impresora oculta rutas, nombres de host y detalles internos; el historial térmico está limitado a **120 muestras por serie** y los sensores personalizados se anonimizan. **No se pueden ejecutar G-code, iniciar o detener impresiones, borrar archivos ni controlar la alimentación mediante el perfil predeterminado.**

### Incidencias frecuentes

| Síntoma | Revisar |
| --- | --- |
| ChatGPT dice que no puede contactar con Moonraker | Alimentación de la impresora, red y dirección de Moonraker |
| Error de autenticación | Clave de Moonraker y permisos |
| No arranca el túnel | ID, clave Restricted y registro del complemento |
| ChatGPT no permite instalar el MCP | Permisos de cuenta, selección del túnel y estado del complemento |
| El instalador pide Docker o terminal | Informar como incidencia DEV: el flujo normal no debe necesitarlo |

## Release gates / Condiciones antes de publicar estable

- [x] Pruebas CI, instalación de la rama desde GitHub y túnel con conexión real desde ChatGPT
- [x] Cinco herramientas de lectura detectadas y consultas reales a una impresora encendida
- [x] Puerto externo sin publicar; perfiles opcionales desactivados
- [x] Validar desde ChatGPT la impresora **apagada**, y su recuperación tras encenderla
- [x] Filtrado y pruebas reales de privacidad de las cinco herramientas predeterminadas de DEV11 (incluido historial térmico acotado)
- [ ] Instalar desde cero en Home Assistant limpio **sin terminal**, con credenciales nuevas
- [x] Comprobar la versión anunciada y las cinco herramientas reales de DEV11 desde ChatGPT
- [ ] Verificar mantenimiento, rotación de secretos, recuperación ante fallos y copias de seguridad
- [ ] Validar compatibilidad arm64 o documentar la limitación final
- [ ] Completar revisión humana de atribuciones y avisos de los componentes exactos del SBOM, obligaciones GPL/LGPL y distribución
- [ ] Obtener autorización explícita para fusionar a `main` y publicar estable
