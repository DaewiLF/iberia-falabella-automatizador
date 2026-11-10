# Validación y cambios — versión 2.2

## Mejoras implementadas

| Prioridad | Requisito | Estado |
|---|---|---|
| Crítica | Validación de hojas y encabezados, con autodetección y mapeos JSON | Implementado |
| Crítica | Detección de SKU duplicados, ambiguos y SKU padre discrepante | Implementado |
| Crítica | Validación de campos esenciales, dimensiones, precio, GTIN y URL principal | Implementado |
| Crítica | Comparación de las partes OOXML, atributos de estilo y celdas permitidas | Implementado |
| Alta | Vista previa de cambios por celda antes de descargar | Implementado |
| Alta | Precios exactos por SKU/pack, archivo de precios finales, precedencia clara | Implementado |
| Alta | Fotos de productos compuestos con mapeo manual o inferencia inequívoca | Implementado |
| Media | Selección múltiple de padres y filtrado por responsable | Implementado |
| Media | Configuración JSON de hojas, encabezados y columnas | Implementado |
| Media | Reportes CSV y filtros por estado/SKU | Implementado |
| Media | Historial mínimo y preferencias locales | Implementado |
| Media | Script para crear un EXE Windows con PyInstaller | Incluido, compilación Windows pendiente |
| Opcional | Recalcular el Excel de precios mediante Excel para Windows | Script COM incluido, prueba en Windows pendiente |
| Próxima integración | Publicación directa en Seller Center | No disponible: requiere autorización e integración del marketplace |
| Próxima integración | Reglas de otros marketplaces | No verificadas: faltan plantillas y reglas oficiales |

## Pruebas realizadas

- 11 pruebas automatizadas con archivos reales e inferencia de packs: **correctas**.
- Libro comercial de 7 SKU: coincidencia exacta de 7 productos.
- Cambio de precio de prueba en 7 celdas N: **7 cambios exactos**, ninguna parte ajena a la hoja fue modificada.
- Caso de SKU vendedor duplicado en Responsables: se detecta y se bloquea la fila.
- Caso de precio/EAN faltante: salida **no publicable** y descarga identificada como borrador.
- Plantilla con SKU vacíos y filas preformateadas: recuperación de 7 registros.
- Mapeo alternativo de dimensiones: escribe las columnas previstas.
- Importación de precio final desde un segundo Excel (incluido el precio de pack): correcta.
- Prueba de API local: vista previa, bloqueo de descarga sin confirmar, aprobación, descarga XLSX, CSV e historial: correcta.

**No se ha realizado una subida real a Falabella Seller Center, ni se ha probado PyInstaller o Microsoft Excel COM en un PC Windows.** La validez final de los datos de producto y el GTIN/GS1 requiere verificación comercial externa.


## Hotfix 2.1: celdas XML autocerradas

- Se corrigió `CELL_RE` para que `<c r="K5" .../>` no abarque también el nodo de `L5`.
- Se añadieron pruebas con la celda K5 vacía y la edición de la celda L5.
- La validación estricta de estilos/partes OOXML permanece activa.

## Mejoras 2.2 verificables

- Seguridad de lectura ZIP/XLSX frente a entradas duplicadas, traversal, macros y expansión anormal.
- Encabezados ambiguos no se asignan silenciosamente.
- CSV seguro ante datos que parecen fórmulas Excel.
- Auditoría JSON y hashes de todas las fuentes cargadas.
- Pruebas sintéticas para GitHub Actions sin datos privados.
- Repositorio local con documentación y CI; publicación remota pendiente de creación manual del repositorio.
