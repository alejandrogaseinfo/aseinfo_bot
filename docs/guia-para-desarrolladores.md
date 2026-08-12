# Guía para desarrolladores de Libras

Esta guía es para quien necesita entender el código que atiende Libras en
producción. No sustituye la configuración de Azure ni contiene secretos. Para
el estado operativo más reciente, consulta primero
[contexto-actual.md](contexto-actual.md).

En producción la estrategia sigue siendo `legacy`; el verificador de evidencia
y el redactor grounded son opt-in y permanecen apagados. Cualquier cambio en
esas banderas requiere evaluación A/B, revisión humana y autorización
explícita.

## Qué hace Libras

Libras es un bot personal de Microsoft Teams para consultar documentación
interna autorizada. Ante cada mensaje:

1. recibe la actividad de Teams;
2. aplica barreras de seguridad y alcance;
3. clasifica la intención;
4. recupera evidencia desde Azure AI Search;
5. verifica que la evidencia sea suficiente y autorizada;
6. construye una respuesta con enlace a la fuente o se abstiene.

La regla central es: si no hay evidencia suficiente, Libras no inventa una
respuesta técnica.

## Arquitectura productiva

```text
Teams / Agents Playground
        |
        v
Azure Bot -> app-libras-prod -> src/app.py -> src/agent.py
                                                |
                                                v
                                      src/handler.py
                                  /       |        \
                                 v        v         v
                         seguridad  intención  recuperación
                                                   |
                                                   v
                                           Azure AI Search
                                                   |
                                                   v
                                      clasificación y evidencia
                                                   |
                                                   v
                                           respuesta Teams

SharePoint -> sincronización separada -> Azure AI Search
```

La aplicación que responde consultas no sincroniza documentos durante cada
mensaje. La ingesta de SharePoint es un proceso separado y escribe en el
índice. La respuesta consulta el índice y el modelo solo después de pasar las
barreras locales.

## Recorrido del código

### Entrada y host HTTP

- `src/app.py` expone `/api/messages`, `/healthz` y `/readyz`.
- `src/agent.py` carga el entorno, crea el cliente de OpenAI y registra el
  manejador de actividades de Teams.
- `on_message()` normaliza comandos, recupera el contexto efímero del chat,
  llama a `process_user_message()` y envía la respuesta.

### Orquestación de una consulta

- `src/handler.py` contiene `process_user_message()`.
- Antes de buscar, rechaza solicitudes de secretos, datos confidenciales,
  bibliotecas fuera de alcance e intentos de alterar las instrucciones.
- Las preguntas de saludo, ayuda, capacidades o contexto insuficiente pueden
  resolverse por la ruta conversacional.
- Las consultas documentales pasan a intención, recuperación, clasificación y
  formateo.

### Intención y experiencia conversacional

- `src/intent.py` clasifica la intención estructurada y usa reglas de respaldo.
- `src/guided_experience.py` implementa el menú inicial y los comandos como
  `/ayuda`, `/version`, `/procedimiento`, `/actualizacion` y `/nuevo`.
- `src/conversation_state.py` mantiene únicamente contexto efímero por chat:
  tema, producto, versión, fuente y última respuesta documental apta para
  referencias como “esa versión” o “lo anterior”.
- `USE_OPENAI_CONVERSATIONS` debe permanecer en `false`: la Conversations API
  es una capacidad futura, no la memoria activa de producción.

### Recuperación y evidencia

- `src/retrieval.py` decide entre el índice Markdown local y Azure AI Search.
- `src/azure_search.py` construye consultas, filtros, ranking, cobertura y
  validación de procedencia.
- `src/document_index.py` es el respaldo local para desarrollo; no debe
  sustituir Azure AI Search en producción.
- `src/evidence_verifier.py` y las reglas de clasificación ayudan a evitar
  que un fragmento relacionado pero insuficiente se presente como respuesta.
- `src/formatting.py` convierte la decisión en texto y enlaces legibles para
  Teams.

### Ingesta de documentos

- `src/sharepoint_sync.py` lee las bibliotecas autorizadas de SharePoint.
- `src/azure_search_ingest.py` transforma documentos en registros y los carga
  al índice.
- `src/document_index.py` y los scripts `src/*index*` sirven para evaluar o
  reconstruir datos localmente.
- No copies PDFs sincronizados ni manifiestos de datos al repositorio: `data/`
  está excluido por `.gitignore`.

## Configuración importante

La configuración se centraliza en `src/config.py` y se documenta en
`.env.example`. En producción, los valores sensibles llegan desde Azure
Key Vault o identidades administradas.

| Área | Variables principales | Producción |
| --- | --- | --- |
| Entorno | `LIBRAS_ENV`, `LIBRAS_RUNTIME_REVISION` | `production`, revisión desplegada |
| Búsqueda | `REQUIRE_AZURE_SEARCH`, `AZURE_SEARCH_ENDPOINT`, `AZURE_SEARCH_INDEX_NAME` | Azure AI Search obligatorio |
| Identidad de búsqueda | `AZURE_SEARCH_USE_ENTRA_ID` | `true`; la aplicación usa RBAC |
| Modelo | `OPENAI_MODEL`, `OPENAI_INTENT_MODEL` | OpenAI oficial mediante Key Vault |
| Recuperación | `RETRIEVAL_STRATEGY` | actualmente `legacy` hasta promover v2 |
| Contexto | `USE_EPHEMERAL_THREAD_CONTEXT` | `true`, acotado al chat |
| Conversations API | `USE_OPENAI_CONVERSATIONS` | `false` |

Nunca agregues valores reales a `.env.example`, documentación, pruebas,
logs, parámetros de infraestructura o commits.

## Desarrollo local

Desde la raíz del repositorio:

```powershell
py -3.11 -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r src/requirements.txt
Copy-Item .env.example .env
python -m unittest discover -s tests -v
python src/app.py
```

El servidor local escucha en `http://127.0.0.1:3978`. Para probar solo el
backend se pueden revisar `http://127.0.0.1:3978/healthz` y
`http://127.0.0.1:3978/readyz`. La prueba real dentro de Teams requiere los
archivos generados por Microsoft 365 Agents Toolkit en `env/`; esos archivos
no se versionan.

Para una ejecución local sin Azure AI Search, conserva
`REQUIRE_AZURE_SEARCH=false` y usa el índice Markdown de respaldo. Esa ruta
sirve para desarrollar y probar; no representa la configuración productiva.

## Diagnosticar una búsqueda de Azure AI Search

Para ver la evidencia exacta que Libras entregaría al resto del flujo, ejecuta
localmente la utilidad de solo lectura con una identidad que tenga acceso al
índice. No es un comando disponible en Teams y no escribe en Azure:

```powershell
python src/debug_retrieval.py --question "dime en que version se utilizó el jquery"
```

La salida JSON separa `candidatos_crudos_de_azure` de
`evidencia_que_recibe_el_bot`. Incluye documento, enlace, fragmento y puntaje
de los candidatos de Azure, junto con los descartes de Libras. Así se puede
distinguir entre “Azure devolvió un candidato no pertinente” y “Libras lo
descartó por versión, procedencia o falta de evidencia directa”.
Ejecutarlo solo en una consola autorizada: el fragmento documental se imprime
en pantalla para facilitar la revisión.

## Cómo leer y modificar el proyecto

Una modificación de comportamiento normalmente sigue este orden:

1. agregar o actualizar un caso en `tests/`;
2. cambiar la capa responsable, no `src/agent.py` salvo que sea entrada o
   salida de Teams;
3. verificar que una consulta sin evidencia siga absteniéndose;
4. verificar que una fuente fuera de alcance no pueda convertirse en evidencia;
5. ejecutar toda la suite;
6. probar una consulta positiva y otra negativa en Web Chat o Teams antes de
   desplegar.

Puntos habituales de extensión:

- nueva intención: `src/intent.py` y sus pruebas;
- nueva regla de seguridad: `src/handler.py` y pruebas de rechazo;
- nueva estrategia de búsqueda: `src/azure_search.py`, `src/retrieval.py` y
  corpus de calidad;
- nueva presentación: `src/formatting.py` y pruebas de respuestas Teams;
- nueva fuente documental: primero actualizar alcance, permisos e ingesta;
  no conectarla directamente desde el manejador de mensajes.

## Validación antes de producción

Ejecuta como mínimo:

```powershell
python -m unittest discover -s tests -v
python src/preflight.py --stage platform
git diff --check
```

En un entorno productivo también hay que comprobar:

- `/healthz` y `/readyz` devuelven estado correcto;
- una pregunta con evidencia devuelve un enlace SharePoint autorizado;
- una pregunta sin evidencia no inventa información;
- una solicitud de secreto se rechaza antes de Azure AI Search;
- una biblioteca fuera de alcance se rechaza;
- el flujo funciona en Web Chat y en Teams.

## Qué no está activo

- ClickUp, GitHub y Jira no son fuentes consultadas por producción.
- El MCP de `downloads.aseinfo.net` es una fase posterior.
- Conversations API y Azure Table Storage están preparados como propuesta
  futura, pero no deben activarse sin aprobar retención, permisos, limpieza y
  pruebas de aislamiento.
- `RETRIEVAL_STRATEGY=v2` requiere validar el corpus y sus puertas de calidad
  antes de promoverlo.

## Archivos que no deben subirse

No subas `.env`, `env/.env.*`, PDFs sincronizados, caches, logs, ZIPs de
trabajo, secretos ni datos reales de usuarios. Antes de compartir el repositorio
revisa `git status` y confirma que no haya archivos locales pendientes fuera de
la documentación o código que quieras entregar.
