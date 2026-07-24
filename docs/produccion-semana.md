# Producción de Libras - foco de esta semana

## Objetivo

Poner `Libras` en producción como aplicación interna de Microsoft Teams para que la audiencia autorizada consulte documentación aprobada de una biblioteca o carpeta de SharePoint/OneDrive.

## Alcance activo

```text
Usuario interno en Teams
        -> Libras (Azure App Service / Azure Bot)
        -> Azure AI Search
        <- SharePoint / OneDrive autorizado
```

- Teams es el único canal de usuarios.
- Azure AI Search es el índice documental de producción.
- SharePoint/OneDrive es la única fuente documental de esta semana.
- La biblioteca inicial debe tener una audiencia y permisos claros.
- El índice local se conserva solo para desarrollo y diagnóstico.

## Estado actual: Solicitud A resuelta; permisos de Azure AI Search pendientes

La habilitación inicial fue confirmada. Datos recibidos:

- Subscription `ASEINFO Azure` (`75eecb3a-3825-4a53-bd91-09386a38e8a4`).
- Resource Group `rg-libras-prod`, región `Central US` para Azure AI Search por disponibilidad.
- Tenant ID `abcee5bb-aa0e-4ecb-9377-71f4d0f42c2a`.
- Application (client) ID `5ddbba70-3350-4386-a834-dc61b93a26ca`.
- Se asume confirmado `Contributor` sobre el Resource Group y `Owner` de la App Registration.

La creación de Azure AI Search `srch-libras-prod` se completó y el índice `libras-docs` existe. El trabajo está temporalmente detenido hasta que el administrador asigne al responsable técnico, sobre `srch-libras-prod`:

- `Search Index Data Contributor`, para crear, actualizar y cargar documentos.
- `Search Index Data Reader`, para consultar y validar documentos.

Después de recibir esos roles, volver a autenticar Azure CLI, verificar el conteo del índice y completar la carga de staging.

### Solicitud A original

La habilitación inicial solicitada era:

1. Resource Group `rg-libras-prod`.
2. Rol `Contributor` para el responsable técnico, limitado a ese Resource Group.
3. App Registration `libras-sharepoint-ingestion-prod`, de tenant único, con el responsable técnico como Owner.

Registrar al recibir la respuesta:

- Subscription ID, Resource Group y región.
- Tenant ID.
- Application (client) ID de la App Registration.
- Confirmación del rol Contributor y de Owner.

Estos datos ya fueron recibidos y la Solicitud A se considera resuelta.

## Preparación técnica ya completada

- La ingesta inicial está limitada a PDFs de la biblioteca o carpeta aprobada.
- Cada fragmento conserva el ID estable del PDF, versión (`etag`), fecha de
  modificación, URL, carpeta y hash de contenido para que una respuesta sea
  trazable hasta el documento de origen.
- La sincronización local reutiliza PDFs sin cambios, detecta renombres y
  conserva cambios y eliminaciones pendientes hasta que Azure AI Search
  actualice o retire los fragmentos asociados. La indexación posterior procesa
  únicamente PDFs nuevos o modificados, salvo una creación o reconstrucción
  explícita del índice.
- El host expone `GET /healthz` para vida y `GET /readyz` para verificar, sin
  revelar secretos, que el modelo y —en producción— Azure AI Search están
  configurados. Los logs registran duración, fuentes y resultado de cada
  consulta sin guardar la pregunta ni fragmentos documentales.
- La validación funcional de la biblioteca piloto se registrará en
  [evaluacion-piloto.md](evaluacion-piloto.md) con preguntas reales, evidencia,
  latencia y casos de actualización/eliminación documental.
- `python src/preflight.py --stage platform` valida los requisitos configurables
  de plataforma para la Solicitud A; `--stage data-access` valida los IDs y la
  carpeta que deberán estar listos antes de formular la Solicitud B.
- Esta preparación no reemplaza la Solicitud A ni habilita acceso productivo:
  falta la identidad corporativa y la autorización del sitio SharePoint.

## Trabajo técnico después de la Solicitud A

1. Desplegar Libras, Azure Bot, App Service e identidades administradas en `rg-libras-prod`.
2. Crear y configurar Azure AI Search con autenticación de Microsoft Entra/RBAC.
3. Preparar la sincronización de SharePoint/OneDrive con la App Registration corporativa, sin usar la cuenta personal del desarrollador.
4. Configurar Key Vault e identidades administradas para secretos de producción.
5. Validar que un documento aprobado se indexa, se recupera y se enlaza desde Teams.
6. Generar y validar el paquete de Teams de producción.

## Solicitud B: solo al final

No pedir la Solicitud B hasta que existan los IDs definitivos del sitio SharePoint, Azure AI Search, identidades administradas, Key Vault y el paquete de Teams.

La Solicitud B autorizará:

- `Sites.Selected` y permiso de lectura exclusivamente sobre el sitio SharePoint aprobado.
- `Search Index Data Reader` para la identidad del bot.
- `Search Index Data Contributor` para la identidad de sincronización.
- Acceso mínimo a secretos en Key Vault.
- Publicación y permiso de uso de Libras en Teams para la audiencia aprobada.

## Criterio de salida de la semana

Libras está disponible en Teams para la audiencia autorizada, responde con evidencia de Azure AI Search procedente de SharePoint/OneDrive y no depende de una cuenta personal para acceder a la fuente documental.

## Material aplazado

Los planes de ClickUp, Jira, GitHub, MCP/DownloadAseinfo.net, automatización incremental y arquitectura híbrida están en [planes-posteriores](planes-posteriores/README.md). Sus adaptadores de código están en `src/planes_posteriores/`. No forman parte de esta entrega.
