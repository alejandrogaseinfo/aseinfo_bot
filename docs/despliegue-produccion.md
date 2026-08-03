# Despliegue productivo de Libras

> Para el estado vigente, consultar primero [contexto-actual.md](contexto-actual.md).
> Las cifras de 15 PDFs y 158 fragmentos que aparecen abajo son históricas: el
> índice fue reconstruido el 29 de julio con 2.354 fragmentos de
> `SOLUCIONES` y sin fuentes fuera de alcance.

Esta guía deja preparado `app-libras-prod` para ejecutar Libras con una
identidad administrada y consultar `srch-libras-prod` sin usar una cuenta
personal.

## Estado actual

- App Service: `app-libras-prod`
- Resource Group: `rg-libras-prod`
- Azure AI Search: `srch-libras-prod`
- Índice: `libras-docs`
- Identidad administrada del App Service: activa
- `Search Index Data Reader` asignado a `app-libras-prod` sobre `srch-libras-prod`
- Índice `libras-docs`: carga controlada completada con 15 PDFs y 158 fragmentos desde `Documentos compartidos/SOLUCIONES`
- Región del App Service y Azure AI Search: `Central US`; las integraciones HTTPS con SharePoint/Microsoft Graph, ClickUp y GitHub no requieren co-localización regional
- App Service Plan: cambiado de `F1/Free` a `B1/Basic`, con autorización administrativa; el estado de cuota pasó a `Normal`
- Autenticación del servicio: admite RBAC/Microsoft Entra ID (modo actual: `Both`)
- Identidad de ingesta: `libras-sharepoint-ingestion-prod`
- `Sites.Selected`: consentimiento administrativo concedido
- Acceso explícito `Read` al sitio SharePoint: creado (`201 Created`)
- `Search Index Data Contributor` para ingesta: asignado sobre `srch-libras-prod`
- Key Vault: `kv-libras-prod` usa Azure RBAC; el App Service tiene `Key Vault Secrets User` y el responsable técnico `Key Vault Secrets Officer`
- Avance: los secretos `OPENAI-API-KEY` y `SHAREPOINT-CLIENT-SECRET` ya existen en `kv-libras-prod`; la referencia de `OPENAI_API_KEY` ya fue agregada a `app-libras-prod`. El código está publicado, la ingesta inicial está completada y la conexión del bot responde correctamente en `/healthz` y `/readyz`. El endpoint y el canal Teams ya están configurados; queda instalar el paquete y ejecutar el piloto.

## Evidencia confirmada el 28 de julio de 2026

- La identidad administrada **asignada por sistema** de `app-libras-prod` está activa; no hay identidades asignadas por usuario ni un recurso `Bot Service` en la suscripción. La conexión de Microsoft Agents debe usar `SystemManagedIdentity`.
- Su `Object (principal) ID` comienza con `2fc398ef`, consistente con la identidad documentada y sus roles RBAC.
- La biblioteca visible como `Documentos compartidos` tiene Drive ID confirmado. Graph la presenta como `Documentos`; es el mismo drive.
- Un `Access denied` desde Graph Explorer con token delegado de usuario no evalúa el permiso `Sites.Selected` de la aplicación. La validación pendiente debe usar el token de aplicación de `libras-sharepoint-ingestion-prod`.

## Configuración del App Service

En **Settings > Environment variables** configurar:

```text
LIBRAS_ENV=production
REQUIRE_AZURE_SEARCH=true
ALLOW_LOCAL_DOCUMENT_FALLBACK=false
USE_AZURE_SEARCH_IN_LOCAL=false
AZURE_SEARCH_ENDPOINT=https://srch-libras-prod.search.windows.net
AZURE_SEARCH_INDEX_NAME=libras-docs
AZURE_SEARCH_USE_ENTRA_ID=true
AZURE_SEARCH_USE_SEMANTIC=false
OPENAI_MODEL=gpt-4o
OPENAI_INTENT_MODEL=gpt-4o-mini
```

`OPENAI_API_KEY` está configurada como referencia al secreto `OPENAI-API-KEY`
de Key Vault. No debe copiarse desde el `.env` local ni quedar en el
repositorio. `SHAREPOINT_CLIENT_SECRET` debe permanecer reservado para el
proceso de ingesta.

### Estado de esta configuración

Se confirmó en Azure Portal que `REQUIRE_AZURE_SEARCH`,
`AZURE_SEARCH_ENDPOINT`, `AZURE_SEARCH_INDEX_NAME` y
`AZURE_SEARCH_USE_ENTRA_ID` tienen los valores indicados. No se configuró una
`AZURE_SEARCH_API_KEY`, por lo que la aplicación debe utilizar la identidad
administrada y el rol RBAC asignado.

El código ya está publicado en el App Service. Actualmente el proceso inicia
`gunicorn`, pero el worker termina con:

```text
ValueError: No service connection configuration provided.
```

Por ello `/healthz` devuelve `503` aunque el recurso muestre `Running`. Faltan
estas variables de aplicación:

```text
CONNECTIONS__SERVICE_CONNECTION__SETTINGS__CLIENTID
CONNECTIONS__SERVICE_CONNECTION__SETTINGS__AUTHTYPE=SystemManagedIdentity
CONNECTIONS__SERVICE_CONNECTION__SETTINGS__SCOPE=https://api.botframework.com
CONNECTIONS__SERVICE_CONNECTION__SETTINGS__TENANTID
```

Con `SystemManagedIdentity` no se configura `CLIENTID`: el SDK utiliza la
identidad administrada asignada por el sistema al App Service. No se debe usar
el Client ID de la aplicación de ingesta de SharePoint para esta conexión.

## Ruta para el administrador

### 1. Permiso de lectura del bot

Un administrador con `Owner` o `User Access Administrator` debe asignar la
identidad administrada de `app-libras-prod` al rol:

```text
Search Index Data Reader
```

El alcance debe ser únicamente el recurso `srch-libras-prod`.

La identidad administrada del App Service tiene este `principalId`:

```text
2fc398ef-6e81-41c3-b955-62b05d31ac7b
```

Si el botón **Add role assignment** está deshabilitado, la cuenta necesita
`Owner`, `User Access Administrator` o `Role Based Access Control Administrator`.

### 2. Consentimiento administrativo para SharePoint

En Microsoft Entra ID, abrir la App Registration
`libras-sharepoint-ingestion-prod` y seguir:

```text
API permissions
  -> Grant admin consent for Asesores en Informática
```

La aplicación ya tiene agregado:

```text
Microsoft Graph -> Sites.Selected -> Application
```

El consentimiento debe ser otorgado por una cuenta con `Privileged Role
Administrator` o `Global Administrator`. Hasta entonces el estado aparece como
`Not granted`. La URL directa de consentimiento es:

```text
https://login.microsoftonline.com/abcee5bb-aa0e-4ecb-9377-71f4d0f42c2a/adminconsent?client_id=5ddbba70-3350-4386-a834-dc61b93a26ca
```

Después de aceptar, el permiso debe mostrar:

```text
Granted for Asesores en Informática
```

### 3. Acceso explícito al sitio SharePoint

`Sites.Selected` no concede acceso automáticamente a ningún sitio. Con el
`Site ID` aprobado, el administrador debe crear un permiso Microsoft Graph con
rol `read` para la aplicación `libras-sharepoint-ingestion-prod`:

```http
POST https://graph.microsoft.com/v1.0/sites/{site-id}/permissions
Content-Type: application/json

{
  "roles": ["read"],
  "grantedToIdentities": [
    {
      "application": {
        "id": "<APPLICATION_CLIENT_ID>",
        "displayName": "libras-sharepoint-ingestion-prod"
      }
    }
  ]
}
```

La concesión puede ejecutarse con Graph Explorer, PowerShell o una herramienta
administrativa equivalente. El resultado debe confirmar acceso `read` al sitio
aprobado.

### 4. Permiso de carga de la identidad de ingesta

Sobre `srch-libras-prod`, asignar a
`libras-sharepoint-ingestion-prod` el rol:

```text
Search Index Data Contributor
```

El alcance debe ser únicamente `srch-libras-prod`. No se debe asignar este rol
a `app-libras-prod`.

### 5. Datos que debe entregar el administrador

```text
SHAREPOINT_TENANT_ID
SHAREPOINT_CLIENT_ID
SHAREPOINT_SITE_ID
SHAREPOINT_DRIVE_ID
SHAREPOINT_FOLDER_PATH
SHAREPOINT_DRIVE_IDS
SHAREPOINT_FOLDER_PATHS
SHAREPOINT_AUTH_MODE=application
```

`SHAREPOINT_DRIVE_IDS` y `SHAREPOINT_FOLDER_PATHS` deben tener la misma
cantidad de elementos y conservar el mismo orden. Una ruta vacía significa la
raíz de esa biblioteca; para `Documentos` se usa `SOLUCIONES`. `Teams Wiki
Data` queda fuera de la lista aprobada. `Hojas de Servicio` también queda fuera
del alcance actual por su volumen pendiente de procesar.

El secreto de la App Registration debe quedar en Key Vault y configurarse como
`SHAREPOINT_CLIENT_SECRET`; nunca debe guardarse en Git.

## Validación

### Próximo paso inmediato

El siguiente bloqueo operativo es configurar la conexión de Microsoft Agents
en `app-libras-prod` con `SystemManagedIdentity`. La carpeta `SOLUCIONES` ya fue validada con un token de
aplicación y la carga inicial ya fue indexada.

La secuencia de cierre es:

1. Configurar `AUTHTYPE=SystemManagedIdentity` y el scope de Bot Framework.
2. Reiniciar el App Service y comprobar `/healthz` y `/readyz`.
3. Validar consultas reales desde Teams con evidencia de Azure AI Search.

El valor que se use para client credentials debe ser el **Value** del secreto
de la App Registration, no su `Secret ID`. El secreto debe resolverse dentro
del entorno autorizado y no debe aparecer en comandos, logs ni documentación.

Después de corregir la conexión del bot:

1. Abrir `/healthz` y comprobar `status=ok`.
2. Abrir `/readyz` y comprobar `status=ready`.
3. Consultar desde Teams un documento realmente indexado desde las bibliotecas
   autorizadas del sitio `Soportealcliente` y una pregunta sin evidencia.
4. Confirmar que la respuesta no solicita inicio de sesión personal.
5. Confirmar que la respuesta incluye la fuente de Azure AI Search.

## Registro y publicación en Teams

`/healthz` y `/readyz` validan el backend, pero no publican automáticamente la
aplicación en Teams. El proveedor `Microsoft.BotService` ya está registrado y
el recurso Azure Bot `bot-libras-prod` fue creado correctamente en
`rg-libras-prod` con plan `Free` y la identidad `id-libras-bot-prod`.
Libras todavía no aparece en un nuevo chat hasta instalar el paquete como
aplicación personalizada; el endpoint, el canal Teams y el paquete con IDs
reales ya están listos.

El Bot Service quedó configurado con el endpoint:

```text
https://app-libras-prod-h0azhpfef6d4fyax.centralus-01.azurewebsites.net/api/messages
```

El paquete de Teams con los IDs reales está generado en
`appPackage/build/Libras-Teams-pilot-2026-07-30.zip`. Falta instalarlo como
aplicación personalizada para la prueba piloto y finalmente publicarlo en el
catálogo de la organización. No ejecutar `atk provision` sin revisar el YAML,
porque podría crear recursos duplicados en Azure en lugar de reutilizar
`app-libras-prod`.

Si `/healthz` devuelve `503`, comprobar primero el historial de despliegue y
los logs de inicio del App Service. La infraestructura puede mostrar estado
`Running` aun cuando no haya código publicado o el proceso de la aplicación no
haya iniciado.

## Ingesta

La carga y actualización de PDFs debe ejecutarse con otra identidad. Esa
identidad necesita `Sites.Selected` con acceso explícito `read` al sitio
SharePoint aprobado y `Search Index Data Contributor` sobre
`srch-libras-prod`; no se debe conceder este último rol al bot que atiende
consultas.
