# Producción de Libras - foco de esta semana

## Estado vigente — 2026-08-12

Producción permanece en `RETRIEVAL_STRATEGY=legacy`, con
`USE_LLM_EVIDENCE_VERIFIER=false`. `USE_LLM_GROUNDED_RESPONSE=true` está
activo únicamente en la ventana controlada vigente. La suite local vigente es
**331/331**. No se desplegó la variante AI-first.

La evaluación AI-first de solo lectura contra `srch-libras-prod/libras-docs`
se ejecutó sin fallback local. Legacy obtuvo 3.07/3.46 s (promedio/p95) sin
redactor y 4.25/6.46 s con redactor. AI-first obtuvo 4.83/5.67 s sin redactor
y 5.13/5.98 s con redactor; el juez se abstuvo en 5/12 y 6/12 casos,
respectivamente.

La ventana aún no tiene consultas reales de Teams registradas, por lo que la
tasa de fallback y la latencia de usuarios reales quedan pendientes de medir
con las mismas 12 preguntas operativas.

Reportes vigentes: `output/revision-humana-ai-first-20260812.json` y
`output/revision-humana-redactor-20260812-postfix6.json`.

Consulta el detalle en [resultado-calidad-20260812.md](resultado-calidad-20260812.md)
y la muestra revisable en
[revision-humana-redactor-20260812.md](revision-humana-redactor-20260812.md).

> El resto de este documento es bitácora histórica de infraestructura. Las
> métricas y decisiones fechadas allí no sustituyen el estado vigente anterior.

> **Estado consolidado 2026-07-31:** consultar primero
> [contexto-actual.md](contexto-actual.md). El alcance autorizado incluye las
> bibliotecas documentales aprobadas del sitio `Soportealcliente`; en la
> biblioteca `Documentos` se mantiene la carpeta `SOLUCIONES` como ruta
> seleccionada. `Hojas de Servicio` y `Teams Wiki Data` permanecen fuera del
> alcance actual. La publicación en Teams sigue pendiente de
> configuración del canal y de distribución controlada.

## Fuente de verdad para el estado actual

Para retomar el proyecto, usar primero [contexto-actual.md](contexto-actual.md).
Las secciones posteriores de este documento conservan la bitácora histórica de
infraestructura y no siempre reflejan el último estado funcional. La validación
de SharePoint se cerró el 29 de julio: se inventariaron 250 archivos en
`SOLUCIONES`, se indexaron 2.354 fragmentos de los 200 formatos legibles y la
comprobación del índice confirmó cero registros fuera de esa carpeta. Las cifras
de **15 PDFs y 158 fragmentos** describen una carga inicial histórica.

### Actualización de cierre funcional — 2026-08-05

La matriz de calidad contra producción termina en **12/12 casos**, con recall
de evidencia y abstención correcta del 100%. La suite local queda en **175
pruebas, OK**. El preflight de plataforma pasa completo y se preparó el
paquete Teams [`Libras-Teams-pilot-2026-08-05-v0.1.1.zip`](../appPackage/build/Libras-Teams-pilot-2026-08-05-v0.1.1.zip).

El preflight de acceso de ingesta aún reporta pendientes en variables de
SharePoint/Key Vault del entorno local; no se reindexó ni se publicó un cambio
remoto durante esta preparación.

El backend validado se publicó posteriormente en `app-libras-prod` mediante
OneDeploy el 2026-08-05. El despliegue terminó correctamente, sin errores, y
`/healthz`/`/readyz` respondieron HTTP 200. La aplicación Libras ya aparece
aprobada en Teams dentro de “Diseñadas para tu organización”; solo falta
revalidar el piloto conversacional con el backend actualizado.

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
- Las bibliotecas incluidas deben tener una audiencia y permisos claros.
- El índice local se conserva solo para desarrollo y diagnóstico.

## Estado actual: Azure Bot conectado y paquete de piloto listo

La habilitación inicial fue confirmada. Datos recibidos:

- Subscription `ASEINFO Azure` (`75eecb3a-3825-4a53-bd91-09386a38e8a4`).
- Resource Group `rg-libras-prod`, región `Central US` para Azure AI Search por disponibilidad.
- Tenant ID `abcee5bb-aa0e-4ecb-9377-71f4d0f42c2a`.
- Application (client) ID `5ddbba70-3350-4386-a834-dc61b93a26ca`.
- Se asume confirmado `Contributor` sobre el Resource Group y `Owner` de la App Registration.

La creación de Azure AI Search `srch-libras-prod` se completó y el índice `libras-docs` existe. La validación inicial confirmó 50 documentos y, después de la carga controlada desde SharePoint, el índice contiene 158 fragmentos provenientes de 15 PDFs descargados de `Documentos compartidos/SOLUCIONES`.

Los permisos de SharePoint y la configuración documental ya fueron validados con un token de aplicación. El código fue publicado en `app-libras-prod` y el plan se escaló de `F1/Free` a `B1/Basic` porque el plan gratuito alcanzó `QuotaExceeded`.

El siguiente bloqueo fue configurar la conexión del bot en el App Service. Ya
está resuelto: el App Service conserva su identidad `SystemAssigned` y tiene
además la identidad `UserAssigned` dedicada `id-libras-bot-prod` para el canal
Bot Framework. El recurso `bot-libras-prod` ya existe en la suscripción y está
conectado al endpoint productivo con el canal de Teams habilitado.

El App Service está en `Central US`, igual que Azure AI Search. Esta ubicación es técnicamente válida para las integraciones HTTPS con SharePoint/Microsoft Graph, ClickUp y GitHub. El plan B1 fue autorizado. Para el recurso Azure Bot se usa la identidad `UserManagedIdentity` dedicada, porque `SystemAssignedMsi` no es un `msaAppType` admitido por Azure Bot.

El 30 de julio de 2026 se registró el proveedor `Microsoft.BotService` en la
suscripción. Se creó `bot-libras-prod` en `rg-libras-prod` con residencia
`Global`, plan `Free` y tipo `User-Assigned Managed Identity`, reutilizando
`id-libras-bot-prod` (Client ID
`bac24639-da91-45a3-ae85-062b07188b9c`). El despliegue de Azure terminó con
estado **complete**. El endpoint de mensajería y el canal de Teams ya están
configurados; queda pendiente instalar el paquete y ejecutar el piloto.

Estado anterior ya resuelto:

- Crear `OPENAI_API_KEY` y `SHAREPOINT_CLIENT_SECRET` en `kv-libras-prod` y configurar sus referencias. (Completado para ambos secretos; la referencia de `OPENAI_API_KEY` ya está agregada al App Service.)
- Validar `SOLUCIONES` mediante la identidad de aplicación y ejecutar la carga inicial controlada. (Completado: 15 PDFs, 158 fragmentos.)

Después de crear los secretos, configurar el proceso de ingesta con su identidad corporativa, validar `SOLUCIONES` y completar la carga de staging.

### Próximo paso inmediato

La conexión de Microsoft Agents en `app-libras-prod` usa la identidad
`UserAssigned` dedicada del bot. El acceso de
SharePoint ya fue validado con un token de aplicación client-credentials de
`libras-sharepoint-ingestion-prod`; el acceso delegado de Graph Explorer no se
usó como evidencia.

La configuración pendiente debe incluir `CONNECTIONS__SERVICE_CONNECTION__SETTINGS__CLIENTID`,
`CONNECTIONS__SERVICE_CONNECTION__SETTINGS__AUTHTYPE=SystemManagedIdentity` y
`CONNECTIONS__SERVICE_CONNECTION__SETTINGS__SCOPE=https://api.botframework.com`.
Después se reiniciará
el App Service y se validarán `/healthz`, `/readyz` y consultas reales desde
Teams.

### Avance de infraestructura al 24 de julio de 2026

- App Service creado: `app-libras-prod`, en `rg-libras-prod`, región `Central US`.
- El App Service usa identidad administrada asignada por el sistema.
- `principalId` de la identidad: `2fc398ef-6e81-41c3-b955-62b05d31ac7b`.
- `Search Index Data Reader` fue asignado y validado para `app-libras-prod` sobre `srch-libras-prod`; el alcance es `This resource` y el principal validado es `2fc398ef-6e81-41c3-b955-62b05d31ac7b`.
- La comprobación **Check access** no muestra asignaciones de denegación y confirma ese único rol para la identidad del App Service.
- El servicio Azure AI Search acepta autenticación con RBAC/Microsoft Entra ID (modo actual: `Both`).
- `Sites.Selected` está aprobado para `libras-sharepoint-ingestion-prod` y muestra `Granted for Asesores en Informática`.
- El permiso explícito `read` de la aplicación sobre el sitio SharePoint aprobado fue creado con resultado `201 Created`.
- `Search Index Data Contributor` está asignado a `libras-sharepoint-ingestion-prod` sobre `srch-libras-prod`.
- `kv-libras-prod` usa Azure RBAC. `app-libras-prod` tiene `Key Vault Secrets User`, el responsable técnico tiene `Key Vault Secrets Officer` y los dos secretos ya fueron creados; falta verificar la resolución de la referencia tras reiniciar y configurar el acceso del job de ingesta.
- El Drive ID de la biblioteca visible como `Documentos compartidos` fue confirmado; Graph la devuelve como `Documentos`. Falta validar la carpeta `SOLUCIONES` con el token de aplicación.
- Se validaron en el App Service las variables de Azure AI Search: `REQUIRE_AZURE_SEARCH=true`, `AZURE_SEARCH_ENDPOINT=https://srch-libras-prod.search.windows.net`, `AZURE_SEARCH_INDEX_NAME=libras-docs` y `AZURE_SEARCH_USE_ENTRA_ID=true`.
- El código ya fue publicado en `app-libras-prod`. El plan F1 inicial alcanzó `QuotaExceeded`; se autorizó y aplicó el cambio a `B1/Basic`, tras lo cual el App Service muestra `Running` y `usageState=Normal`.
- `/healthz` todavía devuelve `503 Service Unavailable` porque el worker de `gunicorn` termina durante el arranque al no encontrar la configuración de conexión del bot; no es una falla de Azure AI Search ni de RBAC.
- `OPENAI_API_KEY` ya está referenciada desde Key Vault en `app-libras-prod`; aún falta completar la configuración sensible del job de ingesta.
- La guía operativa está en [despliegue-produccion.md](despliegue-produccion.md).

### Validación local al 24 de julio de 2026

- Las 56 pruebas automatizadas pasan correctamente con el entorno virtual del proyecto.
- `python src/preflight.py --stage platform` queda en estado OK para modelo, Azure AI Search y paquete de Teams.
- `python src/preflight.py --stage data-access` confirma el tenant y la App Registration, pero mantiene pendientes el sitio, la biblioteca, la carpeta aprobada, el modo `application` y el secreto o referencia de Key Vault.
- La publicación mediante Teams Toolkit usa `src` como raíz del artefacto; por eso el comando `gunicorn ... app:app` de la guía y la plantilla coincide con la estructura desplegada.

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
  de plataforma; `--stage data-access` valida los IDs y la carpeta necesarios
  para completar la configuración de ingesta.
- Esta preparación no reemplaza la Solicitud A ni habilita acceso productivo:
  falta la identidad corporativa y la autorización del sitio SharePoint.

## Trabajo técnico después de la Solicitud A

1. Publicar Libras en el App Service `app-libras-prod` y confirmar que el proceso inicia correctamente.
2. Validar `/healthz` y `/readyz` usando el dominio predeterminado mostrado por Azure Portal.
3. Configurar Key Vault e identidades administradas para secretos de producción.
4. Preparar la sincronización de SharePoint/OneDrive con la App Registration corporativa, sin usar la cuenta personal del desarrollador.
5. Validar que un documento aprobado se indexa, se recupera y se enlaza desde Teams.
6. Generar y validar el paquete de Teams de producción.

## Aprobaciones administrativas pendientes

Las aprobaciones ya pueden gestionarse con los datos disponibles y no deben
esperar al paquete final de Teams:

- Verificar la resolución de la referencia de `OPENAI_API_KEY` y configurar la referencia de `SHAREPOINT_CLIENT_SECRET` en el job de ingesta; los secretos ya están creados.
- Validar el contenido autorizado de `SOLUCIONES` con la identidad de aplicación.
- Publicación y permiso de uso de Libras en Teams para la audiencia aprobada.

## Criterio de salida de la semana

Libras está disponible en Teams para la audiencia autorizada, responde con evidencia de Azure AI Search procedente de SharePoint/OneDrive y no depende de una cuenta personal para acceder a la fuente documental.

## Checklist operativo de cierre

- [x] `Search Index Data Reader` asignado a `app-libras-prod` sobre `srch-libras-prod`.
- [x] Índice `libras-docs` existente y con 50 documentos; autenticación Entra ID/RBAC habilitada en el servicio.
- [x] Configuración no sensible de Azure AI Search validada en `app-libras-prod`.
- [x] `Sites.Selected` con consentimiento administrativo (`Granted`).
- [x] Acceso explícito `read` concedido al sitio SharePoint aprobado (`201 Created`).
- [x] `Search Index Data Contributor` asignado a la identidad de ingesta sobre `srch-libras-prod`.
- [x] Código publicado en `app-libras-prod`.
- [x] App Service escalado de `F1/Free` a `B1/Basic`; cuota normalizada.
- [x] Conexión del bot configurada en `app-libras-prod`: `UserManagedIdentity`, client ID de `id-libras-bot-prod`, tenant y scope de Bot Framework; `/healthz` y `/readyz` validados.
- [ ] Key Vault configurado y referencias verificadas: `OPENAI_API_KEY` ya está referenciado por App Service; `SHAREPOINT_CLIENT_SECRET` debe quedar disponible solo para el proceso de ingesta, sin exponerlo; los roles RBAC del App Service ya están listos.
- [x] `SHAREPOINT_SITE_ID`, `SHAREPOINT_DRIVE_ID` y `SHAREPOINT_FOLDER_PATH=SOLUCIONES` confirmados y validados con token de aplicación.
- [x] `SHAREPOINT_AUTH_MODE=application` configurado para la sincronización local de ingesta.
- [ ] Referencia de Key Vault para `SHAREPOINT_CLIENT_SECRET` configurada en el job de ingesta.
- [x] Identidad separada de ingesta creada con `Search Index Data Contributor`.
- [x] Carga inicial de documentos ejecutada: 15 PDFs, 158 fragmentos indexados en `libras-docs`.
- [ ] Consulta con evidencia real validada desde Teams.
- [ ] Consulta sin evidencia y control de acceso validados desde Teams.
- [ ] Piloto conversacional aprobado en Microsoft 365 Agents Playground antes de solicitar publicación en Teams.
- [x] Proveedor `Microsoft.BotService` registrado en `ASEINFO Azure`.
- [x] Azure Bot `bot-libras-prod` creado en `rg-libras-prod` con `Free` y `id-libras-bot-prod`.
- [x] Endpoint de mensajería configurado en el Azure Bot y canal Microsoft Teams habilitado.
- [x] Paquete de Teams generado con `TEAMS_APP_ID` y `BOT_ID` reales.
- [x] Aplicación instalada y aprobada en Teams; queda revalidar el piloto tras el último despliegue.

## Orden posterior aprobado

Una vez cerrado el checklist anterior, el orden de trabajo es:

1. Integrar ClickUp y GitHub.
2. Integrar Jira como fuente de documentación histórica.
3. Crear el MCP de solo lectura para `https://downloads.aseinfo.net/home`.

Estas fases no deben bloquear el cierre de producción de esta semana.

## Evolución de experiencia de chat (planificada)

El seguimiento de mensajes dentro del mismo chat, los enlaces legibles, las
acciones iniciales y los comandos se organizan en
[plan-evolucion-conversacional-libras.md](plan-evolucion-conversacional-libras.md).
No cambian el alcance documental ni bloquean el checklist actual. El contexto
será efímero por chat de Teams y se perderá al reiniciar el backend o abrir otro
chat.

## Material eliminado o no prioritario

No se mantiene un roadmap alternativo de demo, arquitectura híbrida, Blob Storage ni automatización incremental. Si alguno se vuelve necesario, se documentará como una decisión nueva dentro de este mapa.

## Ajuste de alcance del piloto técnico (2026-08-05)

Para mantener el piloto dentro de la capacidad existente, se actualizaron las
fuentes autorizadas de `app-libras-prod` a `ReadME Hotfixes`,
`Documentos/SOLUCIONES`, `Manuales` y `Scripts de Apoyo`. El filtro productivo
verifica conjuntamente biblioteca y carpeta; por ello no recupera contenido de
las fuentes excluidas aunque permanezca en `libras-docs`.

No se realizó reingesta, reconstrucción de índice ni cambio de SKU. El índice
conserva 2,665 fragmentos y se conserva el respaldo previo en
`output/prod-backup-before-v2-20260805`. Los nueve documentos curados de
`Documentos de Apoyo` quedan fuera temporalmente, ya que permitir la biblioteca
raíz incorporaría otros documentos no seleccionados. `/healthz` y `/readyz`
fueron validados con HTTP 200 tras el ajuste.
