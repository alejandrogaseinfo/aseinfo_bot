# Libras con Azure AI Search y SharePoint/OneDrive

> Alcance activo: esta guía cubre exclusivamente la ruta hacia producción de Libras con Teams, Azure AI Search y SharePoint/OneDrive. Las fuentes y planes posteriores están archivados en [planes-posteriores](planes-posteriores/README.md).

## Objetivo de producción

Libras debe responder en Microsoft Teams con evidencia recuperada desde Azure AI Search. La documentación se origina en una biblioteca o carpeta aprobada de SharePoint/OneDrive.

```text
Teams -> Libras en Azure -> Azure AI Search <- SharePoint / OneDrive autorizado
```

La cuenta personal del desarrollador puede servir para una prueba local, pero no forma parte del flujo de producción.

## Contrato documental inicial

La primera biblioteca aprobada contiene únicamente PDFs y tiene una audiencia
común: todo miembro autorizado de Libras puede consultar todo su contenido. No
hay permisos distintos por documento en esta fase.

Cada fragmento cargado en Azure AI Search conserva `document_id`, versión
(`etag`), fecha de modificación, URL de SharePoint, sitio, drive, carpeta,
hash de contenido, tipo documental y número de fragmento. La identidad estable
es `document_id`, no el nombre del archivo. Si un PDF cambia, sus fragmentos se
reemplazan; si se elimina de SharePoint, la sincronización emite su
`document_id` para que la ingesta elimine todos los fragmentos asociados.
Al aplicar este contrato a un índice piloto que ya existe, se debe ejecutar una
vez la ingesta con `--reset-index` para recrear el esquema con los campos de
metadatos.

## Estado actual y restricción importante

`src/sharepoint_sync.py` usa hoy autenticación delegada: quien ejecuta el script inicia sesión con su propia cuenta de Microsoft 365. Esto permite validar la conectividad, pero no es suficiente para producción ni para una sincronización programada.

Antes de publicar Libras se debe cambiar esa sincronización a la App Registration corporativa `libras-sharepoint-ingestion-prod`, con acceso de solo lectura limitado al sitio aprobado. La Solicitud B del administrador concede ese acceso cuando existan los IDs definitivos.

Cuando se reciban los datos de A y B, configurar `SHAREPOINT_AUTH_MODE=application`,
`SHAREPOINT_TENANT_ID`, `SHAREPOINT_CLIENT_ID`, `SHAREPOINT_SITE_ID`,
`SHAREPOINT_DRIVE_ID` y la carpeta autorizada. El secreto de la App Registration
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
5. Definir la biblioteca o carpeta de SharePoint/OneDrive que será la única fuente inicial.
6. Preparar el paquete de Teams de producción.

## Solicitud B: aprobaciones necesarias al final

La Solicitud B se realiza solo después de terminar la preparación técnica y contar con los IDs de los recursos.

El administrador deberá:

| Área | Aprobación mínima |
|---|---|
| Microsoft Entra / SharePoint | `Sites.Selected`, consentimiento administrativo y lectura exclusiva del sitio SharePoint aprobado para `libras-sharepoint-ingestion-prod`. |
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
5. No se muestran secretos ni documentos fuera de la biblioteca autorizada.
