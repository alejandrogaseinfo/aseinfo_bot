# Libras

Bot interno de Microsoft Teams para consultar documentación aprobada. Recupera evidencia documental, la clasifica y responde únicamente cuando hay respaldo suficiente.

## Estado y alcance

La prioridad actual es validar Libras en Microsoft 365 Agents Playground antes
de solicitar autorización para publicar en Teams. La única fuente documental
autorizada en esta fase es `Documentos compartidos/SOLUCIONES` y sus
subcarpetas. El contexto consolidado está en
[docs/contexto-actual.md](docs/contexto-actual.md); no ampliar el alcance ni
crear roadmaps paralelos sin actualizarlo.

El proyecto ya incluye:

- integración con Microsoft Teams y Microsoft 365 Agents Playground;
- backend Python modular;
- base documental local en Markdown como respaldo;
- Azure AI Search como índice documental principal cuando se configure;
- sincronización de documentos legibles autorizados desde SharePoint;
- clasificación estructurada con fallback por reglas;

El trabajo posterior a producción seguirá este orden: primero ClickUp + GitHub, luego Jira como fuente histórica y finalmente un MCP de solo lectura para `downloads.aseinfo.net`. El mapa y el estado de estas fases están en [docs/planes-posteriores](docs/planes-posteriores/README.md).

## Inicio rápido

Requisitos: Git, Python 3.11 y acceso a Microsoft 365 Agents Toolkit/Playground para ejecutar el bot en Teams.

```bash
git clone <URL_DEL_REPOSITORIO>
cd Aseinfo_bot
python3.11 -m venv .venv
```

Activar el entorno e instalar dependencias:

```bash
# macOS / Linux
source .venv/bin/activate

# Windows PowerShell
.venv\Scripts\Activate.ps1

python -m pip install --upgrade pip
python -m pip install -r src/requirements.txt
```

Crear la configuración local del modelo. Nunca subas este archivo:

```bash
# macOS / Linux
cp .env.example .env

# Windows PowerShell
Copy-Item .env.example .env
```

Para usar OpenAI en la nube, configura `OPENAI_API_KEY` y, si lo necesitas, `OPENAI_MODEL` en `.env`. Para usar Ollama local, consulta [docs/desarrollo-macos.md](docs/desarrollo-macos.md).

Ejecutar las pruebas:

```bash
python -m unittest discover -s tests -v
```

Antes de desplegar o solicitar permisos, ejecutar el preflight. No imprime
secretos; devuelve código 1 si falta algún requisito de la etapa elegida:

```bash
# Solicitud A: plataforma, modelo, Azure AI Search y paquete de Teams
python src/preflight.py --stage platform

# Solicitud B: datos mínimos de la biblioteca/carpeta SharePoint aprobada
python src/preflight.py --stage data-access
```

Iniciar el backend:

```bash
python src/app.py
```

Escucha en `http://127.0.0.1:3978/api/messages`. El inicio desde Teams requiere además los archivos de entorno generados por Microsoft 365 Agents Toolkit; no se incluyen en Git porque contienen datos propios de cada entorno.

## Estructura

- [src/agent.py](src/agent.py): entrada y eventos de Teams; crea el cliente de modelo compatible con OpenAI.
- [src/app.py](src/app.py): host HTTP.
- [src/handler.py](src/handler.py): orquestación del flujo.
- [src/retrieval.py](src/retrieval.py): recuperación y routing de evidencia.
- [src/document_index.py](src/document_index.py): índice Markdown local de respaldo.
- [src/classification.py](src/classification.py): clasificación estructurada y reglas de seguridad.
- [src/formatting.py](src/formatting.py): respuesta visible para Teams.
- [src/models.py](src/models.py): modelos de evidencia y decisión.
- [src/config.py](src/config.py): configuración por entorno.
- [docs/knowledge-base](docs/knowledge-base): documentos locales de prueba o staging.

## Configuración y secretos

`.env.example` enumera las variables para el modelo, Azure AI Search y SharePoint. Cópialo a `.env` y completa solo los servicios que vayas a usar.

Los archivos `env/.env.*` pertenecen a Microsoft 365 Agents Toolkit. En cada máquina se generan o recrean para su propia sesión/tenant; sus archivos `.user` contienen secretos. No copies ni subas claves, tokens, PDFs sincronizados, `.env` ni `env/.env.*`.

El bot puede usar un servicio compatible con la API de OpenAI. Por defecto apunta a OpenAI; si configuras `OPENAI_BASE_URL`, puede apuntar a Ollama local sin modificar la lógica del bot.

## Azure AI Search y SharePoint

La configuración, permisos mínimos y comandos de carga están en [docs/azure-ai-search-sharepoint.md](docs/azure-ai-search-sharepoint.md). Azure AI Search es el índice documental principal cuando está disponible; la base Markdown local se mantiene como fallback de desarrollo.

La arquitectura productiva vigente está documentada en
[docs/arquitectura-produccion.md](docs/arquitectura-produccion.md). Incluye el
flujo de consultas desde Teams, el job separado de ingesta, la carpeta
`Documentos compartidos/SOLUCIONES`, Azure AI Search, OpenAI y las referencias
de secretos desde Key Vault.

## Documentación del proyecto

- [Contexto actual y continuidad](docs/contexto-actual.md)
- [Foco de producción de esta semana](docs/produccion-semana.md)
- [Azure AI Search y SharePoint/OneDrive](docs/azure-ai-search-sharepoint.md)
- [Guía de desarrollo en macOS y Codex](docs/desarrollo-macos.md)
- [Roadmap de integraciones posteriores](docs/planes-posteriores/README.md)
