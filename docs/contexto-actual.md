# Contexto actual de Libras

## Estado vigente — 2026-08-12

La validación posterior de calidad se ejecutó contra `srch-libras-prod/libras-docs`
con **331/331 pruebas locales aprobadas** y una comparación A/B de 12 preguntas
operativas sin fallback local. La variante experimental AI-first quedó detrás
de `USE_AI_FIRST_EXPERIMENTAL` y no se desplegó. El redactor grounded está
activo únicamente durante la ventana controlada vigente; fuera de ella debe
permanecer apagado.

Las correcciones vigentes incluyen deduplicación y validación de citas de
Readme, priorización de `Manual de Relacion DB V1.2` para consultas IRA con
versión no confirmada y permiso acotado para `Ofuscación de datos.sql`. La
estrategia productiva sigue siendo `legacy` y
`USE_LLM_EVIDENCE_VERIFIER=false`; `USE_LLM_GROUNDED_RESPONSE=true` solo en la
ventana controlada vigente.

El detalle reproducible está en
[docs/resultado-calidad-20260812.md](resultado-calidad-20260812.md) y la
muestra humana en [docs/revision-humana-redactor-20260812.md](revision-humana-redactor-20260812.md).

### Ejecución segura de evaluaciones en App Service

Para validaciones remotas, Kudu se usa únicamente para File Manager y
comprobaciones de archivos. La ejecución Python debe hacerse desde **SSH →
Application**, donde está activo `antenv` y están instaladas las dependencias.
Cuando se pruebe una copia temporal ubicada bajo `/home/site/wwwroot/src`, se
debe anteponer `PYTHONPATH="$PWD/src"`; esto no activa el evaluador LLM ni
promueve el código a producción.

Un bundle de evaluación sin `tests/test_*.py` no permite validar la suite:
`unittest discover` puede reportar `Ran 0 tests`. La suite completa y sus
regresiones se validan en el repositorio local. Una evaluación Azure remota
puede ejecutarse por separado con el corpus, registrando siempre qué copia de
`src` se utilizó y sin interpretar el resultado como prueba de despliegue.

Las cifras 13/15 y 303/303 pertenecen a una ejecución histórica de agosto y no
son la línea base vigente. La línea base actual es **315/315 pruebas OK**; el
detalle y la comparación A/B de 12 preguntas están en
[resultado-calidad-20260812.md](resultado-calidad-20260812.md). El contrato del
corpus acepta `evidence`, `sin_evidencia` y `solicita_contexto`.

Las secciones fechadas que siguen se conservan como bitácora de decisiones y
no deben interpretarse como estado operativo actual.

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

## Actualización de calidad y paquete — 2026-08-05

- La matriz funcional contra `libras-docs` termina en **12/12 casos**, con
  recall de evidencia y abstención correcta del 100%.
- La resolución de parámetros de incapacidades recupera las páginas
  operativas 34, 36 y 37; las páginas de índice ya no se presentan como
  evidencia.
- La suite automatizada queda en **175 pruebas, OK** y el preflight de
  plataforma pasa completo.
- Se generó el paquete Teams [`Libras-Teams-pilot-2026-08-05-v0.1.1.zip`](../appPackage/build/Libras-Teams-pilot-2026-08-05-v0.1.1.zip).
- El preflight de acceso de ingesta permanece pendiente por variables locales
  de SharePoint/Key Vault. La preparación no modificó el índice; el despliegue
  del backend se realizó después, sin cambiar documentos ni fuentes.
- El backend validado fue publicado en `app-libras-prod` mediante OneDeploy el
  2026-08-05; el despliegue terminó con `complete=true` y sin errores.
  `/healthz` y `/readyz` del dominio productivo respondieron HTTP 200.
- La aplicación Libras ya aparece aprobada y disponible en Teams dentro de
  “Diseñadas para tu organización”. El despliegue del backend no requiere
  reinstalar el paquete; el ZIP Teams v0.1.1 solo sería necesario si cambia el
  manifiesto o los IDs de la aplicación.

## Actualización de producción — 2026-08-09

- Se publicó el backend actualizado en `app-libras-prod` mediante ZipDeploy.
  Azure reportó `RuntimeSuccessful`, sin instancias fallidas. Identificador:
  `6e10b0c2-f96c-4019-b574-5c9cec0ded92`.
- La versión incluye el enrutamiento general `fuera_alcance`, que rechaza
  consultas externas antes de recuperar documentos o generar respuestas
  conversacionales, además de las correcciones de recuperación incorporadas
  en la versión local.
- La suite automatizada queda en **269 pruebas, OK**.
- Después del despliegue, `/healthz` y `/readyz` respondieron HTTP 200; el
  entorno reporta `production`, Azure AI Search configurado y sin dependencias
  faltantes. No se modificó el manifiesto ni se activó Conversations API.
- `LIBRAS_RUNTIME_REVISION` quedó configurada como `0.1.3`. El campo de
  revisión expuesto por el proceso continúa mostrando un valor anterior y
  requiere una revisión posterior de la configuración de entorno persistente;
  esto no impidió el arranque ni la validación de readiness.

## Decisión sobre contexto durable — 2026-08-08

- Conversations API queda **diferida** hasta revisión con la jefatura y hasta
  que el administrador de Azure esté disponible.
- Para el piloto se mantiene el contexto efímero y acotado del mismo chat de
  Teams. Conserva únicamente producto/módulo, versión, tipo de consulta,
  etiqueta de la última fuente y la última respuesta documental apta para
  resumen; es suficiente para referencias como “esa versión” y “lo anterior”.
- La aplicación no almacenará el transcript completo ni requerirá Azure Table
  Storage para esta fase. La bandera `USE_OPENAI_CONVERSATIONS` permanece en
  `false`.
- El análisis, las condiciones de retención y los criterios para reabrir la
  decisión se conservan en
  [plan-implementacion-conversations-api.md](plan-implementacion-conversations-api.md).

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
  `/readyz` respondió HTTP 200. La suite local de la corrección de calidad
  registra **134 pruebas, OK** el 2026-08-04, pero esto no sustituye la
  evaluación contra el índice productivo real.

## Corrección de calidad — 2026-08-03

Las pruebas de uso real identificaron fallos en seguridad, conversación y
recuperación semántica. El trabajo correctivo está centralizado en
[plan-correccion-calidad-libras.md](plan-correccion-calidad-libras.md). No se
orientará el sistema a contestar frases concretas: se corregirán las reglas de
riesgo, el enrutamiento, el índice, el ranking, la verificación de evidencia y
la memoria conversacional.

El primer caso confirmado es un falso positivo: una pregunta técnica sobre
prórroga de contratos se bloquea por una regla que trata cualquier `contrato`
como confidencial. Antes de reindexar se debe crear un inventario verificable
del índice activo y una línea base de evaluación con documentos reales de las
fuentes autorizadas.

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

### Evolución de experiencia planificada

Sin alterar el objetivo de cierre del piloto ni el orden de integraciones
posteriores, el seguimiento dentro del mismo chat, enlaces legibles, acciones
iniciales y comandos se centralizan en
[plan-evolucion-conversacional-libras.md](plan-evolucion-conversacional-libras.md).
Se mantiene el estado efímero y acotado del mismo chat. Conversations API se
reconsiderará únicamente si se aprueba una necesidad concreta de continuidad
del historial completo entre sesiones o reinicios, conforme a
[plan-implementacion-conversations-api.md](plan-implementacion-conversations-api.md).

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

## Piloto técnico acotado (2026-08-05)

El piloto productivo se limitó explícitamente a estas cuatro fuentes:

- `ReadME Hotfixes`;
- `Documentos/SOLUCIONES`;
- `Manuales`;
- `Scripts de Apoyo`.

La restricción se aplica en `app-libras-prod` por la pareja
`drive_id`/`folder_path`, por lo que los registros de otras bibliotecas no se
pueden usar para responder, aun si permanecen en el índice histórico. Quedan
fuera Legislaciones, Traslados OP/DE, Parches Adicionales, Hojas de Servicio,
Teams Wiki Data y Documentos de Apoyo. Los nueve documentos de Apoyo que antes
formaban parte de la curación técnica también quedan temporalmente fuera: no
se autoriza la biblioteca completa mientras no exista una lista blanca por
documento.

No se reindexó ni se cambió el SKU: `libras-docs` conserva 2,665 fragmentos y
el respaldo previo está en `output/prod-backup-before-v2-20260805` (hash
`cdc40f7ed73c86abb568e706dc893f15ee19678a1b93f5485a0d4f16301fa449`). Tras
aplicar el alcance, `/healthz` y `/readyz` respondieron HTTP 200. La estrategia
de recuperación de producción continúa en `legacy`; v2 sigue pendiente de una
promoción separada.
