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

## Levantar El Bot Localmente

Para probar el bot con el Playground, ejecute dos terminales distintas dentro de `C:\aseinfo_bot\Aseinfo_bot`.

Terminal 1: Playground de Microsoft 365 Agents Toolkit

```powershell
C:
cd C:\aseinfo_bot\Aseinfo_bot
${env:PATH}='C:\aseinfo_bot\Aseinfo_bot/devTools/nodejs;C:\WINDOWS\system32;C:\WINDOWS;C:\WINDOWS\System32\Wbem;C:\WINDOWS\System32\WindowsPowerShell\v1.0\;C:\WINDOWS\System32\OpenSSH\;C:\Program Files\Microsoft SQL Server\170\Tools\Binn\;C:\Program Files\Microsoft SQL Server\Client SDK\ODBC\170\Tools\Binn\;C:\Program Files\dotnet\;C:\Program Files (x86)\Microsoft SQL Server\160\Tools\Binn\;C:\Program Files\Microsoft SQL Server\160\Tools\Binn\;C:\Program Files\Microsoft SQL Server\160\DTS\Binn\;C:\Program Files\Git\cmd;C:\Program Files\Microsoft SQL Server\150\Tools\Binn\;C:\ProgramData\chocolatey\bin;C:\Program Files\GitHub CLI\;%NVM_HOME%;%NVM_SYMLINK%;C:\Users\jgarcia\AppData\Local\Microsoft\WindowsApps;C:\Users\jgarcia\.dotnet\tools;C:\Users\jgarcia\AppData\Local\Programs\Microsoft VS Code\bin;C:\Users\jgarcia\AppData\Roaming\npm;C:\Users\jgarcia\AppData\Local\Python\bin;C:\Users\jgarcia\AppData\Local\nvm;C:\nvm4w\nodejs;C:\Users\jgarcia\.local\bin;c:\users\jgarcia\appdata\roaming\python\python314\scripts'
${env:NODE_OPTIONS}=' --require "c:/Users/jgarcia/AppData/Local/Programs/Microsoft VS Code/4fe60c8b1c/resources/app/extensions/ms-vscode.js-debug/src/bootloader.js"  --inspect-publish-uid=http'
${env:VSCODE_INSPECTOR_OPTIONS}=':::{"inspectorIpc":"\\\\.\\pipe\\node-cdp.27852-b29f80ce-4.sock","deferredMode":false,"waitForDebugger":"","execPath":"C:\\nvm4w\\nodejs\\node.exe","onlyEntrypoint":false,"autoAttachMode":"always","fileCallback":"C:\\Users\\jgarcia\\AppData\\Local\\Temp\\node-debug-callback-1998bd6a194f1924"}'
& 'C:\nvm4w\nodejs\node.exe' '--experimental-network-inspection' '.\devTools\playground\node_modules\@microsoft\m365agentsplayground\cli.js' 'start'
```

Terminal 2: backend Python del bot

```powershell
cd C:\aseinfo_bot\Aseinfo_bot
.venv\Scripts\Activate.ps1
python src\app.py
```

Notas:

- El backend debe quedar escuchando en `http://127.0.0.1:3978/api/messages`.
- Si el Playground responde con una version vieja, reinicie `python src\app.py` y recargue el Playground.
- El comando del Playground incluye variables inyectadas por VS Code. Si cambia el entorno de depuracion, ese bloque puede necesitar actualizarse.

## Notas De Configuracion

- `websiteUrl`, `privacyUrl` y `termsOfUseUrl` del manifest estan en modo provisional con placeholders validos para desarrollo.
- El branding visual todavia es temporal. El color principal del manifest ya fue alineado a verde.
- La integracion real con ClickUp y Jira aun no esta activa en esta fase.
- Los secretos deben guardarse en `env/.env.local.user`, `env/.env.dev.user` o `env/.env.playground.user`. No deben escribirse manualmente en `/.env`.
- La base documental puede leerse desde OpenAI Vector Stores usando `OPENAI_VECTOR_STORE_ID`. Si esa variable no existe o la consulta falla, el bot vuelve al indice Markdown local.
- ClickUp puede habilitarse como fuente de consulta de solo lectura con `CLICKUP_API_TOKEN` y `CLICKUP_LIST_ID`. Si esta configurado, el bot intenta recuperar tareas relacionadas desde esa lista antes de usar el `vector store` o el indice local.

## ClickUp Como Fuente De Consulta

La integracion agregada para ClickUp es solo de lectura y usa la API oficial de ClickUp.

Variables requeridas:

- `CLICKUP_API_TOKEN`: token personal u OAuth valido para leer la lista.
- `CLICKUP_LIST_ID`: id numerico de la lista a consultar.

Variable opcional:

- `CLICKUP_WORKSPACE_ID`: identificador del workspace. Se deja disponible para futuras ampliaciones, aunque la lectura base por lista no lo requiere.

Ejemplo para tu caso actual:

```text
CLICKUP_LIST_ID=901414306756
CLICKUP_WORKSPACE_ID=9014703526
```

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
