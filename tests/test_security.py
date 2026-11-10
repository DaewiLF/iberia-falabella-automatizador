"""Pruebas con archivos OOXML sintéticos (ningún dato comercial)."""
from __future__ import annotations
import csv
import io
from io import BytesIO
from zipfile import ZipFile, ZIP_DEFLATED
import unittest
import warnings
from ooxml import safe_xlsx, ExcelError
from processor import prepare_source, default_config, report_csv


def fake_xlsx(headers=None, extra_entries=()):
    """Libro mínimo con encabezados en Hoja 1."""
    headers = headers or {}
    cells = ''.join(f'<c r="{col}1" t="inlineStr"><is><t>{name}</t></is></c>' for col,name in headers.items())
    with BytesIO() as output:
        with ZipFile(output, 'w', ZIP_DEFLATED) as z:
            z.writestr('xl/workbook.xml', '''<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets><sheet name="Hoja 1" sheetId="1" r:id="rId1"/></sheets></workbook>''')
            z.writestr('xl/_rels/workbook.xml.rels', '''<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Target="worksheets/sheet1.xml" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet"/></Relationships>''')
            z.writestr('xl/worksheets/sheet1.xml', '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><sheetData><row r="1">'+cells+'</row></sheetData></worksheet>')
            for name,data in extra_entries:
                with warnings.catch_warnings():
                    warnings.simplefilter('ignore', UserWarning)
                    z.writestr(name,data)
        return output.getvalue()


class ZipSecurity(unittest.TestCase):
    def test_rejects_duplicate_part_names(self):
        with self.assertRaisesRegex(ExcelError, 'duplicad'):
            safe_xlsx(fake_xlsx(extra_entries=[('xl/workbook.xml','bad')]))

    def test_rejects_traversal_paths(self):
        with self.assertRaisesRegex(ExcelError, 'ruta'):
            safe_xlsx(fake_xlsx(extra_entries=[('../unsafe.txt','x')]))

    def test_accepts_harmless_zip_directory_entries(self):
        safe_xlsx(fake_xlsx(extra_entries=[('xl/','')]))

    def test_rejects_disguised_vba_macros(self):
        with self.assertRaisesRegex(ExcelError,'macro'):
            safe_xlsx(fake_xlsx(extra_entries=[('xl/vbaProject.bin',b'not-a-real-macro')]))

    def test_rejects_high_expansion_ratio(self):
        with self.assertRaisesRegex(ExcelError, 'compresion'):
            safe_xlsx(fake_xlsx(extra_entries=[('xl/huge.txt','X'*2_000_000)]))

    def test_ambiguous_fallback_headers_rejected(self):
        headers={'A':'SKU PADRE','B':'OTRO','D':'Alto','E':'Ancho','F':'Profundidad',
                 'G':'Peso','H':'Talla','I':'Responsables','M':'SKU HIJO/VENDEDOR','N':'SKU HIJO/VENDEDOR'}
        with self.assertRaisesRegex(ExcelError,'ambigu'):
            prepare_source(fake_xlsx(headers),'responsables',default_config())


class CsvSecurity(unittest.TestCase):
    def test_export_escapes_spreadsheet_formulas(self):
        report={'items':[{'row':5,'sku':'=HYPERLINK("https://example.org")','parent':'  +2+2',
                         'size':'34','owner':'@SUM(1,2)','status':'blocked','price':'100',
                         'price_source':'previo','images':0,'changed':0,'issues':[{'level':'error','message':'-SUM(1,2)'}]}]}
        values=list(csv.reader(io.StringIO(report_csv(report).decode('utf-8-sig')), delimiter=';'))[1]
        self.assertEqual(values[1][:1], "'")
        self.assertEqual(values[2][:1], "'")
        self.assertEqual(values[4][:1], "'")
        self.assertTrue(values[-1].startswith("error: -SUM"))

if __name__=='__main__': unittest.main()
