# Hotfix Nomina 2026-07-01

## Resumen

Este hotfix corrige un error de validacion posterior a la actualizacion del modulo de nomina.

## Advertencia De Instalacion

Antes de instalar el paquete, ejecutar el script `ajuste_nomina_previo.sql` y confirmar que la base ya tenga aplicada la estructura del paquete base `2026.06`.

## Sintoma Conocido

Si el usuario instala el hotfix sin ejecutar el ajuste previo, el sistema puede fallar al guardar movimientos y mostrar errores posteriores a la actualizacion.

## Resolucion

Ejecutar el script previo, reinstalar el hotfix y repetir la prueba funcional.
