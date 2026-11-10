"""Motor XLSX conservador: lee OOXML y modifica solamente nodos <c> en hoja destino.
No re-exporta ni re-crea libros; conserva XML de estilos, validaciones, dibujos y demás hojas.
"""
from __future__ import annotations

from decimal import Decimal, InvalidOperation
from io import BytesIO
import posixpath
import re
import xml.etree.ElementTree as ET
from xml.sax.saxutils import escape
import zipfile

MAIN = 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'
REL_DOC = 'http://schemas.openxmlformats.org/officeDocument/2006/relationships'
NS = {'m': MAIN}
# IMPORTANT: the lazy attribute matcher closes a self-closing <c .../> at its own />.
# A greedy [^>]* can consume that slash and then swallow the next <c>...</c>,
# hiding cells (e.g. L5 after an empty K5) or causing duplicated coordinates.
CELL_RE = re.compile(rb'<c\b[^>]*?\br="([A-Z]+)([0-9]+)"[^>]*?(?:/>|>.*?</c>)', re.DOTALL)
ROW_RE = re.compile(rb'<row\b[^>]*\br="(\d+)"[^>]*>.*?</row>', re.DOTALL)

class ExcelError(ValueError):
    pass


def safe_xlsx(content: bytes):
    if not content or not zipfile.is_zipfile(BytesIO(content)):
        raise ExcelError('Uno de los archivos no es un libro Excel .xlsx válido.')
    with zipfile.ZipFile(BytesIO(content)) as z:
        entries = z.infolist()
        if len(entries) > 10_000:
            raise ExcelError('Libro Excel con demasiadas partes internas.')
        names = [part.filename for part in entries]
        if len(names) != len(set(names)):
            raise ExcelError('Libro Excel con partes internas duplicadas.')
        for part in entries:
            name = part.filename
            if (not name or name.startswith('/') or '\\' in name or
                    posixpath.normpath(name) + ('/' if name.endswith('/') else '') != name or
                    name == '..' or name.startswith('../')):
                raise ExcelError('Libro Excel contiene una ruta interna no válida.')
            if part.flag_bits & 1:
                raise ExcelError('Libro Excel cifrado no compatible.')
            if part.file_size > 100_000_000:
                raise ExcelError('Libro Excel contiene una parte demasiado grande.')
            if part.file_size > 1_000_000 and part.file_size > max(1, part.compress_size) * 1000:
                raise ExcelError('Libro Excel con relación de compresion sospechosa.')
        if sum(i.file_size for i in entries) > 350_000_000:
            raise ExcelError('Libro Excel demasiado grande para este prototipo local.')
        if any(name.lower().endswith('/vbaproject.bin') for name in names):
            raise ExcelError('Libro con macros VBA no compatible con plantillas .xlsx.')
        if 'xl/workbook.xml' not in names:
            raise ExcelError('No se encontró la estructura esperada de un .xlsx.')


def worksheet_path(z: zipfile.ZipFile, sheet_name: str) -> str:
    root = ET.fromstring(z.read('xl/workbook.xml'))
    rel = ET.fromstring(z.read('xl/_rels/workbook.xml.rels'))
    relmap = {item.attrib['Id']: item.attrib['Target'] for item in rel}
    for sheet in root.findall('.//m:sheets/m:sheet', NS):
        if sheet.attrib['name'].strip().casefold() == sheet_name.strip().casefold():
            target = relmap.get(sheet.attrib.get(f'{{{REL_DOC}}}id'))
            if not target:
                break
            path = target.lstrip('/') if target.startswith('/') else posixpath.normpath('xl/' + target)
            if path not in z.namelist():
                break
            return path
    raise ExcelError(f'No se encontró la hoja "{sheet_name}" en uno de los libros.')


def shared_strings(z: zipfile.ZipFile) -> list[str]:
    if 'xl/sharedStrings.xml' not in z.namelist():
        return []
    result = []
    with z.open('xl/sharedStrings.xml') as fh:
        for _ev, el in ET.iterparse(fh, events=('end',)):
            if el.tag == f'{{{MAIN}}}si':
                result.append(''.join(t.text or '' for t in el.findall('.//m:t', NS)))
                el.clear()
    return result


def read_rows(content: bytes, sheet_name: str, cols: set[str] | None = None, min_row: int = 1, max_row: int | None = None):
    """Devuelve filas con valores; no calcula fórmulas que carecen de caché."""
    safe_xlsx(content)
    with zipfile.ZipFile(BytesIO(content)) as z:
        path = worksheet_path(z, sheet_name)
        shared = shared_strings(z)
        with z.open(path) as fh:
            for _ev, row in ET.iterparse(fh, events=('end',)):
                if row.tag != f'{{{MAIN}}}row':
                    continue
                rownum = int(row.attrib.get('r', '0'))
                if rownum < min_row:
                    row.clear()
                    continue
                if max_row is not None and rownum > max_row:
                    row.clear()
                    break
                data = {}
                for cell in row.findall('m:c', NS):
                    addr = cell.attrib.get('r', '')
                    col_match = re.match(r'[A-Z]+', addr)
                    if not col_match:
                        continue
                    col = col_match.group(0)
                    if cols is not None and col not in cols:
                        continue
                    v = cell.find('m:v', NS)
                    inline = cell.find('m:is', NS)
                    formula = cell.find('m:f', NS)
                    value = v.text if v is not None else None
                    if cell.attrib.get('t') == 's' and value is not None:
                        try:
                            value = shared[int(value)]
                        except (ValueError, IndexError):
                            value = None
                    elif inline is not None:
                        value = ''.join(t.text or '' for t in inline.findall('.//m:t', NS))
                    elif cell.attrib.get('t') not in ('e', 'str') and value is not None:
                        try:
                            number = float(value)
                            value = int(number) if number.is_integer() else number
                        except (TypeError, ValueError, OverflowError):
                            pass
                    if formula is not None and value is None:
                        data[col + '_SIN_CACHE'] = True
                    if value is not None:
                        data[col] = value
                if data:
                    yield rownum, data
                row.clear()


def clean(v) -> str:
    return str(v).strip() if v is not None else ''


def normalized_sku(v) -> str:
    text = clean(v).upper().replace('–', '-').replace('—', '-')
    text = re.sub(r'\s*/\s*', '-', text)
    return re.sub(r'\s*-\s*', '-', text)


def number(v):
    if v is None or isinstance(v, bool):
        return None
    s = clean(v).replace('\u00a0', '').replace(' ', '')
    if not s:
        return None
    if ',' in s and '.' in s:
        s = s.replace('.', '').replace(',', '.') if s.rfind(',') > s.rfind('.') else s.replace(',', '')
    elif ',' in s:
        s = s.replace(',', '.')
    try:
        x = Decimal(s)
        if not x.is_finite():
            return None
        return int(x) if x == x.to_integral_value() else float(x)
    except InvalidOperation:
        return None


def validate_ean13(v):
    s = clean(v)
    if len(s) != 13 or not s.isdigit():
        return False
    total = sum(int(ch) * (1 if i % 2 == 0 else 3) for i, ch in enumerate(s[:12]))
    return (10 - total % 10) % 10 == int(s[-1])



def replace_cell_bytes(original_row: bytes, col: str, rnum: int, value) -> bytes:
    coord = f'{col}{rnum}'.encode('ascii')
    # Conserva absolutamente los atributos de estilo s=, la celda y fila originales.
    for m in CELL_RE.finditer(original_row):
        if m.group(1) + m.group(2) != coord:
            continue
        original = m.group(0)
        start_tag = re.match(rb'<c\b[^>]*?/?>', original).group(0)
        attrs = start_tag[len(b'<c'):].rstrip(b'/>')
        attrs = re.sub(rb'\s+t="[^"]*"', b'', attrs)
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            replacement = b'<c' + attrs + b'><v>' + str(value).encode('ascii') + b'</v></c>'
        else:
            txt = escape(clean(value)).encode('utf-8')
            replacement = b'<c' + attrs + b' t="inlineStr"><is><t xml:space="preserve">' + txt + b'</t></is></c>'
        return original_row[:m.start()] + replacement + original_row[m.end():]
    # Celda no existente: insertarla respetando el orden de columnas y sin alterar el resto.
    col_index = column_to_number(col)
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        new = b'<c r="' + coord + b'"><v>' + str(value).encode('ascii') + b'</v></c>'
    else:
        new = b'<c r="' + coord + b'" t="inlineStr"><is><t xml:space="preserve">' + escape(clean(value)).encode('utf-8') + b'</t></is></c>'
    for m in CELL_RE.finditer(original_row):
        if column_to_number(m.group(1).decode('ascii')) > col_index:
            return original_row[:m.start()] + new + original_row[m.start():]
    pos = original_row.rfind(b'</row>')
    if pos < 0:
        raise ExcelError('No se pudo identificar el cierre de la fila del archivo.')
    return original_row[:pos] + new + original_row[pos:]


def column_to_number(col):
    n = 0
    for c in col:
        n = n * 26 + ord(c) - 64
    return n


def patch_xml(sheet_xml: bytes, changes: dict[int, dict[str, object]]) -> bytes:
    done = set()
    def do_row(m):
        rownum = int(m.group(1))
        if rownum not in changes:
            return m.group(0)
        row = m.group(0)
        for col, v in sorted(changes[rownum].items(), key=lambda x: column_to_number(x[0])):
            row = replace_cell_bytes(row, col, rownum, v)
        done.add(rownum)
        return row
    out = ROW_RE.sub(do_row, sheet_xml)
    missing = sorted(changes.keys() - done)
    if missing:
        raise ExcelError('La plantilla no tiene las filas de destino preparadas: ' + ', '.join(map(str, missing[:7])))
    return out


def write_unchanged_template(template: bytes, changes: dict[int, dict[str, object]], sheet_name: str = "Subir plantilla"):
    """Copia todas las partes del XLSX intactas salvo los valores de celdas en sheet destino."""
    with zipfile.ZipFile(BytesIO(template), 'r') as zin:
        target = worksheet_path(zin, sheet_name)
        output = BytesIO()
        with zipfile.ZipFile(output, 'w') as zout:
            for entry in zin.infolist():
                payload = zin.read(entry.filename)
                if entry.filename == target and changes:
                    payload = patch_xml(payload, changes)
                zout.writestr(entry, payload)
    result = output.getvalue()
    with zipfile.ZipFile(BytesIO(result)) as z:
        bad = z.testzip()
        if bad:
            raise ExcelError(f'Error de integridad al producir el archivo: {bad}')
    return result


