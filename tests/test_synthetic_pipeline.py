"""Regresiones extremo-a-extremo sin material comercial, ejecutadas en GitHub CI."""
from __future__ import annotations
import unittest
import hashlib
from io import BytesIO
from zipfile import ZipFile
from processor import process
from ooxml import read_rows, worksheet_path
from tests.fixtures_factory import fake_falabella, fake_responsables

class SyntheticPipeline(unittest.TestCase):
    def test_updates_only_price_preserving_all_other_zip_parts(self):
        template=fake_falabella()
        responsables=fake_responsables()
        output,report=process(template,responsables,options={'manual_prices':'SYN-34;29990'})
        self.assertTrue(report['can_publish'],report['items'][0]['issues'])
        self.assertEqual(report['source_sha256']['falabella'],hashlib.sha256(template).hexdigest())
        self.assertEqual(report['source_sha256']['responsables'],hashlib.sha256(responsables).hexdigest())
        self.assertEqual(report['stats']['changed_cells'],1)
        self.assertEqual(report['integrity']['modified_cells'],1)
        values=dict(read_rows(output,'Subir plantilla',cols={'N'},min_row=5,max_row=5))
        self.assertEqual(values[5]['N'],29990)
        with ZipFile(BytesIO(template)) as a,ZipFile(BytesIO(output)) as b:
            target=worksheet_path(a,'Subir plantilla')
            for part in a.namelist():
                if part!=target:self.assertEqual(a.read(part),b.read(part))
            self.assertIn(b'r="N5" s="2"',b.read(target))

    def test_duplicate_sku_cannot_be_marked_publishable(self):
        _,report=process(fake_falabella(),fake_responsables(duplicate=True))
        self.assertFalse(report['can_publish'])
        self.assertEqual(report['stats']['blocked'],1)
        self.assertIn('sku_duplicate',[x['code'] for x in report['items'][0]['issues']])

if __name__=='__main__':unittest.main()
