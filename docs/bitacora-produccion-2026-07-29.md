# Bitácora de producción de Libras — 29 de julio de 2026

Este documento sirve como punto de reanudación para continuar el despliegue en
otro chat.

## Objetivo activo

Publicar Libras como bot interno de Microsoft Teams con este flujo:

```text
Teams -> app-libras-prod -> Azure AI Search (libras-docs) <- SharePoint SOLUCIONES
```

Las integraciones de ClickUp y GitHub son posteriores y no forman parte del
cierre actual.

## Recursos productivos

| Recurso | Valor |
|---|---|
| Suscripción | `ASEINFO Azure` |
| Subscription ID | `75eecb3a-3825-4a53-bd91-09386a38e8a4` |
| Resource Group | `rg-libras-prod` |
| Región | `Central US` |
| App Service | `app-libras-prod` |
| App Service Plan | `ASP-rglibrasprod-aee7` |
| Azure AI Search | `srch-libras-prod` |
| Índice | `libras-docs` |
| Key Vault | `kv-libras-prod` |
| App Service hostname | `app-libras-prod-h0azhpfef6d4fyax.centralus-01.azurewebsites.net` |
| Tenant | `abcee5bb-aa0e-4ecb-9377-71f4d0f42c2a` |

El App Service y Azure AI Search están en Central US. Libras solo consume
SharePoint/Microsoft Graph actualmente; ClickUp y GitHub se consumirán por API
HTTPS en fases posteriores. No es necesario mover Libras a East US/East US 2
salvo que exista una política corporativa obligatoria.

## Completado

- Azure AI Search creado y configurado con autenticación Entra ID/RBAC.
- Índice `libras-docs` existente.
- Identidad administrada del App Service activa:
  - Tipo: `SystemAssigned`
  - Principal ID: `2fc398ef-6e81-41c3-b955-62b05d31ac7b`
- Rol `Search Index Data Reader` asignado al App Service sobre `srch-libras-prod`.
- Identidad corporativa de ingesta `libras-sharepoint-ingestion-prod` autorizada.
- `Sites.Selected` con consentimiento administrativo.
- Permiso explícito `read` sobre el sitio SharePoint aprobado.
- Rol `Search Index Data Contributor` asignado a la identidad de ingesta.
- Secretos `OPENAI-API-KEY` y `SHAREPOINT-CLIENT-SECRET` creados en `kv-libras-prod`.
- Referencia de `OPENAI_API_KEY` agregada al App Service.
- Token client-credentials obtenido correctamente para la aplicación de ingesta.
- Acceso de aplicación validado contra `Documentos compartidos/SOLUCIONES`.
- Sincronización ejecutada:
  - 15 PDFs descargados.
  - 158 fragmentos indexados en `libras-docs`.
- Código publicado mediante ZIP deploy desde el contenido de `src`.
- El plan F1/Free alcanzó `QuotaExceeded` y dejó el sitio deshabilitado.
- Plan escalado y confirmado:
  - SKU: `B1`
  - Tier: `Basic`
  - `usageState`: `Normal`
- El costo estimado consultado para Linux, Central US, B1 y una instancia fue
  aproximadamente `$13.14/mes`, sujeto a contrato, descuentos e impuestos.
- `/healthz` validado con `200 OK` y `{"status": "ok"}`.
- `/readyz` validado con `200 OK` y estado `ready`.

## Diagnóstico del 503

El App Service muestra `Running`, pero `/healthz` devuelve `503` porque el
worker de Gunicorn termina durante el arranque.

Los logs confirmaron:

```text
Starting gunicorn 26.0.0
Listening at: http://0.0.0.0:8000
Booting worker
ValueError: No service connection configuration provided.
Worker failed to boot.
```

El ZIP y la instalación de dependencias fueron correctos. El problema no es
Azure AI Search ni el índice documental: falta la configuración de conexión de
Microsoft Agents en el App Service.

## Decisión de autenticación del bot

La consulta de recursos de toda la suscripción no encontró:

- ningún `Microsoft.BotService/botServices`;
- ninguna identidad `Microsoft.ManagedIdentity/userAssignedIdentities`.

`app-libras-prod` sí tiene una identidad `SystemAssigned`. Por ello, la
configuración adecuada para el estado actual es:

```text
CONNECTIONS__SERVICE_CONNECTION__SETTINGS__AUTHTYPE=SystemManagedIdentity
CONNECTIONS__SERVICE_CONNECTION__SETTINGS__SCOPE=https://api.botframework.com
BOT_TYPE=SystemAssignedMsi
BOT_TENANT_ID=abcee5bb-aa0e-4ecb-9377-71f4d0f42c2a
```

Con `SystemManagedIdentity` no debe configurarse el Client ID de la aplicación
de ingesta de SharePoint. Microsoft Agents usa la identidad del App Service.

## Última acción realizada

Después de reiniciar el App Service, `/healthz` fue validado el 29 de julio de
2026 y devolvió `200 OK`:

```json
{"status": "ok"}
```

Esto confirma que el proceso Python, Gunicorn y el host HTTP ya arrancan
correctamente. Falta validar `/readyz`, que comprueba la configuración del
modelo y Azure AI Search.

## Avance al retomar el 29 de julio

- `/healthz` y `/readyz` fueron validados nuevamente después de configurar la
  identidad del bot; ambos devuelven `200`.
- La documentación vigente de Azure Bot no admite `SystemAssignedMsi` como
  `msaAppType`; los tipos publicados incluyen `UserAssignedMSI`,
  `SingleTenant` y `MultiTenant`.
- Para reutilizar `app-libras-prod` sin usar la identidad de ingesta, se creó
  la identidad administrada dedicada `id-libras-bot-prod` con client ID
  `bac24639-da91-45a3-ae85-062b07188b9c` y se asoció al App Service.
- La conexión de Microsoft Agents quedó configurada como
  `UserManagedIdentity`, con ese client ID, el tenant productivo y el scope de
  Bot Framework. La identidad `SystemAssigned` original se conserva.
- El intento de registrar `Microsoft.BotService` fue rechazado porque la
  cuenta actual no tiene `Microsoft.BotService/register/action` sobre la
  suscripción. No se creó un Bot Service incompleto.

## Primer paso al retomar

Ejecutar esta consulta de solo lectura:

```powershell
az webapp config appsettings list `
  --resource-group "rg-libras-prod" `
  --name "app-libras-prod" `
  --query "[?starts_with(name,'CONNECTIONS__SERVICE_CONNECTION') || name=='BOT_TYPE' || name=='BOT_TENANT_ID'].{name:name,value:value}" `
  -o table
```

Debe mostrar:

```text
CONNECTIONS__SERVICE_CONNECTION__SETTINGS__AUTHTYPE    SystemManagedIdentity
CONNECTIONS__SERVICE_CONNECTION__SETTINGS__SCOPE       https://api.botframework.com
BOT_TYPE                                                SystemAssignedMsi
BOT_TENANT_ID                                           abcee5bb-aa0e-4ecb-9377-71f4d0f42c2a
```

Si no aparecen, repetir:

```powershell
az webapp config appsettings set `
  --resource-group "rg-libras-prod" `
  --name "app-libras-prod" `
  --settings `
  "CONNECTIONS__SERVICE_CONNECTION__SETTINGS__AUTHTYPE=SystemManagedIdentity" `
  "CONNECTIONS__SERVICE_CONNECTION__SETTINGS__SCOPE=https://api.botframework.com" `
  "BOT_TYPE=SystemAssignedMsi" `
  "BOT_TENANT_ID=abcee5bb-aa0e-4ecb-9377-71f4d0f42c2a"
```

Luego:

```powershell
az webapp restart `
  --resource-group "rg-libras-prod" `
  --name "app-libras-prod"
```

Y observar el arranque:

```powershell
az webapp log tail `
  --resource-group "rg-libras-prod" `
  --name "app-libras-prod"
```

En otra ventana probar:

```powershell
$hostName = "app-libras-prod-h0azhpfef6d4fyax.centralus-01.azurewebsites.net"
Invoke-WebRequest "https://$hostName/healthz" -UseBasicParsing
```

Cuando `/healthz` devuelva `200`, probar `/readyz` y después consultas reales
desde Teams. `/healthz` ya está aprobado; queda `/readyz`.

## Estado de Teams

El backend ya está operativo, pero `Libras` no aparece al iniciar un nuevo chat
en Microsoft Teams. Esto es esperado porque hasta ahora solo se probó desde
Microsoft 365 Agents Playground.

La investigación de recursos mostró que en la suscripción no aparece ningún:

- `Microsoft.BotService/botServices`;
- `Microsoft.ManagedIdentity/userAssignedIdentities`.

El App Service conserva una identidad `SystemAssigned` y ahora también tiene
la identidad dedicada `id-libras-bot-prod`, pero todavía falta registrar y
conectar el bot productivo con Teams. El manifiesto
`appPackage/manifest.json` todavía contiene placeholders como `${{TEAMS_APP_ID}}`
y `${{BOT_ID}}`.

## Próximo alcance para el nuevo chat

Antes de solicitar publicación en Teams, se ejecutará un piloto conversacional
en Microsoft 365 Agents Playground. El plan detallado está en
[plan-pruebas-playground.md](plan-pruebas-playground.md). Los resultados deben
registrarse en `docs/evaluacion-piloto.md`.

Después de aprobar el piloto, un chat posterior debe continuar con el registro
y publicación de Teams, en este orden:

1. Con una cuenta con permiso `Microsoft.BotService/register/action`, registrar
   el proveedor `Microsoft.BotService` en la suscripción.
2. Crear el Bot Service productivo asociado al App Service existente, usando
   `id-libras-bot-prod` como `UserAssignedMSI`.
3. Configurar el endpoint de mensajería:
   `https://app-libras-prod-h0azhpfef6d4fyax.centralus-01.azurewebsites.net/api/messages`.
4. Obtener valores reales para `TEAMS_APP_ID` y `BOT_ID`.
5. Resolver los placeholders del manifiesto y generar el ZIP de Teams.
6. Subirlo como aplicación personalizada para una prueba piloto.
7. Publicarlo posteriormente en el catálogo de la organización mediante Teams
   Admin Center.

No ejecutar `atk provision` sin revisar primero su alcance: el archivo
`m365agents.yml` puede intentar crear recursos adicionales, incluido otro
App Service. La infraestructura productiva existente debe reutilizarse.

## Precauciones

- No compartir secretos, tokens, valores de `OPENAI_API_KEY` ni
  `SHAREPOINT_CLIENT_SECRET`.
- No usar el Client ID de `libras-sharepoint-ingestion-prod` para la conexión
  del bot.
- No ejecutar `--reset-index` en Azure AI Search.
- No mover recursos de región sin una decisión explícita de arquitectura.
- No iniciar ClickUp, GitHub, Jira ni el MCP hasta cerrar la validación de
  producción de Teams.
