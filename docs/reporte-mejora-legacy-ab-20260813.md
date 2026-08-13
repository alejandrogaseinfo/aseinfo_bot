# A/B de mejora general del flujo legacy — 2026-08-13

## Alcance y configuración

Se evaluaron las mismas 12 preguntas OPS contra el servicio real
`srch-libras-prod.search.windows.net`, índice `libras-docs`. La variante
productiva permaneció en `legacy`; AI-first solo se ejecutó dentro del
harness local y no se desplegó.

```text
RETRIEVAL_STRATEGY=legacy
USE_AI_FIRST_EXPERIMENTAL=false
USE_LLM_EVIDENCE_VERIFIER=false
USE_CONTEXT_GUARD=false
ALLOW_LOCAL_DOCUMENT_FALLBACK=false
REQUIRE_AZURE_SEARCH=true
```

El harness registró hashes, estados, títulos/metadatos de fuentes, tamaños y
métricas. No almacenó preguntas completas, prompts, secretos ni documentos
completos.

## Diagnóstico de OPS-02, OPS-03 y OPS-06

La corrida diagnóstica contra Azure confirmó un patrón común: Azure entrega
unión amplia y el problema estaba en el límite determinista entre candidatos
crudos, evidencia directa y fuente final; no era un error del servicio ni de
procedencia.

| Caso | Antes de la mejora | Patrón | Mejora general | Después |
|---|---|---|---|---|
| OPS-02 | 202 candidatos; ningún registro con identidad exacta `1.24.1.3`; el manual técnico se descartaba por el filtro de versión. | versión/procedencia, no ranking | Para consultas estructurales con versión explícita, excluir versiones vecinas y aceptar un documento autorizado sin versión solo si contiene el ancla técnica; marcarlo `version_confirmed=false` y advertir. | 202 crudos → 5 acotados → 3 con detalle estructural → 1 fuente: `Manual de Relacion DB V1.2 .docx`, no confirmada. |
| OPS-03 | 193 candidatos; 28 pasaban cobertura y el resultado incluía el manual correcto más una guía técnica tangencial. | cobertura del fragmento y ranking | Exigir ancla técnica y detalle local (`almacena`, `campos`, `relación` o `estructura`) antes del ranking final. | 193 crudos → 28 elegibles → 3 con detalle/ancla → 1 fuente: `Manual de Relacion DB V1.2 .docx`. |
| OPS-06 | 123 candidatos; la rama de scripts dejaba pasar archivos que solo compartían `vacaciones`. | cobertura del propósito del artefacto | Derivar conceptos sustantivos de cualquier consulta de script y exigir que todos aparezcan en título/descripción del artefacto; si la consulta no tiene sujeto, se conserva el fallback de scripts. | 123 crudos → 1 script con sujeto directo; 17 scripts rechazados por `script_subject_scope`; fuente única: `acc.proc_arreglar_vac_negativos.sql`. |

No se añadieron alias por ID o por pregunta. Se conservaron procedencia,
inyección, secretos/credenciales, límites de candidatos y control de versión.
No se modificaron índice, permisos, ContextGuard ni AI-first.

## Resultado A/B (primera corrida)

La calidad exige estado correcto, fuente esperada, versión compatible y cita
estructuralmente válida. Para recall se cuentan las 10 preguntas que esperan
resolver; OPS-11 y OPS-12 esperan abstención.

| Variante | Aprobadas | Recall de evidencia correcta | Abstenciones correctas | Falsos positivos | Falsos negativos | Azure/reintentos | Promedio | p95 | Máximo |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Legacy mejorado | 12/12 | 10/10 (100%) | 2/2 | 0 | 0 | 27 / 0 | 5.06 s | 11.00 s | 11.00 s |
| AI-first experimental | 3/12 | 3/10 (30%) | 0/2 | 2 | 6 | 36 / 0 | 5.96 s | 7.88 s | 7.88 s |

Los seis falsos negativos de AI-first fueron abstenciones o pérdida de
respuesta en OPS-02, OPS-03, OPS-06, OPS-08, OPS-09 y OPS-10. Los dos falsos
positivos fueron OPS-11 y OPS-12, que resolvieron sin la abstención esperada.
No hubo errores ni reintentos de Azure en ninguna variante.

### Fuentes finales

| Caso | Legacy mejorado | AI-first experimental |
|---|---|---|
| OPS-01 | `Readme 1.24.1.2.pdf` | Readme 1.24.1.4 + 1.24.1.2 (mezcla de versiones) |
| OPS-02 | `Manual de Relacion DB V1.2 .docx` (`version_confirmed=false`) | Sin fuente; abstención del juez |
| OPS-03 | `Manual de Relacion DB V1.2 .docx` | Sin fuente; abstención del juez |
| OPS-04 | Gestión de documentos, páginas 6/12/4/7 | Gestión de documentos, páginas 6/3 |
| OPS-05 | Gestión de documentos, páginas 4/5/10 | Gestión de documentos, páginas 4/5 |
| OPS-06 | `acc.proc_arreglar_vac_negativos.sql` | Sin fuente; abstención del juez |
| OPS-07 | Acciones de personal, página 18 | Acciones de personal, páginas 18/17/92 |
| OPS-08 | Instalación GenPlaAPI página 20 + Manual DTC páginas 4/5 | Manual DTC página 2; redactor terminó en abstención |
| OPS-09 | `Ofuscación de datos.sql` (2 fragmentos) | Sin fuente; abstención del juez |
| OPS-10 | Ampliar Tiempo de Sesión, páginas 1–4 | Sin fuente; validador rechazó por confianza |
| OPS-11 | Sin fuentes; `solicita_contexto` | Upgrades incompatibles; falso positivo |
| OPS-12 | Sin fuentes; `sin_evidencia` | Gestión de documentos/Portal Consultas; falso positivo |

## Latencia y consumo

Una segunda corrida idéntica se hizo para comprobar la variabilidad del
proveedor. En las 24 observaciones legacy, el promedio fue 4.98 s, p95 7.83 s
y máximo 11.00 s; la primera muestra contiene un único máximo de 11.00 s. La
segunda muestra fue 4.89 s promedio, 7.83 s p95 y 7.83 s máximo. El p95
agregado queda por debajo de 8 s, pero el máximo aislado debe vigilarse antes
de ampliar audiencia.

| Variante | Chat | Embeddings | Tokens observados | Relación de tokens |
|---|---:|---:|---:|---:|
| Legacy mejorado | 19 | 0 | 13,211 | 1.00× |
| AI-first experimental | 31 | 12 | 60,510 | 4.58× |

No se fija importe en USD porque depende del deployment y tarifa vigentes; los
contadores anteriores son la base para calcularlo.

## Validación local

- Suite completa: **348/348** (346 anteriores + 2 regresiones nuevas).
- `git diff --check`: correcto; solo quedaron advertencias normales de
  conversión LF/CRLF de Git.
- Regresiones añadidas: versión estructural de IRA, alcance por ancla local,
  selección de script por sujeto, y sus casos de preservación de versiones.

## Recomendación y estado de entrega

La mejora cumple el objetivo de calidad: OPS-02, OPS-03 y OPS-06 pasan, el
resultado sube de 9/12 a 12/12 y no aparecen falsos positivos ni mezcla de
versiones en legacy. AI-first queda apagado: su recall y consumo siguen siendo
claramente peores.

La latencia requiere observación: la muestra agregada tiene p95 7.83 s y un
máximo aislado de 11.00 s. No crear bundle ni desplegar todavía. Los cambios
funcionales están limitados a `src/azure_search.py`; las regresiones están en
`tests/test_document_questions.py`. La separación de commits se puede hacer
después de revisar este reporte, sin incluir los cambios no relacionados que
ya estaban pendientes en el árbol.

Artefactos:

- [A/B corrida 1](../tmp/evaluacion-ai-first-ab-20260813-legacy-improvement.json)
- [A/B corrida 2](../tmp/evaluacion-ai-first-ab-20260813-legacy-improvement-r2.json)
- [Log sanitizado corrida 1](../tmp/evaluacion-ai-first-ab-20260813-legacy-improvement.log)
- [Evaluador](../tmp/evaluate_ai_first_ab.py)
