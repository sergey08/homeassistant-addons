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
