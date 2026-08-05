# Catálogo de metadatos para el índice de Libras

> Estado: propuesta para revisión antes de reindexar producción. Este catálogo
> describe documentos y su procedencia; no contiene respuestas precargadas ni
> fragmentos documentales.

## Propósito

El índice actual mezcla manuales, código, hojas de cálculo y documentos de
procedimiento. El nombre técnico de un archivo suele ser insuficiente para que
una pregunta coloquial encuentre la fuente correcta. El catálogo agrega señales
de identificación documental, no contenido inventado.

## Campos por fragmento

| Campo | Origen | Requerido | Regla de calidad |
|---|---|---:|---|
| `document_id` | SharePoint | Sí | Estable y único por documento; nunca usar el título como clave. |
| `title_original` | SharePoint | Sí | Se conserva para la fuente que verá el usuario. |
| `title_terms` | Derivado del título | Sí | Separar puntos, guiones bajos, guiones y camel case; no sustituye el título original. |
| `product` | Carpeta, columnas de SharePoint o revisión | Cuando aplique | Valor controlado; no inferirlo solo porque aparezca una palabra en el texto. |
| `module` | Metadatos de origen o revisión | Cuando aplique | Valor controlado y auditable. |
| `operation` | Metadatos de origen o revisión | Para código/procedimientos | Describe la operación documentada, no una respuesta completa. |
| `artifact_role` | Regla por extensión + revisión | Sí | `manual`, `procedimiento`, `script`, `configuracion`, `reporte`, `plantilla` u otro valor controlado. |
| `version` | Título, contenido o metadato | Cuando exista | Comparar como versión exacta, no por prefijo. |
| `country` | Fuente aprobada o contenido validado | Cuando aplique | No usar países mencionados solo en pies de página o contactos. |
| `source_system`, `drive_id`, `folder_path` | SharePoint | Sí | El `drive_id` delimita la procedencia; `folder_path` vacío puede significar raíz. |
| `quality_status` | Revisión de calidad | Sí | `pendiente`, `aprobado`, `obsoleto`, `duplicado` o `fuera_de_alcance`. |

## Reglas para no introducir ruido

1. La extracción automática solo puede separar el título, detectar extensión,
   leer metadatos de SharePoint y calcular hash. No puede declarar qué significa
   un procedimiento sin una fuente o revisión aprobada.
2. Las etiquetas funcionales deben tener responsable, fecha de revisión y
   evidencia de origen. Un alias como `vac` → `vacaciones` requiere aprobación
   del dueño del dominio; no se agrega por conveniencia del buscador.
3. Los documentos `obsoleto`, `duplicado` y `fuera_de_alcance` permanecen en un
   inventario reversible, pero no se ofrecen como evidencia de respuesta.
4. Los scripts y SQL no se descartan por extensión. Se recuperan cuando su
   operación y producto estén identificados; de lo contrario se mantienen en
   estado `pendiente` y no se usan para afirmar una solución.
5. Los campos se propagan a todos los fragmentos del documento para que una
   página posterior no pierda producto, módulo, versión o país.

## Cola inicial de revisión

Estos elementos no son respuestas precargadas; son candidatos para confirmar
con el dueño de la documentación:

| Documento | Motivo de revisión | Resultado requerido |
|---|---|---|
| `acc.proc_arreglar_vac_negativos.sql` | El nombre sugiere una operación funcional, pero la pregunta natural no recupera el archivo actual. | Confirmar producto, módulo, operación, versión y alcance antes de etiquetar. |
| `Reportes (64).sql` | Concentra 784 fragmentos y puede dominar el ranking. | Confirmar si es una fuente de consulta, un respaldo histórico o un artefacto que debe dividirse. |
| `Horas extras XIII con inserts.xlsx` | Concentra 667 fragmentos. | Confirmar si cada hoja es una unidad documental y si el archivo está vigente. |
| Los 15 grupos de hash duplicado | Repiten contenido exacto entre documentos. | Elegir una copia canónica y conservar las demás como referencias históricas. |

## Criterio para reindexar

La reindexación candidata solo se autoriza cuando los campos funcionales de la
cola inicial estén revisados, el corpus de recuperación tenga casos positivos y
negativos, y exista un índice paralelo o una reversión verificable. La salida se
compara contra el inventario actual y contra el corpus en
`tests/corpus-recuperacion-calidad.json`.
