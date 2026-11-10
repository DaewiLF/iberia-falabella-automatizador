# Historial de cambios

## 2.2.0 — 2026-11-10

- Rechazo temprano de ZIP/XLSX con partes duplicadas, rutas no canónicas, contenido macro, cifrado y expansión sospechosa.
- Cabeceras alternativas ambiguas reportadas como error de importación.
- Reportes CSV protegidos ante inyección de fórmulas desde celdas de origen.
- Auditoría descargable JSON con detalle de filas, cambios, validaciones y SHA-256 de entradas.
- Control adicional `Sec-Fetch-Site` para solicitudes HTTP de mutación.
- Suite sintética independiente de datos reales y CI Windows/Linux Python 3.11/3.13.
- Documentación de operación, arquitectura, seguridad, reglas y publicación GitHub.

## 2.1.0 — 2026-11-10

- Corregido el lector XML de celdas autocerradas que podía reportar falsamente `Integridad: falta L5`.

## 2.0.0 — 2026-11-10

- Vista previa, validaciones por producto, mapeo por SKU, precios por pack, composición de fotos, reportes CSV, preferencias e historial mínimo.
