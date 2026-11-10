## Propósito
Describe el problema, sus archivos y por qué se requiere el cambio.

## Riesgos
- [ ] Comprueba que no se incluyan Excel reales, precios, fotos ni archivos de historial.
- [ ] Si toca `ooxml.py`, conserva las partes internas y los estilos del libro original.
- [ ] No inventa precios ni identificadores GS1/EAN.
- [ ] Revisó los efectos sobre SKU duplicados y packs.

## Verificación
- [ ] `python -m unittest discover -v`
- [ ] `python -m compileall -q app.py processor.py ooxml.py tests`
- [ ] Si corresponde, prueba manual con archivos empresariales **fuera de GitHub**.

## Evidencias
Indica los casos de prueba añadidos y, si hay validación en Seller Center, el resultado sin compartir datos personales o comerciales.
