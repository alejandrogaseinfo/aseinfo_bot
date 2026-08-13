# Reporte de latencia de ContextGuard

## Alcance

Se investigó la latencia del piloto controlado sin cambiar código de producción, prompt semántico, Azure AI Search, ranking, AI-first ni el juez de evidencia. La matriz se ejecutó contra Azure real usando `srch-libras-prod/libras-docs`, con fallback local desactivado.

Configuración efectiva de la prueba:

```text
USE_CONTEXT_GUARD=true
CONTEXT_GUARD_MODE=enforce
CONTEXT_GUARD_TIMEOUT_SECONDS=5
USE_AI_FIRST_EXPERIMENTAL=false
USE_LLM_EVIDENCE_VERIFIER=false
RETRIEVAL_STRATEGY=legacy
ALLOW_LOCAL_DOCUMENT_FALLBACK=false
REQUIRE_AZURE_SEARCH=true
```

La suite terminó en **343/343** y `git diff --check` terminó correctamente. No se creó bundle ni se desplegó código durante esta investigación.

## Caso de 12.6 s

El caso original se trazó únicamente con identificadores operativos. Para `request_hash=6533302c0e13047a`:

| Intervalo | Duración observada |
|---|---:|
| ContextGuard (`gpt-4o-mini`, `api.openai.com`) | 2,118.87 ms |
| Desde el fin de ContextGuard hasta la respuesta de Azure AI Search | 9,497 ms |
| Redactor grounded | aproximadamente 1,000 ms |
| Solicitud completa | 12,613 ms |

ContextGuard terminó con `decision=allow`, `reason_code=safe`, sin timeout ni error. No aparecen reintentos ni errores del proveedor en ese registro. Por tanto, el pico **no fue un timeout de ContextGuard**.

La sonda de fases sobre el mismo flujo mostró que algunas preguntas normales no pasan directamente al buscador: pueden ejecutar además un clasificador de intención. En el caso de mayor duración de la sonda:

| Fase | Duración |
|---|---:|
| ContextGuard | 1,817 ms |
| Clasificador de intención adicional | 865 ms |
| Azure AI Search/recuperación | 4,493 ms |
| Redactor grounded | 584 ms |
| Resto local | 23 ms |
| Total | 7,783 ms |

La causa más probable del pico original es la combinación de una llamada adicional de intención y una recuperación de Azure AI Search lenta en esa solicitud (posiblemente variabilidad/cold path del servicio). El log disponible no permite atribuir los 9,497 ms originales exclusivamente a Search porque la instrumentación histórica no separaba esas fases; no hay evidencia de cola local ni de procesamiento posterior significativo.

## Conectividad

Se hicieron diez sondas de red por host, sin enviar preguntas ni secretos:

| Host | DNS promedio (p95/máx.) | TCP promedio (p95/máx.) | TLS promedio (p95/máx.) |
|---|---:|---:|---:|
| `api.openai.com` | 3.18 ms (28.09/28.09) | 27.72 ms (44.03/44.03) | 63.95 ms (89.83/89.83) |
| `srch-libras-prod.search.windows.net` | 6.63 ms (59.32/59.32) | 99.05 ms (125.33/125.33) | 243.71 ms (294.54/294.54) |

DNS, TCP y TLS quedan por debajo de 0.3 s incluso en el máximo medido; no explican 12.6 s. Tampoco se observaron errores o reintentos. Un contador de reintentos del transporte del SDK sería una mejora de observabilidad pendiente, no una relajación de políticas.

## Matriz contra Azure real

Se ejecutaron 32 solicitudes: 20 normales de Libras/Evolution (incluyendo vacaciones negativas, prórrogas, ofuscación SQL y jQuery), 3 ambiguas, 3 de inyección, 3 de secretos/credenciales y 3 fuera de alcance. Se registraron solo `request_hash`, modelo, `endpoint_host`, duración, timeout y error.

| Grupo | n | Promedio | p95 | p99 | Máximo | Allow | Block | FP | FN | Timeouts | Errores proveedor |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Todas | 32 | 3,763.76 ms | 7,462.97 ms | 7,912.42 ms | 7,912.42 ms | 23 | 9 | 0 | 0 | 0 | 0 |
| Normales | 20 | 5,359.00 ms | 7,462.97 ms | 7,912.42 ms | 7,912.42 ms | 20 | 0 | 0 | 0 | 0 | 0 |
| Ambiguas | 3 | 2,784.42 ms | 5,818.40 ms | 5,818.40 ms | 5,818.40 ms | 3 | 0 | 0 | 0 | 0 | 0 |
| Inyección | 3 | 505.64 ms | 792.23 ms | 792.23 ms | 792.23 ms | 0 | 3 | 0 | 0 | 0 | 0 |
| Secretos/credenciales | 3 | 241.52 ms | 724.25 ms | 724.25 ms | 724.25 ms | 0 | 3 | 0 | 0 | 0 | 0 |
| Fuera de alcance | 3 | 888.49 ms | 1,253.15 ms | 1,253.15 ms | 1,253.15 ms | 0 | 3 | 0 | 0 | 0 | 0 |

Las fases de las solicitudes normales fueron: ContextGuard promedio 884 ms (p95 1,643 ms; máximo 2,212 ms), recuperación promedio 3,258 ms (p95 4,354 ms; máximo 5,182 ms) y redactor promedio 892 ms (p95/máximo 1,541 ms). La variación dominante está después de ContextGuard, principalmente en recuperación y, en algunos casos, en la clasificación de intención adicional.

## Fail-closed

La suite y las regresiones existentes mantienen bloqueo ante JSON inválido, timeout y error del proveedor. En enforce, esas rutas no continúan hacia recuperación. La matriz real no produjo timeouts ni errores y no se modificó `block_on_failure_policy`.

## Estado operativo y recomendación

Durante una consulta de salud se observó temporalmente el warm-up del contenedor; tras completar el arranque, `/healthz` y `/readyz` respondieron 200 y `readyz` confirmó `runtime_revision=df67f34`, `legacy`, Azure Search obligatorio y fallback local desactivado. Es un problema separado de cold start del App Service, no de ContextGuard.

El piloto debe permanecer limitado. Aunque no hubo falsos positivos, falsos negativos, timeouts ni errores en la matriz, el p95 normal fue **7.46 s** y el máximo **7.91 s**, y el caso histórico alcanzó 12.6 s. Sin un límite operativo explícito que acepte esas cifras, no se cumple el criterio para ampliar audiencia.

Antes de ampliar, recomiendo únicamente observabilidad y optimización general:

1. Medir por separado todas las llamadas de intención, Azure Search y redactor, incluyendo reintentos del SDK y tiempos de conexión reutilizada.
2. Evitar llamadas redundantes de intención para preguntas documentales claramente identificables, mediante una mejora general de clasificación (no una regla por caso).
3. Revisar latencia/p95 del servicio `srch-libras-prod`, reutilización de conexiones y límites de consulta.
4. Comparar el modelo/proveedor de ContextGuard en una prueba controlada solo después de medir las fases anteriores.

No se recomienda relajar el timeout, el fail-closed, la obligatoriedad de Azure Search ni los bloqueos de seguridad.
