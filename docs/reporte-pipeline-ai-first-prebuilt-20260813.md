# Pipeline Linux para bundle preconstruido AI-first

## Estado

Preparado, sin ejecutar despliegue ni modificar App Service. El host local es
Windows y no tiene Docker ni WSL instalado; por eso no se generó ningún ZIP
preconstruido localmente.

## CI autorizado

`.github/workflows/build-ai-first-prebuilt.yml` usa `ubuntu-22.04` y Python
3.11. Instala `src/requirements.txt` con `pip --target .ci-site-packages`,
construye `.python_packages/lib/site-packages`, empaqueta un ZIP plano y
ejecuta imports, `gunicorn --check-config`, extracción/listado, suite completa
y `git diff --check`.

El script `scripts/build_prebuilt_linux_bundle.py` exige explícitamente Linux
y Python 3.11. Genera `.deployment` con:

```text
SCM_DO_BUILD_DURING_DEPLOYMENT=false
ENABLE_ORYX_BUILD=false
```

El workflow publica únicamente el artefacto CI; no contiene credenciales,
`.env`, pruebas, logs ni datos, y no tiene pasos de Azure, OneDeploy o Teams.

## Gate posterior al despliegue

Desde SSH → Application debe ejecutarse
`scripts/validate_post_deployment_ai_first.sh`, que comprueba la existencia
física de `handler.py` y `ai_first.py` e importa ambos con
`PYTHONPATH=/home/site/wwwroot`.

Solo después de ese gate, salud HTTP y revisión de configuración se podría
solicitar autorización separada para OneDeploy y el piloto controlado.
