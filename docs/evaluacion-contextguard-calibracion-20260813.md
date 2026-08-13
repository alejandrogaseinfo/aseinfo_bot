# Calibración de ContextGuard — 2026-08-13

## Alcance

Se ajustó únicamente el prompt de clasificación semántica de ContextGuard.
No se modificaron Azure AI Search, el ranking, el juez de evidencia, el
redactor ni el modelo.

La regla general ahora es: bloquear solo una violación explícita de seguridad
o una consulta claramente ajena; permitir preguntas técnicas/operativas aunque
falten producto, versión o evidencia. Los términos de procedimientos SQL,
vacaciones, prórrogas, jQuery, MSDTC, scripts y tablas no son por sí mismos una
razón para bloquear.

## Observe con timeout de 5 segundos

Configuración de la corrida:

```text
USE_CONTEXT_GUARD=true
CONTEXT_GUARD_MODE=observe
CONTEXT_GUARD_TIMEOUT_SECONDS=5
USE_AI_FIRST_EXPERIMENTAL=false
USE_LLM_EVIDENCE_VERIFIER=false
RETRIEVAL_STRATEGY=legacy
ALLOW_LOCAL_DOCUMENT_FALLBACK=false
```

Se ejecutaron 22 casos: 10 normales, 3 ambiguos, 3 fuera de alcance, 3 de
inyección y 3 de secretos.

| Métrica | Resultado |
|---|---:|
| Allow | 13 |
| Block | 9 |
| Errores | 0 |
| Timeouts | 0 |
| Falsos positivos | 0 |
| Falsos negativos | 0 |
| Latencia promedio | 817.54 ms |
| P95 | 898.95 ms |
| Máximo | 1,920.31 ms |

Las cuatro regresiones de vacaciones negativas, prórrogas, ofuscación SQL y
jQuery fueron `allow/safe`. Las inyecciones y solicitudes de credenciales
fueron `block/unsafe_request`; las consultas externas fueron
`block/out_of_scope`; las preguntas ambiguas fueron `allow/safe`.

JSON malformado (`JSONDecodeError`) y error del proveedor (`RuntimeError`)
siguen siendo rechazados por el contrato. El detalle por caso y el JSON de
salida están en el artefacto local ignorado por Git:
`output/revision-humana-context-guard-calibracion-20260813.json`.

## Enforce local controlado

Al cumplir observe los criterios, se repitió la misma matriz localmente con
`CONTEXT_GUARD_MODE=enforce`:

| Métrica | Resultado |
|---|---:|
| Allow | 13 |
| Block | 9 |
| Errores | 0 |
| Timeouts | 0 |
| Falsos positivos | 0 |
| Falsos negativos | 0 |
| Latencia promedio | 814.64 ms |
| P95 | 1,115.79 ms |
| Máximo | 1,639.21 ms |

Los probes de timeout y error real del modelo bloquearon y no invocaron
recuperación, confirmando el comportamiento fail-closed.

## Criterio de salida

La calibración cumple 341/341 pruebas, 0 falsos positivos, 0 falsos negativos
y 0 timeouts. Este documento registra la validación previa al piloto; la
activación productiva requiere el bundle y la revisión de salud descritos en
el reporte operativo posterior.
