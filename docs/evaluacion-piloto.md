# Matriz de evaluación del piloto de Libras

Usar esta matriz cuando estén disponibles los PDFs autorizados de la carpeta
piloto. La evaluación se realiza desde Teams y se registra sin copiar datos
sensibles, secretos ni fragmentos innecesarios.

| case_id | pregunta | PDF esperado | estado esperado | enlace correcto | respuesta fundamentada | inventó datos | latencia_ms | observaciones |
|---|---|---|---|---|---|---|---:|---|
| DOC-01 | Pendiente con pregunta real | Pendiente | resuelto | Sí/No | Sí/No | Sí/No |  |  |
| DOC-02 | Pendiente con pregunta real | Pendiente | resuelto | Sí/No | Sí/No | Sí/No |  |  |
| NOE-01 | Pregunta sin evidencia | Ninguno | sin_evidencia | N/A | Sí/No | Sí/No |  |  |

## Casos mínimos antes de producción

1. Dos preguntas respondidas por PDFs distintos.
2. Una pregunta cuya respuesta dependa de una versión o fecha concreta.
3. Una pregunta sin coincidencia, que debe escalar sin inventar una solución.
4. Un PDF actualizado: confirmar que la versión anterior deja de aparecer.
5. Un PDF eliminado: confirmar que ya no se recupera en Azure AI Search.

Registrar la duración desde el envío en Teams hasta la respuesta. La salida de
esta matriz respalda la validación funcional de la biblioteca piloto; no
sustituye los controles de acceso ni la aprobación de producción.
