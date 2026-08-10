# Guía breve de Azure para Libras

Esta guía explica cómo se ejecuta Libras en Azure. Está pensada para entender
la arquitectura y revisar el entorno; no contiene secretos ni sustituye los
permisos del administrador.

## Los dos flujos

### Consulta desde Teams

```text
Microsoft Teams
    -> Azure Bot: bot-libras-prod
    -> App Service: app-libras-prod
    -> Libras valida y clasifica la consulta
    -> Azure AI Search: srch-libras-prod / índice libras-docs
    -> OpenAI genera o clasifica la respuesta
    -> Teams recibe la respuesta con la fuente
```

### Ingesta documental

```text
SharePoint autorizado
    -> proceso de ingesta: libras-sharepoint-ingestion-prod
    -> extracción y fragmentación de documentos
    -> Azure AI Search / libras-docs
```

La aplicación que responde consultas no lee documentos directamente desde
SharePoint durante cada mensaje. La ingesta actualiza el índice por separado.

## Recursos principales

| Recurso | Función |
| --- | --- |
| `app-libras-prod` | Ejecuta el backend Python de Libras en Azure App Service. |
| `bot-libras-prod` | Conecta Microsoft Teams con el App Service. |
| `srch-libras-prod` | Recurso de Azure AI Search. |
| `libras-docs` | Índice donde se almacenan fragmentos, enlaces y metadatos documentales. |
| `libras-sharepoint-ingestion-prod` | Identidad/proceso separado que lee SharePoint y actualiza Search. |
| `kv-libras-prod` | Azure Key Vault para secretos y referencias de configuración. |
| `rg-libras-prod` | Resource Group de los recursos productivos. |

## Identidades y permisos

Hay dos responsabilidades distintas:

- El App Service necesita leer `libras-docs`, normalmente con el rol `Search
  Index Data Reader`.
- La ingesta necesita leer el sitio SharePoint autorizado y escribir en Search,
  normalmente con `Sites.Selected` + `read` sobre el sitio y `Search Index Data
  Contributor` sobre `srch-libras-prod`.

La ingesta no debe usar la identidad ni los permisos del App Service para
escribir documentos. Se mantiene el principio de mínimo privilegio.

## Configuración que conecta el código con Azure

En producción, las variables llegan desde App Service y Key Vault. Las más
importantes para entender el flujo son:

```text
LIBRAS_ENV=production
REQUIRE_AZURE_SEARCH=true
AZURE_SEARCH_ENDPOINT=https://srch-libras-prod.search.windows.net
AZURE_SEARCH_INDEX_NAME=libras-docs
AZURE_SEARCH_USE_ENTRA_ID=true
OPENAI_MODEL=...
OPENAI_INTENT_MODEL=...
```

`OPENAI_API_KEY` y cualquier secreto de SharePoint no deben copiarse a Git,
documentos, tickets ni logs. En local se usa `.env`, que está excluido del
repositorio.

## Cómo revisar el entorno

Orden recomendado:

1. Revisar `app-libras-prod` y confirmar que el App Service está ejecutándose.
2. Consultar `/healthz` para comprobar que el proceso responde.
3. Consultar `/readyz` para comprobar que tiene sus dependencias requeridas.
4. Revisar la configuración de Azure AI Search y que exista `libras-docs`.
5. Confirmar que la identidad del App Service tenga solamente lectura sobre el
   índice.
6. Revisar por separado el proceso de ingesta y su identidad.
7. Confirmar en Key Vault que las referencias existan sin revelar sus valores.
8. Probar una consulta real en Teams y verificar que el enlace de evidencia sea
   de una fuente SharePoint autorizada.

## Qué no debe hacerse

- No colocar claves, tokens, client secrets o connection strings en el repo.
- No asignar permisos globales de SharePoint o Search sin justificación.
- No usar `AZURE_SEARCH_API_KEY` si la identidad administrada/RBAC está
  configurada y aprobada para el entorno.
- No cambiar el índice productivo desde una prueba local sin respaldo y
  aprobación.
- No asumir que un documento presente en Search está autorizado: Libras valida
  también la procedencia y el alcance documental.

## Documentación relacionada

- [Arquitectura productiva](arquitectura-produccion.md)
- [Despliegue productivo](despliegue-produccion.md)
- [Azure AI Search y SharePoint](azure-ai-search-sharepoint.md)
- [Contexto actual](contexto-actual.md)
