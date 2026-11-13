# Real LiveSync test / Prueba de LiveSync real

## English

**Goal:** verify one document genuinely written by Self-hosted LiveSync, independently of Obsidian MCP and without accessing a production Vault.

1. In Obsidian, create an **empty separate Vault**, e.g. `Obsidian-Client-Test`. Install **Self-hosted LiveSync** only in this test Vault.
2. Create a **different test CouchDB database and test-only user** on an isolated server. Never use your personal database or credentials. Do not paste any password into GitHub issues or commits.
3. Configure the test Vault to synchronise with the disposable database. Start with encryption, obfuscated paths and compression **disabled**, if supported. Check the effective settings rather than assuming defaults.
4. Create `Demo/Hello.md` containing exactly `Hello world` (no trailing newline), and a second longer note to test chunking. Wait until sync completes.
5. From the test database only, extract the **single** `f:` parent record and **its referenced** `h:` chunks. Remove the `_rev` values, credentials and any unrelated documents. Save the clean sample privately. Do not upload it to this public repository until reviewed.
6. Check document metadata: `type`, `datatype`, `path`, `children`, `eden`, `size` and referenced chunk structure. Record LiveSync plug-in version, compression and encryption settings.
7. Wrap the sanitised records in a local JSON file with `parent`, `chunks`, and `expected`, then run `python verify_fixture.py test-fixture.json`. A passing check validates **only that specific sample and configuration**.
8. Repeat with encrypted and compressed test configurations. These are expected to be rejected until format-specific support is implemented.

**Safety:** test fixtures may contain plaintext note content. Never share personal notes, OAuth tokens, CouchDB credentials, Setup URIs or production database exports. Do not enable remote writes or editing.

Sources: [LiveSync configuration](https://github.com/vrtmrz/obsidian-livesync/blob/main/docs/settings.md), [technical architecture](https://github.com/vrtmrz/obsidian-livesync/blob/main/docs/tech_info.md).

## Español

**Objetivo:** verificar un documento generado por Self-hosted LiveSync, sin depender del MCP de Obsidian y sin acceder a tu bóveda habitual.

1. Crea en Obsidian una **bóveda nueva y vacía**, por ejemplo `Obsidian-Client-Test`. Instala **Self-hosted LiveSync** únicamente en ella.
2. Prepara una **base CouchDB de pruebas distinta y un usuario exclusivo** en un servidor aislado. No reutilices la base ni las credenciales personales.
3. Configura esa bóveda contra la base desechable. Empieza, si la versión lo permite, **sin cifrado, sin ofuscación y sin compresión**. Verifica la configuración efectiva.
4. Crea `Demo/Hello.md` con el contenido exacto `Hello world` (sin salto de línea final) y otra nota más larga para provocar fragmentación. Espera al final de la sincronización.
5. Extrae **solo de la base de pruebas** el documento padre `f:` y los fragmentos `h:` que este referencie. Elimina revisiones `_rev`, credenciales y cualquier otro documento. Mantén la muestra privada hasta revisarla.
6. Revisa `type`, `datatype`, `path`, `children`, `eden`, `size` y los fragmentos. Anota versión del complemento y ajustes de cifrado y compresión.
7. Guarda los datos depurados en un JSON local con `parent`, `chunks` y `expected`, y ejecuta `python verify_fixture.py test-fixture.json`. Superar esta prueba verifica **solo esa muestra y esa configuración**.
8. Repite con las opciones de cifrado y compresión habilitadas: por ahora el lector debe rechazarlas.

**Seguridad:** no compartas notas privadas, tokens, contraseñas, enlaces Setup URI ni exportaciones de tu base de producción. La edición remota seguirá deshabilitada.


## Upstream automated test runner / Pruebas automáticas oficiales

**English:** The upstream LiveSync repository maintains a real-Obsidian E2E runner at [test/e2e-obsidian](https://github.com/vrtmrz/obsidian-livesync/tree/main/test/e2e-obsidian). It creates disposable vaults and isolated Obsidian profiles and can drive CouchDB scenarios using Obsidian itself. That is the preferred source for genuine, version-matched fixtures. The public `test/fixtures` directory does **not** currently provide a ready-to-use CouchDB note fixture, so the current decoder's synthetic tests are not proof of production compatibility.

**Español:** El repositorio oficial de LiveSync dispone de un ejecutor E2E con Obsidian real en [test/e2e-obsidian](https://github.com/vrtmrz/obsidian-livesync/tree/main/test/e2e-obsidian). Crea bóvedas y perfiles de Obsidian temporales y permite probar flujos con CouchDB mediante Obsidian. Es la opción preferida para obtener muestras auténticas correspondientes a cada versión. La carpeta pública `test/fixtures` **no** contiene actualmente una muestra CouchDB de nota lista para reutilizar; por tanto, las pruebas ficticias todavía no demuestran compatibilidad en producción.


## Concrete upstream producer / Productor oficial concreto

**English:** The upstream file [`test/e2e-obsidian/scripts/couchdb-upload.ts`](https://github.com/vrtmrz/obsidian-livesync/blob/main/test/e2e-obsidian/scripts/couchdb-upload.ts) already creates `E2E/couchdb-upload.md` through **real Obsidian**, uploads it with **Self-hosted LiveSync**, checks that the CouchDB record and *every referenced chunk* exist, and deletes its temporary database during cleanup. This is our canonical source for a genuine compatibility fixture. The next missing operation is to capture only that generated parent and its children **before upstream cleanup**, sanitize them, and verify the reconstructed bytes. This repository currently does **not** automate that capture, and no production compatibility is claimed.

**Español:** El archivo oficial [`test/e2e-obsidian/scripts/couchdb-upload.ts`](https://github.com/vrtmrz/obsidian-livesync/blob/main/test/e2e-obsidian/scripts/couchdb-upload.ts) ya crea `E2E/couchdb-upload.md` desde **Obsidian real**, lo sincroniza mediante **Self-hosted LiveSync**, verifica que CouchDB contiene el documento padre y *todos sus fragmentos*, y elimina la base temporal al finalizar. Es la fuente de referencia para una muestra auténtica. Falta capturar únicamente ese documento y sus fragmentos **antes de la limpieza**, depurarlos y comparar los bytes reconstruidos. Nuestro repositorio aún **no** automatiza esa captura ni afirma compatibilidad con bases de producción.


## Offline extraction / Extracción sin conexión

**English:** A new `extract_test_fixture.py` tool takes an offline `_all_docs?include_docs=true` JSON export from the **disposable test database**, the exact note path, and a plaintext file with the expected original note contents. It writes a minimal JSON fixture containing only the requested parent, referenced chunks, and expected bytes (UTF-8 text). It rejects incomplete references and mismatches. It **does not contact CouchDB**, and the resulting fixture must be reviewed before publishing.

```bash
cd obsidian_client
python extract_test_fixture.py isolated-export.json Demo/Hello.md original-note.txt isolated-fixture.json
python verify_fixture.py isolated-fixture.json
```

**Español:** La nueva herramienta `extract_test_fixture.py` procesa una exportación JSON `_all_docs?include_docs=true` de la **base temporal de pruebas**, la ruta exacta y un archivo con el texto original de la nota. Genera un JSON mínimo solo con el documento padre, sus fragmentos y el texto esperado. Rechaza referencias incompletas y contenido distinto. **No conecta con CouchDB**. Revisa siempre el resultado antes de publicarlo. Los comandos de arriba sirven también para español.
