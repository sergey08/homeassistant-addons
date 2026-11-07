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
