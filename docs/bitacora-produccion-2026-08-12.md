# Bitácora de cierre — 2026-08-12

> Registro histórico de una ejecución anterior. La línea base vigente es
> 315/315 pruebas locales y la decisión actual está en
> [resultado-calidad-20260812.md](resultado-calidad-20260812.md). Este archivo
> no autoriza despliegues ni activación del redactor.

## Política de ambigüedad de versión

Se implementó la política general para consultas de instalación o actualización
sin versión explícita cuando Azure AI Search devuelve Readme de más de una
versión incompatible. Libras no presenta evidencia final y responde
`solicita_contexto`, pidiendo la versión exacta. Con una versión explícita se
mantiene el filtro exacto; una sola versión candidata y consultas no
relacionadas con releases conservan el comportamiento normal.

## Validación

- Escenarios dirigidos: **4/4 OK**.
- Suite completa: **302/302 pruebas OK**.
- Evaluación real contra Azure AI Search: **no válida como métrica de retrieval**;
  el endpoint no resolvió DNS desde el entorno de ejecución.
- `USE_LLM_EVIDENCE_VERIFIER=false`.
- `RETRIEVAL_STRATEGY=legacy`.
- No se activó el LLM.
- No se realizó ningún despliegue a producción.

La evaluación remota debe ejecutarse desde SSH/App Service, donde el endpoint
de Azure AI Search tenga resolución DNS, usando el bundle temporal preparado en
`/tmp` y sin copiarlo a `/home/site/wwwroot`.

## Operación de validación en App Service

La consola de **Kudu** y **SSH → Application** tienen responsabilidades
distintas:

- **Kudu File Manager/SSH:** sirve para comprobar o transferir archivos. Su
  `python` puede no existir o usar un Python del sistema sin las dependencias
  del proyecto (`python-dotenv`, Azure SDK, etc.); no debe usarse para ejecutar
  la evaluación Python.
- **SSH → Application:** es el canal para ejecutar Python, porque inicia el
  entorno virtual `antenv` con las dependencias instaladas. La implementación
  temporal extraída bajo `src/` se selecciona con
  `PYTHONPATH="/home/site/wwwroot/src"`.

Comando de configuración recomendado desde SSH → Application:

```bash
cd /home/site/wwwroot
PYTHONPATH="$PWD/src" python - <<'PY'
import os
from config import Config

c = Config(os.environ)
print("retrieval_strategy=", c.retrieval_strategy)
print("use_llm_evidence_verifier=", c.use_llm_evidence_verifier)
print("azure_search_enabled=", c.azure_search_enabled)
PY
```

La suite completa no puede considerarse validada en App Service si el bundle
solo contiene `tests/corpus-recuperacion-calidad.json` y no contiene archivos
`tests/test_*.py`; en ese caso `unittest discover` puede terminar con `Ran 0
tests`. La suite oficial debe ejecutarse en el repositorio local, donde sí se
versionan las pruebas.

El 2026-08-12 la evaluación contra Azure ejecutada desde `/home/site/wwwroot`
contactó correctamente `libras-docs` y obtuvo **14/15**, recall de evidencia de
**91.7%** y abstención correcta de **100%**. Ese resultado corresponde a la
línea base del código que se ejecutó allí. La política de ambigüedad del
commit `694fce1` no debe darse por desplegada solo porque existan archivos bajo
`/home/site/wwwroot/src`; debe verificarse explícitamente y no se realizó un
despliegue como parte de esta validación.

### Corrección posterior detectada en la evaluación de `src`

Al ejecutar la copia bajo `/home/site/wwwroot/src` desde SSH → Application, la
evaluación bajó temporalmente a **13/15**. El diagnóstico mostró que RAG-07
(reinstalación técnica de MSDTC) estaba siendo tratado erróneamente como una
consulta de release y se bloqueaba por Readme de varias versiones. La política
se acotó a `_is_release_guidance_question`, que exige una señal de preparación,
precaución o contexto previo junto con instalación/actualización. La
reinstalación técnica ya no activa la abstención de versión.

La regresión quedó cubierta por una prueba específica y la suite local completa
terminó en **303/303 pruebas, OK**. El corpus remoto todavía declara RAG-09 como
`evidence`; por eso no debe usarse para validar la nueva respuesta
`solicita_contexto` hasta actualizar el contrato del evaluador.
