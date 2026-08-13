# Evaluación AI-first y ContextGuard — 2026-08-12

Esta evaluación fue local y de solo lectura contra `srch-libras-prod/libras-docs`.
No se desplegó, reindexó ni cambió ninguna configuración de Azure.

## Configuración confirmada

- `RETRIEVAL_STRATEGY=legacy`.
- `USE_LLM_EVIDENCE_VERIFIER=false`.
- `USE_AI_FIRST_EXPERIMENTAL` no está configurada en App Service y por tanto conserva el valor predeterminado `false`.
- `USE_LLM_GROUNDED_RESPONSE=true` permanece únicamente en la ventana controlada ya existente; no se modificó.
- Azure Search real: `srch-libras-prod.search.windows.net`, índice `libras-docs`, autenticación Entra ID.
- La A/B se ejecutó con `ALLOW_LOCAL_DOCUMENT_FALLBACK=false`; el reporte marca `fallback=false` para la recuperación.

## A/B OPS (12 preguntas)

Reporte detallado: `output/revision-humana-ai-first-20260812-final.json`.

| Variante | Promedio | p95 | Abstenciones del juez | Fallback | Evidencia final vacía |
|---|---:|---:|---:|---:|---:|
| legacy + redactor apagado | 3064.39 ms | 3267.34 ms | — | 0 | 3 |
| legacy + redactor encendido | 4033.39 ms | 5159.14 ms | — | 1 | 3 |
| AI-first + redactor apagado | 4768.51 ms | 5152.24 ms | 6 | 0 | 8 |
| AI-first + redactor encendido | 5032.84 ms | 5554.45 ms | 5 | 2 | 6 |

AI-first añade aproximadamente 1704 ms frente a legacy sin redactor y 999 ms frente a legacy con redactor. El JSON contiene la respuesta, candidatos seleccionados y fuentes por cada OPS.

### Clasificación de abstenciones AI-first

| Caso | Variantes | Clasificación | Evidencia observada |
|---|---|---|---|
| OPS-01 | AI-first apagado | Abstención correcta | El juez entregó un ID desconocido; el validador lo rechazó (`id_desconocido=1`). Con redactor encendido seleccionó los Readme correctos, pero el redactor falló y se usó fallback determinista. |
| OPS-02 | apagado/encendido | Evidencia insuficiente por recuperación | Los 12 candidatos sanitizados no contienen una evidencia directa de la tabla IRA en la versión solicitada; aparecen manuales fragmentados sin versión y un Readme que solo aporta índice/incidencias. |
| OPS-03 | apagado/encendido | Evidencia insuficiente por recuperación | El pool superior contiene fragmentos de `Manual de Relación DB`, pero no el fragmento de `ira_instancias_rutas_aut`; el juez no recibió una prueba directa suficiente. |
| OPS-06 | apagado/encendido | Evidencia insuficiente por recuperación | Azure devuelve explicación general de MSDTC y `Manual DTC`, no el script de reinstalación solicitado. |
| OPS-09 | apagado/encendido | Evidencia insuficiente por recuperación | El conjunto sanitizado no incluye `Ofuscación de datos.sql`; aparecen manuales DB y Readmes no pertinentes. No se añadió una regla para este ID. |
| OPS-10 | apagado/encendido | Rechazo excesivo del juez | Los candidatos `Ampliar Tiempo de Sesion.pdf`, páginas 1–4, contienen el procedimiento completo; el juez se abstuvo por `confianza_insuficiente=1`. |

OPS-08 y OPS-12 no son abstenciones del juez, pero muestran otro problema: el juez seleccionó fuentes y el clasificador determinista no las convirtió en evidencia final (`Manual DTC` p. 2; `Gestión de documentos` p. 10/`Portal Consultas` p. 30). Deben reportarse como fallos de validación/cobertura post-juez, no como motivo para bajar umbrales.

## Límite de versión en legacy

La consulta sin versión `¿Qué precauciones tomo antes de instalar una actualización?` devolvió `requires_version_context=true`, `ambiguous_release_version=26` y `solicita_contexto`.

Con `1.19.1.6`, la evidencia final fue únicamente:

- `Readme 1.19.1.6.pdf — Página 13` (preparación de componentes).
- `Readme 1.19.1.6.pdf — Página 12` (preparación de EvoDB).

No se citó `1.19.1.7` ni una página de incidencias. La regresión está en `tests/test_document_questions.py` y cubre exclusión de versiones vecinas y de un fragmento incidental.

## ContextGuard aislado

Reporte: `output/revision-humana-context-guard-20260812.json`.

Se ejecutó con `USE_CONTEXT_GUARD=true`, `CONTEXT_GUARD_MODE=observe`, `USE_AI_FIRST_EXPERIMENTAL=false`, `USE_LLM_EVIDENCE_VERIFIER=false` y `RETRIEVAL_STRATEGY=legacy`. El guard recibió únicamente el texto de la pregunta: no seleccionó documentos ni sustituyó al juez.

- 6 casos: 1 `allow`, 5 `block`, 0 errores de proveedor.
- Falsos positivos: 2 (`¿Cómo actualizo Evolution?` y `No funciona.` fueron bloqueadas como fuera de alcance).
- Falsos negativos: 0.
- Latencia media: 986.90 ms; p95: 1810.30 ms.
- JSON inválido: rechazado con `JSONDecodeError`.
- Timeout sintético con presupuesto de 2 s: detectado en 2003.96 ms; en `observe` la acción es continuar la recuperación.

## Recomendación

No activar AI-first ni el juez LLM en producción. La prioridad es mejorar recall/fragmentación de Azure para OPS-02/03/06/09 y corregir la aceptación post-juez de OPS-08/12. Para OPS-10 basta revisar la calibración/contrato del juez después de demostrar, con una matriz más amplia, que no se trata de una respuesta incompleta. ContextGuard debe permanecer en `observe` hasta reducir sus dos falsos positivos; no conviene usarlo para seleccionar evidencia.

No se generó bundle, commit ni despliegue en esta fase.
