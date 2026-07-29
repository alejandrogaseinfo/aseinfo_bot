# AGENTS.md

## Proyecto y prioridad activa

`Libras` es un bot interno de Microsoft Teams que responde preguntas a partir de documentación aprobada. La prioridad de esta semana es llevarlo a producción con este único flujo:

```text
Microsoft Teams -> Libras en Azure -> Azure AI Search <- SharePoint / OneDrive
```

El objetivo de producción es que personas autorizadas de la organización puedan consultar, desde Teams, documentación ubicada en una biblioteca o carpeta aprobada de SharePoint/OneDrive.

## Mapa rector vigente

Antes de planificar o implementar, leer:

- [docs/contexto-actual.md](docs/contexto-actual.md)
- [docs/produccion-semana.md](docs/produccion-semana.md)
- [docs/azure-ai-search-sharepoint.md](docs/azure-ai-search-sharepoint.md)

No crear roadmaps paralelos. Actualizar `docs/contexto-actual.md` y
`docs/produccion-semana.md` si cambia el alcance, una dependencia o el estado
de producción.

## Fases posteriores al objetivo de esta semana

El objetivo inmediato está definido en `docs/produccion-semana.md`. Después de cerrar producción, el orden aprobado es:

1. Integrar ClickUp y GitHub.
2. Integrar Jira como fuente de documentación histórica.
3. Crear un MCP de solo lectura para `https://downloads.aseinfo.net/home`.

`docs/planes-posteriores/` y `src/planes_posteriores/` solo pueden guiar esas fases en ese orden. No introducirlas en el flujo productivo de esta semana ni crear una arquitectura paralela.

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

- Integración de ClickUp y GitHub.
- Integración histórica de Jira.
- MCP y `downloads.aseinfo.net`.
- Nuevas fuentes documentales distintas de SharePoint/OneDrive.
- Otras bibliotecas o carpetas de SharePoint distintas de
  `Documentos compartidos/SOLUCIONES`, salvo autorización explícita.
- Automatización incremental avanzada, Blob Storage y enriquecimientos no solicitados.
- Cambios de arquitectura que no sean necesarios para producción.

## Reglas de implementación

- Mantener la orquestación fuera de `agent.py`.
- Aplicar límites y timeouts a llamadas externas.
- No guardar secretos en el código ni en logs.
- Usar rutas relativas con `pathlib` y conservar compatibilidad Windows/macOS.
- No cambiar el alcance para experimentar con IA local u otras integraciones.
- Antes de modificar código, leer este archivo, `README.md` y
  `docs/contexto-actual.md`.

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
