# Investigación Oryx: extracción y publicación AI-first

## Evidencia

- ZIP enviado: `output/libras-backend-ai-first-oryx-compatible-20260813-bundle.zip`.
- El ZIP es plano y contiene `ai_first.py` y `handler.py` en la raíz.
- `.deployment` activa explícitamente `SCM_DO_BUILD_DURING_DEPLOYMENT=true` y
  `ENABLE_ORYX_BUILD=true`.
- Oryx generó `output.tar.zst` con `./ai_first.py` y `./handler.py`.
- SSH confirmó en la instancia activa: `handler.py` presente, `ai_first.py`
  ausente; `import ai_first` falla con `ModuleNotFoundError`.

## Conclusión

La pérdida no ocurre en el ZIP ni en la creación del tar. Ocurre entre el
directorio comprimido producido por Oryx y el árbol activo
`/home/site/wwwroot`. Las entradas `./ai_first.py` y `./handler.py` son rutas
válidas de raíz; ambas deberían materializarse juntas. La presencia de
`handler.py` no prueba que el paquete nuevo se haya activado: puede proceder
del árbol anterior, coherente con que la revisión activa siguiera siendo
`df67f34`.

Con `ENABLE_ORYX_BUILD=true`, OneDeploy recibe un ZIP fuente para compilar,
no un árbol preconstruido listo para copiar. `CompressDestinationDir=true`
hace que Oryx empaquete su destino intermedio; el estado `complete=true` solo
confirma la operación de despliegue, no que cada miembro del tar haya quedado
en el árbol activo. La verificación física posterior es por tanto obligatoria.

## Formato que debe aceptarse

Para el modo actual, el gate de aceptación debe comprobar el árbol final, no
solo el ZIP ni `output.tar.zst`:

```bash
test -f /home/site/wwwroot/ai_first.py
test -f /home/site/wwwroot/handler.py
PYTHONPATH=/home/site/wwwroot python -c "import ai_first, handler"
```

Si cualquiera falla, el despliegue no es válido para AI-first. No se debe
activar `USE_AI_FIRST_EXPERIMENTAL`.

Se añadió `scripts/validate_post_deployment_ai_first.sh` para ejecutar este
gate desde SSH → Application. No despliega, reinicia ni cambia configuración.

## Estado operativo

No se generó bundle nuevo, no se inició OneDeploy ni rollback, no se abrió
Teams y `USE_AI_FIRST_EXPERIMENTAL=false` permanece intacto.
