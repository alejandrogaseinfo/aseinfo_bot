# Incorporación de documentación técnica

Este documento es una instrucción operativa de apoyo. El mapa del MVP está en [plan-mvp-presentacion-lunes.md](plan-mvp-presentacion-lunes.md).

## Fuente principal

La documentación debe provenir primero de DownloadAseinfo.net, porque allí se concentran releases, readmes, hotfixes, changelogs y presentaciones relacionadas con las entregas.

El MCP de DownloadAseinfo.net debería devolver:

- identificador estable;
- nombre y tipo de documento;
- producto y versión;
- fecha de actualización;
- contenido o descarga;
- URL de origen;
- indicación de actualización o eliminación.

## Staging local

Mientras se habilita el MCP, los documentos pueden prepararse en:

```text
docs/knowledge-base/
```

Para importar una carpeta o ZIP de setup/hotfix:

```powershell
.venv\Scripts\python.exe src\setup_ingest.py `
  --product "Evolution Connect" `
  --release "2.8.0" `
  --source C:\entregas\evolution-connect-2.8.0.zip
```

Para importar un README local:

```powershell
.venv\Scripts\python.exe src\repo_sync.py `
  --repo Nomina=C:\codigo\Nomina `
  --repo Facturacion=C:\codigo\Facturacion
```

## Destino del índice

El staging local debe utilizarse como fallback de desarrollo o como entrada temporal para Azure AI Search. El objetivo del MVP no es mantener una colección manual de archivos como fuente definitiva.

Cada documento debe conservar, cuando exista:

- producto;
- módulo;
- release;
- versión;
- fecha;
- tipo de documento;
- fuente original;
- URL o identificador.

## Otras fuentes

- ClickUp y Jira se consultan en modo de solo lectura para información operativa.
- GitHub se limita inicialmente a árbol, readmes, changelogs y documentación seleccionada.
- SharePoint requiere una biblioteca piloto y validación de permisos antes de ampliar la indexación.
