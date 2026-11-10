"""Crea libros OOXML mínimos con datos inventados para el pipeline en CI."""
from __future__ import annotations
from io import BytesIO
from xml.sax.saxutils import escape
from zipfile import ZipFile, ZIP_DEFLATED

W_NS = 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'
REL_NS = 'http://schemas.openxmlformats.org/officeDocument/2006/relationships'

def cell(coord, value, style=None):
    attrs = f'r="{coord}"' + (f' s="{style}"' if style else '')
    if isinstance(value, (int, float)):
        return f'<c {attrs}><v>{value}</v></c>'
    return f'<c {attrs} t="inlineStr"><is><t>{escape(str(value))}</t></is></c>'

def row(index, values, styled=()):
    return f'<row r="{index}">' + ''.join(cell(f'{col}{index}', v, 2 if col in styled else None) for col,v in values.items()) + '</row>'

def workbook(sheet_name, rows):
    book=f'<workbook xmlns="{W_NS}" xmlns:r="{REL_NS}"><sheets><sheet name="{escape(sheet_name)}" sheetId="1" r:id="rId1"/></sheets></workbook>'
    rel='<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Target="worksheets/sheet1.xml" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet"/></Relationships>'
    sheet=f'<worksheet xmlns="{W_NS}"><sheetData>'+''.join(rows)+'</sheetData></worksheet>'
    with BytesIO() as buf:
        with ZipFile(buf, 'w', ZIP_DEFLATED) as z:
            z.writestr('xl/workbook.xml',book)
            z.writestr('xl/_rels/workbook.xml.rels',rel)
            z.writestr('xl/worksheets/sheet1.xml',sheet)
        return buf.getvalue()

def fake_responsables(duplicate=False):
    headers={'A':'SKU PADRE','B':'SKU HIJO/VENDEDOR','C':'Descripción','D':'Alto','E':'Ancho','F':'Profundidad','G':'Peso','H':'Talla','I':'Responsables','J':'Estado'}
    product={'A':'SYN-PACK','B':'SYN-34','C':'Alpargata sintética','D':20,'E':10,'F':30,'G':1,'H':34,'I':'demo','J':'listo'}
    rows=[row(1,headers), row(2,product)]
    if duplicate:rows.append(row(3,{**product,'C':'texto contradictorio'}))
    return workbook('Hoja 1',rows)

def fake_falabella():
    headers={'J':'SKU del vendedor','L':'SKU Padre','I':'Size','N':'PriceFalabella','AK':'Ancho','AL':'Largo','AM':'Alto','AN':'Peso'}
    product={'A':'Nombre sintético','B':'IBERIA','D':'Descripción sintética','E':'Calzado',
             'I':34,'J':'SYN-34','K':'4006381333931','L':'SYN-PACK','N':19990,
             'AK':10,'AL':20,'AM':30,'AN':1,'AQ':'https://example.invalid/imagen.jpg'}
    return workbook('Subir plantilla',[row(4,headers),row(5,product,styled={'J','L','N'})])
