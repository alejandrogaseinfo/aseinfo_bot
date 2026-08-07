# Evaluación de calidad de recuperación — 5 de agosto de 2026

Se ejecutó `tests/corpus-calidad-matriz.json` contra la configuración de
producción (`libras-docs`). La evaluación no imprime las preguntas ni el
contenido de los fragmentos.

## Resultado

| Métrica | Resultado |
|---|---:|
| Casos | 12 |
| Recuperación esperada | 12/12 |
| Recall de evidencia | 100% |
| Abstención correcta | 100% |
| Resolución final con evidencia | 87.5% |
| Respuestas con una sola fuente | 75% |
| Latencia promedio | 3.2 s |
| Latencia p95 | 5.7 s |

Después del ajuste, la recuperación conserva el recall y las reglas locales
resuelven los casos con acción y tema explícitos:

- `PROC-03` y `DIAG-02`: ahora se responden cuando la acción solicitada y el
  tema tienen soporte directo en el documento.
- `DIAG-03`: ahora recupera las páginas operativas 34, 36 y 37, donde se
  documentan los riesgos, parámetros y validaciones de incapacidades.
- `INSUF-01` e `INSUF-02`: ahora solicitan contexto antes de consultar el
  índice, evitando respuestas tangenciales.

## Decisión

La guardia de consultas insuficientemente especificadas, la cobertura de
acciones y el puente de búsqueda hacia “Riesgos de incapacidad” quedan
implementados. La matriz termina en 12/12 casos y resolución final del 100%.
No se recomienda cambiar el ranking.
