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
