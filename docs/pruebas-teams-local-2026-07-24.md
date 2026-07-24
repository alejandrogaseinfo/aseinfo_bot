# Pruebas locales de Libras con Teams

**Fecha:** 24 de julio de 2026
**Estado:** Preparación local verificada; ejecución HTTP/Teams pendiente.

### Bitácora de progreso

| Fecha | Actividad | Resultado | Siguiente acción |
|---|---|---|---|
| 24/07/2026 | Pruebas unitarias (`python -m unittest discover -s tests -v`) | Correcto: 39 pruebas, `OK` | Iniciar el backend y validar endpoints HTTP |
| 24/07/2026 | Preflight de plataforma (`python src\\preflight.py --stage platform`) | Correcto: modelo, Search, manifest, bot, scope personal e íconos | Ejecutar prueba local desde Agents Toolkit |
| 24/07/2026 | Lanzamiento automatizado del backend para validar `healthz/readyz` | Bloqueado por la política del entorno al crear un proceso persistente | Ejecutar `python src\\app.py` manualmente |
| 24/07/2026 | Microsoft 365 Agents Playground iniciado mediante ejecución local | Correcto: Libras aparece y responde al saludo; flujo básico Teams/Playground confirmado | Ejecutar consultas con evidencia, sin evidencia y ambiguas |
| 24/07/2026 | Consulta sobre cambios de Evolution Connect | Incorrecto: el chat solicitó autenticación y luego respondió sin evidencia; la recuperación directa local sí encuentra el documento | Reiniciar el backend y repetir con una consulta más directa; revisar logs |
| 24/07/2026 | Consulta directa sobre funcionalidades del changelog | Correcto: respondió con evidencia y declaró `Base documental local` | Continuar con consulta sin evidencia y consulta ambigua |
| 24/07/2026 | Solicitud de resumen del changelog | Parcial: recuperó información, pero la política la consideró insuficiente para confirmar una resolución activa | Revisar si el comportamiento es aceptable para preguntas informativas |
| 24/07/2026 | Autenticación en Playground | Observación: solicitó iniciar sesión nuevamente en cada pregunta | Revisar configuración de autenticación/sesión del Playground |
| 24/07/2026 | Consulta de documentos disponibles | Parcial: recuperó información, pero no presenta un inventario de las fuentes disponibles | Definir si se agregará una capacidad explícita de listado de fuentes |
| 24/07/2026 | Consulta sin evidencia sobre SAP | Correcto: indicó que no hay evidencia suficiente | Caso de seguridad aprobado |
| 24/07/2026 | Consulta ambigua sobre un error | Incorrecto: declaró evidencia directa basándose en documentos no relacionados de forma suficiente | Ajustar umbrales/política para pedir producto, módulo, versión o mensaje de error |
| 24/07/2026 | Dos consultas consecutivas con evidencia local esperada | Incorrecto en Playground: ambas respondieron sin evidencia, aunque la recuperación y la clasificación por reglas locales las resuelven correctamente | Capturar logs del backend para aislar recuperación frente a clasificación remota |
| 24/07/2026 | Diagnóstico desde Python Debug Console | Correcto para el respaldo local: recuperó 1 evidencia y concluyó `resuelto` mediante reglas locales | Repetir las consultas con la sesión reiniciada y confirmar respuesta en Playground |
| 24/07/2026 | Azure AI Search durante prueba local | Bloqueado: consulta devuelve `Forbidden` por roles de plano de datos pendientes | Mantener como limitación conocida hasta recibir `Search Index Data Reader` |
| 24/07/2026 | Clasificación/embeddings con modelo | Bloqueado: `OPENAI_BASE_URL` no contiene un URL HTTP(S) válido; el sistema usa reglas locales de respaldo | Corregir la configuración de endpoint del modelo antes de validar la ruta remota |
| 24/07/2026 | Consulta directa sobre límites de vistas customizadas desde sesión reiniciada por F5 | Correcto: recuperó y citó `Limites Tecnicos De Vistas Customizadas` desde la base documental local | Caso con evidencia local aprobado |
| 24/07/2026 | Consulta sin evidencia sobre procedimiento SAP desde sesión reiniciada por F5 | Correcto: indicó que no hay evidencia suficiente y no inventó una solución | Caso sin evidencia aprobado |
| 24/07/2026 | Comando `ayuda` | Pendiente de implementación: se trató como consulta documental y no devolvió ayuda del bot | Agregar manejo explícito de comandos del manifest |
| 24/07/2026 | Consulta ambigua sobre un error desde sesión reiniciada por F5 | Incorrecto: citó un hotfix y changelog genéricos como evidencia directa | Forzar solicitud de producto, módulo, versión o mensaje de error antes de recuperar/clasificar |
| 24/07/2026 | Inicio de sesión repetido en Agents Playground | Observación: la autenticación de canal se solicita en cada actividad por el adaptador MSAL/middleware JWT configurado globalmente | Ajustar el modo anónimo de desarrollo o persistencia de sesión del Playground; no bloquea la prueba funcional |
| 24/07/2026 | Corrección de comandos y consultas ambiguas | Implementado: `ayuda` responde con instrucciones y un reporte genérico de error solicita contexto antes de recuperar documentos | Validar ambos casos mediante F5 en Agents Playground |
| 24/07/2026 | Pruebas automatizadas posteriores a la corrección | Correcto: 41 pruebas, `OK` | Ejecutar validación manual breve en Playground |
| 24/07/2026 | Evitar autenticación de Azure AI Search en pruebas locales | Implementado: Azure Search queda desactivado en local por defecto y se habilita solo con `USE_AZURE_SEARCH_IN_LOCAL=true`; producción no cambia | Reiniciar con F5 y verificar que no solicita inicio de sesión por cada consulta |
| 24/07/2026 | Pruebas automatizadas de aislamiento local de Azure Search | Correcto: 42 pruebas, `OK` | Validar una consulta en Playground |
| 24/07/2026 | Autenticación repetida en Playground después del aislamiento de Azure Search | Correcto: el usuario confirmó que ya no solicita inicio de sesión por cada consulta | Caso de autenticación local aprobado |
| 24/07/2026 | Variante de ayuda en lenguaje natural | Implementado: `necesito ayuda`, `quiero ayuda` y variantes comunes devuelven la guía del bot | Validar al reiniciar con F5 |
| 24/07/2026 | Endpoints `healthz` y `readyz` | Implementado: son públicos para sondas locales; `/api/messages` conserva validación JWT | Validar endpoints HTTP con el backend iniciado por F5 |
| 24/07/2026 | Pruebas automatizadas posteriores | Correcto: 45 pruebas, `OK` | Ejecutar comprobación HTTP manual breve |
| 24/07/2026 | Comprobación HTTP con backend iniciado por F5 | Correcto: `healthz` y `readyz` devolvieron JSON sin error de autorización | Endpoints de salud locales aprobados |
| 24/07/2026 | Clasificador LLM de intención inicial | Implementado: enruta lenguaje libre a saludo, ayuda, consulta documental o solicitud de contexto; solo permite respuestas seguras antes de recuperar evidencia | Configurar un endpoint de modelo válido y validar en Playground |
| 24/07/2026 | Respaldo ante endpoint de modelo inválido | Implementado: no intenta llamadas remotas si `OPENAI_BASE_URL` no es HTTP(S), y conserva las reglas locales | Corregir `OPENAI_BASE_URL` según el proveedor elegido |
| 24/07/2026 | Pruebas automatizadas posteriores al router de intención | Correcto: 50 pruebas, `OK` | Validar intención LLM con un endpoint de modelo válido |
| 24/07/2026 | Prueba de lenguaje libre: `buenas, ¿me puedes orientar?` | Bloqueado por configuración: respondió sin evidencia porque el router LLM permanece desactivado ante `OPENAI_BASE_URL` inválida | Configurar un proveedor de modelo con endpoint HTTP(S) válido |
| 24/07/2026 | Configuración para API oficial de OpenAI | Correcto: el entorno efectivo tiene clave configurada, `OPENAI_BASE_URL` vacío y router de intención habilitado con `gpt-4o-mini` | Reiniciar F5 y validar lenguaje libre |
| 24/07/2026 | Corrección de endpoint oficial de OpenAI | Implementado: se usa explícitamente `https://api.openai.com/v1` cuando no se configura proveedor alternativo; cubre clasificación y embeddings | Reiniciar F5 y validar lenguaje libre |
| 24/07/2026 | Conectividad con API oficial de OpenAI | Correcto: verificación de modelos completada sin enviar contenido de usuario | Validar en Playground `buenas, ¿me puedes orientar?` |
| 24/07/2026 | Pruebas automatizadas posteriores a la corrección de endpoint | Correcto: 51 pruebas, `OK` | Validación manual en Playground |
| 24/07/2026 | Prueba LLM de lenguaje libre: `buenas, ¿me puedes orientar?` | Correcto: el router devolvió la guía de Libras | Mantener prueba de variaciones regionales |
| 24/07/2026 | Variación regional: `hola me podes orientar` | Ajustado: saludo + orientación se reconoce localmente y se refuerza como ejemplo del router LLM | Reiniciar F5 y validar la frase |
| 24/07/2026 | Pruebas automatizadas posteriores a variación regional | Correcto: 52 pruebas, `OK` | Validación manual breve en Playground |
| 24/07/2026 | Capa conversacional con modelo | Implementado: tras clasificar saludo, ayuda o falta de contexto, el modelo genera una respuesta natural acotada; consultas técnicas conservan recuperación con evidencia | Validar conversaciones iniciales con F5 |
| 24/07/2026 | Pruebas automatizadas de conversación natural | Correcto: 53 pruebas, `OK` | Validación manual en Playground |
| 24/07/2026 | Conversación inicial y solicitud incompleta en Playground | Correcto: saludo natural y petición de producto, versión, error y pasos | Flujo conversacional local aprobado |
| 24/07/2026 | Consulta técnica de hotfix con fecha relativa | Correcto: respondió con corrección documentada y fuentes de la base local | Flujo con evidencia local aprobado |

## Propósito de este avance

El propósito es probar localmente la integración de Libras con Microsoft Teams mientras se esperan los permisos de datos de Azure AI Search y la Solicitud B.

Este avance permite comprobar que:

- el backend Python inicia correctamente;
- el bot recibe mensajes desde Teams o Microsoft 365 Agents Playground;
- Libras responde en español con el formato esperado;
- la clasificación y la política de evidencia funcionan;
- la base documental Markdown local sirve como respaldo de desarrollo;
- el manifest, los comandos y los íconos de Teams están preparados.

Este avance **no** pretende poner Libras en producción ni validar todavía el acceso corporativo a SharePoint, Azure AI Search o Teams para toda la organización.

## Estado conocido al 24/07/2026

- La Solicitud A está resuelta.
- El Resource Group `rg-libras-prod` está disponible.
- Azure AI Search `srch-libras-prod` fue creado en `Central US`.
- El índice `libras-docs` existe.
- El preflight de plataforma pasó correctamente.
- El usuario todavía espera `Search Index Data Contributor` y `Search Index Data Reader`.
- La Solicitud B aún no se ha ejecutado.
- El repositorio contiene una base Markdown local en `docs/knowledge-base`.
- Los archivos `env/.env.*` pertenecen a Microsoft 365 Agents Toolkit; los archivos `.user` contienen valores sensibles y no deben copiarse ni compartirse.

## Qué se puede probar ahora

Se puede probar el recorrido:

```text
Teams local / Agents Playground
        -> túnel local de Agents Toolkit
        -> http://127.0.0.1:3978/api/messages
        -> Libras
        -> documentación Markdown local
```

Azure AI Search puede permanecer configurado en `.env`, pero no se debe considerar validado como fuente de documentos hasta que el usuario tenga los roles de datos y se complete una consulta real al índice.

## Preparación previa

Desde PowerShell:

```powershell
cd C:\aseinfo_bot\Aseinfo_bot
.\.venv\Scripts\Activate.ps1
python -m unittest discover -s tests -v
```

El resultado esperado es que todas las pruebas terminen en `OK`.

Confirmar también la configuración de plataforma:

```powershell
python src\preflight.py --stage platform
```

Este comando valida configuración y archivos necesarios; no prueba que el usuario pueda leer o escribir documentos en Azure AI Search.

## Configuración local

La configuración privada del backend se encuentra en:

```text
C:\aseinfo_bot\Aseinfo_bot\.env
```

La configuración generada por Microsoft 365 Agents Toolkit se encuentra en `env\`. El código carga primero `.env` y después los archivos de usuario del entorno local. No modificar ni mostrar los archivos `.user` salvo que sea estrictamente necesario para diagnosticar una falla local.

Para estas pruebas deben existir, según el entorno generado por Toolkit, valores locales para:

- `TEAMSFX_ENV`;
- `BOT_ID`;
- `TEAMS_APP_ID`;
- `BOT_ENDPOINT`;
- datos de conexión del bot y del tenant.

No se deben registrar en este documento los valores reales de tokens, secretos o claves.

## Paso 1: iniciar el backend

En una ventana de PowerShell:

```powershell
cd C:\aseinfo_bot\Aseinfo_bot
.\.venv\Scripts\Activate.ps1
python src\app.py
```

El backend debe escuchar en:

```text
http://127.0.0.1:3978
```

En una segunda ventana, validar vida y preparación:

```powershell
Invoke-WebRequest http://127.0.0.1:3978/healthz
Invoke-WebRequest http://127.0.0.1:3978/readyz
```

Resultado esperado de `healthz`:

```json
{"status":"ok"}
```

`readyz` puede depender de la configuración del entorno. Si falla por Azure AI Search, eso debe registrarse como una limitación de permisos y no como una falla de la integración básica de Teams.

## Paso 2: iniciar el entorno local de Teams

Abrir el proyecto con Microsoft 365 Agents Toolkit y seleccionar el entorno local (`local`). Usar la acción de ejecución o depuración local del Toolkit para:

1. iniciar o reutilizar el túnel local;
2. asignar el endpoint público temporal al bot;
3. cargar el manifest local con el sufijo `local`;
4. abrir Teams o Microsoft 365 Agents Playground con la aplicación local.

El endpoint público debe terminar apuntando al backend local en el puerto `3978`. No se debe sustituir el backend por un endpoint de producción.

Si el Toolkit pide iniciar el backend por separado, mantener abierta la primera ventana de PowerShell con `python src\app.py`.

## Paso 3: pruebas funcionales mínimas

Ejecutar desde Teams local o Agents Playground estas categorías de consultas:

| Caso | Ejemplo | Resultado esperado |
|---|---|---|
| Saludo | `Hola` | Libras responde y queda disponible para consultas. |
| Consulta con evidencia local | Preguntar por un procedimiento contenido en `docs/knowledge-base`. | Respuesta con evidencia y referencia al documento local. |
| Consulta sin evidencia | Preguntar por un tema que no exista en la base local. | Libras indica que no tiene evidencia suficiente; no inventa. |
| Consulta ambigua | Preguntar sin indicar producto, módulo o versión. | Solicita contexto o responde con cautela. |
| Actualización documentada | Preguntar por un cambio descrito en un documento de prueba. | Distingue la información documentada de una suposición. |
| Comandos del manifest | Usar `ayuda` o los comandos visibles. | El comando aparece y genera una respuesta coherente. |
| Conversación repetida | Enviar dos preguntas consecutivas. | Cada respuesta corresponde al mensaje actual y no revela datos de otra conversación. |

No usar todavía consultas que pretendan demostrar acceso a SharePoint o a documentos reales de producción.

## Paso 4: validación técnica

Durante las pruebas, revisar la consola del backend y registrar únicamente:

- hora de la prueba;
- categoría de consulta;
- resultado: correcto, incorrecto o bloqueado;
- tiempo aproximado de respuesta;
- fuente declarada por Libras;
- error técnico sin secretos.

No guardar en logs ni en este documento:

- preguntas que contengan información sensible;
- tokens o claves;
- fragmentos documentales confidenciales;
- contenido de `env/*.user`;
- respuestas completas que incluyan datos corporativos no autorizados.

## Criterio de aprobación local

La prueba local se considera satisfactoria cuando:

- `healthz` responde correctamente;
- el bot aparece en Teams local o Agents Playground;
- recibe y responde mensajes;
- al menos una consulta con documento local devuelve evidencia;
- una consulta sin coincidencia no inventa una solución;
- el manifest conserva sus íconos y scopes esperados;
- no se muestran secretos en la interfaz ni en los logs.

Esta aprobación no equivale a aprobación de producción.

### Resultado de aprobación local

**Aprobado el 24/07/2026.** El backend, el Playground, los endpoints de salud,
la conversación inicial, los comandos de ayuda, la recuperación con evidencia
local y la respuesta segura sin evidencia fueron verificados. Permanecen fuera
de esta aprobación Azure AI Search, SharePoint y la publicación corporativa.

## Qué queda bloqueado hasta recibir los permisos de Search

Hasta obtener `Search Index Data Contributor` y `Search Index Data Reader`, no se puede completar de forma confiable:

- cargar o actualizar documentos en `libras-docs`;
- comprobar el conteo de documentos mediante el plano de datos;
- validar búsquedas reales en Azure AI Search;
- demostrar que Teams recupera evidencia desde Azure AI Search.

## Qué queda para la Solicitud B

La Solicitud B se mantiene pendiente hasta contar con los identificadores finales de los recursos y la carpeta documental aprobada. Incluirá, con alcance mínimo:

- acceso de aplicación `Sites.Selected` y lectura solo sobre el sitio SharePoint aprobado;
- roles de Azure AI Search para las identidades administradas del bot y de sincronización;
- permisos mínimos de Key Vault;
- publicación y distribución de Libras en Teams para la audiencia autorizada.

No se debe publicar el paquete de Teams ni solicitar permisos globales como `Files.Read.All`, `Sites.Read.All` o `Sites.FullControl.All` para este flujo.

## Próximo paso recomendado

1. Iniciar `python src\app.py` y validar `healthz` y `readyz`.
2. Ejecutar el entorno local desde Microsoft 365 Agents Toolkit.
3. Probar las consultas de la tabla anterior.
4. Registrar resultados y errores en una bitácora de prueba separada, sin secretos.
5. Cuando lleguen los permisos de Search, cargar el staging y repetir las pruebas con Azure AI Search.

## Referencias del proyecto

- [AGENTS.md](../AGENTS.md)
- [README.md](../README.md)
- [Producción de Libras](produccion-semana.md)
- [Azure AI Search y SharePoint/OneDrive](azure-ai-search-sharepoint.md)
- [Base documental local](knowledge-base)
