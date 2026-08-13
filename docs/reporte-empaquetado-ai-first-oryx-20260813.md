# Validación de empaquetado AI-first para App Service/Oryx — 2026-08-13

## Resultado

No se desplegó, no se reinició App Service, no se abrió Teams y no se cambió
ninguna configuración productiva.

La causa del incidente anterior es operacional/de plataforma: Oryx ejecuta el
build remoto con `CompressDestinationDir=true` y publica `output.tar.zst` como
el directorio de salida comprimido. Ese tarball no es el ZIP fuente. En la
ejecución observada el resultado contenía solo metadata, `requirements.txt` y
el artefacto comprimido, por lo que `ai_first.py` y `handler.py` no estaban
disponibles al importarse desde el destino esperado. El ZIP local sí contenía
ambos archivos; por eso el SHA del ZIP no demostraba la integridad del
resultado Oryx.

## Artefactos reproducibles

- ZIP fuente plano:
  `output/libras-backend-ai-first-oryx-compatible-20260813-bundle.zip`
- SHA-256 ZIP:
  `08039EA243CF9FE3717D22DDB34B02B43FDDC3810480D9DA53E59055A64FA314`
- Equivalente local del directorio comprimido por Oryx:
  `output/libras-backend-ai-first-oryx-compatible-20260813-output.tar.zst`
- SHA-256 `output.tar.zst`:
  `3A6315CE5443F0CF1759B3819C517E714B87FAAE00A60D8D91144059D01B23D6`

El ZIP y el tarball tienen exactamente el mismo conjunto de 26 archivos en
la raíz. El contenido obligatorio fue comprobado dentro del tarball:
`app.py`, `handler.py`, `ai_first.py`, `config.py`, `requirements.txt` y
`.deployment`.

## Pruebas

- Regresión automática del bundle: OK; falla si falta `handler.py` o
  `ai_first.py`.
- Extracción/listado del ZIP y `output.tar.zst`: OK; los listados coinciden.
- Suite completa: **360/360 OK**.
- `git diff --check`: OK.
- Importación local equivalente (`app`, `aiohttp`, `gunicorn`): OK con la
  configuración ficticia de arranque.
- Gunicorn `--check-config` en Windows: no ejecutable porque Gunicorn requiere
  `fcntl`, módulo Linux. Docker/WSL no están disponibles en este host; queda
  pendiente repetirlo en Linux antes de autorizar un despliegue.

## Formato recomendado

Mantener el ZIP plano, con `app.py`, `handler.py`, `ai_first.py`,
`requirements.txt` y `.deployment` en la raíz. Antes de cualquier OneDeploy,
extraer y listar el resultado Oryx real y comparar sus miembros y hashes con
este artefacto. Si `output.tar.zst` no contiene el conjunto completo, detener
la operación y no activar `USE_AI_FIRST_EXPERIMENTAL`.

Configuración productiva no modificada:

```text
RETRIEVAL_STRATEGY=legacy
USE_AI_FIRST_EXPERIMENTAL=false
USE_CONTEXT_GUARD=false
USE_LLM_EVIDENCE_VERIFIER=false
USE_LLM_GROUNDED_RESPONSE=false
REQUIRE_AZURE_SEARCH=true
ALLOW_LOCAL_DOCUMENT_FALLBACK=false
```
