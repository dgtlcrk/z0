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
<section><h2>Saved device inventory</h2><table><thead><tr>
<th>IP</th><th>Name</th><th>MAC</th><th>State</th>
</tr></thead><tbody id="devicerows"></tbody></table></section>
<section><h2>Monitored hosts</h2><table><thead><tr>
<th>Address</th><th>Status</th><th>Last check (UTC)</th>
</tr></thead><tbody id="hostrows"></tbody></table></section>
<section><h2>Recent real events</h2><table><thead><tr>
<th>Time (UTC)</th><th>Address</th><th>Transition</th>
</tr></thead><tbody id="eventrows"></tbody></table></section>
<script>
const byId=id=>document.getElementById(id);
function cell(row,value){let td=document.createElement('td');
td.textContent=String(value??'');row.append(td)}
function showRows(target,items,columns){
  const parent=byId(target);parent.replaceChildren();
  if(!items.length){let tr=document.createElement('tr');
    cell(tr,'No saved records');parent.append(tr);return}
  for(const item of items){let tr=document.createElement('tr');
    for(const fn of columns)cell(tr,fn(item));parent.append(tr)}
}
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
    showRows('devicerows',devices,[
      d=>d.ip_address,d=>d.hostname,d=>d.mac_address,d=>d.state]);
    showRows('hostrows',data.monitoring.hosts,[
      h=>h.address,h=>h.state,h=>h.last_checked||'—']);
    showRows('eventrows',data.events.recent,[
      e=>e.timestamp,e=>e.address,e=>e.old_state+' → '+e.new_state]);
    byId('status').textContent='Snapshot read at '+data.generated_at+
      ' · Refresh only reads saved files';
  }catch(err){byId('error').textContent='Dashboard unavailable: '+err.message}
  finally{byId('refresh').disabled=false}
}
byId('refresh').addEventListener('click',refresh);
refresh();
</script>
</body></html>
"""
