"""Pruebas de regresión: casos offline y, opcionalmente, datos reales no versionados.

Para ejecutar pruebas con Excel empresariales, define estas variables de entorno:
IBERIA_TEST_TEMPLATE, IBERIA_TEST_RESP, IBERIA_TEST_FOTOS, IBERIA_TEST_PRECIOS.
Los archivos permanecen fuera del repositorio y se cargan solo en memoria.
"""
from __future__ import annotations
from io import BytesIO
import json
import os
from pathlib import Path
import re
import unittest
from zipfile import ZipFile
from processor import (process, parse_config, parse_pack_overrides, parse_price_overrides,
                       infer_components, default_config)
from ooxml import (read_rows, write_unchanged_template, worksheet_path, validate_ean13,
                   ExcelError, CELL_RE, replace_cell_bytes, ROW_RE, normalized_sku, number)

REAL_FILES = [os.environ.get(key) for key in (
    'IBERIA_TEST_TEMPLATE','IBERIA_TEST_RESP','IBERIA_TEST_FOTOS','IBERIA_TEST_PRECIOS')]
REAL_READY = all(REAL_FILES) and all(Path(x).is_file() for x in REAL_FILES if x)


@unittest.skipUnless(REAL_READY, 'Integración real opcional: configura IBERIA_TEST_* fuera del repositorio')
class RealWorkbookTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.t, cls.r, cls.f, cls.p = (Path(path).read_bytes() for path in REAL_FILES)
        cls.original_rows = [(n,d) for n,d in read_rows(cls.t, 'Subir plantilla',
                             {'J','K','L','N'},min_row=5,max_row=2000) if d.get('J')]
        if not cls.original_rows:
            raise AssertionError('La plantilla de integración no tiene SKU base para prueba.')
        cls.row_numbers = [n for n,_ in cls.original_rows]
        cls.parent = cls.original_rows[0][1]['L']
        cls.child = cls.original_rows[0][1]['J']
        cls.base_price = 28990
        if all(d.get('N')==cls.base_price for _,d in cls.original_rows):
            cls.base_price = 29990

    def test_normal_preview_preserves_every_external_part(self):
        output,report=process(self.t,self.r,photos=self.f,prices=self.p)
        self.assertEqual(report['stats']['matched'],len(self.row_numbers))
        self.assertTrue(report['integrity']['parts_unchanged'])
        self.assertEqual(report['changes'],0)

    def test_price_edit_preserves_all_other_parts_and_styles(self):
        output,report=process(self.t,self.r,photos=self.f,
                              options={'manual_prices':str(self.parent)+';'+str(self.base_price)})
        self.assertEqual(report['changes'],len(self.row_numbers))
        self.assertTrue(report['integrity']['cell_styles_unchanged'])
        with ZipFile(BytesIO(self.t)) as za,ZipFile(BytesIO(output)) as zb:
            sheet=worksheet_path(za,'Subir plantilla')
            self.assertEqual(za.namelist(),zb.namelist())
            for name in za.namelist():
                if name!=sheet:self.assertEqual(za.read(name),zb.read(name),name)
        rows=dict(read_rows(output,'Subir plantilla',{'N'},min_row=min(self.row_numbers),
                            max_row=max(self.row_numbers)))
        self.assertEqual([rows[n]['N'] for n in self.row_numbers],[self.base_price]*len(self.row_numbers))

    def test_blank_mode_uses_prepared_rows(self):
        empty=write_unchanged_template(self.t,{n:{'J':''} for n in self.row_numbers})
        _,report=process(empty,self.r,options={'parents':str(self.parent),'blank':True})
        self.assertTrue(report['blank_mode'])
        self.assertEqual(report['stats']['matched'],len(self.row_numbers))
        self.assertTrue(report['integrity']['parts_unchanged'])

    def test_source_duplicate_sku_blocks_export(self):
        duplicate=write_unchanged_template(self.r,{10:{'B':self.child}},'Hoja 1')
        _,report=process(self.t,duplicate,photos=self.f)
        self.assertFalse(report['can_publish'])
        self.assertGreater(report['stats']['blocked'],0)
        self.assertTrue(any(i['code']=='sku_duplicate' for it in report['items'] for i in it['issues']))

    def test_missing_price_and_gtin_block_publish(self):
        incomplete=write_unchanged_template(self.t,{n:{'N':'','K':''} for n in self.row_numbers})
        output,report=process(incomplete,self.r,photos=self.f,prices=self.p)
        self.assertFalse(report['can_publish'])
        self.assertEqual(report['stats']['blocked'],len(self.row_numbers))
        self.assertTrue(any(i['code']=='price_missing' for it in report['items'] for i in it['issues']))
        self.assertTrue(output)

    def test_adjacent_empty_cell_is_not_swallowed(self):
        buffer=BytesIO();first=self.row_numbers[0]
        coord=f'K{first}'.encode('ascii')
        with ZipFile(BytesIO(self.t)) as original, ZipFile(buffer,'w') as modified:
            target=worksheet_path(original,'Subir plantilla')
            for part in original.infolist():
                payload=original.read(part.filename)
                if part.filename==target:
                    target_row=next(m.group(0) for m in ROW_RE.finditer(payload)
                                    if int(m.group(1))==first)
                    kcell=next(m.group(0) for m in CELL_RE.finditer(target_row)
                               if m.group(1)+m.group(2)==coord)
                    style=re.search(rb'\bs="[^"]+"',kcell)
                    missing=b'<c r="'+coord+b'"'+(b' '+style.group(0) if style else b'')+b'/>'
                    payload=payload.replace(kcell,missing,1)
                modified.writestr(part,payload)
        modified_template=buffer.getvalue()
        output,report=process(modified_template,self.r,options={'parent_mode':'smallest_child'})
        self.assertTrue(report['integrity']['parts_unchanged'])
        self.assertFalse(report['can_publish'])
        with ZipFile(BytesIO(output)) as z:
            xml=z.read(worksheet_path(z,'Subir plantilla'))
            row=next(m.group(0) for m in ROW_RE.finditer(xml) if int(m.group(1))==first)
            self.assertIn(missing,row)
            self.assertEqual(sum(1 for m in CELL_RE.finditer(row) if m.group(1)==b'L'),1)

    def test_alternate_dimensions_match_source_values(self):
        output,report=process(self.t,self.r,options={'dimension_mode':'swapped'})
        destrow=self.row_numbers[0]
        target=dict(read_rows(output,'Subir plantilla',{'AL','AM'},min_row=destrow,max_row=destrow))[destrow]
        source=next(row for _,row in read_rows(self.r,'Hoja 1',{'B','D','F'},min_row=2)
                    if normalized_sku(row.get('B'))==normalized_sku(self.child))
        self.assertEqual(target['AL'],number(source['F']))
        self.assertEqual(target['AM'],number(source['D']))
        self.assertGreaterEqual(report['changes'],0)


class XmlCellRegression(unittest.TestCase):
    def test_self_closing_cell_does_not_hide_next_cell(self):
        row=(b'<row r="5"><c r="J5"><v>1</v></c><c r="K5" s="4"/>'
             b'<c r="L5" s="42" t="s"><v>3</v></c><c r="M5" s="4"/></row>')
        matches=list(CELL_RE.finditer(row))
        self.assertEqual([m.group(1).decode() for m in matches],['J','K','L','M'])
        self.assertEqual(matches[1].group(0),b'<c r="K5" s="4"/>')
        patched=replace_cell_bytes(row,'L',5,'PACK NUEVO')
        self.assertEqual(patched.count(b'r="L5"'),1)
        self.assertIn(b'<c r="K5" s="4"/>',patched)
        self.assertIn(b'PACK NUEVO',patched)

    def test_missing_cell_inserted_once_next_to_self_closing(self):
        row=b'<row r="5"><c r="K5" s="4"/><c r="M5" s="4"/></row>'
        patched=replace_cell_bytes(row,'L',5,'PACK')
        self.assertEqual([m.group(1).decode() for m in CELL_RE.finditer(patched)],['K','L','M'])
        self.assertEqual(patched.count(b'r="L5"'),1)

class Helpers(unittest.TestCase):
    def test_inferred_components_unambiguous(self):
        result,amb=infer_components('AAA-BBB-CCC-DDD',{'AAA-BBB','CCC-DDD'})
        self.assertEqual(result,['AAA-BBB','CCC-DDD']);self.assertFalse(amb)
    def test_ambiguous_components_not_assigned(self):
        result,amb=infer_components('A-B-C',{'A-B','C','A','B-C'})
        self.assertEqual(result,[]);self.assertTrue(amb)
    def test_invalid_overrides_rejected(self):
        with self.assertRaises(ExcelError):parse_price_overrides('A;100\nA;200')
        with self.assertRaises(ExcelError):parse_pack_overrides('PACK=SKU1, SKU1')
    def test_config_columns_and_ranges_checked(self):
        config=default_config();config['destination']['columns']['price']='J'
        with self.assertRaises(ExcelError):parse_config(json.dumps(config))
    def test_barcode_validation_is_not_registration(self):
        self.assertTrue(validate_ean13('4006381333931'))
        self.assertFalse(validate_ean13('4006381333932'))

if __name__=='__main__':unittest.main(verbosity=2)
