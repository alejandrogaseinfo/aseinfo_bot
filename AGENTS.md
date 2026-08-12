# AGENTS.md

## Prioridad activa

Libras es un bot interno de Microsoft Teams que responde únicamente con
documentación autorizada. La prioridad actual es cerrar la validación de
calidad del flujo RAG y preparar, si se autoriza, un piloto controlado. No se
debe desplegar ni activar el redactor sin autorización explícita.

Configuración productiva vigente:

```text
RETRIEVAL_STRATEGY=legacy
USE_LLM_EVIDENCE_VERIFIER=false
USE_LLM_GROUNDED_RESPONSE=false
```

El índice productivo de referencia es `libras-docs` en el servicio Azure AI
Search `srch-libras-prod`. La fuente documental autorizada es SharePoint en el
alcance aprobado del sitio `Soportealcliente`; no ampliar bibliotecas ni
copiar secretos al entorno local.

## Fuente de verdad documental

Leer en este orden antes de modificar código:

1. `README.md`.
2. `docs/contexto-actual.md`.
3. `docs/plan.md`.
4. `docs/resultado-calidad-20260812.md`.
5. `docs/arquitectura-produccion.md`.

La muestra humana del redactor está en
`docs/revision-humana-redactor-20260812.md`. Las bitácoras fechadas y los
planes archivados son antecedentes; no sustituyen estos documentos vigentes.

## Arquitectura vigente

```text
Teams
  -> App Service / bot
  -> intención y alcance
  -> Azure AI Search (legacy: léxico + apoyo vectorial)
  -> filtros de procedencia, seguridad y versión
  -> ranking determinista
  -> clasificación de evidencia
  -> respuesta determinista o redactor grounded opt-in
  -> respuesta y enlaces
```

El redactor recibe solo evidencias ya autorizadas. No decide permisos,
versiones ni alcance. Una respuesta inválida, una cita no sustentada, una
inyección documental o una falta de evidencia debe fallar cerrado y conservar
la salida determinista o la abstención segura.

## Reglas de implementación

- No cambiar `legacy`, activar el evaluador LLM ni activar el redactor en
  producción durante la validación.
- Mantener filtros estrictos para secretos/credenciales, inyección documental,
  fuentes no autorizadas, versiones incompatibles y ausencia clara de
  evidencia.
- Permitir procedimientos técnicos autorizados, incluido SQL de ofuscación;
  no confundir datos sensibles tratados por un procedimiento con secretos que
  deben bloquearse.
- No crear reglas aisladas para un solo caso. Preferir mejoras generales de
  recuperación, deduplicación, validación de citas y clasificación.
- No reindexar, cambiar el índice, modificar permisos ni desplegar sin una
  instrucción explícita del responsable.
- No guardar secretos, tokens, PDFs sincronizados ni razonamiento del modelo en
  el repositorio o los logs.
- Mantener límites y timeouts de todas las llamadas externas.
- Usar `pathlib`, rutas relativas y compatibilidad Windows/macOS.
- Escribir los commits en español con formato breve, por ejemplo
  `fix: valida las fuentes del redactor`.

## Archivos clave

- `src/agent.py`: entrada y actividades de Teams.
- `src/app.py`: host HTTP (`/api/messages`, `/healthz`, `/readyz`).
- `src/handler.py`: orquestación, barreras y decisión final.
- `src/retrieval.py` y `src/azure_search.py`: recuperación y ranking.
- `src/grounded_response.py`: redactor grounded acotado y validación de citas.
- `src/classification.py`: reglas de evidencia y abstención.
- `src/formatting.py`: respuesta y enlaces visibles.
- `src/config.py`: configuración por entorno.
- `src/sharepoint_sync.py` y `src/azure_search_ingest.py`: ingesta separada.

## Validación mínima

Antes de consolidar cambios:

```powershell
python -m unittest discover -s tests -q
git diff --check
```

Para Azure, usar una consola con permisos de lectura y verificar sin mostrar
secretos:

```powershell
Resolve-DnsName srch-libras-prod.search.windows.net
```

En App Service, ejecutar Python desde **SSH → Application** con las
dependencias activas. Kudu se limita a inspección o transferencia de archivos.
Una evaluación local contra Azure debe usar temporalmente fallback desactivado,
`libras-docs`, `legacy` y ambos LLM apagados.

## Fuera de alcance

ClickUp, GitHub, Jira, MCP de `downloads.aseinfo.net`, nuevas bibliotecas de
SharePoint, reconstrucciones de índice y la estrategia `v2` no forman parte de
esta entrega. Sus documentos permanecen como planes futuros o antecedentes y
no deben entrar en el flujo productivo actual.
