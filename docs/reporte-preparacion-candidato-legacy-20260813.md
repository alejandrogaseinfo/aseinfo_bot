# Preparación de candidato legacy con arranque Linux — 2026-08-13

## Alcance

Este reporte prepara un nuevo artefacto local; no modifica App Service ni
Teams. Producción permanece en `df67f34` y el candidato anterior no se vuelve
a usar.

## Validación reproducible de arranque

`scripts/validate_linux_startup.py` valida un directorio de despliegue o ZIP
con un contenedor `python:3.11.15-slim`. No propaga variables del host ni usa
Azure: instala desde `requirements.txt`, importa `app`, `aiohttp` y `gunicorn`,
y ejecuta la comprobación de Gunicorn para
`aiohttp.worker.GunicornWebWorker` y `app:app`.

El validador rechaza `.env`, pruebas, documentos, datos, salida, `tmp` y una
estructura envuelta en `src/`. El runtime usa `app:app`, por lo que los
archivos de `src/` se publican en la raíz del ZIP.

## Procedimiento obligatorio de publicación y recuperación

1. Iniciar exactamente un OneDeploy y registrar su identificador.
2. Mientras `complete=false`, no iniciar rollback ni otro despliegue.
3. Esperar el estado terminal exitoso (`complete=true`, estado exitoso).
4. Solo entonces consultar `/healthz` y `/readyz`.
5. Si falla el despliegue o la salud, esperar primero su estado terminal.
6. Después iniciar un único rollback con el ZIP productivo aprobado, conservar
   la configuración anterior y comprobar nuevamente ambas sondas.
7. Nunca solapar despliegues.
