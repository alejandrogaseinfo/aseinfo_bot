# Plan de Avance - Chat-Salvador

## Objetivo

Llegar a la reunión de seguimiento con un avance demostrable del flujo de investigación del bot, sin esperar a completar todas las integraciones.

La prioridad inmediata es demostrar que Chat-Salvador puede consultar ClickUp, recuperar información relacionada y presentar evidencia trazable al usuario.

## Resultado esperado para la reunión

El bot debe poder demostrar este flujo:

1. El usuario realiza una consulta sobre un error o caso operativo.
2. El bot consulta ClickUp.
3. Encuentra una tarea relacionada.
4. Muestra título, estado, responsable, descripción y enlace.
5. Indica la ruta de investigación utilizada.
6. Informa que Jira está pendiente por falta de acceso.
7. Informa que los READMEs se incorporarán posteriormente al Vector Store.

## Fases

### Fase 1 - Validar ClickUp como fuente activa

**Estado:** Validada

**Objetivo:** Confirmar una consulta real que devuelva información relevante desde ClickUp.

**Actividades:**

- Identificar una tarea real relacionada con un error, módulo, pantalla o hotfix.
- Probar una consulta con términos que existan en el título o descripción.
- Confirmar que se recuperan título, estado, responsables, descripción y URL.
- Confirmar que la consulta no expone tokens ni datos de configuración.
- Registrar el caso de prueba utilizado para la demo.

**Criterio de aceptación:**

Una consulta en Teams devuelve al menos una tarea real de ClickUp como evidencia y permite abrir el enlace correspondiente.

**Validación realizada:**

Consulta probada: `ruta de investigacion`

La integración devolvió tres tareas reales de la lista `Investigación`:

- `Investigacion sobre nuevos modelos de Open AI` - estado `en progreso`
  - https://app.clickup.com/t/86bavuwk8
- `Investigacion de las herramientas (headroom, grapify, ponytail)` - estado `completado`
  - https://app.clickup.com/t/86baqavm8
- `Definicion de los requerimientos de la investigacion` - estado `completado`
  - https://app.clickup.com/t/86bapqz25

También se validó que la respuesta recupera la lista, el estado, el responsable, el texto disponible de la tarea y la URL directa.

### Fase 2 - Hacer visible la ruta de investigación

**Estado:** Implementada

**Objetivo:** Que el usuario y la audiencia de la reunión entiendan qué fuentes revisa el bot.

**Actividades:**

- Mostrar explícitamente `Fuente: ClickUp`.
- Mostrar estado, responsable, descripción y enlace de la tarea.
- Agregar una sección `Ruta de investigación`.
- Indicar cuando Jira no está configurado.
- Indicar cuando la búsqueda continúa en la base documental o el índice local.

**Ruta inicial:**

```text
ClickUp -> Jira histórico -> Vector Store -> Base documental local
```

**Criterio de aceptación:**

La respuesta permite explicar visualmente qué fuente produjo la evidencia y cuáles fuentes siguen pendientes.

**Implementación realizada:**

- Se agregó la sección `Ruta de investigación` a la respuesta.
- Se identifican ClickUp, Jira, Vector Store y base documental local.
- Los enlaces HTTP de las evidencias se muestran como enlaces accionables.
- Jira se muestra como `pendiente de acceso` cuando no hay credenciales configuradas.
- ClickUp muestra si hubo evidencia encontrada o si fue consultado sin coincidencias.

### Fase 3 - Ingestar documentación de setups y hotfixes

**Estado:** Implementada

**Objetivo:** Usar como fuente principal los documentos que ya acompañan a los setups y hotfixes, incluyendo READMEs, advertencias, instrucciones y changelogs.

**Actividades:**

- Mantener `docs/knowledge-base` como staging técnico de los documentos de entrega.
- Extraer documentos desde una carpeta o ZIP de setup/hotfix.
- Agregar metadatos de producto, versión, entrega y archivo de origen.
- Priorizar estos documentos como evidencia primaria.
- Documentar el flujo Setup/Hotfix -> Vector Store.

**Fuera de alcance para el lunes:**

- Automatizar la lectura desde la ubicación definitiva de los setups.
- Resolver permisos de la fuente operativa.
- Automatizar sincronizaciones periódicas.

**Criterio de aceptación:**

Existe una ruta clara para incorporar documentos desde setups/hotfixes sin modificar la arquitectura principal.

**Implementación realizada:**

- Se agregó `src/setup_ingest.py` para importar carpetas o ZIPs de setups/hotfixes.
- Se agregan metadatos de producto, versión y archivo de origen.
- Se documentó la prioridad de setups/hotfixes sobre fuentes complementarias.
- Se dejó explícita la dependencia de la ubicación real donde se almacenan las entregas.
- Se incorporó el changelog real de Evolution Connect como primera fuente técnica disponible.

**Documento agregado:**

`docs/knowledge-base/changelog_evolution_connect_2026_07_08.md`

### Fase 4 - Formalizar Jira como dependencia bloqueada

**Estado:** Bloqueada por acceso externo

**Objetivo:** Dejar claro que la integración está prevista, pero no puede validarse todavía.

**Actividades:**

- Mantener el módulo inicial `jira_retrieval.py`.
- Documentar que faltan dominio, proyecto, usuario técnico y API token.
- No inventar resultados de Jira en la demo.
- Preparar una lista de datos requeridos para activar la integración.

**Criterio de aceptación:**

La reunión puede explicar con precisión qué está implementado, qué falta y qué acceso se necesita para continuar.

### Fase 5 - Mejorar clasificación y evidencia

**Estado:** Pendiente posterior a la demo

**Objetivo:** Evitar que cualquier coincidencia de ClickUp se interprete automáticamente como una solución confirmada.

**Actividades:**

- Diferenciar tarea activa, tarea cerrada y antecedente.
- Ajustar los estados `resuelto`, `en_progreso` y `similar_del_pasado`.
- Mejorar el ranking de coincidencias.
- Agregar pruebas con respuestas simuladas de ClickUp.

**Criterio de aceptación:**

El bot clasifica la evidencia de ClickUp de forma consistente y prudente.

### Fase 6 - Escalamiento y feedback

**Estado:** Backlog posterior

**Objetivo:** Incorporar interacción humana después de validar la ruta de investigación.

**Actividades futuras:**

- Adaptive Cards.
- Botón “Me sirvió”.
- Botón “Sugerir corrección”.
- Creación de tickets de revisión.
- Notificación proactiva a soporte.

Estas funcionalidades no son necesarias para la demostración inicial del lunes.

## Guion de demo

### Caso positivo

1. Escribir una consulta que coincida con una tarea real de ClickUp.
2. Mostrar la respuesta del bot.
3. Señalar la fuente, el estado, el responsable y el enlace.
4. Explicar que ClickUp representa la fuente activa disponible.

### Caso sin evidencia

1. Escribir una consulta que no coincida con ninguna tarea.
2. Mostrar `sin_evidencia`.
3. Explicar que el bot no inventa una respuesta.
4. Mostrar que Jira y los READMEs son las siguientes fuentes por habilitar.

## Mensaje para la reunión

> El chat ya tiene funcionando la ruta de investigación con ClickUp. Puede recibir una consulta, buscar tareas relacionadas y devolver la evidencia con estado, responsable y enlace. La integración con Jira está pendiente porque todavía no tenemos acceso. También falta recibir los READMEs reales de los repositorios; cuando estén disponibles se agregarán a la base documental y al Vector Store. En esta etapa estamos validando la calidad de la búsqueda y la trazabilidad de las respuestas.

## Orden de trabajo

No avanzar a la siguiente fase hasta cumplir el criterio de aceptación de la fase actual.

1. Validar ClickUp con un caso real.
2. Hacer visible la ruta de investigación.
3. Preparar la entrada de READMEs.
4. Documentar Jira como dependencia.
5. Mejorar clasificación y pruebas.
6. Implementar feedback y escalamiento proactivo.
