# Reglas de datos y mapeo

## Mapeo base

| Campo destino | Columna Falabella | Fuente por defecto |
|---|---|---|
| Size | I | Responsables · Talla |
| SKU del vendedor | J | Responsables · SKU HIJO/VENDEDOR |
| SKU padre | L | Responsables · SKU PADRE; opcionalmente SKU hijo de talla menor |
| Descripción | D | Responsables · Descripción (solo si se solicita) |
| PriceFalabella | N | Precios finales/manualmente/conservado según precedencia |
| Ancho | AK | Responsables · Ancho |
| Largo | AL | Responsables · Alto (modo legado) / Profundidad (alternativo) |
| Alto | AM | Responsables · Profundidad (modo legado) / Alto (alternativo) |
| Peso | AN | Responsables · Peso |
| Fotos | AQ–AX | URLs de fotos / componentes aprobados |

El mapeo de las dimensiones debe confirmarse físicamente. El modo `smallest_child` para el SKU padre en L requiere validar cómo exige agrupar variantes la categoría en Falabella.

## Clasificación de errores

- **Bloqueado:** conflicto de identidad SKU, precio contradictorio, campo esencial o EAN requerido inválido, foto principal inválida, etc.
- **Advertencia:** falta de precio actualizado conservando uno existente, imagen de origen no localizada pero imagen previa válida, categoría no exhaustivamente verificada.
- **Listo para revisión:** no hay errores bloqueantes dentro de la lógica controlada. No equivale a aceptación del marketplace.

## Políticas de datos

- SKU de búsqueda se normaliza, SKU escrito se conserva exactamente.
- Precio del pack requiere valor explícito; no se extrapola automáticamente.
- EAN/GTIN: validación checksum ≠ certificación/registro en GS1.
- La plantilla base no se sobreescribe.
- Al aparecer campos obligatorios nuevos, primero actualizar pruebas, mapeo y validación antes de usar otra versión de plantilla.
