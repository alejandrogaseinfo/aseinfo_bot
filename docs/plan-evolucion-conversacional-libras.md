# Plan de evolución conversacional de Libras

> Plan de implementación — 2026-08-07. No activa cambios en producción.

> Estado de ejecución: P0–P4 implementados y validados localmente. Las fases de
> experiencia se activan con banderas reversibles.

## Decisión de alcance

Libras debe seguir los mensajes **solo dentro del mismo chat de Teams**. Al abrir otro chat o reiniciar el backend, el contexto se pierde.

Por ello no se usará Conversations API en esta fase. Esa API crea un objeto duradero y sus elementos no tienen el TTL estándar de 30 días de las Responses; es apropiada para hilos que deben sobrevivir sesiones, dispositivos, reinicios o varios servicios. Teams no informa de forma fiable cuándo el usuario cerró un chat para borrar ese objeto. Se usará estado efímero, identificado por `conversation.id` de Teams y guardado únicamente en la memoria del backend.

```text
chat actual de Teams -> memoria temporal del backend -> hilo actual
chat nuevo o reinicio -> estado vacío
```

Si en el futuro se necesita recuperar un hilo tras un reinicio, se deberá aprobar una política de retención y evaluar Conversations API. Referencia: [Estado de conversación de OpenAI](https://developers.openai.com/api/docs/guides/conversation-state).

## Priorización

| Prioridad | Implementación | Razón |
| --- | --- | --- |
| P0 | Línea base, pruebas y banderas | Asegura que toda mejora sea medible y reversible. |
| P1 | Seguimiento temporal del mismo chat | Resuelve referencias como “esa versión” o “lo anterior”; es la necesidad principal. |
| P2 | Enlaces legibles | Mejora inmediata de bajo riesgo, sin cambiar evidencia. |
| P3 | Acciones iniciales | Orienta al usuario y reduce preguntas ambiguas. |
| P4 | Comandos `/` | Facilita acciones explícitas, en especial comenzar de nuevo. |

Se recomienda iniciar por **P1**. P2 puede publicarse antes o junto al piloto de P1 como cambio aislado de bajo riesgo.

## Reglas que no cambian

- Azure AI Search y SharePoint autorizado conservan la autoridad de la evidencia.
- Las reglas de secretos, confidencialidad, alcance e inyección se aplican antes de leer o actualizar el estado del hilo.
- No se guardan mensajes, fragmentos, URLs, correos ni IDs de usuario en bases de datos, archivos, logs o servicios externos por esta funcionalidad.
- `RETRIEVAL_STRATEGY=legacy`, clasificación por reglas y fallbacks actuales no cambian.
- Cada fase debe tener una bandera de entorno apagada por defecto.

## P0 — Preparación

1. Ejecutar y registrar la suite actual, latencia y pruebas de Teams.
2. Crear banderas independientes para: contexto temporal, enlaces legibles, acciones iniciales y comandos extendidos.
3. Ampliar la regresión con: versión, procedimiento, seguimiento, falta de evidencia, cambio de tema, secreto, dato confidencial e inyección.
4. Mantener logs sin texto de usuarios ni contenido documental; registrar solo métricas técnicas como duración y uso/no uso de contexto.

**Salida:** con todas las banderas apagadas, no cambia ninguna respuesta actual.

## P1 — Seguimiento temporal del mismo chat

### Punto de partida

`src/agent.py` usa `_documentary_responses`, un diccionario en memoria con la última respuesta documental por `conversation.id`. Es efímero, pero solo admite un seguimiento limitado: se elimina al producir una respuesta no documental y no conserva tema, producto, versión ni datos solicitados.

### Diseño

1. Crear `conversation_state.py` con un `ChatThreadState` por `conversation.id`. No usar almacenamiento persistente ni Conversations API.
2. Conservar una ventana acotada de datos estructurados, no el transcript completo: tema, producto/versión explícitos, última respuesta documental apta para resumen y datos necesarios para resolver referencias. Definir máximo de turnos, tamaño y expiración por inactividad en memoria.
3. En `agent.py`, leer ese estado antes de `process_user_message` y actualizarlo solo después de una respuesta válida. Reinicio o expiración implica hilo vacío y el bot continúa normalmente.
4. En `handler.py`, aplicar primero las barreras actuales; después resolver referencias con ese estado y finalmente llamar a `retrieve_evidence` para obtener evidencia nueva como hoy.
5. Mantener la ruta determinista actual para “resume lo anterior”. Para “¿qué cambios trae esa versión?”, reutilizar solamente versión o documento citado del turno anterior y volver a buscar evidencia.
6. Si el usuario nombra otro producto o versión de forma explícita, ese dato prevalece y abre un nuevo tema dentro del mismo chat.
7. Ante timeout, error o estado inválido, ignorar el contexto y degradar al comportamiento actual, sin mostrar identificadores técnicos.
8. Evitar cruces de contexto si llegan mensajes simultáneos de un mismo chat.

### Pruebas de aceptación

- La segunda pregunta “¿qué cambios trae esa versión?” conserva la versión previa, recupera evidencia nueva y muestra su fuente.
- “Resume los pasos anteriores” usa solo la respuesta documental permitida y mantiene sus enlaces.
- Una pregunta explícita por otro producto no hereda versión, fuente ni pasos del tema anterior.
- Solicitudes sensibles, fuera de alcance o de inyección no modifican el estado ni llegan a recuperación.
- Abrir otro chat o reiniciar el backend elimina el seguimiento.
- Si falla el módulo, el bot responde igual que antes de P1.

## P2 — Enlaces amigables

1. Cambiar solamente `src/formatting.py` para emitir Markdown de Teams. Ejemplo: `[Ver documentación: Acciones de personal (pág. 18)](URL)` en vez de la URL completa; para una carpeta, `[Ver archivos relacionados](URL)`.
2. Formar la etiqueta desde evidencia confiable: título, página/sección y tipo de destino. Nunca usar texto inventado por el modelo.
3. Mostrar varias fuentes como enlaces breves y desduplicados. Sin URL HTTP válida, mostrar título sin fabricar enlace.
4. Ajustar resúmenes y pruebas existentes para preservar Markdown.
5. Validar visualmente en Teams/Playground que cada destino es el documento o carpeta autorizada correcto.

**Reversión:** apagar la bandera de formato y volver a URLs visibles. No toca búsqueda, fuentes ni seguimiento.

## P3 — Inicio guiado

1. Reemplazar el saludo inicial por una tarjeta adaptativa o acciones bajo la pregunta “¿Qué deseas hacer hoy?”.
2. Ofrecer: **Consultar versión**, **Consultar procedimiento**, **Revisar actualización**, **Reportar un error** y **Ayuda**; mantener alternativa textual para clientes que no procesen tarjetas.
3. Cada acción envía un valor de una lista cerrada (`version`, `procedimiento`, `actualizacion`, `error`, `ayuda`) y una pregunta de aclaración. No realiza búsqueda ni entrega una respuesta predefinida.
4. Guardar el tema seleccionado solo en `ChatThreadState`; un nuevo mensaje explícito del usuario puede cambiarlo.
5. Solicitar por categoría producto/versión, tarea, componente actualizado o mensaje de error y pasos para reproducirlo.
6. Validar los payloads y aplicar las mismas barreras que a un mensaje normal.

La experiencia queda controlada por `USE_GUIDED_START=true`; apagarla restaura
el saludo anterior sin desactivar el seguimiento ni los enlaces amigables.

## P4 — Comandos `/`

El manifiesto ya declara comandos de consulta y el normalizador acepta la barra. Se completarán como rutas deterministas, sin que el modelo los interprete.

| Comando | Acción | Efecto |
| --- | --- | --- |
| `/ayuda` | Muestra ejemplos y alcance. | No cambia el hilo. |
| `/version` | Pide producto y versión. | Selecciona tema temporal. |
| `/procedimiento` | Pide tarea, producto y versión. | Selecciona tema temporal. |
| `/actualizacion` | Pide versión o componente. | Selecciona tema temporal. |
| `/nuevo` | Limpia el estado temporal. | Inicia un hilo vacío. |

No se requiere `/borrar_chat`: no hay historial persistido. `/nuevo` es seguro e inmediato. Cuando los comandos estén listos, actualizar `appPackage/manifest.json`, incrementar la versión y validar el paquete en Teams.

## Despliegue y reversión

1. Implementar una fase por vez y ejecutar `python -m unittest discover -s tests -v`, preflight y pruebas manuales de Playground/Teams.
2. Desplegar con banderas apagadas y activar primero para un piloto controlado. Comparar seguridad, latencia, evidencia y errores contra la línea base P0.
3. Si hay desviación, apagar solo la bandera de la fase. P1 vuelve al seguimiento limitado actual y P2 a URLs visibles; no se reconstruye el índice ni se modifica la sincronización de SharePoint.

## Resultado esperado

Libras seguirá el contexto de mensajes en un mismo chat sin crear memoria entre chats. Los enlaces serán breves, las acciones iniciales ayudarán a formular la consulta y `/nuevo` permitirá empezar de cero, preservando el flujo de evidencia documental existente.
