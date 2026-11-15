# Moonraker MCP — flujo seguro de impresión (diseño inicial)

Estado: propuesta de implementación; **no habilitar acciones de escritura en producción** hasta completar pruebas.

## Objetivo
Permitir preparar un modelo para Snapmaker U1, subir G-code validado a Moonraker y lanzar la impresión **solo tras confirmación explícita y reciente del usuario**.

## Hallazgos del repositorio
- La versión 0.1.4 ya incluye las opciones `enable_write_actions` y `allow_print_start` en `config.yaml`, desactivadas por defecto.
- `run.sh` filtra los perfiles `print_*` mediante el interruptor maestro.
- Esto **no demuestra** que exista una herramienta de subida de archivos ni que el flujo de confirmación esté implementado.

## Fases
1. Inventariar herramientas reales del gateway y API Moonraker, identificar ruta de subida y arranque y revisar la política del proxy.
2. Añadir subida de G-code a carpeta de cuarentena, con límites de tamaño, nombre saneado, autenticación, bloqueo de rutas arbitrarias y comprobación de hash.
3. Validar metadatos: máquina Snapmaker U1, tamaño/volumen, herramientas T0–T3, materiales, temperaturas y estimaciones. Rechazar G-code de procedencia o compatibilidad dudosa; preferir laminar STL/3MF con perfil U1.
4. Implementar preparación sin movimiento y vista previa de archivo, consumos y riesgos; obtener confirmación explícita del usuario antes del arranque. Una confirmación no se reutiliza para otro archivo o trabajo.
5. Antes de arrancar, verificar conexión, Klippy ready, estado no imprimiendo/pausado, archivo y hash intactos, y condiciones físicas que requieran verificación humana (cama despejada, pieza retirada, filamento correcto). La API no garantiza por sí sola estas condiciones.
6. Arranque opt-in con permisos mínimos, trazabilidad de usuario, fecha, hash, resultado, y gestión de reintentos idempotente. No iniciar automáticamente por recuperar conexión ni repetir un comando de resultado incierto.
7. Pruebas unitarias, integración simulada y pruebas reales controladas; documentación de rollback. Activar solo tras revisión y aprobación.

## Criterios de aceptación
- Sin permisos de escritura, el catálogo sigue siendo solo lectura.
- La subida nunca implica arranque.
- Ninguna impresión se inicia sin confirmación específica para ese G-code.
- No se ejecuta G-code arbitrario enviado como comando directo.
- Errores de red o timeout no provocan doble arranque.
- Estado, archivo, progreso y resultado se pueden verificar desde el MCP.

## Fuera de alcance inicial
Laminado automático remoto, descarga y ejecución automática de archivos de terceros, gestión de energía o intervención física en la impresora.
