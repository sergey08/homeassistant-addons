# Moonraker MCP v0.1.0 — Release-review handoff / Guía para revisión de publicación

**Estado / Status:** revisión pendiente, **no aprobación de redistribución**. Documento de trabajo del candidato DEV12 de 2026-11-07. La aceptación funcional de AMD64/ARM64 no implica revisión legal o recuperación de credenciales.

## 1. Evidencia exacta de la imagen / Exact image evidence

Abrir [Moonraker MCP DEV2 CI](https://github.com/sergey08/homeassistant-addons/actions) y seleccionar el **workflow exitoso correspondiente al SHA definitivo que se pretenda publicar** (no uno anterior). En **Artifacts** descargar:

- `moonraker-mcp-dev12-cyclonedx-sbom`: `sbom.cdx.json`, `sbom-summary.json`, `license-human-review-worksheet.csv`, `license-review-pending.json`, `trivy-results.json`, `scan-summary.md`, `license-review-queue.csv`, `go-license-evidence.csv`, `third-party-legal-texts.zip`, `alpine-license-review.csv` y resúmenes cuando estén incluidos.
- `moonraker-mcp-dev-binary-inventory`: huellas SHA-256 de ambos ejecutables, `go version -m`, paquete/versiones Alpine y licencia declarada por paquete.

**Nuevo informe de conciliación:** `license-review-evidence-hints.json` une, mediante referencias concretas del SBOM, archivos legales Go y expresiones de licencias de Alpine. **Todas las entradas mantienen `PENDING`**, y el campo `reviewer_approved` sigue en `false`. Esta evidencia facilita la revisión humana, no la sustituye.

**Nota:** los artefactos tienen retención limitada (14 días). Descargarlos en un entorno privado de auditoría; no adjuntar claves, backups, `/data/tunnel` ni registros personales. Si cambia el Dockerfile, la versión Go o alguna dependencia, **regenerar el SBOM y repetir la revisión con el SHA final**.

## 2. Qué sabemos / What is established

En la ejecución [42399856467](https://github.com/sergey08/homeassistant-addons/actions/runs/42399856467), el control de vulnerabilidades informa **0 CRITICAL y 0 HIGH**. El SBOM contiene **129 componentes**, de los cuales **92 no tienen metadatos de licencia automáticos** (89 Go y 3 sin PURL). La herramienta de revisión generó **129 entradas PENDING**, deliberadamente. El archivo legal adjunto contiene **95 archivos** correspondientes a **85 módulos Go**. Son recuentos de esa ejecución, **no números garantizados para la imagen final**.

El binario del túnel distribuido **no es el ZIP oficial OpenAI v0.0.19**: se compila desde un commit upstream fijado de la versión 0.0.20 y utiliza una versión actualizada de `golang.org/x/net`. La prueba del ZIP v0.0.19 es solo regresión de migración.

**Priorización de licencias:** consultar [LICENSE_REVIEW_PRIORITIES_EN_ES.md](./LICENSE_REVIEW_PRIORITIES_EN_ES.md) para los 16 paquetes Alpine de revisión copyleft/recíproca, 9 con expresiones especiales y 12 candidatas permisivas. Son datos del run 42401009003, no aprobación legal.

## 3. Revisión humana necesaria / Required human review

Para cada `bom-ref` del SBOM final:

1. Confirmar nombre, versión y procedencia de la dependencia, incluidas entradas sin PURL y el runtime Go.
2. Examinar archivos LICENSE/COPYING/NOTICE/COPYRIGHT/AUTHORS de la versión exacta y comprobar el alcance de los permisos y condiciones. La presencia de un archivo legal **no basta** para determinar la licencia aplicable.
3. Documentar la obligación de reproducción del texto de licencia, avisos, copyright, atribución, ofertas de fuente o disponibilidad de código fuente si corresponde. Prestar especial atención a paquetes Alpine con GPL/LGPL/MPL o licencias combinadas, sin asumir que toda GPL obliga igual a todo el contenedor.
4. Verificar dónde se cumplen esas obligaciones en la imagen descargable y, cuando proceda, en la documentación o paquete de distribución.
5. Rellenar para cada componente `status: REVIEWED`, `license_evidence`, `notice_obligations` y `reviewer`, **solo después de revisar el componente**. Conservar el vínculo con el hash canónico del mismo SBOM. No editar el manifiesto `license-review-pending.json` para simular aprobaciones.
6. Ejecutar `python3 moonraker_mcp/license_release_gate.py <sbom.cdx.json> <manifest-reviewed.json>` y verificar que termina correctamente. Esta comprobación cubre documentación y trazabilidad; **no sustituye la aprobación legal humana**.

**Bloqueo por diseño:** sin manifiesto completo vinculado al SBOM exacto, el gate de licencias debe fallar. No omitirlo para publicar estable.

## 4. Aceptación funcional y seguridad / Functional and security acceptance

- AMD64 (Lenovo): DEV12 actualizado desde DEV11, cinco herramientas read-only consultadas desde ChatGPT; puerto 8765 no publicado, túnel privado y perfiles opcionales desactivados.
- ARM64: mantenedor confirma aceptación funcional del usuario externo; no hay en el repositorio una transcripción técnica externa con las cinco herramientas y pruebas de seguridad independientes.
- Pendiente: demostrar rotación/revocación del token de OpenAI y recuperación cifrada en un **Home Assistant desechable**; nunca usar ni compartir credenciales del Lenovo.
- Pendiente: comprobar visualmente que la ayuda localizada para `mcp_http_token` aparece en Home Assistant.
- Repetir control final de opciones `enable_*`, puertos, red y comportamiento de impresora desconectada antes del release.

**Acta para la prueba real de restauración:** [RECOVERY_ACCEPTANCE_RECORD_EN_ES.md](./RECOVERY_ACCEPTANCE_RECORD_EN_ES.md). Tiene nueve controles pendientes R1–R9 y campos de firma; no contiene credenciales y **no supone que el ensayo se haya ejecutado**.

## 5. Decisión de publicación / Release decision

**NO PUBLICAR COMO ESTABLE** hasta que la revisión humana de licencias y la prueba/aceptación de recuperación de credenciales estén documentadas, la CI del SHA definitivo sea verde y exista autorización explícita del mantenedor para fusionar `main`, crear el tag/release `v0.1.0` y elegir distribución.

El código DEV puede seguir disponible para ensayos controlados en `dev/moonraker-mcp-dev2`. Una aprobación de compatibilidad ARM64 no desbloquea las licencias, ni la seguridad de restauración.
