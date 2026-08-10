# Seguridad de Libras

## Alcance

Libras es un bot interno de Microsoft Teams. La fuente documental productiva
actual es SharePoint autorizado, sincronizado hacia Azure AI Search. Las
integraciones de ClickUp, Jira, GitHub y `downloads.aseinfo.net` son fases
posteriores; no deben asumirse activas solo porque existan adaptadores o planes
en el repositorio.

## Reportar un problema

No publiques credenciales, tokens, URLs privadas, documentos de SharePoint ni
datos personales en issues o pull requests. Para reportar una vulnerabilidad,
contacta al responsable técnico de Aseinfo por el canal interno autorizado e
incluye:

- descripción breve del problema;
- pasos mínimos para reproducirlo;
- impacto observado;
- evidencia sin secretos ni datos reales innecesarios.

## Reglas de seguridad

- Nunca se almacenan secretos en Git, documentación pública ni logs.
- Las variables `.env`, `env/.env.*.user` y tokens son únicamente locales o se
  administran mediante Key Vault.
- ClickUp se integrará con permisos de solo lectura y solo después de aprobar
  la URL de redirección registrada.
- Las consultas deben responder con evidencia de fuentes autorizadas; no deben
  exponer contenido fuera del alcance documental.
- Los cambios de configuración o permisos productivos requieren revisión del
  responsable técnico y del administrador correspondiente.
