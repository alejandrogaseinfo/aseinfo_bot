# Contexto actual de Libras

> Documento de continuidad para cualquier persona o chat nuevo que retome el
> proyecto. Fecha de consolidación: 2026-07-31.

## Objetivo

Preparar `Libras`, un asistente interno, para que consulte documentación
autorizada desde Microsoft 365 Agents Playground y pueda publicarse como piloto
controlado en Microsoft Teams. La infraestructura de Azure Bot ya fue creada;
la publicación y distribución del paquete de Teams todavía están pendientes.

## Alcance documental autorizado

La autorización recibida se basa en este enlace de SharePoint:

`https://aseinfocorp.sharepoint.com/sites/Soportealcliente/Documentos%20compartidos/Forms/AllItems.aspx?id=%2Fsites%2FSoportealcliente%2FDocumentos%20compartidos%2FSOLUCIONES`

El administrador autorizó la aplicación de ingesta con rol `read` sobre el sitio
`/sites/Soportealcliente` y entregó los `Drive ID` de sus bibliotecas. El alcance
activo se amplió a `ReadME Hotfixes`, `Documentos` (solo `SOLUCIONES`),
`Legislaciones`, `Traslados OP/DE`, `Parches Adicionales`, `Documentos de Apoyo`,
`Manuales` y `Scripts de Apoyo`. `Hojas de Servicio` se deja fuera del alcance
actual por su volumen pendiente de procesar. `Teams Wiki Data` queda fuera por
ser una biblioteca de datos de sistema.

## Arquitectura vigente

```text
Microsoft 365 Agents Playground / Teams
        -> app-libras-prod
        -> Azure AI Search: srch-libras-prod / libras-docs
        <- sincronización de aplicación desde bibliotecas aprobadas de SharePoint
```

- App Service: `app-libras-prod`, Resource Group `rg-libras-prod`, Central US.
- Índice de producción: `libras-docs` en `srch-libras-prod`.
- Aplicación de ingesta: `libras-sharepoint-ingestion-prod`.
- Site ID, drive IDs y secreto están en archivos de entorno/Key Vault; el
  secreto no se debe copiar a documentación, Git, mensajes ni logs.
- La configuración activa usa listas alineadas de `SHAREPOINT_DRIVE_IDS` y
  `SHAREPOINT_FOLDER_PATHS`; una ruta vacía significa la raíz de esa biblioteca.

## Estado técnico

- El flujo de recuperación con Azure AI Search está implementado.
- Se admiten documentos legibles como PDF, DOCX, XLSX, TXT, CSV, SQL, XML,
  RDLC, ASPX, PowerShell, BAT y JSON.
- La respuesta exige evidencia recuperada y enlace SharePoint; sin evidencia,
  el bot debe reconocer la limitación y no inventar.
- La separación contextual Guatemala–El Salvador está cubierta por las
  pruebas de recuperación; no se deben mezclar países, versiones ni fuentes.
- El backend productivo respondió `ready` durante la validación previa y las
  pruebas automatizadas pasan: **79 pruebas, OK**.
- La validación anterior encontró 250 archivos en `SOLUCIONES`, de los cuales
  200 tenían formatos de texto admitidos. `libras-docs` fue reconstruido con
  **2.354 fragmentos**; la carga ampliada requiere un nuevo inventario y
  reconstrucción del índice.
- La recuperación productiva valida la combinación autorizada de `drive_id` y
  `folder_path`, además de procedencia SharePoint HTTPS. Así, una fuente no
  incluida en la lista no puede usarse como evidencia aunque aparezca en el
  índice.
- El proveedor `Microsoft.BotService` quedó registrado en la suscripción
  `ASEINFO Azure` el 30 de julio de 2026.
- Se creó el recurso Azure Bot `bot-libras-prod` en `rg-libras-prod`, con plan
  `Free`, residencia `Global` y tipo `User-Assigned Managed Identity`.
- El Azure Bot reutiliza `id-libras-bot-prod`; no se creó una identidad nueva.
  Su Client ID es `bac24639-da91-45a3-ae85-062b07188b9c`.
- El despliegue del recurso terminó correctamente. El endpoint de mensajería ya
  apunta al App Service productivo, el canal Microsoft Teams está habilitado y
  el paquete de piloto fue generado.
- La validación en Test in Web Chat del 30 de julio detectó un falso positivo:
  una guía técnica sobre creación y modificación de vacaciones se presentó como
  procedimiento de aprobación. La corrección fue redeplegada; la consulta debe
  volver a validarse antes del piloto y responder sin evidencia.
- La prueba en Test in Web Chat también detectó que una solicitud de clave API
  podía llegar a Azure AI Search. Se añadió una barrera de rechazo previa a la
  búsqueda y se redeplegó correctamente; falta validar el caso P10 de
  solicitudes de secretos en Test in Web Chat.
- Se detectaron falsas respuestas ante solicitudes de datos de clientes, pagos
  atrasados e inventario del sitio. La barrera de rechazo previa a la búsqueda
  ya fue redeplegada; falta validar el caso P11 en Test in Web Chat.
- El commit de consolidación anterior es `d7b1222`.
- Las cifras antiguas de 15 PDFs y 158 fragmentos que aparecen en la bitácora
  de producción son históricas y no deben tomarse como inventario actual.

## Pruebas realizadas

En Microsoft 365 Agents Playground se validaron los casos P1, P2, P3, P5,
P6, P7, P8 y P9. P4 Guatemala respondió sin evidencia cuando no había respaldo
autorizado; P4 El Salvador recuperó evidencia específica sin mezclar una
fuente guatemalteca. El detalle está en
[evaluacion-piloto.md](evaluacion-piloto.md).

## Pendientes para completar el piloto de Teams

1. Ejecutar en Microsoft 365 Agents Playground, con el backend productivo
   recién desplegado, una prueba positiva con enlace de `SOLUCIONES` y una
   pregunta sin evidencia. La validación técnica de SharePoint y el índice ya
   está cerrada.
2. Repetir las pruebas de separación Guatemala–El Salvador cuando haya
   evidencia aplicable dentro de `SOLUCIONES`; no sustituir evidencia de otro
   país.
3. Registrar la evidencia final en
   [plan-pruebas-playground.md](plan-pruebas-playground.md) y
   [evaluacion-piloto.md](evaluacion-piloto.md).
4. [x] Configurar en `bot-libras-prod` el endpoint de mensajería productivo.
5. [x] Habilitar el canal Microsoft Teams.
6. [x] Completar los IDs reales del manifiesto y generar el paquete `.zip`.
7. Instalar el paquete como aplicación personalizada y validar el piloto con
   las cinco personas autorizadas de Operaciones.
8. Solicitar posteriormente la distribución controlada desde Teams Admin
   Center. No publicar automáticamente para toda la organización.

## Cómo retomar el trabajo

Leer en este orden:

1. Este documento.
2. [produccion-semana.md](produccion-semana.md), para infraestructura y
   pendientes operativos.
3. [azure-ai-search-sharepoint.md](azure-ai-search-sharepoint.md), para
   configuración de SharePoint e ingesta.
4. [plan-pruebas-playground.md](plan-pruebas-playground.md), para ejecutar las
   pruebas.

Antes de cambiar código, comprobar `git status`, no imprimir secretos y
mantener `ReadME Hotfixes` fuera del alcance activo.
