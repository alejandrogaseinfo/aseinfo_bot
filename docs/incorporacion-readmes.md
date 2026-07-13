# Ingesta de documentación de setups y hotfixes

## Objetivo

Los READMEs no se mantienen en una ubicación operativa separada. Se generan como parte de los setups y hotfixes, por lo que la fuente principal del bot debe ser la documentación incluida en esas entregas.

Los changelogs y notas técnicas de las entregas también pueden incorporarse como documentos de conocimiento.

## Estructura esperada

Los archivos normalizados se guardarán en:

```text
docs/knowledge-base/
```

Convención de nombres:

```text
NombreRepositorio_README.md
```

Ejemplos:

```text
Nomina_README.md
Facturacion_README.md
PortalOperaciones_README.md
```

Otros documentos técnicos pueden conservar un nombre descriptivo, por ejemplo:

```text
changelog_evolution_connect_2026_07_08.md
```

## Importación de un setup o hotfix

Se puede importar una carpeta o un ZIP de setup/hotfix:

```powershell
.venv\Scripts\python.exe src\setup_ingest.py `
  --product "Evolution Connect" `
  --release "2.8.0" `
  --source C:\entregas\evolution-connect-2.8.0.zip
```

El comando extrae documentos `.md`, `.markdown` y `.txt`, agrega metadatos de la entrega y los prepara como evidencia primaria.

## Importación local de un README aislado

```powershell
.venv\Scripts\python.exe src\repo_sync.py `
  --repo Nomina=C:\codigo\Nomina `
  --repo Facturacion=C:\codigo\Facturacion
```

También se puede indicar directamente el archivo:

```powershell
.venv\Scripts\python.exe src\repo_sync.py `
  --repo Nomina=C:\documentos\Nomina\README.md
```

El script copia los archivos a `docs/knowledge-base` y los renombra de forma consistente.

## Sincronización al Vector Store

Después de agregar o actualizar documentos de setups, hotfixes o READMEs:

```powershell
.venv\Scripts\python.exe src\vector_store_sync.py
```

El sincronizador actual ya detecta todos los archivos `.md` de `docs/knowledge-base`, por lo que no se necesita una ruta especial para los READMEs.

## Prioridad de fuentes

```text
Documentación del setup/hotfix
        ↓
ClickUp para casos activos
        ↓
Jira para antecedentes históricos
        ↓
Diffs y cambios de código como evidencia secundaria
```

## Pendientes

- Recibir los READMEs reales de los equipos.
- Confirmar dónde se almacenan actualmente los setups y hotfixes.
- Definir el mecanismo de entrega o carpeta compartida.
- Implementar la sincronización automática cuando exista acceso a esa ubicación.
- Agregar metadatos de repositorio, rama y fecha de actualización.

## Criterio de aceptación de esta fase

La base queda preparada para recibir documentos reales desde un setup o hotfix mediante un comando reproducible, y esos archivos pueden pasar al Vector Store usando el sincronizador existente.

## Documento disponible actualmente

Se incorporó:

- `docs/knowledge-base/changelog_evolution_connect_2026_07_08.md`
- Fuente: `Changelog - Evolution Connect-20260708100224.md`
- Tipo: changelog técnico
- Fecha más reciente documentada: 26/MAR/2026, versión 2.8.0

Este documento permite demostrar conocimiento real del producto aunque todavía no se cuente con los READMEs individuales ni con acceso a Jira.
