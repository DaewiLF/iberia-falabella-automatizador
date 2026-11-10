# Desarrollo, calidad y mantenimiento

## Preparación

Requiere Python 3.11 o superior; **no tiene dependencias Python externas** para el servidor. Clona o descomprime el repositorio y ejecuta:

```bash
python -m unittest discover -v
python -m compileall -q app.py processor.py ooxml.py tests
python app.py --no-browser --port 5000
```

En Windows se puede ejecutar `py -3 -m unittest discover -v` y `iniciar_windows.bat`.

## Estructura

- `tests/test_security.py`: ZIP malicioso, encabezados duplicados, CSV seguro.
- `tests/test_api.py`: servidor HTTP real en puerto aleatorio y auditoría JSON.
- `tests/test_synthetic_pipeline.py`: flujo real con libros OOXML inventados y preservación de contenido.
- `test_app.py`: pruebas de integración opcionales con Excel reales, activadas exclusivamente mediante `IBERIA_TEST_TEMPLATE`, `IBERIA_TEST_RESP`, `IBERIA_TEST_FOTOS` e `IBERIA_TEST_PRECIOS`, sin incorporarlos a GitHub.
- `.github/workflows/tests.yml`: ejecuta pruebas Python 3.11 y 3.13 en Windows y Linux.

## Cómo agregar una nueva regla

1. Crear una prueba sintética que falle al reproducir el defecto o la nueva necesidad.
2. Implementar la regla en `processor.py`. Para cambios de celdas preservar la API `write_unchanged_template`.
3. Ejecutar todas las pruebas; revisar también posibles impactos en celdas protegidas.
4. Revisar la vista previa con una copia de la plantilla oficial **fuera del repositorio**.
5. Documentar cambios y límites en `CHANGELOG.md` y `docs/REGLAS_FALABELLA.md`.

## Gestión de cambios de plantillas

Un cambio de archivo Falabella debe tratarse como cambio de contrato: comprobar nombres de hojas, fila de encabezados, columnas obligatorias y listas/validaciones, actualizar `default_config()` y pruebas sintéticas, y repetir una carga piloto. No asumir que una nueva categoría tiene los mismos campos obligatorios.

## Ejecutable Windows

`crear_exe_windows.bat` usa PyInstaller de forma opcional y genera una distribución `onedir`. No viene compilada ni certificada. Ejecutar en Windows con Python y red, validar inicio y descarga con una copia de prueba. No subir `dist/` automáticamente al repositorio.

## Control de versiones y privacidad

No subir archivos reales, reportes, historiales ni credenciales. `git status` debe mostrar solo código, documentación y plantilla de precios **vacía**. El proyecto no declara licencia open source; para un repositorio empresarial privado se deben seguir las políticas internas de propiedad intelectual.
