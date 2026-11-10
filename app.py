"""Servidor web offline: standard library, acceso únicamente desde el mismo PC.
No sube archivos a Internet ni integra cuentas Seller Center.
"""
from __future__ import annotations
from email import policy
from email.parser import BytesParser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Lock, Timer
from datetime import datetime
import csv
import io
import json
import logging
import os
import re
import secrets
import time
import webbrowser

from ooxml import ExcelError
from processor import process, default_config, report_csv

ROOT=Path(__file__).resolve().parent
LOG=ROOT/'data'/'history.jsonl'
MEMORY={}
LOCK=Lock()
MAX_BODY=85*1024*1024
MAX_FILE=40*1024*1024
TTL=3600


def history_add(report):
    """Solo conserva fecha, hash del Excel y contadores; nunca almacena los archivos cargados."""
    record={'timestamp':report['generated_at'],'template_sha256_prefix':report['template_sha256'][:12],
            'total':report['stats'].get('total',0),'ready':report['stats'].get('ready',0),
            'warnings':report['stats'].get('warnings',0),'blocked':report['stats'].get('blocked',0),
            'changed_cells':report['changes'],'publishable':report['can_publish']}
    try:
        LOG.parent.mkdir(parents=True,exist_ok=True)
        with LOCK:
            past=[]
            if LOG.exists():past=LOG.read_text('utf-8').splitlines()[-99:]
            LOG.write_text('\n'.join(past+[json.dumps(record,ensure_ascii=False)])+'\n','utf-8')
    except OSError:
        logging.warning('No se pudo guardar el historial local.')


def load_history():
    try:
        lines=LOG.read_text('utf-8').splitlines()[-50:]
        return [json.loads(x) for x in reversed(lines)]
    except (OSError,ValueError):return []


def store(blob,report):
    token=secrets.token_urlsafe(24)
    with LOCK:
        expired=[k for k,v in MEMORY.items() if time.monotonic()-v['at']>TTL]
        for k in expired:MEMORY.pop(k,None)
        if len(MEMORY)>12:
            for k in sorted(MEMORY,key=lambda t:MEMORY[t]['at'])[:-9]:MEMORY.pop(k,None)
        MEMORY[token]={'at':time.monotonic(),'file':blob,'report':report,'approved':None}
    return token


def get_token(token):
    with LOCK:
        value=MEMORY.get(token)
        if value and time.monotonic()-value['at']<TTL:return value
    return None


class Server(BaseHTTPRequestHandler):
    protocol_version='HTTP/1.1'

    def log_message(self,fmt,*args):
        logging.info('%s %s',self.address_string(),fmt % args)

    def send_bytes(self,payload,code=200,ctype='text/html; charset=utf-8',filename=None):
        self.send_response(code)
        self.send_header('Content-Type',ctype)
        self.send_header('Content-Length',str(len(payload)))
        self.send_header('Cache-Control','no-store, max-age=0')
        self.send_header('X-Content-Type-Options','nosniff')
        self.send_header('X-Frame-Options','DENY')
        self.send_header('Referrer-Policy','no-referrer')
        self.send_header('Content-Security-Policy',"default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'self'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'")
        if filename:
            self.send_header('Content-Disposition',f'attachment; filename="{filename}"')
        self.end_headers()
        try:self.wfile.write(payload)
        except (BrokenPipeError,ConnectionResetError):pass

    def send_json(self,obj,code=200):
        self.send_bytes(json.dumps(obj,ensure_ascii=False).encode('utf-8'),code,'application/json; charset=utf-8')

    def do_GET(self):
        path=self.path.split('?',1)[0]
        if path in ('/','/index.html'):
            return self.send_bytes((ROOT/'templates/index.html').read_bytes())
        if path in ('/static/style.css','/static/app.js'):
            typ='text/css; charset=utf-8' if path.endswith('.css') else 'application/javascript; charset=utf-8'
            return self.send_bytes((ROOT/path.lstrip('/')).read_bytes(),ctype=typ)
        if path=='/api/config':return self.send_json(default_config())
        if path=='/api/history':return self.send_json({'history':load_history()})
        if path=='/api/health':return self.send_json({'status':'ok','service':'Iberia Falabella local','version':'2.2'})
        if path.startswith('/api/report-json/') and path.endswith('.json'):
            token=path.rsplit('/',1)[-1].removesuffix('.json')
            item=get_token(token)
            if not item:return self.send_json({'error':'Reporte vencido o inexistente.'},404)
            payload=json.dumps(item['report'],ensure_ascii=False,indent=2).encode('utf-8')
            return self.send_bytes(payload,ctype='application/json; charset=utf-8',filename='Auditoria_Falabella.json')
        if path.startswith('/api/report/') and path.endswith('.csv'):
            token=path.rsplit('/',1)[-1].removesuffix('.csv')
            item=get_token(token)
            if not item:return self.send_json({'error':'Reporte vencido o inexistente.'},404)
            return self.send_bytes(report_csv(item['report']),ctype='text/csv; charset=utf-8',filename='Reporte_Falabella.csv')
        if path.startswith('/api/download/'):
            token=path.split('/')[-1]
            item=get_token(token)
            if not item:return self.send_json({'error':'Archivo vencido o inexistente.'},404)
            if item['approved'] is None:return self.send_json({'error':'Debes revisar y confirmar antes de descargar.'},403)
            if item['approved']=='publish' and not item['report']['can_publish']:
                return self.send_json({'error':'El archivo contiene errores bloqueantes.'},403)
            filename='Falabella_lista_revision.xlsx' if item['approved']=='publish' else 'Falabella_BORRADOR_NO_PUBLICAR.xlsx'
            return self.send_bytes(item['file'],ctype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',filename=filename)
        return self.send_json({'error':'Ruta no encontrada.'},404)

    def require_local_origin(self):
        # La verificación de Fetch Metadata también protege POST sin cabecera Origin.
        if self.headers.get('Sec-Fetch-Site','').lower() in ('cross-site','same-site'):
            raise ExcelError('Solicitud no autorizada desde otro sitio web.')
        origin=self.headers.get('Origin','')
        if origin and not re.fullmatch(r'http://(127\.0\.0\.1|localhost):\d+',origin):
            raise ExcelError('Solicitud no autorizada desde otra página web.')
        host=self.headers.get('Host','')
        if not re.fullmatch(r'(127\.0\.0\.1|localhost)(:\d+)?',host):
            raise ExcelError('Solo se permiten conexiones locales.')

    def read_body(self):
        try:length=int(self.headers.get('Content-Length','0'))
        except ValueError:length=0
        if not 0<length<=MAX_BODY:raise ExcelError('El contenido está vacío o supera 85 MB.')
        return self.rfile.read(length)

    def parse_multipart(self,data):
        ctype=self.headers.get('Content-Type','')
        if not ctype.startswith('multipart/form-data'):
            raise ExcelError('Se esperaba un formulario con archivos.')
        raw=(f'Content-Type: {ctype}\r\nMIME-Version: 1.0\r\n\r\n').encode('utf-8')+data
        msg=BytesParser(policy=policy.default).parsebytes(raw)
        if not msg.is_multipart():raise ExcelError('No se pudieron interpretar los archivos.')
        fields={};files={}
        for part in msg.iter_parts():
            key=part.get_param('name',header='content-disposition')
            if not key:continue
            payload=part.get_payload(decode=True) or b''
            if part.get_filename():
                if key not in ('falabella','responsables','fotos','precios','precios_finales','config_file'):
                    raise ExcelError('Campo de archivo no reconocido.')
                if len(payload)>MAX_FILE:raise ExcelError('Un archivo supera el límite de 40 MB.')
                extension=Path(part.get_filename()).suffix.lower()
                if extension != ('.json' if key=='config_file' else '.xlsx'):
                    raise ExcelError('Archivo incompatible: '+part.get_filename()[-100:])
                if key in files:raise ExcelError('No adjuntes el mismo tipo de archivo dos veces.')
                files[key]=payload
            else:
                if len(payload)>120_000:raise ExcelError('Una configuración de texto es demasiado grande.')
                fields[key]=payload.decode('utf-8','replace')
        return files,fields

    def do_POST(self):
        try:
            self.require_local_origin()
            data=self.read_body()
            if self.path=='/api/preview':
                files,fields=self.parse_multipart(data)
                if not files.get('falabella') or not files.get('responsables'):
                    raise ExcelError('Adjunta la plantilla Falabella y el Excel de Responsables.')
                opts={'parents':fields.get('parents',''),'owner':fields.get('owner',''),
                      'name':fields.get('name',''),'brand':fields.get('brand',''),'category':fields.get('category',''),
                      'uniform_price':fields.get('uniform_price',''),
                      'manual_prices':fields.get('manual_prices',''),'pack_mapping':fields.get('pack_mapping',''),
                      'parent_mode':fields.get('parent_mode','responsables'),'dimension_mode':fields.get('dimension_mode','legacy'),
                      'descriptions':fields.get('descriptions')=='on','photos':fields.get('photos')=='on',
                      'prices':fields.get('prices')=='on','blank':fields.get('blank')=='on',
                      'strict_rows':True}
                config=files.get('config_file') or fields.get('config_text') or None
                result,report=process(files['falabella'],files['responsables'],
                                      photos=files.get('fotos'),prices=files.get('precios'),
                                      final_prices=files.get('precios_finales'),options=opts,config=config)
                token=store(result,report)
                history_add(report)
                # Nunca devolver el archivo en la respuesta de previsualización.
                return self.send_json({'token':token,'report':report})
            if self.path=='/api/approve':
                try:req=json.loads(data.decode('utf-8'))
                except (ValueError,UnicodeError):raise ExcelError('Solicitud inválida.')
                token=req.get('token','')
                if not isinstance(token,str):raise ExcelError('Token inválido.')
                item=get_token(token)
                if not item:raise ExcelError('La previsualización venció. Vuelve a procesar.')
                if req.get('ack') is not True:raise ExcelError('Confirma que revisaste los datos.')
                draft=req.get('draft') is True
                if item['report']['can_publish'] is False and not draft:
                    raise ExcelError('Hay errores bloqueantes. Solo puedes descargar un borrador NO PUBLICAR.')
                with LOCK:item['approved']='draft' if draft else 'publish'
                return self.send_json({'download':'/api/download/'+token,'draft':draft})
            return self.send_json({'error':'Ruta no encontrada.'},404)
        except (ExcelError,ValueError,KeyError,UnicodeError,OSError) as exc:
            return self.send_json({'error':str(exc)},400)
        except Exception:
            logging.exception('Error inesperado durante el procesamiento')
            return self.send_json({'error':'Error interno. Revisa la consola para detalles.'},500)


def main():
    import argparse
    parser=argparse.ArgumentParser(description='Automatizador Falabella offline')
    parser.add_argument('--port',type=int,default=5000)
    parser.add_argument('--no-browser',action='store_true')
    args=parser.parse_args()
    if not (1024<=args.port<=65535):parser.error('El puerto debe estar entre 1024 y 65535.')
    logging.basicConfig(level=logging.INFO,format='%(levelname)s: %(message)s')
    url=f'http://127.0.0.1:{args.port}'
    print('\nIBERIA | AUTOMATIZADOR FALABELLA 2.2')
    print('Interfaz: '+url)
    print('Los archivos se procesan solo en tu PC. Ctrl+C para cerrar.\n')
    if not args.no_browser:Timer(0.8,lambda:webbrowser.open(url)).start()
    server=ThreadingHTTPServer(('127.0.0.1',args.port),Server)
    try:server.serve_forever()
    except KeyboardInterrupt:pass
    finally:server.server_close()

if __name__=='__main__':main()
