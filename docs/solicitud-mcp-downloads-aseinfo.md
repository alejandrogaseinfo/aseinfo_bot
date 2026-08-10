# Plan para crear el MCP de `downloads.aseinfo.net`

> Documento para la persona responsable de `downloads.aseinfo.net`. Define el
> contrato mínimo que Libras necesita para consultar instaladores y releases.
> El MCP debe ser de solo lectura y no debe depender de leer el HTML del sitio.

## 1. Objetivo

Crear un MCP que permita a Libras consultar el catálogo de descargas por
producto y versión, obtener los artefactos publicados y devolver enlaces
oficiales para que el usuario decida qué descargar.

El MCP complementará las fuentes de Libras:

```text
SharePoint / Azure AI Search -> manuales y documentación formal
downloads.aseinfo.net       -> releases, instaladores, hotfixes y README
ClickUp                     -> tareas y cambios operativos (fase posterior)
Jira                        -> errores y soluciones (fase posterior)
GitHub                      -> cambios técnicos (fase posterior)
```

El MCP no debe subir, modificar, eliminar, instalar ni descargar archivos en
el servidor de Libras.

## 2. Lo que se observó en el sitio

En la página principal se observan productos y familias como:

- Evolution 1.24.x.
- Evolution 1.19.x.
- Portal Público para Candidatos Externos.
- Evolution Wave: Portal, Onboarding, Analítica y Gestión de Talento.
- Connect, Identity Server, Queue Manager, Scheduler, Nexus DB, Nexus IA y
  E.V.A.
- Versiones estándar por país.

Las páginas de producto muestran, por cada versión:

- número de versión;
- descripción de cambios;
- estado, por ejemplo `Estable`;
- artefactos publicados;
- nombre y tamaño de cada archivo;
- dependencias;
- fecha de publicación;
- fecha de lanzamiento;
- README y, en algunas versiones, Release Notes.

Ejemplos visibles durante la revisión:

- `Evolution 1.19.1.13`: hotfix, hotfix acumulativo, README y sin
  dependencias.
- `Evolution 1.24.2.0`: bundles con QueueManager, release, archivo adicional,
  README y Release Notes.
- `Evolution 1.19.1.0`: aparece un archivo llamado `Release 1.19.1.15.zip`,
  aunque la tarjeta corresponde a `1.19.1.0`. Esto demuestra que el MCP debe
  detectar inconsistencias y no recomendar archivos únicamente por el nombre.

El sitio muestra información de catálogo a un usuario con rol `Viewer`, pero
los accesos a descargas están protegidos. El MCP debe respetar esa diferencia:
una cosa es consultar metadatos y otra obtener un enlace autorizado.

## 3. Decisión funcional principal

El MCP no debe exponer solamente una función llamada
`obtener_instalador_recomendado`, porque una versión puede tener distintos
escenarios:

1. instalación nueva;
2. actualización desde una versión anterior;
3. aplicación de un hotfix;
4. instalación de un bundle con dependencias.

La herramienta debe recibir el escenario o devolver varias opciones claramente
etiquetadas. La recomendación solo puede provenir de una regla explícita del
sitio o del responsable del producto.

Si el sitio no marca un archivo como recomendado, Libras debe decirlo y mostrar
las opciones, no elegir arbitrariamente.

## 4. Herramientas MCP requeridas

Los nombres son sugeridos; pueden cambiar según el SDK. Las capacidades sí son
necesarias.

### `list_products`

Lista productos y sus identificadores estables.

Entrada:

```json
{}
```

Debe devolver nombre, código, estado y URL oficial del producto.

### `list_versions`

Lista versiones de un producto, con filtros opcionales por estado y tipo.

Entrada:

```json
{
  "product": "Evolution",
  "status": "published"
}
```

Debe devolver la versión exacta, descripción, tipo de release, estado y fechas.

### `get_release`

Obtiene el detalle de una versión exacta.

Entrada:

```json
{
  "product": "Evolution",
  "version": "1.19.1.13"
}
```

Debe devolver la tarjeta completa de la versión, sus dependencias y todos sus
artefactos.

### `list_artifacts`

Lista los artefactos de una versión.

Entrada:

```json
{
  "product": "Evolution",
  "version": "1.19.1.13",
  "artifact_type": "all"
}
```

Debe distinguir, como mínimo:

- `release`;
- `installer`;
- `hotfix`;
- `cumulative_hotfix`;
- `bundle`;
- `patch`;
- `readme`;
- `release_notes`;
- `additional`;
- `documentation`.

### `get_installation_options`

Devuelve opciones según el escenario de instalación.

Entrada:

```json
{
  "product": "Evolution",
  "version": "1.19.1.13",
  "scenario": "update"
}
```

Los escenarios mínimos son `new_installation`, `update` y `hotfix`.

Cada opción debe incluir:

- artefacto recomendado, si existe;
- motivo de la recomendación;
- versión base requerida;
- dependencias;
- advertencias;
- enlace oficial.

Si no existe una regla oficial, debe devolver `recommendation_status:
"not_defined"`.

### `get_readme`

Obtiene el contenido permitido del README o su enlace oficial.

Entrada:

```json
{
  "product": "Evolution",
  "version": "1.19.1.13"
}
```

Debe indicar si devuelve contenido, solo metadatos o únicamente un enlace por
restricciones de permisos.

### `list_related_artifacts`

Lista archivos relacionados: notas de versión, parches adicionales, bundles,
acumulativos y dependencias.

Entrada:

```json
{
  "product": "Evolution",
  "version": "1.24.2.0"
}
```

## 5. Contrato de respuesta

Todas las herramientas deben devolver JSON estable. Ejemplo:

```json
{
  "found": true,
  "source": {
    "system": "downloads.aseinfo.net",
    "product_url": "https://downloads.aseinfo.net/producto/evolution-v119",
    "retrieved_at": "2026-08-10T12:00:00Z"
  },
  "product": {
    "id": "evolution-v119",
    "name": "Evolution 1.19.x."
  },
  "release": {
    "id": "stable-1.19.1.13",
    "version": "1.19.1.13",
    "status": "stable",
    "description": "Arreglo de bugs y mejora de rendimiento",
    "published_at": "2023-08-07",
    "released_at": "2023-08-07",
    "dependencies": []
  },
  "artifacts": [
    {
      "id": "artifact-1",
      "name": "Hotfix 1.19.1.13.zip",
      "type": "hotfix",
      "size_bytes": 90194313,
      "download_url": "https://downloads.aseinfo.net/...",
      "status": "published"
    },
    {
      "id": "artifact-2",
      "name": "Hotfix 1.19.1.13 Acumulativo.zip",
      "type": "cumulative_hotfix",
      "size_bytes": 323699712,
      "download_url": "https://downloads.aseinfo.net/...",
      "status": "published"
    },
    {
      "id": "artifact-3",
      "name": "Readme 1.19.1.13.pdf",
      "type": "readme",
      "download_url": "https://downloads.aseinfo.net/...",
      "status": "published"
    }
  ],
  "recommendation": {
    "status": "not_defined",
    "scenario": "update",
    "reason": "El sitio no marca un artefacto recomendado para este escenario."
  },
  "warnings": []
}
```

Los enlaces deben ser oficiales y, si requieren sesión, deben respetar la
autorización del usuario. Nunca se deben devolver tokens, cookies o credenciales
en esta respuesta.

## 6. Reglas de consistencia

El MCP debe validar antes de responder:

- que producto y versión coincidan exactamente;
- que el artefacto pertenezca realmente a la versión consultada;
- que el estado no sea `retired`, `draft` o equivalente;
- que las fechas y nombres sean los publicados por el sitio;
- que las dependencias se devuelvan como relaciones estructuradas;
- que los artefactos con nombres inconsistentes se marquen como advertencia;
- que una versión inexistente no produzca resultados de una versión vecina.

Debe distinguir entre:

```text
Release       -> instalación nueva, si la regla del sitio lo confirma
Hotfix        -> actualización puntual
Hotfix acumulativo -> incluye hotfixes anteriores indicados por el sitio
Bundle        -> paquete con uno o más componentes/dependencias
README        -> instrucciones y notas de instalación
Release Notes -> resumen de cambios
Adicional     -> corrección o archivo complementario
```

## 7. Ejemplos de respuestas que Libras podrá construir

### Pregunta sobre Evolution 1.19.1.13

```text
Para Evolution 1.19.1.13 encontré una versión estable publicada el
07/08/2023. El sitio muestra un hotfix, un hotfix acumulativo y el README.

El sitio no marca cuál debe usarse como instalador recomendado. Para una
actualización, el MCP debe confirmar con la regla de instalación si corresponde
el hotfix puntual o el acumulativo. Documentación: [README].
```

Si el responsable del sitio define una regla oficial, Libras podrá sustituir
la advertencia por:

```text
Para actualizar a Evolution 1.19.1.13, utiliza [artefacto], porque la regla
publicada para el escenario update lo identifica como opción recomendada.
README: [enlace].
```

### Pregunta sobre una release con bundles

```text
Para Evolution 1.24.2.0 hay un release y tres bundles con distintas
combinaciones de QueueManager y soporte de IA/EVA. El MCP debe pedir o recibir
el escenario de instalación para recomendar uno; no debe elegir un bundle solo
por ser el archivo más grande o el más reciente.
```

### Pregunta sin resultado

```text
No encontré la versión solicitada en downloads.aseinfo.net. No usaré la
versión inmediatamente anterior ni la siguiente como sustituto.
```

### Inconsistencia de catálogo

```text
La tarjeta de Evolution 1.19.1.0 muestra un artefacto llamado
Release 1.19.1.15.zip. El catálogo tiene una inconsistencia y no puedo
recomendar ese archivo hasta que el administrador confirme la relación.
```

## 8. API o acceso que debe preparar el administrador

La implementación debe consultar una API oficial o una capa de servicio
estable. No se recomienda que el MCP lea el HTML o automatice botones del sitio.

El administrador debe entregar:

1. Documentación OpenAPI/Swagger o contrato equivalente.
2. URL de pruebas y URL de producción.
3. Identificadores estables de producto, release y artefacto.
4. Endpoints o consultas para productos, versiones, artefactos, README,
   dependencias y enlaces de descarga.
5. Paginación, filtros, ordenamiento y límites de frecuencia.
6. Códigos de error y comportamiento ante versiones inexistentes.
7. Política para archivos retirados y versiones preliminares.
8. Regla oficial para recomendar un artefacto por escenario.
9. Ejemplos reales de Evolution 1.19.1.13, Evolution 1.24.2.0 y un caso con
   inconsistencia corregida.

Si el sitio todavía no tiene API, el primer trabajo del administrador será
exponer una API de lectura desde la base de datos o servicio interno. No debe
exponerse directamente la base de datos al MCP.

## 9. Autenticación y permisos

La opción preferida para el backend de Libras es una identidad de aplicación o
API key de solo lectura, almacenada en Azure Key Vault. El MCP nunca debe
entregar el secreto al modelo.

El administrador debe definir si:

- el catálogo puede consultarse con una identidad de aplicación;
- los enlaces de descarga deben generarse por usuario;
- un usuario puede ver artefactos distintos de otro;
- los enlaces son públicos, temporales o requieren sesión;
- se necesita OAuth delegado para respetar permisos individuales.

Si el sitio limita archivos por usuario, el MCP debe devolver un enlace
autorizado para ese usuario o indicar que no tiene permiso. No debe compartir un
enlace de otra persona.

Permisos mínimos sugeridos:

```text
catalog.read
versions.read
artifacts.read
readme.read
download-link.create   (solo si el sitio genera enlaces autorizados)
```

No se necesitan permisos para crear, modificar o eliminar productos,
versiones o archivos.

## 10. Implementación del servidor MCP

El responsable debe entregar un servidor MCP con:

- transporte HTTP compatible con la plataforma donde se conectará Libras;
- herramientas descritas con entradas y salidas tipadas;
- validación estricta de producto, versión y escenario;
- timeouts y reintentos controlados;
- paginación y rate limiting;
- health check;
- logs sin tokens, cookies ni contenido privado;
- métricas de latencia, errores y uso por herramienta;
- versionado del contrato;
- ambiente de pruebas separado de producción.

El MCP debe devolver metadatos y enlaces, no binarios al modelo. Libras tampoco
debe ejecutar instalaciones ni descargar archivos automáticamente.

## 11. Pruebas de aceptación

El MCP se considera listo cuando pasa estas pruebas:

1. Lista productos y versiones con identificadores estables.
2. Consulta exactamente Evolution 1.19.1.13 sin mezclar 1.19.1.12 o 1.19.1.14.
3. Devuelve sus tres artefactos y sus tipos correctos.
4. Devuelve README, notas y dependencias cuando existan.
5. Explica que no existe recomendación si el sitio no la define.
6. Recomienda una opción solo cuando existe una regla explícita.
7. Distingue instalación nueva, actualización y hotfix.
8. Trata correctamente una versión con bundles como Evolution 1.24.2.0.
9. Detecta y reporta inconsistencias como la de `1.19.1.0`.
10. Devuelve respuesta controlada para producto o versión inexistente.
11. Respeta archivos retirados, permisos y enlaces temporales.
12. Maneja 401, 403, 404, 429 y errores 5xx sin exponer secretos.
13. No realiza operaciones de escritura ni descarga binarios.
14. Mantiene un contrato JSON estable para que Libras combine la fuente con
    SharePoint, ClickUp y Jira.

## 12. Entregables del administrador

- API o servicio de lectura documentado.
- Servidor MCP y código fuente.
- Contrato de herramientas y respuestas.
- Credenciales o mecanismo de autenticación de pruebas.
- Reglas de recomendación por escenario.
- Datos de prueba y casos de inconsistencia.
- Pruebas automatizadas.
- README de configuración y despliegue.
- Procedimiento de rotación de credenciales.
- Health check, métricas y soporte.
- Ambiente de pruebas y procedimiento de promoción a producción.

## 13. Orden recomendado de trabajo

1. Confirmar el modelo de datos real del sitio.
2. Corregir o documentar inconsistencias de catálogo.
3. Definir reglas de instalación nueva, actualización y hotfix.
4. Exponer la API de lectura.
5. Implementar y probar el MCP.
6. Validar autenticación y enlaces autorizados.
7. Integrarlo con Libras en staging.
8. Probar respuestas con SharePoint y, posteriormente, ClickUp/Jira.
9. Publicar después de revisar permisos, logs y seguridad.

La primera entrega no debe intentar resolver toda la correlación con ClickUp,
Jira y GitHub. Debe entregar datos exactos de `downloads.aseinfo.net` para que
Libras pueda combinarlos con esas fuentes en fases posteriores.
