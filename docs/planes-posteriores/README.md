# Roadmap de integraciones posteriores

Esta carpeta conserva únicamente el trabajo posterior al cierre de producción de Libras. No cambia el objetivo de esta semana ni debe bloquearlo.

## Orden aprobado

### 1. ClickUp + GitHub

ClickUp aporta estado operativo e incidentes. GitHub aporta cambios técnicos únicamente cuando exista una relación verificable con el caso. Ambos deben integrarse en modo de solo lectura y con evidencia trazable.

El adaptador experimental de ClickUp está en `src/planes_posteriores/clickup_retrieval.py`. No existe todavía un conector GitHub productivo.

### 2. Jira histórico

Jira se integrará después de ClickUp + GitHub para recuperar antecedentes técnicos. Un ticket histórico no prueba por sí solo que el problema actual siga resuelto.

El adaptador experimental está en `src/planes_posteriores/jira_retrieval.py`.

### 3. MCP de downloads.aseinfo.net

Al final se construirá un MCP seguro y de solo lectura para `https://downloads.aseinfo.net/home`. Su función será descubrir documentos, recuperar metadatos y obtener contenido para la ingesta; no será consultado directamente ante cada pregunta.

La especificación conservada está en [requerimientos-mcp-downloadaseinfo-mvp.md](requerimientos-mcp-downloadaseinfo-mvp.md).

## Documentación activa de producción

- [../produccion-semana.md](../produccion-semana.md)
- [../despliegue-produccion.md](../despliegue-produccion.md)
- [../azure-ai-search-sharepoint.md](../azure-ai-search-sharepoint.md)

No se mantienen aquí planes alternativos de demo, arquitectura híbrida, Blob Storage o automatización incremental.
