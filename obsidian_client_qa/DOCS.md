# Obsidian Client — Developer preview / Vista previa de desarrollo

## English

This is an **independent** Home Assistant application. It does not use, require or read Obsidian MCP files.

Version **0.1.0-dev8** has a local Markdown preview and experimental read-only CouchDB connectivity and a bounded document-type inspection (maximum 20 records). It **does not** decode or edit LiveSync notes.

### Configuration
- `vault_path`: optional local Markdown directory inside `/share`.
- `couchdb_url`: CouchDB server root URL (prefer HTTPS; HTTPS is required when credentials are supplied).
- `couchdb_database`: database name.
- `couchdb_username`, `couchdb_password`: CouchDB credentials; set **only** in Home Assistant app settings.

For security, the client rejects redirects on credentialed CouchDB requests, and the configured CouchDB URL must point to the server root. The **CouchDB status / Estado CouchDB** link checks database metadata, without fetching or modifying documents. It returns only connection status and the document count. Credentials never belong in GitHub.

The `/api/notes` endpoint lists filenames from an optional local Markdown folder. `/api/remote/inspect` returns only aggregate document types, not document bodies. Neither endpoint decodes LiveSync notes.

### Limitations
- No LiveSync document decoding, decryption, merging, attachments or editing.
- Connection and production user experience must be verified on a real instance.
- Do not enable editing until LiveSync conflict resolution is implemented.

## Español

Esta aplicación de Home Assistant es **independiente**. No utiliza ni necesita el MCP de Obsidian ni accede a sus archivos.

La versión **0.1.0-dev8** ofrece una vista previa Markdown local y comprobación experimental de conexión CouchDB e inspección limitada de tipos de documentos (máximo 20 registros). **No descifra ni edita las notas de LiveSync**.

### Configuración
- `vault_path`: carpeta Markdown local opcional dentro de `/share`.
- `couchdb_url`: URL raíz del servidor CouchDB (preferiblemente HTTPS; es obligatorio si se introducen credenciales).
- `couchdb_database`: nombre de la base de datos.
- `couchdb_username`, `couchdb_password`: credenciales CouchDB; introdúcelas **solo** en la configuración de la aplicación en HA.

Por seguridad, el cliente bloquea las redirecciones en solicitudes con credenciales y exige que la URL configurada sea la raíz del servidor. El enlace **CouchDB status / Estado CouchDB** comprueba los metadatos de la base de datos sin descargar ni modificar documentos. Devuelve únicamente el estado de conexión y el número de documentos. Nunca publiques credenciales en GitHub.

El endpoint `/api/notes` enumera nombres de archivos Markdown locales opcionales. `/api/remote/inspect` devuelve únicamente recuentos de tipos de documentos, sin incluir el contenido. Ninguno interpreta las notas LiveSync.

### Limitaciones
- Sin descifrado, interpretación, fusión, adjuntos o edición de documentos LiveSync.
- Hay que verificar la conexión y la experiencia de usuario en una instalación real.
- No habilitaremos la edición hasta implementar la gestión de conflictos de LiveSync.


## Plan de desarrollo dev48 — edición Markdown (no implementado aún)

La versión dev47 es de solo lectura. La rama dev48 prepara la creación y edición de notas sin modificar todavía la bóveda real.

### Requisitos funcionales
- Crear una nota `.md` en una carpeta seleccionada, con nombre validado.
- Editar notas existentes con editor de texto y vista previa Markdown.
- Advertir sobre cambios sin guardar; refrescar el árbol tras guardar.
- Mantener carpetas contraídas por defecto (funcionalidad existente; no duplicar).

### Seguridad e integridad
- La fuente de verdad actual es CouchDB/Obsidian LiveSync, no el directorio local opcional.
- No escribir documentos CouchDB directamente hasta disponer de un codificador LiveSync compatible, incluyendo fragmentos, metadatos, cifrado E2EE y gestión de revisiones/conflictos.
- El montaje `share:ro` de dev47 debe mantenerse mientras no exista un flujo de escritura local seguro y explícito.
- No registrar credenciales, frases E2EE ni contenido de notas en logs.
- Proteger escrituras contra CSRF, rutas fuera de la bóveda, sobrescritura accidental y conflictos concurrentes.
- Ante conflicto de revisión, rechazar guardado y ofrecer recuperar la versión más reciente.

### Criterios de aceptación
1. Leer una nota real, editarla y verla sincronizada en Obsidian sin pérdida de contenido.
2. Crear una nota en una subcarpeta y comprobarla desde otro dispositivo.
3. Rechazar escrituras con revisión obsoleta, rutas inválidas o permisos insuficientes.
4. Comprobar el flujo con y sin E2EE; si una modalidad no está soportada, mantenerla en solo lectura.
5. Conservar el funcionamiento de dev47 hasta superar estas pruebas.


## Contrato de escritura LiveSync — referencia upstream (2026-10)

Referencia técnica: https://github.com/vrtmrz/obsidian-livesync/blob/main/docs/datastructure.md

La documentación upstream declara expresamente que el formato de documentos CouchDB
**no es una API estable para construir registros manualmente**. El contrato ejecutable
reside en la versión exacta de `@vrtmrz/livesync-commonlib` fijada por el proyecto.

Consecuencias para este cliente:

1. El cifrador HKDF Python implementado hasta ahora sirve para comprobar el
   cifrado de cadenas, **no demuestra compatibilidad de escritura LiveSync**.
2. La escritura requiere el servicio de rutas/IDs, hash de chunks, fragmentación,
   compresión, E2EE y codificación remota de la versión correspondiente de Commonlib.
3. Los chunks deben persistirse antes que los metadatos que los referencian;
   las operaciones no son atómicas y hay que gestionar fallos parciales.
4. `ctime` y `mtime` se expresan en milisegundos Unix y `size` es el tamaño
   en bytes del contenido descodificado, no la longitud de caracteres.
5. Los IDs de chunks son derivados del contenido, con variantes como `h:+`
   para ciertos modos cifrados. No generar IDs aleatorios como sustituto.
6. Las revisiones y los borrados lógicos deben respetar las convenciones del
   protocolo, sin sobreescribir revisiones obsoletas.

**Bloqueo de publicación de escritura:** no activar el botón Guardar ni llamar
a `put_revision_checked` desde rutas HTTP hasta integrar Commonlib (o validar
formalmente un codificador contra el mismo paquete/version y una bóveda aislada).
Las pruebas sintéticas de CouchDB verifican condiciones HTTP, no compatibilidad
con Obsidian móvil. Mantener dev47 operativa durante esta integración.
