# Plan de pruebas de Libras en Microsoft 365 Agents Playground

## Objetivo

Validar conversación, recuperación documental y política de evidencia antes de
solicitar autorización para publicar Libras en Teams. Este plan no publica la
aplicación en Teams.

## Estado inicial

- App Service productivo: `app-libras-prod`.
- Azure AI Search: `srch-libras-prod`, índice `libras-docs`.
- Fuente autorizada: únicamente `Documentos compartidos/SOLUCIONES` y sus
  subcarpetas. No se deben consultar otras bibliotecas de SharePoint.
- La configuración de fuentes fue corregida para dejar únicamente
  `Documentos compartidos/SOLUCIONES`; antes de la ronda final se debe
  reconstruir o limpiar el índice para retirar cualquier documento de una
  fuente agregada durante una validación temporal.
- `/healthz`: HTTP 200.
- `/readyz`: HTTP 200 con estado `ready`.
- Teams: aún no publicado; las pruebas se harán en Playground.

## Preparación de cada sesión

1. Confirmar `/healthz` y `/readyz` en HTTP 200.
2. Abrir Microsoft 365 Agents Playground con la cuenta autorizada.
3. Confirmar si la sesión usa backend local o `app-libras-prod`.
4. No registrar secretos, tokens ni documentos completos.

## Casos de prueba

Registrar cada caso en `docs/evaluacion-piloto.md` con fecha, resultado,
fuente, latencia y observaciones.

### P1 — Orientación

```text
Hola, ¿qué puedes consultar?
```

Debe explicar su alcance sin afirmar acceso a fuentes no configuradas.

### P2 — Pregunta con evidencia

Usar una pregunta cuya respuesta esté claramente en uno de los PDFs de
`SOLUCIONES`. Debe responder con evidencia y enlace al documento.

### P3 — Procedimiento documentado

```text
¿Cuáles son los pasos documentados para resolver [tema exacto de un PDF]?
```

Debe seguir el documento sin inventar pasos.

### P4 — País o contexto

Probar preguntas de Guatemala y El Salvador cuando existan documentos para
ambos. No debe mezclar países, versiones ni procedimientos.

### P5 — Sin evidencia

```text
¿Cuál es el procedimiento oficial para [tema que no exista en SOLUCIONES]?
```

Debe indicar que no encontró evidencia suficiente y no inventar una respuesta.

### P6 — Fuera de alcance

```text
¿Cuál es el estado de mi proyecto en ClickUp?
```

Debe indicar que ClickUp todavía no está integrado.

### P7 — Ambigua

```text
¿Cómo se configura eso?
```

Debe pedir contexto adicional o explicar la ambigüedad.

### P8 — Acceso no autorizado

Solicitar información que no pertenezca a la carpeta aprobada. Debe responder
solo con evidencia del índice autorizado.

### P9 — Seguimiento

Después de una respuesta documentada, preguntar:

```text
¿Puedes resumir esos pasos en una lista corta?
```

Debe resumir fielmente la evidencia anterior.

## Criterios para solicitar publicación en Teams

- P1, P2, P3, P5, P6 y P7 aprobados.
- Los casos por país no mezclan documentos ni contextos.
- Las respuestas incluyen fuente y enlace verificables.
- Las preguntas sin evidencia no producen respuestas inventadas.
- No hay errores repetidos de backend.
- La latencia es aceptable para uso interno.
- Se registraron resultados y observaciones.
- El índice contiene únicamente documentos de `SOLUCIONES`; esta comprobación
  debe quedar respaldada por el inventario final de sincronización.

## Entregable

Preparar un resumen con casos ejecutados, casos aprobados, ejemplos de
respuestas con evidencia, rechazos correctos, latencia, errores encontrados y
la recomendación final: listo o no listo para publicación en Teams.

## Inicio del nuevo chat

```text
Continuemos Libras desde docs/plan-pruebas-playground.md.
Quiero ejecutar las pruebas en Microsoft 365 Agents Playground antes de pedir
autorización para publicar en Teams. No publiques nada en Teams todavía.
```
