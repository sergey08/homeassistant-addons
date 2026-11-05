# Release readiness and supply-chain audit / Preparación y cadena de suministro

**Date / Fecha: 2026-11-05 · DEV10.** Evidence collected against the pinned code and the development Docker build, not a formal third-party security certification.

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
