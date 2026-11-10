# Manual de operación

## Inicio

En Windows, descomprime la carpeta y ejecuta `iniciar_windows.bat` con Python 3.11+. El servicio muestra `http://127.0.0.1:5000`. También puedes iniciar con `python app.py --no-browser --port 5001`.

## Archivos que puedes cargar

- **Falabella**: la plantilla oficial `.xlsx` vigente con hojas, estilos y filas preparadas. **Obligatoria**.
- **Responsables**: SKU padre, SKU hijo/vendedor, talla, medidas, peso, responsable. **Obligatoria**.
- **Fotos**: URLs por producto/componente, con estado aprobado.
- **Precios**: hoja de cálculo original de precios, cuando las fórmulas contienen resultados guardados.
- **Precios finales**: la plantilla genérica de `SKU` y `Precio Final`, para valores aprobados y packs.
- **Configuración**: JSON opcional para cambio de columnas/encabezados.

## Flujo recomendado

1. Guarda una copia de la plantilla recibida de Seller Center, sin alterarla.
2. Adjunta Falabella + Responsables; añade fotos y precios cuando corresponda.
3. Filtra uno o más SKU padre, separados por comas, punto y coma o líneas; opcionalmente por responsable exacto.
4. Define correctamente `Formato de SKU padre` y `Mapeo de dimensiones` según medición física y reglas de Falabella.
5. Si necesitas packs, especifica composición en «Reglas avanzadas» cuando la inferencia por componentes no sea inequívoca.
6. Pulsa **Analizar y previsualizar**. Revisa productos bloqueados, advertencias y el antes/después de cada celda.
7. Descarga el **reporte CSV** para trabajar observaciones o **auditoría JSON** para guardar el detalle técnico con hash de las fuentes.
8. Confirma la revisión. Si hay errores bloqueantes, solo podrás descargar un borrador `NO PUBLICAR`.
9. Realiza una prueba de carga real en Seller Center con pocos productos antes de cualquier carga masiva.

## Precedencia de precios

1. Precio manual por SKU hijo.
2. Precio manual por SKU padre.
3. Archivo de precios finales por SKU hijo.
4. Archivo de precios finales por SKU padre.
5. Archivo clásico de precios por SKU hijo cuando existe valor calculado.
6. Precio uniforme CLP, solo si aplica a todas las variantes seleccionadas.
7. Conservación del precio original cuando no hay reemplazo válido.

No se suman precios individuales para inventar el precio de un pack. Si existe un precio incompatible en la misma fuente, revisa la coincidencia y corrige el dato.

## Fotografías de packs

Cuando el SKU del pack es una concatenación inequívoca de SKU de componentes con fotos aprobadas, la aplicación toma primero una foto principal por componente y después secundarias, hasta el límite de 8. Puedes definir una relación explícita `SKU-PADRE = COMPONENTE1, COMPONENTE2` en reglas avanzadas. Nunca publica automáticamente una coincidencia ambigua.

## Errores habituales

- **Integridad: falta L5**: era un error del lector de celdas autocerradas en v2.0, corregido desde v2.1. Verifica que no esté abierta la versión anterior.
- **No hay precio**: el Excel clásico puede contener fórmulas sin resultado guardado. Ábrelo en Excel, recalcula y guarda o utiliza «Precios finales».
- **SKU ambiguo**: hay SKU duplicado o el formato de guiones/barras colisiona. Corrige la fuente.
- **No encuentra hoja**: revisa que la plantilla coincida con la versión configurada y no se haya renombrado una hoja.
- **Faltan filas preformateadas**: utiliza una plantilla con suficientes filas existentes; el sistema no crea filas nuevas.
- **No hay imagen principal**: corrige URLs y estados en el archivo de fotos, o la composición del pack.
- **Página no abre**: confirma que Python esté instalado y el puerto 5000 no esté ocupado; utiliza `--port 5001`.
- **Acceso desde otro equipo**: no está permitido por diseño; la aplicación es solo local por seguridad.

## Qué guardar

Para reproducir una exportación, conserva los originales empresariales en su almacenamiento privado aprobado y guarda el reporte de auditoría JSON también fuera de GitHub. El hash SHA-256 permite comprobar que estás usando exactamente el mismo archivo de entrada.
