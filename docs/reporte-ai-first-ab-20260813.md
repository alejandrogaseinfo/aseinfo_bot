# Reporte A/B AI-first — 2026-08-13

> Las secciones r6 y las corridas previas de este documento son **históricas / superadas**.
> El resultado vigente para el piloto es r8.

## Resultado vigente — r8

La evaluación `output/evaluacion-ai-first-direct-20260813-r8.json` ejecutó
las 12 preguntas OPS en modo lectura contra `srch-libras-prod/libras-docs`, sin
cambiar el índice, App Service, permisos, configuración productiva ni Teams.

| Control | Resultado |
|---|---|
| OPS-01 a OPS-10 | 10/10 respuestas con fuentes Azure validadas |
| OPS-11 | solicita la versión exacta; no emite fuentes |
| OPS-12 | abstención; el validador rechaza evidencia de navegación tangencial |
| Versiones | no mezcla releases; una fuente sin identidad expresa que no confirma la versión solicitada |
| Inyección y secretos | candidatos saneados antes del LLM; no se observaron exposiciones |
| Reintentos Azure Search | 0 |
| Latencia AI-first | media 6.04 s; p95 9.42 s; máximo 10.18 s |

El perfil candidato conserva un único LLM para responder y elegir IDs opacos,
pero utiliza la recuperación Azure con controles de procedencia y versiones
como conjunto de candidatos. Esto evita la segunda consulta amplia, que había
introducido falsas citas y latencia adicional. Permanecen los interruptores de
producción sin cambios durante la evaluación (`USE_AI_FIRST_EXPERIMENTAL=false`,
ContextGuard y juez LLM desactivados). Esta preparación queda autorizada para
un piloto controlado, sujeto a los criterios de rollback siguientes.

## Criterios de rollback del piloto

- Fuente/cita incorrecta o afirmación inventada confirmada: rollback inmediato.
- Error técnico AI-first: rollback inmediato.
- p95 superior a 12 s en al menos 20 consultas normales: rollback.
- Respuesta superior a 20 s: investigar; rollback si se repite.
- Solicitud de contexto o abstención incorrecta repetida: pausar y hacer
  rollback si se confirma.

## Revisión humana aplicada (r8)

La reevaluación `output/evaluacion-ai-first-direct-20260813-r8.json` conserva
los 12 comportamientos esperados e incorpora tres correcciones de presentación:

- OPS-01 identifica expresamente Evolution 1.24.1.2, jQuery 3.7.2 y el
  reemplazo de 1.12.4 desde el Readme 1.24.1.2 (página 5).
- OPS-02 responde primero sobre `ira_instancias_rutas_aut` y sus relaciones
  `ira_codrau` / `ira_codigo_entidad`; mantiene la advertencia de que el Manual
  de Relación DB no confirma la compatibilidad con Evolution 1.24.1.3.
- OPS-09 expresa la anonimización para la persona usuaria (valores aleatorios
  en tablas temporales y campos específicos) sin copiar SQL ni nombres internos.

AI-first r8: **12/12 aprobadas**, media 6.04 s, p95 9.42 s y máximo 10.18 s.
Las variaciones frente a r6 se deben a la latencia de los servicios externos
durante cada ejecución.

---

## Historial superado — r6 y corridas anteriores

## Alcance y configuración

Se ejecutaron las mismas 12 preguntas OPS contra Azure AI Search real:

- servicio: `srch-libras-prod.search.windows.net`
- índice: `libras-docs`
- `RETRIEVAL_STRATEGY=legacy`
- `USE_AI_FIRST_EXPERIMENTAL=false` en la configuración productiva; la variante AI-first se habilitó únicamente dentro del proceso local de evaluación
- `USE_LLM_EVIDENCE_VERIFIER=false`
- `USE_CONTEXT_GUARD=false`
- `ALLOW_LOCAL_DOCUMENT_FALLBACK=false`
- `REQUIRE_AZURE_SEARCH=true`

El evaluador almacenó solo hashes de solicitud, estados, metadatos de fuentes, tamaños de respuesta y métricas. No almacenó preguntas completas, prompts, secretos ni fragmentos completos.

## Resultado resumido

| Variante | Calidad | Tiempo medio | p95 interpolado | Máximo | Consultas Azure | Reintentos | Abstenciones juez | Fallback determinista |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Legacy | 9/12 | 4.67 s | 6.61 s | 7.06 s | 27 (2.25/pregunta) | 0 | 0 | 0 |
| AI-first | 3/12 | 5.36 s | 6.30 s | 6.64 s | 36 (3.00/pregunta) | 0 | 6 | 6 |

En términos semánticos, legacy tuvo 1 falso negativo de cobertura (debía resolver y se abstuvo: OPS-02) y 0 falsos positivos de seguridad. AI-first tuvo 7 falsos negativos de cobertura (OPS-01, OPS-02, OPS-03, OPS-06, OPS-08, OPS-09 y OPS-10) y 2 falsos positivos de afirmación (OPS-11 y OPS-12 resolvieron cuando debían abstenerse). Los campos históricos `false_positives`/`false_negatives` del JSON no se interpretan literalmente; esta clasificación los normaliza según el estado esperado de cada caso.

## Métricas por etapa

Las métricas son promedio / p95 / máximo; `n` es el número de eventos observados.

| Etapa | Legacy | AI-first |
|---|---:|---:|
| Total (12) | 4,667.97 / 6,611.88 / 7,057.24 ms | 5,359.34 / 6,297.66 / 6,640.21 ms |
| Intención | n=7: 896.57 / 1,498.41 / 1,760.71 ms | n=12: 777.24 / 1,045.62 / 1,056.94 ms |
| Cada consulta Azure Search | n=27: 1,223.53 / 2,827.02 / 3,341.60 ms | n=36: 933.22 / 2,659.96 / 2,969.09 ms |
| Recuperación completa | n=11: 3,375.73 / 5,071.15 / 5,591.89 ms | n=12: 3,109.30 / 3,554.81 / 3,721.89 ms |
| Ranking determinista | n=11: 48.79 / 120.00 / 156.66 ms | no aplica |
| Deduplicación | n=9: 4.81 / 8.10 / 8.40 ms | no aplica |
| Sanitización | no aplica | n=12: 7.57 / 14.10 / 14.23 ms |
| Juez LLM | no aplica | n=12: 973.08 / 1,264.84 / 1,314.30 ms |
| Validador local | no aplica | n=12: 0.05 / 0.08 / 0.08 ms |
| Redactor | n=9: 911.66 / 1,234.66 / 1,284.29 ms | n=6: 987.81 / 1,450.64 / 1,567.61 ms |

ContextGuard no participó porque permaneció desactivado. Azure Search no registró errores ni reintentos.

## Resultado por caso y fuentes elegidas

| Caso | Legacy | AI-first |
|---|---|---|
| OPS-01 | Aprobado — `Readme 1.24.1.2.pdf` | Falla de validador — ID desconocido; abstención |
| OPS-02 | Falla de recuperación — sin evidencia | Falla de juez — abstención sin selección |
| OPS-03 | Falla de ranking — añadió `Guía de temas tecnicos Evolution.docx` | Falla de juez — abstención |
| OPS-04 | Aprobado — páginas 6, 12, 4 y 7 de Gestión de documentos | Aprobado — página 6 de Gestión de documentos |
| OPS-05 | Aprobado — páginas 4, 5 y 10 de Gestión de documentos | Aprobado — páginas 4 y 5 de Gestión de documentos |
| OPS-06 | Falla de ranking — `acc.proc_arreglar_vac_negativos.sql` | Falla de juez — abstención |
| OPS-07 | Aprobado — página 18 de Acciones de personal | Aprobado — páginas 18, 17 y 92 de Acciones de personal |
| OPS-08 | Aprobado — instalación GenPlaAPI y Manual DTC, páginas 20/4/5 | Falla de redactor — seleccionó Manual DTC página 2, pero terminó en abstención |
| OPS-09 | Aprobado — `Ofuscación de datos.sql` | Falla de juez — abstención |
| OPS-10 | Aprobado — páginas 1–4 de Ampliar Tiempo de Sesión | Falla de validador — confianza insuficiente |
| OPS-11 | Abstención correcta — sin fuentes | Falso positivo de ranking — seleccionó tres Upgrades incompatibles |
| OPS-12 | Abstención correcta — sin fuentes | Falso positivo de ranking — seleccionó Gestión de documentos y Portal Consultas |

Las citas que sí se emitieron cumplieron la validación estructural de título, ubicación y fragmento; OPS-11/OPS-12 muestran que esa validez estructural no basta para garantizar pertinencia semántica.

## Consumo aproximado

| Variante | Llamadas chat | Llamadas embedding | Tokens totales observados |
|---|---:|---:|---:|
| Legacy | 19 | 0 | 13,312 |
| AI-first | 30 | 12 | 59,724 |

AI-first consumió 4.49× los tokens observados, 1.58× las llamadas de chat y añadió una embedding por pregunta. El reporte no fija USD porque el precio depende del deployment/proveedor; el costo esperado se calcula con esos contadores y la tarifa vigente del recurso.

## Clasificación de fallos

- **Recuperación:** legacy OPS-02.
- **Ranking:** legacy OPS-03/OPS-06; AI-first OPS-11/OPS-12.
- **Juez LLM:** AI-first OPS-02/OPS-03/OPS-06/OPS-09 (abstención sin selección válida).
- **Validador:** AI-first OPS-01 (`id_desconocido`) y OPS-10 (`confianza_insuficiente`).
- **Redactor:** AI-first OPS-08.
- **Seguridad:** no se observaron permisos peligrosos en las 12 preguntas; los dos falsos positivos de AI-first fueron de pertinencia/abstención, no de exposición de secretos.

## Recomendación

No activar AI-first ni cambiar producción. En esta matriz, AI-first no supera a legacy: reduce ligeramente el p95, pero aumenta el tiempo medio, hace tres consultas por pregunta, multiplica el consumo de tokens y reduce la calidad de 9/12 a 3/12. Antes de otra medición deben resolverse de forma general el contrato de IDs/requisitos del juez, la selección de evidencia para abstenciones y la validación de pertinencia/versiones; no se recomienda añadir reglas por OPS.

Artefactos: [JSON A/B](../tmp/evaluacion-ai-first-ab-20260813.json) · [log sanitizado](../tmp/evaluacion-ai-first-ab-20260813.log) · [evaluador](../tmp/evaluate_ai_first_ab.py).

## Actualización r13 — propagación de advertencia de versión (2026-08-14)

La revisión corrigió únicamente el transporte de `version_warning` desde el
contrato JSON del juez hasta `AIFirstDirectResponse`, `BotDecision` y el
formateo final. El validador continúa exigiendo una advertencia para
`version_status=no_confirmada`; no se modificaron el modelo ni la recuperación.

La A/B de 12 casos confirmó OPS-02 como respuesta válida con la advertencia
explícita de que la fuente no confirma compatibilidad con la versión
consultada. Suite: 418 pruebas OK. El artefacto JSON vigente es
`output/evaluacion-ai-first-version-warning-20260814.json`.
