# Clasificación de documentos de revisión — 2026-08-04

Se revisaron los 65 archivos de
`tmp/sharepoint-scope-review-20260804-v2` usando biblioteca, nombre, formato y
texto extraíble. Ningún archivo fue borrado ni incorporado al índice general.
El detalle por archivo está en
`output/clasificacion-review-20260804.json`.

## Resultado

| Clasificación | Cantidad | Decisión |
|---|---:|---|
| `LEGAL_REVIEW` | 12 | Fuera del índice general hasta confirmar país, vigencia, fuente y responsable. |
| `CUSTOMER_RESTRICTED` | 19 | Fuera del índice general; requiere índice/permisos separados o exclusión. |
| `APPROVED_TECHNICAL` | 9 | Pasaron la revisión inicial y se copiaron al staging `core-v3`. |
| `GENERAL_PROCESS_REVIEW` | 16 | Procesos de soporte; validar alcance y sensibilidad antes de promoverlos. |
| `GENERAL_TEMPLATE_REVIEW` | 7 | Plantillas potencialmente reutilizables; comprobar que no contengan datos reales. |
| `GENERAL_SUPPORT_REVIEW` | 1 | Manual del Portal de AutoServicio; revisar tratamiento de usuarios, claves, correos y enlaces. |
| `SECURITY_REVIEW` | 1 | Instalación de GenPlaAPI; confirmar que los campos de usuario/contraseña sean ejemplos y no secretos. |

## Decisiones relevantes

- Los 12 documentos legales incluyen cálculos de renta y nómina de varios
  países, además de enlaces de legislación. No se deben presentar como
  legislación vigente sin país y fecha verificados.
- Los 19 documentos restringidos incluyen materiales de Davivienda, FUNDEA,
  GIZ, Dollarcity, TIGO PA, Banco Hipotecario, POLYTEC y Textiles Lourdes,
  además de inventarios de clientes, doble autenticación y automatizaciones
  sobre carpetas de clientes.
- Los 9 candidatos técnicos aprobados incluyen SQL genérico, restauración de
  base de datos y algoritmos. Se copiaron al `core-v3`, pero aún no se cargaron
  en Azure.
- GenPlaAPI y el manual del Portal de AutoServicio permanecen fuera del núcleo
  por sus configuraciones, usuarios, claves, correos y enlaces.
- Los procesos y plantillas de soporte podrían ser útiles para el equipo, pero
  no son automáticamente conocimiento técnico público de Libras.

## Siguiente acción

El índice general conserva el alcance `core-v3`, que ahora tiene 284 documentos
con texto y 2,665 fragmentos. La próxima promoción controlada debe usar este
staging, sin incorporar la colección especializada ni los 56 documentos que
continúan en revisión.
