# Plan de evolución: índice documental incremental

## Propósito

Llevar el proceso documental de Chat-Salvador desde la carga actual, apropiada para un piloto pequeño, a una operación productiva que procese solamente documentos nuevos, modificados o retirados.

## Estado actual

1. Una persona inicia sesión con su cuenta de Microsoft 365.
2. El proceso descarga los PDF accesibles desde SharePoint hacia `data/sharepoint/` en la computadora que ejecuta la sincronización.
3. El proceso de ingesta lee esa carpeta y carga los fragmentos y metadatos en Azure AI Search.
4. El bot consulta Azure AI Search. SharePoint conserva los PDF originales.

La carga reemplaza los fragmentos ya existentes para las fuentes que procesa, pero la sincronización local vuelve a recorrer los PDF y no limpia por sí sola las copias de archivos eliminados o renombrados.

## Visión objetivo

```text
SharePoint (fuente oficial y editable)
        |
        | sincronización automática con identidad técnica de solo lectura
        v
Azure Blob Storage privado (bodega técnica / respaldo controlado)
        |
        | detectar altas, cambios y eliminaciones
        v
Azure AI Search (índice de texto, fragmentos y metadatos)
        |
        v
Bot de Teams (consultas de usuarios autorizados)
```

SharePoint será la única fuente oficial que las personas editarán. Blob Storage será una copia técnica controlada, no una segunda biblioteca de trabajo. Azure AI Search será el índice de consulta, no el repositorio de los PDF originales.

## Comportamiento incremental esperado

| Evento en SharePoint | Acción esperada |
|---|---|
| PDF nuevo | Copiarlo a la bodega técnica e indexar solo ese PDF. |
| PDF modificado | Reemplazar la copia técnica y eliminar/recrear solo sus fragmentos en el índice. |
| PDF sin cambios | No descargarlo ni reprocesarlo. |
| PDF eliminado | Eliminar la copia técnica conforme a la política de retención y quitar sus fragmentos de Azure AI Search. |
| Reconstrucción del índice | Volver a generar Azure AI Search desde la bodega técnica, sin depender de una computadora personal. |

## Fases propuestas

### Fase 1: piloto estable

- Mantener SharePoint como fuente de los PDF aprobados.
- Usar Azure AI Search como índice central.
- Ejecutar la carga manualmente con una carpeta de staging controlada.
- Registrar el origen, fecha de modificación e identificador de cada documento.
- Definir un límite de almacenamiento y una limpieza de `data/sharepoint/` después de una carga confirmada.

### Fase 2: identidad y almacenamiento corporativos

- Reemplazar el inicio de sesión personal por una identidad técnica de Microsoft Entra ID.
- Dar a esa identidad permiso de solo lectura sobre el sitio o biblioteca autorizada de SharePoint.
- Crear un contenedor privado de Azure Blob Storage para la bodega técnica.
- Mover las claves a Key Vault y usar identidades administradas para los servicios de Azure.

### Fase 3: sincronización incremental

- Guardar por documento: identificador estable de SharePoint, ruta, fecha de modificación, tamaño y hash de contenido.
- Comparar el inventario de SharePoint con el inventario de la bodega técnica en cada ejecución programada.
- Transferir e indexar únicamente altas y cambios.
- Detectar bajas y eliminar sus fragmentos del índice.
- Registrar el resultado de cada ejecución: documentos revisados, creados, actualizados, eliminados y fallidos.

### Fase 4: operación productiva

- Programar la sincronización con la frecuencia acordada (por ejemplo, cada hora o diariamente).
- Crear alertas cuando falle la sincronización, cambie demasiado contenido o el índice quede desactualizado.
- Aplicar retención y versionado en Blob Storage según la política de la empresa.
- Validar permisos: el bot no debe devolver contenido que el usuario no puede consultar según la política definida para la biblioteca.

## Criterios de aceptación para la fase incremental

- Agregar un PDF no debe reprocesar los PDF sin cambios.
- Modificar un PDF debe actualizar únicamente sus fragmentos.
- Eliminar un PDF debe retirar sus fragmentos del índice en la siguiente sincronización.
- El índice debe poder reconstruirse desde Blob Storage sin una computadora o cuenta personal.
- La sincronización debe funcionar con identidad técnica, permisos mínimos y sin secretos en código o archivos locales.
- Cada ejecución debe dejar trazabilidad suficiente para saber qué cambió y qué falló.

## Decisión pendiente antes de implementarlo

Definir junto con TI/Seguridad si Blob Storage será solo staging con limpieza automática o una copia técnica con retención/versionado. En ambos casos, SharePoint sigue siendo la fuente oficial.
