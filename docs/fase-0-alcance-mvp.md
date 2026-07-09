# Fase 0 - Alcance Del MVP

## Objetivo

Definir con precision que resolvera el MVP del bot de autoservicio en Teams y que quedara fuera de alcance en esta primera etapa.

## Usuarios Iniciales

- Operaciones
- Soporte
- Desarrollo

## Casos De Uso Principales

El MVP se enfocara en consultas operativas y tecnicas que ya puedan respaldarse con evidencia en fuentes existentes.

### 1. Errores Tras Actualizaciones

Preguntas relacionadas con fallos que aparecen despues de instalar un hotfix, aplicar un parche o actualizar un paquete.

Objetivo del bot:

- detectar si el problema ya estaba documentado,
- identificar si existe una correccion conocida,
- orientar al usuario hacia la fuente correcta.

### 2. Consultas Sobre Advertencias O Pasos De Instalacion

Preguntas sobre advertencias, prerequisitos o pasos que ya estaban descritos en readmes, documentos de actualizacion o setups.

Objetivo del bot:

- recuperar la instruccion relevante,
- resumirla en lenguaje claro,
- citar la fuente para que el usuario valide el paso.

### 3. Limites Tecnicos De Personalizaciones

Preguntas sobre hasta donde se puede llegar con configuraciones o personalizaciones sin requerir intervencion del equipo de desarrollo, por ejemplo vistas customizadas.

Objetivo del bot:

- responder con base en reglas o antecedentes documentados,
- dejar claro cuando una solicitud ya requiere desarrollo formal.

### 4. Errores Con Antecedentes Similares

Preguntas sobre errores tecnicos, incluidos errores de base de datos como Oracle u otros modulos, cuando no exista un caso identico activo pero si antecedentes utiles.

Objetivo del bot:

- localizar incidentes o documentos parecidos,
- presentar similitudes relevantes,
- sugerir el siguiente paso sin afirmar una equivalencia no comprobada.

## Casos Fuera De Alcance

### 1. Automatizacion De Flujos No Documentados

El bot no intentara automatizar procesos operativos complejos si esos procesos no estan documentados paso a paso.

Esto incluye casos donde se espera que la IA resuelva tareas repetitivas o genere procedimientos completos sin una base documental previa.

### 2. Sustitucion Del Equipo De Desarrollo En Tareas Complejas

El bot no sustituira a los programadores en cambios estructurales, programacion compleja ni solicitudes que requieran desarrollo a medida.

Su rol sera orientar, filtrar y responder con evidencia cuando exista, no ejecutar analisis de ingenieria profunda sin respaldo.

### 3. Uso Del Chat Como Solucion Universal

El MVP no intentara resolver por chat todos los problemas del trabajo diario ni convertirse en una capa general de automatizacion.

Se limitara a consultas concretas, repetibles y trazables.

## Fuentes Minimas Esperadas Para El MVP

- Readmes
- Setups
- Documentos de actualizacion
- Changelogs
- Notas de despliegue
- Notas de hotfix
- Tickets recientes en ClickUp
- Historico de Jira
- Diffs o referencias tecnicas cuando esten disponibles

## Resultado Esperado Del MVP

El MVP se considerara correctamente acotado si puede responder consultas frecuentes con evidencia trazable y si sabe escalar cuando no exista respaldo suficiente.
