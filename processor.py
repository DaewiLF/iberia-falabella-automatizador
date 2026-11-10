"""Reglas de negocio para consolidación segura, con previsualización y validaciones.
No crea libros desde cero: delega la escritura quirúrgica a ooxml.py.
"""
from __future__ import annotations
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime
from io import BytesIO, StringIO
import csv
import hashlib
import json
import re
from typing import Any
from urllib.parse import urlsplit
from xml.etree import ElementTree as ET
from zipfile import ZipFile

from ooxml import (
    ExcelError, clean, normalized_sku, number, read_rows, validate_ean13,
    worksheet_path, write_unchanged_template, ROW_RE, CELL_RE, MAIN,
)

COLUMN_KEYS = {
    'responsables': {'parent':'A','sku':'B','description':'C','source_height':'D','width':'E','depth':'F','weight':'G','size':'H','owner':'I','state':'J'},
    'fotos': {'sku':'B','state':'C','url1':'D','url2':'E','url3':'F','url4':'G','url5':'H','url6':'I'},
    'precios': {'sku':'B','price':'AB'},
    'precios_finales': {'sku':'A','price':'B'},
}
SOURCES = {
    'responsables': {'sheet':'Hoja 1', 'header_row':1},
    'fotos': {'sheet':'Hoja 1', 'header_row':1},
    'precios': {'sheet':'Alpargatas Iberia 15', 'header_row':2},
    'precios_finales': {'sheet':None, 'header_row':1},
}
HEADERS = {
    'responsables': {'parent':('SKU PADRE',), 'sku':('SKU HIJO/VENDEDOR','SKU HIJO','SKU VENDEDOR'),
                     'size':('TALLA',), 'width':('ANCHO',), 'source_height':('ALTO',),
                     'depth':('PROFUNDIDAD',), 'weight':('PESO',), 'owner':('RESPONSABLES','RESPONSABLE')},
    'fotos': {'sku':('SKU',), 'url1':('URL JPG 1','URL 1','FOTO 1'), 'url2':('URL JPG 2','URL 2','FOTO 2'), 'url3':('URL JPG 3','URL 3','FOTO 3'), 'url4':('URL JPG 4','URL 4','FOTO 4'), 'url5':('URL JPG 5','URL 5','FOTO 5'), 'url6':('URL JPG 6','URL 6','FOTO 6'), 'state':('ESTADO',)},
    'precios': {'sku':('SKU ML','SKU','SKU VENDEDOR'), 'price':('PRECIO FINAL REDONDEO','PRECIO FINAL','PRECIO')},
    'precios_finales': {'sku':('SKU','SKU VENDEDOR','SKU HIJO/VENDEDOR','SKU ML'),
                       'price':('PRECIO FINAL','PRECIO','PRECIO FINAL REDONDEO','PRICE')},
}
DEST = {'name':'A','brand':'B','description':'D','category':'E','size':'I','sku':'J','barcode':'K',
        'parent':'L','price':'N','width':'AK','length':'AL','height':'AM','weight':'AN',
        'image1':'AQ','image2':'AR','image3':'AS','image4':'AT','image5':'AU','image6':'AV','image7':'AW','image8':'AX'}
DEST_HEADERS = {'sku':'SKU del vendedor', 'parent':'SKU Padre', 'size':'Size', 'price':'PriceFalabella',
                'width':'Ancho','length':'Largo','height':'Alto','weight':'Peso'}
LABELS = {**{v:k for k,v in DEST.items()}, **{'AK':'Ancho','AL':'Largo','AM':'Alto','AN':'Peso','AQ':'Imagen principal','N':'Precio','L':'SKU padre','J':'SKU vendedor','K':'EAN/GTIN'}}
IMAGE_COLS = [DEST['image'+str(i)] for i in range(1,9)]
REQUIRED = ('sku','parent','size','name','brand','description','category','price','width','length','height','weight','barcode')
MAX_ITEMS = 1500


def default_config():
    return {'version':2, 'sources': {
        name: {'sheet': opts['sheet'], 'header_row':opts['header_row'], 'columns':COLUMN_KEYS[name].copy()}
        for name,opts in SOURCES.items()
    }, 'destination':{'sheet':'Subir plantilla','header_row':4,'start_row':5,'max_row':2000,'columns':DEST.copy()}}


def normalized_label(value):
    import unicodedata
    s = unicodedata.normalize('NFKD',clean(value))
    s = ''.join(c for c in s if not unicodedata.combining(c))
    return re.sub(r'[^A-Z0-9]+',' ',s.upper()).strip()


def parse_config(raw):
    if raw is None or not clean(raw):
        return default_config()
    if isinstance(raw,bytes):
        raw=raw.decode('utf-8-sig')
    try: incoming=json.loads(raw)
    except (ValueError,UnicodeError) as e:
        raise ExcelError('La configuración JSON no es válida.') from e
    if not isinstance(incoming,dict):
        raise ExcelError('La configuración debe ser un objeto JSON.')
    base=default_config()
    source_changes=incoming.get('sources',{})
    if not isinstance(source_changes,dict):raise ExcelError('La sección sources debe ser un objeto JSON.')
    for src, opt in source_changes.items():
        if src not in base['sources'] or not isinstance(opt,dict):
            raise ExcelError('Origen desconocido en configuración: '+src)
        for k in ('sheet','header_row'):
            if k in opt: base['sources'][src][k]=opt[k]
        if not isinstance(opt.get('columns',{}),dict):raise ExcelError('Las columnas deben ser un objeto JSON.')
        for field, col in opt.get('columns',{}).items():
            if field not in COLUMN_KEYS[src]: raise ExcelError('Campo desconocido en '+src+': '+field)
            base['sources'][src]['columns'][field]=col
        if 'headers' in opt:
            heads=opt['headers']
            if not isinstance(heads,dict):raise ExcelError('Los encabezados personalizados deben ser un objeto JSON.')
            if any(k not in COLUMN_KEYS[src] or not isinstance(v,str) or not v.strip() for k,v in heads.items()):
                raise ExcelError('Encabezados personalizados inválidos en '+src)
            base['sources'][src]['headers']=heads
    opt=incoming.get('destination',{})
    if opt:
        if not isinstance(opt,dict): raise ExcelError('Destino de configuración inválido.')
        if not isinstance(opt.get('columns',{}),dict):raise ExcelError('Las columnas de destino deben ser un objeto JSON.')
        for k in ('sheet','header_row','start_row','max_row'):
            if k in opt: base['destination'][k]=opt[k]
        for field,col in opt.get('columns',{}).items():
            if field not in DEST: raise ExcelError('Campo de destino desconocido: '+field)
            base['destination']['columns'][field]=col
    for src,opts in base['sources'].items():
        if opts['sheet'] is not None and (not isinstance(opts['sheet'],str) or len(opts['sheet'])>60):
            raise ExcelError('Nombre de hoja inválido para '+src)
        if not isinstance(opts['header_row'],int) or opts['header_row'] not in range(1,21):
            raise ExcelError('Fila de encabezado inválida para '+src)
        if any(not re.fullmatch(r'[A-Z]{1,3}',str(v)) for v in opts['columns'].values()):
            raise ExcelError('Las columnas del origen '+src+' deben usar letras A-ZZZ.')
    dest=base['destination']
    if any(not re.fullmatch(r'[A-Z]{1,3}',str(v)) for v in dest['columns'].values()):
        raise ExcelError('Las columnas de destino deben usar letras de Excel.')
    if len(set(dest['columns'].values())) != len(dest['columns']):
        raise ExcelError('No puedes asignar dos campos de Falabella a la misma columna.')
    if (not all(isinstance(dest[k],int) for k in ('header_row','start_row','max_row')) or
        not (1 <= dest['header_row'] < dest['start_row'] <= dest['max_row'] <= 100000)):
        raise ExcelError('Rango de filas del destino inválido.')
    if not isinstance(dest['sheet'],str) or not dest['sheet']:
        raise ExcelError('Hoja de salida inválida.')
    return base


def all_sheet_names(blob):
    with ZipFile(BytesIO(blob)) as z:
        root=ET.fromstring(z.read('xl/workbook.xml'))
        return [s.attrib['name'] for s in root.findall('.//{%s}sheet'%MAIN)]


def get_headers(blob,sheet,row):
    rows=list(read_rows(blob,sheet,min_row=row,max_row=row))
    return rows[0][1] if rows else {}


def prepare_source(blob,source,cfg):
    """Retorna hoja, fila de datos y columnas detectadas con esquema explícito/validado."""
    spec=cfg['sources'][source]
    names=all_sheet_names(blob)
    sheet=spec['sheet']
    if sheet is None or sheet.casefold() not in [s.casefold() for s in names]:
        if source=='precios_finales':
            sheet=names[0]
        else:
            raise ExcelError(f'No existe la hoja "{sheet}" en el archivo {source}. Disponibles: {", ".join(names[:8])}')
    columns=spec['columns']
    hdr=get_headers(blob,sheet,spec['header_row'])
    normalized=defaultdict(list)
    for column,value in hdr.items():
        if clean(value): normalized[normalized_label(value)].append(column)
    missing=[]
    for field,choices in HEADERS[source].items():
        if field in spec.get('headers',{}):choices=(spec['headers'][field],)
        chosen=columns[field]
        valid_names={normalized_label(x) for x in choices}
        if normalized_label(hdr.get(chosen)) not in valid_names:
            # Si existe la cabecera esperada en otra columna, usarla automáticamente.
            matching=[col for value in valid_names for col in normalized.get(value,[])]
            if len(matching)==1:
                columns=columns.copy();columns[field]=matching[0]
            elif len(matching)>1:
                raise ExcelError(f'Encabezado alternativo ambiguo en {source}: {field}, columnas {", ".join(sorted(matching))}.')
            else:
                missing.append(f'{field} (esperado {" / ".join(choices)})')
    if missing:
        raise ExcelError(f'Encabezados de {source} incompatibles, hoja "{sheet}" fila {spec["header_row"]}: '+', '.join(missing))
    return sheet,spec['header_row']+1,columns


def source_rows(blob,source,cfg):
    sheet,start,cols=prepare_source(blob,source,cfg)
    letters=set(cols.values())
    for r,raw in read_rows(blob,sheet,cols=letters,min_row=start):
        yield r,{key:raw.get(col) for key,col in cols.items()},raw


def indexed_responsables(blob,cfg):
    records={};collisions=defaultdict(list);stats=Counter()
    for n,row,_ in source_rows(blob,'responsables',cfg):
        key=normalized_sku(row['sku'])
        if not key:continue
        stats['source_rows']+=1
        if key in records:
            collisions[key].append(n)
        else:records[key]=(n,row)
    for k,rows in collisions.items():
        rows.insert(0,records[k][0])
        stats['duplicate_sku']+=len(rows)-1
    return records,collisions,stats


def valid_url(v):
    try:
        s=urlsplit(clean(v));return s.scheme.lower() in ('http','https') and bool(s.hostname) and not s.username and not s.password
    except ValueError:return False


def indexed_photos(blob,cfg):
    photos={}; ambiguous=set();invalid=0
    for n,r,_ in source_rows(blob,'fotos',cfg):
        key=normalized_sku(r['sku'])
        if not key:continue
        # Fotos pendientes o rechazadas no deben publicarse automáticamente.
        status=normalized_label(r.get('state'))
        if status not in ('LISTO','APROBADO','APROBADA','SUBIDA','PUBLICADO'):
            continue
        urls=[]
        for i in range(1,7):
            v=clean(r.get('url'+str(i)))
            if v and not valid_url(v):invalid+=1
            if v and valid_url(v) and v not in urls:urls.append(v)
        if not urls:continue
        if key in photos and photos[key] != urls:
            ambiguous.add(key)
        else:photos[key]=urls
    return photos,ambiguous,invalid


def indexed_prices(blob,source,cfg):
    prices={};ambiguous=set();nocache=0;rows=0
    for n,r,raw in source_rows(blob,source,cfg):
        key=normalized_sku(r['sku'])
        if not key:continue
        rows+=1
        val=number(r['price'])
        if val is None or val<=0:
            if raw.get(cfg['sources'][source]['columns']['price']+'_SIN_CACHE'):nocache+=1
            continue
        if key in prices and prices[key]!=val:ambiguous.add(key)
        prices[key]=val
    return prices,ambiguous,nocache,rows


def parse_price_overrides(text):
    """SKU;precio por línea. Se importan también como texto para resolver packs."""
    result={};duplicate=set()
    for i,raw in enumerate(str(text or '').splitlines(),1):
        raw=raw.strip()
        if not raw or raw.startswith('#'):continue
        bits=raw.split(';') if ';' in raw else raw.split('=',1)
        if len(bits)!=2:raise ExcelError(f'Precios manuales línea {i}: usa SKU;PRECIO.')
        k=normalized_sku(bits[0]);val=number(bits[1])
        if not k or val is None or val<=0:raise ExcelError(f'Precio manual inválido en línea {i}.')
        if k in result and result[k]!=val:duplicate.add(k)
        result[k]=val
    if duplicate:raise ExcelError('Precios manuales contradictorios: '+', '.join(sorted(duplicate)[:5]))
    return result


def parse_pack_overrides(text):
    """SKU-PADRE = SKU-A, SKU-B, SKU-C."""
    result={}
    for ix,line in enumerate(str(text or '').splitlines(),1):
        line=line.strip()
        if not line or line.startswith('#'):continue
        if '=' not in line:raise ExcelError(f'Pack línea {ix}: usa SKU-PADRE = SKU1, SKU2.')
        parent,parts=line.split('=',1)
        key=normalized_sku(parent)
        members=[normalized_sku(p) for p in re.split(r'[,;]',parts) if clean(p)]
        if not key or not members or len(set(members))!=len(members):
            raise ExcelError(f'Pack línea {ix}: SKU o componentes inválidos/repetidos.')
        if key in result and result[key]!=members:
            raise ExcelError(f'Composiciones duplicadas y contradictorias para {key}.')
        result[key]=members
    return result


def infer_components(parent,available):
    if parent in available:return [parent],False
    # Encuentra particiones completas y sin solapamiento; jamás elige una desambiguación al azar.
    tokens=parent.split('-')
    pieces={tuple(s.split('-')):s for s in available}
    solutions=[]
    def walk(pos,steps):
        if len(solutions)>1:return
        if pos==len(tokens):solutions.append(steps);return
        for part,key in pieces.items():
            n=len(part)
            if tuple(tokens[pos:pos+n])==part:
                walk(pos+n,steps+[key])
    walk(0,[])
    if len(solutions)==1:return solutions[0],False
    return [],len(solutions)>1


def choose_images(parent,photos,ambiguous,pack_overrides):
    components=pack_overrides.get(parent)
    inferred=False
    if components is None:
        components,amb=infer_components(parent,set(photos)|ambiguous)
        inferred=True
        if amb:return [],'Partición de pack ambigua',[]
    if not components:return [],'Sin coincidencia de fotos o composición definida',[]
    if any(c in ambiguous for c in components):return [],'Fotos de componente ambiguas',components
    if any(c not in photos for c in components):
        return [],'Faltan fotos de '+', '.join(c for c in components if c not in photos),components
    urls=[]
    # Una foto principal por componente antes de añadir fotos secundarias.
    for c in components:
        for u in photos[c][:1]:
            if u not in urls:urls.append(u)
    for idx in range(1,6):
        for c in components:
            if len(photos[c])>idx and photos[c][idx] not in urls:
                urls.append(photos[c][idx])
            if len(urls)>=8:break
        if len(urls)>=8:break
    return urls, 'Componentes inferidos desde los SKU de fotos' if inferred and len(components)>1 else '',components


def parse_filter(raw):
    return {normalized_sku(x) for x in re.split(r'[\n,;]+',raw or '') if clean(x)}


def read_destination(blob,cfg):
    spec=cfg['destination']
    headers=get_headers(blob,spec['sheet'],spec['header_row'])
    labels=spec['columns']
    missing=[]
    for name,text in DEST_HEADERS.items():
        value=normalized_label(headers.get(labels[name]))
        if normalized_label(text) not in value:
            missing.append(f'{labels[name]} ({text})')
    if missing:raise ExcelError('La plantilla Falabella no coincide con su estructura esperada (fila 4): '+', '.join(missing))
    cols=set(labels.values())
    records=list(read_rows(blob,spec['sheet'],cols=cols,min_row=spec['start_row'],max_row=spec['max_row']))
    return [(i,{k:r.get(col) for k,col in labels.items()}) for i,r in records]


def prepared_rows(blob,cfg):
    spec=cfg['destination']
    with ZipFile(BytesIO(blob)) as z:
        xml=z.read(worksheet_path(z,spec['sheet']))
    return {int(m.group(1)) for m in ROW_RE.finditer(xml) if spec['start_row']<=int(m.group(1))<=spec['max_row']}


def cell_match(xml,coordinate):
    for m in CELL_RE.finditer(xml):
        if (m.group(1)+m.group(2)).decode('ascii')==coordinate:return m.group(0)
    return None


def verify_output(original,result,changes,cfg):
    """Exige igualdad binaria de TODAS las partes salvo la hoja escrita y conserva metadatos de celdas.
    No certifica reglas de negocio del Seller Center.
    """
    with ZipFile(BytesIO(original)) as a,ZipFile(BytesIO(result)) as b:
        if a.namelist()!=b.namelist():raise ExcelError('Integridad: cambió la lista de partes del libro.')
        target=worksheet_path(a,cfg['destination']['sheet'])
        for name in a.namelist():
            if name!=target and a.read(name)!=b.read(name):
                raise ExcelError('Integridad: se modificó una parte protegida: '+name)
        before=a.read(target);after=b.read(target)
        if changes:
            # El archivo XML fuera de las filas permitidas debe quedar idéntico,
            # incluyendo validaciones, comentarios, merges, protección y orden.
            def ignore_changed_rows(xml):
                return ROW_RE.sub(lambda m: b'[[ROW]]' if int(m.group(1)) in changes else m.group(0),xml)
            if ignore_changed_rows(before)!=ignore_changed_rows(after):
                raise ExcelError('Integridad: hubo cambios fuera de las filas autorizadas.')
            # Bloquea escritura en rangos combinados: aunque se mantenga el formato,
            # escribir celdas internas de un merge puede volver inválido el libro.
            merged=[]
            for m in re.finditer(rb'<mergeCell\b[^>]*?\bref="([A-Z]+[0-9]+):([A-Z]+[0-9]+)"',before):
                merged.append((m.group(1).decode('ascii'),m.group(2).decode('ascii')))
            def position(addr):
                cell=re.fullmatch(r'([A-Z]+)([0-9]+)',addr)
                n=0
                for char in cell.group(1):n=n*26+ord(char)-64
                return n,int(cell.group(2))
            for row_number,columns in changes.items():
                for col in columns:
                    x,y=position(f'{col}{row_number}')
                    for start,end in merged:
                        a_col,a_row=position(start);b_col,b_row=position(end)
                        if a_col<=x<=b_col and a_row<=y<=b_row:
                            raise ExcelError(f'La celda {col}{row_number} pertenece a un rango combinado protegido: {start}:{end}.')
            # Garantiza que en cada fila solo cambian las celdas incluidas en el plan.
            rb={int(m.group(1)):m.group(0) for m in ROW_RE.finditer(before) if int(m.group(1)) in changes}
            ra={int(m.group(1)):m.group(0) for m in ROW_RE.finditer(after) if int(m.group(1)) in changes}
            if rb.keys()!=ra.keys():raise ExcelError('Integridad: filas desaparecidas de la plantilla.')
            for rn,columns in changes.items():
                before_row=rb[rn];after_row=ra[rn]
                for col in columns:
                    coord=f'{col}{rn}'; old=cell_match(before_row,coord);new=cell_match(after_row,coord)
                    if not new:raise ExcelError('Integridad: falta '+coord)
                    if old:
                        old_tag=re.match(rb'<c\b[^>]*?/?>',old).group(0)
                        new_tag=re.match(rb'<c\b[^>]*?/?>',new).group(0)
                        for attr in (b's',b'cm',b'vm',b'ph'):
                            exp=rb'\b'+attr+rb'="([^"]*)"'
                            x=re.search(exp,old_tag);y=re.search(exp,new_tag)
                            if (x.group(1) if x else None)!=(y.group(1) if y else None):
                                raise ExcelError('Integridad: cambió el estilo/metadato de '+coord)
                        if b'<f' in old:raise ExcelError('No se permite reemplazar fórmulas en '+coord)
                # Normaliza SOLO las celdas autorizadas para comprobar la igualdad exacta restante.
                def strip_targets(row):
                    matches=list(CELL_RE.finditer(row))
                    for m in reversed(matches):
                        col=m.group(1).decode('ascii')
                        if col in columns:
                            row=row[:m.start()]+row[m.end():]
                    return row
                if strip_targets(before_row)!=strip_targets(after_row):
                    raise ExcelError('Integridad: cambio fuera de las celdas autorizadas, fila '+str(rn))
        if b.testzip() is not None:raise ExcelError('Integridad ZIP inválida.')
    return {'parts_unchanged':True,'cell_styles_unchanged':True,'zip_ok':True,
            'target_sheet':cfg['destination']['sheet'],'modified_cells':sum(len(c) for c in changes.values())}


def add_issue(issues,level,msg,code):
    if not any(x['code']==code and x['message']==msg for x in issues):
        issues.append({'level':level,'message':msg,'code':code})


def validate_row(result, issues, check_images=True):
    for name in REQUIRED:
        val=result.get(name)
        if name in ('price','width','length','height','weight','size'):
            val_num=number(val)
            if val_num is None or val_num<=0:
                add_issue(issues,'error',f'Campo {name} vacío o no positivo.','required_'+name)
        elif name=='barcode':
            if not clean(val):
                add_issue(issues,'error','EAN/GTIN faltante; no se generan códigos aleatorios.','missing_ean')
            elif not validate_ean13(val):
                add_issue(issues,'error','EAN-13 no supera validación de longitud/dígito verificador.','invalid_ean')
        elif not clean(val):
            add_issue(issues,'error','Campo '+name+' vacío.','required_'+name)
    if check_images and not valid_url(result.get('image1')):
        add_issue(issues,'error','Imagen principal no disponible o URL inválida.','missing_image')
    for i in range(1,9):
        v=result.get('image'+str(i))
        if clean(v) and not valid_url(v):
            add_issue(issues,'warning',f'Imagen {i} tiene URL inválida.','invalid_url_'+str(i))


def process(template:bytes,responsables:bytes, photos:bytes|None=None,prices:bytes|None=None,
            final_prices:bytes|None=None,*, options:dict|None=None, config:dict|str|None=None):
    """Devuelve (xlsx candidato, reporte). Descarga apta solo si report.can_publish == True."""
    options=options or {}
    cfg=parse_config(config) if not isinstance(config,dict) else parse_config(json.dumps(config))
    for name,blob in [('Falabella',template),('Responsables',responsables),('Fotos',photos),('Precios',prices),('Precios finales',final_prices)]:
        if blob:
            from ooxml import safe_xlsx
            safe_xlsx(blob)
    base_rows=read_destination(template,cfg)
    cols=cfg['destination']['columns']
    recs,duplicates,source_stats=indexed_responsables(responsables,cfg)
    photos_map,photos_ambig,bad_urls=indexed_photos(photos,cfg) if photos else ({},set(),0)
    base_prices,amb_prices,nocache,price_rows=indexed_prices(prices,'precios',cfg) if prices else ({},set(),0,0)
    final_map,final_ambig,final_nocache,final_rows=indexed_prices(final_prices,'precios_finales',cfg) if final_prices else ({},set(),0,0)
    # SKU padre o SKU vendedor presentes en la planilla de precio final pueden servir como clave.
    overrides=parse_price_overrides(options.get('manual_prices',''))
    packs=parse_pack_overrides(options.get('pack_mapping',''))
    manual_price=number(options.get('uniform_price'))
    if clean(options.get('uniform_price')) and (manual_price is None or manual_price<=0):
        raise ExcelError('El precio uniforme debe ser positivo.')
    included=parse_filter(options.get('parents',''))
    owner=clean(options.get('owner')).casefold()
    update_desc=bool(options.get('descriptions',False))
    update_photo=bool(options.get('photos',True))
    update_price=bool(options.get('prices',True))
    allow_blank=bool(options.get('blank',False))
    use_first_child=options.get('parent_mode')=='smallest_child'
    dimension_mode=options.get('dimension_mode','legacy')
    if dimension_mode not in ('legacy','swapped'):
        raise ExcelError('Mapeo de dimensiones no reconocido.')
    existing=[(n,d) for n,d in base_rows if normalized_sku(d.get('sku'))]
    blank_mode=not existing
    if blank_mode and not allow_blank:
        raise ExcelError('Plantilla vacía: marca "Crear desde filas preformateadas" para continuar.')
    issues_global=[];items=[];planned={}; stats=Counter();prices_used={}; photos_used={}
    if photos and bad_urls:
        issues_global.append({'level':'warning','message':f'{bad_urls} URLs de fotos inválidas ignoradas.','code':'bad_photo_urls'})
    if prices and nocache:
        issues_global.append({'level':'warning','message':f'{nocache} fórmulas de precio no tienen valor guardado. Recalcula el libro en Excel o adjunta precios finales.','code':'price_cache'})
    if final_prices and final_nocache:
        issues_global.append({'level':'warning','message':f'{final_nocache} precios finales sin cálculo guardado.','code':'final_cache'})
    if duplicates:
        issues_global.append({'level':'warning','message':f'{len(duplicates)} SKU duplicados/colisionados en Responsables. Se bloquean las filas afectadas.','code':'dupe_sku'})
    if dimension_mode=='legacy':
        issues_global.append({'level':'warning','message':'Confirma el mapeo físico: largo Falabella ← alto de Responsables; alto Falabella ← profundidad.','code':'dim_review'})
    issues_global.append({'level':'warning','message':'Comprueba si Falabella exige SKU padre real o SKU de la variante menor para agrupar tallas.','code':'parent_review'})
    rows_by_sku={}
    if existing:
        for rownum,old in existing:
            key=normalized_sku(old.get('sku'))
            rows_by_sku.setdefault(key,[]).append(rownum)
        assignments=[]
        for rownum,old in existing:
            oldparent=normalized_sku(old.get('parent'))
            match=recs.get(normalized_sku(old.get('sku')))
            rec_parent=normalized_sku(match[1]['parent']) if match else ''
            if included and not ({oldparent,rec_parent}&included):continue
            if owner and (not match or clean(match[1]['owner']).casefold()!=owner):continue
            assignments.append((rownum,old,match))
    else:
        selected=[]
        for key,rec in recs.items():
            parent=normalized_sku(rec[1].get('parent'))
            if included and parent not in included:continue
            if owner and clean(rec[1]['owner']).casefold()!=owner:continue
            selected.append(rec)
        if not included and len(selected)>80:
            raise ExcelError('Plantilla vacía: especifica uno o varios SKU padre para evitar completar miles de filas por accidente.')
        if not selected:raise ExcelError('No hay productos de Responsables para los filtros elegidos.')
        selected.sort(key=lambda x:(normalized_sku(x[1].get('parent')),number(x[1].get('size')) or 0,normalized_sku(x[1].get('sku'))))
        prepared=prepared_rows(template,cfg)
        start=cfg['destination']['start_row']
        if len(selected)>MAX_ITEMS or any(start+i not in prepared for i in range(len(selected))):
            raise ExcelError('Faltan filas preformateadas en la plantilla. No se insertan filas porque podría romper validaciones o estilos.')
        old_by_row=dict(base_rows)
        assignments=[(start+i,old_by_row.get(start+i,{}),rec) for i,rec in enumerate(selected)]
        issues_global.append({'level':'warning','message':'Plantilla vacía: otros campos específicos de categoría no se completan automáticamente. Usa un archivo base con atributos y GTIN ya definidos.','code':'blank'})
    if len(assignments)>MAX_ITEMS:raise ExcelError('Selección demasiado grande. Divide el lote (máximo 1500 productos).')
    # El primer SKU hijo de cada padre se determina por la talla, sin asumir sufijos de nomenclatura.
    first_children={}
    grouped=defaultdict(list)
    for n,r in recs.values():grouped[normalized_sku(r.get('parent'))].append(r)
    for p,rows in grouped.items():
        if rows:
            rows.sort(key=lambda r:(number(r.get('size')) if number(r.get('size')) is not None else 999999,normalized_sku(r.get('sku'))))
            first_children[p]=clean(rows[0]['sku'])
    for destrow,old,match in assignments:
        issues=[];updates={};mapping={};recnum=None
        sku=clean(old.get('sku'))
        if match is None:
            add_issue(issues,'error','SKU no encontrado en Responsables.','sku_missing')
            rec={};parent=normalized_sku(old.get('parent'))
        else:
            recnum,rec=match
            sku=clean(rec.get('sku'))
            parent=normalized_sku(rec.get('parent'))
            key=normalized_sku(sku)
            if key in duplicates:
                add_issue(issues,'error',f'SKU ambiguo en Responsables, filas {duplicates[key]}.','sku_duplicate')
            if len(rows_by_sku.get(key,[]))>1:
                add_issue(issues,'error','SKU vendedor repetido en la plantilla destino.','template_duplicate')
            oldparent=normalized_sku(old.get('parent'))
            if oldparent and oldparent!=parent and not use_first_child:
                add_issue(issues,'error',f'SKU padre distinto entre Falabella ({oldparent}) y Responsables ({parent}).','parent_mismatch')
            if not any(i['level']=='error' for i in issues):
                mapping={
                    'sku':rec.get('sku'),'parent':(first_children.get(parent) if use_first_child else rec.get('parent')),
                    'size':rec.get('size'),'width':rec.get('width'),
                    'length':rec.get('source_height') if dimension_mode=='legacy' else rec.get('depth'),
                    'height':rec.get('depth') if dimension_mode=='legacy' else rec.get('source_height'),
                    'weight':rec.get('weight'),
                }
                if update_desc or blank_mode:mapping['description']=rec.get('description')
                if blank_mode:
                    if clean(options.get('name')):mapping['name']=clean(options.get('name'))
                    if clean(options.get('brand')):mapping['brand']=clean(options.get('brand'))
                    if clean(options.get('category')):mapping['category']=clean(options.get('category'))
                for field,v in mapping.items():
                    if v is None or clean(v)=='':continue
                    if field in ('size','width','length','height','weight'):
                        v=number(v)
                        if v is None or v<=0:
                            add_issue(issues,'warning',f'{field} no es un número positivo en Responsables.','bad_number_'+field)
                            continue
                    # Conservar EXACTAMENTE el SKU escrito por el operador: no normalizar el valor comercial.
                    updates[field]=v
                if update_price:
                    prices_options=[('Precio manual por SKU',overrides.get(key)),('Precio manual por padre',overrides.get(parent)),
                                    ('Archivo de precios finales por SKU',final_map.get(key)),('Archivo de precios finales por padre',final_map.get(parent)),
                                    ('Archivo de precios clásico por SKU',base_prices.get(key)),('Precio uniforme',manual_price)]
                    for label,pval in prices_options:
                        if pval is not None:
                            if (label.startswith('Archivo') and (key in final_ambig or parent in final_ambig or key in amb_prices)):
                                add_issue(issues,'error','Precios contradictorios para el SKU; requiere corrección.','price_ambiguous');break
                            updates['price']=pval;prices_used[destrow]=label;break
                    if 'price' not in updates and not number(old.get('price')):
                        add_issue(issues,'error','No hay precio final válido para este producto o pack.','price_missing')
                    if 'price' not in updates and number(old.get('price')):
                        add_issue(issues,'warning','Sin precio actualizado; se conserva el valor anterior.','price_existing')
                if update_photo:
                    urls,note,components=choose_images(parent,photos_map,photos_ambig,packs)
                    if urls:
                        photos_used[destrow]={'count':len(urls),'components':components,'note':note}
                        for i,link in enumerate(urls,1):updates['image'+str(i)]=link
                        # Borrar slots excedentes obsoletos para evitar mezcla de fotos antiguas.
                        for i in range(len(urls)+1,9):
                            if clean(old.get('image'+str(i))):updates['image'+str(i)]=''
                    elif photos:
                        add_issue(issues,'warning',note+'; se conservan las imágenes anteriores.','images_unmatched')
        # No tocar una fila con conflictos fuertes de identidad o correspondencia.
        if any(i['code'] in ('sku_missing','sku_duplicate','template_duplicate','parent_mismatch','price_ambiguous') for i in issues):
            updates={}
        complete={**old,**updates}
        validate_row(complete,issues)
        diff=[]
        for field,value in updates.items():
            oldval=old.get(field)
            if clean(oldval)==clean(value):continue
            diff.append({'column':cols[field],'field':field,'before':clean(oldval), 'after':clean(value)})
        # Los errores de identidad impiden editar la fila. Los campos obligatorios
        # ausentes permiten generar SOLO un borrador parcialmente rellenado.
        if diff:
            planned[destrow]={d['column']:updates[d['field']] for d in diff}
        state='blocked' if any(i['level']=='error' for i in issues) else 'warning' if any(i['level']=='warning' for i in issues) else 'ready'
        if state=='blocked':stats['blocked']+=1
        elif state=='warning':stats['warnings']+=1
        else:stats['ready']+=1
        if match:stats['matched']+=1
        stats['price_updated']+=int(any(d['field']=='price' for d in diff))
        stats['images_updated']+=int(any(d['field'].startswith('image') for d in diff))
        items.append({'row':destrow,'sku':sku,'parent':parent,'size':clean((match[1].get('size') if match else old.get('size'))),
                      'owner':clean((match[1].get('owner') if match else '')),'price':clean(complete.get('price')),
                      'price_source':prices_used.get(destrow,'Se conserva anterior'),'images':sum(bool(clean(complete.get('image'+str(i)))) for i in range(1,9)),
                      'image_note':photos_used.get(destrow,{}).get('note',''),
                      'issues':issues,'status':state,'changed':len(diff),'diff':diff,'responsables_row':recnum})
    if not items:raise ExcelError('No hay productos que coincidan con los filtros.')
    candidate=write_unchanged_template(template,planned,sheet_name=cfg['destination']['sheet'])
    integrity=verify_output(template,candidate,planned,cfg)
    stats['updated_rows']=len(planned)
    stats['changed_cells']=sum(len(x) for x in planned.values())
    stats['total']=len(items)
    # Precios e imagen principal ausentes no pueden pasar como publicables sin revisión.
    can_publish=stats['blocked']==0
    sources={'falabella':template,'responsables':responsables,'fotos':photos,
             'precios':prices,'precios_finales':final_prices}
    source_hashes={key:hashlib.sha256(blob).hexdigest() for key,blob in sources.items() if blob is not None}
    return candidate,{'version':'2.2','source_sha256':source_hashes,
                      'items':items,'global_issues':issues_global,
                      'stats':dict(stats),'blank_mode':blank_mode,'can_publish':can_publish,
                      'integrity':integrity,'changes':stats['changed_cells'],
                      'rows':stats['updated_rows'],'template_sha256':hashlib.sha256(template).hexdigest(),
                      'generated_at':datetime.now().astimezone().isoformat(timespec='seconds')}


def csv_safe(value):
    """Evita que un campo externo sea interpretado como fórmula en Excel/Calc."""
    if not isinstance(value,str):
        return value
    if value.lstrip(' \t\r\n').startswith(('=','+','-','@')) or value.startswith(('\t','\r','\n')):
        return "'"+value
    return value


def report_csv(report):
    out=StringIO();w=csv.writer(out,delimiter=';',lineterminator='\r\n')
    w.writerow(['Fila Falabella','SKU','SKU padre','Talla','Responsable','Estado','Precio','Origen del precio','N° fotos','Celdas cambiadas','Problemas'])
    for item in report['items']:
        values=[item.get(x,'') for x in ('row','sku','parent','size','owner','status','price','price_source','images','changed')]
        values.append(' | '.join(f"{q['level']}: {q['message']}" for q in item['issues']))
        w.writerow([csv_safe(value) for value in values])
    return ('\ufeff'+out.getvalue()).encode('utf-8')
