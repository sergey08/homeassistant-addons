# Obsidian Client — Developer preview / Vista previa de desarrollo

## English

This is an **independent** Home Assistant application. It does not use, require or read Obsidian MCP files.

Version **0.1.0-dev4** has a local Markdown preview and an experimental read-only CouchDB connectivity check. It **does not** decode or edit LiveSync notes.

### Configuration
- `vault_path`: optional local Markdown directory inside `/share`.
- `couchdb_url`: CouchDB server root URL (prefer HTTPS; HTTPS is required when credentials are supplied).
- `couchdb_database`: database name.
- `couchdb_username`, `couchdb_password`: CouchDB credentials; set **only** in Home Assistant app settings.

The **CouchDB status / Estado CouchDB** link checks database metadata, without fetching or modifying documents. It returns only connection status and the document count. Credentials never belong in GitHub.

### Limitations
- No LiveSync document decoding, decryption, merging, attachments or editing.
- Connection and production user experience must be verified on a real instance.
- Do not enable editing until LiveSync conflict resolution is implemented.

## Español

Esta aplicación de Home Assistant es **independiente**. No utiliza ni necesita el MCP de Obsidian ni accede a sus archivos.

La versión **0.1.0-dev4** ofrece una vista previa Markdown local y una comprobación experimental de conexión con CouchDB de solo lectura. **No descifra ni edita las notas de LiveSync**.

### Configuración
- `vault_path`: carpeta Markdown local opcional dentro de `/share`.
- `couchdb_url`: URL raíz del servidor CouchDB (preferiblemente HTTPS; es obligatorio si se introducen credenciales).
- `couchdb_database`: nombre de la base de datos.
- `couchdb_username`, `couchdb_password`: credenciales CouchDB; introdúcelas **solo** en la configuración de la aplicación en HA.

El enlace **CouchDB status / Estado CouchDB** comprueba los metadatos de la base de datos sin descargar ni modificar documentos. Devuelve únicamente el estado de conexión y el número de documentos. Nunca publiques credenciales en GitHub.

### Limitaciones
- Sin descifrado, interpretación, fusión, adjuntos o edición de documentos LiveSync.
- Hay que verificar la conexión y la experiencia de usuario en una instalación real.
- No habilitaremos la edición hasta implementar la gestión de conflictos de LiveSync.
