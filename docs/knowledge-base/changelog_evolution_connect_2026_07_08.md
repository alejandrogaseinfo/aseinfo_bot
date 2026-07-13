# Changelog - Evolution Connect

## Version 2.8.0
**\==============**
#### 26/MAR/2026

## **Nuevas funcionalidades**
*   CU-86b84z6xm - Crear endpoint para calcular la duración del tiempo no trabajado y validar la jornada del empleo.
*   CU-86b84zq18 - Gestionar actividades de Onboarding.
*   CU-86b84zqty - Actividades de Connect -IA - Sincronización automática de entidades con flujo hacia RavenDB.
*   CU-86b84zrkd - Reemplazo de infraestructura de cola notificaciones por implementación de Evolution Queue Manager compatible para 1.24.2.
*   CU-86b84zthb - Agregar entidades faltantes del módulo de Reclutamiento y Selección.
*   CU-86b84ztjb - Agregar validaciones de reglas de negocio al crear o modificar Objetivos de Evaluación.
*   CU-86b84ztnk - Actualizar el mensaje de validación para pageSize fuera de rango en endpoints con paginación.
*   CU-86b850bch - Agregar endpoints para ordenar fortalezas y debilidades existentes de la evaluación de desempeño.
*   CU-86b850bnn - Implementar endpoint para devolver los conjuntos de datos autorizados al user, metadata uno a uno y ejecución.
*   CU-86b850byc - Agregar validación en endpoints PUT para impedir cambios en entidades con flujo ya autorizadas.
*   CU-86b850c2a - Modificación en la generación de actividades de instancias de workflow para incluir los nuevos tipos de autorizadores.
*   CU-86b850d35 - Crear endpoint que retorne la versión de Connect y componentes relacionados con la base de datos.
*   CU-86b87pxev - Agregar crud de consultas de excel.
*   CU-86b8dt78c - Crear endpoint GetAll para obtener la información de las entidades adicionales.
*   CU-86b8dt8vz - Crear endpoint GetAll que devuelva los registros de las consultas genéricas.
*   CU-86b92km0y - CRUD de Secciones de Estado Patrimonial y Pasivos del Expediente en el Portal.

## **Mejoras**
*   CU-86b84z7d7 - Codesmell - Agregar validaciones de negocio para la entidad MotivoRetiro.
*   CU-86b84z7e9 - Codesmell - Corregir dependencia circular en UsuarioService.
*   CU-86b84z9h7 - Modificación de la seguridad de contenido en la Solicitud de Licencia.
*   CU-86b84z9ye - Modificación de las validaciones al crear o editar tiempo no trabajado.
*   CU-86b84za0c - Simplificar response de metadata de autorización de cambios al expediente del portal - sección general.
*   CU-86b84za1g - Convertir la funcionalidad de consulta de la metadata de los formularios dinámicos a endpoint.
*   CU-86b84zmww - Revisión de la clase EntityValidationForeingKeyExtensions del Evolution para actualizar las validaciones de empleo relacionadas con Onboarding en Evolution Connect.
*   CU-86b84zn3b - Implementar Transacción en la finalización de la Reversión de Retiros para asegurar la integridad de los datos.
*   CU-86b84zn5j - Agregar endpoint Delete para las evaluaciones de desempeño.
*   CU-86b84znbp - Agregar validaciones para evitar modificar los datos de la evaluación de desempeño cuando esta ya se finalizó.
*   CU-86b84zndp - Modificar validaciones y guardado de datos de la evaluación de competencias de la evaluación de desempeño.
*   CU-86b84znw2 - Implementación de consulta de los permisos de las secciones de Mi Expediente y Expediente Subalternos desde portal (Primera Parte).
*   CU-86b84znyx - Implementación completa del soporte para client credentials.
*   CU-86b84zpah - Modificar la finalización de la reversión de contratación para incluir funcionalidad relacionada con programas de Onboarding.
*   CU-86b84zpch - Modificar la finalización de la reversión de retiro para incluir funcionalidad relacionada con programas de Onboarding.
*   CU-86b84zpjc - Refactorizar la consulta que se realiza para obtener la metadata de autorización de CambioDatoExpediente.
*   CU-86b84zpmj - Modificar la finalización de retiro para incluir funcionalidad relacionada con programas de Onboarding.
*   CU-86b84zpum - Funcionalidad de consulta de un participante de Onboarding.
*   CU-86b84zq2h - Incluir redirección a pantallas de flujo en notificaciones push hacia EvoWave Portal.
*   CU-86b84zq46 - Codesmell - Modificar el modelo utilizado para devolver la información del empleo (endpoint: Me y Subalternos).
*   CU-86b84zqdf - Agregar validaciones de foreign keys y asignación de propiedades de navegación en las entidades Causa Amonestación y Tipo Incapacidad.
*   CU-86b84zqee - Agregar entidades faltantes de distintos módulos en EvoConnect.
*   CU-86b84zqf9 - Modificación del método que actualiza los datos de la instancia de la entidad adición en la tabla anexa.
*   CU-86b84zqpd - Agregar validaciones de reglas de negocio faltantes en Administración de Lactancia.
*   CU-86b84zr2b - Modificación en el endpoint ME para incluir la información del tipo de planilla del empleo.
*   CU-86b84zr46 - Agregar un nuevo endpoint para marcar como no finalizadas las evaluaciones de desempeño.
*   CU-86b84zr4m - Actualización de comentarios, validaciones y visibilidad de notas en la finalización de la evaluación de desempeño.
*   CU-86b84zr5g - Agregar validaciones faltantes para la sección Necesidades de Capacitación de la Evaluación de Desempeño.
*   CU-86b84zr7b - Agregar el nivel de pirámide del empleo del evaluador y evaluado en la Evaluación de desempeño.
*   CU-86b84zrbg - Modificación en el endpoint ME para incluir la información del país de la compañía del empleo.
*   CU-86b84zrcw - Agregar información de paginación a los endpoints GET ALL en Evolution Connect (módulos de acciones y salarios).
*   CU-86b84zrfd - Validar que la fecha de baja no sea menor que la fecha de alta en la Solicitud de Equipo o Acceso.
*   CU-86b84zrj4 - Validar parámetro PermitirEdicionExpedienteEnPortal para la creación, edición y eliminación en las secciones del expediente desde el portal.
*   CU-86b84zrjn - Corrección de DELETE CASCADE en las entidades que lo requieran en EvoConnect.
*   CU-86b84zrtu - Agregar entidades relacionadas a Oferentes del módulo de Reclutamiento.
*   CU-86b84zrve - Codesmell - Agregar validaciones faltantes al editar una Entidad Auditoria.
*   CU-86b84zrxp - Ajustar funcionalidad existente de Onboarding para incluir funcionamiento de los nuevos estados de los participantes para endpoints de consulta y modificación.
*   CU-86b84zt2j - Agregar validaciones de fluent faltantes en las propiedades de Clase Salarial.
*   CU-86b84zt3x - Agregar validación para evitar duplicidad en registros de funcionalidad de catálogo Parte 2.
*   CU-86b84ztfb - Agregar validación para evitar duplicidad en registros de funcionalidad de catálogo Parte 1.
*   CU-86b84ztg2 - Agregar en la finalización de la contratación la inscripción de participantes a un programa de Onboarding.
*   CU-86b84ztmk - Actualización de columna calculada y validación dinámica de TotalInversion en AccionCompaniaExpediente.
*   CU-86b850bu6 - Alinear creación de transacciones en servicios y DbContextBase para integrarse a transacciones externas.
*   CU-86b850czn - Refactorar funcionalidad de recepción de datos de formulario dinámico para los tipos soportados actualmente.
*   CU-86b87q9cp - Mitigar vulnerabilidad A01:25 - Exposición no autorizada de información de usuarios.
*   CU-86b87qa9x - Limpieza de código que involucra el controlador de la Entidad Auditoria.
*   CU-86b8p8528 - Agregar header para enviar el empleo seleccionado del usuario.
*   CU-86b8tkjda - Agregar headers dinámicos para las columnas Grupo de los factores técnicos y no técnicos en la metadata de autorización de la Evaluación de Desempeño.
*   CU-86b92kmjg - Consultar cambios pendientes de autorización del Expediente por sección (diccionario).
*   CU-86b92knau - Estandarizar paginación en endpoints GET ALL.
*   CU-86b92kq0v - Expandir implementación ABAC (políticas, middleware y scripts).
*   CU-86b92kqt9 - Saneamiento de validadores (Codesmells en RuleValidators).
*   CU-86b92krbb - Sustituir GraphQL por endpoints REST en Evolution Connect.
*   CU-86b92krkp - Saneamiento de reglas FluentValidation (codesmells).
## **Correcciones**
*   CU-86b84z9m3 - Corrección de bug en la finalización de las solicitudes de movimiento de tipo traslado de empresas.
*   CU-86b84z9p6 - Corrección de bug en el cálculo del saldo de vacaciones en la finalización de la solicitud de vacación.
*   CU-86b84z9wk - Análisis y revisión para corregir la actualización del detalle de accionistas en la sección Acciones en Empresas del expediente.
*   CU-86b84za3x - Corrección en la evaluación de objetivos de la evaluación de desempeño cuando no utiliza Selector de Rango.
*   CU-86b84za6y - Corrección en la actualización del detalle de accionistas para la sección Acciones en Empresas del Expediente.
*   CU-86b84zab5 - Correcciones de conversión de tipos en mapper de diccionario a entidad para las secciones del grupo personal del expediente del portal.
*   CU-86b84zp2m - Corrección de la configuración entre las entidades DeteccionNecesidadCapacitacion y ProgramaCapacitacion.
*   CU-86b84zpqc - Corregir la ejecución de procedimientos almacenados configurados en las entidades antes de guardar.
*   CU-86b84zr8z - Corrección modelo duplicado que retornan endpoints.
*   CU-86b850cbe - Corrección en la implementación de la Evaluación de Competencias de la evaluación de desempeño.
*   CU-86b8az1c3 - Corrección de los formatos de fechas válidos en los filtros para obtener los datos de los Smartlists.
*   CU-86b8d6uej - Revisar y corregir validaciones incorrectas al modificar comentarios de evaluado/evaluador de las evaluaciones desempeño.
*   CU-86b8dvb3y - Corregir la asignación de rangos en el logro de objetivos de la evaluación de desempeño cuando el período asociado usa selector de rango.
*   CU-86b8f8mdq - Agregar validaciones de rango a parámetros opcionales de los endpoints GET ALL.
*   CU-86b92yxbw - Corregir los endpoints GetAll y de Conteo de las Consultas de Excel para asegurar el filtrado correcto de resultados mediante el parámetro filterCriteria.
*   CU-86b8abjgv - Al eliminar una evaluación no se eliminan los valores previamente asignados a los KPI, en la sección Logro de Objetivos.
*   CU-86b8cqmzf - Reversión de contratación no permite crear/editar cuando el empleado tiene programa onboarding.
*   CU-86b8dhrfp - Validación incorrecta de campos requeridos en Necesidades de Capacitación.
*   CU-86b8dkwxx - No es posible eliminar el contenido del campo Observación en el KPI’S DEL OBJETIVO de una evaluación por objetivos con KIPI´s con estado pendiente.
*   CU-86b8ea4y3 - Wave Gestión de Talento permite finalizar evaluación de desempeño con objetivos pendientes de evaluar, en comparación de Evolution.
*   CU-86b8gdu83 - Comparación de fechas incorrecta en el detalle de solicitud de justificación de marcas.
*   CU-86b8jd0jy - No se autorizan las evaluaciones de desempeño al finalizarlas con o sin ruta de autorización quedando en estado Pendiente.

## Versión 2.7.0
**\================**
#### 18/AGO/2025
## Nueva funcionalidad
*   DEV-5774 - Análisis de requerimiento de funcionalidades faltantes para EvoWave Analítica.
*   DEV-5835 - Implementar endpoint de conteo de consultas de Excel autorizadas para el usuario con soporte de filtrado de datos.
*   DEV-5847 - Crear endpoint Get que devuelva la configuración de los parámetros de filtrado configurados en las consultas de excel.
*   DEV-5856 - Implementar endpoint de conteo de las plantillas de word autorizadas para el usuario con soporte de filtrado de datos.
*   DEV-5858 - Implementar endpoint de conteo de los reportes autorizados para el usuario con soporte de filtrado de datos.
*   DEV-5879 - Crear endpoint Get que devuelva la configuración de los parámetros de filtrado configurados en las plantillas de word.
*   DEV-5880 - Crear endpoint Get que devuelva la configuración de los parámetros de los reportes.
*   DEV-5887 - Crear controlador para Dashboard e implementar funcionalidad para consultar la metadata del tablero y de los filtros.
*   DEV-5888 - Crear controlador de subrecurso para Gráficos e implementar funcionalidad para consultar la metadata y data de la entidad.
*   DEV-6305 - Agregar funcionalidad para permitir generar archivos de excel a partir de los gráficos configurados.

## Mejora
*   DEV-5788 - Agregar filtrado de datos y seguridad al endpoint GetAll del controlador ConsultaExcelController.
*   DEV-5788 - Agregar filtrado de datos y seguridad al endpoint GetAll del controlador ReporteController.
*   DEV-5788 - Agregar filtrado de datos y seguridad al endpoint GetAll del controlador WordTemplateController.
*   DEV-5863 - Modificar endpoint GetAll de ConsultaExcelController para que permita desactivar la paginación de los resultados de manera opcional.
*   DEV-5865 - Modificar endpoint GetAll de WordTemplateController para que permita desactivar la paginación de los resultados de manera opcional.
*   DEV-5867 - Modificar endpoint GetAll de ReporteController para que permita desactivar la paginación de los resultados de manera opcional.
*   DEV-6200 - Agregar nombres y descripciones traducidas para las plantillas de word, reportes y consultas de excel.
*   DEV-6243 - Modificar el endpoint GetAll de Reportes para que reciba una lista de tipos de documento para filtrar en lugar de uno solo.
*   DEV-6250 - Agregar filtrado por criterio de búsqueda a los endpoints GetAll de Reportes, Plantillas de Word y Consultas de Excel.
*   DEV-6315 - Corrección en la ejecución de procedimientos almacenados, reportes y plantillas de Word.
*   DEV-6371 - Agregar seguridad por país a los endpoints de consulta de las Plantillas de Word y Reportes.
*   DEV-6376 - Implementar soporte para selección de compañía y grupo en la generación de reportes de EvoConnect.
*   DEV-6377 - Implementar soporte para selección de compañía y grupo en la generación de Word Templates de EvoConnect.
*   DEV-6429 - Agregar soporte para filtrado de plantillas de word, reportes y consultas excel cuando el código de país o módulo es nulo.
*   DEV-6496 - Agregar localizaciones para las columnas de la data de los Gráficos.
*   DEV-6294 - Correcciones en parseo de enumeraciones debido a excepciones por valores nulos.
*   DEV-6303 - Agregar validaciones en los métodos de notificación de autorizadores para evitar transacciones innecesarias.
*   DEV-6353 - Corrección de codesmell's en EvoConnect.
*   DEV-6356 - Estandarización de errores Bad Request en EvoConnect.

## Versión 2.6.0
**\================**
#### 23/JUN/2025

### **Nueva Funcionalidad**
*   DEV-4356 - Agregar funcionalidad de consulta de Concursos de selección del expediente del portal.
*   DEV-6147 - Crear un endpoint GET que retorne el listado de subalternos autorizados para el usuario autenticado, para la asignación de jornadas.
*   DEV-6192 - Crear endpoint POST para procesar las asignaciones de jornadas a los empleados.
*   DEV-5792 - Agregar funcionalidad CRUD para la solicitud de equipo o acceso realizada desde el portal.

### **Mejora**
*   DEV-5345 - Corrección en validación de permisos de propiedades al crear/editar registros considerando valores por defecto, en las secciones del Expediente del Portal.
*   DEV-5457 - Corrección en la actualización del Property Bag en registros de las secciones del expediente: error al mantener propiedades eliminadas en la configuración de la entidad.
*   DEV-5487 - Corrección de bug al actualizar registros aún no autorizados en las secciones del expediente: se eliminan los valores de cambio expediente cuando el valor nuevo es igual al valor por defecto del campo en la entidad.
*   DEV-5723 - Corrección de bug en la actualización de propiedades de la sección Adicional del expediente en el portal.
*   DEV-5832 - Ajuste de validación de rango de fechas en edición de ausencias de eventos de capacitación.
*   DEV-5963 - Corrección de bug en competencias del puesto del expediente: permitir agregar conductas sin código pero con descripción.
*   DEV-6071 - Cambiar el verbo HTTP de GET a POST en el endpoint para la sección Posición del expediente en el portal.
*   DEV-6111 - Corrección de bug en la sección Posición del expediente en el portal, debido a fallo en la conversión de tipos numéricos en Oracle.
*   DEV-6153 - Corrección del endpoint de consulta de las evaluaciones consolidadas: listado de objetivos, permisos y rendimiento.
*   DEV-6268 - Implementar ejecución estándar de SPs antes de guardar en DbContextBase.
*   DEV-5240 - Agregar funcionalidad de consulta de sección Personal del expediente del portal.
*   DEV-6288 - Mitigación de vulnerabilidad del parámetro OrderByClause en Smartlist.
*   DEV-6291 - Agregar validación para verificar que no se dupliquen documentos de identificación en el expediente en portal cuando los cambios todavía no se mandan a autorizar.

## Versión 2.5.0
**\================**
#### 08/ABR/2025

### **Nueva Funcionalidad**
*   DEV-5500 - Consulta del progreso de los programas del usuario autenticado para Dashboard para indicadores - Onboarding.
*   DEV-5602 - Funcionalidad de consulta de efectividad del programa para indicadores en Dashboard - Onboarding.
*   DEV-5603 - Funcionalidad de evaluación de las actividades (sin utilizar formulario dinámico) - Onboarding.
*   DEV-5778 - Funcionalidad de consulta del rol del usuario autenticado en los programas de Onboarding.
*   DEV-5527 - Agregar funcionalidad de presupuestos del portal de Evolution a EvoConnect.
*   DEV-5309 - Generación de información para Google Analytics y Featurebase.

### **Mejora**
*   DEV-5442 - Agregar asignación automática de actividades al inscribir participantes a un programa.
*   DEV-5484 - Agregar columna en Tipo Responsable Actividad para determinar si es el Jefe el responsable.
*   DEV-5485 - Modificar validaciones en el cambio de estado de las actividades del tablero - Onboarding.
*   DEV-5581 - Ajuste de fechas de actividades tomando en cuenta el sistema de requisitos - Onboarding.
*   DEV-5593 - Modificar endpoint de consulta de actividades para el tablero para incluir datos del participante cuando el usuario es un responsable y la información sobre evaluación - Onboarding.
*   DEV-5614 - Agregar información del expediente cuando el participante no tiene empleo en endpoint de consulta de participantes para Dashboard - Onboarding.
*   DEV-5634 - Agregar filtrado para ordenamiento por fechas en las actividades para Dashboard - Onboarding.
*   DEV-5635 - Eliminación de entidad AlcancePlantilla del esquema de Onboarding.
*   DEV-5662 - Vulnerabilidad SQL Injection al solicitar los datos de una lista de valores, enviando instrucciones SQL maliciosas a los filterParameters.
*   DEV-5698 - Modificación de la entidad ParticipantePrograma y NotificacionActividadPlantilla.
*   DEV-5714 - Modificación en la relación de las entidades de participantes sin asignar y participante programa.
*   DEV-6209 - Modificación del endpoint de consulta de efectividad de los programas de Onboarding para permitir que el jefe inmediato pueda visualizar los datos de efectividad.
*   DEV-6236 - Corrección del valor máximo de la nota en la evaluación de las actividades.
*   DEV-5760 - Bugs por URLs en Healthchecks.
*   DEV-6179 - Bugs por URLs en Healthchecks.

### **Correcciones**
*   DEV-5977 - Corregir bug en la creación de registros de entidades adicionales cuando tienen tabla anexa.
*   DEV-6096 - Corrección de bug en la finalización de entidades.

## Versión 2.4.0
**\==================**
#### 13/MAR/2025

### **Nueva Funcionalidad**
*   DEV-4926 - Agregar funcionalidad de consulta de la sección Salario del expediente del portal.
*   DEV-4927 - Agregar funcionalidad de consulta de la sección Beneficios Adicionales del expediente del portal.
*   DEV-4928 - Agregar funcionalidad de consulta de la sección Formas de pago del expediente del portal.
*   DEV-4929 - Agregar funcionalidad de consulta de la sección Sustituciones para autorizaciones del expediente del portal.
*   DEV-5103 - Implementación de la evaluación de concursos de selección realizada desde portal.
*   DEV-5081 - Funcionalidad de consulta de Participantes sin Asignar a un Programa de Onboarding.
*   DEV-5082 - Funcionalidad de consulta de las actividades para la pantalla gestionar inconsistencias - Onboarding.
*   DEV-5083 - Funcionalidad de asignación de responsables de las actividades - Onboarding.

### **Mejora**
*   DEV-5152 - Agregar campos faltantes al endpoint GetAsync de las evaluaciones desempeño consolidadas del expediente.
*   DEV-5201 - Corrección de mensaje de validación en la sección de aficiones del expediente por parámetros faltantes para completar traducción.
*   DEV-4523 - Modificación de la Consulta Genérica (tablas, registros) para que puedan retornar JSON o plantilla personalizada.
*   DEV-4548 - Refactorización infraestructura de metadata de autorización (Ver Entidad) I Parte.
*   DEV-4569 - Agregar soporte de property bag a la sección Familiares del expediente del portal.
*   DEV-4570 - Agregar soporte de property bag a la sección Emergencias del expediente del portal.
*   DEV-4574 - Agregar soporte de property bag a la sección Educación del expediente del portal.
*   DEV-4736 - Agregar endpoints GET (all/id) a la Sección Capacitaciones del expediente para mostrar los cambios pendientes de autorización como diccionario.
*   DEV-4737 - Agregar endpoints GET (all/id) a la Sección Educación del expediente para mostrar los cambios pendientes de autorización como diccionario.
*   DEV-4738 - Agregar endpoints GET (all/id) a la Sección Parentesco con Empleados del expediente para mostrar los cambios pendientes de autorización como diccionario.
*   DEV-4739 - Agregar endpoints GET (all/id) a la Sección Capacidades Especiales del expediente para mostrar los cambios pendientes de autorización como diccionario.
*   DEV-4741 - Agregar endpoints GET (all/id) a la Sección Asociaciones del expediente para mostrar los cambios pendientes de autorización como diccionario.
*   DEV-4801 - Agregar endpoints GET (All/Id) para consultar los datos actuales (autorizados) de la sección familiares del expediente respetando los permisos de visualización del usuario.
*   DEV-4802 - Agregar endpoints GET (All/Id) para consultar los datos actuales (autorizados) de la sección Emergencias del expediente respetando los permisos de visualización del usuario.
*   DEV-4804 - Agregar endpoint GET (Id) para consultar los datos actuales (autorizados) de la sección General del expediente respetando los permisos de visualización del usuario.
*   DEV-4819 - Refactorización y correcciones para mejorar el endpoint de consulta dinámica/personalizada de autorizaciones en EvoConnect.
*   DEV-4821 - Crear nuevo controlador y agregar soporte de property bag para la funcionalidad de la sección de Equipo o Acceso del expediente.
*   DEV-4843 - Corrección de bug en la actualización de los registros de las secciones del expediente del portal. (Parte 1).
*   DEV-4882 - Corrección de bug en endpoints de consulta: No se deben incluir propiedades que no pertenecen a la entidad, cuando están en propiedades permitidas, evitando asignar valor null.
*   DEV-4922 - Corrección de bug en la actualización de los registros de las secciones del expediente del portal. (Parte 2).
*   DEV-4924 - Corrección de bug en la actualización de los registros de las secciones del expediente del portal. (Parte 3).
*   DEV-4930 - Crear nuevo controlador y agregar soporte de property bag para la funcionalidad de la sección de Seguros del expediente.
*   DEV-4931 - Crear nuevo controlador y agregar soporte de property bag para la funcionalidad de la sección de Reclamos de Seguro Médico del expediente.
*   DEV-4932 - Crear nuevo controlador y agregar soporte de property bag para la funcionalidad de la sección de Evaluaciones de desempeño del expediente.
*   DEV-5028 - Actualización de EvoConnect al hotfix 1.19.1.15 de Evolution.
*   DEV-5052 - Agregar endpoints de consulta de las evaluaciones de desempeño consolidadas al controlador de evaluación desempeño del expediente en portal.
*   DEV-5070 - Corrección de bugs por validaciones en la sección Educación del expediente en portal.
*   DEV-5071 - Agregar endpoints GET (all/id) a la Sección Cuentas Bancarias del expediente para mostrar los cambios pendientes de autorización como diccionario.
*   DEV-5100 - Corrección de bugs en la sección Empleos Anteriores del expediente en portal.
*   DEV-5105 - Incluir estado de eventos en el listado de capacitaciones del expediente del portal.
*   DEV-5203 - Reestructuración del formato de campos que se retornan en los endpoints de datos actuales de la sección de cuentas de banco del expediente del portal.
*   DEV-5215 - Corrección al defecto DEV-5148: Validaciones duplicadas en campos string requeridos en secciones del expediente.
*   DEV-5220 - Completar soporte para CRUD de property bag en la sección de solicitud de constancias.
*   DEV-5233 - Error al eliminar el property bag de un registro en las secciones del expediente del portal.
*   DEV-5239 - Agregar endpoints GET (all/id) a la Sección Aficiones del expediente para mostrar los cambios pendientes de autorización como diccionario.
*   DEV-5241 - Agregar endpoints GET (all/id) a la Sección de Referencias del expediente para mostrar los cambios pendientes de autorización como diccionario.
*   DEV-5321 - Corrección de error en Observaciones: Permitir contenido HTML seguro en el endpoint que permite modificar la sección general del expediente.
*   DEV-5324 - Corrección de conversión de decimales en la clase convertidora de Capacitaciones (Duración y TotalGastos).
*   DEV-5335 - Aficiones Expediente Portal: Corrección de validación de permisos en propiedades booleanas con valor por defecto false.
*   DEV-5340 - Idiomas Expediente Portal: Corrección de validación de permisos en propiedades booleanas con valor por defecto false.
*   DEV-5344 - Modificar endpoint PostArray en Solicitud de Horas Extra para que reciba el código del centro de costo del Maestro de la solicitud.
*   DEV-5356 - Error al actualizar un registro con property bag que ha sido creado desde módulo.
*   DEV-5432 - Corrección del Endpoint GetAll para incluir archivos adjuntos en solicitudes de horas extra.
*   DEV-5437 - Modificación del endpoint GetAll del controlador de Retiro para incluir los filtros por empleado retirado y estado.
*   DEV-5441 - Corrección de bug en la actualización de los registros de la sección Direcciones del expediente en el portal.
*   DEV-5445 - Corrección en la comparación de XML en el método EqualValues para evitar errores con cadenas vacías.
*   DEV-5507 - Corrección en la comparación de datos de tipo DateTime en el método EqualValues para evitar errores con cadenas vacías.
*   DEV-5516 - Corrección en la localización de Plan Anual Vacación: Ajuste de placeholders.
*   DEV-5049 - Agregar validación de mínimo y máximo de archivos adjuntos equivalente a la configuración de Evolution 1.24.
*   DEV-5194 - Agregar columna en TipoResponsableActividad para identificar al participante como responsable.
*   DEV-5084 - Modificar endpoint que permite asignar participantes a un programa de Onboarding.
*   DEV-5244 - Flujos pendientes de asignación de responsables a las actividades de Onboarding.
*   DEV-5256 - Obtener información de tipos de responsables internos de actividades de Onboarding.

## Version 2.3.0
**\==================**
#### 15/DIC/2024

### **Nueva Funcionalidad**

*   DEV-3721 - Aplicar seguridad de contenido a los endpoints No CRUD/Flujo utilizados en Portal.
*   DEV-4036 - Agregar funcionalidad de Evaluaciones de Desempeño del Portal: Sección General, Logro de Objetivos, Finalización, Comentarios Evaluado/Evaluador, FODA.
*   DEV-4211 - Completar funcionalidad de Evaluación de Competencias de la Evaluación de Desempeño para Portal.
*   DEV-4212 - Agregar funcionalidad de Necesidades de Capacitación de la Evaluación de Desempeño.
*   DEV-4232 - Implementar endpoint para la consulta dinámica de autorizaciones en Evoconnect.
*   DEV-4349 - Agregar funcionalidad para consulta y edición de información adicional del expediente que se realiza desde el portal.
*   DEV-4542 - Agregar parámetro al endpoint Data del SmartlistController para que permita especificar ordenamiento en la petición.
*   DEV-4556 - Aplicar seguridad de contenido a los endpoints No CRUD/Flujo utilizados en Portal (Parte 2).
*   DEV-4752 - Modificación en secciones Parentesco y Cuentas Bancarias relacionadas al Property Bag por bugs detectados en funcionalidades similares.
*   DEV-4567 - Agregar soporte de property bag a la sección Identificación del expediente del portal.
*   DEV-4568 - Agregar soporte de property bag a la sección Documentos del expediente del portal.
*   DEV-4571 - Agregar soporte de property bag a la sección Direcciones del expediente del portal.
*   DEV-4573 - Agregar soporte de property bag a la sección Capacitaciones del expediente del portal.
*   DEV-4453 - Agregar soporte de property bag a la sección Cuentas Bancarias del expediente del portal.
*   DEV-4576 - Agregar soporte de property bag a la sección Parentescos con empleados del expediente del portal.
*   DEV-4578 - Agregar soporte de property bag a la sección Capacidad Especial del expediente del portal.
*   DEV-4580 - Agregar soporte de property bag a la sección Empleos Anteriores del expediente del portal.
*   DEV-4582 - Agregar soporte de property bag a la sección Aficiones del expediente del portal.
*   DEV-4583 - Agregar soporte de property bag a la sección Asociaciones del expediente del portal.
*   DEV-4822 - Agregar soporte de property bag para la sección de Referencias del expediente.
*   DEV-4231 - Implementar endpoints básicos para gestionar las Prioridades de Actividades de Onboarding.
*   DEV-4239 - Agregar endpoint para obtener la información de actividades de programas de onboarding que se necesita para el tablero.
*   DEV-4263 - Implementar endpoints CRUD para TipoActividad.
*   DEV-4308 - Agregar endpoint de consulta de notificaciones de actividades de onboarding.
*   DEV-4387 - Implementar Endpoint de Consulta de Programas de Onboarding.
*   DEV-4428 - Agregar nueva entidad al modelo de onboarding: ParticipanteSinAsignar para almacenar la información de candidatos a participar en programas de onboarding.
*   DEV-4473 - Implementar asignación de participantes a programas de onboarding.
*   DEV-4474 - Agregar Entidad Participantes sin Asignar a Evoconnect.
*   DEV-4678 - Agregar filtro de fecha para el endpoint de consulta de las actividades de onboarding.
*   DEV-4230 - Implementar endpoints básicos para gestionar los Tipos de Responsable de Actividades de Onboarding.
*   DEV-4319 - Implementar funcionalidad catálogo para la entidad Tipo Evaluación del módulo de Onboarding.
*   DEV-4337 - Incluir datos básicos del participante de la actividad asociada a la notificación en el endpoint de MisNotificaciones y preparación de datos de prueba.
*   DEV-4338 - Agregar endpoint patch para poder actualizar campos seleccionados de las actividades de onboarding.
*   DEV-4388 - Analizar, documentar e implementar seguridad de contenido para los endpoints de onboarding implementados.

### **Mejoras**

*   DEV-4059 - Documentar sección consultas reportes e interfaces.
*   DEV-4310 - Agregar detalle de formularios dinámicos al endpoint GET por ID en el controlador de Motivo de Retiro y al endpoint GET por ID en el controlador de Entrevista Retiro.
*   DEV-4314 - Corrección en GET por ID en EntrevistaRetiro para mostrar valores por defecto cuando el retiro no tiene entrevista asociada.
*   DEV-4332 - Agregar información de Centros de Costo al GetDto de Empleo de manera accesible según la asociación de centros de costo con la plaza del empleado.
*   DEV-4466 - Corrección de excepción al consultar las estructuras salariales de los empleados.
*   DEV-4467 - Completar información de personas a contratar en las requisiciones de personal de plaza nueva y puesto nuevo agregando la compañía que muestra Evolution.
*   DEV-4483 - Mejorar la actualización de registros en el expediente del portal excluyendo campos requeridos que el usuario no puede modificar.
*   DEV-4508 - Incorporar datos del puesto en el endpoint GET (by id) para requisiciones de tipo 'plaza nueva'.
*   DEV-4554 - Corrección de bug en el endpoint GetById del controlador de Reclamo de Seguro Médico: No devuelve concepto ni estado del reclamo.
*   DEV-4559 - Modificar endpoints POST/PUT del controlador de la sección Parentescos con Empleados del expediente del portal para recibir diccionario dinámico en vez de DTO.
*   DEV-4560 - Modificar endpoints POST/PUT del controlador de la sección Educación del expediente del portal para recibir diccionario dinámico en vez de DTO.
*   DEV-4561 - Modificar endpoints POST/PUT del controlador de la sección Capacitaciones del expediente del portal para recibir diccionario dinámico en vez de DTO.
*   DEV-4562 - Modificar endpoints POST/PUT del controlador de la sección Capacidad Especial del expediente del portal para recibir diccionario dinámico en vez de DTO.
*   DEV-4563 - Modificar endpoints POST/PUT del controlador de la sección Idiomas del expediente del portal para recibir diccionario dinámico en vez de DTO.
*   DEV-4564 - Modificar endpoints POST/PUT del controlador de la sección Referencias del expediente del portal para recibir diccionario dinámico en vez de DTO.
*   DEV-4565 - Modificar endpoints POST/PUT del controlador de la sección Aficiones del expediente del portal para recibir diccionario dinámico en vez de DTO.
*   DEV-4566 - Modificar endpoints POST/PUT del controlador de la sección Asociaciones del expediente del portal para recibir diccionario dinámico en vez de DTO.
*   DEV-4575 - Modificar endpoints POST/PUT de la Sección Familiares del expediente del portal para recibir diccionario dinámico en vez de DTO.
*   DEV-4577 - Modificar endpoint POST que modifica la Sección General del expediente del portal para recibir diccionario dinámico en vez de DTO.
*   DEV-4581 - Modificar endpoints POST/PUT de la Sección Emergencias del expediente del portal para recibir diccionario dinámico en vez de DTO.
*   DEV-4597 - Corrección de bug en endpoints Post y Put del controlador de Reclamo de Seguro Médico: Validación incorrecta del familiar o beneficiario del reclamo de seguro médico.
*   DEV-4599 - Agregar archivos adjuntos de los conceptos en el endpoint Get por Id de los reclamos de seguro médico.
*   DEV-4629 - Agregar soporte para subir archivos de los conceptos de reclamo de seguro médico.
*   DEV-4660 - Corregir validaciones de seguridad en el controlador de requisición de personal de tipo puesto nuevo.
*   DEV-4727 - Modificar endpoints POST/PUT de la sección Direcciones del expediente del portal para recibir diccionario dinámico en vez de DTO.
*   DEV-4729 - Modificar endpoints POST/PUT de la Sección Empleos Anteriores del expediente del portal para recibir diccionario dinámico en vez de DTO.
*   DEV-4761 - Agregar validaciones y datos faltantes al endpoint de asignación de vacaciones del Plan Anual de Vacaciones.
*   DEV-4787 - Corregir excepción al guardar una evaluación de evento de capacitación por empleado.
*   DEV-4820 - Crear nuevo controlador y agregar soporte de property bag para la funcionalidad de la sección de competencias curriculares del expediente.
*   DEV-4832 - Corrección en la sección Documentos del expediente (se debe incluir la propiedad CodigoArchivo en la clase convertidora).
*   DEV-4365 - Corregir funcionalidad de guardado y actualización de entrevistas de retiro para asignar correctamente el valor posible en los campos que corresponde.
*   DEV-4835 - Corrección de envío de notas en formularios dinámicos de evaluaciones de eventos por empleados.
*   DEV-4783 - Implementar endpoints de consulta de eventos de capacitación para complementar la sección capacitaciones del expediente.
* * *

## Versión 2.2.0.0
**\================**
#### 20/SEP/2024

### **Nueva Funcionalidad**

*   DEV-3541 - Agregar CRUD de Cuentas Bancarias del Expediente desde el Portal.
*   DEV-3542 - Agregar CRUD de Aficiones del Expediente desde el Portal.
*   DEV-3543 - Agregar CRUD de Documentación del Expediente desde el Portal.
*   DEV-3575 - Agregar CRUD de Asociaciones del Expediente desde el Portal.
*   DEV-3613 - Funcionalidad de consultas Genéricas.
*   DEV-3615 - Sección de Mi Expediente, CRUD de Beneficios Adicionales.
*   DEV-3616 - Agregar CRUD de Capacidad Especial del Expediente desde el Portal.
*   DEV-3626 - Sección de Mi Expediente, CRUD de sección de Equipo o Acceso.
*   DEV-3636 - Agregar CRUD de sección de Seguros.
*   DEV-3655 - Sección de Mi Expediente, CRUD de Reclamos de seguro médico.
*   DEV-3666 - Completar funcionalidad de Evaluaciones de desempeño desde el Portal.
*   DEV-3667 - Sección de educación, de mi expediente.
*   DEV-3680 - Agregar CRUD de Documentos de Identificación desde el Portal.
*   DEV-3700 - ACTUALIZAR Evoconnect con cambios de la versión 1.19.1.14 de Evolution.
*   DEV-3701 - Aplicar correctamente las validaciones de seguridad de contenido al crear, modificar y eliminar los datos actuales y corrección de bugs al consultar registros de la sección documentos de identificación del expediente en el portal.
*   DEV-3702 - Corrección de bugs al consultar los datos actuales de la sección evaluaciones de desempeño del expediente en el portal e incluir las evaluaciones consolidadas a las consultas.
*   DEV-3703 - Aplicar correctamente las validaciones de seguridad de contenido al crear, modificar y eliminar los datos actuales y corrección de bugs al consultar registros de la sección cuentas bancarias del expediente en el portal.
*   DEV-3708 - Aplicar correctamente las validaciones de seguridad de contenido al crear, modificar y eliminar los datos actuales y agregar los endpoints de consulta de datos actuales de la sección capacidad especial del expediente en el portal.
*   DEV-3710 - Agregar funcionalidad para cambios sobre la sección Idiomas del expediente en el portal.
*   DEV-3711 - Aplicar correctamente las validaciones de seguridad de contenido, al crear, editar, eliminar o consultar los datos actuales de la sección Educación del expediente en el portal.
*   DEV-3713 - Aplicar correctamente las validaciones de seguridad de contenido, al crear, modificar, eliminar o consultar los datos actuales de la sección Documentación del expediente en el portal y agregar validaciones de fluent.
*   DEV-3714 - Aplicar correctamente las validaciones de seguridad de contenido, al crear, modificar, eliminar o consultar los datos actuales de la sección Parentesco con Empleados del expediente en el portal y agregar validaciones de fluent.
*   DEV-3715 - Agregar funcionalidad de consulta de la sección Equipo o acceso del expediente en el portal.
*   DEV-3716 - Agregar funcionalidad de consulta de la sección Seguro del expediente en el portal.
*   DEV-3717 - Agregar funcionalidad de consulta de la sección Reclamo de seguro médico del expediente en el portal.
*   DEV-3718 - Agregar funcionalidad de consulta de los datos actuales de las secciones Aficiones y Asociaciones del expediente en el portal.
*   DEV-3719 - Agregar funcionalidad de consulta de los datos actuales de la sección contrataciones del expediente en el portal.
*   DEV-3720 - Agregar funcionalidad de consulta de Documentos Gestionados.
*   DEV-3722 - Agregar métodos para verificar las acciones permitidas (permite crear, modificar, eliminar) sobre una sección del expediente en el servicio de SeccionExpedienteService.
*   DEV-3723 - Agregar la infraestructura adecuada para validar las relaciones de entidades primarias que no cuentan con DELETE CASCADE e Implementar para relaciones de Empleo.
*   DEV-3725 - Agregar funcionalidad para Evaluación de eventos de capacitación.
*   DEV-3840 - Agregar endpoints de consulta para la sección Competencias curriculares del Expediente.
*   DEV-3910 - Integración de Asistente de OpenAI FITOBOT para facilitar la ejecución de acciones de un usuario.
*   DEV-3996 - Agregar consulta de la Sección de Contrataciones del Expediente del Portal.
*   DEV-3997 - Agregar Sección de Capacitaciones del Expediente del Portal.
*   DEV-3998 - Agregar Sección de Empleos Anteriores del Expediente del Portal.
*   DEV-3999 - Agregar Sección de Referencias del Expediente del Portal.
*   DEV-4056 - Agregar funcionalidad de la sección Gestión de Talento del Expediente del portal.
*   DEV-4129 - Agregar convención en configuración EF para que no se utilice la cláusula OUTPUT cuando se actualizan tablas con campos calculados y Triggers.
*   Se agregó Health Check para verificar el estado de la aplicación y los servicios asociados.
*   Se agregó Open Telemetry para la trazabilidad de las peticiones y la generación de métricas.

### **Mejoras**

*   DEV-3871 - Agregar parámetro en la solicitud para obtener la data de una lista de valores para indicar si se quiere localizar la descripción de cada item.
*   DEV-3891 - Agregar manejo de compatibilidad de versiones de SQL Server con el driver de Entity Framework.
*   DEV-3948 - Agregar el centro de costo a AsociacionCentroCostoGetDto e incluirse en getall y get (id) del controlador de esta entidad.
*   DEV-3987 - Cambiar la transacción que se utiliza en la finalización de Movimientos para utilizar la de Entity Framework.
*   DEV-4041 - Agregar información de Ingresos y Descuentos a la consulta de ISR Calculado por id.
*   DEV-3800 - Agregar la data de archivos adjuntos a los endpoint GET (por id) de las entidades de portal que los soportan y que actualmente no cuentan con ellos.
*   DEV-3818 - Agregar campos localizados para los campos de TipoAyudaEconomica que soportan tokens de localización.
*   DEV-3835 - Mejoras de Documentación Swagger para Solicitud de Incapacidades.
*   DEV-3836 - Mejoras de Documentación Swagger para Solicitud de Ingresos Eventuales.
*   DEV-3837 - Mejoras de Documentación Swagger para Solicitud de Movimiento.
*   DEV-3838 - Mejoras de Documentación Swagger para Solicitud de Permiso.
*   DEV-3839 - Mejoras de Documentación Swagger para Solicitud de Reconocimiento.
*   DEV-3709 - Arreglar Documentación Swagger para Solicitud de Descuentos Eventuales.
*   DEV-3964 - Actualización de la dependencia EnterpriseLibrary.Data.NetCore para ser compatible con versiones más recientes de .NET Core y Entity Framework.
*   DEV-3983 - Modificar funcionalidad de escalas de clase salarial para que sea subrecurso de la clase salarial.
*   DEV-4000 - Mejoras de Documentación Swagger de controladores para la Sección Consultas del Portal.
*   DEV-4001 - Mejoras de Documentación Swagger de controladores para la Sección Acciones del Portal.
*   DEV-4034 - Aplicar correctamente la Seguridad de Contenido en los Endpoints para Portal a nivel de CRUD y Flujo.
*   DEV-3675 - Agregar asignación de ExpedienteDigitaCodigo en el delegado anónimo de SustitucionTemporalController.
*   DEV-3724 - Completar funcionalidad para Declaraciones Juradas de usuario.

### **Correcciones**

*   DEV-4052 - Correcciones de errores reportados en la Solicitud de Incremento.
*   DEV-4058 - Corrección de Bugs para la Solicitud de Movimientos.
*   DEV-4060 - Corregir la obtención de canales de notificación del expediente porque solo se obtenía el primer dispositivo de usuario registrado.
*   DEV-3799 - Corregir los endpoints de carga y descarga de archivos adjuntos para que asignen las propiedades de navegación de la entidad antes de validar seguridad de contenido.
