# Requerimientos del MCP de DownloadAseinfo.net para el MVP de Chat-Salvador

## 1. Propósito

Este documento define el alcance funcional y técnico del MCP que expondrá la documentación de `DownloadAseinfo.net` al bot `Chat-Salvador`.

Está pensado para que el responsable de la aplicación pueda entregarlo a Codex como especificación de implementación.

El MCP debe ser una interfaz segura y de solo lectura para:

1. descubrir documentos;
2. obtener metadatos;
3. recuperar contenido extraíble;
4. preparar documentos para Azure AI Search o el índice local;
5. permitir que el bot muestre la fuente original.

Este documento es un anexo del [mapa único del MVP](plan-mvp-presentacion-lunes.md).

## 2. Contexto

Chat-Salvador es un bot de Microsoft Teams para soporte y operaciones. Debe responder consultas sobre información que ya existe en:

- releases;
- readmes;
- setups;
- hotfixes;
- changelogs;
- notas de instalación;
- presentaciones técnicas;
- documentos relacionados con entregas de productos.

`DownloadAseinfo.net` será la fuente documental principal del MVP porque ya contiene información utilizada por los equipos. El MCP no debe modificar la aplicación ni convertirse en el sistema de almacenamiento del bot.

La búsqueda vectorial y la generación de respuestas serán responsabilidad de otros componentes:

```text
DownloadAseinfo.net
        ↓
MCP de DownloadAseinfo.net
        ↓
Cliente MCP de Chat-Salvador
        ↓
Normalización de evidencia
        ↓
Azure AI Search o índice local
        ↓
Respuesta fundamentada en Teams
```

## 3. Alcance

### Incluido en la primera versión

- acceso de solo lectura;
- listado paginado de documentos;
- filtros básicos;
- obtención de metadatos;
- obtención de contenido extraíble;
- identificadores estables;
- URL o ubicación original;
- producto, versión, release y fechas;
- manejo de errores controlado;
- autenticación para un ambiente de prueba;
- pruebas automatizadas;
- ejemplos reales de documentos.

### Fuera de alcance de la primera versión

- crear documentos;
- modificar documentos;
- eliminar documentos desde el MCP;
- publicar releases;
- cambiar permisos;
- generación de respuestas con IA;
- clasificación de consultas;
- búsqueda vectorial dentro del MCP;
- sincronización automática completa;
- indexación obligatoria directa en Azure AI Search;
- scraping de HTML si existe una API, endpoint o acceso interno más estable.

La primera versión debe ser pequeña, estable y suficiente para alimentar el MVP. No debe intentar resolver todos los problemas futuros de integración.

## 4. Principios de implementación

1. Preferir API, servicio interno o acceso controlado a la fuente de datos antes que scraping de la interfaz web.
2. Mantener el MCP independiente del backend de Teams.
3. No acoplar el MCP a OpenAI ni a Azure AI Search.
4. Usar una identidad de solo lectura.
5. No devolver documentos o metadatos no autorizados.
6. Devolver errores explícitos; no ocultar un error como ausencia de información.
7. Mantener identificadores estables.
8. No devolver contenido completo en el listado.
9. No inventar metadatos que no existan en la fuente.
10. Mantener una versión documentada del contrato.

## 5. Herramientas MCP requeridas

La primera versión debe exponer como mínimo:

```text
list_documents
get_document_metadata
get_document_content
```

Los nombres pueden adaptarse a la convención del servidor, pero se recomienda conservarlos para simplificar la integración con Codex y Chat-Salvador.

## 6. Herramienta `list_documents`

### Objetivo

Obtener el catálogo de documentos disponibles sin transferir el contenido completo.

### Entrada

```json
{
  "cursor": "string | null",
  "limit": 50,
  "product": "string | null",
  "module": "string | null",
  "version": "string | null",
  "release": "string | null",
  "document_type": "string | null",
  "updated_after": "ISO-8601 datetime | null",
  "include_archived": false
}
```

### Reglas de entrada

- `cursor` es opcional y permite continuar una consulta paginada.
- `limit` debe tener un valor por defecto y un máximo; se recomienda máximo `100`.
- Los filtros son opcionales.
- `updated_after` debe aceptar ISO-8601 con zona horaria.
- Los valores inválidos deben devolver `INVALID_FILTER` o `INVALID_ARGUMENT`.
- La respuesta no debe incluir el contenido completo de cada documento.

### Salida

```json
{
  "items": [
    {
      "document_id": "doc-123",
      "title": "Release Evolution Connect 2.8.0",
      "file_name": "release-evolution-connect-2.8.0.pptx",
      "document_type": "release",
      "product": "Evolution Connect",
      "module": null,
      "version": "2.8.0",
      "release": "2026-03-26",
      "published_at": "2026-03-26T10:00:00Z",
      "updated_at": "2026-03-26T10:00:00Z",
      "source_url": "https://downloadaseinfo.net/...",
      "mime_type": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
      "size_bytes": 245760,
      "content_available": true,
      "status": "active",
      "content_hash": "sha256:..."
    }
  ],
  "next_cursor": "string | null",
  "has_more": false,
  "total_count": 1
}
```

### Estados de documento

Se recomienda utilizar:

- `active`: documento disponible y vigente según la fuente;
- `archived`: documento disponible, pero archivado;
- `deleted`: el identificador se conserva, pero el contenido ya no está disponible;
- `unknown`: la fuente no proporciona estado.

Los documentos `deleted` no deben devolverse como contenido disponible, pero pueden aparecer para que una futura sincronización detecte eliminaciones.

## 7. Herramienta `get_document_metadata`

### Entrada

```json
{
  "document_id": "doc-123"
}
```

### Salida

```json
{
  "document_id": "doc-123",
  "title": "Release Evolution Connect 2.8.0",
  "file_name": "release-evolution-connect-2.8.0.pptx",
  "document_type": "release",
  "product": "Evolution Connect",
  "module": null,
  "version": "2.8.0",
  "release": "2026-03-26",
  "published_at": "2026-03-26T10:00:00Z",
  "updated_at": "2026-03-26T10:00:00Z",
  "source_url": "https://downloadaseinfo.net/...",
  "mime_type": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
  "size_bytes": 245760,
  "content_available": true,
  "content_hash": "sha256:...",
  "status": "active"
}
```

### Reglas

- `document_id` debe ser estable entre consultas.
- Si no existe, devolver `NOT_FOUND`.
- Si existe pero no hay permiso, devolver `FORBIDDEN`.
- No devolver el contenido completo en esta herramienta.
- Los campos desconocidos deben devolverse como `null`.

## 8. Herramienta `get_document_content`

### Entrada

```json
{
  "document_id": "doc-123",
  "include_metadata": true,
  "max_characters": 200000
}
```

### Salida

```json
{
  "document_id": "doc-123",
  "title": "Release Evolution Connect 2.8.0",
  "content": "Texto extraído del documento...",
  "content_format": "plain_text",
  "mime_type": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
  "content_hash": "sha256:...",
  "truncated": false,
  "extraction_status": "success",
  "extraction_error": null,
  "source_url": "https://downloadaseinfo.net/...",
  "metadata": {
    "product": "Evolution Connect",
    "version": "2.8.0",
    "release": "2026-03-26"
  }
}
```

### Reglas de contenido

- El contenido debe ser texto UTF-8 o declarar su codificación.
- Debe conservar títulos, secciones, listas y referencias importantes.
- En PowerPoint, incluir número o título de diapositiva cuando sea posible.
- En PDF, conservar el orden razonable de las páginas.
- En Word, conservar títulos y párrafos.
- En Markdown y TXT, devolver el texto original o una versión limpiada sin perder contexto.
- Si el contenido se trunca, `truncated` debe ser `true`.
- Si no se puede extraer texto, `extraction_status` debe indicar el fallo y debe conservarse la URL de descarga.

## 9. Metadatos mínimos

El MCP debe devolver, cuando estén disponibles:

- `document_id`;
- `title`;
- `file_name`;
- `document_type`;
- `product`;
- `module`;
- `version`;
- `release`;
- `published_at`;
- `updated_at`;
- `source_url`;
- `mime_type`;
- `size_bytes`;
- `content_available`;
- `status`;
- `content_hash`.

Los campos inexistentes deben devolverse como `null`, no omitirse de forma inconsistente.

## 10. Tipos de documento

Se recomienda normalizar los tipos a estos valores:

| Tipo | Uso |
|---|---|
| `readme` | Documentación general o de repositorio |
| `release` | Notas de una entrega |
| `setup` | Instalación y configuración |
| `hotfix` | Correcciones y notas de hotfix |
| `changelog` | Cambios acumulados |
| `presentation` | Presentación técnica |
| `procedure` | Procedimiento operativo |
| `technical_note` | Nota técnica |
| `other` | Documento aún no clasificado |

La extensión del archivo no debe ser el único criterio de clasificación. Si la aplicación ya tiene una clasificación interna, se debe reutilizar o documentar la regla.

## 11. Formatos y extracción

### Prioridad P0

- Markdown;
- TXT;
- PDF con texto;
- PowerPoint con texto.

### Prioridad P1

- Word;
- ZIP con documentos técnicos;
- PDF escaneado con OCR.

### Reglas de seguridad

- No ejecutar macros.
- No ejecutar archivos descargados.
- Validar extensión y MIME type.
- Protegerse contra path traversal al procesar ZIP.
- Limitar tamaño de archivo y consumo de memoria.
- Registrar el resultado de extracción.
- Considerar error un documento cuyo contenido extraído quede vacío.

Si un formato no está soportado en P0, el MCP debe devolver `UNSUPPORTED_FORMAT` o una URL de descarga segura. No debe fingir que el contenido fue extraído.

## 12. Identidad y cambios de documentos

### Identificador estable

`document_id` no debe depender únicamente del nombre visible del archivo. Debe mantenerse estable mientras la fuente considere que se trata del mismo documento.

### Hash de contenido

Se recomienda devolver un hash SHA-256:

```text
sha256:abcdef...
```

El hash permitirá detectar cambios, evitar reindexaciones innecesarias y auditar qué contenido se utilizó.

### Fechas

Todas las fechas deben utilizar ISO-8601 con zona horaria:

```text
2026-03-26T10:00:00Z
```

## 13. Sincronización incremental

La sincronización automática no es obligatoria para la demo, pero el contrato debe dejarla preparada.

Como mínimo, `list_documents` debería aceptar:

```text
updated_after="2026-03-01T00:00:00Z"
```

En el futuro debe permitir detectar:

- documentos nuevos;
- documentos modificados;
- documentos archivados;
- documentos eliminados;
- cambios de contenido mediante `content_hash`.

Para el MVP se acepta una sincronización manual ejecutada por un script.

## 14. Búsqueda dentro del MCP

### No obligatoria para P0

No es necesario implementar búsqueda vectorial dentro del MCP. Azure AI Search será el componente encargado de la búsqueda documental.

### Opcional P1

Si resulta sencilla, se puede agregar:

```text
search_documents(
  query,
  product?,
  module?,
  version?,
  document_type?,
  limit?
)
```

Esta búsqueda puede ser textual y basada en filtros. No debe duplicar la responsabilidad de Azure AI Search.

## 15. Errores

El MCP debe devolver códigos estables y mensajes seguros.

| Código | Significado |
|---|---|
| `INVALID_ARGUMENT` | Parámetros inválidos |
| `INVALID_FILTER` | Filtro no soportado o mal formado |
| `AUTH_REQUIRED` | Falta autenticación |
| `FORBIDDEN` | La identidad no tiene permiso |
| `NOT_FOUND` | Documento inexistente |
| `UNSUPPORTED_FORMAT` | Formato no soportado |
| `EXTRACTION_FAILED` | No se pudo extraer contenido |
| `RATE_LIMITED` | Se excedió el límite de consultas |
| `TIMEOUT` | La fuente tardó demasiado |
| `UPSTREAM_UNAVAILABLE` | La aplicación origen no responde |
| `INTERNAL_ERROR` | Error interno no esperado |

### Formato sugerido

```json
{
  "error": {
    "code": "FORBIDDEN",
    "message": "La identidad utilizada no tiene acceso al documento solicitado.",
    "retryable": false,
    "request_id": "req-123"
  }
}
```

### Reglas de errores

- No incluir tokens.
- No incluir cadenas de conexión.
- No devolver stack traces al cliente.
- No revelar rutas internas innecesarias.
- Incluir `request_id` para diagnóstico.
- Indicar `retryable` cuando sea posible.

## 16. Autenticación y permisos

### Requisito mínimo

El MCP debe utilizar una identidad de solo lectura para el ambiente de desarrollo o prueba.

### Debe documentarse

- endpoint del MCP;
- ambiente al que corresponde;
- método de autenticación;
- identidad de servicio;
- permisos concedidos;
- expiración o rotación de credenciales;
- restricciones de red;
- procedimiento para revocar acceso.

### La identidad no debe poder

- crear documentos;
- modificar documentos;
- eliminar documentos;
- cambiar permisos;
- publicar entregas;
- consultar información fuera del catálogo autorizado.

## 17. Límites y rendimiento

Valores iniciales recomendados:

| Operación | Recomendación |
|---|---|
| `list_documents.limit` por defecto | 50 |
| `list_documents.limit` máximo | 100 |
| Timeout de listado | 15 segundos |
| Timeout de metadatos | 10 segundos |
| Timeout de contenido | 30 segundos |
| Máximo de caracteres | Configurable; sugerido 200.000 |
| Concurrencia | Limitada para proteger la fuente |
| Reintentos | Solo en errores transitorios y con backoff |

Si el MCP no responde, el cliente del bot debe poder continuar con las demás fuentes o con el fallback local. El error debe quedar registrado y visible como dependencia no disponible.

## 18. Integración con Chat-Salvador

El cliente del bot debe convertir los resultados del MCP a su modelo común de evidencia.

| Campo del MCP | Campo conceptual del bot |
|---|---|
| `document_id` | `source_id` |
| `document_type` | `document_type` o `tipo` |
| `title` | `titulo` |
| `source_url` | `ubicacion` |
| `content` | `fragmento` o entrada para chunking |
| `product` | `product` |
| `module` | `module` |
| `version` | `version` |
| `updated_at` | `updated_at` |
| `content_hash` | `content_hash` |

El bot debe conservar la referencia al documento original aunque el contenido se fragmente para Azure AI Search.

## 19. Flujo de ingestión inicial

```text
list_documents
      ↓
filtrar documentos autorizados y soportados
      ↓
get_document_metadata
      ↓
get_document_content
      ↓
normalizar texto y metadatos
      ↓
fragmentar por secciones
      ↓
indexar en Azure AI Search o staging local
      ↓
guardar document_id, updated_at y content_hash
```

### Reglas de ingestión

- No duplicar documentos con el mismo `document_id` y `content_hash`.
- No indexar documentos con `status=deleted`.
- Reportar documentos sin contenido extraíble.
- Conservar la URL original.
- Adjuntar producto, versión y release a cada fragmento.
- Registrar la fecha de última sincronización.
- Generar un reporte de éxitos, omisiones y errores.

## 20. Pruebas requeridas

### Unitarias

- validación de filtros;
- validación de paginación;
- normalización de fechas;
- normalización de tipos;
- generación de hash;
- mapeo de estados;
- documento sin versión;
- contenido vacío;
- errores estructurados.

### De contrato

- `list_documents` devuelve la estructura acordada;
- `next_cursor` continúa sin duplicar elementos;
- `get_document_metadata` conserva el mismo `document_id`;
- `get_document_content` devuelve texto UTF-8;
- un documento inexistente devuelve `NOT_FOUND`;
- un documento no autorizado devuelve `FORBIDDEN`;
- los campos ausentes se devuelven como `null`.

### De formatos

- [ ] Markdown.
- [ ] TXT.
- [ ] PDF con texto.
- [ ] PowerPoint con texto.
- [ ] Archivo no soportado.
- [ ] Archivo corrupto.
- [ ] Documento vacío.
- [ ] Documento que excede el límite.

### De seguridad

- [ ] Sin autenticación.
- [ ] Usuario sin permiso.
- [ ] Documento inexistente.
- [ ] Intento de modificación o eliminación.
- [ ] Verificación de que no se imprimen secretos.
- [ ] Verificación de que los errores no muestran stack traces.
- [ ] Verificación de límites de tamaño.

### De integración

- [ ] El cliente lista documentos reales.
- [ ] El cliente obtiene metadatos reales.
- [ ] El cliente obtiene contenido real.
- [ ] Un documento llega al staging local.
- [ ] Un documento llega a Azure AI Search si el servicio está disponible.
- [ ] El bot muestra la fuente original.
- [ ] Una falla del MCP activa el fallback esperado.

## 21. Datos de prueba mínimos

El ambiente de prueba debe incluir:

1. un README;
2. un changelog;
3. un hotfix;
4. un documento de setup;
5. una presentación o documento equivalente;
6. un documento archivado;
7. un documento cuyo contenido no pueda extraerse;
8. un caso sin permiso, si la aplicación soporta permisos diferenciados.

Cada documento debe tener una respuesta esperada y una URL o ubicación verificable.

## 22. Criterios de aceptación

El MCP está listo para el MVP cuando:

- [ ] Existe un servidor o endpoint accesible desde el ambiente de prueba.
- [ ] La autenticación está documentada.
- [ ] El acceso es de solo lectura.
- [ ] `list_documents` funciona con paginación.
- [ ] Los filtros básicos funcionan o están documentados como limitación.
- [ ] `get_document_metadata` devuelve campos consistentes.
- [ ] `get_document_content` devuelve texto para los formatos P0.
- [ ] Cada documento tiene un identificador estable.
- [ ] Cada documento tiene URL o ubicación original cuando existe.
- [ ] Se devuelve producto, versión, release y fecha cuando la fuente los conoce.
- [ ] Se devuelve hash o mecanismo equivalente para detectar cambios.
- [ ] Los errores tienen códigos controlados.
- [ ] No se exponen secretos en respuestas ni logs.
- [ ] Se probaron documentos reales.
- [ ] El bot puede transformar la respuesta a evidencia trazable.
- [ ] El equipo puede repetir la prueba siguiendo instrucciones escritas.

## 23. Entregables esperados

La persona que implemente el MCP debe entregar:

1. código del servidor MCP;
2. configuración del ambiente de desarrollo;
3. documentación de instalación y ejecución;
4. definición de las herramientas expuestas;
5. ejemplos de llamadas y respuestas;
6. pruebas automatizadas;
7. lista de formatos soportados;
8. lista de filtros soportados;
9. lista de errores conocidos;
10. identidad de prueba o procedimiento para solicitarla;
11. al menos tres documentos reales para validar;
12. instrucciones para que el bot lo consuma desde local y dev.

## 24. Información que debe confirmar el responsable

Antes de implementar, confirmar:

- ¿Dónde se almacenan físicamente los documentos?
- ¿La aplicación expone una API o endpoint de descarga?
- ¿Los documentos tienen identificadores estables?
- ¿Existe metadata de producto, versión y release?
- ¿Qué formatos se utilizan realmente?
- ¿Hay permisos diferentes por usuario?
- ¿Cuál será la identidad de lectura del MCP?
- ¿Existe un ambiente de prueba?
- ¿Qué límites de consultas tiene la aplicación?
- ¿Qué documentos deben estar disponibles para la presentación?
- ¿Se necesita acceso a documentos archivados?
- ¿Cómo se detectará que un documento fue actualizado o eliminado?

## 25. Prompt sugerido para Codex

El responsable puede utilizar este prompt:

> Implementa un MCP de solo lectura para DownloadAseinfo.net siguiendo `docs/requerimientos-mcp-downloadaseinfo-mvp.md`.
>
> Primero inspecciona la aplicación existente y determina si existe una API, endpoint de descarga o acceso interno más estable que hacer scraping de la interfaz web. No modifiques documentos de origen.
>
> Implementa inicialmente `list_documents`, `get_document_metadata` y `get_document_content`. Mantén los nombres de campos y códigos de error definidos en el documento. Agrega paginación, filtros básicos, identificadores estables, fechas ISO-8601, hash de contenido y errores seguros.
>
> Prioriza Markdown, TXT, PDF con texto y PowerPoint con texto. Para formatos no soportados, devuelve `UNSUPPORTED_FORMAT` o una URL de descarga segura. No implementes búsqueda vectorial ni generación de respuestas; Azure AI Search y Chat-Salvador se encargan de esas responsabilidades.
>
> Agrega pruebas unitarias, pruebas de contrato y una prueba de integración con documentos reales o fixtures representativos. Documenta cómo ejecutar el MCP localmente, cómo configurar autenticación y cómo probar cada herramienta.
>
> Antes de finalizar, verifica que el MCP no pueda modificar ni eliminar documentos, que no exponga secretos y que todos los errores tengan códigos controlados.

## 26. Definición de terminado

El trabajo no se considera terminado solo porque el servidor MCP inicie. Debe cumplirse lo siguiente:

1. el servidor inicia en el ambiente acordado;
2. el cliente puede descubrir las herramientas;
3. se puede listar un conjunto real de documentos;
4. se puede obtener metadata de un documento;
5. se puede obtener contenido de un documento soportado;
6. el bot puede utilizar la respuesta como evidencia;
7. una persona puede abrir la fuente original;
8. los errores de permisos y disponibilidad son distinguibles;
9. existen pruebas reproducibles;
10. existe documentación suficiente para mantener el MCP.

## 27. Resumen para compartir

El requerimiento no es construir un bot que navegue la web como un usuario. El requerimiento es exponer mediante MCP una interfaz segura y de solo lectura para descubrir documentos de DownloadAseinfo.net, recuperar sus metadatos y obtener su contenido. La primera versión debe ser pequeña, estable y orientada a alimentar el MVP de Chat-Salvador. La búsqueda vectorial, la generación de respuestas y la sincronización automática se resolverán en componentes posteriores.
