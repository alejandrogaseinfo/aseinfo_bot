# Guía para entender Libras

Fecha de referencia: 3 de agosto de 2026.

Esta guía explica cómo está construido Libras, cómo obtiene información de
SharePoint, cómo responde una pregunta, qué puede hacer y cuáles son sus
limitaciones. Está basada en el código actual y en la arquitectura productiva
documentada. Cuando un documento del repositorio contiene cifras históricas,
se indica como tal.

## 1. Resumen ejecutivo

Libras es un asistente interno para Microsoft Teams que responde preguntas
técnicas usando documentación aprobada. Su funcionamiento principal es RAG
(Retrieval-Augmented Generation): primero recupera fragmentos relevantes de un
índice documental y después genera o clasifica una respuesta usando únicamente
la evidencia recuperada.

La idea más importante es esta:

```text
SharePoint
   │  ingesta separada: listar, descargar, extraer texto, fragmentar, indexar
   ▼
Azure AI Search: índice libras-docs
   ▲
   │  consulta: búsqueda vectorial + búsqueda por palabras + filtros de seguridad
   │
Microsoft Teams → Libras en Azure → respuesta con fuente y enlace SharePoint
```

SharePoint no se consulta en tiempo real cada vez que una persona escribe. La
información disponible para el bot depende de la última sincronización y carga
exitosa al índice.

## 2. Componentes principales

| Componente | Responsabilidad |
|---|---|
| Microsoft Teams / Azure Bot | Canal por el que llega el mensaje del usuario. |
| `src/agent.py` | Recibe actividades de Teams, identifica la conversación y envía la respuesta. |
| `src/app.py` | Host HTTP; expone `/api/messages`, `/healthz` y `/readyz`. |
| `src/handler.py` | Orquesta todo el flujo de una pregunta y aplica controles previos. |
| `src/sharepoint_sync.py` | Se autentica contra Microsoft Graph, recorre las fuentes aprobadas y descarga archivos legibles. |
| `src/azure_search_ingest.py` | Punto de entrada de la carga del staging local hacia Azure AI Search. |
| `src/azure_search.py` | Extrae texto, genera fragmentos y embeddings, crea/actualiza el índice y recupera evidencia. |
| Azure AI Search | Índice de producción que contiene fragmentos, embeddings, URLs y metadatos de origen. |
| OpenAI o proveedor compatible | Genera embeddings, clasifica intención y, cuando aplica, clasifica la respuesta. |
| `src/document_index.py` | Respaldo local de documentos Markdown, permitido solo fuera de producción. |
| `src/classification.py` | Decide si la evidencia permite responder y si el caso está resuelto, en progreso, histórico o sin evidencia. |
| `src/formatting.py` | Convierte la decisión interna en el texto visible en Teams. |

El mapa de archivos detallado está también en el [README del proyecto](../README.md).

## 3. Fuentes documentales y alcance

La configuración de las fuentes se hace mediante pares alineados de:

- `SHAREPOINT_DRIVE_IDS`: bibliotecas documentales.
- `SHAREPOINT_FOLDER_PATHS`: carpeta dentro de cada biblioteca.

Una ruta vacía representa la raíz de la biblioteca. El código exige que ambas
listas tengan el mismo número de elementos; si no coinciden, no forma fuentes
válidas.

Según el contexto vigente del proyecto, el alcance aprobado incluye:

- `ReadME Hotfixes`.
- Biblioteca `Documentos`, únicamente la carpeta `SOLUCIONES` y sus subcarpetas.
- `Legislaciones`.
- `Traslados OP/DE`.
- `Parches Adicionales`.
- `Documentos de Apoyo`.
- `Manuales`.
- `Scripts de Apoyo`.

`Hojas de Servicio` y `Teams Wiki Data` están fuera del alcance actual. El
control de recuperación no se basa solo en el nombre de la URL: valida
`source_system=sharepoint`, URL HTTPS, `drive_id` y `folder_path` contra la
lista aprobada.

La fuente de verdad para cambiar este alcance es
[`docs/contexto-actual.md`](contexto-actual.md), no una bitácora histórica.

## 4. Cómo se extrae información de SharePoint

### 4.1 Autenticación

El módulo `sharepoint_sync.py` soporta dos modos:

1. `delegated`: inicia un device flow y usa la cuenta de la persona que ejecuta
   el script. Sirve para desarrollo o validación puntual.
2. `application`: usa una App Registration corporativa mediante secreto y token
   de aplicación. Es el modo esperado para producción.

En producción, la aplicación debe tener `Sites.Selected` y permiso explícito de
lectura únicamente sobre el sitio aprobado. La identidad de ingesta es
independiente de la identidad del bot que atiende preguntas.

El bot no necesita el secreto de SharePoint para responder consultas: consume
Azure AI Search. El secreto de SharePoint pertenece únicamente al proceso de
ingesta y debe estar fuera del código, Git y logs.

### 4.2 Recorrido de bibliotecas y carpetas

El cliente usa Microsoft Graph sobre `/drives/{drive-id}`. Recorre la carpeta
configurada de forma recursiva, sigue las páginas de resultados de Graph y
conserva únicamente archivos con extensiones admitidas.

Extensiones admitidas actualmente:

```text
ASPX, BAT, CSV, DOCX, JSON, PDF, PS1, RDLC, SQL, TXT, XLSX, XML
```

Imágenes, vídeos, ejecutables, DLL, comprimidos y otros binarios no se cargan
porque no tienen una extracción de texto RAG confiable en esta implementación.

### 4.3 Descarga segura

Para cada archivo, Graph puede devolver una redirección temporal hacia
SharePoint. El código descarga esa URL sin reenviar el bearer token de Graph al
host de redirección. Esto evita entregar innecesariamente el token de Graph a
otro host.

### 4.4 Estado de sincronización

La sincronización mantiene archivos de estado en el staging:

- `.libras-sharepoint-sync-state.json`: estado de cada documento.
- `.libras-sharepoint-changes.json`: documentos nuevos o modificados pendientes.
- `.libras-sharepoint-deletions.json`: documentos eliminados pendientes de retirar del índice.

La identidad estable es el ID del elemento de SharePoint, no el nombre del
archivo. Cuando hay varias bibliotecas, se antepone el `drive_id` para evitar
colisiones entre elementos con el mismo ID en drives distintos.

Para detectar cambios se comparan, entre otros, `eTag`, URL, fecha de
modificación, drive y carpeta. Si un documento cambia, se vuelve a descargar.
Si se elimina, se conserva una notificación de borrado hasta que la ingesta
quite todos sus fragmentos de Azure AI Search.

## 5. Cómo se transforma un archivo en conocimiento buscable

El flujo de ingesta es:

```text
archivo SharePoint
  → archivo local de staging + metadata JSON
  → extracción de texto
  → páginas/secciones
  → fragmentos con solapamiento
  → embedding por fragmento
  → Azure AI Search
```

### Extracción por tipo

- PDF: `pypdf` extrae texto página por página.
- DOCX: se leen párrafos y tablas.
- XLSX: se recorren hojas y filas con valores calculados (`data_only=True`).
- TXT, CSV, SQL, XML, RDLC, ASPX, PS1, BAT y JSON: se leen como texto.

Cada fragmento conserva metadatos como:

- ID documental y `drive_item_id`.
- Nombre y URL HTTPS de SharePoint.
- `drive_id`, sitio y carpeta.
- `eTag`/versión y fecha de modificación.
- hash del contenido.
- tipo de archivo y número de fragmento.

### Fragmentación

El texto se divide aproximadamente en bloques de 450 palabras, con solapamiento
de 75 palabras y un límite de 6.000 caracteres. Esto permite buscar una parte
del documento sin enviar el archivo completo al modelo.

Además, cada fragmento recibe un contexto documental compacto de hasta 900
caracteres. La finalidad es que una página posterior conserve información
general que quizás solo aparecía en la portada.

### Índice y embeddings

Azure AI Search almacena, entre otros, estos campos:

```text
id, title, content, document_context, content_vector,
source_url, source_system, document_id, document_version,
last_modified, content_hash, document_type, folder_path,
drive_id, indexed_at, chunk_number, content_tokens
```

El embedding por defecto se genera con `text-embedding-3-small`. La
dimensionalidad se configura con `OPENAI_EMBEDDING_DIMENSIONS`; el valor por
defecto del código es 1.536, aunque la documentación de producción describe
una configuración piloto de 512 para ahorrar cuota. El valor usado al crear el
índice debe coincidir con el usado al generar embeddings.

La carga normal es incremental: procesa cambios pendientes y elimina
fragmentos obsoletos. `--reset-index` elimina y recrea el índice configurado,
por lo que es una operación administrativa que debe ejecutarse con cuidado.

## 6. Qué ocurre cuando el usuario hace una pregunta

### Paso 1: entrada y autenticación

Teams envía una actividad a `/api/messages`. El middleware valida el JWT de
Bot Framework. `/healthz` y `/readyz` son excepciones para permitir sondas de
salud sin autenticación conversacional.

### Paso 2: controles determinísticos antes de buscar

`handler.py` revisa primero si el mensaje:

- solicita claves API, contraseñas, tokens, secretos, credenciales o cadenas de conexión;
- pide datos de clientes, contratos, información personal, estados financieros o pagos;
- intenta enumerar archivos o hacer inventarios del sitio;
- menciona una biblioteca explícitamente fuera del alcance;
- es un comando de ayuda, saludo o pregunta simple sobre las capacidades del bot;
- es un resumen de la respuesta documental anterior.

Estos casos no necesitan consultar SharePoint ni Azure AI Search.

### Paso 3: guardia semántica opcional

`ContextGuard` puede usar un modelo pequeño para detectar inyección de
prompts, solicitudes fuera de alcance o intentos de realizar acciones. No es un
mecanismo de autorización y no recibe documentos ni secretos.

En el código está desactivado por defecto (`USE_CONTEXT_GUARD=false`). Si se
activa, puede operar en `observe` o `enforce`. En `observe` registra el resultado
pero deja continuar la consulta; en `enforce` puede bloquearla. Su política no
sustituye los filtros determinísticos.

### Paso 4: intención conversacional

Si está habilitado el clasificador LLM, clasifica el mensaje como:

```text
saludo | ayuda | consulta_documental | reporte_error | consulta_ambigua
```

Para las preguntas conversacionales, el router añade un propósito acotado:
`ayuda`, `capacidad`, `alcance` o `aclaracion`. Así puede interpretar frases
como “¿cómo me puedes apoyar?” o “¿sobre qué carpetas puedes buscar?” sin
ampliar indefinidamente la lista de intenciones. Las respuestas de capacidad y
alcance se generan de manera determinística y no consultan el índice. Las
fuentes visibles se configuran con `LIBRAS_SHAREPOINT_SOURCE_LABELS`; esa
variable debe contener etiquetas legibles y no IDs, secretos ni rutas internas.

Los saludos, ayudas y reportes demasiado ambiguos reciben una respuesta breve
sin búsqueda. Una pregunta factual sobre un procedimiento o documento se deja
pasar a recuperación aunque no mencione versión o módulo.

### Paso 5: recuperación en Azure AI Search

La búsqueda combina dos señales:

1. búsqueda vectorial: compara el significado de la pregunta con
   `content_vector`;
2. búsqueda lexical: busca palabras exactas en título, contenido y tokens
   normalizados.

Se combinan los candidatos y se reordenan con cobertura de conceptos, frases,
posición vectorial, posición lexical y anclas específicas. Una coincidencia
aislada o tangencial no basta.

Antes de aceptar evidencia se aplican filtros adicionales:

- procedencia SharePoint HTTPS y origen autorizado;
- biblioteca y carpeta autorizadas;
- país explícito, cuando la pregunta lo menciona y el texto permite distinguirlo;
- versión exacta, evitando confundir `1.19.1.10` con `1.19.1.0` o `1.19.1.13`;
- nombre exacto de archivo cuando el usuario lo solicita;
- sección específica de Readme cuando el índice contiene esa sección;
- cobertura de la acción solicitada, por ejemplo, no usar una guía de
  “creación de vacaciones” como evidencia de un procedimiento de “aprobación”.

Si el mejor resultado es demasiado débil, se devuelve una lista vacía de
evidencia. Los fragmentos relevantes se convierten en objetos
`EvidenceSource`; normalmente se conservan hasta tres resultados relevantes y
se eliminan duplicados antes de responder.

### Paso 6: clasificación de la respuesta

Con la evidencia recuperada, Libras usa el modelo principal cuando está
disponible. La instrucción exige devolver JSON y clasificar el caso como:

- `resuelto`: hay respuesta directa o solución documentada;
- `en_progreso`: hay seguimiento activo documentado;
- `similar_del_pasado`: existe un antecedente, pero no una resolución confirmada;
- `sin_evidencia`: la evidencia no alcanza para responder con seguridad.

El código siempre conserva una clasificación por reglas como respaldo. Si el
modelo contradice una regla crítica —por ejemplo, marca sin evidencia cuando
las reglas detectan una respuesta válida— se usa la decisión local. Las
consultas con una versión explícita se responden de forma determinística a
partir de los fragmentos citados para no sustituir detalles por un resumen
genérico.

### Paso 7: respuesta visible

Cuando hay evidencia, Teams recibe el resumen y el título de la fuente. Si la
fuente tiene una URL HTTP/HTTPS, también se muestra el enlace de SharePoint.

En preguntas procedurales, Libras convierte los marcadores imperativos en una
lista ordenada y elige una fuente principal según su cobertura de la consulta.
Una fuente secundaria solo se conserva si aporta al menos dos pasos nuevos;
en el índice legacy, que no tiene requisitos explícitos, se conserva solo la
fuente principal. Los fragmentos secundarios del índice v2 deben traer
requisitos cubiertos; así se descartan navegaciones repetidas o variantes
aisladas sin perder evidencia complementaria validada.

Cuando no hay evidencia suficiente, se muestra la limitación y no se muestran
fuentes tangenciales. El fragmento técnico completo y los metadatos internos no
se exponen en la respuesta normal.

## 7. Capacidades actuales

Libras puede:

- responder preguntas sobre procedimientos, manuales, hotfixes, actualizaciones y documentación técnica indexada;
- recuperar información de varias bibliotecas o carpetas aprobadas;
- buscar preguntas formuladas con lenguaje natural, combinando similitud semántica y coincidencia exacta;
- resolver consultas por nombre de archivo, versión y algunas secciones concretas;
- trabajar con PDF, Word, Excel y varios formatos de texto o código;
- proporcionar el título y el enlace verificable del documento de origen;
- resumir la respuesta documental anterior cuando el usuario pide una lista o resumen corto;
- resolver referencias documentales acotadas como “esa versión” o “dicha actualización” usando la versión explícita de la última respuesta documental;
- pedir contexto cuando un reporte de error es demasiado ambiguo;
- rechazar solicitudes de secretos, datos confidenciales, inventarios y bibliotecas fuera del alcance;
- continuar con reglas locales si el modelo LLM falla o supera el tiempo límite;
- exponer sondas de salud y readiness para operación en Azure.

## 8. Limitaciones importantes

### Frescura de la información

La respuesta no refleja automáticamente un cambio recién hecho en SharePoint.
Debe ejecutarse la sincronización y luego la ingesta. El repositorio contiene
los comandos CLI, pero no implementa por sí mismo un programador de tareas; la
frecuencia y el monitoreo del job son responsabilidad de la operación.

### Permisos por usuario

En el piloto, la aplicación de ingesta crea un índice común. Libras no replica
los permisos individuales de cada documento de SharePoint en cada pregunta.
Todo usuario que pueda utilizar el bot puede consultar todo lo que haya sido
indexado. Por eso el contenido debe ser interno general para la audiencia o se
debe implementar un diseño de autorización por usuario antes de incluir
información sensible.

### Calidad de extracción

- Un PDF escaneado o basado solo en imágenes normalmente no produce texto útil porque no hay OCR.
- En Excel se leen valores de celdas; no se conserva necesariamente la fórmula original ni el formato visual.
- La estructura compleja de Word, RDLC, ASPX o código puede perder presentación al convertirse a texto plano.
- Los archivos no soportados quedan fuera del índice.
- Un documento vacío o sin texto extraíble no se indexa.

### Calidad de búsqueda y respuesta

La recuperación puede no encontrar una respuesta si el documento usa términos
muy distintos, si la pregunta es ambigua o si el filtro de cobertura considera
que la coincidencia es insuficiente. Esto es deliberado: el bot prefiere
responder sin evidencia antes que presentar un documento relacionado como si
fuera una respuesta exacta.

El modelo puede cometer errores de interpretación, por lo que las respuestas
deben validarse contra el enlace citado. Los controles reducen alucinaciones,
pero no son una garantía matemática de exactitud.

### Dependencias y tiempos

La operación depende de Teams, Azure App Service, Azure AI Search, Microsoft
Graph durante la ingesta y el proveedor de modelos durante embeddings y
clasificación. Hay límites configurables para recuperación, intención,
clasificación, guardia y conversación. Un timeout puede producir una respuesta
de “sin evidencia” aunque el documento exista.

### Memoria conversacional

El seguimiento conversacional es deliberadamente acotado. El bot conserva solo
la última respuesta documental en memoria del proceso. Esto permite resolver
resúmenes como “resume esos cambios”, “¿cuáles son los puntos principales?” o
“explícalo de forma sencilla”. También reconoce referencias como “esa versión”,
“ese documento”, “ese hotfix” o “ese release”; cuando la respuesta anterior
menciona una versión explícita —por ejemplo, `1.19.1.10`— la agrega solo a la
búsqueda siguiente para evitar que se recupere una versión vecina. No se envía
todo el historial al LLM ni se mantiene una memoria persistente o una base de
historial.

La memoria se pierde al reiniciar el proceso y puede ser inconsistente si se
ejecutan varias instancias sin afinidad de conversación. Para obtener una
respuesta precisa, la pregunta de seguimiento debe realizarse en la misma
conversación y después de una respuesta documental que mencione claramente la
versión o el documento.

### Integraciones y acciones

Libras no navega por Internet, no consulta ClickUp, GitHub, Jira u otros
sistemas en el flujo actual, no modifica documentos, no ejecuta comandos y no
abre tickets. ClickUp/GitHub, Jira y el MCP de descargas están definidos como
fases posteriores, no como capacidades actuales.

### Archivos enviados por el usuario

El manifest de Teams declara `supportsFiles=false` y el código solo muestra un
aviso si esa opción se habilita. El flujo actual no analiza adjuntos enviados
en el chat como una fuente documental.

## 9. Configuración que controla el comportamiento

Las variables más relevantes están en `src/config.py` y `.env.example`:

```text
LIBRAS_ENV
REQUIRE_AZURE_SEARCH
ALLOW_LOCAL_DOCUMENT_FALLBACK
USE_AZURE_SEARCH_IN_LOCAL
OPENAI_MODEL
OPENAI_INTENT_MODEL
OPENAI_EMBEDDING_MODEL
OPENAI_EMBEDDING_DIMENSIONS
USE_LLM_INTENT_CLASSIFIER
USE_CONTEXT_GUARD
CONTEXT_GUARD_MODE
CONTEXT_GUARD_FAILURE_POLICY
RETRIEVAL_TIMEOUT_SECONDS
RETRIEVAL_GRACE_SECONDS
CLASSIFICATION_TIMEOUT_SECONDS
INTENT_TIMEOUT_SECONDS
CONVERSATION_TIMEOUT_SECONDS
AZURE_SEARCH_ENDPOINT
AZURE_SEARCH_INDEX_NAME
AZURE_SEARCH_API_KEY o AZURE_SEARCH_USE_ENTRA_ID
SHAREPOINT_AUTH_MODE
SHAREPOINT_TENANT_ID
SHAREPOINT_CLIENT_ID
SHAREPOINT_CLIENT_SECRET
SHAREPOINT_SITE_ID
SHAREPOINT_DRIVE_IDS
SHAREPOINT_FOLDER_PATHS
```

En producción, `REQUIRE_AZURE_SEARCH=true` y
`ALLOW_LOCAL_DOCUMENT_FALLBACK=false` evitan que una respuesta salga por
accidente de la base Markdown local. El bot de consulta debería tener permiso
`Search Index Data Reader`; la identidad de ingesta, separada, necesita
`Search Index Data Contributor`.

## 10. Cómo formular mejores preguntas

La recuperación mejora si la pregunta incluye:

- producto o módulo;
- versión exacta;
- nombre exacto del archivo, si se conoce;
- mensaje de error literal;
- acción que se quiere realizar;
- contexto de la biblioteca o carpeta, si es relevante.

Ejemplos:

```text
¿Qué pasos documenta el archivo Configuración de MiniProfiler en Evolution para la versión 1.10.0?

En el Readme 1.19.1.11, ¿qué nuevos requisitos de software se indican?

Al ejecutar el script X recibo el error Y en Evolution 1.19.1.10. ¿Qué corrección documentada existe?
```

Una pregunta como “tengo un problema” no identifica qué buscar. Una pregunta
como “¿cuál es el procedimiento oficial para aprobar vacaciones?” necesita un
documento que hable explícitamente de aprobación; una guía que solo hable de
crear vacaciones no es evidencia suficiente.

## 11. Operación y diagnóstico

Para validar el entorno sin revelar secretos:

```powershell
python src/preflight.py --stage platform
python src/preflight.py --stage data-access
python -m unittest discover -s tests -v
```

Para inspeccionar SharePoint sin descargar archivos:

```powershell
python src/sharepoint_sync.py --inventory
```

Para sincronizar e indexar una fuente aprobada:

```powershell
python src/sharepoint_sync.py --output-dir data/sharepoint
python src/azure_search_ingest.py --source-dir data/sharepoint --create-index
```

`--create-index` se usa para crear el índice si no existe. Para una migración
de esquema o reconstrucción completa se usa `--reset-index`, con revisión
previa porque borra y recrea el índice configurado.

Endpoints operativos:

- `/healthz`: el host está vivo.
- `/readyz`: están configurados el modelo y, en producción, Azure AI Search.
- `/api/messages`: endpoint protegido que recibe actividades de Teams.

Los logs registran duración, cantidad de evidencias, tipos de fuente y estado
de decisión. No deberían registrar la pregunta completa ni el contenido de los
fragmentos.

## 12. Estado de validación conocido

La suite local actual ejecutada el 5 de agosto de 2026 terminó con **168
pruebas aprobadas**. Cubre sincronización, extracción, metadatos, cambios y
eliminaciones, recuperación, versiones, nombres de archivo, filtros de
procedencia, controles de secretos, autorización HTTP, timeouts y rutas de
salud.

Esto demuestra que el comportamiento del código está cubierto por pruebas; no
reemplaza la validación operativa de extremo a extremo en Teams con un documento
real de SharePoint, una consulta sin evidencia, un documento actualizado y un
documento eliminado.

## 13. Resumen final

Libras es, esencialmente, tres sistemas coordinados:

1. un sincronizador controlado de SharePoint hacia staging;
2. un pipeline de extracción, fragmentación, embeddings e indexación en Azure AI Search;
3. un asistente de Teams que filtra la pregunta, recupera evidencia, clasifica
   la respuesta y muestra el enlace de origen.

Su fortaleza es la trazabilidad: no debería responder una consulta técnica sin
evidencia autorizada. Sus límites más importantes son la frescura dependiente
de la ingesta, la extracción imperfecta de formatos complejos y la ausencia de
permisos documentales individuales por usuario. Estos tres puntos deben formar
parte de cualquier decisión para ampliar el alcance del bot.
