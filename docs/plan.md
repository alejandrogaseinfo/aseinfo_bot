# Plan de mejora del flujo RAG y redacción de Libras

## Objetivo

Mejorar la calidad de las respuestas documentales de Libras manteniendo el
alcance actual: Microsoft Teams, Azure AI Search y SharePoint/OneDrive
autorizado.

El flujo objetivo es:

```text
Pregunta
  ↓
Intención y alcance
  ↓
Azure AI Search híbrido (léxico + vectorial)
  ↓
Filtros esenciales
  ↓
Ranking determinista
  ↓
LLM redactor usando las mejores evidencias
  ↓
Respuesta con enlaces o abstención
```

## Estado de partida y restricciones

- Producción permanece en `RETRIEVAL_STRATEGY=legacy`.
- `USE_LLM_EVIDENCE_VERIFIER=false` se mantiene apagado.
- `USE_LLM_GROUNDED_RESPONSE=false` se mantiene apagado hasta aprobar la
  evaluación.
- No se promueve `v2` como parte de esta primera entrega.
- No se agregan reglas específicas para RAG-09 o RAG-10 salvo una regresión
  reproducible que obligue a corregir una política general.
- No se despliega ni se cambia configuración productiva sin autorización
  explícita.
- No se agregan nuevas fuentes documentales, permisos globales ni recursos de
  Azure.

La línea base funcional actual es la suite local aprobada y la evaluación de
Azure registrada en `docs/contexto-actual.md`. Antes de modificar código se
debe conservar una copia de los resultados de la línea base.

## Fase 0 — Congelar y revisar cambios locales

### Actividades

- Confirmar el commit de trabajo y registrar los cambios locales pendientes.
- Revisar `git diff` completo antes de agregar nuevas modificaciones.
- Separar mentalmente los cambios funcionales de los cambios de documentación
  y pruebas. No desplegar mientras ambos grupos no estén revisados.
- Identificar explícitamente los cambios actuales, incluyendo:
  `src/grounded_response.py`, `src/handler.py`, `src/config.py`, el evaluador,
  el corpus, las pruebas nuevas y `docs/plan.md`.
- Ejecutar la suite completa:

  ```powershell
  python -m unittest discover -s tests -v
  ```

- Ejecutar `git diff --check`.
- No crear todavía un bundle ni ejecutar despliegues.

### Salida

- Inventario revisado de cambios locales.
- Ninguna modificación en producción.

## Fase 1 — Corpus ampliado y línea base local

Esta fase precede a cualquier cambio de recuperación o redacción. El objetivo
es disponer de preguntas representativas para medir si una mejora realmente
ayuda.

### Actividades

- Ampliar `tests/corpus-recuperacion-calidad.json` hasta 25–40 preguntas
  representativas.
- Incluir procedimientos, conceptos, diagnósticos, versiones explícitas,
  versiones ambiguas, paráfrasis, preguntas sin evidencia, fuentes no
  autorizadas, secretos e inyección documental.
- Mantener RAG-07, RAG-09 y RAG-10 como regresiones generales, no como reglas
  aisladas.
- Ejecutar el corpus con el comportamiento actual de `legacy`.
- Registrar recall, abstención, solicitudes de contexto, documentos
  recuperados y latencia.

### Criterio de salida

- Existe una matriz revisada de 25–40 preguntas.
- Existe una línea base reproducible de `legacy`.
- Las expectativas de `evidence`, `sin_evidencia` y `solicita_contexto` están
  validadas antes de cambiar la recuperación o activar el redactor.

## Fase 1B — Auditoría paralela de Azure AI Search

Esta fase puede ejecutarse en paralelo con la evaluación local y no bloquea la
mejora ni la prueba local de `grounded_response.py`.

### Actividades

- Desde SSH → Application o una consola con permisos de lectura, inspeccionar
  el esquema de `libras-docs`.
- Confirmar que existen `content_vector`, `content`, `title`, `source_url`,
  `folder_path`, `drive_id` y los metadatos necesarios para procedencia.
- Confirmar la dimensión real de `content_vector`.
- Compararla con `OPENAI_EMBEDDING_DIMENSIONS` usado por la ingesta y por la
  aplicación.
- Confirmar que los fragmentos recientes tienen vector y que no hay una mezcla
  accidental de dimensiones.
- Ejecutar una consulta de diagnóstico y guardar únicamente métricas y títulos
  autorizados, no secretos:

  ```powershell
  python src\debug_retrieval.py --question "¿Cómo se administran los documentos en Evolution?"
  ```

### Criterio de salida

- La dimensión del índice, la ingesta y la consulta coincide.
- Se puede identificar si la búsqueda vectorial está funcionando o si está
  fallando y el sistema está usando únicamente la ruta léxica.
- Si es necesaria una reconstrucción, se hará primero sobre un índice candidato
  separado; no se ejecutará `--reset-index` sobre producción sin aprobación.

## Fase 2 — Comparación A/B local del redactor

Esta es la primera prueba funcional de la mejora de respuestas. Se ejecuta sin
Azure remoto, sin despliegue y sin modificar configuración productiva.

### Variantes

```text
legacy + USE_LLM_GROUNDED_RESPONSE=false
legacy + USE_LLM_GROUNDED_RESPONSE=true
```

### Actividades

- Ejecutar las mismas preguntas y las mismas evidencias en ambas variantes.
- Comparar claridad, completitud, fidelidad a los fragmentos, fuentes citadas,
  abstenciones y latencia.
- Verificar que un timeout, error o JSON inválido del modelo conserva la
  respuesta determinista.
- Verificar que las consultas con versión explícita y solicitudes de seguridad
  mantienen sus rutas deterministas.

### Criterio de salida

- El redactor mejora la claridad sin agregar afirmaciones no sustentadas.
- Las fuentes visibles son únicamente las utilizadas.
- El fallback determinista funciona.
- Se decide si vale la pena continuar con una prueba piloto del redactor.

## Fase 3 — Ampliar la matriz y revisar calidad humana

Si el A/B inicial es prometedor, ampliar la matriz con nuevas formulaciones y
casos reales antes de modificar la recuperación.

### Actividades

- Añadir preguntas naturales no literales y consultas con varias evidencias.
- Revisar manualmente una muestra de respuestas apagadas y encendidas.
- Registrar observaciones de utilidad, fidelidad, enlaces y latencia.
- No crear reglas especiales para un único RAG; corregir solo patrones
  generales y medibles.

### Criterio de salida

- Existe una comparación documentada entre ambas variantes.
- Se conocen las categorías donde el redactor mejora y donde debe hacer
  fallback.
- La matriz es suficientemente amplia para decidir sobre un piloto.

## Fase 4 — Experimento opcional de búsqueda híbrida real

Esta fase es un experimento, no una obligación inmediata. La ruta `legacy` ya
tiene búsqueda léxica y vectorial de apoyo; primero debe demostrarse que una
unión permanente mejora recall sin degradar latencia o abstención.

### Actividades

- Ejecutar siempre una pasada léxica y una pasada vectorial con límites y
  timeout independientes.
- Unir candidatos por `id` y conservar el mejor rango de cada pasada.
- Mantener diversidad por documento para que un manual grande no monopolice el
  pool.
- Aplicar un ranking determinista sobre cobertura, título, contexto de carpeta,
  rango léxico y rango vectorial.
- Mantener el pool amplio para recuperación y reducirlo antes del redactor a
  las mejores evidencias.
- Mantener el semantic ranker opcional; no hacerlo requisito de la primera
  entrega.
- Comparar la variante candidata con `legacy` usando exactamente el mismo
  corpus.

### Criterio de salida

- Las paráfrasis recuperan el mismo documento que la formulación literal.
- No disminuye la abstención correcta.
- RAG-07 y RAG-09 conservan su comportamiento.
- La latencia p95 permanece dentro del presupuesto definido para Teams.

## Fase 5 — Convertir cobertura literal en señal blanda para preguntas normales

Para procedimientos, manuales y conceptos, la coincidencia literal de todos
los términos no debe ser un requisito absoluto. Debe ser una señal del ranking
y de la suficiencia de evidencia.

### Filtros que permanecen estrictos

- Secretos, credenciales y datos confidenciales.
- Inyección documental.
- Procedencia fuera de las bibliotecas o carpetas autorizadas.
- Versión incompatible cuando el usuario indicó una versión.
- Ausencia clara de candidatos útiles.
- Solicitud de contexto cuando hay versiones incompatibles de un release.

### Cambios previstos

- Revisar `_has_minimum_content_coverage()` en `src/azure_search.py` para que
  no descarte automáticamente una paráfrasis válida por falta de coincidencia
  literal.
- Revisar `_evidence_covers_requested_facet()` en `src/classification.py` para
  reservar las comprobaciones más estrictas a facetas de riesgo o solicitudes
  que realmente requieren un dato explícito.
- Mantener un umbral mínimo de relevancia y una política de abstención cuando
  no exista evidencia razonablemente relacionada.
- No añadir alias exclusivos para preguntas concretas; las señales deben ser
  lingüísticas y reutilizables.

### Criterio de salida

- Aumenta el recall de paráfrasis y conceptos.
- No aparecen enlaces tangenciales en preguntas sin evidencia.
- No se degrada la seguridad, la procedencia ni el control de versiones.

## Fase 6 — Consolidar el redactor como última etapa

El redactor de `src/grounded_response.py` debe recibir únicamente las mejores
fuentes que ya pasaron procedencia, inyección, versión y ranking.

### Actividades

- Seleccionar primero la evidencia final de forma determinista.
- Invocar después `generate_grounded_response()`.
- Evitar que `classify_case()` sobrescriba una respuesta documental ya
  redactada.
- Mantener respuestas deterministas para consultas de versión exacta y rutas de
  seguridad.
- Exigir JSON válido con respuesta y IDs de fuente.
- Rechazar IDs desconocidos, respuestas vacías, respuestas excesivamente
  largas, JSON inválido o errores del proveedor.
- Conservar el fallback determinista cuando el LLM falle o exceda el timeout.

### Criterio de salida

- Cada respuesta generada cita únicamente fuentes entregadas al modelo.
- El redactor no puede ampliar el alcance ni decidir permisos o versiones.
- Una falla del modelo no cambia el resultado seguro del bot.
- La salida es más clara en revisión humana que la respuesta determinista
  equivalente.

Las actividades de esta fase se ejecutan solo si la comparación A/B confirma
que el redactor mejora la experiencia.

## Fase 7 — Consolidación antes de cualquier despliegue

Esta fase es obligatoria. No se debe probar Azure con un árbol local ambiguo ni
generar un bundle antes de consolidar los cambios.

### Actividades

- Revisar nuevamente `git diff` completo.
- Separar cambios funcionales de documentación y confirmar que cada cambio
  pertenece al plan.
- Ejecutar `git diff --check`.
- Ejecutar la suite local completa.
- Ejecutar el corpus actualizado localmente.
- Guardar los resultados de la comparación A/B y de la matriz.
- Crear un commit en español con el alcance aprobado.
- Generar el bundle desde ese commit.
- Registrar la revisión o identificador del bundle.

### Criterio de salida

- El árbol de trabajo queda limpio o contiene únicamente cambios explícitamente
  aprobados.
- El commit, el bundle y los resultados de pruebas son trazables.
- Todavía no se ha cambiado producción; solo queda preparado el artefacto.

## Fase 8 — Validación en Azure sin activar usuarios

### Actividades

- Construir el paquete de código con una revisión identificable.
- Desplegar primero con el redactor apagado, solo si existe autorización para
  actualizar el App Service.
- En SSH → Application, comprobar configuración, versión y dependencias.
- Ejecutar `/healthz` y `/readyz`.
- Ejecutar una consulta real de recuperación contra `libras-docs`.
- Revisar logs de timeout, errores de embeddings, procedencia y cantidad de
  fuentes.

### Configuración inicial segura

```text
LIBRAS_ENV=production
REQUIRE_AZURE_SEARCH=true
ALLOW_LOCAL_DOCUMENT_FALLBACK=false
RETRIEVAL_STRATEGY=legacy
USE_LLM_EVIDENCE_VERIFIER=false
USE_LLM_GROUNDED_RESPONSE=false
```

`/readyz` es una comprobación de configuración; debe complementarse con una
consulta real porque no garantiza por sí solo que Azure AI Search o OpenAI
respondan correctamente.

## Fase 9 — Piloto controlado en Teams

Solo después de aprobar la matriz y la validación de Azure:

- Activar `USE_LLM_GROUNDED_RESPONSE=true` para una audiencia piloto o una
  ventana controlada.
- Mantener `RETRIEVAL_STRATEGY=legacy`.
- Mantener `USE_LLM_EVIDENCE_VERIFIER=false`.
- Probar preguntas positivas, negativas, RAG-07, RAG-09, secretos e
  inyección.
- Comparar las respuestas con la línea base.
- Apagar inmediatamente la bandera si aparecen afirmaciones no sustentadas,
  fuentes incorrectas o latencia inaceptable.

## Criterios de promoción

No promover el redactor a una audiencia amplia hasta cumplir todos estos puntos:

- Suite local completa en verde.
- Cero regresiones en RAG-07, RAG-09 y RAG-10.
- Procedencia autorizada en el 100% de las respuestas.
- Abstención y solicitud de contexto correctas en la matriz.
- Cero afirmaciones no sustentadas detectadas en revisión.
- Enlaces válidos a las fuentes realmente utilizadas.
- Latencia p95 aceptable para Teams.
- Fallback determinista probado con timeout y error del modelo.
- Rollback documentado: volver `USE_LLM_GROUNDED_RESPONSE=false`.

## Fuera de alcance

- Promover `v2` completa.
- Activar `USE_LLM_EVIDENCE_VERIFIER`.
- Incorporar ClickUp, GitHub, Jira o MCP.
- Cambiar las bibliotecas autorizadas.
- Reindexar producción sin copia o índice candidato y aprobación.
- Crear recursos adicionales de Azure sin una necesidad operativa demostrada.

## Estado de seguimiento

- [x] Línea base congelada en `docs/resultado-calidad-20260812.md`.
- [x] Corpus ampliado a 29 casos y línea base `legacy` ejecutados en modo de
  lectura contra `libras-docs`.
- [x] Comparación A/B local del redactor ejecutada con evidencias controladas.
- [x] A/B ampliado sobre 29 preguntas; quedan pendientes revisión humana y
  decisión de activación.
- [x] Regresión de citas, IRA versionada y procedimiento SQL de ofuscación
  corregida; A/B operativo de 12 preguntas repetido contra Azure.
- [x] Dimensión y cobertura vectorial del índice verificadas en paralelo.
- [ ] Matriz ampliada y revisión humana completadas.
- [ ] Experimento híbrido ejecutado o descartado con métricas.
- [ ] Cobertura literal suavizada para preguntas normales, si la matriz lo
  justifica.
- [ ] Redactor consolidado como etapa final, si la matriz lo aprueba.
- [x] `git diff` revisado y cambios funcionales/documentales separados.
- [x] Suite completa y corpus ejecutados después de la consolidación.
- [x] Commit `0353b55` creado y bundle generado; la evaluación posterior al
  commit terminó en 29/29.
- [ ] Validación real desde SSH → Application completada.
- [ ] Despliegue con redactor apagado autorizado.
- [ ] Piloto Teams autorizado.
- [ ] Activación del redactor aprobada.
