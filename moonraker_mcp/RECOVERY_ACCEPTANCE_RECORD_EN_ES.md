# Moonraker MCP — Acta de recuperación previa a v0.1.0 / Recovery acceptance record

**Estado:** PENDIENTE DE EJECUCIÓN. Este acta se refiere a un **Home Assistant de pruebas desechable**, nunca al Lenovo que está funcionando. No introducir credenciales, identificadores del túnel, direcciones privadas, ficheros `options.json`, capturas de campos secretos, copias de seguridad ni claves reales en este documento.

## Alcance del ensayo

- Plataforma de pruebas: Home Assistant OS/Supervised con Supervisor; arquitectura `amd64` o `aarch64`.
- Código sometido a ensayo: commit exacto de `dev/moonraker-mcp-dev2` y versión de complemento registrada por el revisor.
- Credenciales: **túnel OpenAI exclusivo de prueba**, API key restringida independiente, token HTTP MCP único y credencial Moonraker de pruebas si procede.
- Puerto `8765/tcp`: **sin publicar**; perfiles opcionales: **desactivados**.

## Pasos y resultados de aceptación

| Ref. | Prueba segura | Evidencia no sensible exigida | Estado |
| --- | --- | --- | --- |
| R1 | Arranque inicial solo desde GUI, con token MCP no vacío | Versión, arquitectura y `started` | PENDIENTE |
| R2 | Activar túnel con clave de pruebas A y consultar `moonraker_connection_status` | Registro redactado de arranque y respuesta operacional sin IP | PENDIENTE |
| R3 | Crear una nueva clave restringida B en OpenAI, introducirla en la GUI y reiniciar | Arranque y consulta MCP correctos después del cambio | PENDIENTE |
| R4 | Revocar la clave A desde OpenAI, sin tocar la nueva B | Confirmación de revocación en proveedor; conexión B aún funciona | PENDIENTE |
| R5 | Crear copia de aplicación **protegida y cifrada**; comprobar ubicación y acceso del fichero | Identificador local de copia **no compartido** y confirmación de protección | PENDIENTE |
| R6 | Restaurar la copia únicamente en un HA desechable de pruebas | Restauración sin fuga de secretos y sin publicar el puerto | PENDIENTE |
| R7 | Tras restaurar, establecer una **nueva clave C**; revocar cualquier clave de prueba recuperada aún activa | Arranque con C, nueva consulta MCP y revocación de las antiguas | PENDIENTE |
| R8 | Confirmar que una opción vacía de `openai_tunnel_api_key` **no** se confunde con una revocación y que los secretos de copias antiguas siguen sujetos a rotación | Confirmación del comportamiento documentado, sin mostrar claves | PENDIENTE |
| R9 | Comprobar el apagado del túnel y limpieza del entorno desechable | Se desconectó el túnel de pruebas y se revocaron sus credenciales | PENDIENTE |

**No habilitar interfaces externas ni ejecutar G-code para verificar esta acta.** La CI contiene pruebas sintéticas de R6–R8, pero estas **no** validan la restauración real de Supervisor ni la revocación en OpenAI.

## Acta final (rellenar exclusivamente tras ejecutar el ensayo)

- Fecha:
- Entorno y arquitectura de pruebas:
- Versión del complemento y SHA de GitHub:
- Resultado agregado: `PENDIENTE / APROBADO / RECHAZADO`
- Referencias R1–R9 verificadas:
- Incidencias y mitigaciones, sin datos privados:
- Revisor:
- Aprobación del mantenedor:

**Criterio de aceptación:** el resultado solo puede pasar a `APROBADO` si cada prueba R1–R9 tiene evidencia operacional real, especialmente R4 y R6. No marcar una prueba como exitosa porque haya pasado una simulación, una CI o una comprobación en el Lenovo.

**Limitaciones:** un acta aprobada resuelve solo recuperación/rotación operativa. La revisión humana de licencias y el SBOM exacto siguen siendo requisitos **independientes** antes de publicar v0.1.0.

[Procedimiento de credenciales](./SECRET_ROTATION_BACKUPS_EN_ES.md) · [Guía de liberación](./RELEASE_REVIEW_HANDOFF_EN_ES.md)
