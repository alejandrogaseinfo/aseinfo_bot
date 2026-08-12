# Resultados locales de calidad — 2026-08-12

## Estado de la suite

- Suite local completa después de la ampliación: **311/311 pruebas aprobadas**.
- La regresión de RAG-07 permanece cubierta: reinstalar MSDTC no se trata como
  una actualización de release.
- El evaluador acepta explícitamente la categoría `conceptual`.

## Línea base de `legacy`

La ejecución local inicial no fue válida como métrica porque el `.env` del
desarrollador apuntaba a un servicio/índice antiguo que no resuelve DNS. No se
modificó ese archivo.

Con una configuración de proceso que apunta, solo para lectura, al índice
productivo `srch-libras-prod/libras-docs`, usando Entra ID, vector de 512
dimensiones y `RETRIEVAL_STRATEGY=legacy`, el corpus inicial de 15 casos obtuvo:

| Métrica | Resultado |
|---|---:|
| Casos aprobados | 15/15 |
| Recall de evidencia | 100% |
| Abstención correcta | 100% |
| Solicitud de versión correcta | 100% |
| Latencia promedio | 3.03 s |
| Latencia p95 | 3.90 s |

El corpus se amplió a 29 casos con procedimientos, conceptos, diagnósticos,
paráfrasis, versiones explícitas y consultas insuficientemente especificadas.
Los negativos de secretos, inventario e inyección se mantienen en las pruebas
del handler: el evaluador de retrieval no debe medir esas barreras ejecutando
una búsqueda que ocurre después de ellas.

La ejecución final de los 29 casos con la misma configuración de lectura obtuvo:

| Métrica | Resultado |
|---|---:|
| Casos aprobados | 29/29 |
| Recall de evidencia | 100% |
| Abstención correcta | 100% |
| Solicitud de versión correcta | 100% |
| Resolución con evidencia | 100% |
| Latencia promedio | 3.37 s |
| Latencia p95 | 6.10 s |

La latencia máxima observada fue 7.92 s. Debe revisarse contra el presupuesto
aceptable para Teams antes de activar cualquier redactor.

## A/B local del redactor grounded

Se usaron las mismas cuatro preguntas y evidencias aprobadas en ambas variantes:

```text
legacy + USE_LLM_GROUNDED_RESPONSE=false
legacy + USE_LLM_GROUNDED_RESPONSE=true
```

- La salida determinista tuvo una latencia media de **2 ms**.
- El redactor tuvo una latencia media de **1.43 s** en las llamadas exitosas.
- Tres de cuatro llamadas devolvieron el contrato JSON válido.
- En la pregunta sobre la estructura completa de una tabla, el modelo se
  abstuvo al detectar que el fragmento solo describía la tabla y dos campos de
  relación; el fallback determinista se conserva.
- En una pregunta diagnóstica que las reglas locales clasificaron como
  insuficiente, el redactor no debe invocarse; se conserva la abstención local.
- En las preguntas procedurales restantes, la respuesta fue más concisa y
  citó únicamente las fuentes utilizadas.

Este resultado es prometedor, pero todavía no autoriza activar el redactor: la
muestra es pequeña y falta revisión humana sobre la matriz ampliada.

### A/B ampliado con evidencia real

Sobre las mismas 29 preguntas, el handler habría dejado **20 casos elegibles**
para el redactor: las consultas genéricas se detienen antes de recuperar y las
versiones o abstenciones permanecen deterministas. En una ejecución controlada
se observaron:

- **17/20** llamadas con contrato válido y respuesta redactada (85%).
- **2/20** abstenciones explícitas del modelo, ambas apropiadas porque el
  fragmento era solo un encabezado o portada sin pasos/definición suficiente.
- **1/20** fallback técnico por respuesta inválida o vacía; una repetición del
  mismo caso devolvió contrato válido, por lo que debe conservarse el fallback.
- Latencia media del redactor en llamadas exitosas: **1.45 s**; p95: **1.89 s**.
- Longitud media: **661 caracteres** en la salida determinista frente a
  **292 caracteres** en la salida redactada.

La conclusión provisional es mantener el redactor apagado hasta revisar las
respuestas con una persona y confirmar que la latencia combinada de recuperación
y redacción es aceptable para Teams.

## Auditoría de Azure AI Search en modo lectura

- Índice: `libras-docs` en `srch-libras-prod`.
- Documentos: 4,393 fragmentos.
- Campo `content_vector`: `Collection(Edm.Single)`, dimensión **512**.
- La consulta vectorial devuelve resultados y la consulta léxica recupera el
  manual de gestión de documentos.
- Producción reporta `RETRIEVAL_STRATEGY=legacy`, semantic ranker apagado,
  `REQUIRE_AZURE_SEARCH=true` y fallback local apagado.
- `USE_LLM_EVIDENCE_VERIFIER` y `USE_LLM_GROUNDED_RESPONSE` están ausentes en
  App Service y por defecto permanecen desactivados.

No se modificó el índice, la configuración productiva ni el despliegue.

## Bundle posterior al commit

- Revisión de código: `4ebaaa5`.
- Bundle: `output/libras-eval-bundle-20260812-4ebaaa5.zip`.
- SHA-256: `6369E2C104FEB437BFD399A2B168D146DEBF2A0D1CCEA4DCAEAA03D398AFB8E2`.
- El bundle contiene el código, las pruebas y el corpus, pero no contiene
  `.env`, `data` ni archivos de salida.
- La evaluación posterior al commit, ejecutada desde el bundle con la misma
  configuración de lectura, terminó en **29/29**.
