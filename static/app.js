'use strict';
const $ = id => document.getElementById(id);
const form=$('work-form');
let current=null;
const text=(id,v)=>{$(id).textContent=String(v??'');};
const el=(tag,content,className='')=>{const e=document.createElement(tag);if(className)e.className=className;if(content!=null)e.textContent=String(content);return e;};
const readable=({ready:'Listo',warning:'Advertencia',blocked:'Bloqueado'});
const settingsKeys=['parents','owner','name','brand','category','uniform_price','parent_mode','dimension_mode','pack_mapping','manual_prices','photos','prices','descriptions','blank'];
function savePreferences(){
  const pref={};for(const key of settingsKeys){const input=form.elements.namedItem(key);if(input)pref[key]=input.type==='checkbox'?input.checked:input.value;}
  localStorage.setItem('iberia_falabella_preferences_v2',JSON.stringify(pref));notice('Preferencias guardadas en este navegador, no incluyen archivos.');
}
function loadPreferences(){
  try{const prefs=JSON.parse(localStorage.getItem('iberia_falabella_preferences_v2')||'null');if(!prefs)return;
    for(const key of settingsKeys){const input=form.elements.namedItem(key);if(input&&Object.hasOwn(prefs,key)){if(input.type==='checkbox')input.checked=!!prefs[key];else input.value=prefs[key];}}
  }catch(err){console.warn('Preferencias inválidas',err);}
}
function notice(message){let b=$('toast');if(!b){b=el('div',null,'toast');b.id='toast';document.body.appendChild(b)}b.textContent=message;b.hidden=false;setTimeout(()=>b.hidden=true,4000);}
for(const input of document.querySelectorAll('.upload input')){
  input.addEventListener('change',()=>{
    const label=input.closest('.upload');label.classList.toggle('uploaded',input.files.length>0);
    label.querySelector('.selected').textContent=input.files.length?input.files[0].name:'Seleccionar archivo';
  });
}
async function postJSON(path,payload){
 const r=await fetch(path,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)});const data=await r.json();if(!r.ok)throw Error(data.error||'Solicitud fallida.');return data;
}
function showError(e){text('error-message',e.message||String(e));$('error-box').hidden=false;$('error-box').scrollIntoView({behavior:'smooth',block:'center'});}
async function loadHistory(){
 try{const r=await fetch('/api/history');const data=await r.json();const root=$('history-list');root.replaceChildren();
  if(!data.history.length){root.append(el('p','No hay ejecuciones registradas.','muted'));return;}
  for(const item of data.history.slice(0,7)){
    const line=el('div',null,'history-item');const left=el('div');
    left.append(el('strong',new Date(item.timestamp).toLocaleString('es-CL')));
    left.append(el('small',`${item.total} productos · ${item.changed_cells} cambios`));
    line.append(left,el('span',item.blocked?`${item.blocked} bloqueados`:'Sin bloqueos',item.blocked?'bad':'good'));root.append(line);
  }
 }catch(err){console.warn('Historial no disponible',err);}
}
function addIssueList(container,issues){
 const ul=el('ul',null,'issue-list');for(const issue of issues){const li=el('li',issue.message,`issue ${issue.level}`);ul.append(li);}container.append(ul);
}
function renderRow(item){
 const tr=el('tr');tr.dataset.status=item.status;tr.dataset.search=(item.sku+' '+item.owner+' '+item.parent).toLocaleLowerCase();
 for(const col of ['row','sku','size','price','images','changed']){
   const cell=el('td',item[col]);if(col==='sku')cell.className='code';tr.append(cell);
 }
 tr.append(el('td',readable[item.status]||item.status,`chip ${item.status}`));
 const detail=el('td');const button=el('button',`Ver ${item.issues.length} avisos / ${item.diff.length} cambios`,'plain detail-button');button.type='button';
 const details=el('div',null,'row-details');details.hidden=true;
 if(item.issues.length)addIssueList(details,item.issues);
 if(item.diff.length){const tbl=el('table',null,'change-table');const header=el('tr');for(const h of ['Celda','Campo','Anterior','Nuevo'])header.append(el('th',h));tbl.append(header);
   for(const d of item.diff){const r=el('tr');for(const field of ['column','field','before','after'])r.append(el('td',d[field]));tbl.append(r)}details.append(tbl);
 } else details.append(el('p','No se aplicaron cambios a esta fila.','muted'));
 if(item.image_note)details.append(el('p',item.image_note,'muted'));
 button.addEventListener('click',()=>{details.hidden=!details.hidden;button.textContent=details.hidden?'Ver detalle':'Ocultar detalle'});
 detail.append(button,details);tr.append(detail);return tr;
}
function filterRows(){
 const filter=$('status-filter').value;const value=$('sku-search').value.trim().toLocaleLowerCase();
 for(const row of $('result-rows').children)row.hidden=!( (filter==='all'||row.dataset.status===filter)&&row.dataset.search.includes(value));
}
function showPreview(resp){
 current=resp;const r=resp.report;const st=r.stats;
 for(const [key,val] of [['count-total',st.total],['count-ready',st.ready||0],['count-warn',st.warnings||0],['count-blocked',st.blocked||0],['count-changes',st.changed_cells||0]])text(key,val);
 const blocked=(st.blocked||0)>0;
 const banner=$('status-banner');banner.className='status-banner '+(blocked?'danger':'success');
 banner.textContent=blocked?`${st.blocked} producto(s) tienen errores críticos. No podrás descargar un archivo identificado como listo para publicar. Puedes exportar un borrador NO PUBLICAR.`:'No se detectaron errores bloqueantes en los campos controlados. Aun debes revisar reglas particulares de Seller Center y hacer una carga piloto.';
 text('result-desc',`${r.items.length} productos revisados · ${r.rows} filas modificadas · generado ${new Date(r.generated_at).toLocaleString('es-CL')}`);
 const ul=$('global-notes');ul.replaceChildren();addIssueList(ul,r.global_issues);
 text('note-count',r.global_issues.length);
 text('integrity-note',r.integrity.parts_unchanged?'Validación OOXML superada: partes externas a la hoja, estilos de celdas y ZIP comprobados.':'Validación de integridad pendiente.');
 const tbody=$('result-rows');tbody.replaceChildren();for(const item of r.items)tbody.append(renderRow(item));
 $('status-filter').value='all';$('sku-search').value='';
 $('report-download').href='/api/report/'+encodeURIComponent(resp.token)+'.csv';
 $('audit-download').href='/api/report-json/'+encodeURIComponent(resp.token)+'.json';
 $('ack').checked=false;updateDownloadButtons();$('result').hidden=false;$('result').scrollIntoView({behavior:'smooth',block:'start'});
}
function updateDownloadButtons(){
 const ok=!!current && $('ack').checked;
 $('download-final').disabled=!ok||!current.report.can_publish;
 $('download-draft').disabled=!ok;
}
async function download(draft){
 if(!current||!$('ack').checked)return;
 try{
  const info=await postJSON('/api/approve',{token:current.token,ack:true,draft});
  const link=document.createElement('a');link.href=info.download;link.download='';document.body.append(link);link.click();link.remove();
  notice(draft?'Borrador generado. NO debes cargarlo en Seller Center.':'Archivo disponible para revisión final.');
 }catch(e){showError(e)}
}
form.addEventListener('submit',async ev=>{
 ev.preventDefault();current=null;$('result').hidden=true;$('error-box').hidden=true;
 const btn=$('preview-button');btn.disabled=true;btn.textContent='Analizando archivos y comprobando integridad…';
 try{
  const response=await fetch('/api/preview',{method:'POST',body:new FormData(form)});
  let data;try{data=await response.json()}catch{throw Error('El servidor no devolvió un resultado válido.');}
  if(!response.ok)throw Error(data.error||'No se pudo procesar el archivo.');
  showPreview(data);loadHistory();
 }catch(e){showError(e)}finally{btn.disabled=false;btn.innerHTML='Analizar y previsualizar <span>→</span>';}
});
$('ack').addEventListener('change',updateDownloadButtons);
$('status-filter').addEventListener('change',filterRows);
$('sku-search').addEventListener('input',filterRows);
$('download-final').addEventListener('click',()=>download(false));
$('download-draft').addEventListener('click',()=>download(true));
$('save-preferences').addEventListener('click',savePreferences);
$('reset-preferences').addEventListener('click',()=>{localStorage.removeItem('iberia_falabella_preferences_v2');form.reset();notice('Preferencias restablecidas. Los archivos adjuntos deben volver a seleccionarse.');});
$('refresh-history').addEventListener('click',loadHistory);
$('config-download').addEventListener('click',async()=>{
 try{const r=await fetch('/api/config');const data=await r.json();
  const url=URL.createObjectURL(new Blob([JSON.stringify(data,null,2)],{type:'application/json'}));
  const a=document.createElement('a');a.href=url;a.download='mapeo_iberia_base.json';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
 }catch(e){showError(e)}
});
loadPreferences();loadHistory();
