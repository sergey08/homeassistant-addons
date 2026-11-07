# SeRgEY — Home Assistant Apps / Aplicaciones para Home Assistant

**EN:** Open-source Home Assistant apps, distributed through one repository.  
**ES:** Aplicaciones de código abierto para Home Assistant, distribuidas desde un único repositorio.

[![Add this repository to Home Assistant](https://my.home-assistant.io/badges/supervisor_add_addon_repository.svg)](https://my.home-assistant.io/redirect/supervisor_add_addon_repository/?repository_url=https%3A%2F%2Fgithub.com%2Fsergey08%2Fhomeassistant-addons)

## English

### One-click repository setup

Click the **Add Repository** badge above. Choose your Home Assistant instance and confirm adding this repository. The button adds the *catalog*, not an app automatically.

If the redirect does not pre-fill the repository dialog, open **Settings → Apps → App Store → ⋮ → Repositories** and paste:

```text
https://github.com/sergey08/homeassistant-addons
```

### Available apps

**Obsidian MCP for Home Assistant — 0.2.7**

- Install from the Home Assistant app store on AMD64 (`amd64`) or ARM64 (`aarch64`).
- Work with local Markdown files or use optional Self-hosted LiveSync with your existing CouchDB server. Use the optional OpenAI Secure MCP Tunnel for private access from ChatGPT.
- Update an existing installation from its own app page to retain its persistent vault and configuration. A separate catalog entry is a separate installation.
- For a new tunnel setup, choose the official Linux ZIP that matches your architecture and use the SHA256 manifest from the same release. Home Assistant `aarch64` uses the `linux-arm64.zip` package.

In the app’s **Configuration** tab, choose a **Storage mode**.

| Storage mode | How to set it up | Where the notes are stored |
| --- | --- | --- |
| `livesync` | Enable **Enable LiveSync** and use your existing Self-hosted LiveSync settings and CouchDB server. Fill in **LiveSync shared vault path** only if you already use a shared vault under `/share`. | The existing LiveSync vault, synchronized with CouchDB. |
| **Local - default** | Leave both path fields empty. Save and restart. The app creates the vault with `Bienvenida.md` the first time. | `/config/local-vault` inside the app. It is included when Home Assistant backs up the app and is accessible through Samba at `app_configs/<app-id>/local-vault`. |
| **Local - Personal folder path** | Enter the full path of an existing folder under `/share` in **Local - Personal folder path**. Save and restart. | Your chosen Markdown folder. Include `share` in your Home Assistant backup to back up these notes. |

Both local modes work without CouchDB. Changing modes leaves notes in their original locations. If you previously saved `local`, select **Local - Personal folder path** when updating and keep the path you already use.

[App source](./obsidian_suite/) · [Documentation](./obsidian_suite/DOCS.md)


**Obsidian Client — 0.1.0-dev2 (experimental)**

- Browse local Markdown notes under `/share` using Home Assistant Ingress.
- Search note paths/names and render Markdown, tables and code blocks.
- Read-only operation; no Obsidian MCP required.

**Not yet supported:** LiveSync/CouchDB connection and decryption, automatic sync, embedded attachments and wiki links. The app has been installed and tested on Home Assistant OS (HTTP 200, Gunicorn). Markdown rendering with real notes and LiveSync are not yet validated; this is not a stable release.

[App source](./obsidian_client/) · [Documentation (EN/ES)](./obsidian_client/DOCS.md)

### Related project

[Obsidian MCP for Home Assistant](https://github.com/sergey08/obsidian-mcp-homeassistant) is an independent project for AI assistant access to Obsidian, not a prerequisite for this reader.

### Contributing and security

Use **Issues** for bugs and feature requests and **Pull requests** for proposed changes. The maintainer controls changes to the main branch. Do not publish secrets, encryption keys, passwords or private vault contents.

## Español

### Añadir el repositorio con un clic

Pulsa el botón **Add Repository** situado arriba. Selecciona tu instancia de Home Assistant y confirma que quieres añadir este repositorio. El botón añade el *catálogo*, no instala automáticamente una aplicación.

Si el enlace no rellena automáticamente el diálogo de repositorios, abre **Ajustes → Aplicaciones → Tienda de aplicaciones → ⋮ → Repositorios** y pega:

```text
https://github.com/sergey08/homeassistant-addons
```

### Aplicaciones disponibles

**Obsidian MCP for Home Assistant — 0.2.7**

- Instala el complemento desde la tienda de Home Assistant en AMD64 (`amd64`) o ARM64 (`aarch64`).
- Trabaja con archivos Markdown locales o activa Self-hosted LiveSync con tu servidor CouchDB existente. El túnel seguro de OpenAI es opcional y permite el acceso privado desde ChatGPT.
- Actualiza una instalación existente desde su propia ficha para conservar la bóveda y la configuración persistentes. Una entrada de otro catálogo corresponde a una instalación independiente.
- Para configurar un túnel nuevo, elige el ZIP oficial de Linux que corresponda a tu arquitectura y usa el manifiesto SHA256 de la misma versión. Home Assistant `aarch64` usa el paquete `linux-arm64.zip`.

En la pestaña **Configuración** de la aplicación, elige un modo en **Storage mode**.

| Storage mode | Cómo se configura | Dónde quedan las notas |
| --- | --- | --- |
| `livesync` | Activa **Enable LiveSync** y utiliza tu configuración de Self-hosted LiveSync y tu servidor CouchDB. Rellena **LiveSync shared vault path** solo si ya usas una bóveda compartida bajo `/share`. | En la bóveda existente de LiveSync, sincronizada con CouchDB. |
| **Local - default** | Deja vacíos los dos campos de ruta. Guarda y reinicia. La aplicación crea la bóveda con `Bienvenida.md` la primera vez. | En `/config/local-vault` dentro de la aplicación. Se incluye al respaldar la aplicación en Home Assistant y está accesible por Samba en `app_configs/<id-de-la-app>/local-vault`. |
| **Local - Personal folder path** | Introduce en **Local - Personal folder path** la ruta completa a una carpeta existente bajo `/share`. Guarda y reinicia. | En la carpeta Markdown que elijas. Incluye `share` en la copia de Home Assistant para respaldar estas notas. |

Ambos modos locales funcionan sin CouchDB. Al cambiar de modo, las notas permanecen en su ubicación original. Si tenías guardado `local`, al actualizar selecciona **Local - Personal folder path** y conserva tu ruta actual.

[Código](./obsidian_suite/) · [Documentación](./obsidian_suite/DOCS.md)


**Obsidian Client — 0.1.0-dev2 (experimental)**

- Navega por notas Markdown locales dentro de `/share` mediante Ingress.
- Busca por ruta o nombre y muestra Markdown, tablas y bloques de código.
- Funciona en modo solo lectura; no necesita Obsidian MCP.

**Todavía no disponible:** conexión y descifrado LiveSync/CouchDB, sincronización automática, adjuntos y enlaces wiki. La aplicación ya se ha instalado y probado en Home Assistant OS (HTTP 200 y Gunicorn). Falta validar la lectura de notas reales y LiveSync; no es una versión estable.

[Código de la aplicación](./obsidian_client/) · [Documentación (EN/ES)](./obsidian_client/DOCS.md)

### Proyecto relacionado

[Obsidian MCP para Home Assistant](https://github.com/sergey08/obsidian-mcp-homeassistant) es un proyecto independiente que permite a asistentes de IA acceder a Obsidian; no es necesario para este lector.

### Colaboración y seguridad

Utiliza **Issues** para informar de errores y proponer mejoras, y **Pull requests** para sugerir cambios. El mantenedor controla los cambios en la rama principal. No publiques contraseñas, claves de cifrado ni documentos privados.

---

## License / Licencia

[MIT](./LICENSE).
