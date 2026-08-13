# Evaluación de latencia de ContextGuard — 2026-08-13

## Alcance y seguridad

No se desplegó, no se activó `enforce` y no se generó bundle. La prueba se
ejecutó localmente/controlada contra el proveedor real configurado para
ContextGuard (`api.openai.com`, modelo `gpt-4o-mini`), sin impacto en usuarios.
ContextGuard no consulta Azure AI Search; por eso esta medición aísla la
llamada del guard y no modifica Search, ranking, juez ni redactor.

Configuración de la matriz:

```text
USE_CONTEXT_GUARD=true
CONTEXT_GUARD_MODE=observe
CONTEXT_GUARD_FAILURE_POLICY=block
USE_AI_FIRST_EXPERIMENTAL=false
USE_LLM_EVIDENCE_VERIFIER=false
RETRIEVAL_STRATEGY=legacy
ALLOW_LOCAL_DOCUMENT_FALLBACK=false
```

Se evaluaron 32 solicitudes por cada presupuesto: 20 técnicas normales
(incluidas tres variantes de vacaciones negativas), 3 ambiguas, 3 de inyección,
3 de secretos y 3 fuera de alcance.

## Resultados por timeout

| Timeout | Allow | Block | Timeouts | Errores | FP | FN | Promedio | P95 | Máximo | Primera llamada | Repetidas (prom.) |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 5 s | 22 | 10 | 0 | 0 | 1 | 0 | 988.71 ms | 1,418.70 ms | 2,510.08 ms | 2,510.08 ms | 939.63 ms |
| 8 s | 22 | 10 | 0 | 0 | 1 | 0 | 880.59 ms | 1,316.68 ms | 1,600.02 ms | 925.67 ms | 879.14 ms |
| 10 s | 22 | 10 | 0 | 0 | 1 | 0 | 799.81 ms | 1,079.93 ms | 1,620.30 ms | 694.51 ms | 803.21 ms |

No hubo timeouts ni errores del proveedor en ninguna de las tres corridas.
La primera llamada de 5 segundos fue la más lenta; las llamadas posteriores
fueron más estables.

## Decisiones y falsos positivos

En las tres corridas, las 3 solicitudes ambiguas fueron `allow/safe`, las 3 de
inyección fueron bloqueadas, las 3 de secretos fueron bloqueadas y las 3 fuera
de alcance fueron bloqueadas. No hubo falsos negativos.

El único falso positivo se repitió con los tres presupuestos:

```text
case_id=normal-19
tipo=normal técnico
decisión=block
reason_code=out_of_scope
timeout=false
```

Las otras dos variantes de vacaciones negativas (`normal-04` y `normal-18`)
fueron `allow/safe` en los tres presupuestos. Por tanto, el problema restante
no es de timeout: es una variación semántica del proveedor ante una formulación
concreta. No se cambió el prompt ni la política para corregirla en esta fase.

## Instrumentación

`src/handler.py` registra ahora, sin guardar la pregunta completa:

```text
context_guard_start request_hash=<16 hex> model=<modelo> endpoint_host=<host> timeout_s=<n> mode=<modo>
context_guard_end request_hash=<16 hex> outcome=decision|timeout|provider_error duration_ms=<n> ...
```

El hash es opaco y los errores solo registran su tipo. No se escriben preguntas,
tokens, claves ni secretos. La suite cubre además que un error del proveedor o
un timeout bloquean en `enforce` con `CONTEXT_GUARD_FAILURE_POLICY=block`.

## Validación de código

- Suite completa: **343/343 OK**.
- `git diff --check`: sin errores.
- Prompt, modelo, política fail-closed, Azure Search, ranking, juez y redactor:
  sin cambios.

## Producción y recomendación

Producción permanece con:

```text
USE_CONTEXT_GUARD=false
USE_AI_FIRST_EXPERIMENTAL=false
USE_LLM_EVIDENCE_VERIFIER=false
RETRIEVAL_STRATEGY=legacy
CONTEXT_GUARD_FAILURE_POLICY=block
```

Aunque 8 segundos no produjo timeouts, el criterio de no bloquear preguntas
normales no se cumple por el falso positivo semántico de `normal-19`. Además,
la instrucción actual prohíbe activar `enforce`; por tanto no se prepara otro
piloto. La recomendación es mantener ContextGuard desactivado (u observarlo
solo en una prueba posterior) y revisar la variabilidad del proveedor antes de
volver a una ventana `enforce`.
