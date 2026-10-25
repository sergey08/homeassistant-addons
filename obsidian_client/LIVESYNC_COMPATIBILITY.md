# LiveSync compatibility / Compatibilidad LiveSync

## English

**Current status:** read-only diagnostics only. The independent Obsidian Client does not use Obsidian MCP, and does not yet decode, decrypt, synchronise or write LiveSync notes.

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

**Estado actual:** únicamente diagnósticos de solo lectura. Obsidian Client es independiente del MCP de Obsidian y todavía no interpreta, descifra, sincroniza ni escribe notas LiveSync.

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

English: `livesync_plain.py` is a deliberately narrow decoder for **synthetic fixtures only**. The 7 isolated unit tests pass locally, but **this is not a verified implementation of upstream LiveSync**, and the module is not wired to the Home Assistant app or any real CouchDB database. Compression, encryption, metadata variants and version-specific chunk formats remain unsupported.

Español: `livesync_plain.py` es un decodificador limitado para **datos ficticios de prueba**. Las 7 pruebas aisladas pasan localmente, pero **no se ha validado su compatibilidad con LiveSync real** y el módulo no está conectado a la aplicación ni a una base CouchDB real. No admite todavía compresión, cifrado, variantes de metadatos ni formatos de fragmentos propios de cada versión.
