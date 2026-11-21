const $=s=>document.querySelector(s), $$=s=>[...document.querySelectorAll(s)];
let data, initialProfile, selected='Z02', scenario='base', filter='viable', configuringFirstTime=false;
let habitaMap, mapMarkers={};
const money=n=>new Intl.NumberFormat('es-MX',{style:'currency',currency:'MXN',maximumFractionDigits:n%1?2:0}).format(n);
const names={Z01:'Parque Norte',Z02:'Distrito Central',Z03:'Distrito Premium',Z04:'Colonia Compacta',Z05:'Corredor Periférico',Z06:'Zona en evaluación'};
const places={Z01:'Gustavo A. Madero, CDMX',Z02:'Cuauhtémoc, CDMX',Z03:'Miguel Hidalgo, CDMX',Z04:'Benito Juárez, CDMX',Z05:'Iztapalapa, CDMX',Z06:'Álvaro Obregón, CDMX'};
const rooms={Z01:2,Z02:3,Z03:3,Z04:1,Z05:2,Z06:2}, travel={Z01:35,Z02:25,Z03:20,Z04:20,Z05:70,Z06:30};
const coordinates={Z01:[19.4840,-99.1100],Z02:[19.4326,-99.1332],Z03:[19.4270,-99.1900],Z04:[19.3800,-99.1600],Z05:[19.3500,-99.0500],Z06:[19.3600,-99.2200]};
const finance=id=>data.finanzas.alternativas.find(x=>x.id===id), zone=id=>data.zonas.find(x=>x.id===id);
const payment=f=>scenario==='stress'?f.pago_estres:scenario==='short'?f.pago_plazo_corto:f.pago_total;

function property(){
  const z=zone(selected),f=finance(selected); if(!z||!f){$('#propertySummary').innerHTML='';return}
  $('#propertySummary').innerHTML=`<div><span class="badge">${z.cumple&&f.cumple?'COMPATIBLE':'REVISAR'}</span><span class="zone-id">${z.id}</span></div><p class="location">⌖ &nbsp;${places[z.id]}</p><h3>${names[z.id]}</h3><div class="price">${money(z.precio)}</div><div class="facts"><div><small>Habitaciones</small><b>⌁ &nbsp;${rooms[z.id]}</b></div><div><small>Traslado</small><b>◷ &nbsp;${travel[z.id]} min</b></div></div><div class="payment-box"><small>PAGO MENSUAL ESTIMADO</small><strong>${money(payment(f))}</strong></div><button class="primary" id="toCompare">Ver en el comparador</button>`;
  $('#toCompare').onclick=()=>$('#comparador').scrollIntoView({behavior:'smooth'});
}
function card(r){const f=finance(r.id),z=zone(r.id);return `<article class="rank-card"><div class="rank-head"><small>OPCIÓN ${r.posicion}</small><span class="zone-id">${r.id}</span><h3>⌖<br>${names[r.id]}</h3><p>Zona ficticia · ${Math.round(z.cobertura*100)}% cobertura</p></div><div class="rank-body"><div class="rank-values"><div><span>Precio de referencia</span><strong>${money(r.precio)}</strong></div><div><span>Pago en escenario</span><strong>${money(payment(f))}</strong></div></div><div class="rank-meta"><span>⌁ ${rooms[r.id]} habitaciones</span><span>◷ ${travel[r.id]} min traslado</span><span>♢ ${z.indicadores.seguridad}/100 seguridad</span></div><button class="detail-link" data-detail="${r.id}">Ver detalle</button></div>${f.estres_supera_limite?'<div class="warning">△ &nbsp; El pago de estrés supera tu límite mensual.</div>':''}<div class="score">${r.puntaje.toFixed(1)}</div><div class="score-label">AFINIDAD</div><br></article>`}
function detail(id){
  if(!id){$('#detail').hidden=true;return} $('#detail').hidden=false;selected=id;
  const z=zone(id),f=finance(id);let bars=Object.entries(z.indicadores).filter(([,v])=>v!=null).map(([k,v])=>`<div class="indicator"><span>${k[0].toUpperCase()+k.slice(1)}</span><b>${v}</b><div class="bar"><i style="width:${v}%"></i></div></div>`).join('');
  $('#detail').innerHTML=`<div class="detail-top"><span class="badge">${id}</span><p class="eyebrow">DETALLE DE ALTERNATIVA</p><h3>${names[id]}</h3></div><div class="finance"><span>Capital a financiar</span><strong>${money(f.capital)}</strong><hr><span>Enganche <b>${money(f.enganche)}</b></span></div><h4>INDICADORES DE ZONA</h4><div class="indicators">${bars}</div><div class="coordinator"><b>✣ &nbsp; Lectura del coordinador</b>${id===data.recomendacion_id?'Maximiza la puntuación ponderada por sus indicadores territoriales. Revisa también el escenario de estrés antes de decidir.':'Alternativa viable con un pago mensual menor. Revisa sus indicadores territoriales y la afinidad con tus prioridades.'}</div>`;
  property();refreshMapMarkers();
}
function bindDynamic(){$$('[data-detail]').forEach(b=>b.onclick=()=>{detail(b.dataset.detail);$('#detail').scrollIntoView({behavior:'smooth',block:'center'})})}
function markerIcon(id){const z=zone(id);return L.divIcon({className:'habita-marker',iconSize:[140,40],iconAnchor:[18,32],html:`<div class="map-pin ${selected===id?'active':''}"><b><span>⌂</span></b><em>${money(z.precio)}</em></div>`})}
function initMap(){
  if(typeof L==='undefined'){$('#realMap').innerHTML='<div class="map-loading">No fue posible cargar el mapa. Revisa tu conexión.</div>';return}
  $('#realMap').innerHTML='';
  habitaMap=L.map('realMap',{zoomControl:true,scrollWheelZoom:false}).setView([19.42,-99.14],11);
  L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png',{maxZoom:19,attribution:'&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'}).addTo(habitaMap);
  const note=document.createElement('div');note.className='map-note';note.textContent='Ubicaciones aproximadas · Datos simulados';$('#realMap').append(note);
}
function refreshMapMarkers(){
  if(!habitaMap||!data)return;Object.values(mapMarkers).forEach(marker=>marker.remove());mapMarkers={};
  const visible=filter==='viable'?new Set(data.ranking.map(r=>r.id)):new Set(data.zonas.map(z=>z.id));
  data.zonas.filter(z=>visible.has(z.id)).forEach(z=>{const marker=L.marker(coordinates[z.id],{icon:markerIcon(z.id),title:`${names[z.id]} · ${money(z.precio)}`}).addTo(habitaMap);marker.on('click',()=>detail(z.id));marker.bindTooltip(`${names[z.id]} · ${places[z.id]}`,{direction:'top',offset:[18,-28]});mapMarkers[z.id]=marker});
}
function applyFilter(){refreshMapMarkers()}
function render(){
  const count=data.ranking.length,total=data.zonas.length;$('#viableStat').textContent=count;$('#totalStat').textContent=total;$('#viableFilter').textContent=count;$('#allFilter').textContent=total;$('#limit').textContent=money(data.limite_pago);$('#budget').textContent=money(data.perfil.presupuesto_maximo);
  $('.hero h2').innerHTML=count?`${count} ${count===1?'alternativa se ajusta':'alternativas se ajustan'} a tu perfil`:'Ninguna alternativa cumple todos tus límites';
  $('#ranking').innerHTML=count?data.ranking.map(card).join(''):'<div class="empty-state"><h3>Sin alternativas viables</h3><p>Prueba aumentando el presupuesto o el pago máximo, o ajustando tus requisitos de traslado, habitaciones y seguridad.</p><button class="secondary" id="emptyAdjust">Ajustar perfil</button></div>';
  $('#discardedCount').textContent=`${data.descartadas.length} ${data.descartadas.length===1?'alternativa descartada':'alternativas descartadas'}`;$('#discardedList').innerHTML='<ul>'+data.descartadas.map(x=>`<li><b>${names[x.id]}</b>: ${x.motivos.join('; ')}.</li>`).join('')+'</ul>';
  if(count){detail(data.recomendacion_id)}else{detail(null);selected=data.zonas[0]?.id;property()}applyFilter();bindDynamic();if($('#emptyAdjust'))$('#emptyAdjust').onclick=openProfile;
}
function fillForm(profile){const form=$('#profileForm');for(const [key,value] of Object.entries(profile)){if(form.elements[key])form.elements[key].value=value}form.elements.tasa_anual_pct.value=(profile.tasa_anual*100).toFixed(1)}
function showFirstRun(){configuringFirstTime=true;document.body.classList.add('first-run');fillForm(data.perfil);$('#formError').textContent='';$('#profileDialog').show()}
function openProfile(){configuringFirstTime=false;document.body.classList.remove('first-run');fillForm(data.perfil);$('#formError').textContent='';$('#profileDialog').showModal()}
const wait=ms=>new Promise(resolve=>setTimeout(resolve,ms));
function resetAnalysis(){
  const dialog=$('#analysisDialog');dialog.classList.remove('finished');$('#analysisTitle').textContent='Analizando tu perfil';$('#analysisCopy').textContent='Los especialistas revisan tus límites antes de ordenar alternativas.';$('#analysisProgress').style.width='8%';$('#viewResults').hidden=true;
  $$('.analysis-steps article').forEach((item,index)=>{item.className='';item.querySelector('.step-state').textContent=index+1;item.querySelector('em').textContent='En espera'});
}
function activateStage(index){
  const steps=$$('.analysis-steps article');steps.forEach((item,i)=>{if(i<index){item.className='complete';item.querySelector('.step-state').textContent='✓';item.querySelector('em').textContent='Completado'}else if(i===index){item.className='active';item.querySelector('em').textContent='Analizando…'}});$('#analysisProgress').style.width=`${Math.min(88,18+index*23)}%`;
}
function finishAnalysis(pipeline){
  $$('.analysis-steps article').forEach((item,index)=>{item.className='complete';item.querySelector('.step-state').textContent='✓';const duration=pipeline?.[index]?.duration_ms;item.querySelector('em').textContent=duration==null?'Completado':`Completado · ${duration} ms`});
  $('#analysisProgress').style.width='100%';$('#analysisTitle').textContent='Análisis completado';$('#analysisCopy').textContent=`Encontramos ${data.ranking.length} ${data.ranking.length===1?'alternativa viable':'alternativas viables'} después de aplicar todas tus restricciones.`;$('#analysisDialog').classList.add('finished');$('#viewResults').hidden=false;
}
async function submitProfile(event){
  event.preventDefault();const form=event.currentTarget;if(!form.reportValidity())return;const button=$('#analyzeButton');form.classList.add('loading');button.textContent='Calculando…';$('#formError').textContent='';
  const payload={};for(const element of form.elements){if(element.name)payload[element.name]=Number(element.value)}payload.tasa_anual=payload.tasa_anual_pct/100;delete payload.tasa_anual_pct;
  const wasFirstRun=configuringFirstTime;$('#profileDialog').close();document.body.classList.remove('first-run');resetAnalysis();$('#analysisDialog').showModal();let stage=0;activateStage(stage);const ticker=setInterval(()=>{if(stage<3)activateStage(++stage)},430);
  try{const request=fetch('/api/analyze',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)}).then(async response=>{const result=await response.json();if(!response.ok)throw Error(result.error||'No se pudo recalcular.');return result});const [result]=await Promise.all([request,wait(1900)]);clearInterval(ticker);data=result;scenario='base';localStorage.setItem('habimas-configured','true');$$('[data-scenario]').forEach(x=>x.classList.toggle('active',x.dataset.scenario==='base'));render();finishAnalysis(data.pipeline)}catch(error){clearInterval(ticker);$('#analysisDialog').close();wasFirstRun?showFirstRun():openProfile();$('#formError').textContent=error.message}finally{form.classList.remove('loading');button.textContent='Recalcular análisis'}
}
function showToast(message){const t=$('#toast');t.textContent=message;t.classList.add('show');setTimeout(()=>t.classList.remove('show'),2800)}
async function init(){try{const r=await fetch('/api/dashboard');if(!r.ok)throw Error();data=await r.json();initialProfile=structuredClone(data.perfil);initMap();render();if(localStorage.getItem('habimas-configured')!=='true'||new URLSearchParams(location.search).has('setup'))showFirstRun()}catch{$('.page').innerHTML='<div class="empty-state" style="margin-top:4rem"><h3>No se pudo cargar el análisis</h3><p>Reinicia el servidor con <code>python3 server.py</code>.</p></div>'}}

$$('[data-scenario]').forEach(b=>b.onclick=()=>{scenario=b.dataset.scenario;$$('[data-scenario]').forEach(x=>x.classList.toggle('active',x===b));render()});
$$('[data-filter]').forEach(b=>b.onclick=()=>{filter=b.dataset.filter;$$('[data-filter]').forEach(x=>x.classList.toggle('active',x===b));applyFilter()});
$('#discardedButton').onclick=()=>{$('#discardedList').hidden=!$('#discardedList').hidden;$('#discardedButton em').textContent=$('#discardedList').hidden?'Ver motivos':'Ocultar motivos'};
$('#openMenu').onclick=()=>{$('#sidebar').classList.add('open');$('#scrim').classList.add('show')};$('#closeMenu').onclick=$('#scrim').onclick=()=>{$('#sidebar').classList.remove('open');$('#scrim').classList.remove('show')};$$('nav a').forEach(a=>a.onclick=()=>{$$('nav a').forEach(x=>x.classList.remove('active'));a.classList.add('active');$('#closeMenu').click()});
$('#profileButton').onclick=openProfile;$('#closeProfile').onclick=()=>$('#profileDialog').close();$('#resetProfile').onclick=()=>fillForm(initialProfile);$('#profileForm').onsubmit=submitProfile;init();
$('#viewResults').onclick=()=>{$('#analysisDialog').close();history.replaceState({},'',location.pathname);window.scrollTo({top:0,behavior:'smooth'});showToast(`Análisis actualizado: ${data.ranking.length} alternativas viables.`)};
