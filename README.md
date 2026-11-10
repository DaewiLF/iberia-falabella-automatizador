# Iberia — Automatizador Falabella 2.2

Aplicación web **local y sin dependencias Python externas** para combinar Excel de Responsables, URLs de fotos y precios sobre una **copia de la plantilla original de Falabella**. Incluye vista previa detallada, detección de problemas, reportes CSV/JSON e historial local. No está conectada al Seller Center.

## Cómo empezar en Windows

1. Descarga el ZIP, descomprímelo y mantén sus carpetas (`templates` y `static`).
2. Si todavía no tienes Python, instala **Python 3.11 o superior** desde <https://www.python.org/downloads/> y marca **Add python.exe to PATH**.
3. Haz doble clic en **`iniciar_windows.bat`**. Se abrirá tu navegador en `http://127.0.0.1:5000`.
4. Adjunta la plantilla Falabella y el Excel de Responsables. Si los tienes, añade URLs de Fotos, Precios de Falabella y/o un Excel de precios finales calculados.
5. Selecciona los SKU padres (opcional para plantillas ya llenas), responsable, opciones de conversión y reglas de packs si necesitas personalizarlas.
6. Haz clic en **Analizar y previsualizar**. Revisa los cambios, errores y advertencias. Descarga el **reporte CSV** cuando lo necesites.
7. Marca la confirmación y descarga: un Excel de revisión si no hay bloqueos, o un archivo **BORRADOR_NO_PUBLICAR** si hay errores críticos. Haz siempre una prueba piloto en Seller Center.

Para detenerla, cierra la consola o presiona `Ctrl+C`. También puedes iniciar desde terminal: `python app.py --port 5001 --no-browser`.

**No requiere Internet para funcionar ni envía los archivos a ningún servidor.** No subas plantillas con fórmulas peligrosas o contenidos externos sin comprobar su origen; el sistema lee datos de XML y no ejecuta macros.

## Formato del Excel de precios finales

La quinta carga, **Precios finales calculados**, puede contener una hoja sencilla con encabezados en la primera fila:

| SKU | Precio Final |
|---|---:|
| ARTICULO-A-34 | 8990 |
| PACK-A-B-C | 27790 |

El motor busca por SKU vendedor y, para packs, también por SKU padre. Si cargas el Excel clásico de precios Iberia, lee **SKU ML** y **Precio Final Redondeo**. No evalúa fórmulas de Excel dentro del navegador.

**Precedencia de precios:** precio manual por SKU, manual por SKU padre, Excel de precios finales por SKU, Excel de precios finales por SKU padre, Excel de precios clásico por SKU, precio uniforme y, por último, precio existente en la plantilla.

Si la fórmula de precios de `AB` carece de resultado guardado, usa Microsoft Excel (Ctrl+Alt+F9, guardar) o el ayudante opcional **`recalcular_precios_windows.bat`**: arrastra el archivo original de precios sobre el BAT. Este ayudante **requiere Microsoft Excel para Windows**, genera una **copia** `_RECALCULADO.xlsx` y mantiene el original intacto. El ayudante es opcional y la integración COM todavía requiere verificación en un PC con Excel real.

## Relación SKU y fotos de packs

Se identifica la variante mediante SKU vendedor (`Responsables!B` a `Falabella!J`). Para el SKU padre se usa `Responsables!A` o, si eliges esa opción, el SKU vendedor de la variante de menor talla (debes confirmar cuál exige tu categoría en Seller Center).

Las fotos se recuperan de dos formas, sin adivinar:

- **Exacta:** si el SKU padre tiene imágenes registradas y aprobadas en Fotos, se usan esas imágenes.
- **Componentes:** si no existe foto del pack completo, se intenta dividir el SKU padre en una única combinación de SKU existentes en Fotos; si hay más de una interpretación, no se asigna nada automáticamente. También puedes indicar una composición explícita, una por línea:

```text
PACK-A-B-C = ARTICULO-A, ARTICULO-B, ARTICULO-C
```

Solo se toman URLs `http(s)` bien formadas con estados `Listo`, `Aprobado`, `Aprobada`, `Subida` o `Publicado`. Una imagen principal de cada componente precede a las secundarias. Máximo ocho imágenes; se eliminan duplicadas. **No se comprueba por Internet que las URLs respondan con HTTP 200**, solamente su sintaxis.

## Dimensiones

Se conserva el mapeo acordado anteriormente como modo predeterminado:

| Columna Falabella | Responsables (modo actual) |
|---|---|
| I · Talla | H · Talla |
| J · SKU vendedor | B · SKU HIJO/VENDEDOR |
| L · SKU padre | A · SKU PADRE |
| AK · Ancho | E · Ancho |
| AL · Largo | D · Alto |
| AM · Alto | F · Profundidad |
| AN · Peso | G · Peso |

También existe la opción **Largo ← Profundidad / Alto ← Alto**. El mapeo correcto depende de cómo se haya medido el paquete físicamente: no lo asumas por el nombre de los encabezados.

## Validaciones antes de la descarga

- Coincidencias y colisiones de SKU (guiones y `/` usados solo para comparar; el texto comercial escrito se mantiene).
- Duplicados de SKU de vendedor en Responsables y en Falabella.
- Revisión de SKU padre, tallas y dimensiones positivas.
- Nombre, marca, descripción, categoría y precio final.
- EAN-13: longitud, dígitos y checksum. **Un checksum correcto NO prueba que el GTIN esté registrado con GS1.** Esta aplicación no genera identificadores aleatorios para cargas comerciales.
- Foto principal con formato URL y estado aprobado cuando proviene del Excel de Fotos.
- Encabezados exigidos para cada fuente y los campos de destino de Falabella.

Los conflictos de identidad bloquean la actualización de la fila. Otros campos faltantes marcan la fila como bloqueada **para publicación**, pero pueden aparecer parcialmente completados en un borrador. No se completa ningún dato faltante por imaginación.

Los mensajes generales incluyen la revisión del SKU padre, las dimensiones y las fórmulas no calculadas. Aunque la vista previa indique «sin errores bloqueantes», **no es una certificación de aceptación en Seller Center**; las reglas del catálogo pueden cambiar y algunos campos obligatorios son específicos de categoría.

## Integridad del libro original

Se edita directamente la parte OOXML de la hoja de destino; los restantes miembros del ZIP XLSX se copian sin cambiar su contenido. Después de escribir, el motor comprueba:

1. Igualdad del conjunto y orden de partes internas del XLSX.
2. **Igualdad binaria** del contenido de cada parte distinta de la hoja destino.
3. Igualdad de la estructura XML fuera de las celdas autorizadas, y conservación de atributos `s`, `cm`, `vm`, `ph` de las celdas modificadas.
4. Validez de la compresión ZIP resultante.
5. Rechazo de sobreescritura de fórmulas en celdas destino.

No altera el archivo que subiste. No crea filas ni reconstruye hojas; en plantillas vacías **solo usa filas ya preformateadas**. Plantillas con firma digital pueden invalidar la firma al cambiar sus datos; no se ha verificado la compatibilidad con todas las versiones de Seller Center.

## Archivo de configuración JSON

En **Reglas avanzadas** puedes descargar `mapeo_iberia_base.json` y editarlo para definir las hojas, filas de encabezado y columnas de los archivos de origen. Los encabezados se autodetectan cuando cambian de columna. Si cambia además el nombre de encabezado, puedes declarar un alias propio en la sección `headers` del origen:

```json
{
  "sources": {
    "precios_finales": {
      "sheet": "Mi lista",
      "header_row": 1,
      "columns": {"sku": "C", "price": "G"},
      "headers": {"sku": "Codigo producto", "price": "Valor Venta"}
    }
  }
}
```

También es posible configurar columnas y nombre de hoja de salida, pero se validan los identificadores de encabezado Falabella antes de aplicar cambios. La configuración no equivale a compatibilidad certificada con otros marketplaces.

## Historial, privacidad y preferencias

- El historial `data/history.jsonl` guarda solo fecha, hash parcial del Excel base y contadores de resultados. No conserva nombres de archivo, SKUs ni datos de productos.
- Los archivos de salida quedan **en memoria por máximo una hora**. Para descargar debes confirmar en la vista previa; un token expirado requiere volver a analizar.
- Puedes guardar preferencias de filtros y reglas en el navegador local, sin adjuntar archivos ni almacenarlos en el servidor.
- El servidor escucha únicamente en `127.0.0.1` y rechaza solicitudes de origen web ajeno.
- Si deseas borrar el historial, cierra la aplicación y elimina `data/history.jsonl`. Para borrar las preferencias, usa **Restablecer** en la interfaz.

## Crear un ejecutable de Windows sin requerir Python en el equipo de destino

En un **PC Windows con Python e Internet**, ejecuta `crear_exe_windows.bat`, que instala PyInstaller y compila `dist\IberiaFalabella\IberiaFalabella.exe` (formato `onedir`, **copia la carpeta completa**, no solo el EXE). El PC que reciba esa carpeta no debería requerir una instalación de Python. **El ZIP distribuido contiene el código y el script de compilación, no un EXE ya compilado**; este paso no ha sido probado en Windows desde este entorno Linux.

## Desarrolladores y pruebas

Arquitectura: navegador (`templates/index.html`, `static/app.js`, `static/style.css`) → servidor `app.py` → reglas y validación `processor.py` → motor OOXML `ooxml.py`. Solo Python estándar. No usa base de datos ni servicios remotos.

Pruebas automatizadas, desde la carpeta del proyecto:

```bash
python -m unittest discover -v
```

Las pruebas sintéticas funcionan sin datos comerciales. Las pruebas con Excel reales son opcionales y se habilitan **solo si** configuras rutas externas mediante `IBERIA_TEST_TEMPLATE`, `IBERIA_TEST_RESP`, `IBERIA_TEST_FOTOS` e `IBERIA_TEST_PRECIOS`. No subas esos archivos al repositorio. Para pruebas de publicación, utiliza una plantilla real vigente y valida el resultado con Seller Center en una carga piloto.

### Límites deliberados

- Solo Excel `.xlsx` sin macros; no admite `.xls`, `.xlsm` ni Google Sheets directamente.
- Los precios del pack no se derivan automáticamente de la suma de unidades ni de una fórmula no calculada.
- No se verifica por red la disponibilidad real de las imágenes.
- No existe conexión automática a Seller Center: no se envían ni publican productos desde la aplicación.
- Para una futura integración con Ripley o Mercado Libre hay que aportar una plantilla real de cada marketplace y verificar sus reglas.
- La funcionalidad para recalcular Excel en Windows mediante COM tiene un script opcional, no una integración directa en la página.

## Archivos complementarios incluidos

- `plantilla_precios_finales.xlsx`: archivo vacío con las columnas SKU y Precio Final; útil para incorporar valores finales aprobados.
- `mapeo_iberia_base.json`: configuración inicial exportable y editable.
- `VALIDACION_Y_CAMBIOS.md`: matriz de mejoras y pruebas.
- `recalcular_precios_windows.bat` y `.ps1`: ayudante opcional para Excel Windows.


## Corrección v2.1: “Integridad: falta L5”

En la versión 2.0 el lector de nodos XML podía fusionar una celda vacía
`<c .../>` con la celda siguiente, impidiendo verificar correctamente una
actualización en una columna adyacente. La versión 2.1 reconoce cada
celda por separado y agrega pruebas de regresión para celdas vacías junto
a los campos de SKU padre. Esta corrección no elimina la validación de
integridad ni cambia los estilos de Excel.

Para utilizarla, **cierra primero la ventana de la consola de v2.0** y
ejecuta `iniciar_windows.bat` dentro de la carpeta nueva v2.2. Si la
versión anterior está abierta, el puerto 5000 puede estar ocupado.

---

## Actualización 2.2 — Seguridad, auditoría y repositorio

Se incluyen controles para rechazar XLSX hostiles (entradas ZIP duplicadas, rutas anómalas, macros ocultas y expansión excesiva), detectar encabezados alternativos ambiguos y exportar CSV sin riesgo de interpretación como fórmulas. Puedes descargar **Auditoría JSON** desde la vista previa; contiene detalles completos de la exportación y los hashes SHA-256 de los archivos utilizados. Este JSON puede contener información comercial y **no debe subirse a GitHub**.

La suite de pruebas ahora funciona con archivos inventados y GitHub Actions, además de las pruebas opcionales con Excel reales. Para las instrucciones de GitHub y privacidad del repositorio, consulta:

- [`docs/GITHUB_PUBLICACION.md`](docs/GITHUB_PUBLICACION.md): creación, push y permisos.
- [`docs/ARQUITECTURA.md`](docs/ARQUITECTURA.md): flujo del motor y OOXML.
- [`docs/OPERACION.md`](docs/OPERACION.md): pasos de uso, precios, packs y errores.
- [`docs/REGLAS_FALABELLA.md`](docs/REGLAS_FALABELLA.md): campos y supuestos comerciales.
- [`docs/DESARROLLO.md`](docs/DESARROLLO.md): tests, mantenimiento y extensibilidad.
- [`docs/SEGURIDAD_Y_DATOS.md`](docs/SEGURIDAD_Y_DATOS.md): privacidad y limitaciones.
- [`CHANGELOG.md`](CHANGELOG.md): cambios por versión.
- [`docs/ROADMAP.md`](docs/ROADMAP.md): mejoras implementadas y pendientes externas.

**GitHub:** el repositorio de destino es `DaewiLF/iberia-falabella-automatizador`. Su visibilidad puede ser pública; se recomienda configurarlo como privado antes de incorporar documentos internos. No se ha ejecutado ninguna subida real a Seller Center.
