# Estado Actual Del MVP - Chat-Salvador

## 1. Objetivo De Este Documento

Este documento resume el estado actual del MVP del bot `Chat-Salvador`, construido sobre Microsoft Teams y Python, para que pueda explicarse con claridad en una demo interna.

El objetivo es dejar documentado:

- que se ha construido hasta el momento,
- por que se tomo esta direccion tecnica,
- que ya funciona,
- que todavia no esta implementado,
- y cual deberia ser el siguiente paso del proyecto.

## 2. Resumen Ejecutivo

Ya existe un primer MVP funcional del bot dentro del flujo de Microsoft Teams / Microsoft 365 Agents Playground.

Este MVP ya puede:

- recibir una consulta del usuario,
- buscar evidencia en una base documental local,
- clasificar el caso en una categoria operativa,
- y responder con una salida estructurada, formal y trazable.

Todavia no es un producto final ni un piloto listo para usuarios reales, pero ya es una base demostrable y tecnicamente correcta para evolucionar hacia:

- integracion con documentacion real,
- integracion con ClickUp,
- integracion con Jira,
- y posteriormente Azure AI Search.

## 3. Que Se Queria Resolver

El problema original del proyecto es que muchas consultas operativas y tecnicas llegan al equipo de desarrollo aunque varias de ellas:

- ya estan documentadas en setups o readmes,
- ya tienen advertencias conocidas,
- ya tienen antecedentes en errores pasados,
- o deberian poder filtrarse antes de convertirse en escalamiento tecnico.

La idea del MVP es reducir interrupciones innecesarias y responder de forma consistente, prudente y basada en evidencia.

## 4. Enfoque General Que Se Tomo

En lugar de intentar resolver todo desde el principio con Azure, ClickUp, Jira y automatizaciones complejas, se decidio construir el proyecto por capas.

La razon de hacerlo asi fue tecnica y estrategica:

- primero habia que dejar claro que preguntas iba a responder el bot,
- luego habia que convertir la plantilla de Teams en un bot real del proyecto,
- despues habia que definir un pipeline interno ordenado,
- y solo entonces tenia sentido conectar fuentes reales.

Este enfoque evita dos errores comunes:

1. integrar demasiadas cosas antes de tener clara la logica del bot,
2. y depender por completo del modelo antes de tener reglas de respaldo y trazabilidad.

## 5. Fases Que Ya Se Han Trabajado

## 5.1 Fase 0 - Definicion Del MVP

La Fase 0 ya fue cerrada y documentada.

Se definio:

- que casos de uso principales debe cubrir el bot,
- que cosas quedan fuera de alcance,
- como debe responder,
- y cuando debe devolver `sin_evidencia`.

Documentos creados:

- [docs/fase-0-alcance-mvp.md](C:/aseinfo_bot/Aseinfo_bot/docs/fase-0-alcance-mvp.md:1)
- [docs/preguntas-prioritarias-mvp.md](C:/aseinfo_bot/Aseinfo_bot/docs/preguntas-prioritarias-mvp.md:1)
- [docs/politica-respuesta-escalamiento.md](C:/aseinfo_bot/Aseinfo_bot/docs/politica-respuesta-escalamiento.md:1)

Esto fue importante porque permitio fijar desde el inicio el comportamiento esperado del bot y evitar que respondiera sin criterio.

## 5.2 Fase 2 - Profesionalizacion De La Base Actual

La plantilla generica de Microsoft 365 Agents Toolkit fue convertida en una base real del proyecto.

Se hicieron estos cambios:

- se definio el nombre `Chat-Salvador`,
- se configuro el bot como `Asistente de Base de Conocimiento y Resolucion de Errores`,
- se actualizaron nombre, descripcion y comandos del manifest,
- se ajusto el tono del bot a espanol formal,
- y se dejo branding base con color verde.

Archivo principal impactado:

- [appPackage/manifest.json](C:/aseinfo_bot/Aseinfo_bot/appPackage/manifest.json:1)

Tambien se actualizo el README del proyecto para que ya no parezca una plantilla:

- [README.md](C:/aseinfo_bot/Aseinfo_bot/README.md:1)

## 5.3 Fase 3 - Diseno Tecnico Del MVP

Se reestructuro el backend para salir del esquema inicial de "un archivo que manda todo a OpenAI".

Se creo una arquitectura modular sencilla pero correcta:

- [src/agent.py](C:/aseinfo_bot/Aseinfo_bot/src/agent.py:1): punto de entrada del bot
- [src/handler.py](C:/aseinfo_bot/Aseinfo_bot/src/handler.py:1): orquestacion de la consulta
- [src/retrieval.py](C:/aseinfo_bot/Aseinfo_bot/src/retrieval.py:1): recuperacion de evidencia
- [src/document_index.py](C:/aseinfo_bot/Aseinfo_bot/src/document_index.py:1): indexacion documental local
- [src/classification.py](C:/aseinfo_bot/Aseinfo_bot/src/classification.py:1): clasificacion del caso
- [src/formatting.py](C:/aseinfo_bot/Aseinfo_bot/src/formatting.py:1): construccion de la respuesta al usuario
- [src/logging_utils.py](C:/aseinfo_bot/Aseinfo_bot/src/logging_utils.py:1): logging base
- [src/models.py](C:/aseinfo_bot/Aseinfo_bot/src/models.py:1): modelos internos
- [src/config.py](C:/aseinfo_bot/Aseinfo_bot/src/config.py:1): configuracion del proyecto

### Por Que Se Hizo Asi

Se hizo asi porque el proyecto necesita crecer despues hacia multiples fuentes y reglas de decision, y eso no era sostenible si toda la logica quedaba mezclada en un solo archivo.

Esta arquitectura ya deja preparada la evolucion hacia:

- Azure AI Search,
- ClickUp,
- Jira,
- reglas de confianza,
- y futura curacion de respuestas.

## 5.4 Fase 4 - MVP Documental Inicial

La Fase 4 no esta cerrada, pero ya fue iniciada con una primera implementacion funcional.

Se construyo una base documental local en Markdown:

- [docs/knowledge-base](C:/aseinfo_bot/Aseinfo_bot/docs/knowledge-base:1)

Se agregaron documentos de ejemplo para probar el comportamiento del bot:

- un hotfix de nomina,
- un documento de limites de vistas customizadas,
- y un antecedente historico de error Oracle.

La indexacion documental local hace lo siguiente:

- carga documentos `.md`,
- los divide por bloques o fragmentos,
- normaliza terminos,
- compara la consulta del usuario contra los fragmentos,
- y devuelve la evidencia mas relevante.

### Por Que Se Hizo Asi

No se conecto Azure AI Search desde el inicio porque eso hubiera mezclado demasiadas cosas al mismo tiempo:

- infraestructura,
- indexacion,
- acceso a documentos reales,
- y comportamiento del bot.

Primero convenia demostrar que el flujo funcional si tenia sentido con una base documental local controlada.

## 6. Manejo De Secretos

Se corrigio el manejo de la clave de OpenAI.

Antes, la clave estaba operativamente en `/.env`, lo cual no era la mejor practica para este proyecto.

Ahora el bot esta preparado para tomar la clave desde archivos seguros por entorno:

- `env/.env.local.user`
- `env/.env.dev.user`
- `env/.env.playground.user`

Adicionalmente, [src/agent.py](C:/aseinfo_bot/Aseinfo_bot/src/agent.py:1) ya carga esos archivos al arrancar y [src/config.py](C:/aseinfo_bot/Aseinfo_bot/src/config.py:1) acepta:

- `OPENAI_API_KEY`
- o `SECRET_OPENAI_API_KEY`

Esto deja el proyecto mejor alineado con el funcionamiento del toolkit y con una futura migracion a Azure Key Vault o App Settings.

## 7. Comportamiento Del Bot Que Ya Existe

Hoy el bot ya sigue un flujo real:

1. el usuario escribe una consulta,
2. el sistema recupera evidencia documental,
3. intenta clasificar el caso,
4. formatea una respuesta estructurada,
5. y responde con trazabilidad.

## 7.1 Estados Soportados

Internamente el bot ya trabaja con estos estados:

- `resuelto`
- `en_progreso`
- `similar_del_pasado`
- `sin_evidencia`

## 7.2 Estructura De La Respuesta

La respuesta visible al usuario incluye:

- estado,
- confianza,
- resumen,
- evidencia,
- siguiente accion,
- escalamiento.

Esto es importante porque evita respuestas ambiguas y deja visible por que el bot esta diciendo lo que dice.

## 8. Problema Encontrado Durante La Prueba

Durante la primera prueba del Playground paso algo importante:

- el bot si recupero la evidencia correcta,
- pero la capa de clasificacion basada en OpenAI fallo,
- y el sistema cayo al fallback de seguridad.

Ese hallazgo fue util porque demostro dos cosas:

1. el retrieval estaba funcionando,
2. pero no podiamos depender completamente del modelo para clasificar algo que ya estaba claramente documentado.

## 9. Ajuste Que Se Hizo A Partir De Esa Prueba

Se implemento una clasificacion local de respaldo en [src/classification.py](C:/aseinfo_bot/Aseinfo_bot/src/classification.py:1).

### Que Hace Esa Clasificacion Local

Si la evidencia recuperada contiene señales suficientemente claras, el sistema puede clasificar sin depender del modelo.

Ejemplos:

- si encuentra instrucciones de correccion o advertencias claras, clasifica como `resuelto`,
- si encuentra señales de ticket activo o seguimiento, clasifica como `en_progreso`,
- si encuentra antecedente historico, clasifica como `similar_del_pasado`.

Luego [src/handler.py](C:/aseinfo_bot/Aseinfo_bot/src/handler.py:1):

- usa OpenAI si esta disponible,
- pero si el modelo falla, aplica reglas locales,
- y tambien puede sustituir un `sin_evidencia` del modelo por una clasificacion local mas solida si la evidencia realmente lo justifica.

### Por Que Se Hizo Asi

Porque en este tipo de bot no basta con "preguntarle al modelo". El sistema necesita comportamiento prudente, repetible y defendible cuando la evidencia documental ya es suficientemente clara.

## 10. Demo Que Ya Se Logro

Ya se logro una demo funcional en Microsoft 365 Agents Playground.

Caso probado:

- consulta sobre fallo despues de instalar un hotfix de nomina.

Resultado obtenido:

- el bot encontro evidencia documental,
- clasifico el caso como `resuelto`,
- dio una accion siguiente concreta,
- y no escalo innecesariamente.

Eso demuestra que el MVP ya puede resolver el flujo base de:

- pregunta,
- recuperacion documental,
- clasificacion,
- respuesta estructurada.

## 11. Que Ya Se Puede Decir En Una Demo

Una explicacion correcta del estado actual podria ser esta:

> Ya existe un primer MVP funcional del bot en Teams. El sistema ya no es una plantilla generica ni un simple chat con OpenAI. Hoy ya puede recibir una pregunta, buscar evidencia en una base documental local, clasificar el caso y responder con formato estructurado. Todavia no esta conectado a ClickUp, Jira ni Azure AI Search, pero la base tecnica ya esta lista para crecer hacia esas integraciones sin rehacer el proyecto.

## 12. Que Esta Pendiente

Estas son las piezas que aun no se han implementado o no se consideran cerradas.

## 12.1 Pendiente Inmediato

- cargar documentos reales del negocio,
- incorporar changelogs reales,
- y reemplazar documentos de ejemplo por evidencia operativa real.

## 12.2 Pendiente De Integracion

- ClickUp para tickets activos o recientes,
- Jira para historico de incidentes,
- Azure AI Search para indexacion y busqueda formal.

## 12.3 Pendiente Funcional

- curacion de respuestas por parte de consultor o desarrollador,
- mayor politica de confianza,
- observabilidad mas robusta,
- y endurecimiento de errores.

## 13. Que No Se Hizo Todavia Y Por Que

No se conecto ClickUp, Jira ni Azure AI Search todavia porque hacerlo en este punto hubiera mezclado demasiadas dependencias antes de tener probado el flujo base.

La decision fue:

- primero validar el comportamiento del bot,
- luego validar la recuperacion documental,
- despues cargar informacion real,
- y solo entonces conectar fuentes externas e infraestructura adicional.

Esto reduce riesgo tecnico y evita rehacer componentes.

## 14. Que Falta Para Pasar Del Demo Al Siguiente Nivel

Para avanzar con buen criterio, el siguiente bloque de trabajo deberia ser:

1. cargar readmes, setups y hotfixes reales,
2. incorporar changelogs reales como fuente documental,
3. validar mas consultas reales del negocio,
4. y luego integrar ClickUp y Jira.

## 15. Conclusion

El proyecto ya tiene una base funcional seria.

Lo construido hasta el momento no es solo "un chat bonito". Ya existe:

- una definicion funcional del MVP,
- una identidad real del bot,
- una arquitectura modular,
- un pipeline documental inicial,
- manejo de secretos mas correcto,
- clasificacion estructurada,
- y una demo validada en Playground.

Todavia falta la parte mas importante para convertirlo en una herramienta realmente util: cargar conocimiento real y conectar las fuentes operativas.

Pero la etapa actual ya demuestra que el enfoque tecnico funciona y que el proyecto va en una direccion correcta.
