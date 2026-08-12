# Bitácora de cierre — 2026-08-12

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
