# Release readiness and supply-chain audit / Preparación y cadena de suministro

**Date / Fecha: 2026-11-05 · DEV10.** Evidence collected against the pinned code and the development Docker build, not a formal third-party security certification.

## 2026-11-05 — Embedded dependency inventory, CI and secret handling

**EN:** GitHub Actions now extracts the exact `mcp-raker` and `tunnel-client` binaries from the built add-on image, records their SHA-256 hashes and embedded Go build-module metadata (`go version -m`), and inventories installed Alpine packages (`apk info -vv`). The workflow publishes a short-retention artifact containing **text metadata only, not the executables or secrets**. The initial inventory run was green and produced an artifact; the final optimized upload is separately CI-checked. This is an **inventory**, not a CycloneDX/SPDX SBOM, not license clearance, and not a vulnerability scan.

**ES:** La CI obtiene ahora de la imagen realmente construida las huellas SHA-256 y el inventario de módulos Go incorporados de ambos ejecutables, además de la lista de paquetes Alpine instalados. El artefacto conserva solo metadatos de texto, sin binarios ni contraseñas. Esto facilita la auditoría, pero **todavía no acredita todas las licencias, vulnerabilidades ni la procedencia de compilación**.

The operating guide [Secret rotation and backup safety / Rotación de claves y copias](./SECRET_ROTATION_BACKUPS_EN_ES.md) covers provider-side revocation, Home Assistant encrypted backups and the fact that clearing the tunnel key option does not delete an already provisioned legacy key. **Actual rotation and backup restore on a disposable second HA installation remain untested.**


## 2026-11-06 — CycloneDX inventory gate for DEV11 / Inventario CycloneDX

**EN:** The DEV11 CI workflow has been extended to generate a machine-readable CycloneDX SBOM from the **actual built Docker image**, not only from declared upstream `go.mod` entries. It checks the format and unique component references, counts component types and available license metadata, and retains the JSON plus Trivy vulnerability/license evidence as a short-lived CI artifact. The final CI execution and exact inventory totals must be checked before treating this gate as validated. CycloneDX is an inventory standard, **not a guarantee of complete dependency discovery, license compliance, or no vulnerabilities**. A maintainer must review entries with missing or ambiguous license information, including compiled Go modules and Alpine packages, before distribution.

**ES:** Añadida generación de SBOM CycloneDX a partir de la imagen DEV11 realmente compilada. Se comprueba el formato, las referencias únicas y la cantidad de componentes que incluyen metadatos de licencia. Se conserva un artefacto temporal con el SBOM y los resultados Trivy. **No equivale a declarar revisadas todas las licencias:** habrá que examinar las dependencias sin licencia identificada, las obligaciones de aviso/código fuente y los paquetes Alpine. La prueba de instalación limpia en otro Home Assistant continúa pendiente.

## 2026-11-06 — Validated DEV11 CycloneDX SBOM / Resultado verificado

**EN:** The CycloneDX 1.6 report generated from the full built DEV11 image passed CI in [GitHub Actions run 42219231227](https://github.com/sergey08/homeassistant-addons/actions/runs/42219231227). It recorded **129 components**: 126 libraries, 2 applications and 1 operating-system component. **37 of the 129** have license metadata in this automatically generated inventory; 92 do not. Lack of detected license metadata **does not mean unlicensed software** and must not be interpreted as a legal breach. The CI archived `moonraker-mcp-dev11-cyclonedx-sbom` and the binary inventory for 14 days, with no runtime credentials or executable contents added to the SBOM artifact. Next: reconcile missing license metadata against upstream module/package license notices, verify any copyleft obligations and check that actual binary dependencies are covered. This SBOM is a useful baseline, not a complete provenance or licensing clearance.

**ES:** El SBOM **CycloneDX 1.6** de DEV11 se ha generado y validado mediante GitHub Actions: **129 componentes detectados** (126 bibliotecas, 2 aplicaciones, 1 componente de sistema operativo). **37** incluyen metadatos de licencia y **92** no los incluyen en este informe automatizado. **No significa que 92 componentes no tengan licencia**: falta identificar la licencia correspondiente y verificar las obligaciones de redistribución. Se conservó el informe durante 14 días; quedan pendientes la conciliación de dependencias y avisos, instalación realmente limpia en otra instancia HA y autorización expresa antes de publicar.

## English

### Binary provenance

| Component | Installed source | Verification | Remaining limitation |
| --- | --- | --- | --- |
| `mcp-raker` | Image pinned to `ghcr.io/lexfrei/mcp-raker@sha256:cdfbb9b4ead2b3f8a253eb55c1996a69cfdbc17088cc111b7d265d8b71f7090e` | Immutable manifest digest; container labels previously compared with source revision `0caea7c31a0780462331e9031e3bf0f435d190ed` | Labels are not an independent signed build attestation or reproducible-build guarantee |
| OpenAI `tunnel-client` | Official release `v0.0.19`, linux-amd64 ZIP | Hardcoded SHA-256 `9ee9448592345a9dd1517fb79791ab54d24f051142eb92bcbe8cd355effc9142`; checked during Docker build and CI | Build provenance beyond release checksum and independent signature still needs review |
| Alpine runtime | `alpine:3.22` | Fixed minor version and packages from Alpine repositories | Base image tag is mutable; production candidate should pin image digest and check vulnerability scanning |

### Licenses and transitive dependencies

- The pinned `mcp-raker` source revision declares **18 Go module dependencies** in `go.mod`, including direct and indirect entries. Its project license is **BSD-3-Clause**.
- OpenAI `tunnel-client` `v0.0.19` declares **71 Go module dependencies** in `go.mod`, direct and indirect. The project uses **Apache-2.0** and has a `NOTICE` file.
- The Docker image contains the complete upstream BSD-3-Clause license and OpenAI Apache-2.0 license and `NOTICE`; GitHub Actions checks presence.
- **Not yet completed:** review licenses and notices for every dependency actually linked into each published executable (the lists above are module declarations, **not** an SBOM or proof of complete attribution). Also verify required notices for Alpine packages.

### Installer and credential assurance

GitHub Actions validates Home Assistant safe defaults, builds the full image, starts the image without a real printer, and tests fail-closed behavior. An added **offline Docker first-run test** supplies only Home Assistant-like options and a synthetic restricted key, then verifies that the image automatically creates private `tunnel-client` and `api-key` assets with UID 65534 and modes 0700/0600, without printing the secret. The network is disabled and a fake tunnel ID is used, so failure to reach OpenAI is expected.

**This test is not an independent end-user Home Assistant installation.** A separate HA OS/Supervisor instance, a fresh OpenAI tunnel/key and a real ChatGPT custom-server registration must still be tested before stable publication. Do not conduct this against the already working DEV10 installation as a substitute for clean onboarding.

### Remaining stable release gates

- [x] Real ChatGPT → private tunnel → printer read-only tools, including power-off/reconnect.
- [x] Default field sanitization for printer info, server info and short temperature history.
- [x] Full image CI with pinned OpenAI ZIP digest and bundled primary notices.
- [x] Simulated options-only first run without manual copying of files (Docker CI).
- [ ] Clean second Home Assistant installation using only app UI, with separate restricted key.
- [ ] Generate and review a complete SBOM and third-party license/notice attribution for linked dependencies.
- [ ] Pin Alpine base by digest and establish repeatable security/vulnerability updates.
- [ ] Review secret rotation across Home Assistant options, private file, backups and tunnel controls.
- [ ] Approve final license/privacy policy and authorize stable publication explicitly.

## Español

El código está disponible en la rama `dev/moonraker-mcp-dev2` y la instalación real DEV10 continúa privada. Hemos identificado dos binarios de terceros: `mcp-raker`, fijado por digest OCI, y el cliente oficial del túnel OpenAI v0.0.19, cuyo ZIP se comprueba por SHA-256. Las licencias principales BSD-3-Clause y Apache-2.0, incluido el aviso `NOTICE`, están dentro de la imagen.

La revisión del archivo `go.mod` de cada revisión concreta muestra **18 módulos declarados** para `mcp-raker` y **71 para el cliente OpenAI**, directos e indirectos. Esta cifra **no equivale** a una lista exacta de dependencias enlazadas ni a un análisis completo de licencias. Es necesario generar un SBOM y revisar las atribuciones antes de publicar.

Se ha añadido una prueba Docker con red deshabilitada, credenciales ficticias y únicamente las opciones que configuraría el usuario en Home Assistant. Comprueba la creación automática del ejecutable y la clave protegida, así como la ausencia de filtraciones del secreto en los registros. **No sustituye una instalación real en un segundo Home Assistant.**

**No fusionar con `main` ni publicar estable sin superar esos pasos y recibir autorización explícita.**
