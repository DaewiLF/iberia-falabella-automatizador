# Implementación: seguridad, auditoría y GitHub

Referencia: `../specs/2026-11-10-hardening-github-design.md`

## Tarea 1: pruebas sintéticas de seguridad del motor
- Crear `tests/test_security.py` con XLSX OOXML mínimos sin datos reales.
- Casos: ZIP con archivos duplicados, ruta fuera de estructura, expansión excesiva, y encabezado alternativo duplicado.
- Ejecutar pruebas nuevas: fallan antes de modificar producción.
- Endurecer `ooxml.safe_xlsx` y `processor.prepare_source`.
- Ejecutar pruebas nuevas y suite existente.

## Tarea 2: exportación segura y reporte detallado
- Prueba de CSV con valor iniciado en fórmula; falla antes de corregir.
- Escapar campos de texto con prefijos peligrosos en `processor.report_csv`.
- Prueba de exportación JSON por token válido y token inexistente.
- Incorporar endpoint `/api/report-json/<token>.json` y botón de descarga de JSON en la UI.
- Ejecutar conjunto completo.

## Tarea 3: prácticas de mantenimiento y entrega
- `.gitignore`, `.gitattributes`, `pyproject.toml`, workflow CI en Python 3.11 y 3.13 Windows/Linux.
- Documentación de arquitectura, operación, seguridad, pruebas, mantenimiento y política de datos.
- Actualizar identificación de versión, manual y CHANGELOG.
- Verificar `python -m unittest discover -v`, `python -m compileall -q`, `git status` y contenido del ZIP.
- Crear commit local; paquete fuente listo para un repo GitHub privado.

## Revisión de riesgos
- Verificar que ningún ZIP XLSX privado quede en el repositorio fuente.
- Revisar consistencia de `can_publish` y preservación OOXML en pruebas reales.
- Incluir advertencias por pruebas que requieren Windows/Seller Center.
