#!/usr/bin/env python3
"""Deployable web app: ONE page = zone->block sidebar + 3D twin (center) + overview map (right), all visible together."""
import json, os, shutil, re
SRC='/home/claude/zone5pkg/Amaravati_Twins'
APP='/home/claude/webapp/kreayotoo-amaravati-twins'
LOGO=open('/home/claude/logo_b64.txt').read().strip()
man=json.load(open(SRC+'/manifest.json'))
comb=json.load(open(SRC+'/combined.json'))
combByZone={c['zone']:c for c in comb if c['kind']=='zone'}
city=next((c for c in comb if c['kind']=='city'),None)

if os.path.exists(APP): shutil.rmtree(APP)
os.makedirs(APP+'/blocks')
for f in os.listdir(SRC+'/blocks'):
    if f.endswith('.html'): shutil.copy(SRC+'/blocks/'+f, APP+'/blocks/'+f)
shutil.copy(SRC+'/manifest.json', APP+'/manifest.json'); shutil.copy(SRC+'/combined.json', APP+'/combined.json')

def _zkey(z):
    m=re.match(r'(\d+)(.*)',str(z)); return (int(m.group(1)),m.group(2)) if m else (999,str(z))
zones=sorted(set(m['zone'] for m in man),key=_zkey)
ZC={z:c for z,c in zip(zones,['#5fe0d2','#19C6F0','#FF8A2B','#C44BE0','#5cd68a','#f5c542','#ff6b9d','#9d8cff'])}
T={'pipes':sum(m['pipes'] for m in man),'mh':sum(m['manholes'] for m in man),'km':round(sum(m['length_km'] for m in man),1)}
FILES={m['code']:'blocks/'+os.path.basename(m['file']) for m in man}
TITLES={m['code']:f"ZONE {m['zone']} \u00b7 BLOCK {m['block']}" for m in man}
for c in comb:
    FILES[c['code']]='blocks/'+os.path.basename(c['file'])
    TITLES[c['code']]=('AMARAVATI \u00b7 ALL ZONES' if c['kind']=='city' else f"ZONE {c['zone']} \u00b7 ALL BLOCKS")
HAS_TRUNK=os.path.exists(SRC+'/blocks/AmaravatiTwin_TRUNK.html')
if HAS_TRUNK:
    FILES['TRUNK']='blocks/AmaravatiTwin_TRUNK.html'; TITLES['TRUNK']='TRUNK MAIN \u00b7 TRANSMISSION NETWORK'
    tk=json.load(open('/home/claude/trunk_network.json'))['stats']['water']
first=man[0]['code']

side=''
if city:
    side+=('<button class="citybtn" data-code="CITY"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7">'
           '<circle cx="12" cy="12" r="9"/><path d="M3 12h18M12 3c2.5 2.5 3.8 5.6 3.8 9s-1.3 6.5-3.8 9c-2.5-2.5-3.8-5.6-3.8-9S9.5 5.5 12 3Z"/></svg>'
           f'<div class="cbx"><b>Entire City \u2014 all zones</b><span>{city["blocks"]} blocks in one 3D scene</span></div></button>')
if HAS_TRUNK:
    side+=('<button class="trunkbtn" data-code="TRUNK"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7">'
           '<path d="M4 8h9a3 3 0 0 1 3 3 3 3 0 0 1-3 3H8"/><circle cx="4" cy="8" r="1.7"/><circle cx="20" cy="14" r="1.7"/></svg>'
           f'<div class="cbx"><b>Trunk Main \u2014 transmission</b><span>{tk["count"]:,} pipes \u00b7 {tk["length_m"]/1000:.0f} km \u00b7 up to {tk["max_dia"]:,} mm dia</span></div></button>')
for z in zones:
    zb=[m for m in man if m['zone']==z]; zp=sum(m['pipes'] for m in zb); zc=combByZone.get(z)
    zbtn=(f'<button class="zview" data-code="ZONE_{z}" title="All {len(zb)} blocks of Zone {z} in one 3D scene">'
          '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M12 2 3 7l9 5 9-5-9-5ZM3 12l9 5 9-5M3 17l9 5 9-5"/></svg></button>') if zc else ''
    side+=(f'<div class="zsec"><div class="zrow"><span class="caret" data-zone="{z}">\u25b8</span>'
           f'<button class="ztitle" data-zone="{z}"><b><span class="zdot" style="background:{ZC[z]}"></span>ZONE {z}</b>'
           f'<span>{len(zb)} blocks \u00b7 {zp:,} pipes</span></button>{zbtn}</div>'
           f'<div class="zblocks" id="zb-{z}" style="display:none">')
    for m in zb:
        side+=(f'<button class="blk" data-code="{m["code"]}"><div class="bc">{m["zone"]} \u00b7 {m["block"]}</div>'
               f'<div class="bs">{m["pipes"]:,} pipes \u00b7 {m["manholes"]:,} MH \u00b7 {m["length_km"]} km</div></button>')
    side+='</div></div>'

MANJS=json.dumps([{'code':m['code'],'zone':m['zone'],'block':m['block'],'lat':m['lat'],'lon':m['lon'],
                   'pipes':m['pipes'],'mh':m['manholes'],'km':m['length_km']} for m in man])

CSS='''
:root{--bg:#060f1c;--pan:#0a1a2e;--pan2:#0c2138;--line:#1d3a57;--ink:#eaf2f9;--dim:#9bb1c6;--teal:#5fe0d2;--cy:#19C6F0;--mono:ui-monospace,monospace}
*{box-sizing:border-box}html,body{margin:0;height:100%}
body{background:var(--bg);color:var(--ink);font-family:'Inter',system-ui,Arial,sans-serif;display:flex;flex-direction:column;height:100vh;overflow:hidden}
header{display:flex;align-items:center;gap:18px;padding:11px 20px;border-bottom:1px solid var(--line);background:linear-gradient(180deg,#081b30,#07162a);position:relative;z-index:5}
header::before{content:"";position:absolute;left:0;top:0;width:100%;height:4px;background:linear-gradient(90deg,#19C6F0,#5fe0d2,#19C6F0);opacity:.6}
.logo{height:42px}
.htxt b{font-size:16px;font-weight:800;color:#fff;display:block;text-shadow:0 1px 0 #c4cdd6,0 2px 3px rgba(0,0,0,.5)}
.htxt span{font-size:11px;color:var(--teal);letter-spacing:.13em;text-transform:uppercase}
.sum{margin-left:auto;display:flex;gap:10px}
.kpi{background:var(--pan2);border:1px solid var(--line);border-radius:8px;padding:6px 13px;text-align:center;min-width:78px}
.kpi b{font-family:var(--mono);font-size:16px;color:var(--cy);display:block;line-height:1.1}
.kpi span{font-size:9px;color:var(--dim);letter-spacing:.1em;text-transform:uppercase}
.wrap{flex:1;display:flex;min-height:0}
.side{width:256px;background:var(--pan);border-right:1px solid var(--line);overflow-y:auto;padding:12px 10px;flex-shrink:0}
.citybtn{display:flex;align-items:center;gap:10px;width:100%;text-align:left;background:linear-gradient(135deg,#0e3348,#0c2138);border:1px solid var(--teal);border-radius:11px;padding:11px 13px;margin-bottom:14px;color:var(--ink);cursor:pointer;transition:.15s}
.citybtn:hover{box-shadow:0 0 0 1px var(--teal) inset;transform:translateY(-1px)}
.citybtn svg{width:26px;height:26px;color:var(--teal);flex-shrink:0}
.trunkbtn{display:flex;align-items:center;gap:10px;width:100%;text-align:left;background:linear-gradient(135deg,#0b3050,#0c2138);border:1px solid #19C6F0;border-radius:11px;padding:11px 13px;margin-bottom:14px;color:var(--ink);cursor:pointer;transition:.15s}
.trunkbtn:hover{box-shadow:0 0 0 1px #19C6F0 inset;transform:translateY(-1px)}
.trunkbtn svg{width:26px;height:26px;color:#19C6F0;flex-shrink:0}
.cbx b{font-size:13px;font-weight:800;display:block}.cbx span{font-size:10px;color:var(--dim);font-family:var(--mono)}
.zsec{margin-bottom:5px}.zrow{display:flex;align-items:center;gap:4px}
.caret{cursor:pointer;color:var(--dim);font-size:11px;width:16px;text-align:center;transition:transform .15s;user-select:none;flex-shrink:0}
.caret.open{transform:rotate(90deg);color:var(--teal)}
.ztitle{flex:1;text-align:left;background:var(--pan2);border:1px solid var(--line);border-radius:9px;padding:9px 12px;color:var(--ink);cursor:pointer;transition:.15s}
.ztitle:hover{border-color:var(--cy)}
.ztitle b{font-size:13px;font-weight:700;display:flex;align-items:center;gap:7px}
.zdot{width:9px;height:9px;border-radius:50%;display:inline-block}
.ztitle span{font-size:10px;color:var(--dim);font-family:var(--mono);margin-top:2px;display:block;padding-left:16px}
.zview{background:var(--pan2);border:1px solid var(--line);border-radius:9px;padding:8px;color:var(--teal);cursor:pointer;flex-shrink:0;transition:.15s}
.zview:hover{border-color:var(--teal);background:#0e2c44}.zview svg{width:17px;height:17px;display:block}
.zblocks{padding:6px 0 6px 16px}
.blk{display:block;width:100%;text-align:left;background:var(--pan2);border:1px solid var(--line);border-radius:9px;padding:9px 12px;margin-bottom:6px;color:var(--ink);cursor:pointer;transition:.15s}
.blk:hover{border-color:var(--cy);transform:translateX(2px)}
.blk.act{border-color:var(--teal);background:#0e2c44;box-shadow:0 0 0 1px var(--teal) inset}
.bc{font-weight:700;font-size:13px}.bs{font-size:10px;color:var(--dim);margin-top:2px;font-family:var(--mono)}
/* center = the twin */
.viewer{flex:1;position:relative;min-width:0;background:#6c737b;display:flex;flex-direction:column}
.vbar{display:flex;align-items:center;gap:12px;padding:7px 14px;background:#081b30;border-bottom:1px solid var(--line);flex-shrink:0}
.vbar .vt{font-family:var(--mono);font-size:13px;color:var(--teal);font-weight:700}
.vbar .vhint{margin-left:auto;font-size:11px;color:#7f97ad;font-family:var(--mono)}
iframe{flex:1;width:100%;border:0;background:#6c737b}
/* right = overview map, always visible, collapsible */
.mapcol{width:360px;flex-shrink:0;border-left:1px solid var(--line);background:var(--pan);display:flex;flex-direction:column;transition:width .18s}
.mapcol.collapsed{width:0;border-left:0;overflow:hidden}
.maphead{display:flex;align-items:center;gap:8px;padding:9px 12px;border-bottom:1px solid var(--line);background:#081b30;flex-shrink:0}
.maphead b{font-size:12px;letter-spacing:.12em;text-transform:uppercase;color:var(--teal);font-family:var(--mono)}
.maphead span{font-size:10.5px;color:var(--dim);font-family:var(--mono)}
#map{flex:1;min-height:0}
.mtoggle{position:absolute;top:50px;right:0;z-index:6;background:var(--pan2);border:1px solid var(--line);border-right:0;border-radius:8px 0 0 8px;color:var(--teal);width:26px;height:44px;cursor:pointer;font-size:14px;display:none}
.mapcol.collapsed ~ .mtoggle{display:block}
.leaflet-popup-content-wrapper{background:#0c2138;color:#eaf2f9;border:1px solid #1d3a57}.leaflet-popup-tip{background:#0c2138}
.pop b{font-size:14px}.pop .ps{font-size:11px;color:#9bb1c6;font-family:var(--mono);margin:4px 0 8px}
.pop button{background:#19C6F0;color:#06121f;border:0;border-radius:6px;padding:6px 12px;font-weight:700;cursor:pointer;width:100%}
'''

JS='''
const map=L.map('map',{zoomControl:true});
L.esri.basemapLayer('Imagery').addTo(map); L.esri.basemapLayer('ImageryLabels').addTo(map);
const pts=[];
MAN.forEach(m=>{
  const mk=L.circleMarker([m.lat,m.lon],{radius:8,color:'#06121f',weight:1.5,fillColor:ZC[m.zone]||'#19C6F0',fillOpacity:.92}).addTo(map);
  mk.bindPopup(`<div class="pop"><b>${m.zone} \u00b7 ${m.block}</b><div class="ps">${m.pipes.toLocaleString()} pipes \u00b7 ${m.mh.toLocaleString()} MH \u00b7 ${m.km} km</div><button onclick="openView('${m.code}')">Open in viewer \u2192</button></div>`);
  mk.on('click',()=>{mk.openPopup(); openView(m.code);}); pts.push([m.lat,m.lon]);
});
if(pts.length) map.fitBounds(pts,{padding:[40,40]});
const fr=document.getElementById('fr'),vt=document.getElementById('vt'),vhint=document.getElementById('vhint');
function openView(code){
  const file=FILES[code]; if(!file) return;
  document.querySelectorAll('.blk').forEach(x=>x.classList.toggle('act',x.dataset.code===code));
  vt.textContent=TITLES[code]||code;
  vhint.textContent=(code.indexOf('ZONE_')===0||code==='CITY')?'combined view \u00b7 toggle "Structures" in the panel to add manholes':'';
  fr.src=file;
}
// sidebar wiring
document.querySelectorAll('.caret,.ztitle').forEach(el=>el.addEventListener('click',()=>{
  const z=el.dataset.zone,box=document.getElementById('zb-'+z),car=document.querySelector('.caret[data-zone="'+z+'"]');
  const open=box.style.display==='none'; box.style.display=open?'block':'none'; car.classList.toggle('open',open);
}));
document.querySelectorAll('.zview').forEach(b=>b.addEventListener('click',e=>{e.stopPropagation(); openView(b.dataset.code);}));
const cb=document.querySelector('.citybtn'); if(cb) cb.addEventListener('click',()=>openView('CITY'));
document.querySelector('.trunkbtn') && document.querySelector('.trunkbtn').addEventListener('click',()=>openView('TRUNK'));
document.querySelectorAll('.blk').forEach(b=>b.addEventListener('click',()=>openView(b.dataset.code)));
// map collapse
const mapcol=document.getElementById('mapcol');
document.getElementById('mcollapse').addEventListener('click',()=>{mapcol.classList.add('collapsed');});
document.getElementById('mtoggle').addEventListener('click',()=>{mapcol.classList.remove('collapsed'); setTimeout(()=>map.invalidateSize(),200);});
// open first block + expand its zone so both twin and map show on load
(function(){ const c=FIRST; const z=(MAN.find(m=>m.code===c)||{}).zone;
  const box=document.getElementById('zb-'+z),car=document.querySelector('.caret[data-zone="'+z+'"]');
  if(box){box.style.display='block'; car.classList.add('open');}
  openView(c); })();
'''

html=('<!doctype html><html lang="en"><head>\n<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">\n'
'<title>Amaravati Utility Digital Twin \u2014 Kreayotoo</title>\n'
'<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"/>\n'
'<style>'+CSS+'</style></head>\n<body>\n<header>\n'
f'  <img class="logo" src="data:image/png;base64,{LOGO}" alt="Kreayotoo">\n'
f'  <div class="htxt"><b>Amaravati Utility Digital Twin</b><span>Capital City \u00b7 {len(man)} Blocks \u00b7 {len(zones)} Zones</span></div>\n'
'  <div class="sum">\n'
f'    <div class="kpi"><b>{len(man)}</b><span>Blocks</span></div>\n'
f'    <div class="kpi"><b>{T["pipes"]:,}</b><span>Pipes</span></div>\n'
f'    <div class="kpi"><b>{T["mh"]:,}</b><span>Manholes</span></div>\n'
f'    <div class="kpi"><b>{T["km"]}</b><span>km Network</span></div>\n  </div>\n</header>\n'
'<div class="wrap">\n'
f'  <aside class="side">{side}</aside>\n'
'  <section class="viewer">\n'
'    <div class="vbar"><span class="vt" id="vt"></span><span class="vhint" id="vhint"></span></div>\n'
'    <iframe id="fr" title="twin"></iframe>\n  </section>\n'
'  <aside class="mapcol" id="mapcol">\n'
f'    <div class="maphead"><b>Overview</b><span>{len(man)} blocks</span><button id="mcollapse" style="margin-left:auto;background:none;border:0;color:#9bb1c6;cursor:pointer;font-size:15px">\u2192</button></div>\n'
'    <div id="map"></div>\n  </aside>\n'
'  <button class="mtoggle" id="mtoggle">\u2039</button>\n'
'</div>\n'
'<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>\n'
'<script src="https://unpkg.com/esri-leaflet@3.0.10/dist/esri-leaflet.js"></script>\n'
'<script>\n'
f'const MAN={MANJS}, ZC={json.dumps(ZC)}, FILES={json.dumps(FILES)}, TITLES={json.dumps(TITLES)}, FIRST={json.dumps(first)};\n'
+JS+'\n</script>\n</body></html>')

open(APP+'/index.html','w').write(html)
open(APP+'/vercel.json','w').write(json.dumps({"cleanUrls":True,"trailingSlash":False},indent=2))
print('web app rebuilt (one-page: sidebar + twin + map) \u00b7', len(man),'blocks +', len(comb),'combined \u00b7 index', os.path.getsize(APP+'/index.html')//1024,'KB')
