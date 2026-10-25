# SeRgEY — Home Assistant Apps

Aplicaciones de código abierto para **Home Assistant OS / Supervised**.

Este repositorio agrupa aplicaciones independientes que se instalan desde la **Tienda de aplicaciones** de Home Assistant. Una sola URL permite descubrir las aplicaciones actuales y las que publiquemos más adelante.

## Instalación del repositorio

1. Abre **Home Assistant → Ajustes → Aplicaciones → Tienda de aplicaciones**.
2. En el menú **⋮ → Repositorios**, añade:
   `https://github.com/sergey08/homeassistant-addons`
3. Actualiza la tienda de aplicaciones. Las aplicaciones compatibles aparecerán en el catálogo.

> **Aviso:** las aplicaciones en fase de desarrollo no deben considerarse versiones estables.

## Aplicaciones

### 📓 Obsidian Client — en desarrollo (0.1.0-dev1)

Visor Markdown integrado en Home Assistant mediante **Ingress** y acceso desde la barra lateral.

**Funcionalidades incluidas en el prototipo:**
- Navegación de notas Markdown almacenadas localmente en `/share`.
- Búsqueda por ruta y nombre.
- Renderizado de Markdown, tablas y bloques de código.
- Acceso en modo solo lectura sin necesidad de Obsidian MCP.

**Pendiente:** conexión y sincronización con LiveSync/CouchDB, compatibilidad con bóvedas cifradas mediante un puente seguro, imágenes, enlaces wiki y pruebas de instalación.

[Código de la aplicación](./obsidian_client/) · [Instrucciones y limitaciones](./obsidian_client/DOCS.md)

## Otros proyectos relacionados

- [Obsidian MCP for Home Assistant](https://github.com/sergey08/obsidian-mcp-homeassistant): acceso MCP a Obsidian para asistentes de IA. Proyecto independiente; no es un requisito del cliente visual.

## Contribuir

Puedes utilizar **Issues** para informar de errores y proponer mejoras, y **Pull requests** para enviar cambios. La publicación y aceptación de cambios queda a cargo del mantenedor.

## Seguridad

No publiques contraseñas, tokens, claves de cifrado, documentos privados ni archivos de tu bóveda en el repositorio.

## Licencia

[MIT](./LICENSE).
