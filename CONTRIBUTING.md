# Contribuir

Antes de modificar el motor, lee `docs/ARQUITECTURA.md` y `docs/DESARROLLO.md`. Reporta defectos mediante issues usando **solo ejemplos sintéticos**; nunca compartas Excel de la empresa. Usa una rama por cambio y agrega pruebas de regresión.

Cada PR debe ejecutar `python -m unittest discover -v` y `python -m compileall -q app.py processor.py ooxml.py tests`. No cambies mapeos o validaciones comerciales sin verificar su correspondencia con una plantilla real vigente, fuera de GitHub.
