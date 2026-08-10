# Plan futuro — Conversations API para Libras

> Estado: **diferido hasta revisión con la jefatura y disponibilidad del
> administrador de Azure**. La bandera `USE_OPENAI_CONVERSATIONS` permanece en
> `false`; no se configura almacenamiento, no se asignan permisos y no se
> despliega esta capacidad.

## Decisión actual

Libras es un asistente de **consulta documental**. Su objetivo es recuperar
evidencia vigente desde Azure AI Search y responder con fuentes verificables,
no mantener una relación, expediente o proceso largo entre sesiones.

Por ello, la alternativa aprobada para el piloto es el contexto temporal y
acotado del chat de Teams: tema, producto, versión, última respuesta documental
y los datos mínimos para resolver referencias como “esa versión” o “lo
anterior”. `/nuevo` limpia ese contexto local inmediatamente.

Conversations API queda como alternativa futura, solo si se aprueba el requisito
de que un usuario continúe el contexto completo después de reiniciar el backend,
volver días después o cambiar de dispositivo.

## Justificación de la decisión

El contexto temporal es la mejor alternativa actual porque:

- satisface los seguimientos esperados en un chat de consultas sin conservar un
  transcript completo;
- reduce la exposición y la retención de información interna;
- evita una nueva dependencia operativa de Azure Storage, RBAC y limpieza de
  objetos remotos;
- mantiene las respuestas documentales basadas en evidencia nueva, en lugar de
  depender de un historial que podría quedar desactualizado;
- permite usar `/nuevo` de forma inmediata, sin una operación remota de borrado;
- es reversible y ya está integrado en el flujo actual de Libras.

La guía de OpenAI distingue el manejo manual de contexto, la continuación por
`previous_response_id` y Conversations. Las conversaciones de esta última son
objetos durables; sus ítems no siguen el TTL estándar de 30 días, por lo que
requieren una política explícita de retención y borrado. [Estado de conversación
de OpenAI](https://developers.openai.com/api/docs/guides/conversation-state).

## Objetivo

Hacer que Libras conserve el contexto completo de un chat personal de Microsoft
Teams, incluso después de un reinicio del backend. El comando `/nuevo` debe
eliminar ese contexto e iniciar un hilo vacío.

La solución usará **Conversations API** junto con **Responses API** de OpenAI.
Una conversación de OpenAI es un objeto durable; por ello, el borrado explícito
es un requisito funcional de esta implementación.

## Alcance futuro y versiones

| Componente | Versión de partida | Entrega prevista | Cambio |
| --- | --- | --- | --- |
| Backend Libras | `0.1.3` | Por decidir tras aprobación | No ahora |
| Aplicación Teams | `0.1.0` | `0.1.0` | No |

Cuando se retome, este trabajo será de **backend**. No modifica `appPackage/manifest.json`, los
permisos de Teams, `appId`, `botId`, dominios ni capacidades. Por tanto, no se
debe generar ni solicitar aprobación de un nuevo paquete Teams para esta
entrega.

> Excepción: si posteriormente se cambia el manifiesto o se publica una nueva
> versión del paquete, esa actualización sí seguirá el flujo de aprobación del
> tenant de Teams.

## Arquitectura objetivo

```text
Usuario en Teams
    -> activity.conversation.id
    -> tabla de mapeo persistente
       (tenant + Teams conversation ID -> OpenAI conversation ID)
    -> OpenAI Conversations API + Responses API
    -> respuesta con contexto completo del hilo

Azure AI Search -> evidencia documental -> Responses API
```

La clave del mapeo incluirá el identificador de tenant y el identificador de
conversación de Teams. No se utilizará como clave el nombre, correo ni texto
del usuario.

## Puertas obligatorias antes de retomar

1. Aprobar la retención de contenido: las Conversations e ítems de OpenAI se
   conservan hasta que se borran explícitamente.
2. Crear un almacenamiento persistente mínimo para el mapeo; se recomienda
   Azure Table Storage por guardar solo identificadores y fechas.
3. Definir una retención operativa para chats abandonados y un proceso de
   limpieza que borre tanto la conversación de OpenAI como su mapeo local.
4. Confirmar que producción usa la API oficial de OpenAI. Un proveedor
   compatible configurado mediante `OPENAI_BASE_URL` puede no implementar
   Conversations ni Responses API; en ese caso la función deberá desactivarse
   de forma segura y conservar el comportamiento actual.

## Fases futuras de implementación

### 1. Configuración y persistencia

- Añadir una bandera reversible `USE_OPENAI_CONVERSATIONS=false`.
- Configurar la conexión de Azure Table Storage mediante identidad administrada
  o referencia de Key Vault; no guardar cadenas de conexión ni IDs de
  conversaciones en el repositorio.
- Crear un repositorio `conversation_mapping_store` con operaciones:
  `get`, `create_if_absent`, `delete` y `delete_expired`.
- Guardar únicamente: clave opaca de Teams, `openai_conversation_id`,
  `created_at`, `last_seen_at` y versión de esquema.
- Aplicar unicidad, TTL y control de concurrencia para evitar que dos mensajes
  simultáneos creen dos hilos de OpenAI para el mismo chat.

### 2. Adaptador de OpenAI

- Crear un módulo aislado, por ejemplo `src/openai_conversations.py`, que
  encapsule `client.conversations.create`, la creación de respuestas y el
  borrado de conversaciones.
- En el primer mensaje de un chat, crear la conversación y persistir su ID.
- En cada mensaje posterior, llamar a `client.responses.create` usando el
  mismo `conversation` y el mensaje nuevo como entrada.
- Pasar como contexto de la respuesta final únicamente la evidencia aprobada
  que entregue Azure AI Search y las instrucciones de Libras.
- Establecer timeouts, clasificación de errores, reintentos solo para fallos
  transitorios y trazas con IDs anonimizados; nunca registrar mensajes ni
  claves.

### 3. Integración con el flujo de Libras

- Conservar antes de cualquier llamada remota los rechazos de secretos, datos
  confidenciales, bibliotecas fuera de alcance e inyección de instrucciones.
- Mantener Azure AI Search como única fuente documental autorizada y conservar
  el formateo de fuentes y enlaces existente.
- Adaptar las rutas conversacionales y la generación final documental para que
  usen el adaptador nuevo. La clasificación por reglas permanece como red de
  seguridad.
- Retirar gradualmente el uso de `ConversationStateStore` como memoria de
  historial. Puede mantenerse de forma temporal para estado de interfaz
  (tema del menú), pero no debe ser la fuente de verdad del chat.
- Definir compactación o resumen de hilos largos antes de alcanzar la ventana
  de contexto del modelo; preservar restricciones, hechos confirmados, fuentes
  y preguntas abiertas, no un resumen inventado.

### 4. Comando `/nuevo`

Al recibir `/nuevo`, el backend debe ejecutar, en este orden:

1. Encontrar el mapeo del chat de Teams.
2. Solicitar el borrado de la conversación correspondiente en OpenAI.
3. Eliminar el mapeo persistente, incluso si la conversación remota ya no
   existe.
4. Limpiar el estado efímero de interfaz.
5. Responder: `Listo. Empezamos un hilo nuevo. Escribe tu pregunta.`

La operación debe ser idempotente: repetir `/nuevo` no debe producir error ni
recuperar contexto anterior. Si OpenAI no está disponible, no se confirmará el
borrado como exitoso; se dejará una marca de borrado pendiente para reintento y
se impedirá reutilizar el ID anterior.

### 5. Pruebas

Agregar pruebas unitarias y de integración para:

- creación y reutilización de un ID de conversación por chat de Teams;
- aislamiento entre dos chats y entre tenants;
- continuidad después de reiniciar el proceso del backend;
- seguimiento documental: referencias como “esa versión”, “lo anterior” y
  “esos documentos”;
- `/nuevo` elimina el mapeo y el siguiente mensaje crea un hilo distinto;
- repetición de `/nuevo` y recuperación ante un borrado remoto ya ejecutado;
- rechazo de solicitudes sensibles antes de persistirlas;
- indisponibilidad de Azure Table Storage, OpenAI o un proveedor incompatible;
- límite de contexto, compactación y métricas de tokens/latencia;
- regresión de evidencia, enlaces y respuestas sin respaldo.

La validación manual debe cubrir Web Chat y el chat personal de Teams con una
conversación existente, un chat nuevo y una sesión posterior a reiniciar
`app-libras-prod`.

### 6. Despliegue y reversión

1. Desplegar el backend `0.1.4` con la bandera apagada.
2. Validar salud, conectividad a Azure Table Storage y credenciales de OpenAI.
3. Activar la bandera para una audiencia de piloto y ejecutar la matriz de
   pruebas.
4. Supervisar errores, latencia, uso de tokens, fallos de borrado y calidad de
   evidencia.
5. Si hay regresión, apagar `USE_OPENAI_CONVERSATIONS`; el flujo actual vuelve
   a funcionar sin tocar el paquete de Teams.

## Criterios de aceptación

- Todo mensaje de un mismo chat personal usa la misma conversación de OpenAI.
- El contexto sobrevive un reinicio del backend.
- Ningún chat puede leer el contexto de otro chat o tenant.
- `/nuevo` deja el hilo sin contexto y elimina el objeto remoto asociado.
- Las respuestas documentales conservan evidencia y enlaces autorizados.
- No se envían ni registran solicitudes bloqueadas por las políticas de
  seguridad.
- El paquete de Teams sigue en `0.1.0` y no se solicita nueva aprobación.

## Referencias

- [Estado de conversación de OpenAI](https://developers.openai.com/api/docs/guides/conversation-state)
- [Retención y controles de datos de OpenAI](https://developers.openai.com/api/docs/guides/your-data#storage-requirements-and-retention-controls-per-endpoint)
