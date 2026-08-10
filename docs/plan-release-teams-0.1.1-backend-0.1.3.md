# Plan de preparación para la siguiente versión de Libras

**Objetivo:** dejar listo el proyecto para solicitar la actualización de la aplicación personalizada de Teams a `0.1.1` y decidir, con evidencia, si el backend puede declararse `0.1.3` o requiere ajustes previos.

## Estado de partida

- La aplicación instalada en Teams muestra `0.1.0`.
- El manifiesto del repositorio contiene actualmente `0.1.2`, pero esa versión no debe considerarse publicada hasta confirmar su carga en Teams.
- El backend contiene las mejoras conversacionales del commit `37795e1`.
- El backend y el paquete de Teams tienen ciclos de versión independientes.
- El objetivo de publicación será:

```text
Backend: 0.1.3
Teams:   0.1.1
```

## Fase 1: inventario y control de cambios

1. Confirmar que `0.1.0` es realmente la versión publicada en el catálogo o tenant.
2. Revisar el manifiesto y decidir qué cambios visibles se incluirán en `0.1.1`.
3. No cambiar `appId`, `botId`, iconos ni permisos sin justificarlo explícitamente.
4. Separar archivos generados de los entregables:
   - excluir `output/`, logs, ZIP temporales y cachés;
   - resolver las eliminaciones pendientes de `docs/planes-posteriores` antes del release.
5. Registrar el alcance en un changelog:

```text
Teams 0.1.1: primera actualización publicada desde 0.1.0.
Backend 0.1.3: mejoras de conversación, comandos y calidad de recuperación.
```

## Fase 2: auditoría del backend `0.1.3`

### Funciones que deben estar comprobadas

- Seguimiento temporal dentro del mismo chat.
- Limpieza del contexto mediante `/nuevo`.
- Menú guiado como orientación suave, sin filtrar incorrectamente la pregunta.
- Comandos `/ayuda`, `/version`, `/procedimiento` y `/actualizacion`.
- Preguntas directas sin seleccionar una opción.
- Preguntas relacionadas y no relacionadas con una opción seleccionada.
- Referencias como “esos documentos”, “esa versión” y “lo anterior”.
- Respuestas sobre capacidades y fuentes autorizadas.
- Protección contra la invención de nombre, memoria personal o evidencia.
- Enlaces amigables y anclas `#page=N` cuando exista página documental.
- Respuestas controladas cuando no hay evidencia suficiente.

### Criterio de decisión

El backend se puede declarar `0.1.3` si:

- todas las pruebas automatizadas pasan;
- no existen regresiones conocidas en las respuestas documentales;
- las variables de producción están documentadas;
- `/healthz` y `/readyz` responden correctamente;
- el comportamiento en Web Chat y Teams coincide;
- existe un procedimiento de rollback probado.

Si falla alguno de estos puntos, se corrige primero y se mantiene la versión como candidata (`0.1.3-rc.1`) hasta repetir la validación.

## Fase 3: pruebas automatizadas y de regresión

Ejecutar como mínimo:

```powershell
python -m pytest -q
git diff --check
```

Agregar o revisar casos para:

1. `/nuevo` seguido de una pregunta sin relación con el chat anterior.
2. Pregunta de seguimiento con pronombres (“esos”, “esa”, “lo anterior”).
3. Selección de procedimiento seguida de una pregunta conceptual.
4. Pregunta conceptual sin seleccionar menú.
5. Consulta de versión con documentos vecinos de otras versiones.
6. “Resume lo anterior” con y sin contexto.
7. “¿Qué te puedo preguntar?” y “¿Qué fuentes usas?”.
8. Preguntas sin evidencia suficiente.
9. Enlaces a PDF con número de página.
10. Renderizado de Adaptive Cards y Markdown en Teams.

## Fase 4: validación de producción del backend

1. Definir `LIBRAS_RUNTIME_REVISION=0.1.3` en el entorno de producción.
2. Desplegar el backend sin modificar identificadores de Teams.
3. Validar `/healthz` y `/readyz` después del despliegue.
4. Ejecutar una prueba corta en Web Chat.
5. Ejecutar la matriz de pruebas en un chat de Teams de prueba.
6. Revisar logs y confirmar que no haya errores de Adaptive Cards, Azure AI Search o autenticación.
7. Registrar el identificador del despliegue y conservar el artefacto para rollback.

## Fase 5: preparar el paquete Teams `0.1.1`

1. Cambiar en `appPackage/manifest.json`:

```json
"version": "0.1.1"
```

2. Mantener el mismo `id` y `botId`.
3. Revisar títulos y descripciones de comandos para que sean amigables y consistentes.
4. Confirmar que el manifiesto no agregue permisos innecesarios.
5. Validar el esquema del manifiesto.
6. Generar el ZIP incluyendo únicamente:
   - `manifest.json`;
   - `color.png`;
   - `outline.png`.
7. Verificar que el ZIP no incluya `.env`, código fuente, logs, `output/` ni credenciales.

## Fase 6: aprobación y actualización en Teams

1. Subir el ZIP como nueva versión de la aplicación personalizada.
2. Solicitar aprobación administrativa si la política del tenant la exige.
3. Informar al administrador que es la primera actualización publicada desde `0.1.0`.
4. Confirmar que la aplicación conserva el mismo `appId` y `botId`.
5. Después de la aprobación, abrir los detalles de la aplicación y confirmar que muestra `0.1.1`.
6. Probar la aplicación instalada en un chat nuevo y en un chat existente.

Los cambios de código del backend no requieren volver a subir el paquete Teams; los cambios del manifiesto sí requieren una nueva versión del paquete.

## Fase 7: aceptación final

El release se considera aprobado cuando:

- Teams muestra `0.1.1`;
- el backend reporta `0.1.3`;
- el menú y los comandos funcionan;
- no aparece `Card - access it on https://go.skype.com/cards.unsupported`;
- las respuestas mantienen evidencia y enlaces correctos;
- `/nuevo` limpia el contexto;
- se documentó el resultado de las pruebas;
- existe rollback para el backend y para la aplicación Teams.

## Resultado esperado

El entregable final debe incluir:

- commit del backend `0.1.3`;
- manifiesto Teams `0.1.1`;
- ZIP validado;
- changelog;
- matriz de pruebas ejecutada;
- identificador del despliegue;
- evidencia de aprobación o actualización en Teams;
- instrucciones de rollback.
