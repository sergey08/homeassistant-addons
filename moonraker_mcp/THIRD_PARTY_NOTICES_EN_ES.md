# Moonraker MCP v0.1.0 — Avisos de terceros / Third-party notices

**Estado: guía para revisión final de redistribución. No constituye aprobación jurídica ni un sustituto de licencias completas.**

## Binarios incluidos

| Componente | Procedencia fijada | Licencia upstream indicada | Evidencia incorporada a la imagen |
| --- | --- | --- | --- |
| mcp-raker | [lexfrei/mcp-raker, commit f01636be](https://github.com/lexfrei/mcp-raker/tree/f01636bec21a21cfc5f9ee84dc68dad7d44d6dd9) | BSD-3-Clause | `/usr/share/doc/moonraker-mcp/licenses/mcp-raker-BSD-3-Clause.txt` |
| tunnel-client | [openai/tunnel-client, commit c2144b09](https://github.com/openai/tunnel-client/tree/c2144b0904980bcbae2636cdca4f4167e9818e0b) | Apache-2.0 | `tunnel-client-Apache-2.0.txt` y `tunnel-client-NOTICE.txt` |
| Go toolchain | imagen Go fijada por digest en Dockerfile | BSD-3-Clause (material Go) | `go-toolchain-BSD-3-Clause.txt` |

Los dos binarios Go **se compilan desde los commits fijados**, con la dependencia `golang.org/x/net v0.62.0` actualizada. No son ZIP upstream inalterados. Las diferencias `go.mod`/`go.sum` y las referencias a commits se copian dentro de la imagen en `/usr/share/doc/moonraker-mcp/provenance/`.

## Imagen base y librerías Alpine

La imagen de ejecución utiliza Alpine 3.22 y contiene paquetes con licencias de varios tipos. El catálogo y versiones exactas se obtienen del inventario del candidato CI: [run 42419665124](https://github.com/sergey08/homeassistant-addons/actions/runs/42419665124) (`moonraker-mcp-dev12-cyclonedx-sbom`, `moonraker-mcp-dev-binary-inventory`). Las diez familias prioritarias GPL/LGPL/MPL y sus fuentes se describen en [ALPINE_SOURCE_AUDIT_EN_ES.md](./ALPINE_SOURCE_AUDIT_EN_ES.md).

Las recetas verificadas se pueden reproducir desde [aports 2235ae24](https://github.com/alpinelinux/aports/tree/2235ae248c31ea48a9df764becdfecc2a85b4f31). La comparación SHA-512 de fuentes (164/166 en el último inventario completo) es evidencia de integridad, **no** de cumplimiento de obligaciones de redistribución. Si se proporciona la imagen binaria a terceros, debe identificarse el mecanismo adecuado para ofrecer el código fuente correspondiente a cada componente sujeto a esa obligación, incluyendo parches y scripts pertinentes.

**Comprobación final mínima, todavía pendiente:** determinar y documentar el cumplimiento de avisos y obligaciones GPL/LGPL/MPL de la imagen efectivamente publicada. En particular, aclarar ubicación de los textos legales Alpine y el acceso a fuentes correspondientes para receptores. Los cuatro textos upstream ya incluidos no cubren automáticamente todos los componentes de la imagen.

## Usuarios / Users

- La instalación de usuario solo requiere configurar Home Assistant y Moonraker; **no** descargan manualmente estos archivos legales ni crean scripts de auditoría.
- El túnel de OpenAI es opcional y requiere las credenciales del propio usuario, introducidas mediante los campos protegidos de Home Assistant; no se facilitan ni reutilizan credenciales de los mantenedores.
- No instalar en paralelo DEV y estable con el mismo `tunnel_id`. La migración de Supervisor entre identidades distintas no está garantizada.

## Decisión de lanzamiento

**Pendiente**: revisión concreta de cumplimiento de redistribución, CI final del commit que se publique y autorización expresa del mantenedor para merge, tag y GitHub Release. Las pruebas de restauración cifrada y revocación real del token están **NO VERIFICADAS**, nunca se declaran PASS.

EN: The package includes the above upstream notices and pinned source-build provenance. The remaining Alpine redistribution obligations require release review; this file is informational, **not a legal clearance statement**.
