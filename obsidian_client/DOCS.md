# Obsidian Client — Developer preview / Vista previa de desarrollo

## English

### Description
Experimental, read-only Markdown browser integrated into the Home Assistant sidebar via Ingress.

### Requirements and configuration
- Home Assistant OS or Supervised.
- A local folder containing Markdown files, for example `/share/obsidian-client/vault`.
- Set `vault_path` to a path inside `/share`.

### Current limitations
- Read-only; does not edit or sync notes.
- Does not connect to or decrypt CouchDB/LiveSync.
- Wiki links, attachments and embedded media are not yet supported.
- Building and installing the app in Home Assistant has not yet been verified.

Never commit credentials, encryption passwords or personal notes.

## Español

### Descripción
Explorador experimental de Markdown en modo solo lectura, integrado en la barra lateral de Home Assistant mediante Ingress.

### Requisitos y configuración
- Home Assistant OS o Supervised.
- Una carpeta local con archivos Markdown, por ejemplo `/share/obsidian-client/vault`.
- Configura `vault_path` con una ruta dentro de `/share`.

### Limitaciones actuales
- Solo lectura; no edita ni sincroniza notas.
- No conecta ni descifra CouchDB/LiveSync.
- Los enlaces wiki, adjuntos y archivos multimedia incrustados todavía no están disponibles.
- Aún no se ha verificado la compilación e instalación en Home Assistant.

Nunca publiques credenciales, contraseñas de cifrado ni notas personales.
