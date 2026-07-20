# Estado actual de Chat-Salvador

## Propósito

Este documento resume el punto de partida técnico para revisar el MVP. El alcance, el roadmap y los criterios de aceptación están únicamente en [plan-mvp-presentacion-lunes.md](plan-mvp-presentacion-lunes.md).

## Lo que ya existe

- Bot funcional en Microsoft Teams / Microsoft 365 Agents Playground.
- Host HTTP en Python.
- Arquitectura modular para recibir, recuperar, clasificar y formatear consultas.
- Índice local de documentos Markdown.
- Clasificación en `resuelto`, `en_progreso`, `similar_del_pasado` y `sin_evidencia`.
- Fallback local cuando falla la clasificación con OpenAI.
- Respuesta visible con estado, confianza, resumen, ruta de investigación, evidencia, siguiente acción y escalamiento.
- Integración opcional de lectura con ClickUp y Jira en el código actual.
- Scripts para incorporar documentos de setups y READMEs locales al staging documental.

## Lo que todavía debe construirse para el MVP de presentación

- Contrato común de evidencia con fuente, versión, fecha, enlace y estado.
- Proveedor de evidencia para Azure AI Search y el MCP de DownloadAseinfo.net.
- Un conector operativo opcional para Jira o ClickUp.
- GitHub y SharePoint como extensiones posteriores, no como requisito de la primera demo.
- Selección simple de fuente para no consultar todas las fuentes en cada pregunta.
- Lote de documentación real proveniente de releases, readmes, hotfixes y changelogs.
- Validación de casos activos en ClickUp/Jira y antecedentes históricos.
- Corrección de reglas de confianza que puedan confundir una mención de hotfix con una solución confirmada.
- Evaluación reproducible con preguntas reales del equipo.

## Decisión de continuidad

La base actual se conserva. No se rehace la integración con Teams ni el flujo principal. Se refactoriza la capa de recuperación para incorporar un proveedor de evidencia sencillo: Azure AI Search para la documentación del MVP y el índice local como fallback. DownloadAseinfo.net será la fuente documental prioritaria; Jira o ClickUp se agregan si el acceso está listo.

## Evidencia disponible

La base local se encuentra en [knowledge-base](knowledge-base). Los documentos actuales sirven para validación técnica; deben complementarse con documentos reales de DownloadAseinfo.net antes de considerar el MVP representativo del conocimiento operativo.
