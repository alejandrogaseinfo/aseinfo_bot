# AGENTS.md

## Proyecto

`Chat-Salvador` es un bot de autoservicio para Microsoft Teams orientado a soporte tecnico y operaciones. El objetivo del MVP es responder preguntas con evidencia trazable sobre:

- errores posteriores a actualizaciones o hotfixes,
- advertencias documentadas en readmes o setups,
- limites tecnicos de personalizaciones,
- y antecedentes de errores similares.

## Estado Actual

El proyecto ya no es una plantilla generica. Hoy existe un MVP funcional con:

- identidad real del bot en Teams,
- arquitectura modular en Python,
- base documental local en Markdown,
- retrieval documental local,
- clasificacion estructurada,
- fallback por reglas si OpenAI falla,
- y respuesta formateada para Teams.

Documentacion de referencia:

- [README.md](C:/aseinfo_bot/Aseinfo_bot/README.md:1)
- [docs/estado-actual-demo-chat-salvador.md](C:/aseinfo_bot/Aseinfo_bot/docs/estado-actual-demo-chat-salvador.md:1)
- [docs/fase-0-alcance-mvp.md](C:/aseinfo_bot/Aseinfo_bot/docs/fase-0-alcance-mvp.md:1)
- [docs/politica-respuesta-escalamiento.md](C:/aseinfo_bot/Aseinfo_bot/docs/politica-respuesta-escalamiento.md:1)

## Flujo Tecnico

El flujo principal actual es:

1. Teams entrega el mensaje al agente.
2. [src/agent.py](C:/aseinfo_bot/Aseinfo_bot/src/agent.py:1) recibe el evento y delega.
3. [src/handler.py](C:/aseinfo_bot/Aseinfo_bot/src/handler.py:1) orquesta retrieval, clasificacion y formato.
4. [src/retrieval.py](C:/aseinfo_bot/Aseinfo_bot/src/retrieval.py:1) obtiene evidencia documental local.
5. [src/document_index.py](C:/aseinfo_bot/Aseinfo_bot/src/document_index.py:1) carga, fragmenta y puntua documentos `.md`.
6. [src/classification.py](C:/aseinfo_bot/Aseinfo_bot/src/classification.py:1) intenta clasificar con OpenAI y tiene reglas locales de respaldo.
7. [src/formatting.py](C:/aseinfo_bot/Aseinfo_bot/src/formatting.py:1) arma la respuesta final para Teams.

## Archivos Clave

- [src/agent.py](C:/aseinfo_bot/Aseinfo_bot/src/agent.py:1): punto de entrada del bot
- [src/app.py](C:/aseinfo_bot/Aseinfo_bot/src/app.py:1): host aiohttp en `localhost:3978`
- [src/config.py](C:/aseinfo_bot/Aseinfo_bot/src/config.py:1): configuracion base
- [src/models.py](C:/aseinfo_bot/Aseinfo_bot/src/models.py:1): `EvidenceSource` y `BotDecision`
- [appPackage/manifest.json](C:/aseinfo_bot/Aseinfo_bot/appPackage/manifest.json:1): identidad y comandos del bot
- [docs/knowledge-base](C:/aseinfo_bot/Aseinfo_bot/docs/knowledge-base:1): base documental actual del MVP

## Contrato De Respuesta

El bot debe responder con esta estructura visible:

- `Estado`
- `Confianza`
- `Resumen`
- `Evidencia`
- `Siguiente accion`
- `Escalamiento`

Estados internos soportados:

- `resuelto`
- `en_progreso`
- `similar_del_pasado`
- `sin_evidencia`

## Reglas Importantes

1. No eliminar la clasificacion por reglas.
   Es una red de seguridad deliberada. No depender solo del modelo.

2. No mover toda la logica de nuevo a `agent.py`.
   La modularidad actual es parte del diseno del MVP.

3. No usar `/.env` como fuente manual de secretos.
   `/.env` se trata como archivo runtime/generado.

4. Mantener respuestas prudentes.
   Si no hay evidencia fuerte, debe preferirse `sin_evidencia` o escalamiento.

5. No integrar ClickUp, Jira o Azure AI Search de forma improvisada.
   Primero deben definirse bien la fuente, el contrato y el criterio de confianza.

## Secretos Y Entornos

Los secretos deben vivir en:

- `env/.env.local.user`
- `env/.env.dev.user`
- `env/.env.playground.user`

`src/agent.py` ya carga esos archivos. `src/config.py` acepta:

- `OPENAI_API_KEY`
- `SECRET_OPENAI_API_KEY`

## Como Probar El Bot

El Playground espera el bot en:

- `http://127.0.0.1:3978/api/messages`

Procedimiento operativo de arranque local:

- ver [README.md](C:/aseinfo_bot/Aseinfo_bot/README.md:40), seccion `Levantar El Bot Localmente`

Si el Playground sigue mostrando respuestas viejas:

1. verificar que el proceso correcto este escuchando en `3978`,
2. reiniciar el proceso Python que ejecuta `src/app.py`,
3. recargar el Playground o abrir una conversacion nueva.

Consulta de prueba recomendada:

```text
Despues de instalar un hotfix de nomina, el sistema fallo al guardar movimientos. Ya existe una advertencia o solucion documentada?
```

Resultado esperado actual:

- `Estado: resuelto`
- evidencia desde `docs/knowledge-base/readme_hotfix_nomina_2026_07_01.md`

## Pendientes Del Proyecto

Pendiente inmediato:

- cargar documentos reales del negocio,
- incorporar changelogs reales,
- ampliar base documental mas alla de documentos de ejemplo.

Pendiente posterior:

- integracion ClickUp,
- integracion Jira,
- integracion Azure AI Search,
- flujo de curacion de respuestas.

## Forma Correcta De Continuar

La siguiente evolucion recomendada es:

1. fortalecer Fase 4 con documentos reales,
2. validar mas consultas reales,
3. luego integrar fuentes operativas externas,
4. y despues endurecer observabilidad y politicas de confianza.

No conviene saltar directamente a infraestructura adicional sin antes mejorar la calidad de la evidencia documental.
