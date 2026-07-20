# Desarrollo en macOS y uso de Codex

Esta guía permite abrir una copia limpia de Chat-Salvador en una Mac y continuar el trabajo sin mover secretos desde otra computadora.

## Qué se clona y qué se recrea

Se clona el código, documentación, infraestructura y la base Markdown de ejemplo. Se recrean localmente las dependencias, los entornos de Python y la configuración con credenciales.

No se deben subir ni copiar mediante Git:

- `.env` y cualquier token, clave API o contraseña;
- `env/.env.*`, especialmente los archivos `.user` de Microsoft 365 Agents Toolkit;
- `data/sharepoint/`, que contiene descargas autorizadas de SharePoint;
- `.venv/`, cachés y archivos generados.

Los datos de SharePoint se deben sincronizar de nuevo con la identidad autorizada en la Mac. No se asume que una cuenta en una máquina tenga los mismos permisos en otra.

## Preparación de la Mac

1. Instala Git y Python 3.11. Confirma que `python3.11 --version` funciona.
2. Clona el repositorio y crea un entorno virtual desde la raíz:

   ```bash
   git clone <URL_DEL_REPOSITORIO>
   cd Aseinfo_bot
   python3.11 -m venv .venv
   source .venv/bin/activate
   python -m pip install --upgrade pip
   python -m pip install -r src/requirements.txt
   ```

3. Crea tu configuración privada del modelo:

   ```bash
   cp .env.example .env
   ```

4. Ejecuta la validación base:

   ```bash
   python -m unittest discover -s tests -v
   ```

El backend se inicia con `python src/app.py`. Para conectarlo a Teams, abre el proyecto con Microsoft 365 Agents Toolkit y crea/configura el entorno local de esa Mac. Los valores de `BOT_ID`, `TEAMS_APP_ID`, `BOT_ENDPOINT` y secretos del bot no se versionan.

## Usar Ollama como IA local

Con 24 GB de RAM, un modelo de 7B cuantizado es un punto de partida razonable. Instala Ollama en la Mac, inicia su servicio y descarga el modelo elegido, por ejemplo:

```bash
ollama pull qwen2.5:7b
```

En `.env`, configura:

```dotenv
OPENAI_BASE_URL=http://127.0.0.1:11434/v1
OPENAI_API_KEY=ollama
OPENAI_MODEL=qwen2.5:7b
```

El proyecto crea un cliente compatible con OpenAI y usa esa URL cuando está definida. Mantén el resto de la arquitectura (Teams, recuperación y clasificación) igual. Si el modelo no respeta de forma confiable la respuesta JSON, la clasificación por reglas sigue siendo la protección mínima, pero se debe probar el flujo completo antes de una demo.

Para volver a OpenAI en la nube, borra `OPENAI_BASE_URL`, indica una clave válida en `OPENAI_API_KEY` y selecciona el modelo deseado.

## Primer contexto para Codex

Codex debe leer primero [AGENTS.md](../AGENTS.md), después [README.md](../README.md) y por último el mapa rector [plan-mvp-presentacion-lunes.md](plan-mvp-presentacion-lunes.md). Las reglas esenciales son:

- no rehacer la integración existente con Teams;
- no inventar respuestas sin evidencia;
- mantener Azure AI Search como principal y el índice Markdown como fallback;
- no leer, revelar o modificar secretos;
- ejecutar las pruebas antes de entregar cambios que afecten el comportamiento.

Al investigar un problema, usar `src/handler.py` como punto de entrada del flujo, y `src/retrieval.py` y `src/classification.py` para las decisiones principales. No concentrar lógica nueva en `src/agent.py`.
