# LiveSync compatibility / Compatibilidad LiveSync

## English

**Current status (0.1.0-dev13):** read-only diagnostics and a working **synthetic local decoder demo** (`/api/demo`). The independent Obsidian Client does not use Obsidian MCP. It still does not retrieve or decode notes from a real LiveSync database.

| Feature | Current support |
| --- | --- |
| CouchDB connection and document type counts | Read-only diagnostics |
| Local Markdown file listing and preview | Read-only |
| Remote plain-text notes and chunk reassembly | Offline synthetic prototype only; remote integration not implemented |
| E2EE V1/V2, obfuscated paths and encrypted metadata | Not implemented |
| Attachments, editing, deletion and conflict resolution | Disabled |

Self-hosted LiveSync can represent a single note with metadata and multiple chunks; a CouchDB document is not always a complete note. Current upstream configurations can also encrypt content and internal metadata. Never treat encrypted or compressed payloads as plaintext. A proposed external CouchDB API specification is under review; do not enable writes without version-matched fixtures and conflict tests.

Source / Fuente:
- https://github.com/vrtmrz/obsidian-livesync/blob/main/docs/settings.md
- https://github.com/vrtmrz/obsidian-livesync/pull/1001

## Español

**Estado actual (0.1.0-dev13):** diagnóstico de solo lectura y **demostración local de decodificación ficticia** (`/api/demo`). Obsidian Client es independiente del MCP de Obsidian. Todavía no recupera ni interpreta notas de una base LiveSync real.

| Función | Compatibilidad actual |
| --- | --- |
| Conexión CouchDB y recuentos de tipos de documentos | Diagnóstico de solo lectura |
| Listado y vista previa de Markdown local | Solo lectura |
| Notas remotas de texto y reconstrucción de fragmentos | Prototipo aislado con datos ficticios; conexión remota no implementada |
| E2EE V1/V2, rutas ofuscadas y metadatos cifrados | No implementado |
| Adjuntos, edición, borrado y resolución de conflictos | Deshabilitados |

Self-hosted LiveSync puede almacenar una misma nota mediante metadatos y varios fragmentos; un documento CouchDB no siempre equivale a una nota completa. Las configuraciones actuales también pueden cifrar el contenido y los metadatos internos. No se deben interpretar datos cifrados o comprimidos como texto. Existe una propuesta de especificación para clientes externos pendiente de revisión; no habilitaremos escrituras sin pruebas de compatibilidad y de conflictos.

Fuentes: enlaces anteriores.

## Offline prototype / Prototipo aislado

English: `livesync_plain.py` is a deliberately narrow decoder for **synthetic fixtures only**. GitHub Actions verifies the synthetic unit tests and a disposable real CouchDB round-trip. The module is bundled in the Home Assistant app for `/api/demo`, but **this does not demonstrate upstream LiveSync compatibility** and no production database is accessed. Compression, encryption, metadata variants and version-specific chunk formats remain unsupported.

Español: `livesync_plain.py` es un decodificador limitado para **datos ficticios de prueba**. GitHub Actions verifica las pruebas ficticias y una prueba de lectura/escritura sobre un CouchDB real desechable. El módulo ya está incluido en la aplicación mediante `/api/demo`, pero **esto no demuestra compatibilidad con LiveSync real** y no se accede a ninguna base de producción. No admite todavía compresión, cifrado, variantes de metadatos ni formatos de fragmentos propios de cada versión.

## Acceptance gate / Criterio de aceptación

English: Before enabling remote note reading, create an **independent empty Obsidian vault**, configure its Self-hosted LiveSync plug-in to use a **separate test CouchDB database**, create one plaintext and one chunked Markdown note, and compare original note bytes with the reconstructed result. Validate deleted documents, encrypted and compressed configurations, missing chunks and revisions. Keep remote editing disabled until separate conflict-resolution tests pass. **Never reuse a production vault, database or account for these tests.**

Español: Antes de habilitar la lectura remota, crear una **bóveda nueva y vacía de Obsidian**, configurar Self-hosted LiveSync contra una **base CouchDB de pruebas distinta**, crear una nota Markdown simple y otra dividida en fragmentos y comparar los bytes originales con el resultado reconstruido. Comprobar borrados, cifrado, compresión, fragmentos ausentes y revisiones. Mantener la edición remota deshabilitada hasta superar pruebas específicas de conflictos. **No reutilizar la bóveda, base de datos ni cuenta de producción para estos ensayos.**
