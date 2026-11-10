# Moonraker MCP v0.1.0 — Checklist mínimo de publicación

**Estado:** candidato DEV funcional validado, sin publicación autorizada.

El objetivo es dejar de ampliar la auditoría y publicar una primera versión estable con los controles realmente necesarios. Este documento sustituye a las listas largas **como plan operativo**, pero no convierte pruebas ausentes ni revisiones legales pendientes en aprobaciones.

## Requisitos de salida (cortos)

- [x] Pruebas funcionales en amd64 y arm64 realizadas; túnel ChatGPT/Moonraker comprobado.
- [x] CI de seguridad, pruebas y compilaciones multi-arquitectura configurada; la CI debe estar verde **para el SHA candidato final**.
- [ ] Confirmar **cumplimiento práctico de redistribución**: textos LICENSE y NOTICE de los binarios y paquetes incluidos, atribuciones y disponibilidad del código fuente correspondiente cuando las licencias lo exijan. Basta una revisión centrada en obligaciones reales; **no se exige terminar una auditoría SHA-512 de todas las descargas ni rellenar 129 fichas jurídicas como condición artificial**. No declarar conforme lo no revisado.
- [ ] Documentar los riesgos aceptados: no se repiten pruebas de recuperación/rotación de tokens, a petición del mantenedor; dejar escrito **NO VERIFICADO**, nunca PASS. Comprobar que el catálogo no sugiere una migración automática desde DEV a estable.
- [ ] Preparar versión `0.1.0`, nombre sin DEV y documentación de instalación para usuarios nuevos; comprobar CI final.
- [ ] Obtener autorización explícita del mantenedor **después** de revisar el candidato final; solo entonces fusionar PR #89, crear `moonraker-mcp-v0.1.0` y publicar GitHub Release.

## Qué dejamos de perseguir antes de v0.1.0

- No más auditorías generales del inventario Alpine, salvo que la revisión de obligaciones reales descubra una ausencia concreta.
- Las verificaciones de 164/166 fuentes siguen archivadas como **evidencias útiles**, pero las dos URL con fallos HTTP no impiden por sí solas distribuir una imagen si la disponibilidad de código fuente y el cumplimiento de licencias están resueltos por otras vías.
- No más claves, túneles ni instalaciones adicionales de prueba; sin cambios en el Lenovo.
- No ocultar que un resultado de integridad parcial, CI fallida o revisión legal incompleta sigue siendo parcial.

## Control antes del botón Publicar

1. Verificar que GitHub Actions esté verde en el commit exacto elegido.
2. Revisar las obligaciones reales de cada familia licenciada relevante para la **imagen distribuida**, avisos entregados y fuentes accesibles. Para GPL/LGPL/MPL, confirmar los medios adecuados de cumplimiento.
3. Revisar `config.yaml`, README e identidad del repositorio estable; indicar cómo se configura el token **existente** desde la interfaz de Home Assistant, sin pedir operaciones manuales de shell.
4. Registrar riesgos conscientemente no ensayados y pedir aprobación concreta para merge/tag/release.

**Este checklist es una simplificación del proceso, no un dictamen jurídico.**

## Modalidad de la primera distribución: código fuente

**Alcance revisado:** `config.yaml` no declara `image:`. Al añadir este catálogo, Home Assistant construye el complemento en el equipo del usuario desde el `Dockerfile` y descarga directamente los proyectos y paquetes de terceros que necesita. El repositorio no entrega una imagen GHCR propia ni los binarios compilados de Moonraker MCP. El código original del complemento se distribuye bajo la licencia MIT del repositorio y los archivos LICENSE/NOTICE upstream incluidos se mantienen con sus atribuciones y procedencia.

**Distinción jurídica y operativa:** esta revisión corresponde exclusivamente al código fuente distribuido en GitHub, no certifica una imagen Docker redistribuida por el mantenedor. Los 129 registros PENDING del SBOM siguen siendo válidos como límite a una eventual publicación de imágenes binarias y **no** se marcan aprobados. La compilación local puede tardar más y depende de la disponibilidad de repositorios externos. Los usuarios que redistribuyan imágenes deberán revisar sus propias obligaciones de licencias, avisos y fuentes correspondientes.

**Riesgo residual aceptado para la primera distribución:** las pruebas reales de restauración cifrada y revocación de credenciales no se han ejecutado. No se garantizan recuperación automática ni migración DEV→estable. La instalación inicial debe hacerse con credenciales propias, token MCP único, puerto 8765 no publicado y perfiles de escritura desactivados. No se deben reutilizar IDs de túneles entre DEV y estable.

**Publicación efectiva:** esta delimitación no constituye una certificación jurídica exhaustiva; únicamente aclara que el paquete fuente y la imagen binaria tienen alcances de redistribución distintos. Confirmar CI final y autorización del mantenedor para integrar en `main` antes de publicar.
