# Plan Detallado De Implementacion Del Bot De Autoservicio En Teams

## 1. Objetivo

Construir un bot de autoservicio para Microsoft Teams, desplegado primero en un entorno de desarrollo aislado, capaz de responder preguntas operativas y tecnicas con base en evidencia proveniente de documentos, tickets activos y casos historicos.

La solucion debe permitir responder, como minimo, en estos escenarios:

- `resuelto`: el problema ya esta documentado o corregido.
- `en_progreso`: el problema ya fue reportado y tiene seguimiento activo.
- `similar_del_pasado`: no hay caso activo igual, pero si antecedentes utiles.
- `sin_evidencia`: no hay respaldo suficiente para responder con confianza.

La meta del MVP es reducir interrupciones directas al equipo de desarrollo y dar respuestas consistentes, trazables y seguras.

## 2. Estado Actual Del Proyecto

Hoy el proyecto ya cuenta con una base funcional en Teams y Python:

- Proyecto base generado con `Microsoft 365 Agents Toolkit`.
- Backend en Python con `microsoft-agents-hosting-aiohttp`.
- Archivo principal del bot en [src/agent.py](C:/aseinfo_bot/Aseinfo_bot/src/agent.py:1).
- Host HTTP en [src/app.py](C:/aseinfo_bot/Aseinfo_bot/src/app.py:1).
- Configuracion base en [src/config.py](C:/aseinfo_bot/Aseinfo_bot/src/config.py:1).
- Manifest de Teams en [appPackage/manifest.json](C:/aseinfo_bot/Aseinfo_bot/appPackage/manifest.json:1).
- Prueba local funcional en `Microsoft 365 Agents Playground`.
- Entorno Python corregido a `3.11.x`.

Limitaciones actuales:

- El bot actual solo reenvia el mensaje a OpenAI.
- No existe busqueda documental ni clasificacion formal.
- No hay integracion con ClickUp ni Jira.
- No hay observabilidad real, manejo de secretos robusto ni control de acceso.
- El manifest y branding siguen en modo plantilla.

## 3. Principios De Implementacion

- Desarrollar primero en `Microsoft 365 Developer tenant`.
- Usar recursos de Azure separados para `dev` y luego `prod`.
- No publicar en el tenant oficial hasta cerrar el piloto.
- No permitir respuestas sin evidencia cuando el caso requiera trazabilidad.
- Mantener el proyecto actual como shell de Teams y evolucionarlo, no reiniciarlo.

## 4. Arquitectura Objetivo

### 4.1 Componentes

- `Teams App`: interfaz y canal de conversacion para usuarios.
- `App Service`: backend del bot en Python.
- `OpenAI API`: generacion y estructuracion de respuestas.
- `Azure AI Search`: indexacion y recuperacion documental para el MVP.
- `Azure Key Vault`: secretos y credenciales.
- `Application Insights`: logs, errores, trazas y auditoria basica.
- `ClickUp API`: fuente de tickets activos o recientes.
- `Jira API`: fuente historica de incidentes y casos cerrados.

### 4.2 Flujo De Alto Nivel

1. Usuario hace una pregunta en Teams.
2. El bot normaliza la consulta.
3. El backend busca evidencia en documentos indexados.
4. Si aplica, consulta tickets activos en ClickUp.
5. Si aplica, consulta historial en Jira.
6. El backend construye un contexto de evidencia.
7. OpenAI clasifica el caso y genera una respuesta estructurada.
8. El bot responde al usuario con:
   - estado,
   - confianza,
   - evidencia,
   - siguiente accion.
9. La consulta y sus fuentes quedan registradas en logs.

## 5. Ruta De Implementacion

## Fase 0. Cierre Funcional Del MVP

### Objetivo

Definir con precision que resuelve el MVP y que queda fuera.

### Tareas

- Definir usuarios iniciales:
  - operaciones,
  - soporte,
  - desarrollo,
  - otros.
- Definir tipo de preguntas objetivo.
- Definir casos fuera de alcance del MVP.
- Definir tono del bot:
  - directo,
  - tecnico,
  - sin improvisar.
- Definir formato de respuesta al usuario.
- Definir reglas de escalamiento cuando no exista evidencia.

### Entregables

- Documento corto de alcance.
- Lista de preguntas prioritarias.
- Politica de respuestas y escalamiento.

### Criterio De Salida

Existe una lista cerrada de casos que el MVP debe resolver y un criterio explicito de cuando responder `sin_evidencia`.

## Fase 1. Preparar Entorno De Desarrollo Real

### Objetivo

Montar un entorno aislado para no depender del tenant oficial.

### Tareas

- Crear o habilitar `Microsoft 365 Developer tenant`.
- Confirmar cuenta de prueba con permisos de `custom app upload`.
- Definir suscripcion o grupo de recursos de Azure para `dev`.
- Confirmar cuenta y consumo de `OpenAI API`.
- Definir convenciones de nombres para recursos:
  - `aseinfo-bot-dev-*`
  - `aseinfo-bot-prod-*`
- Confirmar version de Python `3.11.x`.
- Confirmar variables de entorno necesarias para `local`, `dev` y `prod`.

### Entregables

- Tenant de Microsoft 365 de desarrollo listo.
- Azure de prueba listo.
- Variables por entorno definidas.

### Criterio De Salida

Se puede instalar y probar la app en el tenant de desarrollo sin tocar el tenant oficial.

## Fase 2. Limpiar Y Profesionalizar La Base Actual

### Objetivo

Convertir la plantilla generica en una base real del proyecto ASEINFO.

### Tareas

- Cambiar nombre corto y nombre largo en [appPackage/manifest.json](C:/aseinfo_bot/Aseinfo_bot/appPackage/manifest.json:1).
- Actualizar:
  - `developer.name`
  - `websiteUrl`
  - `privacyUrl`
  - `termsOfUseUrl`
  - descripciones
- Sustituir saludo generico del bot.
- Reemplazar `system_prompt` generico.
- Definir branding minimo:
  - `color.png`
  - `outline.png`
- Revisar comandos expuestos en el manifest.
- Crear un README interno del proyecto con su objetivo real.

### Entregables

- Bot con nombre y descripcion reales.
- Prompt base alineado al caso de negocio.
- Manifest listo para entorno dev.

### Criterio De Salida

El bot deja de verse como plantilla y ya se presenta como asistente de autoservicio ASEINFO.

## Fase 3. Diseno Tecnico Del MVP

### Objetivo

Definir la estructura del backend y del pipeline de respuesta.

### Tareas

- Separar la logica en modulos:
  - `handler`
  - `retrieval`
  - `classification`
  - `formatting`
  - `logging`
- Definir esquema de respuesta estructurada.
- Definir politica de confianza.
- Definir cuando se consulta:
  - solo documental,
  - documental + ClickUp,
  - documental + Jira,
  - todas las fuentes.
- Definir modelo OpenAI a usar por entorno.
- Definir estrategia para manejo de errores.

### Entregables

- Diseno de componentes.
- Esquema de respuesta.
- Politica de confianza y escalamiento.

### Criterio De Salida

Existe una especificacion suficiente para codificar sin ambiguedad.

## Fase 4. MVP Documental

### Objetivo

Responder preguntas usando solo documentos base con evidencia.

### Fuentes Iniciales

- setups,
- readmes,
- changelogs,
- notas de despliegue,
- notas de hotfix.

### Tareas

- Recolectar un lote inicial de documentos.
- Limpiar y normalizar formatos.
- Definir estrategia de fragmentacion:
  - tamano de chunk,
  - traslape,
  - metadatos.
- Crear proceso de indexacion documental.
- Subir contenido a `Azure AI Search`.
- Implementar consulta de recuperacion.
- Inyectar evidencia recuperada al prompt.
- Responder con fuente y cita minima.

### Entregables

- Pipeline de indexacion documental.
- Consulta documental integrada al bot.
- Respuestas con evidencia.

### Criterio De Salida

Una pregunta del usuario puede contestarse con base en uno o varios documentos reales, indicando la fuente utilizada.

## Fase 5. Clasificacion Formal De Respuestas

### Objetivo

Estandarizar la salida del bot y evitar respuestas ambiguas.

### Estructura Interna Minima

```json
{
  "estado": "resuelto | en_progreso | similar_del_pasado | sin_evidencia",
  "confianza": "alta | media | baja",
  "fuentes": [
    {
      "tipo": "documento | clickup | jira | diff",
      "titulo": "string",
      "ubicacion": "string",
      "fragmento": "string"
    }
  ],
  "ticket_relacionado": "string | null",
  "version_relacionada": "string | null",
  "respuesta_usuario": "string",
  "siguiente_accion": "string"
}
```

### Tareas

- Diseñar plantilla de salida del modelo.
- Definir reglas para cada estado.
- Impedir que el modelo invente tickets, versiones o fuentes.
- Definir mensajes estandarizados por estado.
- Mostrar solo lo necesario al usuario y guardar el resto para trazabilidad.

### Entregables

- Clasificacion implementada.
- Respuesta estructurada.
- Politica de no improvisacion.

### Criterio De Salida

Cada respuesta del bot cae en una categoria valida y tiene evidencia trazable.

## Fase 6. Integracion Con ClickUp

### Objetivo

Detectar si un problema ya esta reportado y en atencion.

### Tareas

- Identificar workspace, espacios y listas relevantes.
- Definir autenticacion segura para ClickUp.
- Implementar cliente de solo lectura.
- Buscar tickets por:
  - palabras clave,
  - modulo,
  - pantalla,
  - estado,
  - fechas.
- Definir ranking de coincidencia.
- Construir respuesta para `en_progreso`.

### Entregables

- Integracion ClickUp de lectura.
- Respuestas con ticket relacionado y estado.

### Criterio De Salida

El bot puede responder que un caso ya esta reportado, incluyendo ticket y estado con respaldo real.

## Fase 7. Integracion Con Jira Historico

### Objetivo

Aprovechar el historial para responder con antecedentes utiles.

### Tareas

- Identificar proyectos y tipos de issue relevantes.
- Definir autenticacion segura para Jira.
- Implementar cliente de solo lectura.
- Recuperar casos cerrados o resueltos.
- Permitir busqueda por similitud y por terminos.
- Enriquecer la salida `similar_del_pasado`.

### Entregables

- Integracion Jira.
- Respuestas con historial relacionado.

### Criterio De Salida

El bot puede citar antecedentes historicos de forma util y concreta.

## Fase 8. Enriquecimiento Con Diffs Y Cambios Recientes

### Objetivo

Usar cambios recientes como evidencia tecnica secundaria.

### Tareas

- Identificar fuente de diffs:
  - repositorio Git,
  - despliegues,
  - changelog tecnico.
- Definir un proceso de consulta de cambios recientes.
- Relacionar cambios con modulos o pantallas.
- Usar esta fuente solo como evidencia secundaria.

### Entregables

- Estrategia de correlacion con cambios recientes.

### Criterio De Salida

El bot puede sugerir si hubo cambios recientes relacionados, sin convertir eso en evidencia principal salvo respaldo adicional.

## Fase 9. Seguridad, Observabilidad Y Operacion

### Objetivo

Asegurar que el bot sea trazable, controlado y seguro antes del piloto.

### Tareas

- Mover secretos a `Key Vault`.
- Configurar `Application Insights`.
- Registrar:
  - consulta,
  - estado calculado,
  - confianza,
  - fuentes usadas,
  - error si existe.
- Ocultar secretos y datos sensibles en logs.
- Definir quienes pueden usar el bot.
- Definir reglas para no exponer informacion sensible.
- Definir timeouts y manejo de fallos externos.

### Entregables

- Telemetria basica.
- Politica de seguridad.
- Auditoria minima de uso.

### Criterio De Salida

La solucion ya es apta para un piloto controlado.

## Fase 10. Piloto Controlado En Tenant De Desarrollo

### Objetivo

Validar utilidad, precision y experiencia de usuario.

### Tareas

- Seleccionar grupo pequeno de usuarios.
- Definir casos reales de prueba.
- Medir:
  - precision,
  - utilidad,
  - tiempos de respuesta,
  - frecuencia de `sin_evidencia`.
- Ajustar prompts, pesos y reglas.
- Documentar hallazgos.

### Entregables

- Informe de piloto.
- Lista de mejoras pendientes.

### Criterio De Salida

El piloto demuestra valor suficiente y no presenta riesgos graves para una salida controlada.

## Fase 11. Paso A Tenant Oficial

### Objetivo

Promover la solucion solo cuando este lista.

### Tareas

- Replicar configuracion de Azure para `prod`.
- Replicar configuracion de Teams para `prod`.
- Validar secretos y permisos.
- Generar app package final.
- Coordinar con admin de Teams:
  - carga del paquete,
  - instalacion,
  - permisos,
  - politica de acceso.
- Preparar soporte inicial posterior a salida.

### Entregables

- Checklist de salida a produccion.
- App instalada en Teams oficial.

### Criterio De Salida

La app queda publicada en el tenant oficial con soporte inicial y control de cambios.

## 6. Backlog Tecnico Del Proyecto

## 6.1 Estructura De Codigo Recomendada

Se recomienda evolucionar `src/` hacia una estructura como esta:

```text
src/
  app.py
  agent.py
  config.py
  models/
    response_schema.py
  services/
    retrieval.py
    classifier.py
    clickup_client.py
    jira_client.py
    logging_service.py
  scripts/
    ingest_documents.py
    reindex_documents.py
  prompts/
    system_prompt.txt
    classification_prompt.txt
```

## 6.2 Cambios Por Archivo

### [src/agent.py](C:/aseinfo_bot/Aseinfo_bot/src/agent.py:1)

- Reemplazar llamada directa libre a OpenAI.
- Agregar pipeline:
  - recibir mensaje,
  - recuperar evidencia,
  - clasificar,
  - formatear salida,
  - responder.
- Agregar manejo de errores por paso.

### [src/config.py](C:/aseinfo_bot/Aseinfo_bot/src/config.py:1)

Agregar configuraciones para:

- `OPENAI_MODEL_NAME`
- `AZURE_SEARCH_ENDPOINT`
- `AZURE_SEARCH_KEY`
- `AZURE_SEARCH_INDEX_NAME`
- `APPINSIGHTS_CONNECTION_STRING`
- `CLICKUP_API_KEY`
- `CLICKUP_WORKSPACE_ID`
- `JIRA_BASE_URL`
- `JIRA_USER`
- `JIRA_API_TOKEN`

### [appPackage/manifest.json](C:/aseinfo_bot/Aseinfo_bot/appPackage/manifest.json:1)

- Cambiar nombre y descripciones.
- Revisar comandos sugeridos.
- Ajustar branding.
- Revisar permisos.

### `infra/`

- Agregar o planificar:
  - Key Vault,
  - Application Insights,
  - Azure AI Search.

## 7. Diseño De Respuesta Del Bot

## 7.1 Formato Visible Para El Usuario

La respuesta final del bot debe ser simple, pero estructurada. Ejemplo:

```text
Estado: Resuelto
Confianza: Alta

Resumen:
El error ya aparece documentado en el setup del modulo de facturacion.

Evidencia:
- setup_facturacion_v2.md
- changelog_2026_06_18.md

Siguiente accion:
Aplicar el ajuste indicado en el setup y volver a probar.
```

## 7.2 Regla De No Improvisacion

Si el bot no tiene evidencia suficiente:

- no inventa estados,
- no inventa tickets,
- no inventa versiones,
- responde `sin_evidencia`,
- sugiere escalamiento.

## 8. Entornos

## 8.1 Local

Uso:

- desarrollo rapido,
- Playground,
- validacion tecnica.

## 8.2 Dev

Uso:

- tenant Microsoft 365 Developer,
- App Service dev,
- Search dev,
- Key Vault dev,
- piloto controlado.

## 8.3 Prod

Uso:

- tenant oficial,
- recursos Azure productivos,
- controles reforzados.

## 9. Checklists Operativos

## 9.1 Checklist Del MVP Documental

- Proyecto base levanta en Playground.
- Branding base actualizado.
- Prompt base definido.
- Documentos base recolectados.
- Indice documental creado.
- Recuperacion documental funcional.
- Respuesta con evidencia lista.
- Clasificacion inicial implementada.
- Logs basicos activos.

## 9.2 Checklist Antes De ClickUp

- MVP documental estable.
- Reglas de `sin_evidencia` validadas.
- Formato de respuesta estable.
- Telemetria funcional.

## 9.3 Checklist Antes Del Piloto

- Secrets fuera del codigo.
- Logs y errores visibles.
- Tenant dev operativo.
- Usuarios piloto definidos.
- Casos reales de prueba listos.

## 9.4 Checklist Antes De Produccion

- Tenant oficial listo.
- Bot validado en tenant dev.
- Prompt estabilizado.
- Integraciones validadas.
- Politica de acceso acordada.
- Checklist de soporte inicial cerrado.

## 10. Sprints Recomendados

## Sprint 1. Base Del Proyecto Real

Objetivo:

Dejar la plantilla convertida en bot ASEINFO y con diseno tecnico listo.

Trabajo:

- actualizar manifest,
- definir prompt,
- definir esquema de respuesta,
- preparar arquitectura y backlog,
- preparar tenant dev y Azure dev.

Salida:

- bot con identidad real,
- roadmap tecnico listo,
- entornos definidos.

## Sprint 2. MVP Documental

Objetivo:

Responder preguntas con evidencia documental.

Trabajo:

- reunir documentos,
- indexar,
- recuperar,
- responder con citas,
- clasificar `resuelto` y `sin_evidencia`.

Salida:

- primer bot util para consultas reales.

## Sprint 3. Clasificacion Y Endurecimiento

Objetivo:

Estabilizar el comportamiento del bot.

Trabajo:

- mejorar confianza,
- mejorar mensajes,
- agregar logs,
- agregar manejo de errores.

Salida:

- MVP apto para piloto tecnico.

## Sprint 4. ClickUp Y Jira

Objetivo:

Ampliar el bot con estado operativo y antecedentes.

Trabajo:

- integracion ClickUp,
- integracion Jira,
- ajuste del pipeline.

Salida:

- bot con mayor valor operativo.

## Sprint 5. Piloto Y Preparacion De Produccion

Objetivo:

Validar con usuarios y dejar lista la promocion.

Trabajo:

- piloto,
- ajustes finales,
- checklist de produccion,
- coordinacion con admin.

Salida:

- app lista para Teams oficial.

## 11. Riesgos Principales

- Falta de permisos en Teams oficial para pruebas tempranas.
- Documentacion base incompleta o desactualizada.
- Respuestas con baja precision si la indexacion es pobre.
- Exceso de confianza del modelo sin respaldo suficiente.
- Integraciones externas con ClickUp o Jira sin permisos o con limites de API.
- Exposicion accidental de datos sensibles si no se filtran logs y fuentes.

## 12. Mitigaciones

- Probar primero en `Microsoft 365 Developer tenant`.
- Limitar el MVP a fuentes documentales conocidas.
- Forzar `sin_evidencia` cuando la recuperacion sea debil.
- Registrar todas las fuentes usadas para auditoria.
- Integrar sistemas externos inicialmente en modo solo lectura.
- Revisar seguridad antes del piloto.

## 13. Proximo Paso Inmediato

El siguiente paso recomendado es ejecutar `Sprint 1` con este orden exacto:

1. Actualizar [appPackage/manifest.json](C:/aseinfo_bot/Aseinfo_bot/appPackage/manifest.json:1) con branding real.
2. Reescribir el `system_prompt` del bot en [src/agent.py](C:/aseinfo_bot/Aseinfo_bot/src/agent.py:1).
3. Definir el esquema estructurado de respuesta.
4. Preparar lista inicial de documentos para indexar.
5. Decidir si el MVP usara `Azure AI Search` como indice documental.
6. Crear el esqueleto de modulos `retrieval`, `classifier` y `logging`.

## 14. Definicion De Exito

La iniciativa se considera exitosa si:

- el bot responde desde Teams con evidencia real,
- clasifica correctamente casos resueltos, en progreso o similares,
- reduce consultas directas al equipo,
- puede operar en tenant de desarrollo sin afectar produccion,
- y llega al tenant oficial solo despues de un piloto validado.
