# Implementación de recuperación híbrida sobre la estrategia legacy

> Estado: **diseño aprobado para iniciar implementación local**. Fecha:
> 2026-08-11. Este anexo implementa la fase 2 de
> [plan-correccion-calidad-libras.md](plan-correccion-calidad-libras.md); no
> crea una ruta de producto ni un índice alternos.

## Propósito

Mejorar la selección de evidencia de `libras-docs` sin modificar el índice ni
su infraestructura. Azure AI Search seguirá recuperando candidatos y Libras
conservará decisiones deterministas de seguridad e identidad. Un reranker
evaluará un conjunto intermedio, acotado y trazable, para que el modelo que
redacta la respuesta reciba solo entre tres y cinco evidencias citables.

La razón del cambio es que la ruta `legacy` actual obtiene candidatos útiles
junto a otros parcialmente relacionados. Sus filtros de cobertura y el umbral
de relevancia pueden descartar candidatos secundarios antes de compararlos
contra los mejores. En los diagnósticos recientes:

- la consulta sobre jQuery contiene la evidencia correcta de `jQuery 3.7.2` y
  su reemplazo de `1.12.4`, además de resultados incidentales;
- la consulta estructural de IRA para `1.24.1.3` debe preferir el Manual de
  Relación DB y conservar `version_confirmed=false`, en vez de sustituir una
  respuesta técnica por un Readme de la misma versión.

## Restricciones no negociables

- Mantener `RETRIEVAL_STRATEGY=legacy` durante esta implementación.
- Mantener `AZURE_SEARCH_USE_SEMANTIC=false`.
- No reindexar, no cambiar embeddings, modelos, SKU, fuentes autorizadas ni el
  manifiesto de Teams.
- No desplegar a `app-libras-prod` hasta aprobar la evaluación y la estrategia
  de promoción explícitamente.
- Mantener la abstención: si no hay evidencia directa verificable, la salida es
  `sin_evidencia`, sin enlaces tangenciales.
- Mantener los límites de llamada y los timeouts actuales.

El backend de referencia es `app-libras-prod`; al iniciar este plan,
`/healthz` y `/readyz` están sanos y la suite local de referencia registra 278
pruebas exitosas.

## Estado actual que se preserva

`src/azure_search.py` ya recupera hasta `CANDIDATE_POOL_SIZE=100` en pases
léxicos y, como fallback, vectoriales. Combina resultados, limita tres
fragmentos por documento y ejecuta `_rerank_records`. La ruta final aplica un
umbral relativo de relevancia y devuelve hasta tres evidencias.

No es aún híbrida de extremo a extremo: si un candidato léxico supera la
cobertura mínima, la consulta vectorial no se realiza. Además, los filtros de
cobertura se usan como puerta previa al ranking; por ello un candidato
secundario potencialmente útil puede no llegar a ser comparado.

`src/debug_retrieval.py` expone dos vistas distintas que no deben confundirse:

- `candidatos_crudos_de_azure` contiene los primeros resultados de una única
  búsqueda léxica de diagnóstico;
- `evidencia_que_recibe_el_bot` contiene solo las evidencias seleccionadas por
  Libras y es la vista que llega a la generación.

La primera vista se ampliará para explicar las etapas reales de `legacy`; no
se enviarán los candidatos crudos al modelo final.

## Decisión sobre el prompt evaluador propuesto

El prompt recibido como muestra para `ira_instancias_rutas_aut` es útil como
**referencia de evaluación**, pero no se integrará tal cual. Demuestra que un
modelo puede seleccionar correctamente el Manual de Relación DB aun cuando
Azure rankea documentos incidentales por encima. También demuestra que la
respuesta debe limitarse a lo que el fragmento sustenta: propósito de la tabla
y campos de relación, no una estructura completa no documentada.

No se puede usar directamente porque su entrada contiene candidatos crudos y
no incluye los metadatos necesarios para las reglas de seguridad e identidad.
Tampoco se adopta su solicitud de `reasoning.encrypted_content`: Libras no
necesita ni debe almacenar razonamiento del modelo para recuperar evidencia.

El contrato local del evaluador será el siguiente:

1. Recibe únicamente candidatos que ya pasaron los filtros duros.
2. Cada candidato incluye `candidate_id`, título, fragmento acotado, enlace y
   metadatos de trazabilidad permitidos; nunca vectores ni secretos.
3. Los textos se serializan como datos delimitados y la instrucción declara
   que no son órdenes.
4. Devuelve solo JSON. Un veredicto solo puede usar `candidate_id` y
   requisitos presentes en listas permitidas.
5. Libras valida el JSON, vuelve a comprobar los límites y falla cerrado ante
   error, salida malformada, inyección o falta de cobertura directa.

Ejemplo de salida aceptada:

```json
{
  "verdicts": [
    {
      "candidate_id": "manual-db-v12-chunk-0",
      "requirements": ["estructura_ira"],
      "directo": true
    }
  ]
}
```

## Arquitectura objetivo

```text
Azure AI Search: unión de candidatos léxicos y vectoriales acotados
  -> normalización y diversidad por documento
  -> filtros duros deterministas
  -> pool elegible de 10 a 20 candidatos
  -> reranker/verificador de evidencia
  -> 3 a 5 evidencias directas, diversas y trazables
  -> clasificación, respuesta fundamentada o abstención
```

### Etapa 1: candidatos de Azure controlados

Conservar los pases existentes y su deduplicación por `id`. Para poder evaluar
recuperación híbrida real, el pase vectorial debe poder contribuir al conjunto
cuando sea útil, no solo cuando el léxico no tenga cobertura. El resultado se
limitará globalmente antes de cualquier evaluación posterior; el valor inicial
propuesto es 40--60 candidatos diversificados y nunca una lista abierta de 130
o más resultados para el modelo.

### Etapa 2: filtros duros que no puede relajar el reranker

| Regla | Motivo | Comportamiento |
|---|---|---|
| `source_system=sharepoint`, HTTPS, `drive_id` y `folder_path` autorizados | Seguridad de procedencia | Rechazo fail-closed. |
| Archivo explícito solicitado | Identidad documental | Solo el archivo cuyo título coincide. |
| Readme, release, hotfix o requisitos con versión explícita | Exactitud de versión | Coincidencia de versión exacta; sin fallback. |
| Identificador técnico compuesto solicitado | Exactitud técnica | Coincidencia exacta del identificador, no una mención incidental. |
| País sensible solicitado | Exactitud normativa | No mezclar evidencia de otro país ni texto genérico. |
| Portadas, índices y tablas de contenido para una pregunta sustantiva | Calidad de evidencia | No son citables ni entran al reranker. |
| Contenido con patrón de inyección documental | Defensa en profundidad | Excluir, registrar motivo y no enviar a ningún modelo. |

La procedencia autorizada no basta contra instrucciones maliciosas introducidas
en un documento autorizado. El contenido documental se tratará siempre como
datos delimitados, nunca como instrucciones. El evaluador solo podrá devolver
IDs de candidatos de una lista permitida y su salida será validada antes de
usarla.

El caso de consulta estructural con versión es la única excepción documentada:
si no existe evidencia con la versión exacta, puede mantenerse un manual que
contenga el identificador técnico exacto. Debe salir con
`version_confirmed=false` y `fallback_reason=version_no_confirmada`; no puede
usarse para una consulta Readme/release.

### Etapa 3: elegibilidad y reranking

Las reglas actuales de cobertura léxica, proximidad entre acción y sujeto,
sinónimos, coincidencias de frases, posición Azure y umbral de relevancia son
señales de relevancia, no reglas de seguridad. Se conservarán como señales del
reranker y como criterios de desempate, en lugar de descartar todos los casos
que no superen una coincidencia literal.

El pool para evaluar será de 10--20 candidatos después de los filtros duros y
de la diversidad documental. Debe incluir los mejores candidatos de Azure y
una cuota de candidatos secundarios con señales complementarias. Ningún
documento podrá ocupar más de tres posiciones; el límite definitivo por
documento se ajustará al seleccionar evidencia.

La primera implementación reutilizará el ranking determinista existente como
baseline. Si se habilita el evaluador de evidencia ya disponible en
`src/evidence_verifier.py`, se usará únicamente para verificar cobertura de
requisitos sobre esos candidatos acotados, con temperatura cero, JSON validado
y fallo cerrado. No se cambia el modelo configurado ni se habilita la
configuración semántica de Azure.

### Etapa 4: evidencia final, trazabilidad y abstención

El selector final enviará tres a cinco fuentes como máximo. Deben ser
directamente citables, no redundantes y, cuando la pregunta tenga más de un
requisito, cubrirlos de manera complementaria. Se conservarán:

- título, enlace y fragmento;
- `document_id`, versión, fecha, tipo y ruta;
- `version_confirmed` y razón de fallback;
- rango de Azure, señales de ranking y modo de verificación en el diagnóstico;
- conteo de candidatos y razones agregadas de descarte.

Si no queda una fuente con cobertura directa, el selector no degradará a una
respuesta probable: devolverá abstención sin fuentes.

## Cambios de código propuestos

1. En `src/azure_search.py`, separar explícitamente las funciones de:
   recolección, filtros duros, elegibilidad/relevancia, reranking y selección
   final. No cambiar el contrato público de `retrieve_azure_search_evidence`.
2. Añadir constantes configurables en código para límite de unión, tamaño del
   pool de reranking y límite final, con valores seguros por defecto. No añadir
   variables de App Service hasta que el comportamiento quede validado.
3. Extender `RetrievalTrace` solo con métricas no sensibles necesarias para
   observar las etapas y razones de descarte.
4. En `src/debug_retrieval.py`, mostrar una vista por etapa con conteos,
   candidatos identificados por metadatos permitidos y razones de descarte. La
   salida no debe incluir vectores, secretos ni contenido adicional.
5. Reutilizar `_excerpt_around_query` para limitar los fragmentos antes de
   evaluar o generar, de modo que una sección incidental no contamine una
   evidencia correcta.

## Matriz de validación

Ejecutar cada caso contra las tres variantes, sin tocar el índice:

| Caso | Filtros actuales | Pool ampliado | Híbrida con reranking | Criterio de aprobación |
|---|---|---|---|---|
| jQuery 3.7.2 y reemplazo 1.12.4 | Debe recuperar Readme correcto | Puede conservar coincidencias incidentales | Solo Readme correcto llega a evidencia final | No aparece Crystal Reports. |
| IRA + 1.24.1.3 | Manual técnico como fallback | Readme y Manual pueden coexistir | Manual IRA primero, versión no confirmada | Advertencia visible; no falso versionado. |
| Requisitos Readme/release con versión | Solo Readme exacto | Igual | Igual | Ningún fallback de versión. |
| Archivo explícito | Solo archivo solicitado | Igual | Igual | No devuelve un archivo relacionado. |
| Identificador técnico exacto | Rechaza mención casual | Igual | Igual | El identificador está en el fragmento citable. |
| Índice o tabla de contenido | Rechazado | Rechazado | Rechazado | Nunca llega al evaluador. |
| Fuente o ruta no autorizada | Rechazado | Rechazado | Rechazado | No llega a evidencia. |
| Inyección en documento | Caso nuevo | Caso nuevo | Caso nuevo | No llega al evaluador ni a generación. |
| Sin evidencia directa | Abstención | Abstención | Abstención | Sin enlace tangencial. |
| Respuesta que requiere dos secciones | Puede perder secundaria | Conserva candidatas | Entrega evidencias complementarias | Cobertura completa con <=5 fuentes. |

Métricas mínimas por variante: recall@3 y recall@5 de evidencia, precisión de
la fuente citada, abstención correcta, cantidad de evidencia final, tasa de
rechazo por regla y latencia p50/p95. La comparación debe conservar los casos
actuales de `tests/test_document_questions.py`, las pruebas de diagnóstico de
`tests/test_debug_retrieval.py` y casos nuevos de regresión para cada fila.

## Orden de ejecución local

### Entrega 1 — observabilidad y línea base

- [x] Añadir pruebas para verificar los conteos de cada etapa, sin alterar la
  selección actual de evidencia.
- [x] Extender el diagnóstico con: unión acotada, filtros duros, elegibles,
  pool evaluado, aceptados y razones agregadas de descarte.
- [x] Confirmar mediante regresión que `evidencia_que_recibe_el_bot` conserva
  exactamente el comportamiento legacy actual antes del cambio funcional.

Resultado inicial: la unión queda limitada a 60 candidatos y el pool que
recibe el ranking determinista queda limitado a 20. `RetrievalTrace` y el
diagnóstico exponen conteos agregados por etapa, sin preguntas ni fragmentos
 adicionales. La suite local queda en 285 pruebas exitosas. El evaluador LLM no
 está activado. El diagnóstico ya expone los conteos de los pases Azure
 léxico, enfocado, prefijo, vectorial, scripts y archivo explícito, además de
 documentos únicos y máximo de fragmentos por documento.

Corrección aplicada después de la primera revisión: el límite global ahora se
calcula después de procedencia, país, versión, archivo, identificador técnico y
restricciones de script. Así, el ruido no puede expulsar un registro autorizado
antes de cruzar los filtros de seguridad.

### Entrega 2 — pool híbrido determinista

- [ ] Crear pruebas primero para límite global del pool, diversidad y la
  separación entre filtros duros y señales de relevancia.
- [ ] Separar en `azure_search.py` la recolección, el filtrado duro, la
  elegibilidad y el selector final, sin cambiar el contrato público de
  `retrieve_azure_search_evidence`.
- [ ] Permitir que los resultados vectoriales contribuyan al pool de forma
  acotada y medible; no habilitar Azure Semantic Search.
- [ ] Dejar el ranking determinista como reranker inicial y seleccionar tres a
  cinco evidencias, conservando abstención.

### Entrega 3 — evaluador de evidencia acotado

- [x] Agregar una barrera determinista para marcadores fuertes de inyección en
  contenido documental autorizado, con fallo cerrado y regresión.
- [x] Agregar casos de prueba para salida JSON válida, ID desconocido, requisito
  no permitido y fallo del proveedor; todas las salidas malformadas fallan
  cerrado.
- [ ] Reutilizar `verify_semantic_evidence` o extraer un adaptador compatible,
  siempre detrás de los filtros duros y con fallo cerrado.
- [ ] Habilitar el evaluador únicamente mediante una bandera local segura; la
  configuración productiva sigue sin cambios.

### Entrega 4 — evaluación y decisión

- [ ] Ejecutar pruebas unitarias afectadas y la suite completa.
- [ ] Ejecutar la matriz de recuperación en modo solo lectura contra el índice
  autorizado, si la configuración disponible lo permite.
- [x] Crear el arnés local para ejecutar los mismos casos contra estrategias
  nombradas y comparar recall, abstención, cobertura y latencia, sin
  credenciales ni llamadas a Azure.
- [x] Comparar filtros actuales, pool ampliado y reranking con las métricas
  definidas en un entorno autorizado de App Service, sin modificar el índice.
- [x] Registrar los casos fallidos y sus conteos por etapa para separar recall
  de falsos positivos.
- [x] Ejecutar pruebas dirigidas para RAG-09 (prioridad Readme/release) y
  RAG-10 (abstención ante coincidencia temática débil).
- [ ] Solicitar aprobación explícita antes de configurar producción o desplegar
  en `app-libras-prod`.

## Bitácora de ejecución y decisiones

### 2026-08-11 — comparación real en App Service

Se ejecutó `src/compare_retrieval_strategies.py` contra el índice autorizado
`libras-docs` usando Entra ID desde SSH → Application. Se evaluaron 15 casos y
se conservaron los artefactos en `/tmp/libras-eval` del contenedor temporal.
No hubo reindexación, cambios de configuración, llamadas al modelo evaluador
LLM ni despliegue.

| Variante | Pass rate | Recall de evidencia | Abstención correcta | Latencia promedio |
|---|---:|---:|---:|---:|
| `actual_legacy` | 86.7% | 91.7% | 66.7% | 1.56 s |
| `candidatos_ampliados` | 86.7% | 91.7% | 66.7% | 2.43 s |
| `ampliados_reranking_determinista` | 86.7% | 91.7% | 66.7% | 1.87 s |

Decisión provisional: mantener los límites actuales (unión 60, pool de
reranking 20). Ampliar candidatos no mejoró calidad y aumentó latencia.

### Casos que requieren trabajo dirigido

- **RAG-09**: la pregunta espera `Readme 1.19.1.6`, pero la evidencia final
  selecciona documentos `Upgrade`. Los candidatos pasaron todos los filtros
  duros; el problema es de cobertura/ranking o de expectativa del corpus.
  Debe verificarse si el Readme esperado está indexado antes de modificar el
  ranking.
- **RAG-10**: la pregunta exige `sin_evidencia`, pero se aceptan páginas de
  `Gestion de documentos` y `Portal Consultas`. Es un falso positivo de
  relevancia; se necesita una regla dirigida de abstención para coincidencias
  temáticas sin cobertura directa.

### 2026-08-11 — corrección dirigida local para RAG-09 y RAG-10

Se añadieron regresiones unitarias para ambos casos y se mantuvieron sin
cambios los filtros de procedencia autorizada, archivo explícito, versión
estricta, identificador técnico e inyección documental.

- **RAG-09:** una consulta de precauciones previas a instalar o actualizar
  activa un pase léxico adicional, acotado, para `readme` más los términos
  enfocados. La unión sigue limitada a 60 y el reranking a 20. El título de un
  Readme/release/hotfix solo recibe preferencia si el fragmento también aporta
  evidencia de preparación, respaldo o recomendación; un Readme incidental no
  desplaza una lista de preparación directa.
- **RAG-10:** para una falla que menciona simultáneamente permisos, descarga y
  documentos, cada candidato debe contener los tres conceptos en una ventana
  local de evidencia. Las páginas que solo hablan de gestión o consulta de
  documentos se descartan como `weak_document_access_coverage`, produciendo
  abstención sin enlaces tangenciales.
- **Trazabilidad:** el diagnóstico conserva el conteo agregado del pase
  `azure_release_readme`, los candidatos Readme/release elegibles y el motivo
  de descarte de cobertura de acceso débil. No se agregan fragmentos crudos al
  modelo ni al trace.

La inspección local de los respaldos de producción disponibles
(`backup-libras-docs-20260804` y `backup-libras-pre-duplicados-20260806`)
confirmó 16 fragmentos de `Readme 1.19.1.6.pdf`, con procedencia SharePoint,
PDF, `folder_path` raíz y metadatos de versión/modificación consistentes. No
es una afirmación sobre el estado en vivo: la estación local no pudo resolver
el endpoint configurado para diagnóstico. La comprobación final debe repetirse
desde SSH → Application usando Entra ID y `libras-docs`, sin reindexar.

Validación local: **287 pruebas, OK**. No hubo despliegue, reindexación,
cambio de modelos, SKU, manifiesto de Teams, estrategia `legacy` ni activación
de Azure Semantic Search o del evaluador LLM.

### 2026-08-11 — revisión previa a Azure en vivo

La ejecución anterior de **287 pruebas, OK** queda confirmada como la línea
base de la corrección RAG-09/RAG-10. Se añadieron dos regresiones de revisión
y la suite completa actual terminó en **289 pruebas, OK**.

- **Rango Readme:** la fusión de candidatos ahora conserva todos los rangos
  asignados por pases anteriores. La regresión reutiliza el mismo Readme en
  los pases keyword, focused, Readme/release, vectorial, prefix y script, y
  comprueba que `_release_readme_rank` permanece disponible para el ranking y
  los límites de pool.
- **RAG-10:** la abstención solo se activa si la pregunta expresa de forma
  simultánea permisos, descarga y documentos. Una pregunta ordinaria sobre
  cómo descargar documentos conserva su evidencia directa; no se aplica la
  barrera de abstención.
- **Cobertura respaldada:** siguen confirmados los 16 fragmentos de
  `Readme 1.19.1.6.pdf` en los respaldos locales disponibles; esta evidencia
  no sustituye una lectura del índice actual.

**Estado: pendiente de verificación real en SSH → Application** con Entra ID
contra `libras-docs`, sin reindexar ni alterar configuración productiva.

Los diagnósticos crudos se generaron en `/tmp/RAG-09-debug.json` y
`/tmp/RAG-10-debug.json` durante la sesión de App Service. El nombre de logger
`chat_salvador` es heredado y no representa el índice ni cambia el resultado.

### Próximo bloque

1. Repetir la comprobación en vivo de metadatos/cobertura de `Readme 1.19.1.6`
   desde SSH → Application, sin reindexar.
2. Repetir la comparación real de los 15 casos desde ese mismo entorno y
   registrar RAG-09/RAG-10 junto con latencia.
3. Decidir promoción solo después de comparar contra esta línea base y obtener
   aprobación explícita.

### 2026-08-12 — segunda comparación real después del bloque dirigido

Se repitió la comparación desde SSH → Application con el código actualizado,
Entra ID y el corpus de 15 casos. No hubo despliegue ni reindexación.

El resultado global permaneció en `86.7%` de pass rate y `91.7%` de recall de
evidencia en las tres variantes. `actual_legacy` continuó siendo la opción más
conveniente por latencia.

- **RAG-09:** el pase `azure_release_readme` recuperó candidatos Readme, pero
  no seleccionó `Readme 1.19.1.6`; se eligieron `1.19.1.13`, `1.24.0.1` y
  `1.19.1.8`. Ampliar la unión tampoco corrigió el caso.
- **RAG-10:** `weak_document_access_coverage` sí descartó candidatos, pero
  quedaron tres registros elegibles que todavía llegaron a la evidencia final.
  La ventana de cobertura o la etapa posterior es demasiado permisiva y debe
  corregirse antes de activar un evaluador semántico.

Decisión: mantener `legacy` 60/20, no activar pool ampliado y revisar primero
la abstención determinista de RAG-10. El evaluador LLM seguirá desactivado.

### 2026-08-12 — endurecimiento local de RAG-10 y evaluador acotado

No se desplegó ni se modificó configuración productiva. La barrera determinista
de RAG-10 ahora exige que permisos, descarga y documentos aparezcan juntos en
una misma unidad local de prosa; título, metadatos y pasajes separados ya no
pueden combinarse para producir evidencia final.

El evaluador LLM de V2 permanece desactivado por defecto. Cuando se habilite
explícitamente, recibe como máximo 12 documentos distintos posteriores a los
filtros duros, IDs opacos (`c01` …), fragmentos con credenciales redactadas y
un contrato JSON estricto. Respuestas con inyección, JSON/estructura inválida,
IDs o requisitos no permitidos, o confianza menor a `0.80` fallan cerradas;
el ranking determinista se conserva como fallback. El diagnóstico V2 también
propaga conteos de candidatos por etapa.

Verificación local: `python -m unittest discover -s tests -p 'test_*.py'` —
294 pruebas, OK.

La comparación controlada contra Azure solicitada el 2026-08-12 no pudo
iniciarse desde esta terminal: `Config.azure_search_enabled` resultó falso y
el comando terminó sin crear resultados ni contactar Azure. La validación
local dirigida sí pasó: 146 pruebas OK (verificador, RAG-10, V2 y diagnóstico).
La comparación real queda pendiente de ejecutarse desde SSH/Application con
la identidad autorizada, sin activar `USE_LLM_EVIDENCE_VERIFIER`.

### 2026-08-12 — artefactos de validación actualizados (sin despliegue)

La comparación de Azure confirmó que el artefacto previamente extraído era
anterior a esta corrección: combinaba metadatos y contenido en RAG-10 y no
contenía el contrato endurecido del evaluador. Se generaron localmente un ZIP
de backend y un ZIP de evaluación de la revisión actual, ambos sin `.env` ni
cachés Python. No se desplegaron, no se reinició App Service y no se cambió
ninguna variable. La suite completa volvió a finalizar con **294 pruebas, OK**.

La inspección del corpus productivo mostró que las tres fuentes de RAG-10 eran
instrucciones válidas de descarga, pero no diagnóstico de una falla. Se añadió
una señal local obligatoria de troubleshooting (`revisar`, `verificar`,
`validar`, configuración, error o problema) junto con permisos, descarga y
documentos. Las pruebas dirigidas quedan en **147 pruebas, OK**; el evaluador
LLM sigue desactivado.

La corrección posterior de RAG-09 ajusta el límite del pool para preservar
primero Readme/release con evidencia local de preparación cuando la pregunta
es preinstalación. Así la página release no se pierde entre candidatos
históricos antes del reranking. Se añadió una regresión de ese límite y la
suite completa queda en **296 pruebas, OK**. No se activó el evaluador LLM.

El diagnóstico productivo confirmó que `Readme 1.19.1.6` sí aparece en Azure
(rangos 36 y 60), pero la cobertura exigía literalmente las acciones `tomar` e
`instalar`; el documento expresa la misma intención como preparación, respaldo,
aplicación y recomendaciones. Se amplió la cobertura únicamente para preguntas
de preinstalación cuando esas familias de evidencia aparecen juntas. La suite
completa queda en **297 pruebas, OK**; falta repetir la evaluación en Azure.

### Decisión RAG-09 — 2026-08-12

La evaluación productiva confirmó que `Readme 1.19.1.6` sí está indexado y
contiene preparación, respaldos e instrucciones de actualización, pero la
pregunta de RAG-09 no especifica versión y devuelve múltiples Readme
incompatibles. No se añadirá una excepción para seleccionar `1.19.1.6`.

La política general será abstenerse de presentar evidencia final y solicitar la
versión (`solicita_contexto`) cuando una consulta de instalación/actualización
no tenga versión explícita y existan varias versiones candidatas. Con versión
explícita se mantiene el filtro estricto. Esta decisión evita falsos versionados
y hace que la regla sea reutilizable para cualquier documento versionado.

## Criterios para proponer despliegue

No se propondrá un despliegue mientras no se cumplan todos estos puntos:

1. La suite completa pasa y se mantienen las regresiones de jQuery, IRA,
   versiones, procedencia y abstención.
2. Ninguna fuente no autorizada, índice, tabla de contenido o candidato con
   inyección llega a la respuesta final.
3. La estrategia híbrida supera o iguala la línea base en recall y abstención,
   sin degradar la precisión de las fuentes.
4. El diagnóstico permite explicar por qué cada evidencia fue aceptada o
   descartada sin revelar secretos ni resultados crudos innecesarios.
5. La decisión de promoción está aprobada de forma explícita.
