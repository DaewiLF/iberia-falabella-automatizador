"""Pruebas de rutas públicas con servidor HTTP local efímero."""
from __future__ import annotations
from contextlib import contextmanager
import http.client
import json
from threading import Thread
import unittest
from http.server import ThreadingHTTPServer
from app import Server, store


@contextmanager
def server():
    srv=ThreadingHTTPServer(('127.0.0.1',0),Server)
    t=Thread(target=srv.serve_forever,daemon=True)
    t.start()
    try: yield srv.server_port
    finally:
        srv.shutdown()
        srv.server_close()
        t.join(timeout=3)


class AuditApi(unittest.TestCase):
    def test_json_report_matches_preview_without_reopening_workbook(self):
        report={'version':'2.2','items':[{'sku':'PRUEBA-34','status':'warning','diff':[]}],
                'stats':{'total':1},'can_publish':False}
        token=store(b'xlsx de ejemplo',report)
        with server() as port:
            client=http.client.HTTPConnection('127.0.0.1',port,timeout=10)
            client.request('GET','/api/report-json/'+token+'.json')
            resp=client.getresponse();data=resp.read();client.close()
        self.assertEqual(resp.status,200)
        self.assertIn('application/json',resp.getheader('Content-Type'))
        self.assertIn('attachment;',resp.getheader('Content-Disposition'))
        self.assertEqual(json.loads(data),report)

    def test_browser_cross_site_post_is_rejected_even_without_origin(self):
        with server() as port:
            client=http.client.HTTPConnection('127.0.0.1',port,timeout=10)
            payload=json.dumps({'token':'no-existe','ack':True}).encode('utf-8')
            client.request('POST','/api/approve',body=payload,headers={
                'Content-Type':'application/json', 'Sec-Fetch-Site':'cross-site'})
            resp=client.getresponse();data=resp.read();client.close()
        self.assertEqual(resp.status,400)
        self.assertIn('no autorizada',json.loads(data)['error'])

    def test_expired_or_unknown_json_report_returns_404(self):
        with server() as port:
            client=http.client.HTTPConnection('127.0.0.1',port,timeout=10)
            client.request('GET','/api/report-json/no-existe.json')
            resp=client.getresponse();data=resp.read();client.close()
        self.assertEqual(resp.status,404)
        self.assertIn('error',json.loads(data))

if __name__=='__main__': unittest.main()
