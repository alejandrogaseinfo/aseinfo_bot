# Revisión humana del redactor — muestra operativa

Esta es la muestra propuesta para revisar la calidad del chat como lo usaría
un funcionario de operaciones. Las preguntas están expresadas con variaciones
naturales, pero cada una conserva un criterio de respuesta verificable.

## Cómo usarla

Ejecutar cada pregunta dos veces con las mismas evidencias:

1. `legacy + redactor apagado`.
2. `legacy + redactor encendido`.

Registrar las dos respuestas, las fuentes visibles y la latencia. Marcar
`Aprobada`, `Observada` o `Rechazada`. Una respuesta se rechaza si inventa
campos, pasos, versiones o relaciones, aunque su redacción sea clara.

## Preguntas seleccionadas

| ID | Pregunta natural | Resultado correcto que debe conservarse | Fuente/evidencia esperada | Tipo |
|---|---|---|---|---|
| OPS-01 | ¿En qué versión se actualizó jQuery y qué versión reemplazó? | Evolution **1.24.1.2** actualizó jQuery a **3.7.2**, reemplazando **1.12.4**. No aceptar una versión de Readme incidental. | Readme 1.24.1.2, fragmento que menciona las tres versiones. | versión + evidencia |
| OPS-02 | En la 1.24.1.3, ¿qué se sabe de la tabla IRA? | El Manual de Relación DB identifica `wfl.ira_instancias_rutas_aut` y sus relaciones `ira_codrau` e `ira_codigo_entidad`; no demuestra que el manual sea específico de la versión 1.24.1.3. | Manual de Relación DB V1.2. | versión no confirmada |
| OPS-03 | ¿Qué guarda `ira_instancias_rutas_aut` y con qué campos se relaciona? | Guarda información de flujos; se relaciona mediante `ira_codrau` e `ira_codigo_entidad`. No inventar columnas adicionales. | Manual de Relación DB V1.2. | estructura |
| OPS-04 | Necesito administrar documentos en Evolution, ¿cómo se hace? | Responder solo con los pasos/tipos documentados y citar el manual correspondiente. | Gestion de documentos / manual de documentos. | procedimiento |
| OPS-05 | ¿Qué documentos se pueden gestionar? Dame algunos ejemplos. | Dar únicamente ejemplos presentes en la evidencia; no convertir una lista parcial en una lista completa. | Documento de gestión de documentos. | conceptual |
| OPS-06 | El script de vacaciones negativas, ¿qué hace exactamente? | Explicar su propósito y alcance documentados; no agregar instrucciones de ejecución que el fragmento no incluya. | Script o documento de vacaciones negativas. | procedimiento |
| OPS-07 | Para una prórroga de contrato, ¿qué parámetros debo revisar? | Enumerar solo los parámetros respaldados por la evidencia y conservar el módulo/producto. | Documento de prórroga de contratos. | procedimiento |
| OPS-08 | Después de reinstalar MSDTC, ¿qué validamos en ambos servidores? | Responder las validaciones DTC documentadas; no tratar “reinstalar” como una solicitud de release o actualización. | Manual DTC / verificación. | diagnóstico |
| OPS-09 | ¿Cómo se ofuscan datos sensibles en SQL? | Mostrar solo el procedimiento SQL autorizado y su fuente; nunca revelar credenciales ni secretos. | Script SQL de ofuscación. | seguridad |
| OPS-10 | ¿Cómo amplío el tiempo de sesión en Evolution? | Resumir los pasos documentados y conservar el enlace de la fuente. | Ampliar Tiempo de Sesion. | procedimiento |
| OPS-11 | ¿Qué precauciones tomo antes de instalar una actualización? | Si hay Readmes incompatibles, pedir la versión exacta; no escoger una release por ranking. | Readmes versionados. | solicita_contexto |
| OPS-12 | Un usuario tiene permisos, pero no puede descargar documentos. ¿Qué reviso? | Mantener `sin_evidencia` si las fuentes no contienen un procedimiento directo; no inventar diagnóstico. | Ninguna fuente suficiente. | abstención |

## Reglas específicas para las tres preguntas de referencia

- En OPS-01, el candidato crudo `Readme 1.24.1.4` de la captura no basta para
  contestar. La respuesta observada que atribuye el cambio a 1.24.1.2 solo es
  aprobable si la evidencia final contiene el fragmento de 1.24.1.2. Si solo
  llega el candidato 1.24.1.4, debe marcarse como **inconsistencia de ranking**
  y no como respuesta correcta.
- En OPS-02, la versión solicitada es 1.24.1.3, pero el Manual DB V1.2 no
  confirma esa versión. La respuesta debe mostrar la advertencia de versión no
  confirmada y limitarse a los campos documentados.
- En OPS-03, al no solicitar versión, se puede responder directamente con el
  propósito de la tabla y los dos campos de relación. No se debe completar una
  estructura SQL que no aparece en el documento.

## Decisión de la muestra

El redactor solo se considerará candidato a piloto si:

- OPS-01, OPS-02 y OPS-03 pasan sin mezclar versiones;
- OPS-09 no expone secretos ni texto de instrucciones documentales;
- OPS-11 solicita versión cuando corresponde;
- OPS-12 se abstiene sin mostrar fuentes tangenciales;
- las respuestas encendidas mejoran claridad sin perder fidelidad frente a la
  variante determinista;
- no aumentan los fallbacks ni la latencia p95 más allá del umbral acordado.

