"""Dependency-free, read-only local monitoring page."""

PAGE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>z0_n3t | Network Monitor</title>
<style>
:root{color-scheme:dark;font-family:system-ui,-apple-system,sans-serif;
background:#0b1220;color:#edf3ff}
*{box-sizing:border-box}
body{margin:0 auto;padding:24px;max-width:1200px}
header{display:flex;justify-content:space-between;align-items:center;
gap:20px;flex-wrap:wrap;margin-bottom:24px}
h1{margin:0;font-size:1.75rem}
small,.muted{color:#94a3b8}
button{background:#2563eb;border:0;border-radius:8px;color:white;
padding:10px 18px;cursor:pointer;font-weight:600}
button:disabled{opacity:.5;cursor:wait}
.controls{display:flex;gap:12px;flex-wrap:wrap;margin-bottom:12px}
input,select{background:#0b1220;border:1px solid #475569;color:#edf3ff;
border-radius:8px;padding:10px;min-width:150px}
input{flex:1}
.pill{display:inline-block;border-radius:16px;padding:3px 9px;
background:#334155;font-size:.8rem}
.pill.online,.pill.available{color:#86efac;background:#14532d}
.pill.gateway_on,.pill.gateway_reported{color:#93c5fd;background:#1e3a8a}
.pill.stale,.pill.not_observed{color:#fcd34d;background:#78350f}
.pill.unavailable{color:#fca5a5;background:#7f1d1d}
.controls label{display:flex;align-items:center;gap:7px}
.controls input[type=checkbox]{min-width:0;flex:none}
#devicerows tr{cursor:pointer}
#devicerows tr:hover,#devicerows tr:focus{background:#253651;outline:2px solid #60a5fa}
#details[hidden]{display:none}
.detail-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(210px,1fr));gap:12px}
.detail-grid div{background:#0b1220;padding:12px;border-radius:8px;
overflow-wrap:anywhere}
.detail-grid strong{display:block;font-size:.8rem;color:#94a3b8;margin-bottom:4px}
#detailclose{float:right;background:#334155}
#details{border-color:#60a5fa}
.detail-grid .time-value{overflow-wrap:normal;word-break:normal}
.detail-grid .time-value time{white-space:normal}
.detail-note{color:#94a3b8;font-size:.85rem;margin:8px 0 14px}
.detail-heading{margin:24px 0 12px}
.cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));
gap:14px;margin:22px 0}
.card,section{background:#172235;border:1px solid #304057;
border-radius:12px;padding:20px}
.card strong{display:block;font-size:2rem;margin-top:8px}
section{margin-top:16px;overflow-x:auto}
h2{margin:0 0 15px;font-size:1.1rem}
table{border-collapse:collapse;width:100%;font-size:.9rem}
th,td{text-align:left;padding:10px;border-bottom:1px solid #304057}
th{color:#94a3b8}
.tag{display:inline-block;padding:4px 8px;border-radius:6px;background:#304057}
.error{color:#fca5a5;margin:12px 0}
</style>
</head>
<body>
<header><div><h1>z0_n3t / Network Monitor</h1>
<small>Saved snapshots · Read-only · No active scans</small></div>
<div><button id="refresh">Refresh saved data</button></div></header>
<p id="status" class="muted">Loading saved monitoring data…</p>
<p id="error" class="error" role="alert"></p>
<div class="cards">
<div class="card">Tracked devices<strong id="devices">—</strong></div>
<div class="card">Confirmed online history<strong id="online">—</strong></div>
<div class="card">Monitored hosts<strong id="hosts">—</strong></div>
<div class="card">Real transitions<strong id="events">—</strong></div>
</div>
<section><h2>Inventory states</h2><div id="states"></div></section>
<section><h2>Saved device inventory</h2>
<div class="controls">
<input id="search" type="search" aria-label="Search devices"
placeholder="Search IP, name or MAC">
<label>State <select id="stateFilter">
<option value="">All states</option>
</select></label>
<label>Sort <select id="sort">
<option value="ip">IP address</option>
<option value="name">Device name</option>
<option value="state">State</option>
<option value="mac">MAC address</option>
</select></label>
<label><input type="checkbox" id="unidentifiedOnly"> Unidentified only</label>
</div>
<p id="shown" class="muted" aria-live="polite"></p><table><thead><tr>
<th>IP</th><th>Name</th><th>Identity</th><th>MAC</th><th>State</th>
</tr></thead><tbody id="devicerows"></tbody></table></section>
<section id="details" hidden tabindex="-1" aria-label="Selected device details">
<button id="detailclose" type="button">Close details</button>
<h2 id="detailtitle">Device details</h2>
<p class="muted">Saved data only · no active scans</p>
<p id="detailerror" class="error" role="alert"></p>
<h2 class="detail-heading">Device identity &amp; discovery</h2>
<p class="detail-note">Inventory observations are not live availability tests.</p>
<div class="detail-grid" id="detailfields"></div>
<h2 class="detail-heading">Verified availability checks</h2>
<p class="detail-note">Saved results from manually initiated ICMP probes.</p>
<div id="detailavailability" class="muted"></div>
<h2 class="detail-heading">Recorded real transitions</h2>
<table><thead><tr><th>Time (local)</th><th>From</th><th>To</th>
</tr></thead><tbody id="detailevents"></tbody></table>
</section>
<section><h2>Monitored hosts</h2><table><thead><tr>
<th>Address</th><th>Status</th><th>Last check (local)</th>
</tr></thead><tbody id="hostrows"></tbody></table></section>
<section><h2>Recent real events</h2><table><thead><tr>
<th>Time (UTC)</th><th>Address</th><th>Transition</th>
</tr></thead><tbody id="eventrows"></tbody></table></section>
<script>
const byId=id=>document.getElementById(id);
let savedDevices=[];
let selectedIdentifier='';
function cell(row,value){let td=document.createElement('td');
td.textContent=String(value??'');row.append(td)}
function stateBadge(state){
  const span=document.createElement('span');
  span.className='pill '+String(state||'').toLowerCase();
  span.textContent=state||'UNKNOWN';
  return span;
}
function renderDevices(){
  const query=byId('search').value.trim().toLowerCase();
  const state=byId('stateFilter').value;
  const unknownOnly=byId('unidentifiedOnly').checked;
  const sort=byId('sort').value;
  const key={ip:'ip_address',name:'display_name',state:'state',mac:'mac_address'}[sort];
  const matches=savedDevices.filter(d=>
    (!state||d.state===state)&&
    (!unknownOnly||d.identification_source==='unidentified')&&
    [d.ip_address,d.display_name,d.hostname,d.mac_address,d.state]
      .some(v=>String(v||'').toLowerCase().includes(query)));
  matches.sort((a,b)=>String(a[key]||'').localeCompare(
    String(b[key]||''),undefined,{numeric:true,sensitivity:'base'}));
  const tbody=byId('devicerows');
  tbody.replaceChildren();
  for(const device of matches){
    const tr=document.createElement('tr');
    tr.tabIndex=0;
    tr.setAttribute('role','button');
    tr.setAttribute('aria-label','View details for '+
      (device.display_name||device.hostname||device.mac_address));
    tr.addEventListener('click',()=>openDetails(device));
    tr.addEventListener('keydown',event=>{
      if(event.key==='Enter'||event.key===' '){
        event.preventDefault();openDetails(device);
      }
    });
    cell(tr,device.ip_address||'—');
    cell(tr,device.display_name||device.hostname||'—');
    const identity={
      operator_label:'Your label',observed_hostname:'Observed',
      unidentified:'Unidentified'
    }[device.identification_source]||'Unclassified';
    cell(tr,identity);
    cell(tr,device.mac_address||'—');
    const td=document.createElement('td');
    td.append(stateBadge(device.state));tr.append(td);
    tbody.append(tr);
  }
  if(!matches.length){const tr=document.createElement('tr');
    const td=document.createElement('td');td.colSpan=5;
    td.textContent='No matching devices';tr.append(td);tbody.append(tr)}
  byId('shown').textContent='Showing '+matches.length+' of '+
    savedDevices.length+' devices';
}
function showRows(target,items,columns){
  const parent=byId(target);parent.replaceChildren();
  if(!items.length){let tr=document.createElement('tr');
    cell(tr,'No saved records');parent.append(tr);return}
  for(const item of items){let tr=document.createElement('tr');
    for(const fn of columns)cell(tr,fn(item));parent.append(tr)}
}
function formattedTime(value){
  if(!value)return 'Not recorded';
  const date=new Date(value);
  if(Number.isNaN(date.getTime()))return String(value);
  const local=new Intl.DateTimeFormat(undefined,{
    year:'numeric',month:'short',day:'numeric',
    hour:'numeric',minute:'2-digit',second:'2-digit',timeZoneName:'short'
  }).format(date);
  return local+' (local)';
}
function fieldValue(value){
  return value===null||value===undefined||value===''?
    'Not reported':String(value);
}
function detailField(name,value){
  const item=document.createElement('div');
  const label=document.createElement('strong');
  label.textContent=name;item.append(label);
  const content=document.createElement('span');
  content.textContent=fieldValue(value);
  item.append(content);byId('detailfields').append(item);
}
async function openDetails(device){
  const identifier=device.mac_address||device.ip_address;
  if(!identifier)return;
  selectedIdentifier=identifier;
  byId('details').hidden=false;
  byId('detailtitle').textContent='Device: '+
    (device.display_name||device.hostname||identifier);
  byId('detailfields').replaceChildren();
  byId('detailavailability').textContent='Loading saved detail…';
  byId('detailerror').textContent='';
  byId('detailevents').replaceChildren();
  byId('details').focus();
  try{
    const response=await fetch('/api/network/device?mac='+
      encodeURIComponent(identifier),{cache:'no-store'});
    if(!response.ok)throw Error('Device API returned HTTP '+response.status);
    const data=await response.json();
    if(selectedIdentifier!==identifier)return;
    const d=data.device;
    for(const [name,value] of Object.entries({
      'Display name':d.display_name,'Observed hostname':d.hostname,
      'Identity source':({operator_label:'Operator label',
        observed_hostname:'Observed hostname',
        unidentified:'Unidentified'}[d.identification_source]||'Not reported'),
      'Locally administered MAC':d.locally_administered_mac?'Yes':'No',
      'IP address':d.ip_address,'MAC address':d.mac_address,
      'Inventory state':d.state,'Gateway status':d.gateway_status,
      'Connection type':d.connection_type,
      'Sources':(d.sources||[]).join(', '),
      'First seen':formattedTime(d.first_seen),
      'Last observed':formattedTime(d.last_observed),
      'Last confirmed online':formattedTime(d.last_confirmed_online),
      'Observation count':d.observation_count,
      'Last gateway activity':d.last_activity,
    }))detailField(name,value);
    const a=data.availability;
    byId('detailavailability').textContent=a?
      a.state+' · Last checked: '+formattedTime(a.last_checked)+
      ' · Successful probes: '+a.successes+
      ' · Consecutive failures: '+a.failures:
      'No saved availability monitoring for this device';
    showRows('detailevents',data.events,[
      e=>formattedTime(e.timestamp),e=>e.old_state,e=>e.new_state]);
  }catch(err){
    if(selectedIdentifier===identifier){
      byId('detailerror').textContent=err.message;
      byId('detailavailability').textContent='Unable to load details';
    }
  }
}
byId('detailclose').addEventListener('click',()=>{
  selectedIdentifier='';
  byId('details').hidden=true;
});
async function refresh(){
  byId('refresh').disabled=true;byId('error').textContent='';
  try{
    const response=await fetch('/api/network/dashboard',{cache:'no-store'});
    if(!response.ok)throw Error('Server returned HTTP '+response.status);
    const data=await response.json();
    const devicesResponse=await fetch('/api/network/devices',
      {cache:'no-store'});
    if(!devicesResponse.ok)throw Error('Device API returned HTTP '+
      devicesResponse.status);
    const devices=await devicesResponse.json();
    byId('devices').textContent=data.inventory.total;
    byId('online').textContent=data.inventory.confirmed_online_history;
    byId('hosts').textContent=data.monitoring.total;
    byId('events').textContent=data.events.total;
    const stateText=Object.entries(data.inventory.states)
      .map(([key,count])=>key+': '+count).join('  ·  ');
    byId('states').textContent=stateText||'No saved devices';
    savedDevices=devices;
    const filter=byId('stateFilter');
    const selected=filter.value;
    filter.replaceChildren(new Option('All states',''));
    for(const state of [...new Set(devices.map(d=>d.state))].sort()){
      filter.add(new Option(state,state));
    }
    filter.value=selected;
    renderDevices();
    showRows('hostrows',data.monitoring.hosts,[
      h=>h.address,h=>h.state,h=>formattedTime(h.last_checked)]);
    showRows('eventrows',data.events.recent,[
      e=>formattedTime(e.timestamp),e=>e.address,
      e=>e.old_state+' → '+e.new_state]);
    byId('status').textContent='Snapshot read at '+data.generated_at+
      ' · Refresh only reads saved files';
  }catch(err){byId('error').textContent='Dashboard unavailable: '+err.message}
  finally{byId('refresh').disabled=false}
}
byId('refresh').addEventListener('click',refresh);
for(const name of ['search','stateFilter','sort','unidentifiedOnly']){
  byId(name).addEventListener(name==='search'?'input':'change',renderDevices);
}
refresh();
</script>
</body></html>
"""
