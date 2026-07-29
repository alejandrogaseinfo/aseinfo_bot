# Matriz de evaluación del piloto de Libras

Usar esta matriz cuando estén disponibles los PDFs autorizados de la carpeta
piloto. La evaluación se realiza desde Teams y se registra sin copiar datos
sensibles, secretos ni fragmentos innecesarios.

| case_id | pregunta | PDF esperado | estado esperado | enlace correcto | respuesta fundamentada | inventó datos | latencia_ms | observaciones |
|---|---|---|---|---|---|---|---:|---|
| DOC-01 | Pendiente con pregunta real | Pendiente | resuelto | Sí/No | Sí/No | Sí/No |  |  |
| DOC-02 | Pendiente con pregunta real | Pendiente | resuelto | Sí/No | Sí/No | Sí/No |  |  |
| NOE-01 | Pregunta sin evidencia | Ninguno | sin_evidencia | N/A | Sí/No | Sí/No |  |  |

## Casos mínimos antes de producción

1. Dos preguntas respondidas por PDFs distintos.
2. Una pregunta cuya respuesta dependa de una versión o fecha concreta.
3. Una pregunta sin coincidencia, que debe escalar sin inventar una solución.
4. Un PDF actualizado: confirmar que la versión anterior deja de aparecer.
5. Un PDF eliminado: confirmar que ya no se recupera en Azure AI Search.

Registrar la duración desde el envío en Teams hasta la respuesta. La salida de
esta matriz respalda la validación funcional de la biblioteca piloto; no
sustituye los controles de acceso ni la aprobación de producción.

## Sesión de validación en Microsoft 365 Agents Playground — 2026-07-29

- Backend confirmado: entorno local en `http://127.0.0.1:3978/api/messages`.
- Playground confirmado: `http://127.0.0.1:56150/`.
- `/healthz` y `/readyz` del backend productivo: HTTP 200; esta sesión no usó
  producción para las consultas conversacionales.
- P1 — orientación: **aprobado** tras la corrección previa a publicación.
  Libras indica que consulta documentación técnica aprobada (procedimientos,
  manuales, hotfixes y actualizaciones), sin afirmar acceso a fuentes no
  configuradas. El registro de mensajes del Playground confirma la respuesta.
- P6 — fuera de alcance: **aprobado** tras la corrección previa a publicación.
  Ante la consulta sobre ClickUp, Libras responde que ClickUp todavía no está
  integrado y limita su alcance a la documentación técnica aprobada.
- P5 — sin evidencia: **aprobado**. Para la renovación del certificado SSL del
  portal, Libras indicó que no se proporcionó evidencia suficiente; no inventó
  un procedimiento. Latencia registrada en el Playground: aproximadamente 8 s.
- P7 — ambigua: **aprobado**. Libras pidió producto o módulo, versión y una
  pregunta concreta antes de buscar evidencia.
- P2 — evidencia y enlace: **aprobado**. La respuesta sobre ampliar el tiempo
  de sesión cita `Ampliar Tiempo de Sesion.pdf — Página 1 — Azure AI Search` y
  presenta su enlace HTTPS de SharePoint. Latencia aproximada: 11 s.
- P3 — procedimiento documentado: **aprobado**. La configuración de
  MiniProfiler se respondió desde `Configuración de MiniProfiler en Evolution`
  con fuente y enlace HTTPS de SharePoint. Latencia aproximada: 5 s.
- P4 — separación por país: **aprobado**. En una sesión con Guatemala se citó
  solamente `GT - Políticas de Pago Mensual.pdf` (4 agrupaciones); en una
  sesión limpia con El Salvador se citó solamente `Políticas de Pago SV.pdf`
  (ISSS, AFP e Impuesto sobre la Renta). No hubo cruce de fuentes. Ambos
  enlaces son HTTPS de SharePoint corporativo; el de El Salvador usa el dominio
  corporativo personal `aseinfocorp-my.sharepoint.com`. Latencias aproximadas:
  5 s para Guatemala y 10 s para El Salvador.
- P8 — sin evidencia: **aprobado**. Para el procedimiento de vacaciones de
  Recursos Humanos, Libras indicó que no se proporcionó evidencia directa y no
  mostró fuente ni enlace. Latencia aproximada: 5 s.
- P9 — seguimiento: **aprobado**. Después de P2, Libras entregó el resumen de
  los tres pasos y preservó la fuente y el enlace de SharePoint, sin búsqueda
  adicional. Latencia inferior a 1 s.

Resultado provisional: **listo para solicitar autorización de publicación en
Teams**. No se realizó publicación ni cambio de distribución en Teams.

## Preparación de P2, P3, P4, P8 y P9 — 2026-07-29

- Prevalidación del índice autorizado: 158 fragmentos; todos con procedencia
  SharePoint y enlace HTTPS. Los metadatos con ruta pertenecen a una sola
  carpeta de origen del índice.
- P2 — evidencia y enlace: usar `¿Cuáles son los pasos documentados para
  ampliar el tiempo de sesión en Evolution?`. La recuperación devuelve el PDF
  `Ampliar Tiempo de Sesion` con fuente y enlace HTTPS verificables.
- P3 — procedimiento documentado: usar `¿Qué configuración documentada tiene
  MiniProfiler en Evolution 1.10.0 o superior?`. La recuperación devuelve el
  PDF de `Configuración de MiniProfiler en Evolution` con fuente y enlace HTTPS.
- P4 — separación por país: ejecutar como dos subcasos independientes:
  - Guatemala: `En Guatemala, ¿cuántas agrupaciones de tipos de ingresos se
    deben identificar en la política de pago mensual?` Debe citar solamente
    `GT - Políticas de Pago Mensual`.
  - El Salvador: `En El Salvador, ¿qué descuentos de ley se aplican en la
    planilla quincenal?` Debe citar solamente `Políticas de Pago SV`.
- P8 — acceso no autorizado: usar `¿Cuál es el procedimiento oficial de
  Recursos Humanos para aprobar vacaciones?`. La respuesta final comprobada
  indica que no recuperó evidencia relevante y no incluye fuente ni enlace.
- P9 — seguimiento: después de P2 o P3, usar `¿Puedes resumir esos pasos en
  una lista corta?`. La implementación conserva la última respuesta documental
  por conversación y reproduce su fuente y enlace, sin ejecutar una búsqueda
  adicional.

Correcciones incorporadas antes de la ejecución final en Playground:

1. Se descarta evidencia que no sea de SharePoint HTTPS.
2. Una consulta con país explícito excluye resultados de otro país y documentos
   con pies de página multinacionales que no prueban aplicabilidad local.
3. Una coincidencia con pocos términos específicos se considera insuficiente,
   para evitar respuestas de temas fuera del índice.
4. El seguimiento documental resume la respuesta previa conservando su fuente.

Validación técnica: 69 pruebas automatizadas aprobadas.

## Rectificación de evidencia y ejecución final — 2026-07-29

La sesión anterior que mostraba políticas de Guatemala y El Salvador queda
invalidada: el Playground estaba conectado a una instancia antigua con
configuración local y documentos de `RAG-Piloto`. No se usa como evidencia de
producción.

Se reconstruyó el índice productivo con el estado vigente de SharePoint:

- 15 PDF descargados desde `Documentos compartidos/SOLUCIONES`.
- 108 fragmentos indexados.
- 15 URLs autorizadas; 0 URLs inesperadas y 0 documentos de `RAG-Piloto`.
- Backend confirmado con `environment=production`, Azure AI Search requerido y
  `/healthz`/`/readyz` en HTTP 200.

Ejecución final en Microsoft 365 Agents Playground conectado al backend
productivo:

- P2 — **aprobado**: MiniProfiler respondió con parámetros documentados y
  enlace HTTPS corporativo dentro de `SOLUCIONES`.
- P3 — **aprobado**: entregó el procedimiento documentado con fuente, páginas
  y enlace HTTPS corporativo.
- P4 — **sin evidencia disponible**: Guatemala y El Salvador respondieron sin
  datos, sin mezclar países ni citar documentos fuera de la carpeta autorizada.
  La carpeta actual no contiene PDFs de políticas por país.
- P8 — **aprobado como control negativo**: la consulta de políticas de México
  no recuperó evidencia ni enlace desde una fuente no autorizada.
- P9 — **aprobado**: resumió la respuesta documental previa y conservó su
  fuente y enlace.

Estado actual: **no solicitar todavía la publicación en Teams**. Falta decidir
si se incorporan a la carpeta autorizada documentos aprobados de políticas de
Guatemala y El Salvador, y luego repetir P4. No se realizó publicación ni
cambio de distribución en Teams.

## Ampliación a todo el contenido legible de SOLUCIONES — 2026-07-29

El alcance se amplió de PDF-only a todos los formatos con texto recuperable de
la carpeta autorizada. La sincronización descargó 200 archivos: 15 PDF, 29
DOCX, 8 XLSX, 88 SQL, 26 TXT, 20 RDLC, 6 XML, 4 PS1, 2 ASPX, 1 CSV y 1 BAT.
Los archivos binarios restantes no se indexan.

La reconstrucción final generó 2.354 fragmentos correspondientes a 197
documentos con texto, todos con `source_system=sharepoint`, sin URLs
inesperadas ni referencias a `RAG-Piloto`. Tres archivos quedaron fuera: un TXT
vacío y dos DOCX sin texto extraíble; se mantienen registrados en el estado de
sincronización.

Regresión final en Agents Playground:

- P1, P2, P3, P5, P6, P7, P8 y P9: **aprobados**.
- P4 Guatemala: **sin evidencia**, correctamente sin inventar política.
- P4 El Salvador: recuperó un SQL de alertas de recibo de pago específico de
  El Salvador, con enlace de `SOLUCIONES`; no mezcló una fuente guatemalteca.
- Se validaron además consultas sobre SQL y XLSX con enlaces SharePoint.
- No se realizó publicación ni cambio de distribución en Teams.

## Alcance autorizado confirmado — 2026-07-29

La instrucción recibida autoriza consultar cualquier documento de la carpeta
`Documentos compartidos/SOLUCIONES`, incluidas sus subcarpetas. El enlace
compartido apunta específicamente a esa carpeta; no autoriza por sí mismo el
acceso a otras bibliotecas o ubicaciones de SharePoint. `ReadME Hotfixes` queda
fuera del alcance activo y no debe consultarse ni indexarse para esta versión.

La validación de fuentes, evidencia y enlaces queda limitada a `SOLUCIONES`.
No se publicó nada ni se cambió la distribución en Teams.
