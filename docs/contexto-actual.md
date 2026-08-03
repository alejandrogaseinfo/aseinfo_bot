# Contexto actual de Libras

> Documento de continuidad para cualquier persona o chat nuevo que retome el
> proyecto. Fecha de consolidación: 2026-07-31.

## Objetivo

Operar `Libras` como piloto controlado en Microsoft Teams, usando documentación
autorizada de SharePoint, y completar las pruebas de calidad y seguridad antes
de promocionarlo para usuarios de Aseinfo.

> **Límite de alcance:** Libras no es Bot-Salvador ni usa la carpeta histórica
> de planillas de México, El Salvador y Guatemala. Sus únicas fuentes son las
> bibliotecas autorizadas del sitio SharePoint `Soportealcliente`, descritas en
> este documento. Cualquier referencia a esas planillas en bitácoras antiguas
> es antecedente de un entorno distinto y no define pruebas, evidencia ni
> comportamiento esperado para Libras.

## Actualización de estado — 2026-07-31

- La aplicación ya está instalada y responde desde Microsoft Teams. También se
  validó en Azure Bot Test in Web Chat.
- La recuperación multi-biblioteca funciona: se comprobó una respuesta con
  `ReadME Hotfixes` y otra con `SOLUCIONES`, ambas con enlaces SharePoint
  verificables. Las bibliotecas activas son las indicadas en este documento.
- Las consultas que nombran bibliotecas fuera del alcance, como `Hojas de
  Servicio` y `Teams Wiki Data`, se rechazan antes de buscar para evitar que
  una respuesta de otra biblioteca parezca válida.
- Se corrigió la consulta por versión: una petición por `Evolution 1.19.1.10`
  recupera solamente el `Readme 1.19.1.10.pdf` y responde desde el fragmento
  citado, sin mezclar `1.19.1.0`, `1.19.1.3` ni `1.19.1.13`.
- Las preguntas por una sección concreta de un Readme priorizan esa sección y
  no la portada, el índice ni un PDF de actualización relacionado. Por ejemplo,
  los nuevos requisitos de software de `Readme 1.19.1.11` responden
  `Ninguno.` tal como consta en el documento.
- El backend productivo fue redeplegado y reiniciado después de esta corrección;
  `/readyz` respondió HTTP 200 y la suite automatizada registra **96 pruebas,
  OK**.

### Decisión temporal de acceso

Durante el piloto, cualquier persona de Aseinfo que pueda usar Microsoft Teams
puede interactuar con Libras. Libras consulta un índice creado con la identidad
de la aplicación; no implementa filtrado individual equivalente a los permisos
de SharePoint. Por tanto, este escenario solo es aceptable mientras el contenido
indexado se considere **interno general** para toda Aseinfo.

Antes de promocionar la aplicación, se realizará una revisión controlada de los
documentos sincronizados para detectar y excluir, redactar o mover contenido
con datos de clientes, contratos, credenciales, finanzas o información personal.
La revisión combinará detección automatizada de candidatos y validación manual
con los dueños documentales.

### Siguiente etapa

La prioridad inmediata es dejar el chat sólido en este escenario de acceso
interno general mediante pruebas controladas de alcance, relevancia, versiones,
solicitudes confidenciales e inyecciones de instrucciones. Dos comportamientos
detectados quedan pendientes de corrección: las preguntas sobre las capacidades
del bot deben responder con su alcance sin buscar documentos, y las solicitudes
de Internet deben indicar que Libras no navega ni consulta datos en tiempo real.

Después de cerrar estas pruebas y decidir el tratamiento del contenido sensible,
la siguiente fase será la integración con ClickUp.

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
- La recuperación conserva filtros genéricos de contexto cuando un documento
  autorizado los aporte, pero no se debe asumir que existen políticas de
  planilla por país en las fuentes de Libras. Las pruebas de relevancia deben
  partir de documentos realmente indexados desde `Soportealcliente`.
- El backend productivo respondió `ready` durante la validación previa y las
  pruebas automatizadas pasan: **96 pruebas, OK**.
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
P6, P7, P8 y P9. El antiguo P4 de Guatemala/El Salvador pertenece al entorno
anterior de Bot-Salvador y queda descartado como evidencia o criterio de
Libras. El detalle y la corrección de alcance están en
[evaluacion-piloto.md](evaluacion-piloto.md).

## Pendientes para completar el piloto de Teams

1. Ejecutar en Microsoft 365 Agents Playground, con el backend productivo
   recién desplegado, una prueba positiva con enlace de `SOLUCIONES` y una
   pregunta sin evidencia. La validación técnica de SharePoint y el índice ya
   está cerrada.
2. Ejecutar pruebas de relevancia con preguntas coloquiales sobre documentos
   realmente indexados en las bibliotecas autorizadas de `Soportealcliente`;
   comprobar que Libras no sustituya una respuesta por un documento que solo
   comparte términos generales.
3. Registrar la evidencia final en
   [plan-pruebas-playground.md](plan-pruebas-playground.md) y
   [evaluacion-piloto.md](evaluacion-piloto.md).
4. [x] Configurar en `bot-libras-prod` el endpoint de mensajería productivo.
5. [x] Habilitar el canal Microsoft Teams.
6. [x] Completar los IDs reales del manifiesto y generar el paquete `.zip`.
7. [x] Instalar el paquete como aplicación personalizada y validar su respuesta
   en Teams.
8. Completar las pruebas controladas de calidad, alcance y seguridad descritas
   en la actualización de estado antes de promover la aplicación para usuarios
   de Aseinfo.

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
mantener la recuperación limitada a las bibliotecas activamente autorizadas.
