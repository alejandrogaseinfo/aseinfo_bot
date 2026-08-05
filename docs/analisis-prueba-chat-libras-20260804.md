# Análisis de la prueba de chat de Libras — 2026-08-04

## Alcance de la evidencia

Se revisó `C:\Users\jgarcia\Desktop\prueba-chat-libras.pdf`, con nueve páginas de una exportación de Teams. La exportación repite visualmente cada mensaje en dos bloques, por lo que las repeticiones no representan dos consultas distintas.

## Hallazgos por caso

| Caso | Qué ocurrió | Causa probable | Acción |
|---|---|---|---|
| Prórroga de contratos | Se rechazó como confidencial. | Teams usaba una regla/versión anterior del guard o una configuración distinta. | Verificar revisión desplegada, endpoint, índice y `LIBRAS_ENV`; reiniciar/desplegar. |
| Parámetros de incapacidades | Citó `Readme 1.19.1.0.pdf`, pero no explicó el hallazgo. | Recuperación parcial y redacción genérica. El fragmento sí menciona un parámetro de aplicación para validar traslapes, pero no enumera necesariamente todos los parámetros. | Responder solo con el dato exacto disponible y declarar los límites. |
| Clasificación de incapacidades | Dio clasificaciones generales de `Acciones de personal.pdf`; luego perdió continuidad al añadir “en Evolution”. | La fuente puede ser válida para clasificación funcional, pero no prueba por sí sola configuración de Evolution; falta contexto conversacional. | Exigir evidencia de producto/módulo y conservar el contexto del turno anterior. |
| Parámetros modificables | Respondió sin evidencia. | Puede ser abstención correcta, pero hay riesgo de coincidencias tangenciales con “parámetro” o “incapacidad”. | Validar sujeto + operación en el mismo fragmento, no en el documento completo. |
| Administración de documentos + Evolution | Con “en Evolution” falló; sin “en Evolution” recuperó `Gestion de documentos.pdf`. | El documento describe gestión de documentos, pero el nombre no repite “Evolution”; filtro de producto demasiado literal. | Usar biblioteca/carpeta/metadatos aprobados para identificar producto. |
| Ejemplos de documentos | Respondió formularios, manuales, procedimientos e instructivos con fuente. | Caso correctamente recuperado y formateado. | Mantener respuesta directa + fuente + enlace. |
| Vacaciones negativas | Tres formulaciones terminaron sin evidencia pese a existir `acc.proc_arreglar_vac_negativos.sql`. | Teams no usaba la versión de código/índice actual, o el filtro anterior no normalizaba identificadores SQL y variantes morfológicas. | Verificar despliegue; conservar normalización y prioridad del título. |
| Descuentos/aguinaldo de El Salvador | Se abstuvo. | Correcto mientras no exista fuente autorizada, vigente y específica. | Mantener abstención. |

## Diagnóstico consolidado

### Desalineación entre el PDF y la versión actual

El índice productivo actual fue recargado con `core-v3` y la evaluación obtuvo 5/5 casos, incluyendo administración de documentos, vacaciones negativas y abstención legal. El PDF muestra el comportamiento anterior. La hipótesis principal es que el bot de Teams ejecutaba una revisión anterior o tenía variables diferentes.

La primera comprobación debe ser operativa:

- revisión/commit desplegado;
- endpoint e índice efectivos, sin imprimir secretos;
- `LIBRAS_ENV=production`;
- reinicio del proceso;
- prueba controlada desde Teams con timestamp correlacionable en logs.

### Recuperación y evidencia no son lo mismo

Encontrar un documento relacionado no significa que el fragmento responda. El caso de parámetros de incapacidades puede confirmar la existencia de un parámetro de aplicación y la lógica de traslape, pero no necesariamente sus nombres y valores. La respuesta debe extraer solo lo demostrado por el fragmento.

### Contexto documental demasiado amplio

El contexto de todo el documento ayuda a ordenar resultados, pero no debe habilitar una respuesta si el fragmento no contiene el sujeto y la operación solicitados. La validación debe combinar título normalizado, tokens del fragmento, coocurrencia cercana y metadatos de producto, módulo, país y rol.

### Falta cobertura de evaluación para incapacidades

El corpus inicial no tenía casos específicos de parámetros de incapacidades, clasificación, seguimiento con/sin “Evolution” ni diferencia entre “menciona una incapacidad” y “documenta cómo configurarla”. Deben incorporarse antes de otra promoción.

## Plan correctivo priorizado

### P0 — Confirmar que Teams usa lo corregido

1. Registrar revisión desplegada y configuración efectiva.
2. Reiniciar/desplegar la aplicación.
3. Repetir las consultas del PDF y guardar resultados con timestamp.
4. Confirmar que contratos y vacaciones ya no son bloqueados o abstencionistas injustificadamente.

### P1 — Mejorar fidelidad de respuesta

1. Separar `evidencia encontrada`, `evidencia directa` y `sin evidencia suficiente`.
2. Exigir que cada afirmación cite el fragmento que la soporta.
3. Si la fuente solo describe una incidencia o pantalla, decirlo explícitamente y no convertirla en una lista de parámetros.
4. Añadir casos de incapacidades y administración documental al corpus.

### P1 — Mejorar identificación documental

1. Propagar `product`, `module`, `operation`, `artifact_role`, `country` y `quality_status` durante la ingesta.
2. Usar carpeta/biblioteca aprobada para identificar Evolution cuando el título no lo menciona.
3. Mantener contexto para ranking, pero no para validar por sí solo una afirmación.

### P2 — Conversación

Implementar estado persistente por conversación, con mapeo seguro de Teams al backend, para que “la pregunta anterior”, “en Evolution” o “ese documento” no se interpreten como consultas aisladas.

## Estado actual

- Índice productivo: `core-v3`, 284 documentos y 2,665 fragmentos.
- Corpus productivo ampliado: 8/8 casos aprobados, recall 1.0 y abstención 1.0.
- Pruebas automatizadas: 140 exitosas.
- Respaldo del índice anterior: `output/backup-libras-docs-20260804.jsonl.gz`.
- La revisión correctiva está publicada en `app-libras-prod`; `/healthz` y
  `/readyz` confirman que el proceso está listo con el índice productivo.
- Falta la prueba funcional desde Teams para confirmar el recorrido completo de
  Bot Framework, conversación y presentación de fuentes.
