# Chat-Salvador

Chat-Salvador es un bot para Microsoft Teams orientado a operaciones y soporte tecnico. Su objetivo es responder consultas sobre errores, hotfixes, advertencias de actualizacion y antecedentes tecnicos con base en evidencia recuperada desde fuentes documentales y, en fases posteriores, desde ClickUp, Jira y diffs de codigo.

## Estado Actual

La base del proyecto ya fue adaptada para:

- usar identidad real del bot en Teams,
- responder en español con tono formal,
- clasificar casos en `resuelto`, `en_progreso`, `similar_del_pasado` o `sin_evidencia`,
- devolver una respuesta estructurada con evidencia y siguiente accion,
- y dejar `retrieval` como stub inicial para no bloquear el prototipo.

## Arquitectura Inicial

- [src/agent.py](./src/agent.py): punto de entrada del agente en Teams.
- [src/handler.py](./src/handler.py): orquestacion del flujo de consulta.
- [src/retrieval.py](./src/retrieval.py): recuperacion inicial simulada de evidencia.
- [src/classification.py](./src/classification.py): clasificacion estructurada con OpenAI.
- [src/formatting.py](./src/formatting.py): construccion de la respuesta visible al usuario.
- [src/logging_utils.py](./src/logging_utils.py): logger base.
- [src/models.py](./src/models.py): modelos internos del flujo.

## Prerrequisitos

- Python 3.11.x
- Microsoft 365 Agents Toolkit
- Cuenta de desarrollo para Microsoft 365
- Clave de OpenAI en `OPENAI_API_KEY`
- ID del vector store en `OPENAI_VECTOR_STORE_ID`

## Ejecucion Local

1. Crear y activar un entorno virtual de Python.
2. Instalar dependencias desde [src/requirements.txt](./src/requirements.txt).
3. Configurar variables de entorno para el entorno local.
4. Ejecutar el proyecto desde el flujo de depuracion de Microsoft 365 Agents Toolkit.

## Notas De Configuracion

- `websiteUrl`, `privacyUrl` y `termsOfUseUrl` del manifest estan en modo provisional con placeholders validos para desarrollo.
- El branding visual todavia es temporal. El color principal del manifest ya fue alineado a verde.
- La integracion real con ClickUp y Jira aun no esta activa en esta fase.
- Los secretos deben guardarse en `env/.env.local.user`, `env/.env.dev.user` o `env/.env.playground.user`. No deben escribirse manualmente en `/.env`.
- La base documental puede leerse desde OpenAI Vector Stores usando `OPENAI_VECTOR_STORE_ID`. Si esa variable no existe o la consulta falla, el bot vuelve al indice Markdown local.

## Base Documental Local

La Fase 4 arranca con un MVP documental local en [docs/knowledge-base](./docs/knowledge-base), que permite:

- cargar documentos Markdown base,
- fragmentarlos por secciones,
- recuperar coincidencias por terminos relevantes,
- y usarlos como evidencia antes de integrar Azure AI Search.

## Vector Store De OpenAI

El bot ya puede consultar un `vector store` de OpenAI como fuente principal de evidencia.

1. Configure `OPENAI_VECTOR_STORE_ID` en `env/.env.local.user` o en el entorno correspondiente.
2. Suba o sincronice los documentos hacia ese store.
3. Ejecute el bot normalmente.

Para sincronizar la base Markdown actual del proyecto hacia el `vector store`, ejecute:

```powershell
C:\aseinfo_bot\Aseinfo_bot\.venv\Scripts\python.exe C:\aseinfo_bot\Aseinfo_bot\src\vector_store_sync.py
```

El script reemplaza en el `vector store` los archivos Markdown con el mismo nombre presentes en [docs/knowledge-base](./docs/knowledge-base).
