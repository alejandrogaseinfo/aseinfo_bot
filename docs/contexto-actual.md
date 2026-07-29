# Contexto actual de Libras

> Documento de continuidad para cualquier persona o chat nuevo que retome el
> proyecto. Fecha de consolidación: 2026-07-29.

## Objetivo

Preparar `Libras`, un asistente interno, para que consulte documentación
autorizada desde Microsoft 365 Agents Playground y posteriormente pueda
publicarse en Microsoft Teams. La publicación en Teams todavía no está
autorizada y no debe ejecutarse.

## Alcance documental autorizado

La autorización recibida se basa en este enlace de SharePoint:

`https://aseinfocorp.sharepoint.com/sites/Soportealcliente/Documentos%20compartidos/Forms/AllItems.aspx?id=%2Fsites%2FSoportealcliente%2FDocumentos%20compartidos%2FSOLUCIONES`

Ese enlace apunta a la carpeta `Documentos compartidos/SOLUCIONES`. Por tanto,
el bot puede consultar cualquier documento de esa carpeta y sus subcarpetas,
pero no otras bibliotecas o carpetas de SharePoint. En particular,
`ReadME Hotfixes`, Manuales, Documentos de Apoyo y cualquier otra ubicación
quedan fuera hasta recibir autorización explícita.

## Arquitectura vigente

```text
Microsoft 365 Agents Playground / Teams
        -> app-libras-prod
        -> Azure AI Search: srch-libras-prod / libras-docs
        <- sincronización de aplicación desde SharePoint/SOLUCIONES
```

- App Service: `app-libras-prod`, Resource Group `rg-libras-prod`, Central US.
- Índice de producción: `libras-docs` en `srch-libras-prod`.
- Aplicación de ingesta: `libras-sharepoint-ingestion-prod`.
- Site ID, drive ID y secreto están en archivos de entorno/Key Vault; no se
  deben copiar a documentación, Git, mensajes ni logs.
- La capacidad multi-fuente que existe en el código es reutilizable, pero no
  significa que todas las fuentes estén autorizadas. La configuración activa
  debe contener solo el drive de `Documentos compartidos` y
  `SHAREPOINT_FOLDER_PATH=SOLUCIONES`.

## Estado técnico

- El flujo de recuperación con Azure AI Search está implementado.
- Se admiten documentos legibles como PDF, DOCX, XLSX, TXT, CSV, SQL, XML,
  RDLC, ASPX, PowerShell, BAT y JSON.
- La respuesta exige evidencia recuperada y enlace SharePoint; sin evidencia,
  el bot debe reconocer la limitación y no inventar.
- La separación contextual Guatemala–El Salvador está cubierta por las
  pruebas de recuperación; no se deben mezclar países, versiones ni fuentes.
- El backend productivo respondió `ready` durante la validación previa y las
  pruebas automatizadas pasan: **75 pruebas, OK**.
- El commit de consolidación anterior es `d7b1222`.
- Las cifras antiguas de 15 PDFs y 158 fragmentos que aparecen en la bitácora
  de producción son históricas y no deben tomarse como inventario actual.

## Pruebas realizadas

En Microsoft 365 Agents Playground se validaron los casos P1, P2, P3, P5,
P6, P7, P8 y P9. P4 Guatemala respondió sin evidencia cuando no había respaldo
autorizado; P4 El Salvador recuperó evidencia específica sin mezclar una
fuente guatemalteca. El detalle está en
[evaluacion-piloto.md](evaluacion-piloto.md).

## Pendientes antes de solicitar publicación

1. Ejecutar una sincronización/reconstrucción del índice con el alcance
   corregido: solo `SOLUCIONES`.
2. Confirmar que el índice no conserva documentos de `ReadME Hotfixes` ni de
   otras fuentes.
3. Repetir en Playground una prueba positiva con enlace de `SOLUCIONES`, una
   pregunta sin evidencia y las pruebas de separación Guatemala–El Salvador.
4. Registrar la evidencia final en
   [plan-pruebas-playground.md](plan-pruebas-playground.md) y
   [evaluacion-piloto.md](evaluacion-piloto.md).
5. Solo después de completar lo anterior, preparar la solicitud de autorización
   para publicación en Teams. No publicar automáticamente.

## Cómo retomar el trabajo

Leer en este orden:

1. Este documento.
2. [produccion-semana.md](produccion-semana.md), para infraestructura y
   pendientes operativos.
3. [azure-ai-search-sharepoint.md](azure-ai-search-sharepoint.md), para
   configuración de SharePoint e ingesta.
4. [plan-pruebas-playground.md](plan-pruebas-playground.md), para ejecutar las
   pruebas.

Antes de cambiar código, comprobar `git status`, no imprimir secretos y
mantener `ReadME Hotfixes` fuera del alcance activo.
