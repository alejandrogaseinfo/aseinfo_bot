# AGENTS.md

## Proyecto

`Chat-Salvador` es un bot de autoservicio para Microsoft Teams orientado a soporte y operaciones. Su objetivo es consultar conocimiento técnico existente, reducir preguntas repetitivas y escalar los casos que no tengan evidencia suficiente.

## Mapa rector

El único mapa vigente del MVP es:

- [docs/plan-mvp-presentacion-lunes.md](docs/plan-mvp-presentacion-lunes.md)

Ese documento define el alcance, la arquitectura, las fuentes, las prioridades, el plan de trabajo, los criterios de aceptación y el backlog posterior. No crear roadmaps paralelos sin actualizar primero ese archivo.

## Estado técnico actual

El proyecto ya tiene:

- integración funcional con Microsoft Teams / Microsoft 365 Agents Playground;
- backend Python con `microsoft-agents-hosting-aiohttp`;
- flujo modular en `agent.py`, `handler.py`, `retrieval.py`, `classification.py` y `formatting.py`;
- índice documental local en Markdown;
- clasificación estructurada;
- fallback de clasificación por reglas;
- respuesta con estado, confianza, evidencia, siguiente acción y escalamiento;
- integración opcional de lectura con ClickUp y Jira mediante código existente.

La evolución inmediata es convertir la recuperación en un `EvidenceProvider` sencillo: Azure AI Search para documentación del MVP, índice local como fallback y Jira o ClickUp como fuente operativa opcional. DownloadAseinfo.net alimentará el índice mediante su MCP o, mientras este no esté disponible, mediante staging real controlado. GitHub y SharePoint quedan como proveedores posteriores.

## Decisiones importantes

1. No rehacer el proyecto ni la integración con Teams.
2. Mantener la clasificación por reglas como red de seguridad.
3. Usar Azure AI Search como índice documental del MVP y conservar el índice local como fallback.
4. Mantener OpenAI para generación durante el MVP, salvo que exista una restricción corporativa explícita.
5. Consultar Jira o ClickUp como fuente operativa de solo lectura cuando exista acceso; no son condición para demostrar el núcleo documental.
6. Tratar MCP como mecanismo de acceso a fuentes, no como almacenamiento central.
7. No indexar todo el código de GitHub durante el MVP; GitHub y SharePoint son extensiones posteriores.
8. Responder solo con evidencia y escalar ante la duda.

## Contrato de respuesta

La respuesta visible debe incluir:

- Estado: `resuelto`, `en_progreso`, `similar_del_pasado` o `sin_evidencia`.
- Confianza: `alta`, `media` o `baja`.
- Resumen.
- Ruta de investigación.
- Evidencia con fuente, fragmento y ubicación.
- Versión o fecha cuando exista.
- Siguiente acción.
- Escalamiento cuando corresponda.

No inventar tickets, estados, causas, fechas, versiones, permisos ni soluciones.

## Reglas de implementación

- Mantener la lógica de orquestación fuera de `agent.py`.
- Evitar que `retrieval.py` llame todas las fuentes en cada consulta; usar routing por intención.
- Normalizar todas las fuentes a un modelo común de evidencia.
- No clasificar como `resuelto` solo porque aparezca la palabra `hotfix`.
- Aplicar límites y timeouts a llamadas externas.
- No guardar secretos en el código ni en logs.
- Preservar el índice local como fallback de desarrollo.
- No mostrar documentos o enlaces que el usuario no pueda consultar.

## Trabajo multiplataforma y con Codex

- El repositorio debe funcionar tanto en Windows como en macOS. Usar rutas relativas con `pathlib` en Python y comandos documentados para ambos sistemas.
- No cambiar el alcance del MVP ni rehacer la integración con Teams para probar IA local. La IA local es una configuración del cliente OpenAI-compatible.
- La configuración del modelo se lee de `OPENAI_API_KEY`, `OPENAI_MODEL` y, opcionalmente, `OPENAI_BASE_URL`. Si se define la URL base, se puede usar Ollama local (`http://127.0.0.1:11434/v1`).
- Los archivos `.env`, `env/.env.*` y cualquier secreto son locales. Nunca pedirlos, imprimirlos, copiarlos al repositorio ni sustituirlos por valores inventados.
- Antes de modificar código, leer este archivo, el `README.md` y el documento rector. Para el arranque en Mac, seguir [docs/desarrollo-macos.md](docs/desarrollo-macos.md).

## Archivos clave

- `src/agent.py`: entrada y eventos de Teams.
- `src/app.py`: host HTTP.
- `src/handler.py`: orquestación.
- `src/retrieval.py`: recuperación y futura capa de adaptadores.
- `src/document_index.py`: índice local de respaldo.
- `src/classification.py`: decisión estructurada y reglas de seguridad.
- `src/formatting.py`: respuesta visible.
- `src/models.py`: modelos de evidencia y decisión.
- `src/config.py`: configuración por entorno.
- `docs/knowledge-base`: documentos locales de prueba o staging.

## Documentos vigentes

- [docs/incorporacion-readmes.md](docs/incorporacion-readmes.md): proceso de incorporación documental.
- [docs/requerimientos-mcp-downloadaseinfo-mvp.md](docs/requerimientos-mcp-downloadaseinfo-mvp.md): contrato técnico del MCP de DownloadAseinfo.net.
- [docs/estado-actual-demo-chat-salvador.md](docs/estado-actual-demo-chat-salvador.md): estado y evidencia de avance.

## Pruebas mínimas antes de una demo

- Probar una consulta con evidencia documental real.
- Probar una consulta con ticket activo.
- Probar una consulta histórica.
- Probar una consulta sin evidencia.
- Verificar que cada afirmación tenga fuente.
- Verificar que un fallo de una fuente no derribe el bot.
- Revisar que no se impriman tokens ni secretos.
