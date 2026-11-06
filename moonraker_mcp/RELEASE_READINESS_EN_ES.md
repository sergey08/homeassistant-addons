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

## 2026-11-06 — Missing-license metadata reconciliation queue / Cola de revisión

**EN:** A new deterministic helper, `sbom_license_queue.py`, reads the generated CycloneDX SBOM and writes `license-review-queue.csv` and `license-review-summary.json`. Each row records the component name, exact version, PURL, SBOM reference, ecosystem and review status **PENDING**. The helper categorizes `pkg:golang`, `pkg:apk` and other PURL types without inventing a license. Malformed and duplicate component references fail tests instead of silently disappearing. The CI attaches both documents alongside the SBOM. A count of missing fields is **not** a license infringement finding; each entry must be checked against authoritative upstream license files and required notices. No automated redistribution clearance is granted by the helper.

**ES:** Se ha añadido la generación automática de una cola de componentes cuyo SBOM no identifica la licencia. Los informes `license-review-queue.csv` y `license-review-summary.json` recogen nombre, versión exacta, identificador PURL, ecosistema y estado **PENDIENTE**. No se asignan licencias por inferencia. Cada elemento deberá contrastarse con su proyecto original y sus avisos de redistribución. La CI verifica el formato y conserva los informes junto al SBOM.

## 2026-11-06 — Verified license gap grouping / Clasificación real de licencias pendientes

**EN:** The new conservative review queue passed the full GitHub Actions run [42220551342](https://github.com/sergey08/homeassistant-addons/actions/runs/42220551342). Of the **129** CycloneDX components, **92** lack license metadata: **89 components have `pkg:golang` PURLs** and **3 have no PURL**. No Alpine `pkg:apk` item was in this specific missing-license-metadata queue. The generated `license-review-queue.csv` and `license-review-summary.json` are included with the CycloneDX and Trivy reports in the 14-day workflow artifact. This narrows the next investigation to exact Go module versions and three unidentifiable component references. Verify licenses from each upstream project's authoritative LICENSE/NOTICE files, record provenance, and assess redistribution obligations. **Do not equate missing auto-detected license metadata with a legal defect.**

**ES:** El workflow de GitHub Actions **42220551342** ha validado la cola de conciliación de licencias. De **129 componentes** detectados, **92** carecen de metadatos de licencia en el SBOM: **89 son módulos Go con identificador `pkg:golang` y 3 no incluyen PURL**. Ningún paquete `pkg:apk` figura en este grupo específico. Los CSV/JSON de revisión se adjuntan al SBOM y al informe Trivy como artefactos temporales (14 días). Debemos contrastar las 89 versiones concretas de Go y los 3 componentes no identificados con sus fuentes y avisos legales antes de distribuir la versión estable.

## 2026-11-06 — Exact Go source legal-file evidence / Fuentes originales contrastadas

**EN:** A new CI step uses the exact public Go PURLs and versions from the CycloneDX license review queue, queries the public Go module proxy with checksum verification, and records hashes of bounded, non-symlink `LICENSE`, `COPYING`, `NOTICE`, `COPYRIGHT` or `AUTHORS` files found at module roots. It **never executes downloaded module code**, copies private keys or assumes an SPDX license from a filename. [Successful Actions run 42222304256](https://github.com/sergey08/homeassistant-addons/actions/runs/42222304256) processed all **92 pending component references**: **86** yielded source legal-file evidence and **6** remain manual review. Since 3 of the 92 have no Go PURL, the six unresolved include those three plus three remaining Go module references. This is provenance evidence only: actual license text, copyleft obligations and required redistribution notices have not been legally cleared. Artifacts retain a CSV of source file hashes and module checksums for 14 days.

**ES:** Una nueva comprobación de CI contrasta las versiones exactas de los módulos Go con sus fuentes públicas y registra las huellas SHA-256 de archivos legales encontrados, sin ejecutar el código de las dependencias ni inferir automáticamente sus licencias. La ejecución real de GitHub Actions **42222304256** terminó correctamente: **86 de 92 componentes pendientes** tienen ahora evidencia de archivos legales en origen; **6 siguen pendientes** (3 sin identificador PURL y 3 módulos Go). No supone aprobación de redistribución: todavía hay que revisar las condiciones y los avisos de cada licencia.

## 2026-11-06 — Six unresolved references identified / Seis referencias identificadas

**EN:** CI job logs from [run 42222910177](https://github.com/sergey08/homeassistant-addons/actions/runs/42222910177) identified the remaining six **component entries** (not necessarily six distinct libraries): `stdlib v1.27.3` appears twice; `github.com/openai/tunnel-client` appears once with no normalized version PURL; `alpine 3.22.8` appears once without a PURL; and two executable/image-file records without PURLs are `opt/moonraker-mcp/vendor/tunnel-client` and `usr/local/bin/mcp-raker`. These are **not** six conventional unresolved public Go module versions. Follow-up attribution should map the Go standard library to the official Go distribution license, the OpenAI executable to its exact pinned release and existing Apache-2.0/NOTICE files, Alpine to package/base-image license records, and the `mcp-raker` binary to its source commit and BSD-3-Clause license. Do not assert that these matches alone satisfy all notice requirements. The two stdlib entries may represent records associated with different embedded Go binaries; do not deduplicate without preserving provenance.

**ES:** Los registros de CI identifican las seis referencias restantes: **dos registros de `stdlib` Go 1.27.3**, **un registro de `github.com/openai/tunnel-client` sin versión normalizada**, **Alpine 3.22.8** y **dos registros de archivos ejecutables** (el binario de túnel y `mcp-raker`). No son seis librerías Go desconocidas. Deben conciliarse con las licencias originales de la distribución Go, cliente OpenAI, imagen Alpine y código fuente `mcp-raker`. Mantener la distinción entre una atribución candidata y el cumplimiento legal completo.

## 2026-11-06 — Verified official legal sources for special components / Licencias originales verificadas

**EN:** Compared exact authoritative GitHub revisions, not guessed SPDX classifications:

| SBOM component | Verified authoritative license source | Distribution evidence |
| --- | --- | --- |
| Go `stdlib v1.27.3` (two entries) | [`golang/go` `go1.27.3` `LICENSE`](https://github.com/golang/go/blob/go1.27.3/LICENSE), copyright Go Authors, BSD-style 3-condition terms | Added the **complete** text verbatim to `licenses/go-toolchain-BSD-3-Clause.txt`; Docker copies `licenses/` to `/usr/share/doc/moonraker-mcp/licenses`; CI checks text present |
| `mcp-raker` compiled executable | [`lexfrei/mcp-raker` pinned source commit `f01636bec21a21cfc5f9ee84dc68dad7d44d6dd9` `LICENSE`](https://github.com/lexfrei/mcp-raker/blob/f01636bec21a21cfc5f9ee84dc68dad7d44d6dd9/LICENSE), BSD-3-Clause | Existing exact license `mcp-raker-BSD-3-Clause.txt` bundled and verified in CI |
| OpenAI tunnel-client v0.0.19 and its copied executable | [`LICENSE`](https://github.com/openai/tunnel-client/blob/v0.0.19/LICENSE) Apache-2.0 and [`NOTICE`](https://github.com/openai/tunnel-client/blob/v0.0.19/NOTICE) | Both texts already bundled and checked by CI; release artifact ZIP SHA-256 separately verified |
| Alpine 3.22.8 base image | Alpine is a collection of packages under **different licenses**, not one uniform Alpine license. the offline APKv2 installed-package database reports package name (`P`), exact version (`V`) and license expression (`L`). | DEV CI now archives `alpine-package-metadata.txt` and `alpine-packages.txt`; Trivy license scan and CycloneDX SBOM retained for obligations review |

These checks address primary attribution for the **six exceptional SBOM entries**, not the obligations of every transitively redistributed dependency. In particular, retaining GPL/LGPL software packages may trigger corresponding license/source provisions; no blanket redistribution approval is granted here. The Alpine `3.22` Docker tag is still mutable and needs a digest before stable release.

**ES:** Se han verificado las fuentes oficiales exactas de **Go 1.27.3 (licencia BSD de la distribución Go)**, **mcp-raker (BSD-3-Clause en el commit fijado)** y **tunnel-client OpenAI v0.0.19 (Apache-2.0 + NOTICE)**. La licencia de Go ya está incluida en la imagen y validada por CI. Alpine no tiene una sola licencia para todos sus componentes: se guardará la información de licencias de los paquetes efectivamente instalados mediante los campos `P`, `V` y `L` de la base local APKv2. Los seis registros especiales cuentan así con un origen de atribución definido, pero **no se declara cerrada la auditoría legal** de toda la distribución. Pendientes: obligaciones GPL/LGPL y otras licencias transitivas, atribuciones y revisión del inventario completo; fijación digest de Alpine; instalación limpia en otro Home Assistant y aprobación final.

## 2026-11-06 — Alpine package-specific redistribution review / Clasificación por paquete

**EN:** The development CI now reads installed APKv2 package records directly from the built image and produces `alpine-license-review.csv` and `alpine-license-review-summary.json`. The CSV records exact package name/version/license expression, a conservative review category and **PENDING** review status. Categories flag GPL/LGPL/MPL/EPL/CDDL and similar reciprocal/copy-left expressions for human review, while unknown or compound expressions are left unresolved. Standard permissive expressions are marked **candidates** only; no automated legal clearance is granted. Offline unit tests reject malformed/duplicated APKv2 records. The outputs are part of the short-retention GitHub Actions audit artifact. Validate its execution and exact counts before treating the new report as complete.

**ES:** La CI genera dos informes nuevos de los **paquetes Alpine realmente instalados**: CSV de nombre, versión, expresión de licencia y prioridad de revisión; JSON resumen por grupos. Se destacan GPL/LGPL/MPL y otras licencias recíprocas, pero **ninguna queda aprobada automáticamente**. Las expresiones desconocidas o compuestas siguen pendientes de revisión. También se comprueba con tests que las entradas incompletas o duplicadas se rechazan. Falta contrastar el reporte final con los avisos y obligaciones de redistribución y fijar el digest de la imagen base Alpine antes de publicar.

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
