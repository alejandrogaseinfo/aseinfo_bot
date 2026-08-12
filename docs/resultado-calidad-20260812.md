# Resultados locales de calidad — 2026-08-12

## Estado de la suite

- Suite local completa después de la consolidación: **327/327 pruebas aprobadas**.
- La regresión de RAG-07 permanece cubierta: reinstalar MSDTC no se trata como
  una actualización de release.
- El evaluador acepta explícitamente la categoría `conceptual`.

## Repetición A/B instrumentada — 2026-08-12

La repetición posterior a la corrección general del router evitó que una
pregunta documental concreta se desviara a conversación antes de consultar
Azure AI Search. Se ejecutaron las mismas 12 preguntas con
`RETRIEVAL_STRATEGY=legacy`, índice `libras-docs`, Entra ID y fallback local
deshabilitado.

| Variante | Aprobación funcional | Latencia promedio | Latencia p95 |
|---|---:|---:|---:|
| Redactor apagado | 12/12 | 4.10 s | 6.67 s |
| Redactor encendido | 12/12 | 4.55 s | 7.93 s |

OPS-01, OPS-02, OPS-03, OPS-04, OPS-05, OPS-06, OPS-07, OPS-08, OPS-09,
OPS-10, OPS-11 y OPS-12 conservaron el resultado esperado. OPS-10 usó el
fallback determinista porque el borrador no preservaba todos los pasos. OPS-11
pidió la versión exacta y OPS-12 mantuvo la abstención por falta de evidencia
diagnóstica directa.

Reporte instrumentado: `output/revision-humana-redactor-20260812-postfix6.json`.
Esta corrida no modificó producción, no activó ningún LLM y no reindexó Azure.

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

### A/B posterior a validación de fuentes

> Este bloque conserva la primera repetición con el redactor encendido. La
> repetición vigente solicitada el 2026-08-12 se ejecutó con ambos LLM apagados
> y está en `output/revision-humana-redactor-20260812-postfix2.json`.

### Repetición posterior a correcciones generales — 2026-08-12

Se repitieron las mismas 12 preguntas contra `srch-libras-prod/libras-docs`,
con `legacy`, sin fallback local, `USE_LLM_EVIDENCE_VERIFIER=false` y
`USE_LLM_GROUNDED_RESPONSE=false`.

- **12/12** consultas ejecutadas sin error.
- **10** resueltas y **2** abstenciones: OPS-11 solicita contexto de versión y
  OPS-12 se abstiene por ausencia de cobertura diagnóstica directa.
- Latencia media: **3.15 s**.
- OPS-01 incluye explícitamente Evolution **1.24.1.2**.
- OPS-02 conserva advertencia de versión no confirmada (`version_confirmed=false`).
- OPS-04/07/10 recuperan procedimientos y parámetros desde evidencia del índice.
- OPS-06 responde desde el script real; OPS-09 mantiene el procedimiento SQL
  autorizado sin exponer código innecesario.
- OPS-08 combina validaciones de firewall, reglas DTC y Component Services.

Reporte vigente: `output/revision-humana-redactor-20260812-postfix3.json`.

El redactor grounded sigue apagado y no existe autorización de piloto.

### Revisión humana posterior — correcciones prioritarias

La repetición `postfix3` confirma que OPS-02 ya limita la respuesta a la tabla
IRA y sus campos, OPS-04 prioriza el manual de gestión documental, OPS-09
explica el procedimiento SQL autorizado sin exponer código y OPS-11 solicita la
versión exacta. OPS-10 permanece en abstención segura porque Azure devuelve
solo el encabezado del PDF, sin pasos accionables; no se debe completar ese
procedimiento hasta corregir la cobertura del documento en el índice.

Se repitieron las 12 preguntas operativas contra `srch-libras-prod/libras-docs`
con `RETRIEVAL_STRATEGY=legacy`, fallback local desactivado y el evaluador LLM
apagado. La comparación se ejecutó con el redactor apagado y encendido, sin
cambiar producción:

- **12/12** casos ejecutados sin error de proveedor ni fallback local.
- Latencia media: **4.21 s** sin redactor y **4.83 s** con redactor.
- **OPS-01** quedó limitado a `Readme 1.24.1.2.pdf — Página 5`; ya no cita
  `1.24.1.4` para el cambio histórico de jQuery.
- **OPS-02** prioriza `Manual de Relacion DB V1.2 .docx — Documento`, con
  `version_confirmed=false` y advertencia visible de que el manual no confirma
  la correspondencia con Evolution 1.24.1.3.
- **OPS-09** recupera `Ofuscación de datos.sql — Documento` y permite el
  procedimiento autorizado, sin abrir la puerta a credenciales, contraseñas,
  tokens o secretos.
- La salida del redactor conserva fuentes únicas y acota la respuesta a los
  fragmentos recibidos; la prueba unitaria rechaza una cita de Readme cuyo
  título no coincide con la versión afirmada.

Reporte detallado: `output/revision-humana-redactor-20260812-postfix.json`.

La activación sigue pendiente de revisión humana final y autorización para un
piloto controlado.

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

- Revisión de código: `0353b55`.
- Bundle: `output/libras-eval-bundle-20260812-0353b55.zip`.
- SHA-256: `EA3EAF2C177054947A298303C83A6F616DDD3037B19BF08549DEDF6A7774AEDE`.
- El bundle contiene el código, las pruebas y el corpus, pero no contiene
  `.env`, `data` ni archivos de salida.
- La evaluación posterior al commit, ejecutada desde el bundle con la misma
  configuración de lectura, terminó en **29/29**.
