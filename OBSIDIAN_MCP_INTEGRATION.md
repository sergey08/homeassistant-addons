# Obsidian MCP integration for Home Assistant

## English

Development version **0.3.0-beta.1**. The integration adds the Obsidian MCP server under **Settings → Devices & services**. It exposes the existing Streamable HTTP tools for listing, searching, reading, revising, writing, appending, moving and recoverably deleting Markdown notes. The existing tool names, parameters and response formats are preserved.

### Install and configure

1. Once the integration repository is available to HACS, add it as an **Integration**, download it and restart Home Assistant.
2. Under **Settings → Devices & services → Add integration**, select **Obsidian MCP**.
3. Select `local` and an existing directory under `/share`, or select `livesync` to use `<config>/obsidian_mcp/vault`. The two optional background services and the remote endpoint start disabled.
4. Open **Configure** to import LiveSync settings, check CouchDB, store the tunnel runtime key or see the vault and process status. Use **Reconfigure** to enable services or change the vault.

### ChatGPT, LiveSync and remote clients

- **ChatGPT:** Place the official platform-compatible `tunnel-client` in `<config>/obsidian_mcp/tunnel/bin/` with execute permission. Store the runtime key via **Configure** or copy it privately to `tunnel/api-key`. Enable the private tunnel with its existing `tunnel_…` ID. The integration provides a private loopback upstream on an automatically assigned port.
- **LiveSync:** Import the existing `livesync-operativo.json`, and provision a compatible LiveSync CLI wrapper at `<config>/obsidian_mcp/bin/livesync-cli`. It must run inside the Home Assistant Core environment and support the original app arguments `--settings`, `--vault`, `--interval` and the `LIVESYNC_DB_PATH` environment variable. The upstream [1.0.39 CLI](https://github.com/vrtmrz/obsidian-livesync/tree/1.0.39/src/apps/cli) uses Node.js and native dependencies. Provision a build compatible with the Core environment and CPU. The integration does not install Node.js or the CLI binary. If the vault already receives Markdown from an independent sync process, use local mode to keep that process. CouchDB remains a separate service.
- **Grok and other remote clients:** Enable remote MCP, provide an independent random Bearer token of at least 32 characters, and use `https://<your-ha-host>/api/obsidian_mcp/mcp` through your HTTPS entry point. The client must support Streamable HTTP and send `Authorization: Bearer <token>`. The private OpenAI tunnel continues using its loopback endpoint.

### Migrate and roll back

Back up the vault and provision private files outside GitHub. In local mode you can select the existing `/share` vault. In managed LiveSync mode, stop the old writer before copying the vault, recoverable trash and LiveSync settings to the integration's private directory or switching a shared vault to the integration. Keep LiveSync disabled until the CouchDB check succeeds. Stop the old tunnel client before enabling the same tunnel ID in the integration. Verify a disposable MCP note and, if applicable, its replication into a second Obsidian client. To roll back, disable the integration and restart the old app. Reconcile any edits made to a copied vault before switching back.

## Español

Versión de desarrollo **0.3.0-beta.1**. La integración añade el servidor MCP de Obsidian en **Ajustes → Dispositivos y servicios**. Conserva las herramientas Streamable HTTP para listar, buscar, leer, consultar revisiones, escribir, añadir texto, mover y enviar notas Markdown a una papelera recuperable. Mantiene los nombres, los parámetros y los formatos de respuesta.

### Instalar y configurar

1. Cuando el repositorio de integración esté disponible para HACS, añádelo como **Integración**, descárgalo y reinicia Home Assistant.
2. En **Ajustes → Dispositivos y servicios → Añadir integración**, selecciona **Obsidian MCP**.
3. Selecciona `local` y un directorio existente dentro de `/share`, o selecciona `livesync` para usar `<config>/obsidian_mcp/vault`. Los dos servicios opcionales y el acceso remoto quedan desactivados al inicio.
4. Abre **Configurar** para importar ajustes de LiveSync, comprobar CouchDB, guardar la clave del túnel o ver el estado de la bóveda y los procesos. Usa **Reconfigurar** para activar servicios o cambiar la bóveda.

### ChatGPT, LiveSync y clientes remotos

- **ChatGPT.** Coloca el `tunnel-client` oficial compatible con tu plataforma, con permiso de ejecución, en `<config>/obsidian_mcp/tunnel/bin/`. Guarda la clave de ejecución en **Configurar** o cópiala de forma privada a `tunnel/api-key`. Activa el túnel con el identificador `tunnel_…` existente. La integración ofrece un endpoint privado en loopback con puerto asignado automáticamente.
- **LiveSync.** Importa `livesync-operativo.json` y coloca un lanzador LiveSync CLI compatible en `<config>/obsidian_mcp/bin/livesync-cli`. Debe ejecutarse dentro del entorno de Home Assistant Core y admitir los argumentos de la aplicación original `--settings`, `--vault`, `--interval` y la variable `LIVESYNC_DB_PATH`. El [CLI 1.0.39 oficial](https://github.com/vrtmrz/obsidian-livesync/tree/1.0.39/src/apps/cli) utiliza Node.js y dependencias nativas. Prepara una compilación compatible con Core y con tu arquitectura. Node.js y el binario del CLI se proporcionan por separado. Si ya sincronizas la bóveda Markdown con un proceso independiente, selecciona el modo local para conservarlo. CouchDB sigue siendo un servicio separado.
- **Grok y otros clientes remotos.** Activa MCP remoto, genera un token Bearer independiente de 32 caracteres o más y usa `https://<tu-host-ha>/api/obsidian_mcp/mcp` a través de tu acceso HTTPS. El cliente debe admitir Streamable HTTP y enviar `Authorization: Bearer <token>`. El túnel privado de OpenAI sigue usando su endpoint de loopback.

### Migración y reversión

Haz una copia de la bóveda y prepara los archivos privados fuera de GitHub. En modo local puedes seleccionar la bóveda existente dentro de `/share`. Para LiveSync gestionado, detén el escritor anterior antes de copiar la bóveda, la papelera recuperable y los ajustes de LiveSync al directorio privado de la integración o antes de reutilizar la bóveda compartida. Mantén LiveSync desactivado hasta comprobar CouchDB. Detén el cliente de túnel anterior antes de activar el mismo ID en la integración. Verifica una nota de prueba a través de MCP y, si corresponde, su sincronización en otro cliente Obsidian. Para revertir, desactiva la integración y reinicia la aplicación anterior. Si editaste una copia de la bóveda, reconcilia esos cambios antes de volver a la original.
