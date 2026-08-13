# Instrumentación de latencia por etapa

## Alcance

Este cambio añade observabilidad no sensible para separar ContextGuard,
intención, Azure AI Search, ranking, deduplicación, redactor y tiempo total.
No cambia `legacy`, filtros, ranking, índice, prompts, políticas de seguridad,
fallback ni configuración productiva. No se creó bundle ni se desplegó.

Cada evento conserva únicamente:

- `request_hash`: hash truncado de la consulta;
- `model` y `endpoint_host`;
- inicio/fin mediante eventos pareados;
- `duration_ms`, `timeout_s`, `outcome` y código de error;
- `retries` en cada llamada observada del SDK de Azure Search.

No se registran preguntas, prompts, documentos, tokens ni secretos. Para las
llamadas OpenAI de intención y redacción se marca `sdk_retries=unobserved`:
el contador solicitado para esta fase se implementó en Azure Search, donde el
SDK expone `PipelineResponse.context.history`. Esto evita presentar como exacto
un contador que todavía no ofrece el cliente OpenAI utilizado.

## Eventos

| Etapa | Eventos | Medición |
|---|---|---|
| ContextGuard | `context_guard_start/end` | ya existente; decisión, timeout y error |
| Intención | `intent_start/end` | cada llamada al clasificador, incluyendo timeout/error |
| Recuperación total | `retrieval_start/end` | ventana completa de recuperación y timeout del handler |
| Cada consulta Search | `azure_search_query_start/end` | llamada lexical/semantic/vector, duración y retries del SDK |
| Recuperación Azure | `azure_retrieval_start/end` | unión y salida de la estrategia configurada |
| Ranking | `retrieval_ranking_start/end` | ranking determinista y número de candidatos |
| Deduplicación | `retrieval_dedup_start/end`, `retrieval_merge_dedup_start/end` | deduplicación local y posterior a la unión |
| Redactor | `grounded_response_start/end` | duración, timeout/error y modelo |

Las consultas de Search se identifican por `query_index` y `query_kind`, nunca
por el texto buscado. El contador de reintentos se obtiene del historial del
pipeline de Azure SDK, incluida la ruta de error cuando el proveedor devuelve
una excepción con respuesta.

## ¿Cuándo se necesita intención?

En la ruta legacy, una consulta documental concreta se detecta primero con
`_looks_like_documentary_question`. Si `USE_LLM_INTENT_CLASSIFIER=true`, el
clasificador se llama solo cuando la consulta no es documental; las preguntas
documentales continúan directamente a recuperación. La ruta AI-first mantiene
su llamada de intención detrás de `USE_AI_FIRST_EXPERIMENTAL` y permanece
apagada.

La nueva telemetría permite comprobar esta decisión por `request_hash`: un
evento `intent_start` debe existir únicamente cuando la rama conversacional o
AI-first lo necesita. No se añadió ninguna regla por pregunta o por OPS.

## Validación

Las regresiones de observabilidad verifican que el hash no contenga el texto de
la consulta, que el host no incluya rutas y que el contador de retries se
registre sin exponer el payload. La suite local quedó verde después de la
instrumentación; el conteo puede aumentar cuando se conservan las regresiones
nuevas.

La siguiente prueba controlada debe ejecutar la matriz contra
`srch-libras-prod/libras-docs` y calcular p50/p95/p99 por cada evento, sin
activar AI-first ni `USE_LLM_EVIDENCE_VERIFIER`. La expansión de audiencia queda
bloqueada hasta que el p95 y el máximo cumplan el límite operativo acordado y
se mantengan cero falsos positivos, falsos negativos y timeouts normales.

## Optimizaciones generales propuestas

1. Eliminar llamadas redundantes de intención solo mediante la clasificación
   documental general ya existente, verificando el efecto con la nueva métrica.
2. Revisar cuántas consultas lexicales/focused/vector se ejecutan por solicitud
   y comparar su recall contra su coste antes de reducirlas.
3. Medir retries, cold connection y tiempos de cada llamada Search para ajustar
   límites del SDK sin relajar el fail-closed.
4. Reutilizar clientes/conexiones donde sea seguro y comparar el coste del
   redactor frente a la respuesta determinista.
