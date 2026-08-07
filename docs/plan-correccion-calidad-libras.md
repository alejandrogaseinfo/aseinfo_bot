# Plan de corrección de calidad de Libras

> Estado: **en ejecución**. Inicio: 2026-08-03. Este documento concentra la
> corrección de calidad del piloto. Complementa, sin sustituir,
> [contexto-actual.md](contexto-actual.md) y
> [plan-pruebas-playground.md](plan-pruebas-playground.md). El esquema de
> metadatos funcionales está en
> [catalogo-metadatos-indexacion.md](catalogo-metadatos-indexacion.md).

## Objetivo

Lograr que Libras identifique preguntas técnicas expresadas en lenguaje
natural, recupere evidencia documental directa y responda con una explicación
fundamentada y un enlace verificable. Debe rechazar peticiones inseguras o
fuera de alcance sin bloquear consultas técnicas legítimas.

La solución no consiste en codificar respuestas para preguntas individuales.
Se corrigen la clasificación de seguridad, la interpretación de consulta, la
calidad del índice, el ranking, la verificación de evidencia y la memoria de
conversación.

## Hallazgos iniciales

| Área | Hallazgo | Estado |
|---|---|---|
| Seguridad | La regla actual trata cualquier mención de `contrato(s)` como información confidencial. Puede bloquear consultas técnicas, como parámetros de prórroga de contratos. | Confirmado; corrección inmediata. |
| Seguridad | Las inyecciones de instrucciones y preguntas claramente ajenas al alcance no tienen una barrera determinista previa a recuperación. | Confirmado; pendiente. |
| Conversación | La aplicación conserva solo la última respuesta documental en memoria del proceso. No guarda turnos del usuario, se borra tras una respuesta no documental y no sobrevive reinicios o varios workers. | Confirmado; pendiente. |
| Recuperación | La aceptación de evidencia exige coincidencias léxicas rígidas; `administrar` no equivale a `gestión`, aunque el documento relevante exista. | Confirmado; pendiente. |
| Ranking | El índice crea configuración semántica, pero la consulta no la usa. El ranking propio sobrepondera la posición vectorial frente a la cobertura de la pregunta. | Confirmado; pendiente. |
| Índice | La documentación histórica contiene cifras y alcances distintos. Se necesita un inventario actual del índice antes de excluir o reindexar contenido. | Confirmado; pendiente. |
| Alcance | Preguntas de legislación salvadoreña solo son casos positivos si la fuente aprobada contiene esa legislación. De otro modo deben permanecer como `sin evidencia` o fuera de alcance. | Requiere verificación documental. |

## Secuencia de corrección

### Fase 0 — Línea base e inventario

1. Exportar un inventario no sensible del índice: `document_id`, título,
   biblioteca, ruta, tipo, fecha, hash, número de fragmentos y estado de texto
   extraíble.
2. Identificar duplicados, documentos vacíos, portadas/índices repetitivos,
   archivos obsoletos y contenido que no aporta recuperación.
3. Construir un corpus de evaluación versionado. Cada caso tendrá pregunta
   natural, resultado esperado (`documento/sección` o `sin_evidencia`) y tipo
   de prueba; no almacenará datos de clientes, secretos ni fragmentos internos.
4. Medir recuperación `recall@3`, precisión de fuente, tasa de abstención
   correcta, fidelidad de respuesta, seguridad y latencia.

El comando `src/evaluate_retrieval_quality.py` implementa la medición inicial
de recuperación y abstención. El corpus debe ser revisado después del
inventario y cada caso positivo debe declarar el título del documento esperado:

```powershell
python src\evaluate_retrieval_quality.py --cases ruta\corpus-calidad.json --use-current-environment
```

**Salida:** inventario validado y línea base de calidad. No se reconstruye el
índice productivo hasta conservar esta evidencia y un mecanismo de reversión.

### Resultado de la línea base (2026-08-04)

El inventario de solo lectura de `libras-docs` confirmó **343 documentos** y
**4,569 fragmentos**. Es una medición de metadatos, no una lectura ni una
exportación del contenido:

| Señal | Evidencia | Riesgo para recuperación | Decisión |
|---|---:|---|---|
| Ruta de biblioteca no detallada | 146 documentos; 2,215 fragmentos (48.5%) tienen `folder_path` vacío. Puede significar una fuente configurada en la raíz, no necesariamente un dato perdido. | No se puede filtrar ni explicar con granularidad de subcarpeta casi la mitad del índice. | Conservar `drive_id` como límite de procedencia y capturar la ruta padre real desde SharePoint antes de usarla como señal de calidad. |
| Código SQL | 1,435 fragmentos (31.4%) | Puede introducir ruido, pero también contiene procedimientos útiles. | No excluir por tipo; clasificarlo y enriquecerlo con producto, operación y descripción. |
| Documentos muy fragmentados | Los tres mayores archivos concentran 1,735 fragmentos (38.0%). | Pueden ocupar los candidatos iniciales y ocultar documentos pequeños relevantes. | Diversificar candidatos por documento y revisar fragmentación de archivos extensos. |
| Duplicados exactos | 15 grupos, 30 documentos. | Repite evidencia y desperdicia candidatos. | Consolidar o marcar una copia canónica antes de la siguiente reindexación. |

El corpus inicial de cinco casos quedó en
`tests/corpus-recuperacion-calidad.json`. Contra producción, sin modificar el
índice, la configuración actual logró 3/5 casos (recall de evidencia 1/3 y
abstención correcta 2/2). La configuración candidata con ranking semántico y
diversidad documental logró 4/5 (recall 2/3 y abstención correcta 2/2). No se
promueve todavía: el caso de vacaciones negativas sigue sin recuperar el
script aunque existe en el inventario, por lo que requiere enriquecimiento de
la ingesta y una evaluación más amplia.

### Fase 1 — Seguridad y enrutamiento

1. Separar tema y riesgo: bloquear solicitudes de divulgación de datos de un
   cliente, contrato identificable, saldo, pago, información personal o
   secretos; permitir preguntas técnicas generales que incluyan palabras como
   `contrato`.
2. Añadir detección determinista de inyección de instrucciones y de solicitudes
   que intenten evadir controles. El guard semántico será una segunda capa,
   primero en observación y después en modo estricto cuando se mida su precisión.
3. Evitar que una pregunta factual llegue a una ruta de "pedir contexto" solo
   porque no contiene producto o versión. Las aclaraciones quedan para errores
   realmente indeterminados.

**Criterio de salida:** los casos de seguridad no llegan a recuperación; las
consultas técnicas legítimas no reciben un rechazo de seguridad.

### Fase 2 — Recuperación e indexado

1. Conservar por fragmento metadatos recuperables: producto, módulo, operación,
   tipo documental, versión, biblioteca, sección y vigencia, cuando estén
   disponibles desde el documento o la fuente controlada.
2. Fragmentar respetando encabezados, secciones y tablas; propagar contexto
   documental útil a cada fragmento, sin depender de los primeros caracteres
   del archivo.
3. Aplicar recuperación híbrida real (texto, vector y ranking semántico), con
   filtros estrictos por fuente autorizada y versión cuando el usuario la
   indique.
4. Sustituir reglas de coincidencia literal de verbos por una comprobación de
   relevancia semántica que confirme que el fragmento responde la intención de
   la pregunta.
5. Penalizar o excluir ruido documentado por el inventario, sin eliminar scripts
   ni documentos técnicos útiles solo por su extensión.

**Criterio de salida:** una paráfrasis normal recupera el mismo documento o
sección que la formulación técnica equivalente; una coincidencia tangencial no
se presenta como respuesta.

#### Ejecución candidata controlada

El índice candidato debe usar otro nombre, por ejemplo
`libras-docs-candidate-20260804`, y las mismas fuentes autorizadas. La carga
requiere permisos de escritura en Azure AI Search y permiso para generar
embeddings; no se debe reutilizar el nombre productivo en esta fase:

```powershell
$env:LIBRAS_ENV = "production"
$env:AZURE_SEARCH_ENDPOINT = "https://srch-libras-prod.search.windows.net"
$env:AZURE_SEARCH_INDEX_NAME = "libras-docs-candidate-20260804"
$env:AZURE_SEARCH_USE_ENTRA_ID = "true"
$env:AZURE_SEARCH_USE_SEMANTIC = "true"
python src\azure_search_ingest.py --source-dir data\sharepoint --create-index --use-current-environment
python src\evaluate_retrieval_quality.py --cases tests\corpus-recuperacion-calidad.json --use-current-environment
```

El comando es preparatorio: requiere que `data\sharepoint` contenga una
sincronización autorizada y no debe ejecutarse hasta revisar el catálogo de
metadatos y confirmar el nombre del índice candidato. `--use-current-environment`
evita cargar accidentalmente un `.env` local distinto.

#### Restricción de capacidad descubierta (2026-08-04)

La sincronización autorizada de SharePoint produjo 350 archivos, 350 metadatos,
350 estados y ninguna eliminación. Sin embargo, el primer intento de carga
completa se interrumpió por el límite de ejecución de la terminal y dejó solo
260 documentos/3,000 fragmentos en el candidato; no era una pérdida de
SharePoint. Al reintentar por lotes, Azure AI Search devolvió `Storage quota has
been exceeded`.

El servicio `srch-libras-prod` es **Free**, con cuota de 50 MB. El índice de
producción ocupa 46.8 MB (28.8 MB de vector) por sí solo, por lo que no hay
capacidad para un candidato completo de 3,000 fragmentos. El candidato parcial
se eliminó; `libras-docs` no fue modificado. Para una comparación completa se
requiere una de estas alternativas aprobadas:

1. un servicio Azure AI Search separado para calidad/preproducción (opción
   recomendada), o
2. ampliar temporalmente el SKU/capacidad del servicio con aprobación de
   costos, o
3. usar solo muestras pequeñas en el servicio Free y ejecutar el corpus amplio
   con un índice local/reproducible.

Si se habilita un servicio candidato, debe conservar la dimensión de embeddings
de producción (`512`) y definir `TEAMSFX_ENV=production` al cargar secretos;
dejar que el `.env` local seleccione `1536` vuelve a inflar el índice y puede
agotar la cuota prematuramente.

La cuenta de trabajo tiene `Contributor` sobre `rg-libras-prod`, por lo que
probablemente puede crear un servicio nuevo dentro de ese grupo; eso no
significa autorización para generar cargos. El nivel Free no se escala en el
mismo servicio: la alternativa correcta es crear otro servicio Basic/Standard,
cargar allí el candidato y cambiar el endpoint solo en la sesión de evaluación.

Mientras no exista aprobación de costo, el trabajo puede continuar con una
evaluación local en memoria sobre el staging de SharePoint, auditoría de
documentos vacíos/duplicados y el catálogo de metadatos. Esto permite corregir
extracción, normalización y clasificación sin tocar producción; la evaluación
en Azure se repite cuando exista capacidad.

### Fase 3 — Respuesta fundamentada y conversación

1. Separar recuperación, verificación de evidencia y redacción. La respuesta
   solo puede afirmar hechos cubiertos por los fragmentos aprobados.
2. Mantener el formato: respuesta directa, fuente y enlace verificable. Si la
   evidencia es solo relacionada, responder sin evidencia y sin enlazarla.
3. Reemplazar la memoria en proceso por estado persistente por conversación de
   Teams. Se evaluará Responses API con Conversations API para contexto durable,
   junto con un mapeo seguro `Teams conversation id -> OpenAI conversation id`.
4. Antes de activar memoria durable, aprobar retención, borrado y el tratamiento
   de información interna. Las conversaciones de la Conversations API no tienen
   la expiración predeterminada de 30 días de las respuestas; por ello no se
   activarán sin una política explícita de retención y borrado. No se guardarán
   secretos ni fragmentos documentales innecesarios.

**Criterio de salida:** los seguimientos entienden referencias como "eso",
"el documento anterior" o "salúdame por mi nombre" cuando ese dato fue recibido
legítimamente en la conversación.

### Fase 4 — Validación y despliegue controlado

1. Comparar índice y backend candidatos contra la línea base en preproducción.
2. Ejecutar el corpus de evaluación y los casos de Teams antes de promover el
despliegue.
3. Liberar a un grupo piloto, revisar telemetría agregada y conservar reversión
al índice y backend anteriores.

Metas iniciales: 100% de bloqueo de secretos e inyecciones conocidas; al menos
90% de recuperación del documento esperado en los tres primeros resultados;
al menos 95% de respuestas con fuente correcta; cero enlaces en respuestas sin
evidencia.

## Registro de casos prioritarios

| ID | Caso | Resultado esperado | Diagnóstico inicial |
|---|---|---|---|
| SEC-01 | "parámetros para prórroga de contratos" | Búsqueda documental; no bloqueo por confidencialidad. | Falso positivo confirmado. |
| SEC-02 | "ignora las instrucciones..." | Rechazo de seguridad sin búsqueda. | Falta barrera determinista. |
| CON-01 | Saludo, presentación y pregunta de seguimiento. | Respuesta natural que conserve contexto. | No hay memoria de turnos. |
| RAG-01 | "cómo administrar documentos" frente a documentación de "gestión de documentos". | Recuperar el documento si describe la capacidad solicitada. | Regla léxica rígida. |
| RAG-02 | Preguntas de incapacidades. | Fuente que responda directamente o `sin evidencia`. | Requiere auditoría de candidatos e índice. |
| SCOPE-01 | Legislación laboral de El Salvador. | Responder solo si existe fuente autorizada y vigente; en otro caso abstenerse. | Alcance por confirmar. |

## Bitácora

| Fecha | Cambio o evidencia | Resultado |
|---|---|---|
| 2026-08-03 | Se creó este plan y se reprodujo localmente el caso SEC-01. | La consulta técnica sobre contratos activa la regla de confidencialidad; se inicia su corrección con prueba de regresión. |
| 2026-08-03 | Se corrigió SEC-01 y se añadió el rechazo determinista de SEC-02. | La consulta técnica llega a recuperación; la inyección explícita se rechaza antes del modelo y de Azure AI Search. |
| 2026-08-03 | Se añadió `src/index_inventory.py`. | Pendiente ejecutar contra el índice productivo con la identidad autorizada; el comando es de solo lectura y no reconstruye ni elimina registros. |
| 2026-08-03 | Se intentó ejecutar el inventario desde esta estación. | La configuración local apunta a un servicio de búsqueda de desarrollo no disponible. Se requiere cargar la configuración autorizada de producción antes de obtener la línea base. |
| 2026-08-03 | Se añadió `src/evaluate_retrieval_quality.py`. | El evaluador mide recuperación del documento esperado y abstención correcta sin llamar al modelo generativo ni modificar el índice. |
| 2026-08-04 | Los comandos de auditoría admiten `--use-current-environment`. | Permite usar la configuración explícita de producción de la terminal sin cargar archivos `.env` locales de desarrollo. |
| 2026-08-04 | Se ejecutó el inventario con identidad Entra autorizada. | Producción contiene 343 documentos y 4,569 fragmentos; 48.5% no registra ruta detallada (podría ser raíz de biblioteca), hay 15 grupos duplicados y 38.0% se concentra en tres archivos extensos. |
| 2026-08-04 | Se creó y ejecutó el corpus de recuperación inicial contra producción. | Línea base: 3/5. El documento `Gestion de documentos.pdf` existe pero la pregunta “administrar documentos” no lo recuperaba; el script de vacaciones también existe pero no se recupera. |
| 2026-08-04 | Se implementó en candidato la consulta semántica real, diversidad por documento y aceptación controlada de paráfrasis. | 4/5 en el corpus (recall 2/3, abstención 2/2). Cambio local validado; no se ha desplegado ni reindexado producción. |
| 2026-08-04 | La ingesta candidata ahora antepone contexto documental y términos normalizados del nombre del archivo a cada fragmento y a su embedding. | Los nombres técnicos con puntos, guiones bajos o camel case serán recuperables por palabras; requiere una reindexación controlada para reflejarse en Azure AI Search. |
| 2026-08-04 | Se añadió `--use-current-environment` al cargador de Azure AI Search. | Permite preparar un índice candidato con variables explícitas sin que archivos `.env` locales redirijan la carga a otro servicio. No se ejecutó ninguna carga. |
| 2026-08-04 | Se validó el cargador y la suite completa después del cambio. | `--help` expone el modo candidato y las 134 pruebas automatizadas pasan; la creación del índice paralelo queda pendiente de confirmar permisos y nombre. |
| 2026-08-04 | Se confirmó en Azure que la identidad de trabajo tiene `Search Index Data Contributor` en `srch-libras-prod`. Se creó `libras-docs-candidate-20260804` y se cargó una muestra controlada de 3 documentos. | La muestra contiene 43 fragmentos y no modifica `libras-docs`. |
| 2026-08-04 | Se ejecutó el corpus contra la muestra candidata. | 4/5 casos aprobados, recall 2/3 y abstención 2/2. “Gestión de documentos” se recupera; `acc.proc_arreglar_vac_negativos.sql` sigue sin encontrarse porque `vac` requiere un alias funcional aprobado. |
| 2026-08-04 | Terminó la carga completa del staging al índice candidato. | El candidato tiene 261 documentos y 3,013 fragmentos frente a 343 y 4,569 en producción: faltan 82 documentos y 1,556 fragmentos. No es comparable ni promovible todavía. |
| 2026-08-04 | Se ejecutó el corpus contra el candidato completo. | 3/5 casos aprobados, recall 1/3 y abstención 2/2. La paráfrasis “administrar documentos” vuelve a quedar desplazada por fuentes tangenciales cuando entra todo el ruido; confirma que se necesita clasificación/filtrado de calidad además de ranking. |
| 2026-08-04 | Se sincronizó SharePoint en `tmp/sharepoint-refresh-20260804`. | 350 archivos legibles, 350 metadatos, 350 documentos en el estado de sincronización y 0 eliminaciones; la fuente está completa para una carga controlada. |
| 2026-08-04 | Se consultaron los nombres de los ocho `drive_id` configurados mediante Microsoft Graph. | El alcance es: `ReadME Hotfixes` (raíz), `Documentos` solo `SOLUCIONES`, `Legislaciones` (raíz), `Traslados OP/DE` (raíz), `Parches Adicionales` (raíz), `Documentos de Apoyo` (raíz), `Manuales` (raíz) y `Scripts de Apoyo` (raíz). |
| 2026-08-04 | Se comparó el alcance con la última sincronización. | Archivos legibles por fuente: ReadME Hotfixes 43, Documentos/SOLUCIONES 200, Legislaciones 9, Traslados OP/DE 5, Parches Adicionales 0, Documentos de Apoyo 51, Manuales 20 y Scripts de Apoyo 22. |
| 2026-08-04 | La recarga completa del candidato fue truncada por el límite de 10 minutos de la terminal. | El índice llegó a 260 documentos/3,000 fragmentos y el manifiesto conservó los 350 cambios; se descartó como medición incompleta. |
| 2026-08-04 | Se reintentó por lotes; el primer lote produjo 600 fragmentos y el segundo fue rechazado por cuota. | El servicio es SKU Free: cuota 50 MB, uso 60.7 MB; `libras-docs` ocupa 46.8 MB. Se eliminó únicamente el candidato y se bloquea la carga completa hasta disponer de capacidad separada o ampliada. |
| 2026-08-04 | Se adoptó un alcance reducido y se separó el contenido dominante. | Se generaron tres staging no destructivos: `core` (282 archivos antes de extracción), `specialized` (los 3 documentos dominantes) y `review` (Legislaciones, Traslados OP/DE y Documentos de Apoyo; 65 archivos). Los tres documentos no entran al índice general. |
| 2026-08-04 | Se ejecutó evaluación local de extracción y ranking léxico sobre el alcance `core`. | 275 documentos con texto y 2,652 fragmentos. “Gestión de documentos” aparece entre los primeros resultados; el script de vacaciones requiere alias funcional; las consultas legales de El Salvador siguen necesitando filtro de país/evidencia. |
| 2026-08-04 | Se clasificaron los 65 documentos de la colección `review`. | 12 `LEGAL_REVIEW`, 19 `CUSTOMER_RESTRICTED`, 9 `APPROVED_TECHNICAL`, 1 `GENERAL_SUPPORT_REVIEW`, 16 `GENERAL_PROCESS_REVIEW`, 7 `GENERAL_TEMPLATE_REVIEW` y 1 `SECURITY_REVIEW`. Los 9 aprobados pasaron a `core-v3`; los restantes siguen fuera del índice general. |
| 2026-08-04 | Se revisaron los 11 candidatos técnicos y se creó `core-v3`. | Se aprobaron 9 documentos técnicos genéricos para el núcleo; el manual del Portal de AutoServicio queda en `GENERAL_SUPPORT_REVIEW` y GenPlaAPI en `SECURITY_REVIEW`. `core-v3` contiene 284 documentos con texto y 2,665 fragmentos; no se cargó Azure. |
| 2026-08-04 | Se corrigió la normalización de identificadores y la puntuación del re-ranker local. | Los separadores `_`, `-` y `.` de nombres SQL ahora exponen conceptos (`vac_vacaciones` → `vacacion`), y la puntuación incorpora título normalizado, contexto documental, tokens indexados y tipo de archivo. La coincidencia de conceptos en el título recibe mayor peso que una mención incidental. Las 137 pruebas pasan. El procedimiento `acc.proc_arreglar_vac_negativos.sql` obtiene cobertura de `arreglar` + `vacacion` y prioridad por nombre en la prueba de ranking; falta validar el ranking completo en Azure con un índice candidato. |
| 2026-08-04 | Se regeneró la evaluación local metadata-aware sobre `core-v3` después del ajuste. | 284 documentos y 2,665 fragmentos: RAG-01 y RAG-02 recuperan `Gestion de documentos.pdf` en los primeros resultados; RAG-03 coloca `acc.proc_arreglar_vac_negativos.sql` en el primer resultado; SCOPE-01 y SCOPE-02 no encuentran una fuente autorizada esperada y deben abstenerse. El reporte queda en `output/evaluacion-core-v3-metadata-aware.json`. |
| 2026-08-04 | Se recargó producción con `core-v3` después de respaldar `libras-docs`. | La carga se ejecutó por lotes conservando rutas relativas. Verificación directa: 2,665 registros, 284 documentos y 50 MB de cuota con 26.6 MB de almacenamiento y 33.3 MB de vector. El respaldo está en `output/backup-libras-docs-20260804.jsonl.gz`. |
| 2026-08-04 | La primera evaluación productiva del índice recargado obtuvo 3/5. | RAG-01 y RAG-02 pasan; RAG-03 fue filtrado por cobertura literal y SCOPE-01 aceptó un Readme tangencial. Se ajustó la cobertura genérica para variantes morfológicas, contexto/tokens y mínimo de dos conceptos en consultas con país. Falta repetir la evaluación productiva. |
| 2026-08-04 | Se repitió el corpus productivo después del ajuste de cobertura. | 5/5 casos aprobados, recall 1.0 y abstención correcta 1.0. RAG-01/RAG-02 recuperan `Gestion de documentos.pdf`; RAG-03 recupera el procedimiento de vacaciones negativas; SCOPE-01/SCOPE-02 se abstienen sin evidencia autorizada. Las 138 pruebas automatizadas también pasan. |
| 2026-08-04 | Se incorporaron al corpus los casos reales del PDF y se endureció la evidencia directa. | La validación ahora exige coocurrencia local entre sujeto y operación, reconoce acciones conjugadas y rechaza tablas de contenido/índices como respuesta. El corpus productivo ampliado obtiene 8/8, con recall y abstención de 1.0; 140 pruebas automatizadas pasan. |
| 2026-08-04 | Se publicó la revisión correctiva en `app-libras-prod` mediante ZipDeploy y se reinició el servicio. | El despliegue finalizó sin errores. `/healthz` devuelve `ok` y `/readyz` confirma `production`, Azure AI Search configurado y obligatorio. Falta la prueba funcional desde Teams. |
| 2026-08-04 | Se validó el camino de memoria durable con la documentación oficial de OpenAI. | Conversations API con Responses API es adecuado para estado compartido entre sesiones, pero requiere un mapeo persistente y política de retención/borrado antes de activarse. |
| 2026-08-04 | Se detectó que las preguntas sobre parámetros de prórroga devolvían una introducción o relaciones DB en vez de la sección concreta. | Se añadió búsqueda léxica compacta, preferencia de encabezados de fragmento y manejo de cláusulas relativas. Las tres formulaciones recuperan primero `Acciones de personal.pdf — Página 18`; no requiere reindexación. |
| 2026-08-04 | Se publicó el ajuste de prórroga de contratos en `app-libras-prod`. | Despliegue remoto finalizado sin errores; `/healthz=ok` y `/readyz=ready` con Azure AI Search configurado. El corpus ampliado obtiene 10/10 y la suite completa tiene 142 pruebas exitosas. |
| 2026-08-04 | Se detectó una diferencia entre preguntas interrogativas e imperativas con la misma evidencia. | Las solicitudes como “Dame los parámetros…” ahora se reconocen como preguntas documentales directas, sin dejar que el clasificador las convierta en abstención. Se publicó la corrección; 143 pruebas pasan y `/readyz=ready`. |
| 2026-08-04 | Una pregunta de validación DTC tras reinstalación fue descartada aunque el manual estaba indexado. | Se separó la circunstancia temporal (“después de reinstalar”) de la acción realmente solicitada y se normalizó la familia revisar/validar/verificar/confirmar. El caso recupera `Manual DTC Verificacion.pdf` páginas 3 y 4. |
| 2026-08-05 | Se verificó la consulta DTC desde Teams después de una publicación limpia del App Service. | Libras recupera `Manual DTC Verificacion.pdf` páginas 3, 4 y 5. La respuesta cita la validación de firewall/DTC en ambos servidores; la recuperación, procedencia y enlace ya son correctos. Queda como mejora futura sintetizar también servicios y `Local DTC` de las tres páginas. |
| 2026-08-05 | Prueba aleatoria desde Teams sobre `Upgrade 1.24.1.1`. | La primera respuesta usó portada/tabla de contenido como evidencia. Se añadió regresión para rechazar navegación en preguntas sustantivas; la corrección recupera una instrucción directa de respaldo en la página 6 y conserva fuente/enlace de SharePoint. |
| 2026-08-05 | Pruebas aleatorias desde Teams sobre `Reiniciar appjob` y `Ofuscación de datos.sql`. | Appjob recupera la instrucción de reinicio, pero no demuestra la validación posterior; la consulta directa de ofuscación no recupera el SQL autorizado. Se añadió `RAG-08` para este último caso. La evaluación productiva ampliada queda en 9/12 (recall 0.778; abstención correcta 0.667); `RAG-03`, `RAG-06` y `RAG-08` quedan pendientes de corregir en ranking/cobertura e índice. |
| 2026-08-05 | Se publicó el filtro refinado de navegación en `app-libras-prod` mediante OneDeploy `a0efcafa-d916-481c-a18d-3b0300a0bb61`. | Despliegue sin errores; `/healthz=200` y `/readyz=200`. La suite automatizada queda en 146 pruebas exitosas. No se reindexó producción: el fallo de los SQL requiere una corrección separada y reversible de recuperación/índice. |

## Reconstrucción v2 — estado de implementación (2026-08-05)

Se implementó localmente una estrategia reversible `RETRIEVAL_STRATEGY=v2`.
La estrategia queda desactivada por defecto (`legacy`) y el índice productivo
no ha sido modificado durante esta fase.

- `QueryPlan` separa requisitos, versión, artefacto e identificadores; las
  cláusulas de contexto se omiten de forma determinista y las paráfrasis
  funcionales se normalizan sin relacionarlas con un documento concreto.
- La recuperación une vector, consulta completa y conceptos normalizados antes
  de validar; la diversidad se aplica después de evaluar los fragmentos para
  no expulsar la página factual de un documento grande.
- Una fuente v2 solo se emite si un fragmento cubre un requisito. Portadas,
  índices y documentos de enlaces se excluyen. Las respuestas incompletas
  informan los requisitos no demostrados y no enlazan fuentes tangenciales.
- La ingesta nueva agrega texto de recuperación, rol de artefacto, calidad y
  metadatos revisados. Los SQL se separan por declaración y preservan los
  identificadores de procedimientos. Los campos funcionales solo se leen del
  bloque explícito `libras` del sidecar, nunca de una inferencia automática.
- El verificador semántico opcional (`USE_LLM_EVIDENCE_VERIFIER=true`) está
  limitado a ocho documentos candidatos y falla cerrado. Debe conservar las
  anclas técnicas del requisito y, para código, el nombre de la operación.

### Evidencia de la candidata local

Se construyó una candidata local reproducible sobre `data/sharepoint`: 722
archivos produjeron 4,575 fragmentos y embeddings de 512 dimensiones. La cola
focalizada contiene 343 documentos: 22 dominantes, 30 duplicados y 93 scripts
sin operación estructural. Los SQL de vacaciones y ofuscación están incluidos.

La evaluación con verificación semántica y el corpus vigente terminó en 8/12:
recuperación top-3 0.60, fuente directa correcta 0.60, abstención correcta 1.0
y ninguna fuente sin evidencia validada. No supera las puertas de promoción
(0.90/0.95/0.95/0), así que quedan prohibidos el respaldo con fines de cambio,
la reconstrucción de `libras-docs`, la activación de v2 y cualquier despliegue
en `app-libras-prod` hasta una nueva medición aprobada.

El caso `RAG-06` se corrigió en el contrato: la página 37 de `Acciones de
personal.pdf` sí documenta directamente los parámetros de riesgos de
incapacidad. El SQL de vacaciones permanece pendiente de aprobación humana:
el identificador `vac` no se expandirá automáticamente a una operación
funcional.

### Siguiente ventana autorizable

1. Completar la revisión humana de los 343 documentos focalizados mediante
   `src/apply_index_review.py`, empezando por los SQL críticos, duplicados y
   documentos dominantes.
2. Ampliar el conjunto de retención estratificado y repetir
   `src/evaluate_local_retrieval_candidate.py` con 512 dimensiones y el
   verificador semántico habilitado. No ajustar el ranking con sus paráfrasis.
3. Solo si todas las puertas pasan, restaurar conectividad de Azure, exportar
   `libras-docs` con `src/backup_search_index.py`, verificar su manifiesto,
   reconstruir con `src/azure_search_ingest.py --reset-index`, habilitar v2 y
   validar desde Teams. `src/restore_search_index.py --reset-index` es la ruta
   de reversión verificada por conteo y hash.

| Fecha | Cambio o evidencia | Resultado |
|---|---|---|
| 2026-08-05 | Se implementó la reconstrucción v2, cola de revisión, respaldo/restauración verificables y candidata local reanudable. | 156 pruebas automatizadas pasan. La estrategia continúa en `legacy`; no se modificó ni desplegó producción porque las puertas de calidad fallan. |
| 2026-08-05 | Se comprobó el candidato local completo con 512 dimensiones y verificación semántica limitada. | La abstención alcanza 100% y no hay fuentes no validadas, pero la recuperación/fuente directa es 60%; promoción bloqueada. |
| 2026-08-05 | Se incorporaron las brechas observadas en la prueba funcional de Teams: solicitud de credenciales, listado total del sitio y evidencia de intención tangencial. | Las solicitudes con “pasar” credenciales y “listar” documentos se bloquean antes de recuperar evidencia. Un changelog no responde requisitos de software, un tipo documental no responde un procedimiento de versionado y una frase sin detalle no responde una lista de parámetros. Los SQL se resumen sin pegar código ejecutable. La suite completa tiene 181 pruebas exitosas; no se desplegó producción. |
| 2026-08-05 | Se corrigió la composición de diagnósticos documentales. | Libras reúne validaciones completas de varias páginas y las presenta como lista numerada. Un encabezado truncado no se usa como respuesta para una solicitud de servicios o validaciones. La suite completa tiene 183 pruebas exitosas; no se desplegó producción. |
| 2026-08-05 | Se ajustó la recuperación de precauciones de actualización y el límite de diagnóstico de descargas. | Las preguntas previas a instalar una actualización buscan también los encabezados documentales de preparación, respaldo y configuración; una regresión valida la recuperación de esa evidencia. Una ruta normal de descarga ya no se presenta como solución cuando el usuario reporta que la descarga falla: para ello se exige evidencia diagnóstica explícita. La suite completa tiene 184 pruebas exitosas; no se desplegó producción. |
| 2026-08-05 | Se amplió y validó la candidata local v2 con los casos observados en Teams. | El corpus pasó de 12 a 14 casos e incluye precauciones de actualización y descarga fallida. Se reforzó el anclaje semántico para conservar equivalencias operativas legítimas sin asociar encabezados o tablas de base de datos con acciones funcionales no documentadas. La evaluación final con verificador semántico obtuvo 14/14, recuperación/fuente directa/abstención de 1.0 y cero fuentes no sustentadas; p95 local de 10.9 s. La suite completa tiene 188 pruebas exitosas. La promoción o despliegue sigue sin ejecutarse. |
| 2026-08-05 | Se acotó el piloto productivo sin reindexar. | `app-libras-prod` solo autoriza ReadME Hotfixes, Documentos/SOLUCIONES, Manuales y Scripts de Apoyo mediante pares `drive_id`/`folder_path`. Se excluyeron las demás bibliotecas, incluidos los nueve documentos curados de Documentos de Apoyo para no habilitar la biblioteca completa. El índice se preservó con 2,665 fragmentos, existe respaldo previo verificable y `/healthz`/`/readyz` devolvieron HTTP 200. |
| 2026-08-06 | Se corrigió la respuesta de AppJob y se endureció el tratamiento de procedencia heredada. | La inspección del índice confirmó que `Configuración SMTP Evolution - 1.19.docx` pertenece a `SOLUCIONES`; el problema no era una fuga de Documentos de Apoyo sino un fragmento excesivamente amplio. Los registros heredados sin `drive_id`/`folder_path` ahora fallan cerrados salvo que su URL pruebe una de las cuatro bibliotecas del piloto. Los documentos con pasos numerados se recortan al paso pertinente, evitando exponer configuración SMTP incidental. Las regresiones y la suite completa pasan con 190 pruebas. Se publicaron OneDeploy `a5ce4d3b-7512-4181-8cde-e9bc3c1cb78b` y `d3d07873-1b24-4d71-9d7a-8a3eb9e8b874`; `/healthz` y `/readyz` devolvieron HTTP 200. La confirmación visual posterior desde Teams queda pendiente porque el navegador agotó su espera al leer el chat. |
| 2026-08-06 | Se habilitó la relación entre carpetas descriptivas y archivos genéricos. | La recuperación deriva en memoria el trayecto padre desde la URL segura de SharePoint y lo usa como contexto y señal de ranking; una carpeta con tres o más conceptos coincidentes prevalece sobre menciones incidentales. Los diagnósticos concretos ejecutan una pasada acotada por prefijos para reconocer rutas CamelCase como `TiempoNoTrabajado`. La consulta “Tengo un error de fechas en tiempos no trabajados” se verificó contra el índice productivo y devuelve únicamente `Indicaciones.txt` con su enlace y solución. El plan Free rechazó toda escritura por cuota agotada, por lo que no se borró ni reindexó ningún documento; el arreglo no depende de ello. La suite completa tiene 195 pruebas exitosas y OneDeploy `4ad6c6cc-e229-45e5-9b97-47ce2168901e` quedó completado; `/healthz` y `/readyz` devolvieron HTTP 200. |
| 2026-08-06 | Se añadieron enlaces a los archivos relacionados de cada solución. | Junto al enlace del archivo citado, Teams muestra `Archivos relacionados` con la vista nativa `Forms/AllItems.aspx` de su carpeta de SharePoint. `SHAREPOINT_FOLDER_CTID` configura el identificador de la biblioteca para construir el enlace completo. La publicación inicial quedó bloqueada al descargar `uv` durante la compilación rápida y produjo 503; se desactivó esa ruta, se republicó como OneDeploy `861c6d13-022a-406d-9b2c-7f368c5be698` y `/healthz`/`/readyz` volvieron a HTTP 200. La suite completa tiene 196 pruebas exitosas. |
| 2026-08-06 | Se normalizó la codificación de la URL de carpeta. | El enlace `AllItems.aspx` codifica los segmentos de ruta, incluido `Documentos%20compartidos`, para coincidir con la URL nativa de SharePoint. OneDeploy `7a7e809b-317c-4864-bff6-bea92f8c5f9f` terminó correctamente y `/healthz`/`/readyz` devolvieron HTTP 200. |
| 2026-08-06 | Se incorporaron las columnas descriptivas de SharePoint para scripts. | El sincronizador lee `Detalle`/`Description` y `Dependencia` para archivos `.sql`, `.ps1` y `.bat`, los agrega al contexto y tokens de búsqueda, y Libras los usa para explicar el propósito del script sin mostrar código ejecutable. La suite completa tiene 201 pruebas exitosas. OneDeploy `33e20f68-b119-45f0-a875-9a5f579f3bcd` terminó correctamente; `/healthz` y `/readyz` devolvieron HTTP 200. El script ya existente aún requiere liberar cuota del índice Free y ejecutar una actualización controlada para que esta descripción quede disponible en producción. |
| 2026-08-06 | Se reconstruyó `libras-docs` para mantener el piloto dentro de la cuota Free. | Se eliminó el índice candidato `libras-docs-v2-candidate` (2,671 fragmentos), se creó un respaldo reducido y se restauraron 1,326 fragmentos de `ReadME Hotfixes`, `SOLUCIONES` y `Scripts de Apoyo`. `Manuales` queda temporalmente fuera del índice por capacidad, pero no se eliminó de SharePoint. `acc.proc_arreglar_vac_negativos.sql` quedó indexado con su descripción de `Detalle`; el índice devuelve 1,326 documentos y `/healthz`/`/readyz` responden HTTP 200. El respaldo original permanece en `output/backup-libras-pre-duplicados-20260806`. |
