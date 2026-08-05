# Recomendación de alcance documental para Libras

Fecha de análisis: 2026-08-04
Fuente: configuración de producción, Microsoft Graph en modo lectura y
navegación autenticada del sitio `Soportealcliente`.

## Conclusión

No conviene indexar todo el sitio. La mejor configuración para el bot general
es conservar el núcleo técnico de Evolution y separar o excluir el contenido
de clientes, hojas operativas, datos de sistema y archivos binarios. La
selección debe hacerse por biblioteca y carpeta, pero también por documento y
tipo; excluir una biblioteca completa ocultaría información útil.

## Bibliotecas observadas

El sitio expone estas bibliotecas a la identidad usada por la auditoría:

| Biblioteca | Estado en Libras | Alcance actual | Hallazgo |
|---|---|---|---|
| ReadME Hotfixes | Usar | Raíz | 43 archivos legibles, principalmente PDF; esencial para respuestas por versión. |
| Documentos | Usar con límite | Solo `SOLUCIONES` | La raíz contiene carpetas de clientes, tickets y operaciones que no deben entrar al índice general. |
| Legislaciones | Usar con revisión | Raíz | 9 archivos legibles; contiene renta/nómina de varios países, pero no una base completa de legislación salvadoreña. |
| Traslados OP/DE | Usar con revisión | Raíz | 5 DOCX de procesos operativos. |
| Parches Adicionales | Mantener fuera por ahora | Raíz | Sin archivos legibles en la última consulta. |
| Documentos de Apoyo | Usar de forma selectiva | Raíz | Mezcla manuales generales, plantillas y documentos de clientes. |
| Manuales | Usar | Raíz | 20 PDF; alta relevancia técnica, pero requiere ranking por producto/versión. |
| Scripts de Apoyo | Usar | Raíz | 22 SQL; poco volumen y alto valor para preguntas de procedimientos/scripts. |
| Hojas de Servicio | Excluir del índice general | No configurada | Tiene al menos 116 carpetas fechadas; es un repositorio operativo de alto volumen y posible información de clientes. |
| Teams Wiki Data | Excluir | No configurada | Datos de sistema de Teams. |
| Páginas del sitio | Excluir inicialmente | No es biblioteca sincronizada | Contenido de navegación/páginas; requiere curación explícita antes de indexarse. |

## Prioridad dentro de `Documentos/SOLUCIONES`

La consulta estructural de la raíz mostró estas carpetas y volúmenes:

| Carpeta | Archivos totales | Archivos con formato legible | Decisión |
|---|---:|---:|---|
| `EVOLUTION` | 129 | 104 | Mantener; es el núcleo técnico. Excluir binarios, instaladores y multimedia. |
| `SQL` | 73 | 71 | Mantener, pero clasificar por producto/operación y evitar que domine el ranking. |
| `1.24` | 18 | 4 | Mantener solo archivos de versión/documentación; no indexar ZIP como texto. |
| `VHUR` | 17 | 10 | Mantener si VHUR forma parte del alcance de soporte; separar por producto. |
| `Conjuntos de Datos` | 3 | 3 | Revisar dueño y sensibilidad antes de incluir. |
| `IDS` | 2 | 2 | Mantener si son procedimientos técnicos aprobados. |
| `Archivos de Banco` | 2 | 2 | Revisar; puede contener información específica de clientes/bancos. |
| `LEGISLACIÓN LABORAL` | 1 | 0 | No aporta actualmente: el archivo es RAR y no se extrae texto. |
| `EvoWave` | 1 | 1 | Mantener si el producto sigue dentro del alcance. |
| `VARIOS` | 2 | 2 | Revisar manualmente antes de incluir. |

Los tres documentos que más espacio y candidatos consumen son `Reportes (64).sql`
(784 fragmentos), `Horas extras XIII con inserts.xlsx` (667) y `03 - Query para
copiar consulta Excel.sql` (284). Juntos representan aproximadamente 38% de
los fragmentos productivos. Deben pasar a una colección técnica especializada
o recibir límites de fragmentación; no deben eliminarse automáticamente sin
confirmar su valor.

## Documentos de Apoyo: separación necesaria

La biblioteca mezcla contenido general con material de clientes. Deben
separarse antes de ampliar el índice general:

- Mantener bajo revisión: `Automatizaciones`, `Capacitaciones Evolution`,
  `Inventario de Documentos y Formatos` y `Manuales Internos`.
- Separar o excluir del índice general: carpetas y archivos identificados con
  clientes como `Banco Hipotecario`, `Cityparking`, `Dollarcity`, `GIZ` y
  `TIGO PA`, además de plantillas que contengan campos o procesos específicos
  de clientes.
- No indexar ZIP, PPTX, imágenes, video o ejecutables hasta disponer de un
  extractor y una decisión de sensibilidad.

## Legislaciones y preguntas de El Salvador

La biblioteca `Legislaciones` contiene `Calculadora Renta El Salvador.xlsx`,
archivos de renta de Costa Rica/Guatemala/Nicaragua/Panamá, archivos de nómina
de Honduras/Nicaragua/Panamá y presentaciones de legislación regional. No se
observó allí una fuente específica de descuentos legales o fecha de aguinaldo
para El Salvador. Por eso esas respuestas deben continuar en `sin evidencia`
hasta que exista una fuente autorizada y vigente; no es correcto “arreglar” el
resultado solo cambiando el ranking.

## Recomendación de implementación

1. Crear una clasificación de colección: `GENERAL_SUPPORT`,
   `TECHNICAL_CODE`, `LEGAL_REVIEW` y `CUSTOMER_RESTRICTED`.
2. Indexar en el bot general solo `GENERAL_SUPPORT`, `TECHNICAL_CODE` aprobado y
   `LEGAL_REVIEW` con país/vigencia explícitos.
3. Mantener `CUSTOMER_RESTRICTED` fuera del índice común o en un índice con
   permisos separados; no confiar únicamente en el prompt para protegerlo.
4. Propagar biblioteca, carpeta, producto, versión, país, operación y estado de
   revisión como metadatos filtrables.
5. Medir el corpus de preguntas después de cada cambio. La primera prueba de
   selección debe comparar: núcleo actual, núcleo sin los tres documentos
   dominantes y núcleo con `Documentos de Apoyo` depurado.

Esta selección reduce ruido y consumo sin perder de entrada las fuentes que
responden las preguntas técnicas observadas. La carga completa debe ejecutarse
en un servicio de QA con capacidad suficiente; el servicio Free actual no es
adecuado para mantener producción y un candidato grande simultáneamente.

## Decisión adoptada para la siguiente evaluación

Se materializó la selección en staging, sin borrar archivos de SharePoint:

- `tmp/sharepoint-scope-core-20260804-v2`: 282 archivos fuente; 275 documentos
  con texto y 2,652 fragmentos después de extracción. Es el único alcance
  destinado al índice general.
- `tmp/sharepoint-scope-specialized-20260804-v2`: exactamente los tres
  documentos dominantes (1,735 fragmentos) para una futura colección técnica.
- `tmp/sharepoint-scope-review-20260804-v2`: 65 archivos de Legislaciones,
  Traslados OP/DE y Documentos de Apoyo, pendientes de revisión de sensibilidad
  y vigencia.

La primera evaluación léxica local sobre `core` ya recupera `Gestion de
documentos.pdf` para las consultas de administración de documentos. El caso de
vacaciones negativas todavía necesita un alias funcional aprobado para asociar
“vacaciones negativas” con el procedimiento `vac_get...`; no se resolverá
añadiendo una respuesta fija.
