# Libras con Azure AI Search y SharePoint/OneDrive

> Alcance activo: esta guía cubre exclusivamente la ruta hacia producción de Libras con Teams, Azure AI Search y SharePoint/OneDrive. Las integraciones posteriores tienen un orden separado en [planes-posteriores](planes-posteriores/README.md).

## Objetivo de producción

Libras debe responder en Microsoft Teams con evidencia recuperada desde Azure AI Search. La documentación se origina en una biblioteca o carpeta aprobada de SharePoint/OneDrive.

```text
Teams -> Libras en Azure -> Azure AI Search <- SharePoint / OneDrive autorizado
```

La cuenta personal del desarrollador puede servir para una prueba local, pero no forma parte del flujo de producción.

## Contrato documental inicial

Las carpetas aprobadas contienen archivos PDF y otros formatos con texto
recuperable. Libras ingiere PDF, DOCX, XLSX, TXT, CSV, SQL, XML, RDLC, ASPX,
PowerShell, BAT y JSON. Imágenes, vídeos, ejecutables, DLL y archivos
comprimidos se mantienen fuera del índice porque no ofrecen texto RAG fiable.
Todo miembro autorizado de Libras puede consultar el contenido indexado; no hay
permisos distintos por documento en esta fase. El alcance productivo autorizado
incluye las bibliotecas documentales aprobadas del sitio `Soportealcliente`.
En `Documentos` se consulta únicamente la carpeta `SOLUCIONES`; las demás
bibliotecas aprobadas se consultan desde su raíz. `Hojas de Servicio` queda
fuera del alcance actual por su volumen pendiente de procesar. `Teams Wiki Data`
queda fuera por ser una biblioteca de datos de sistema.

Cada fragmento cargado en Azure AI Search conserva `document_id`, versión
(`etag`), fecha de modificación, URL de SharePoint, sitio, drive, carpeta,
hash de contenido, tipo documental y número de fragmento. La identidad estable
es `document_id`, no el nombre del archivo. Si un archivo cambia, sus fragmentos se
reemplazan; si se elimina de SharePoint, la sincronización emite su
`document_id` para que la ingesta elimine todos los fragmentos asociados.
En el servicio de búsqueda `Free` se usa `OPENAI_EMBEDDING_DIMENSIONS=512`
para mantener el índice dentro de la cuota de almacenamiento; el modelo
`text-embedding-3-small` admite esa reducción.
Al aplicar este contrato a un índice piloto que ya existe, se debe ejecutar una
vez la ingesta con `--reset-index` para recrear el esquema con los campos de
metadatos.

## Estado actual y restricción importante

`src/sharepoint_sync.py` usa hoy autenticación delegada: quien ejecuta el script inicia sesión con su propia cuenta de Microsoft 365. Esto permite validar la conectividad, pero no es suficiente para producción ni para una sincronización programada.

Antes de publicar Libras se debe cambiar esa sincronización a la App Registration corporativa `libras-sharepoint-ingestion-prod`, con acceso de solo lectura limitado al sitio aprobado. El acceso requiere tres pasos separados: agregar `Sites.Selected`, obtener consentimiento administrativo y conceder explícitamente el rol `read` sobre el sitio mediante Microsoft Graph.

Configurar `SHAREPOINT_AUTH_MODE=application`, `SHAREPOINT_TENANT_ID`,
`SHAREPOINT_CLIENT_ID`, `SHAREPOINT_SITE_ID`, `SHAREPOINT_DRIVE_ID`,
`SHAREPOINT_DRIVE_IDS` y `SHAREPOINT_FOLDER_PATHS`. Las dos listas deben estar
alineadas: una ruta vacía representa la raíz de la biblioteca correspondiente.
El secreto de la App Registration
debe llegar mediante una referencia de Key Vault como `SHAREPOINT_CLIENT_SECRET`;
nunca se guarda en Git. En este modo Libras no usa `/me/drive` ni el inicio de
sesión delegado: consulta únicamente el drive explícitamente aprobado.

## Dependencias de la Solicitud A

Esperar y registrar:

- Subscription ID, Resource Group `rg-libras-prod` y región.
- Rol `Contributor` del responsable técnico sobre ese Resource Group.
- Tenant ID.
- Application (client) ID de `libras-sharepoint-ingestion-prod`.
- Confirmación de que el responsable técnico es Owner de esa App Registration.

## Preparación técnica después de la Solicitud A

1. Desplegar App Service, Azure Bot e identidades administradas en `rg-libras-prod`.
2. Crear Azure AI Search y usar autenticación Microsoft Entra/RBAC para el acceso de producción.
3. Crear el índice `libras-docs` y configurar sus metadatos de documento, URL de origen y fragmentos.
4. Crear Key Vault con Azure RBAC y preparar referencias de secretos para App Service.
5. Definir las bibliotecas y carpetas aprobadas de SharePoint/OneDrive que
   serán las fuentes documentales.
6. Preparar el paquete de Teams de producción.

## Permisos productivos requeridos

El administrador deberá:

| Área | Aprobación mínima |
|---|---|
| Microsoft Entra / SharePoint | `Sites.Selected` como permiso Application, consentimiento administrativo y concesión explícita `read` sobre el sitio SharePoint aprobado para `libras-sharepoint-ingestion-prod`. |
| Azure AI Search | `Search Index Data Reader` para la identidad del bot y `Search Index Data Contributor` para la identidad de sincronización. |
| Key Vault | `Key Vault Secrets User` para la identidad del bot y `Key Vault Secrets Officer` para la identidad que carga secretos. |
| Teams | Cargar, permitir y distribuir el paquete de Libras a la audiencia corporativa aprobada. |

No usar `Files.Read.All`, `Sites.Read.All` ni `Sites.FullControl.All` como permisos de aplicación globales para este flujo.

## Prueba local temporal

Solo mientras se completa la migración a identidad corporativa, se puede validar una carpeta piloto con la autenticación delegada actual:

```powershell
python src\sharepoint_sync.py --output-dir data\sharepoint
python src\azure_search_ingest.py --source-dir data\sharepoint --create-index
python src\app.py
```

Esta prueba no autoriza ni sustituye la configuración de producción.

## Criterios de salida

1. Una persona de la audiencia aprobada puede instalar Libras y conversar con él en Teams.
2. Libras recupera un documento real de SharePoint/OneDrive mediante Azure AI Search y muestra su enlace de origen.
3. Una consulta sin coincidencia responde sin evidencia y no inventa una solución.
4. El acceso a SharePoint no depende de la cuenta personal del desarrollador.
5. No se muestran secretos ni documentos fuera de las bibliotecas y carpetas autorizadas.
