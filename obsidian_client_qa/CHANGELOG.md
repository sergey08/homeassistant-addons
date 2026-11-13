# Changelog / Historial de cambios

## 0.1.0-dev93
- Correct the message after a successful remote read-only reload: editor is clean, not unsynchronized.
- Remote CouchDB writes remain disabled.

## 0.1.0-dev92
- Editor: reload encrypted remote Markdown directly through the proven read-only CouchDB endpoint, without depending on the failing CLI fetch.
- Preserve unsaved drafts unless replacement is explicitly accepted; no remote writes.

## 0.1.0-dev91
- Editor: asks before replacing a decrypted remote note with a different local copy; preserves the selected content and accurately reports the result.
- Remote CouchDB writes remain disabled.

## 0.1.0-dev90 (experimental / experimental)
- EN: Prefer specific, allowlisted fetch error details over the generic rebuilder origin.
- ES: Prioriza detalles específicos y seguros de errores fetch frente al origen genérico rebuilder.
- EN: Add regression coverage. Remote writes remain disabled; no real vault migration.
- ES: Añade prueba de regresión. Escrituras remotas desactivadas y sin migración de la bóveda real.

## 0.1.0-dev89 (experimental / experimental)
- EN: Improve safe CLI fetch diagnostics by classifying the first exception frame rather than the entire stack.
- ES: Mejora el diagnóstico seguro de errores de fetch: identifica el primer punto de excepción y no toda la pila.
- EN: Correct the remote-preview unit-test contract and verify official CLI, Docker build, Python tests and encrypted CouchDB roundtrip through GitHub Actions.
- ES: Corrige el contrato del test de vista previa remota y valida CLI oficial, imagen Docker, pruebas Python y recuperación cifrada en CouchDB aislado.
- EN: Remote writes remain disabled. No migration or write to the real vault.
- ES: Las escrituras remotas continúan desactivadas. Sin migración ni escritura en la bóveda real.

## 0.1.0-dev82 (experimental / experimental)
- EN: Explicit, read-only Markdown retrieval through an isolated LiveSync CLI fetch; an editor button loads the remote copy on demand.
- ES: Recuperación explícita de Markdown en solo lectura mediante una copia temporal aislada de LiveSync CLI; botón de carga manual en el editor.
- EN: The draft editor can open when direct E2EE read fails, but local saving is blocked until a remote copy has been loaded.
- ES: El editor puede abrirse si falla la lectura E2EE directa, pero bloquea el guardado local hasta cargar una copia remota.
- EN: Preview request bounds, safe error categories and new offline tests. Remote editing/synchronization remain disabled.
- ES: Límites de petición, categorías de errores seguras y nuevas pruebas locales. La edición y sincronización remota siguen desactivadas.
- EN/ES: Automated regression suite and real CouchDB end-to-end verification still pending / Pendientes las pruebas automatizadas y la validación real extremo a extremo con CouchDB.

## 0.1.0-dev26
- EN: Optional LiveSync encryption switch and private E2EE passphrase in add-on configuration. Decryption is **not yet implemented**.
- ES: Selector de cifrado LiveSync y frase E2EE privada en la configuración. El descifrado **aún no está implementado**.

## 0.1.0-dev24
- EN: Read-only diagnostic for encrypted LiveSync metadata paths.
- ES: Diagnóstico de solo lectura de rutas de metadatos cifrados.

## 0.1.0-dev20
- EN: Allow CouchDB HTTP authentication only for the explicitly configured internal Home Assistant add-on hostname and port 5984.
- ES: Se permite HTTP autenticado únicamente hacia el nombre y puerto 5984 internos del complemento autorizado de Home Assistant.

## Development status / Estado del desarrollo
- EN: The app can connect to CouchDB and inspect metadata, but cannot yet decode encrypted LiveSync documents or edit notes.
- ES: La aplicación puede conectarse a CouchDB y analizar metadatos, pero todavía no descifra documentos LiveSync cifrados ni edita notas.
