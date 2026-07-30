# Bitácora de producción — 2026-07-30

## Hito: creación del Azure Bot productivo

Se confirmó que el proveedor `Microsoft.BotService` aparece como **Registered**
en la suscripción `ASEINFO Azure`. El registro fue necesario para poder crear
la infraestructura que conecta el backend de Libras con Microsoft Teams.

Se creó correctamente el recurso Azure Bot con estos datos no sensibles:

| Campo | Valor |
|---|---|
| Bot handle | `bot-libras-prod` |
| Suscripción | `ASEINFO Azure` |
| Resource group | `rg-libras-prod` |
| Residencia de datos | `Global` |
| Plan | `Free` |
| Tipo de aplicación | `User-Assigned Managed Identity` |
| Identidad reutilizada | `id-libras-bot-prod` |
| Client ID | `bac24639-da91-45a3-ae85-062b07188b9c` |
| Tenant ID | `abcee5bb-aa0e-4ecb-9377-71f4d0f42c2a` |

El despliegue mostrado por Azure terminó con estado **Your deployment is
complete**. El recurso quedó creado en `rg-libras-prod`.

## Qué quedó completado

1. Abrir el recurso `bot-libras-prod`.
2. Configurar el endpoint de mensajería:

   `https://app-libras-prod-h0azhpfef6d4fyax.centralus-01.azurewebsites.net/api/messages`

3. Habilitar y guardar el canal **Microsoft Teams**.
4. Obtener los IDs reales necesarios para el manifiesto.
5. Generar el paquete `.zip` de Teams.

## Qué queda pendiente

1. Instalar el paquete como aplicación personalizada y validar el piloto con
   cinco personas de Operaciones.
2. Distribuirlo de forma controlada mediante Teams Admin Center.

## Límites y precauciones

- La creación del Azure Bot no otorgó permisos nuevos sobre SharePoint.
- El Azure Bot no es la identidad de ingesta; no debe recibir
  `Search Index Data Contributor`.
- La fuente documental sigue limitada a `Documentos compartidos/SOLUCIONES`.
- El backend productivo, Azure AI Search y la validación de SharePoint ya están
  cerrados; ClickUp y GitHub permanecen como integraciones posteriores.
- No se subió todavía ningún `.zip` a Teams.

## Hito: conexión del Bot Service y paquete de piloto

Se configuró en `bot-libras-prod` el endpoint de mensajería productivo:

`https://app-libras-prod-h0azhpfef6d4fyax.centralus-01.azurewebsites.net/api/messages`

Se habilitó el canal `Microsoft Teams`; su estado quedó `Succeeded` y
`isEnabled=true`. La identidad del bot se mantuvo como `UserAssignedMSI`,
reutilizando `id-libras-bot-prod`.

El manifiesto de producción quedó con estos IDs no secretos:

| Campo | Valor |
|---|---|
| `TEAMS_APP_ID` | `98888f43-7cf5-44c6-89ca-248a0d644919` |
| `BOT_ID` | `bac24639-da91-45a3-ae85-062b07188b9c` |

El paquete se generó en
`appPackage/build/Libras-Teams-pilot-2026-07-30.zip` y contiene únicamente
`manifest.json`, `color.png` y `outline.png` en la raíz. El manifiesto no
contiene placeholders. `/healthz` devolvió `200` con `status=ok` y `/readyz`
devolvió `200` con `status=ready`.

## Pendiente de cierre

Instalar el paquete como aplicación personalizada, validar una consulta con
evidencia y otra sin evidencia, y ejecutar el piloto controlado con cinco
personas de Operaciones. No distribuir todavía a toda la organización.

## Hito: manejo de JWT inválidos

Durante una prueba manual se detectó que los JWT malformados enviados a
`/api/messages` podían producir `500` por excepciones de PyJWT no capturadas
por el middleware de Microsoft Agents. Se ajustó el middleware propio para
convertir errores de formato, `kid` ausente y errores de validación PyJWT en
`401 Unauthorized`, sin procesar el mensaje.

Se añadieron dos pruebas de regresión y la suite completa pasó con **77
pruebas, OK**. El backend se redeplegó en `app-libras-prod` con estado
`RuntimeSuccessful`. La comprobación posterior confirmó:

- `/healthz`: `200` con `status=ok`.
- `/readyz`: `200` con `status=ready`.
- JWT sin segmentos: `401`.
- JWT con estructura inválida o sin `kid`: `401`.

## Hito: paquete Teams corregido para piloto

Después de retirar la solicitud pendiente, se actualizó el manifiesto para
el piloto controlado. La versión es `0.1.0`, el modo de instalación y el
alcance del bot son exclusivamente `personal`, y se incorporaron las URLs
corporativas de soporte, privacidad, términos y documentación administrativa.
El paquete validado contiene únicamente los tres archivos requeridos en la
raíz y quedó en `appPackage/build/Libras-Teams-pilot-0.1.0.zip`. El paquete
se envió nuevamente a Teams como solicitud de publicación y está pendiente de
la acción del administrador.
