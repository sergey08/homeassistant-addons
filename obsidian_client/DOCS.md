# Obsidian Client — Vista previa de desarrollo

Esta aplicación abre un explorador de archivos Markdown locales en la barra lateral de Home Assistant mediante Ingress.

## Requisitos

- Home Assistant OS / Supervised.
- Carpeta Markdown local disponible en `/share/obsidian-client/vault` (o cambia `vault_path` por otra ruta dentro de `/share`).

## Limitaciones actuales

- Solo lectura; no edita notas.
- No accede ni descifra directamente una base de datos CouchDB/LiveSync.
- No sincroniza automáticamente con Obsidian Sync Server SSL.
- No se ha verificado aún la compilación e instalación en Home Assistant.

**No introduzcas credenciales ni claves de cifrado en GitHub.**
