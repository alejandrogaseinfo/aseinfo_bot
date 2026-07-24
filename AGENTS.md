# AGENTS.md

## Proyecto y prioridad activa

`Libras` es un bot interno de Microsoft Teams que responde preguntas a partir de documentación aprobada. La prioridad de esta semana es llevarlo a producción con este único flujo:

```text
Microsoft Teams -> Libras en Azure -> Azure AI Search <- SharePoint / OneDrive
```

El objetivo de producción es que personas autorizadas de la organización puedan consultar, desde Teams, documentación ubicada en una biblioteca o carpeta aprobada de SharePoint/OneDrive.

## Mapa rector vigente

Antes de planificar o implementar, leer:

- [docs/produccion-semana.md](docs/produccion-semana.md)
- [docs/azure-ai-search-sharepoint.md](docs/azure-ai-search-sharepoint.md)

No crear roadmaps paralelos. Actualizar `docs/produccion-semana.md` si cambia el alcance, una dependencia o el estado de producción.

## Documentación aplazada

`docs/planes-posteriores/` y `src/planes_posteriores/` conservan planes, arquitectura, referencias y adaptadores para fases posteriores. **No leer, importar, usar, actualizar ni implementar nada desde esas carpetas durante esta semana**, salvo que el usuario reactive explícitamente una de esas fases.

Las fases aplazadas incluyen ClickUp, Jira, GitHub, MCP/DownloadAseinfo.net, arquitectura híbrida, automatización incremental con Blob Storage y planes de demo históricos.

## Estado técnico relevante

El proyecto ya tiene:

- integración funcional con Microsoft Teams / Microsoft 365 Agents Playground;
- backend Python con `microsoft-agents-hosting-aiohttp`;
- flujo modular en `agent.py`, `handler.py`, `retrieval.py`, `classification.py` y `formatting.py`;
- índice documental local como respaldo de desarrollo;
- sincronización delegada de PDFs desde una carpeta piloto de OneDrive/SharePoint;
- ingesta de documentos en Azure AI Search.

Para producción, el acceso personal/delegado a SharePoint debe sustituirse por una identidad corporativa con permisos mínimos sobre el sitio autorizado. Azure AI Search será el índice documental de producción; el índice local queda únicamente como fallback de desarrollo.

## Decisiones de implementación

1. No rehacer la integración de Teams ni el backend principal.
2. Limitar esta semana a Teams, Azure AI Search y SharePoint/OneDrive.
3. Usar una sola biblioteca o carpeta documental aprobada como fuente inicial.
4. Aplicar mínimo privilegio: `Sites.Selected` y lectura exclusiva del sitio aprobado; no usar permisos globales de Microsoft Graph.
5. Mantener autenticación corporativa, identidades administradas y secretos fuera del código y logs.
6. No mostrar documentos, fragmentos ni enlaces que la audiencia autorizada no pueda consultar.
7. Mantener la clasificación por reglas y la política de evidencia como red de seguridad.

## Fuera de alcance esta semana

- ClickUp, Jira, GitHub y sus conectores.
- MCP y DownloadAseinfo.net.
- Nuevas fuentes documentales distintas de SharePoint/OneDrive.
- Automatización incremental avanzada, Blob Storage y enriquecimientos posteriores.
- Cambios de arquitectura que no sean necesarios para producción.

## Reglas de implementación

- Mantener la orquestación fuera de `agent.py`.
- Aplicar límites y timeouts a llamadas externas.
- No guardar secretos en el código ni en logs.
- Usar rutas relativas con `pathlib` y conservar compatibilidad Windows/macOS.
- No cambiar el alcance para experimentar con IA local u otras integraciones.
- Antes de modificar código, leer este archivo, `README.md` y `docs/produccion-semana.md`.

## Archivos clave

- `src/agent.py`: entrada y eventos de Teams.
- `src/app.py`: host HTTP.
- `src/handler.py`: orquestación.
- `src/retrieval.py`: recuperación documental.
- `src/document_index.py`: índice local de respaldo.
- `src/config.py`: configuración por entorno.
- `src/sharepoint_sync.py`: sincronización actual desde OneDrive/SharePoint.
- `src/azure_search_ingest.py`: carga hacia Azure AI Search.

## Pruebas mínimas antes de producción

- Probar una pregunta desde Teams con evidencia real de SharePoint.
- Verificar que Azure AI Search devuelve el documento y enlace correctos.
- Probar una consulta sin evidencia.
- Verificar que el bot no expone secretos ni datos fuera de la biblioteca autorizada.
- Verificar que una persona de la audiencia objetivo puede instalar y usar Libras en Teams.
