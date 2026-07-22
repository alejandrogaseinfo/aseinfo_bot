# RAG con Azure AI Search y SharePoint sin permisos de administrador

Esta implementación mantiene el bot de Teams existente y añade dos pasos separados: sincronizar PDFs autorizados a una carpeta local controlada e indexarlos en Azure AI Search. El chat consulta primero Azure AI Search; si el servicio no está configurado, falla o no encuentra evidencia, conserva la base Markdown local como respaldo.

## Qué permisos hacen falta

No se requiere ser administrador global de Microsoft 365 ni de Azure.

| Componente | Mínimo necesario | Si no lo tienes |
|---|---|---|
| Teams local | Poder abrir el Agents Playground y cargar/ejecutar la app en el tenant | Pedir que habiliten el entorno de desarrollo o demostrar por el endpoint local |
| PDFs | Tu usuario debe tener lectura en la biblioteca y consentir `Files.Read.All` delegada para la app de sincronización | El permiso delegado no requiere consentimiento de administrador por defecto, pero una política del tenant puede impedir el consentimiento de usuario; no se debe usar una cuenta ajena |
| Azure AI Search existente | Clave de consulta para el bot; clave de administración o rol **Search Index Data Contributor** para la carga | Pedir que creen el recurso y te asignen sólo ese rol o una clave de ingesta |
| Crear Azure AI Search | `Contributor` sobre un grupo de recursos o suscripción | Usar temporalmente la base local; no intentar crear recursos con credenciales de otra persona |

Una cuenta Microsoft personal (Outlook/Hotmail) normalmente tiene OneDrive personal, no SharePoint Online. Si por “cuenta personal” te refieres a tu usuario de trabajo dentro de Microsoft 365, los pasos siguientes aplican. Si los PDFs están en OneDrive personal, se debe usar su `driveId` y una aplicación que admita cuentas Microsoft personales; la opción más sencilla para esta semana es copiarlos a una biblioteca de SharePoint o OneDrive for Business a la que tu usuario tenga acceso.

## Configuración mínima

1. Copiar `.env.example` a un archivo de usuario ignorado por Git, por ejemplo `env/.env.local.user`, y completar las variables de Azure AI Search.
2. Crear o reutilizar un registro de aplicación **público** en Microsoft Entra. Debe permitir flujo de dispositivo y tener permiso delegado de Microsoft Graph `Files.Read.All`. No se configura `client secret`.
3. Limitar `SHAREPOINT_FOLDER_PATH` a la carpeta de PDFs aprobados. Para tu propio OneDrive no necesitas buscar `driveId`: déjalo vacío y el script resuelve el drive del usuario que inicia sesión. Sólo se requiere `driveId` si vas a sincronizar una biblioteca distinta.
4. Instalar dependencias desde la raíz del proyecto:

```powershell
pip install -r src\requirements.txt
```

Para el acceso a Azure AI Search se puede usar `AZURE_SEARCH_API_KEY` o, si te asignan roles de datos, dejar esa clave vacía y usar `AZURE_SEARCH_USE_ENTRA_ID=true`. En el segundo caso, la sesión local debe estar disponible para `DefaultAzureCredential` (por ejemplo, inicio de sesión de Azure CLI o Visual Studio). Para consultar se requiere **Search Index Data Reader**; para cargar documentos, **Search Index Data Contributor**; y para crear el índice con `--create-index`, **Search Service Contributor**. Con clave, esa última operación requiere una clave de administración.

## Flujo de carga

La primera orden muestra un código y una URL de Microsoft; inicia sesión con **tu propio usuario**. Sólo se descargan PDFs que ese usuario puede leer. Los archivos y su metadata se guardan en `data/sharepoint/`, que Git ignora.

```powershell
python src\sharepoint_sync.py --output-dir data\sharepoint
python src\azure_search_ingest.py --source-dir data\sharepoint --create-index
```

Después, iniciar el bot como ya está configurado:

```powershell
python src\app.py
```

El primer comando de ingesta crea el índice `chat-salvador-docs` si falta. Para cargas posteriores omite `--create-index`. Los PDFs se fragmentan por página (y, si una página es extensa, en segmentos cortos con solapamiento), para que una coincidencia no oculte la respuesta dentro de un documento completo. Cada fragmento recibe un *embedding* y Azure AI Search compara el significado de la pregunta con esos fragmentos; no hace falta consolidar temas en un PDF gigante ni mantener reglas por documento. El índice conserva título, URL de SharePoint, sistema de origen y fragmentos de texto; el bot enlaza a la URL original, por lo que SharePoint sigue aplicando sus permisos al abrirla.

Si cambias la estrategia de fragmentación, vuelve a ejecutar la ingesta. El proceso reemplaza los fragmentos anteriores del mismo documento y elimina los que ya no correspondan, por lo que no es necesario borrar ni dividir físicamente los PDFs.

Si previamente cargaste copias manuales de los mismos PDFs, o si actualizas una versión anterior del índice que no tenía el campo vectorial, ejecuta una única carga limpia con `--reset-index`. Esa opción elimina sólo `AZURE_SEARCH_INDEX_NAME` y lo reconstruye desde las copias sincronizadas que incluyen metadata de OneDrive:

```powershell
python src\azure_search_ingest.py --source-dir data\sharepoint --reset-index
```

## Crear el servicio, sólo si tienes Azure Contributor

La infraestructura está aislada en `infra/azure-search.bicep` y no modifica el despliegue actual del bot. Antes de ejecutarla, reemplazar el nombre de ejemplo por uno globalmente único:

```powershell
az deployment group create --resource-group <grupo> --template-file infra\azure-search.bicep --parameters infra\azure-search.parameters.json
```

La plantilla usa `free` por defecto, suficiente para un lote piloto pequeño y sin consumir el crédito. Cada suscripción admite un único servicio Free y tiene 50 MB de almacenamiento; cambia a `basic` únicamente si el piloto lo necesita. No ejecutar el nivel de pago sin autorización sobre la suscripción. Si no tienes ese permiso, pide a quien gestione Azure que te entregue endpoint, nombre del índice y credenciales o rol de datos; el código de ingesta ya queda listo para ello.

## Criterio de prueba esta semana

1. Ejecutar el bot localmente desde el Playground de Teams.
2. Sincronizar 2–5 PDFs no sensibles de la biblioteca piloto.
3. Hacer una consulta que aparezca en uno de esos PDFs y comprobar que la respuesta muestra `SharePoint` o `Azure AI Search` y el enlace de origen.
4. Probar una pregunta sin coincidencia; debe responder sin evidencia, sin inventar una solución.
