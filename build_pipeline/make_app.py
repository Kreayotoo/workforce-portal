#!/usr/bin/env python3
"""ONE self-contained file (double-click, no server). Nested zone->block sidebar + overview map + 3D viewer.
Individual blocks render from embedded data; zone/city COMBINED views are merged in the browser on demand."""
import json, os, re
SRC='/home/claude/zone5pkg/Amaravati_Twins'
TPL=open('/home/claude/dashboard_template.html').read()
LOGO=open('/home/claude/logo_b64.txt').read().strip()
man=json.load(open(SRC+'/manifest.json'))

def load_net(code):
    h=open(f'{SRC}/blocks/AmaravatiTwin_{code}.html').read()
    return json.loads(re.search(r'const NET\s*=\s*(\{.*?\});', h, re.S).group(1))

BLK={m['code']:load_net(m['code']) for m in man}          # block datasets only
HAS_TRUNK = os.path.exists('trunk_network.json')
if HAS_TRUNK:
    BLK['TRUNK']=json.load(open('trunk_network.json'))   # city-wide transmission overlay
    # normalise: trunk JSON only has 'water' stats and no map georeference — the
    # dashboard template expects all 5 utility stats and a map object (crash otherwise)
    _T=BLK['TRUNK']; _LB={'water':'Trunk Main','sewer':'Sewerage','strom':'Storm Water','reuse':'Reuse Water','power':'Power'}
    _w=_T['stats'].get('water',{})
    for _u in ['water','sewer','strom','reuse','power']:
        if _u not in _T['stats']:
            _T['stats'][_u]={'label':_LB[_u],'count':0,'length_m':0,'avg_dia':0,'max_dia':0,'min_dia':0,
                             'min_inv':_w.get('min_inv',20),'max_inv':_w.get('max_inv',30)}
    if not _T.get('map'):
        from pyproj import Transformer as _Tr
        _t44=_Tr.from_crs(32644,4326,always_xy=True)
        _cE,_cN=_T['meta']['center_E'],_T['meta']['center_N']
        _lon0,_lat0=_t44.transform(_cE,_cN)
        _lonX,_latX=_t44.transform(_cE+1,_cN); _lonN,_latN=_t44.transform(_cE,_cN+1)
        _g=_T.get('geo',{}).get('water',[])
        _lats=[v for s2 in _g for v in (s2[0],s2[2])] or [_lat0]
        _lons=[v for s2 in _g for v in (s2[1],s2[3])] or [_lon0]
        _T['map']={'center':[round(_lat0,6),round(_lon0,6)],
                   'bounds':[[min(_lats),min(_lons)],[max(_lats),max(_lons)]],
                   'lonPerM_x':_lonX-_lon0,'latPerM_x':_latX-_lat0,
                   'lonPerM_n':_lonN-_lon0,'latPerM_n':_latN-_lat0}
    if not _T.get('nodes'): _T['nodes']=[]
HAS_BLDG = os.path.exists('building_viewer.html') and os.path.exists('building_real_draco.glb')
if HAS_BLDG:
    import base64 as _b64
    BLDG_GLB='data:model/gltf-binary;base64,'+_b64.b64encode(open('building_real_draco.glb','rb').read()).decode()
    BVIEW=open('building_viewer.html').read().replace('__LOGO__','data:image/png;base64,'+LOGO).replace('__FLOORS__', open('floors.json').read() if os.path.exists('floors.json') else '[]').replace('__SPACES__', open('spaces.json').read() if os.path.exists('spaces.json') else '[]')   # __GLB__ kept, filled at runtime
    BLDG_LEVEL = (BLK['TRUNK']['frl']['level'] if (HAS_TRUNK and 'TRUNK' in BLK) else 23.0)
def _zkey(z):
    mm=re.match(r'(\d+)(.*)',str(z)); return (int(mm.group(1)),mm.group(2)) if mm else (999,str(z))
zones=sorted(set(m['zone'] for m in man),key=_zkey)
ZC={z:c for z,c in zip(zones,['#5fe0d2','#19C6F0','#FF8A2B','#C44BE0','#5cd68a','#f5c542','#ff6b9d','#9d8cff'])}
ZONEBLOCKS={z:[m['code'] for m in man if m['zone']==z] for z in zones}
MANMAP={m['code']:{'zone':m['zone'],'block':m['block']} for m in man}
T={'pipes':sum(m['pipes'] for m in man),'mh':sum(m['manholes'] for m in man),'km':round(sum(m['length_km'] for m in man),1)}
first=man[0]['code']

# per-zone storm-water summary (REAL capacity from Civil 3D inverts+diameters) for the live weather dashboard
import math as _m
def _manning_q(dmm, S, n=0.014):
    D=(dmm or 300)/1000.0
    if D<=0: return 0.0
    S=max(S, 0.0008)                      # floor for flat/reverse-graded pipes
    A=_m.pi*D*D/4.0; R=D/4.0
    return (1.0/n)*A*(R**(2.0/3.0))*(S**0.5)   # m3/s full-bore
zone_storm={}
for z in zones:
    cnt=0; length=0.0; Es=[]; Ns=[]; caps=[]; slopes=[]; dias=[]
    for m in man:
        if m['zone']!=z: continue
        net=BLK[m['code']]; cE=net['meta']['center_E']; cN=net['meta']['center_N']
        segs=net['networks'].get('strom',[]); dm=net['dims'].get('strom',[])
        for i,s in enumerate(segs):
            Es+=[s[0]+cE,s[3]+cE]; Ns+=[s[1]+cN,s[4]+cN]
            L=_m.hypot(s[3]-s[0], s[4]-s[1]); length+=L; cnt+=1
            D=dm[i][1] if i<len(dm) else 300
            slope=abs(s[2]-s[5])/L if L>0.5 else 0.0015     # invert drop / length = real design gradient
            dias.append(D); slopes.append(slope); caps.append((D,_manning_q(D,slope)))
    area=(max(Es)-min(Es))*(max(Ns)-min(Ns)) if Es else 50000
    maxD=max(dias) if dias else 300
    outfall=sum(q for D,q in caps if D>=0.8*maxD)          # conveyance of the trunk/outfall drains
    if outfall<=0: outfall=max((q for D,q in caps), default=0.1)
    zone_storm[z]={'count':cnt,'length_m':round(length),'area_m2':round(area),
                   'capacity_m3s':round(outfall,3),'max_dia':round(maxD),
                   'avg_slope':round(sum(slopes)/len(slopes),4) if slopes else 0.0015}
NLAT=round(sum(m['lat'] for m in man)/len(man),4); NLON=round(sum(m['lon'] for m in man)/len(man),4)
# per-block DMA (district metered area) stats for the leak-detection dashboard
dma_data=[]
for m in man:
    net=BLK[m['code']]; cE=net['meta']['center_E']; cN=net['meta']['center_N']
    wsegs=net['networks'].get('water',[])
    wlen=sum(_m.hypot(s[3]-s[0],s[4]-s[1]) for s in wsegs)
    Es=[];Ns=[]
    for s in wsegs: Es+=[s[0]+cE,s[3]+cE]; Ns+=[s[1]+cN,s[4]+cN]
    area=(max(Es)-min(Es))*(max(Ns)-min(Ns)) if Es else 100000
    wnodes=sum(1 for n in net['nodes'] if n.get('u')=='water')
    dma_data.append({'code':m['code'],'zone':m['zone'],'block':m['block'],
                     'water_km':round(wlen/1000,2),'area_ha':round(area/10000,1),
                     'nodes':wnodes,'lat':m['lat'],'lon':m['lon']})
HAS_LEAK=os.path.exists('leak_dashboard.html')
if HAS_LEAK:
    LKVIEW=open('leak_dashboard.html').read().replace('__LOGO__','data:image/png;base64,'+LOGO).replace('__DMADATA__',json.dumps(dma_data))
HAS_DECISION=os.path.exists('decision_dashboard.html') and os.path.exists('plots.json') and os.path.exists('incident_net.json')
if HAS_DECISION:
    DVIEW=(open('decision_dashboard.html').read()
           .replace('__LOGO__','data:image/png;base64,'+LOGO)
           .replace('__PLOTS__', open('plots.json').read())
           .replace('__NET__', open('incident_net.json').read())
           .replace('__BLOCKS__', open('blocks_ll.json').read()))   # __LANDUSE__ filled at runtime
HAS_WEATHER=os.path.exists('weather_dashboard.html')
if HAS_WEATHER:
    WVIEW=open('weather_dashboard.html').read().replace('__LOGO__','data:image/png;base64,'+LOGO).replace('__LAT__',str(NLAT)).replace('__LON__',str(NLON)).replace('__ZONESTORM__',json.dumps(zone_storm))
HAS_LANDUSE=os.path.exists('landuse.png') and os.path.exists('landuse_bounds.json')
if HAS_LANDUSE:
    import base64 as _b64lu
    LANDUSE_URL='data:image/png;base64,'+_b64lu.b64encode(open('landuse.png','rb').read()).decode()
    LANDUSE_BOUNDS=json.load(open('landuse_bounds.json'))['bounds']
    LANDUSE_LEGEND=json.load(open('landuse_legend.json')) if os.path.exists('landuse_legend.json') else []
# inject the landuse overlay into the twin template (or blank the tokens)
if HAS_LANDUSE:
    TPL=TPL.replace('__LANDUSE__', LANDUSE_URL).replace('__LANDUSE_BOUNDS__', json.dumps(LANDUSE_BOUNDS))
else:
    TPL=TPL.replace('__LANDUSE__','').replace('__LANDUSE_BOUNDS__','[[0,0],[0,0]]')
if HAS_DECISION:
    DVIEW=(DVIEW.replace('__LANDUSE_BOUNDS__', json.dumps(LANDUSE_BOUNDS) if HAS_LANDUSE else '[[0,0],[0,0]]')
                .replace('__ZONESTORM__', json.dumps(zone_storm)))

def esc(s): return json.dumps(s).replace('</','<\\/')

side=(f'<button class="citybtn" data-code="CITY"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7">'
      '<circle cx="12" cy="12" r="9"/><path d="M3 12h18M12 3c2.5 2.5 3.8 5.6 3.8 9s-1.3 6.5-3.8 9c-2.5-2.5-3.8-5.6-3.8-9S9.5 5.5 12 3Z"/></svg>'
      f'<div class="cbx"><b>Entire City \u2014 all zones</b><span>{len(man)} blocks in one 3D scene</span></div></button>')
if HAS_TRUNK:
    tk=BLK['TRUNK']['stats']['water']
    side+=('<button class="trunkbtn" data-code="TRUNK"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7">'
           '<path d="M4 8h9a3 3 0 0 1 3 3 3 3 0 0 1-3 3H8"/><circle cx="4" cy="8" r="1.7"/><circle cx="20" cy="14" r="1.7"/></svg>'
           f'<div class="cbx"><b>Trunk + Ring Main</b><span>{tk["count"]:,} pipes \u00b7 {tk["length_m"]/1000:.0f} km \u00b7 up to {tk["max_dia"]:,} mm dia</span></div></button>')
if HAS_BLDG:
    side+=('<button class="bldgbtn" data-code="BUILDING"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7">'
           '<path d="M4 21V6l7-3v18M11 21V9l7 3v9M3 21h18M7 8v0M7 11v0M7 14v0M14.5 13v0M14.5 16v0"/></svg>'
           '<div class="cbx"><b>WTP Admin Building</b><span>BIM model \u00b7 Revit \u2192 3D \u00b7 16 levels</span></div></button>')
if HAS_WEATHER:
    side+=('<button class="wxbtn" data-code="WEATHER"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7"><path d="M7 15.5a3.5 3.5 0 0 1 .3-7 5 5 0 0 1 9.5-1A3.2 3.2 0 0 1 18 15.5Z"/><path d="M8 18l-1 2.5M12 18l-1 2.5M16 18l-1 2.5"/></svg>'
           '<div class="cbx"><b>Live Weather &amp; Storm Risk</b><span>Real rainfall \u00b7 simulated storm response</span></div></button>')
OMVIEW=r'''<!DOCTYPE html><html><head><meta charset="utf-8"><style>
:root{--bg:#0a1626;--pn:#0e1f33;--bd:#1d3a57;--ink:#dceafb;--mut:#7fa3c4;--tl:#35b596;--am:#f0b429;--rd:#ff5a6e}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:13px/1.45 "Segoe UI",system-ui,sans-serif}
.top{display:flex;align-items:center;gap:14px;padding:14px 18px;border-bottom:1px solid var(--bd)}
.top h1{font-size:15px;margin:0;letter-spacing:.06em}.tag{font:600 10px monospace;color:#08131f;background:var(--tl);border-radius:5px;padding:2px 7px}
.note{font:11px monospace;color:var(--mut);margin-left:auto}
.tabs{display:flex;gap:6px;padding:10px 18px 0}.tab{background:var(--pn);border:1px solid var(--bd);border-bottom:none;border-radius:8px 8px 0 0;padding:7px 15px;cursor:pointer;color:var(--mut);font-weight:600}
.tab.act{color:var(--ink);border-color:var(--tl)}
.pane{display:none;padding:16px 18px}.pane.act{display:block}
.tiles{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:12px;margin-bottom:16px}
.tile{background:var(--pn);border:1px solid var(--bd);border-radius:10px;padding:12px 14px}
.tile b{display:block;font-size:22px;margin-top:2px}.tile span{font:600 10px monospace;color:var(--mut);letter-spacing:.08em}
.tile.warn b{color:var(--am)}.tile.bad b{color:var(--rd)}.tile.ok b{color:var(--tl)}
select,input,button.bt{background:#0b1a2c;border:1px solid var(--bd);color:var(--ink);border-radius:7px;padding:6px 9px;font:12px inherit}
button.bt{cursor:pointer}button.bt:hover{border-color:var(--tl)}button.bt.pri{background:var(--tl);color:#06121c;font-weight:700;border:none}
.bar{display:flex;gap:8px;flex-wrap:wrap;align-items:center;margin-bottom:12px}
table{width:100%;border-collapse:collapse;font-size:12px}th{font:600 10px monospace;color:var(--mut);text-align:left;letter-spacing:.07em;padding:7px 8px;border-bottom:1px solid var(--bd)}
td{padding:7px 8px;border-bottom:1px solid #14293f}tr:hover td{background:#10233a}
.chip{font:600 10px monospace;border-radius:5px;padding:2px 7px}.c-ok{background:#0e3328;color:#7fe8c6}.c-due{background:#3a2f10;color:#f6cf6b}.c-ov{background:#3d1420;color:#ff8fa0}
.c-open{background:#12314e;color:#8ec8ff}.c-asg{background:#2c2a4e;color:#c0b6ff}.c-prg{background:#3a2f10;color:#f6cf6b}.c-cls{background:#0e3328;color:#7fe8c6}
.mut{color:var(--mut)}.crit-H{color:#ff8fa0;font-weight:700}.crit-M{color:#f6cf6b}.crit-L{color:var(--mut)}
.banner{background:#102a3c;border:1px solid #23516f;border-radius:9px;padding:9px 13px;font:11px monospace;color:#a9cbe4;margin-bottom:14px}
.pgr{display:flex;gap:8px;align-items:center;margin-top:10px;font:11px monospace;color:var(--mut)}
#rep{display:none;background:#fff;color:#111;padding:26px;font:12px/1.5 "Segoe UI",sans-serif}
#rep h2{margin:0 0 2px;font-size:18px}#rep .sub{color:#555;font-size:11px;margin-bottom:14px}
#rep table{width:100%;border-collapse:collapse;margin:8px 0 16px}#rep th,#rep td{border:1px solid #bbb;padding:5px 7px;text-align:left;font-size:11px}
#rep th{background:#eef3f7}#rep .sig{display:flex;gap:40px;margin-top:34px}#rep .sig div{flex:1;border-top:1px solid #333;padding-top:5px;font-size:11px}
@media print{ body>*{display:none!important} #rep{display:block!important} }
</style></head><body>
<div class="top"><h1>O&amp;M \u00b7 MAINTENANCE MANAGEMENT</h1><span class="tag">PHASE 1 \u00b7 LOCAL STORE</span>
<span class="note" id="stamp"></span></div>
<div class="tabs"><div class="tab act" data-p="kpi">KPI Dashboard</div><div class="tab" data-p="ast">Asset Register</div><div class="tab" data-p="pm">PM Schedule</div><div class="tab" data-p="wo">Work Orders</div><div class="tab" data-p="st">Stores</div><div class="tab" data-p="lv">Live Data</div></div>

<div class="pane act" id="p-kpi">
 <div class="banner">Live O&amp;M indicators computed from this browser's work-order &amp; PM store \u00b7 SLB/CPHEEO aligned \u00b7 SLA defaults ASSUMED (P1 24h \u00b7 P2 72h \u00b7 P3 168h)</div>
 <div class="bar"><button class="bt pri" id="kRep">\u2b73 Generate monthly O&amp;M report (print / save as PDF)</button></div>
 <div class="tiles" id="kt"></div>
 <div style="display:grid;grid-template-columns:1fr 1fr;gap:14px">
  <div class="tile"><span>OPEN WORK ORDERS BY UTILITY</span><div id="kbar" style="margin-top:10px"></div></div>
  <div class="tile"><span>PM STATUS</span><div id="kpm" style="margin-top:10px"></div></div>
 </div>
</div>

<div class="pane" id="p-ast">
 <div class="banner">Auto-generated register from the digital-twin geometry \u00b7 asset IDs are system-assigned \u00b7 criticality = diameter class (\u2265600 HIGH \u00b7 \u2265300 MED)</div>
 <div class="bar">Zone <select id="aZone"></select> Block <select id="aBlk"></select> Utility <select id="aUtil"><option value="water">Potable Water</option><option value="sewer">Sewer</option><option value="strom">Storm</option><option value="reuse">Reuse</option><option value="power">Power</option></select>
 <span class="mut" id="aSum"></span></div>
 <table><thead><tr><th>ASSET ID</th><th>SIZE</th><th>LENGTH</th><th>CRITICALITY</th><th></th></tr></thead><tbody id="aBody"></tbody></table>
 <div class="pgr"><button class="bt" id="aPrev">\u25c0</button><span id="aPg"></span><button class="bt" id="aNext">\u25b6</button><span id="aCh"></span></div>
</div>

<div class="pane" id="p-pm">
 <div class="banner">Frequencies per CPHEEO O&amp;M manual defaults \u00b7 commissioning date <b>ASSUMED</b> \u2014 edit: <input type="date" id="commD" style="margin:0 6px"> applies to all schedules \u00b7 completions stored locally</div>
 <div class="bar">Utility <select id="pUtil"><option value="">All</option><option value="water">Water</option><option value="sewer">Sewer</option><option value="strom">Storm</option><option value="reuse">Reuse</option><option value="power">Power</option></select>
 Status <select id="pStat"><option value="">All</option><option>OVERDUE</option><option>DUE SOON</option><option>OK</option></select>
 <button class="bt" id="pCsv">\u2b73 Export CSV</button><span class="mut" id="pSum"></span></div>
 <table><thead><tr><th>TASK</th><th>BLOCK</th><th>FREQ</th><th>LAST DONE</th><th>NEXT DUE</th><th>STATUS</th><th></th></tr></thead><tbody id="pBody"></tbody></table>
</div>

<div class="pane" id="p-lv">
 <div class="banner">Live device telemetry \u00b7 any-brand ingestion (REST \u00b7 MQTT \u00b7 Modbus-TCP \u00b7 OPC-UA) \u00b7 threshold \u2192 alarm \u2192 auto work-order \u00b7 SIM devices are labelled SIMULATED</div>
 <div class="tiles" id="lvT"></div>
 <table><thead><tr><th>DEVICE</th><th>KIND</th><th>UTILITY</th><th>VALUE</th><th>AGE</th><th>STATE</th></tr></thead><tbody id="lvBody"></tbody></table>
 <div style="margin-top:14px"><b style="font:600 10px monospace;color:var(--mut)">RECENT ALARMS</b><div id="lvAl" style="margin-top:6px"></div></div>
</div>
<div class="pane" id="p-st">
 <div class="banner">Warehouse / stores \u00b7 issue materials to work orders via tickets \u00b7 stock shared with the same Phase-1/2 store</div>
 <div class="bar"><input id="sN" placeholder="item name" style="width:180px"><input id="sU" placeholder="unit" style="width:70px"><input id="sQ" type="number" placeholder="qty" style="width:80px"><input id="sM" type="number" placeholder="min level" style="width:90px"><button class="bt pri" id="sAdd">+ Add item</button>
  <span style="width:22px"></span>
  <select id="sWo" style="min-width:150px"></select><select id="sIt"></select><input id="sQt" type="number" placeholder="qty" style="width:70px"><button class="bt" id="sIss">Issue to WO</button>
  <button class="bt" id="sCsv">\u2b73 Export CSV</button></div>
 <table><thead><tr><th>ITEM</th><th>UNIT</th><th>IN STOCK</th><th>MIN</th><th>STATUS</th></tr></thead><tbody id="stBody"></tbody></table>
</div>
<div class="pane" id="p-wo">
 <div class="banner">Corrective + PM work orders \u00b7 stored in this browser (phase-1) \u00b7 raise from any chamber popup in the 3D twin or below</div>
 <div class="bar"><input id="wAsset" placeholder="Asset / location" style="width:170px">
  <select id="wUtil"><option value="water">Water</option><option value="sewer">Sewer</option><option value="strom">Storm</option><option value="reuse">Reuse</option><option value="power">Power</option></select>
  <select id="wBlk"></select>
  <select id="wPri"><option>P1</option><option selected>P2</option><option>P3</option></select>
  <input id="wDesc" placeholder="description" style="flex:1;min-width:160px">
  <button class="bt pri" id="wNew">+ Raise WO</button>
  <button class="bt" id="wCsv">\u2b73 Export CSV</button>
  <label class="bt" style="cursor:pointer">\u2b71 Import complaints CSV<input type="file" id="wImp" accept=".csv" style="display:none"></label>
  <button class="bt" id="wTpl">CSV template</button></div>
 <table><thead><tr><th>WO</th><th>ASSET</th><th>UTIL</th><th>BLOCK</th><th>PRI</th><th>AGE</th><th>ASSIGNEE</th><th>STATUS</th></tr></thead><tbody id="wBody"></tbody></table>
</div>

<script>
const P=(function(){try{return window.parent&&window.parent.MAN?window.parent:null}catch(e){return null}})();
const MAN=P?P.MAN:[], BLK=P?P.BLK:{};
const UL={water:'Water',sewer:'Sewer',strom:'Storm',reuse:'Reuse',power:'Power'};
const LS={get:(k,d)=>{try{return JSON.parse(localStorage.getItem(k))??d}catch(e){return d}},set:(k,v)=>{try{localStorage.setItem(k,JSON.stringify(v))}catch(e){}}};
const OMAPI={base:null,mode:'LOCAL',tok:localStorage.getItem('om_tok')||'',user:localStorage.getItem('om_user')||'',role:localStorage.getItem('om_role')||''};
function omHdr(){const h={'Content-Type':'application/json'};if(OMAPI.tok)h['Authorization']='Bearer '+OMAPI.tok;return h;}
function omLoginUI(base){
 let ov=document.getElementById('omLogin');
 if(!ov){ov=document.createElement('div');ov.id='omLogin';
  ov.style.cssText='position:fixed;inset:0;background:rgba(4,10,18,.88);display:flex;align-items:center;justify-content:center;z-index:9999';
  ov.innerHTML='<div style="background:var(--pn);border:1px solid var(--tl);border-radius:12px;padding:26px 30px;width:300px">'
   +'<div style="font:700 13px monospace;letter-spacing:.08em;color:var(--tl);margin-bottom:4px">SERVER LOGIN</div>'
   +'<div class="mut" style="font-size:11px;margin-bottom:14px">O&M shared store requires sign-in \u00b7 role-based access \u00b7 audited</div>'
   +'<input id="olU" placeholder="username" style="width:100%;margin-bottom:8px">'
   +'<input id="olP" type="password" placeholder="password" style="width:100%;margin-bottom:8px">'
   +'<div id="olE" style="color:var(--rd);font-size:11px;height:14px;margin-bottom:6px"></div>'
   +'<button class="bt pri" id="olGo" style="width:100%">Sign in</button>'
   +'<button class="bt" id="olSkip" style="width:100%;margin-top:8px">Work offline (local store)</button></div>';
  document.body.appendChild(ov);
  document.getElementById('olGo').onclick=async function(){
   try{const r=await fetch(base+'/api/auth/login',{method:'POST',headers:{'Content-Type':'application/json'},
     body:JSON.stringify({username:document.getElementById('olU').value,password:document.getElementById('olP').value})});
    if(!r.ok){document.getElementById('olE').textContent='invalid credentials';return;}
    const d=await r.json();OMAPI.tok=d.token;OMAPI.user=d.name;OMAPI.role=d.role;
    localStorage.setItem('om_tok',d.token);localStorage.setItem('om_user',d.name);localStorage.setItem('om_role',d.role);
    ov.remove();omConnect();
   }catch(e){document.getElementById('olE').textContent='server unreachable';}};
  document.getElementById('olSkip').onclick=function(){ov.remove();
   const tg=document.querySelector('.tag');if(tg)tg.textContent='PHASE 1 \u00b7 LOCAL STORE';refresh();};
 }}
function omLogout(){['om_tok','om_user','om_role'].forEach(k=>localStorage.removeItem(k));
 OMAPI.tok='';OMAPI.user='';OMAPI.role='';OMAPI.mode='LOCAL';OMAPI.base=null;location.reload();}
async function omConnect(){
 for(const b of ['http://127.0.0.1:8000','http://localhost:8000']){
  try{
   const pg=await Promise.race([fetch(b+'/api/om/ping'),new Promise((_,j)=>setTimeout(()=>j('t'),700))]);
   if(!(pg&&pg.ok)) continue;
   const pi=await pg.json();
   const r=await fetch(b+'/api/om/store',{headers:omHdr()});
   if(r.status===401){ omLoginUI(b); return; }
   if(r.ok){const d=await r.json();OMAPI.base=b;OMAPI.mode='SERVER';
    // merge: keep local WOs the server has not seen yet (raised from 3D while offline)
    const loc=LS.get('om_wos',[]), srv=d.wos||[], ids=new Set(srv.map(w=>w.id));
    const merged=loc.filter(w=>!ids.has(w.id)).concat(srv);
    LS.set('om_wos',merged);LS.set('om_pm',d.pm||{});if(d.comm)LS.set('om_comm',d.comm);if(d.stock)LS.set('om_stock',d.stock);
    if(merged.length!==srv.length) omPush();
    break;}}catch(e){}}
 const tg=document.querySelector('.tag');
 if(tg)tg.textContent=OMAPI.mode==='SERVER'?('PHASE 2 \u00b7 SERVER STORE \u00b7 '+(OMAPI.user||'')+' ('+(OMAPI.role||'')+')'):'PHASE 1 \u00b7 LOCAL STORE';
 let lo=document.getElementById('omOut');
 if(OMAPI.mode==='SERVER'&&!lo){lo=document.createElement('button');lo.id='omOut';lo.className='bt';lo.textContent='Logout';
  lo.style.marginLeft='10px';lo.onclick=omLogout;const tp=document.querySelector('.top');if(tp)tp.appendChild(lo);}
 if(OMAPI.role==='Viewer'){window.OMRO=1;}
 document.getElementById('commD').value=comm(); refresh();}
function omPush(){ if(OMAPI.mode!=='SERVER'||!OMAPI.base) return;
 try{ fetch(OMAPI.base+'/api/om/store',{method:'POST',headers:{'Content-Type':'application/json'},
  headers:omHdr(),body:JSON.stringify({wos:LS.get('om_wos',[]),pm:LS.get('om_pm',{}),comm:LS.get('om_comm','2024-06-01'),stock:LS.get('om_stock',[])})})
  .then(function(r){ if(r&&r.status===401){ OMAPI.mode='LOCAL'; omLoginUI(OMAPI.base); } }); }catch(e){} }
function roGuard(){ if(window.OMRO){ alert('Your role is Viewer (read-only). Ask an Admin for write access.'); return true; } return false; }
document.getElementById('stamp').textContent=new Date().toLocaleString();
document.querySelectorAll('.tab').forEach(t=>t.onclick=()=>{document.querySelectorAll('.tab').forEach(x=>x.classList.remove('act'));document.querySelectorAll('.pane').forEach(x=>x.classList.remove('act'));t.classList.add('act');document.getElementById('p-'+t.dataset.p).classList.add('act');refresh();});
/* ---- PM model ---- */
const PMT=[["Valve exercising","water",180],["Chamber / hydrant inspection","water",365],["Leak sounding survey","water",180],
["Manhole inspection","sewer",365],["Sewer jetting / desilting","sewer",365],
["Drain desilting (pre-monsoon)","strom",365],["Reuse chamber inspection","reuse",365],["Duct bank & chamber inspection","power",365]];
function comm(){return LS.get('om_comm','2024-06-01')}
document.getElementById('commD').value=comm();
document.getElementById('commD').onchange=e=>{LS.set('om_comm',e.target.value);omPush();refresh()};
function pmRows(){const done=LS.get('om_pm',{});const out=[];const today=Date.now();
 MAN.forEach(m=>{const has={water:m.pipes>0,sewer:m.pipes>0,strom:true,reuse:m.pipes>0,power:m.pipes>0};
  PMT.forEach(([t,u,f])=>{const id=m.code+'|'+t;const ld=done[id]||comm();
   const due=new Date(new Date(ld).getTime()+f*864e5);const dd=(due-today)/864e5;
   out.push({id,task:t,util:u,code:m.code,freq:f,last:ld,due:due.toISOString().slice(0,10),
    st:dd<0?'OVERDUE':(dd<30?'DUE SOON':'OK'),dd});});});
 return out;}
function markDone(id){ if(roGuard()) return; const d=LS.get('om_pm',{});d[id]=new Date().toISOString().slice(0,10);LS.set('om_pm',d);omPush();refresh();}
/* ---- Live Data ---- */
window.__live=[];
async function drawLive(){
 const tb=document.getElementById('lvBody'), tl=document.getElementById('lvT'), la=document.getElementById('lvAl');
 if(OMAPI.mode!=='SERVER'||!OMAPI.base){
  tb.innerHTML='<tr><td colspan="6" class="mut">start the server and sign in \u2014 live telemetry appears here (see server/INGEST.md to connect any brand of sensor)</td></tr>';
  tl.innerHTML=''; la.innerHTML=''; return; }
 try{
  const lv=await (await fetch(OMAPI.base+'/api/live',{headers:omHdr()})).json();
  window.__live=lv;
  const on=lv.filter(d=>d.state!=='\u2014'&&d.state!=='STALE').length, al=lv.filter(d=>d.state==='ALARM').length;
  tl.innerHTML=tile('DEVICES REGISTERED',lv.length,'')+tile('REPORTING',on,on?'ok':'warn')+tile('ACTIVE ALARMS',al,al?'bad':'ok');
  tb.innerHTML=lv.map(d=>{const age=d.ts?((Date.now()/1000-d.ts)/60):null;
   const cl=d.state==='ALARM'?'c-ov':(d.state==='OK'?'c-ok':'c-due');
   return '<tr><td title="'+d.id+'">'+d.name+'</td><td>'+d.kind+'</td><td>'+(UL[d.utility]||d.utility)+'</td>'+
    '<td><b>'+(d.value==null?'\u2014':d.value)+'</b> '+(d.unit||'')+'</td>'+
    '<td>'+(age==null?'\u2014':(age<1?'now':age.toFixed(0)+' min'))+'</td>'+
    '<td><span class="chip '+cl+'">'+d.state+'</span></td></tr>';}).join('')
    ||'<tr><td colspan="6" class="mut">no devices registered \u2014 POST /api/devices (INGEST.md)</td></tr>';
  const als=await (await fetch(OMAPI.base+'/api/alarms?n=12',{headers:omHdr()})).json();
  la.innerHTML=als.slice().reverse().map(a=>'<div class="mut" style="font-size:11px">'+new Date(a.ts).toLocaleString()+' \u2014 <b>'+a.device+'</b> '+a.msg+'</div>').join('')||'<div class="mut">no alarms yet</div>';
 }catch(e){ tb.innerHTML='<tr><td colspan="6" class="mut">live feed unavailable</td></tr>'; }
}
setInterval(function(){ if(document.getElementById('p-lv').classList.contains('act')) drawLive(); },7000);
/* ---- Stores model ---- */
function stock(){return LS.get('om_stock',[])}
function saveStock(v){LS.set('om_stock',v);omPush();}
document.getElementById('sAdd').onclick=function(){const n=document.getElementById('sN').value.trim();if(!n)return;
 const v=stock();v.push({it:n,u:document.getElementById('sU').value||'no',q:+document.getElementById('sQ').value||0,mn:+document.getElementById('sM').value||0});
 saveStock(v);document.getElementById('sN').value='';refresh();};
document.getElementById('sIss').onclick=function(){const wi=+document.getElementById('sWo').value,ii=+document.getElementById('sIt').value,q=+document.getElementById('sQt').value||0;
 const v=stock(),a=wos();if(!(v[ii])||!(a[wi])||q<=0)return;
 if(v[ii].q<q){alert('insufficient stock ('+v[ii].q+' '+v[ii].u+')');return;}
 v[ii].q-=q;(a[wi].materials=a[wi].materials||[]).push({it:v[ii].it,q:q,ts:Date.now()});
 (a[wi].log=a[wi].log||[]).push({ts:Date.now(),m:'material ticket: '+v[ii].it+' \u00d7 '+q+' '+v[ii].u});
 LS.set('om_wos',a);saveStock(v);refresh();};
document.getElementById('sCsv').onclick=function(){const v=stock();
 dl('Stores_Stock.csv','item,unit,in_stock,min_level,status\n'+v.map(x=>[x.it,x.u,x.q,x.mn,(x.q<=x.mn?'LOW':'OK')].join(',')).join('\n'));};
function drawSt(){const v=stock(),a=wos();
 document.getElementById('stBody').innerHTML=v.map(x=>'<tr><td>'+x.it+'</td><td>'+x.u+'</td><td>'+x.q+'</td><td>'+x.mn+'</td><td><span class="chip '+(x.q<=x.mn?'c-ov':'c-ok')+'">'+(x.q<=x.mn?'LOW':'OK')+'</span></td></tr>').join('')||'<tr><td colspan="5" class="mut">no items yet \u2014 add stores stock above</td></tr>';
 document.getElementById('sWo').innerHTML=a.map((w,i)=>w.status!=='Closed'?'<option value="'+i+'">'+w.id+'</option>':'').join('');
 document.getElementById('sIt').innerHTML=v.map((x,i)=>'<option value="'+i+'">'+x.it+' ('+x.q+' '+x.u+')</option>').join('');}
/* ---- WO model ---- */
function wos(){return LS.get('om_wos',[])}
function saveWos(a){LS.set('om_wos',a); omPush(); try{P&&P.omAddWO&&P.omBadge}catch(e){}}
function ageH(w){return ((w.closed?new Date(w.closed):new Date())-new Date(w.opened))/36e5}
/* ---- KPI pane ---- */
function drawKpi(){const a=wos(),open=a.filter(w=>w.status!=='Closed');
 const cls=a.filter(w=>w.closed);const mttr=cls.length?(cls.reduce((s,w)=>s+ageH(w),0)/cls.length):0;
 const br=open.filter(w=>ageH(w)>w.sla_h).length;
 const pm=pmRows();const ov=pm.filter(r=>r.st==='OVERDUE').length;
 const compl=pm.length?(100*(pm.length-ov)/pm.length):100;
 document.getElementById('kt').innerHTML=
  tile('OPEN WORK ORDERS',open.length,open.length?'warn':'ok')+
  tile('SLA BREACHES',br,br?'bad':'ok')+
  tile('MTTR (hrs)',cls.length?mttr.toFixed(1):'\u2014','')+
  tile('PM TASKS OVERDUE',ov,ov?'bad':'ok')+
  tile('PM COMPLIANCE',compl.toFixed(0)+'%',compl>90?'ok':'warn')+
  tile('ASSETS UNDER MGMT',(MAN.reduce((s,m)=>s+m.pipes+m.mh,0)).toLocaleString(),'')+
  (function(){const lw=stock().filter(x=>x.q<=x.mn).length;return tile('LOW STOCK ITEMS',lw,lw?'warn':'ok');})();
 const by={};open.forEach(w=>by[w.utility]=(by[w.utility]||0)+1);
 const mx=Math.max(1,...Object.values(by));
 document.getElementById('kbar').innerHTML=Object.keys(UL).map(u=>{const v=by[u]||0;
  return '<div style="display:flex;gap:8px;align-items:center;margin:4px 0"><span style="width:52px;font:600 10px monospace;color:var(--mut)">'+UL[u].toUpperCase()+'</span><div style="flex:1;background:#0b1a2c;border-radius:4px;height:12px"><div style="width:'+(v/mx*100)+'%;background:var(--tl);height:12px;border-radius:4px"></div></div><b style="width:26px;text-align:right">'+v+'</b></div>';}).join('');
 const pc={OVERDUE:0,'DUE SOON':0,OK:0};pm.forEach(r=>pc[r.st]++);
 document.getElementById('kpm').innerHTML=['OVERDUE','DUE SOON','OK'].map(k=>{const cl=k==='OK'?'c-ok':(k==='OVERDUE'?'c-ov':'c-due');
  return '<div style="display:flex;justify-content:space-between;margin:6px 0"><span class="chip '+cl+'">'+k+'</span><b>'+pc[k]+'</b></div>';}).join('');
}
function tile(l,v,c){return '<div class="tile '+c+'"><span>'+l+'</span><b>'+v+'</b></div>'}
/* ---- Assets pane ---- */
let aPg=0;const PGN=100;
const zones=[...new Set(MAN.map(m=>m.zone))];
document.getElementById('aZone').innerHTML=zones.map(z=>'<option>'+z+'</option>').join('');
function fillBlks(sel,z){sel.innerHTML=MAN.filter(m=>m.zone===z).map(m=>'<option value="'+m.code+'">'+m.code+'</option>').join('');}
fillBlks(document.getElementById('aBlk'),zones[0]);
document.getElementById('aZone').onchange=e=>{fillBlks(document.getElementById('aBlk'),e.target.value);aPg=0;refresh();};
['aBlk','aUtil'].forEach(id=>document.getElementById(id).onchange=()=>{aPg=0;refresh();});
document.getElementById('aPrev').onclick=()=>{aPg=Math.max(0,aPg-1);drawAssets();};
document.getElementById('aNext').onclick=()=>{aPg++;drawAssets();};
function drawAssets(){const code=document.getElementById('aBlk').value,u=document.getElementById('aUtil').value;
 const net=BLK[code];const tb=document.getElementById('aBody');
 if(!net){tb.innerHTML='<tr><td colspan="5" class="mut">block data unavailable</td></tr>';return;}
 const segs=net.networks[u]||[],dm=net.dims[u]||[];
 const N=segs.length,pgs=Math.max(1,Math.ceil(N/PGN));aPg=Math.min(aPg,pgs-1);
 let h='';for(let i=aPg*PGN;i<Math.min(N,(aPg+1)*PGN);i++){const s=segs[i],d=dm[i]||[0,0,0];
  const L=Math.hypot(s[3]-s[0],s[4]-s[1]);const dia=Math.max(d[1],d[2]);
  const cr=dia>=600?'H':(dia>=300?'M':'L');
  const sz=d[0]===1?d[1]+'\u00d7'+d[2]+' mm':'\u00d8'+d[1]+' mm';
  const aid=code+'-'+u.toUpperCase().slice(0,2)+'-'+String(i+1).padStart(4,'0');
  h+='<tr><td>'+aid+'</td><td>'+sz+'</td><td>'+L.toFixed(1)+' m</td><td class="crit-'+cr+'">'+(cr==='H'?'HIGH':cr==='M'?'MEDIUM':'LOW')+'</td><td><button class="bt" onclick="quickWO(\''+aid+'\',\''+u+'\',\''+code+'\')">Raise WO</button></td></tr>';}
 tb.innerHTML=h||'<tr><td colspan="5" class="mut">no assets in this utility</td></tr>';
 document.getElementById('aPg').textContent=(aPg+1)+' / '+pgs;
 const ch=(net.nodes||[]).filter(n=>n.u===u).length;
 document.getElementById('aCh').textContent='\u00b7 '+ch.toLocaleString()+' chambers in this block/utility';
 document.getElementById('aSum').textContent=N.toLocaleString()+' pipe assets';
}
window.quickWO=function(aid,u,code){addWO({asset:aid,utility:u,block:code,priority:'P2',desc:'raised from asset register',origin:'Asset register'});};
/* ---- PM pane ---- */
function drawPm(){const fu=document.getElementById('pUtil').value,fs=document.getElementById('pStat').value;
 const rows=pmRows().filter(r=>(!fu||r.util===fu)&&(!fs||r.st===fs)).sort((a,b)=>a.dd-b.dd).slice(0,400);
 document.getElementById('pBody').innerHTML=rows.map(r=>{const cl=r.st==='OK'?'c-ok':(r.st==='OVERDUE'?'c-ov':'c-due');
  return '<tr><td>'+r.task+'</td><td>'+r.code+'</td><td>'+r.freq+' d</td><td>'+r.last+'</td><td>'+r.due+'</td><td><span class="chip '+cl+'">'+r.st+'</span></td><td><button class="bt" onclick="markDone(\''+r.id.replace(/'/g,"\\'")+'\')">Mark done</button></td></tr>';}).join('');
 document.getElementById('pSum').textContent=rows.length+' schedules shown (first 400)';
}
['pUtil','pStat'].forEach(id=>document.getElementById(id).onchange=refresh);
window.markDone=markDone;
document.getElementById('pCsv').onclick=()=>{const rows=pmRows();
 dl('PM_Schedule.csv','task,block,utility,freq_days,last_done,next_due,status\n'+rows.map(r=>[r.task,r.code,r.util,r.freq,r.last,r.due,r.st].join(',')).join('\n'));};
/* ---- WO pane ---- */
document.getElementById('wBlk').innerHTML=MAN.map(m=>'<option>'+m.code+'</option>').join('');
function addWO(p){ if(roGuard()) return; const a=wos();
 a.unshift({id:'WO-'+Date.now().toString(36).toUpperCase(),asset:p.asset||'-',utility:p.utility,block:p.block,
  type:p.type||'Corrective',priority:p.priority||'P2',sla_h:p.priority==='P1'?24:(p.priority==='P3'?168:72),
  desc:p.desc||'',assignee:'',status:'Open',opened:new Date().toISOString(),closed:null,
  origin:p.origin||'Manual',log:[{ts:Date.now(),m:'created \u00b7 '+(p.origin||'Manual')}],docs:[],materials:[]});
 saveWos(a);refresh();}
document.getElementById('wNew').onclick=()=>{addWO({asset:document.getElementById('wAsset').value||'-',
 utility:document.getElementById('wUtil').value,block:document.getElementById('wBlk').value,
 priority:document.getElementById('wPri').value,desc:document.getElementById('wDesc').value});
 document.getElementById('wAsset').value='';document.getElementById('wDesc').value='';};
window.setSt=function(i,v){ if(roGuard()){drawWo();return;} const a=wos();a[i].status=v;a[i].closed=(v==='Closed')?new Date().toISOString():null;
 (a[i].log=a[i].log||[]).push({ts:Date.now(),m:'status \u2192 '+v});saveWos(a);refresh();};
function escalateAll(){const a=wos();let ch=0;
 a.forEach(w=>{ if(w.status!=='Closed'&&ageH(w)>w.sla_h&&!w.esc){ w.esc=1;
   const up={'P3':'P2','P2':'P1'}[w.priority];
   if(up)w.priority=up;
   (w.log=w.log||[]).push({ts:Date.now(),m:'auto-escalated \u00b7 SLA breach'+(up?(' \u2192 '+up):'')}); ch=1; } });
 if(ch)saveWos(a);}
window.setAs=function(i,v){const a=wos();a[i].assignee=v;(a[i].log=a[i].log||[]).push({ts:Date.now(),m:'assignee \u2192 '+(v||'\u2014')});saveWos(a);};
window.expW=-1; window.tgW=function(i){window.expW=(window.expW===i?-1:i);drawWo();};
window.addCm=function(i){const el=document.getElementById('cm'+i);const t=(el&&el.value||'').trim();if(!t)return;
 const a=wos();(a[i].log=a[i].log||[]).push({ts:Date.now(),m:'note: '+t});saveWos(a);drawWo();};
window.attD=function(i,inp){const f=inp.files&&inp.files[0];if(!f)return;
 if(f.size>300*1024){alert('max 300 KB per attachment');inp.value='';return;}
 const rd=new FileReader();rd.onload=function(){const a=wos();a[i].docs=a[i].docs||[];
  if(a[i].docs.length>=3){alert('max 3 attachments per WO');return;}
  a[i].docs.push({n:f.name,d:rd.result});(a[i].log=a[i].log||[]).push({ts:Date.now(),m:'attached '+f.name});
  saveWos(a);drawWo();};rd.readAsDataURL(f);};
window.opB=function(b){try{if(P&&P.openView)P.openView(b);}catch(e){}};
function drawWo(){const a=wos();
 document.getElementById('wBody').innerHTML=a.map((w,i)=>{const ag=ageH(w);
  const br=w.status!=='Closed'&&ag>w.sla_h;
  const sc={'Open':'c-open','Assigned':'c-asg','In-progress':'c-prg','Closed':'c-cls'}[w.status];
  let row='<tr><td style="cursor:pointer" onclick="tgW('+i+')">'+(window.expW===i?'\u25be ':'\u25b8 ')+w.id+(br?' <span class="chip c-ov">SLA</span>':'')+(w.esc?' <span class="chip c-due">ESC</span>':'')+'</td><td title="'+(w.desc||'')+'">'+w.asset+'</td><td>'+(UL[w.utility]||w.utility)+'</td><td>'+w.block+'</td><td>'+w.priority+'</td><td>'+ag.toFixed(1)+' h</td>'+
  '<td><input style="width:110px" value="'+(w.assignee||'')+'" onchange="setAs('+i+',this.value)"></td>'+
  '<td><select class="chip '+sc+'" style="border:none" onchange="setSt('+i+',this.value)">'+['Open','Assigned','In-progress','Closed'].map(s=>'<option '+(s===w.status?'selected':'')+'>'+s+'</option>').join('')+'</select></td></tr>';
  if(window.expW===i){
    const lg=(w.log||[]).slice(-8).map(l=>'<div class="mut" style="font-size:11px">'+new Date(l.ts).toLocaleString()+' \u2014 '+l.m+'</div>').join('')||'<div class="mut">no activity yet</div>';
    const dc=(w.docs||[]).map((d2,j)=>'<img src="'+d2.d+'" title="'+d2.n+'" style="height:44px;border:1px solid var(--bd);border-radius:5px;margin-right:6px;cursor:pointer" onclick="(function(){var win=window.open();win.document.write(\'<img src=\\\''+d2.d+'\\\'>\');})()">').join('');
    const mt=(w.materials||[]).map(m2=>'<span class="chip c-open" style="margin-right:6px">'+m2.it+' \u00d7 '+m2.q+'</span>').join('')||'<span class="mut">none</span>';
    row+='<tr><td colspan="8" style="background:#0c1e33">'
      +'<div style="display:flex;gap:22px;flex-wrap:wrap;padding:6px 2px">'
      +'<div style="flex:1;min-width:230px"><b style="font:600 10px monospace;color:var(--mut)">ACTIVITY \u00b7 origin: '+(w.origin||'Manual')+'</b>'+lg
      +'<div style="display:flex;gap:6px;margin-top:6px"><input id="cm'+i+'" placeholder="add note / comment" style="flex:1"><button class="bt" onclick="addCm('+i+')">Add</button></div></div>'
      +'<div style="min-width:210px"><b style="font:600 10px monospace;color:var(--mut)">ATTACHMENTS (max 3 \u00b7 300 KB)</b><div style="margin:6px 0">'+dc+'</div>'
      +'<label class="bt" style="cursor:pointer">+ Attach photo/doc<input type="file" accept="image/*,.pdf" style="display:none" onchange="attD('+i+',this)"></label></div>'
      +'<div style="min-width:190px"><b style="font:600 10px monospace;color:var(--mut)">MATERIALS ISSUED</b><div style="margin-top:6px">'+mt+'</div>'
      +((w.block&&w.block!=='-')?'<button class="bt" style="margin-top:10px" onclick="opB(\''+w.block+'\')">\u2197 Open in 3D twin</button>':'')+'</div>'
      +'</div></td></tr>';
  }
  return row;}).join('')||'<tr><td colspan="8" class="mut">no work orders yet \u2014 raise one above or from any chamber popup in the 3D twin</td></tr>';
}
document.getElementById('wTpl').onclick=()=>dl('Complaint_Template.csv','complaint_id,date,location,utility,description,priority\ncplt-1001,2026-08-01,Z1B_B5 near park,water,No supply since morning,P2\n');
document.getElementById('wImp').onchange=e=>{const f=e.target.files[0];if(!f)return;
 const rd=new FileReader();rd.onload=()=>{try{
  const lines=String(rd.result).split(/\r?\n/).filter(x=>x.trim());
  const hd=lines[0].toLowerCase().split(',').map(x=>x.trim());const ix=n=>hd.indexOf(n);
  const a=wos();let nAdd=0;
  for(let i=1;i<lines.length;i++){const c=lines[i].split(',');
   const u=((ix('utility')>=0&&c[ix('utility')])||'water').trim().toLowerCase();
   const pr=((ix('priority')>=0&&c[ix('priority')])||'P2').trim().toUpperCase();
   const dt=(ix('date')>=0&&c[ix('date')]||'').trim();
   a.unshift({id:'WO-'+(Date.now()+i).toString(36).toUpperCase(),
    asset:((ix('location')>=0&&c[ix('location')])||(ix('complaint_id')>=0&&c[ix('complaint_id')])||'-').trim(),
    utility:['water','sewer','strom','reuse','power'].includes(u)?u:'water', block:'-', type:'Complaint',
    priority:['P1','P2','P3'].includes(pr)?pr:'P2', sla_h:pr==='P1'?24:(pr==='P3'?168:72),
    desc:(((ix('complaint_id')>=0&&c[ix('complaint_id')])||'')+' '+((ix('description')>=0&&c[ix('description')])||'')).trim(),
    assignee:'', status:'Open', opened:(dt?new Date(dt):new Date()).toISOString(), closed:null, origin:'Complaint import', log:[{ts:Date.now(),m:'created \\u00b7 Complaint import'}], docs:[], materials:[]}); nAdd++; }
  saveWos(a);refresh();alert(nAdd+' complaints imported as work orders');
 }catch(err){alert('import failed: '+err.message)} e.target.value='';};
 rd.readAsText(f);};
document.getElementById('wCsv').onclick=()=>{const a=wos();
 dl('Work_Orders.csv','id,asset,utility,block,priority,status,assignee,opened,closed,age_h,desc\n'+a.map(w=>[w.id,w.asset,w.utility,w.block,w.priority,w.status,w.assignee,w.opened,w.closed||'',ageH(w).toFixed(1),(w.desc||'').replace(/,/g,';')].join(',')).join('\n'));};
function dl(name,txt){const b=new Blob([txt],{type:'text/csv'});const u=URL.createObjectURL(b);
 const a=document.createElement('a');a.href=u;a.download=name;a.click();setTimeout(()=>URL.revokeObjectURL(u),500);}
document.getElementById('kRep').onclick=()=>{
 const now=new Date(), mo=now.toLocaleString('en-IN',{month:'long',year:'numeric'});
 const a=wos(), pm=pmRows();
 const m0=new Date(now.getFullYear(),now.getMonth(),1);
 const opened=a.filter(w=>new Date(w.opened)>=m0), closed=a.filter(w=>w.closed&&new Date(w.closed)>=m0);
 const openNow=a.filter(w=>w.status!=='Closed');
 const mttr=closed.length?(closed.reduce((x,w)=>x+ageH(w),0)/closed.length).toFixed(1):'\u2014';
 const byU=u=>({o:opened.filter(w=>w.utility===u).length,c:closed.filter(w=>w.utility===u).length,p:openNow.filter(w=>w.utility===u).length});
 const pmU=u=>{const r=pm.filter(x=>x.util===u);const ov=r.filter(x=>x.st==='OVERDUE').length;return r.length?(100*(r.length-ov)/r.length).toFixed(0)+'%':'\u2014';};
 let rep=document.getElementById('rep'); if(!rep){rep=document.createElement('div');rep.id='rep';document.body.appendChild(rep);}
 rep.innerHTML='<h2>Amaravati Utility Digital Twin \u2014 Monthly O&M Report</h2>'
  +'<div class="sub">Period: '+mo+' \u00b7 Generated: '+now.toLocaleString()+' \u00b7 Store: '+OMAPI.mode+' \u00b7 Kreayotoo Solutions (P) Ltd for APCRDA</div>'
  +'<table><tr><th>Indicator</th><th>Value</th></tr>'
  +'<tr><td>Work orders opened (month)</td><td>'+opened.length+'</td></tr>'
  +'<tr><td>Work orders closed (month)</td><td>'+closed.length+'</td></tr>'
  +'<tr><td>Currently open</td><td>'+openNow.length+'</td></tr>'
  +'<tr><td>MTTR of closed WOs (h)</td><td>'+mttr+'</td></tr>'
  +'<tr><td>PM tasks overdue (today)</td><td>'+pm.filter(x=>x.st==='OVERDUE').length+'</td></tr></table>'
  +'<table><tr><th>Utility</th><th>Opened</th><th>Closed</th><th>Open now</th><th>PM compliance</th></tr>'
  +Object.keys(UL).map(u=>'<tr><td>'+UL[u]+'</td><td>'+byU(u).o+'</td><td>'+byU(u).c+'</td><td>'+byU(u).p+'</td><td>'+pmU(u)+'</td></tr>').join('')+'</table>'
  +'<b>Open work orders (top 12 by age)</b>'
  +'<table><tr><th>WO</th><th>Asset</th><th>Utility</th><th>Priority</th><th>Age h</th><th>Assignee</th></tr>'
  +openNow.slice().sort((x,y)=>ageH(y)-ageH(x)).slice(0,12).map(w=>'<tr><td>'+w.id+'</td><td>'+w.asset+'</td><td>'+(UL[w.utility]||w.utility)+'</td><td>'+w.priority+'</td><td>'+ageH(w).toFixed(1)+'</td><td>'+(w.assignee||'\u2014')+'</td></tr>').join('')+'</table>'
  +'<div style="font-size:10px;color:#555">Data source: O&M '+(OMAPI.mode==='SERVER'?'server':'browser')+' store \u00b7 PM frequencies per CPHEEO O&M manual defaults \u00b7 commissioning date & SLA targets ASSUMED pending client confirmation.</div>'
  +'<div class="sig"><div>Prepared \u2014 O&M Engineer</div><div>Reviewed \u2014 Utility Manager</div><div>Approved \u2014 APCRDA</div></div>';
 window.print();
};
function refresh(){escalateAll();drawKpi();drawAssets();drawPm();drawWo();drawSt();drawLive();}
refresh();
omConnect();
</script></body></html>'''
if HAS_DECISION:
    side+=('<button class="dsbtn" data-code="DECISION"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7"><path d="M12 3a9 9 0 1 0 9 9"/><path d="M12 7v5l3.5 2"/><path d="M16 3l2 2 4-4"/></svg>'
           '<div class="cbx"><b>Decision Support</b><span>Live alerts \u00b7 impact \u00b7 actions</span></div>'
           '<span class="nbadge" id="dsBadge"></span></button>')
if HAS_LEAK:
    side+=('<button class="lkbtn" data-code="LEAK"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7"><path d="M12 2.5c3.5 4 6 7 6 10a6 6 0 0 1-12 0c0-1.2.4-2.5 1.1-3.8"/><path d="M9 14a3 3 0 0 0 3 3"/></svg>'
           '<div class="cbx"><b>DMA Leak Detection</b><span>Night-flow analysis \u00b7 non-revenue water</span></div></button>')
side+=('<button class="ombtn" data-code="OM"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7"><path d="M14.7 6.3a4 4 0 0 0-5.4 5.4L3 18v3h3l6.3-6.3a4 4 0 0 0 5.4-5.4l-2.6 2.6-2.1-2.1 2.7-2.5z"/></svg>'
       '<div class="cbx"><b>O&amp;M \u00b7 Maintenance</b><span>Assets \u00b7 PM schedule \u00b7 work orders</span></div>'
       '<span class="nbadge" id="omBadge"></span></button>')
for z in zones:
    zb=[m for m in man if m['zone']==z]; zp=sum(m['pipes'] for m in zb)
    zbtn=(f'<button class="zview" data-code="ZONE_{z}" title="All {len(zb)} blocks of Zone {z} in one 3D scene">'
          '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M12 2 3 7l9 5 9-5-9-5ZM3 12l9 5 9-5M3 17l9 5 9-5"/></svg></button>')
    side+=(f'<div class="zsec"><div class="zrow"><span class="caret" data-zone="{z}">\u25b8</span>'
           f'<button class="ztitle" data-zone="{z}"><b>ZONE {z}</b>'
           f'<span>{len(zb)} blocks \u00b7 {zp:,} pipes</span></button>{zbtn}</div>'
           f'<div class="zblocks" id="zb-{z}" style="display:none">')
    for m in zb:
        side+=(f'<button class="blk" data-code="{m["code"]}"><div class="bc">{m["zone"]} \u00b7 {m["block"]}</div>'
               f'<div class="bs">{m["pipes"]:,} pipes \u00b7 {m["manholes"]:,} MH \u00b7 {m["length_km"]} km</div></button>')
    side+='</div></div>'

MANJS=json.dumps([{'code':m['code'],'zone':m['zone'],'block':m['block'],'lat':m['lat'],'lon':m['lon'],
                   'pipes':m['pipes'],'mh':m['manholes'],'km':m['length_km']} for m in man])

CSS=open('/dev/stdin').read() if False else '''
:root{--bg:#060f1c;--pan:#0a1a2e;--pan2:#0c2138;--line:#1d3a57;--ink:#eaf2f9;--dim:#9bb1c6;--teal:#5fe0d2;--cy:#19C6F0;--mono:ui-monospace,monospace}
*{box-sizing:border-box}html,body{margin:0;height:100%}
body{background:var(--bg);color:var(--ink);font-family:'Inter',system-ui,Arial,sans-serif;display:flex;flex-direction:column;height:100vh;overflow:hidden}
header{display:flex;align-items:center;gap:16px;padding:11px 18px;border-bottom:1px solid var(--line);background:linear-gradient(180deg,#081b30,#07162a);position:relative;z-index:5}
header::before{content:"";position:absolute;left:0;top:0;width:100%;height:4px;background:linear-gradient(90deg,#19C6F0,#5fe0d2,#19C6F0);opacity:.6}
.logo{height:40px}
.htxt b{font-size:15px;font-weight:800;color:#fff;display:block;text-shadow:0 1px 0 #c4cdd6,0 2px 3px rgba(0,0,0,.5)}
.htxt span{font-size:10.5px;color:var(--teal);letter-spacing:.12em;text-transform:uppercase}
.sum{margin-left:auto;display:flex;gap:8px}
.kpi{background:var(--pan2);border:1px solid var(--line);border-radius:8px;padding:5px 12px;text-align:center;min-width:72px}
.kpi b{font-family:var(--mono);font-size:15px;color:var(--cy);display:block;line-height:1.1}
.kpi span{font-size:8.5px;color:var(--dim);letter-spacing:.08em;text-transform:uppercase}
.wrap{flex:1;display:flex;min-height:0}
.side{width:252px;background:var(--pan);border-right:1px solid var(--line);overflow-y:auto;padding:12px 10px;flex-shrink:0}
.citybtn{display:flex;align-items:center;gap:10px;width:100%;text-align:left;background:linear-gradient(135deg,#0e3348,#0c2138);border:1px solid var(--teal);border-radius:11px;padding:11px 13px;margin-bottom:14px;color:var(--ink);cursor:pointer;transition:.15s}
.citybtn:hover{box-shadow:0 0 0 1px var(--teal) inset;transform:translateY(-1px)}
.citybtn svg{width:26px;height:26px;color:var(--teal);flex-shrink:0}
.trunkbtn{display:flex;align-items:center;gap:10px;width:100%;text-align:left;background:linear-gradient(135deg,#0b3050,#0c2138);border:1px solid #19C6F0;border-radius:11px;padding:11px 13px;margin-bottom:14px;color:var(--ink);cursor:pointer;transition:.15s}
.trunkbtn:hover{box-shadow:0 0 0 1px #19C6F0 inset;transform:translateY(-1px)}
.trunkbtn svg{width:26px;height:26px;color:#19C6F0;flex-shrink:0}
.bldgbtn{display:flex;align-items:center;gap:10px;width:100%;text-align:left;background:linear-gradient(135deg,#3a2f10,#0c2138);border:1px solid #f5c542;border-radius:11px;padding:11px 13px;margin-bottom:14px;color:var(--ink);cursor:pointer;transition:.15s}
.bldgbtn:hover{box-shadow:0 0 0 1px #f5c542 inset;transform:translateY(-1px)}
.bldgbtn svg{width:26px;height:26px;color:#f5c542;flex-shrink:0}
.wxbtn{display:flex;align-items:center;gap:10px;width:100%;text-align:left;background:linear-gradient(135deg,#0b3a2c,#0c2138);border:1px solid #57d98a;border-radius:11px;padding:11px 13px;margin-bottom:14px;color:var(--ink);cursor:pointer;transition:.15s}
.wxbtn:hover{box-shadow:0 0 0 1px #57d98a inset;transform:translateY(-1px)}
.wxbtn svg{width:26px;height:26px;color:#57d98a;flex-shrink:0}
.dsbtn{display:flex;align-items:center;gap:10px;width:100%;text-align:left;background:linear-gradient(135deg,#2b1444,#0c2138);border:1px solid #a98bff;border-radius:11px;padding:11px 13px;margin-bottom:14px;color:var(--ink);cursor:pointer;transition:.15s}
.dsbtn:hover{box-shadow:0 0 0 1px #a98bff inset;transform:translateY(-1px)}
.dsbtn svg{width:26px;height:26px;color:#a98bff;flex-shrink:0}
.dsbtn{position:relative}
.ombtn{display:flex;align-items:center;gap:10px;width:100%;text-align:left;background:linear-gradient(135deg,#0c3a30,#0c2138);border:1px solid #35b596;border-radius:11px;padding:11px 13px;margin-bottom:14px;color:var(--ink);cursor:pointer;transition:.15s;position:relative}
.ombtn:hover{box-shadow:0 0 0 1px #35b596 inset;transform:translateY(-1px)}
.ombtn svg{width:26px;height:26px;color:#35b596;flex-shrink:0}
.nbadge{position:absolute;top:7px;right:9px;background:#ff5d5d;color:#fff;font:700 10px ui-monospace,monospace;border-radius:20px;padding:2px 7px;display:none;box-shadow:0 0 0 3px rgba(255,93,93,.18)}
.nbadge.on{display:block}
@keyframes pulseB{0%,100%{opacity:1}50%{opacity:.45}}
.nbadge.crit{animation:pulseB 1.6s infinite}
.lkbtn{display:flex;align-items:center;gap:10px;width:100%;text-align:left;background:linear-gradient(135deg,#3a1220,#0c2138);border:1px solid #ff5d5d;border-radius:11px;padding:11px 13px;margin-bottom:14px;color:var(--ink);cursor:pointer;transition:.15s}
.lkbtn:hover{box-shadow:0 0 0 1px #ff5d5d inset;transform:translateY(-1px)}
.lkbtn svg{width:26px;height:26px;color:#ff7d7d;flex-shrink:0}
.lu-legend{background:rgba(9,20,34,.94);border:1px solid #24405c;border-radius:10px;padding:0;max-width:210px;font-family:system-ui,Arial,sans-serif;color:#eaf2f9;box-shadow:0 4px 18px rgba(0,0,0,.4)}
.lu-hd{display:flex;align-items:center;gap:8px;padding:8px 11px;cursor:pointer;border-bottom:1px solid #24405c}
.lu-hd b{font-size:11px;letter-spacing:.05em;text-transform:uppercase;color:#5fe0d2;flex:1}
.lu-tg{display:flex;align-items:center;gap:4px;font-size:10px;color:#9bb1c6;cursor:pointer}
.lu-hd #luExp{color:#9bb1c6;font-size:11px}
.lu-body{max-height:280px;overflow-y:auto;padding:8px 11px}
.lu-i{display:flex;align-items:center;gap:7px;font-size:10.5px;color:#cfe0f0;padding:2px 0;line-height:1.25}
.lu-i span{width:13px;height:13px;border-radius:3px;flex-shrink:0;border:1px solid rgba(255,255,255,.15)}
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
.viewer{flex:1;position:relative;min-width:0;background:#6c737b;display:flex;flex-direction:column}
.vbar{display:flex;align-items:center;gap:12px;padding:7px 14px;background:#081b30;border-bottom:1px solid var(--line);flex-shrink:0}
.vbar .vt{font-family:var(--mono);font-size:13px;color:var(--teal);font-weight:700}
.vbar .vhint{margin-left:auto;font-size:11px;color:#7f97ad;font-family:var(--mono)}
.frwrap{flex:1;position:relative}
iframe{width:100%;height:100%;border:0;background:#6c737b}
.loading{position:absolute;inset:0;display:none;align-items:center;justify-content:center;background:#05101d;color:var(--teal);font-family:var(--mono);font-size:13px;z-index:3;flex-direction:column;gap:12px}
.loading.on{display:flex}
.spin{width:34px;height:34px;border:3px solid var(--line);border-top-color:var(--teal);border-radius:50%;animation:sp 1s linear infinite}
@keyframes sp{to{transform:rotate(360deg)}}
.mapcol{width:344px;flex-shrink:0;border-left:1px solid var(--line);background:var(--pan);display:flex;flex-direction:column;transition:width .18s}
.mapcol.collapsed{width:0;border-left:0;overflow:hidden}
.maphead{display:flex;align-items:center;gap:8px;padding:9px 12px;border-bottom:1px solid var(--line);background:#081b30;flex-shrink:0}
.maphead b{font-size:11.5px;letter-spacing:.1em;text-transform:uppercase;color:var(--teal);font-family:var(--mono)}
.maphead span{font-size:10px;color:var(--dim);font-family:var(--mono)}
#map{flex:1;min-height:0}
.mtoggle{position:absolute;top:52px;right:0;z-index:6;background:var(--pan2);border:1px solid var(--line);border-right:0;border-radius:8px 0 0 8px;color:var(--teal);width:26px;height:44px;cursor:pointer;font-size:14px;display:none}
.mapcol.collapsed ~ .mtoggle{display:block}
.leaflet-popup-content-wrapper{background:#0c2138;color:#eaf2f9;border:1px solid #1d3a57}.leaflet-popup-tip{background:#0c2138}
.pop b{font-size:14px}.pop .ps{font-size:11px;color:#9bb1c6;font-family:var(--mono);margin:4px 0 8px}
.pop button{background:#19C6F0;color:#06121f;border:0;border-radius:6px;padding:6px 12px;font-weight:700;cursor:pointer;width:100%}
@media(max-width:760px){.mapcol{position:absolute;right:0;top:0;bottom:0;z-index:20;box-shadow:-8px 0 24px rgba(0,0,0,.5)}.side{width:210px}}
'''

JS='''
const LABEL={water:'Water',sewer:'Sewer',strom:'Storm',reuse:'Reuse',power:'Power'},ORDER=['water','sewer','strom','reuse','power'];
function amax(a){let m=-Infinity;for(let i=0;i<a.length;i++)if(a[i]>m)m=a[i];return isFinite(m)?m:0;}
function amin(a){let m=Infinity;for(let i=0;i<a.length;i++)if(a[i]<m)m=a[i];return isFinite(m)?m:0;}
function mergeNets(codes){
  const nets=codes.map(c=>BLK[c]).filter(Boolean); let Es=[],Ns=[];
  nets.forEach(net=>{const cE=net.meta.center_E,cN=net.meta.center_N;
    ORDER.forEach(u=>(net.networks[u]||[]).forEach(s=>{Es.push(s[0]+cE,s[3]+cE);Ns.push(s[1]+cN,s[4]+cN);}));});
  const CE=Es.reduce((a,b)=>a+b,0)/Es.length,CN=Ns.reduce((a,b)=>a+b,0)/Ns.length;
  const networks={},dims={},geo={};ORDER.forEach(u=>{networks[u]=[];dims[u]=[];geo[u]=[];});
  nets.forEach(net=>{const cE=net.meta.center_E,cN=net.meta.center_N;
    ORDER.forEach(u=>{const segs=net.networks[u]||[],dm=net.dims[u]||[],gg=net.geo[u]||[];
      segs.forEach((s,i)=>{networks[u].push([+(s[0]+cE-CE).toFixed(2),+(s[1]+cN-CN).toFixed(2),s[2],+(s[3]+cE-CE).toFixed(2),+(s[4]+cN-CN).toFixed(2),s[5]]);
        dims[u].push(dm[i]||[0,200,200]);geo[u].push(gg[i]||[0,0,0,0]);});});});
  let nodes=[];
  nets.forEach(net=>{const cE=net.meta.center_E,cN=net.meta.center_N;
    (net.nodes||[]).forEach(n=>{const m=Object.assign({},n);m.x=+(n.x+cE-CE).toFixed(2);m.z=+(n.z+cN-CN).toFixed(2);nodes.push(m);});});
  const stats={};ORDER.forEach(u=>{const segs=networks[u],dias=dims[u].map(d=>d[1]);let len=0;
    segs.forEach(s=>len+=Math.hypot(s[3]-s[0],s[4]-s[1]));
    const invs=segs.map(s=>s[2]).concat(segs.map(s=>s[5]));
    stats[u]={label:LABEL[u],count:segs.length,length_m:+len.toFixed(1),
      avg_dia:dias.length?Math.round(dias.reduce((a,b)=>a+b,0)/dias.length):0,max_dia:Math.round(amax(dias)),min_dia:Math.round(amin(dias)),
      min_inv:+amin(invs).toFixed(2),max_inv:+amax(invs).toFixed(2)};});
  const b0=nets[0].map,c0E=nets[0].meta.center_E,c0N=nets[0].meta.center_N;
  const lat0=b0.center[0]+(CE-c0E)*b0.latPerM_x+(CN-c0N)*b0.latPerM_n;
  const lon0=b0.center[1]+(CE-c0E)*b0.lonPerM_x+(CN-c0N)*b0.lonPerM_n;
  let lats=[],lons=[];ORDER.forEach(u=>geo[u].forEach(g=>{lats.push(g[0],g[2]);lons.push(g[1],g[3]);}));
  const rim=nodes.length?nodes.reduce((a,n)=>a+n.rim,0)/nodes.length:25;
  return {meta:{zone:'',block:'',grid:'44N',center_E:+CE.toFixed(2),center_N:+CN.toFixed(2),aboveground:false,combined:true},
    stats,networks,geo,dims,nodes,nodes_src:'combined multi-block view',nodes_frl:true,
    frl:{level:+rim.toFixed(2),note:'combined view',src:'combined'},
    map:{center:[+lat0.toFixed(6),+lon0.toFixed(6)],bounds:[[amin(lats),amin(lons)],[amax(lats),amax(lons)]],
      lonPerM_x:b0.lonPerM_x,latPerM_x:b0.latPerM_x,lonPerM_n:b0.lonPerM_n,latPerM_n:b0.latPerM_n},road:null};
}
function buildDoc(NET,pill,label){
  let h=TPL.split('__NETDATA__').join(JSON.stringify(NET)).split('__LOGO__').join('data:image/png;base64,'+LOGO);
  const ldl=label==='TRUNK'?'TRUNK MAIN':(label==='CITY'?'ENTIRE CITY':label.split('_').join('\\u00b7').split('ZONE-').join('ZONE '));
  return h.split('ZONE 1B \\u00b7 BLOCK 5 \\u00b7 GRID 44N').join(pill).split('Z1B-B5 (44N)').join(label+' (44N)')
          .split('Digital Twin \\u00b7 Z1B-B5').join('Digital Twin \\u00b7 '+ldl);
}
const dvF=document.createElement('div');
dvF.style.cssText='position:fixed;inset:0;background:#05070d;opacity:0;pointer-events:none;transition:opacity .18s;z-index:99998;';
document.body.appendChild(dvF);
function fadeIn(){ dvF.style.opacity='1'; dvF.style.pointerEvents='auto'; }
function fadeOut(){ setTimeout(()=>{ dvF.style.opacity='0'; dvF.style.pointerEvents='none'; },260); }
const crumbEl=document.createElement('div');
crumbEl.style.cssText='position:absolute;left:14px;top:8px;z-index:60;font:600 11px monospace;letter-spacing:.08em;color:#9fd8ce;';
function updateCrumb(code){
  const parts=[['CITY','AMARAVATI']];
  if(code&&code.indexOf('ZONE_')===0) parts.push([code,'ZONE '+code.slice(5)]);
  else if(code==='TRUNK') parts.push(['TRUNK','TRUNK + RING MAIN']);
  else if(code&&/^([A-Z0-9]+)_B\d+$/i.test(code)){ const m=MANMAP[code];
    if(m){ parts.push(['ZONE_'+m.zone,'ZONE '+m.zone]); parts.push([code,'BLOCK '+m.block]); } }
  else if(code&&code!=='CITY'){ parts.push([code,code]); }
  crumbEl.innerHTML=parts.map((p,i)=>'<span data-c="'+p[0]+'" style="cursor:pointer;opacity:'+(i===parts.length-1?1:.6)+'">'+p[1]+'</span>').join(' <span style="opacity:.4">\u25b8</span> ');
  crumbEl.querySelectorAll('span[data-c]').forEach(el=>el.onclick=()=>openView(el.dataset.c));
  const host=fr&&fr.parentElement; if(host&&crumbEl.parentElement!==host){ host.style.position=host.style.position||'relative'; host.appendChild(crumbEl); }
}
window.addEventListener('message',e=>{ const el=document.getElementById('fr'); if(!el) return;
  if(e.data&&e.data.openBlock){ fadeIn(); openView(e.data.openBlock); return; }
  if(e.data==='twin-fs-on'){ el.dataset.pv=el.getAttribute('style')||'';
    el.style.cssText='position:fixed;top:0;left:0;right:0;bottom:0;width:100vw;height:100vh;z-index:99999;border:none;background:#0a1626;'; }
  else if(e.data==='twin-fs-off'){ el.setAttribute('style', el.dataset.pv||''); } });
const fr=document.getElementById('fr'),vt=document.getElementById('vt'),vhint=document.getElementById('vhint'),ld=document.getElementById('ld');
const fsb=document.getElementById('fsb');
if(fsb) fsb.onclick=()=>{ const el=fr;
  if(document.fullscreenElement){ document.exitFullscreen(); }
  else if(el.requestFullscreen){ el.requestFullscreen(); }
  else if(el.webkitRequestFullscreen){ el.webkitRequestFullscreen(); } };
document.addEventListener('fullscreenchange',()=>{ if(fsb) fsb.textContent=document.fullscreenElement?'\u2715 Exit':'\u26f6 Fullscreen'; });
let loadTimer=null;
let bldgLL=null;   // WTP Admin building location, set by dragging the map marker
function openView(code){
  try{ updateCrumb(code); }catch(e){}
  if(code==='OM'){ document.querySelectorAll('.blk').forEach(x=>x.classList.remove('act'));
    vt.textContent='O&M \\u00b7 MAINTENANCE MANAGEMENT'; vhint.textContent='asset register \\u00b7 CPHEEO PM schedules \\u00b7 work orders \\u00b7 phase-1 local store';
    ld.classList.add('on'); fr.onload=()=>{clearTimeout(loadTimer);ld.classList.remove('on');fadeOut();};
    loadTimer=setTimeout(()=>ld.classList.remove('on'),20000);
    setTimeout(()=>{ fr.srcdoc=OMVIEW; },30); return; }
  if(code==='DECISION'){ document.querySelectorAll('.blk').forEach(x=>x.classList.remove('act'));
    vt.textContent='DECISION SUPPORT \\u00b7 IMPACT SIMULATION'; vhint.textContent='tap the map to place an incident \\u00b7 real GIS buffer + network analysis';
    ld.classList.add('on'); fr.onload=()=>{clearTimeout(loadTimer);ld.classList.remove('on');fadeOut();};
    loadTimer=setTimeout(()=>ld.classList.remove('on'),20000);
    setTimeout(()=>{ fr.srcdoc=DVIEW.split('__LANDUSE__').join(LANDUSE); },30); return; }
  if(code==='LEAK'){ document.querySelectorAll('.blk').forEach(x=>x.classList.remove('act'));
    vt.textContent='DMA LEAK DETECTION \\u00b7 NON-REVENUE WATER'; vhint.textContent='minimum night flow + mass balance on your network';
    ld.classList.add('on'); fr.onload=()=>{clearTimeout(loadTimer);ld.classList.remove('on');fadeOut();};
    loadTimer=setTimeout(()=>ld.classList.remove('on'),15000);
    setTimeout(()=>{ fr.srcdoc=LKVIEW; },30); return; }
  if(code==='WEATHER'){ document.querySelectorAll('.blk').forEach(x=>x.classList.remove('act'));
    vt.textContent='LIVE WEATHER \\u00b7 STORM-WATER RESPONSE'; vhint.textContent='real rainfall (Open-Meteo) \\u00b7 simulated network response';
    ld.classList.add('on'); fr.onload=()=>{clearTimeout(loadTimer);ld.classList.remove('on');fadeOut();};
    loadTimer=setTimeout(()=>ld.classList.remove('on'),15000);
    setTimeout(()=>{ fr.srcdoc=WVIEW; },30); return; }
  if(code==='BUILDING'){ document.querySelectorAll('.blk').forEach(x=>x.classList.remove('act'));
    vt.textContent='WTP ADMIN BUILDING \\u00b7 BIM MODEL'; vhint.textContent='Revit IFC \\u2192 glTF \\u00b7 drag to orbit, pinch/scroll to zoom';
    ld.classList.add('on'); fr.onload=()=>{clearTimeout(loadTimer);ld.classList.remove('on');fadeOut();};
    loadTimer=setTimeout(()=>ld.classList.remove('on'),15000);
    setTimeout(()=>{ fr.srcdoc=BVIEW.split('__GLB__').join(BLDG_GLB); },30); return; }
  let NET,pill,label,combined=false,trunk=false;
  if(code==='CITY'){combined=true;NET=mergeNets(CITYCODES);pill='AMARAVATI \\u00b7 ALL ZONES';label='CITY';
    if(BLDG_GLB){ NET.meta.building={glb:BLDG_GLB, level:BLDG_LEVEL, lat:(bldgLL?bldgLL.lat:null), lon:(bldgLL?bldgLL.lon:null)}; } }
  else if(code==='TRUNK'){combined=true;trunk=true;NET=BLK['TRUNK'];NET.meta.mapNav=true;pill='TRUNK + RING MAIN \\u00b7 TRANSMISSION NETWORK';label='TRUNK';}
  else if(code.indexOf('ZONE_')===0){combined=true;const z=code.slice(5);NET=mergeNets(ZONEBLOCKS[z]);pill='ZONE '+z+' \\u00b7 ALL BLOCKS';label='ZONE-'+z;}
  else {const m=MANMAP[code];if(!m)return;NET=BLK[code];pill='ZONE '+m.zone+' \\u00b7 BLOCK '+m.block;label=code;}
  document.querySelectorAll('.blk').forEach(x=>x.classList.toggle('act',x.dataset.code===code));
  vt.textContent=pill;
  vhint.textContent=trunk?'transmission main \\u00b7 pipes sized by diameter (500\\u20132500 mm)':(combined?'combined view \\u00b7 toggle "Structures" in the panel to add manholes':'');
  ld.classList.add('on');
  fr.onload=()=>{clearTimeout(loadTimer);ld.classList.remove('on');fadeOut();};
  loadTimer=setTimeout(()=>ld.classList.remove('on'),12000);
  setTimeout(()=>{ fr.srcdoc=buildDoc(NET,pill,label); },30);   // let the spinner paint first
}
document.querySelectorAll('.caret,.ztitle').forEach(el=>el.addEventListener('click',()=>{
  const z=el.dataset.zone,box=document.getElementById('zb-'+z),car=document.querySelector('.caret[data-zone="'+z+'"]');
  const open=box.style.display==='none';box.style.display=open?'block':'none';car.classList.toggle('open',open);
}));
document.querySelectorAll('.zview').forEach(b=>b.addEventListener('click',e=>{e.stopPropagation();openView(b.dataset.code);}));
const cb=document.querySelector('.citybtn');if(cb)cb.addEventListener('click',()=>openView('CITY'));
const tb=document.querySelector('.trunkbtn');if(tb)tb.addEventListener('click',()=>openView('TRUNK'));
const bb=document.querySelector('.bldgbtn');if(bb)bb.addEventListener('click',()=>openView('BUILDING'));
const wb=document.querySelector('.wxbtn');if(wb)wb.addEventListener('click',()=>openView('WEATHER'));
const db2=document.querySelector('.dsbtn');if(db2)db2.addEventListener('click',()=>openView('DECISION'));
const ob2=document.querySelector('.ombtn');if(ob2)ob2.addEventListener('click',()=>openView('OM'));
window.omAddWO=function(wo){ try{ const a=JSON.parse(localStorage.getItem('om_wos')||'[]'); a.unshift(wo);
  localStorage.setItem('om_wos',JSON.stringify(a)); }catch(e){} omBadge(); };
function omBadge(){ try{ const a=JSON.parse(localStorage.getItem('om_wos')||'[]');
  const n=a.filter(w=>w.status!=='Closed').length; const b=document.getElementById('omBadge');
  if(b){ b.textContent=n>0?n:''; b.style.display=n>0?'':'none'; } }catch(e){} }
omBadge(); setInterval(omBadge,5000);
// live alert badge on the Decision Support button (real rainfall vs real drain capacity)
async function refreshAlertBadge(){
  const b=document.getElementById('dsBadge'); if(!b) return;
  let live=0, crit=0;
  try{
    const u='https://api.open-meteo.com/v1/forecast?latitude='+NLAT+'&longitude='+NLON+
            '&hourly=precipitation&past_days=2&forecast_days=2&timezone=auto';
    const d=await (await fetch(u)).json();
    const H=d.hourly, now=new Date();
    let i0=H.time.findIndex(t=>new Date(t)>=now); if(i0<1) i0=1;
    let ante=0; for(let i=Math.max(0,i0-48);i<i0;i++) ante+=H.precipitation[i]||0;
    const nxt=[]; for(let i=i0;i<i0+24&&i<H.time.length;i++) nxt.push(H.precipitation[i]||0);
    const p1=Math.max(0,...nxt); let p3=0;
    for(let i=0;i+3<=nxt.length;i++){const m=(nxt[i]+nxt[i+1]+nxt[i+2])/3; if(m>p3)p3=m;}
    const iPk=Math.max(p1,p3), C=Math.min(0.95,0.70+Math.min(ante/60,1)*0.22);
    if(iPk>0.4) Object.keys(ZONESTORM).forEach(z=>{
      const s=ZONESTORM[z], A=Math.max(s.area_m2,50000), Qc=Math.max(0.02,s.capacity_m3s||0.1);
      const u2=Math.min(200, C*iPk*A/3.6e6/Qc*100);
      if(u2>=50){ live++; if(u2>100){ crit++;
        try{ const k2='om_auto_storm_'+z+'_'+new Date().toISOString().slice(0,10);
          if(!localStorage.getItem(k2) && window.omAddWO){ localStorage.setItem(k2,'1');
            window.omAddWO({id:'WO-'+Date.now().toString(36).toUpperCase(), asset:'ZONE '+z+' storm drains',
              utility:'strom', kind:'zone', block:'ZONE_'+z, type:'Auto', priority:'P1', sla_h:24,
              desc:'AUTO \\u00b7 forecast rainfall exceeds drain capacity ('+u2.toFixed(0)+'% utilisation)',
              assignee:'', status:'Open', opened:new Date().toISOString(), closed:null,
              origin:'Auto: storm alert', log:[{ts:Date.now(),m:'auto-created \\u00b7 live rainfall vs Manning capacity'}]});
          } }catch(e){} } }
    });
  }catch(e){}
  setBadge(live, crit, live);               // baseline until the dashboard reports its live count
}
function setBadge(n, crit, live){
  const b=document.getElementById('dsBadge'); if(!b) return;
  if(!n){ b.classList.remove('on'); return; }
  b.textContent=n; b.classList.add('on'); b.classList.toggle('crit', crit>0);
  b.title=(live||0)+' live rainfall alert(s) + demo sensor alerts';
}
// the Decision Support view reports its true, continuously-updating alert count
window.addEventListener('message', e=>{ const d=e.data;
  if(d && d.t==='alertCount') setBadge(d.n, d.crit, d.live); });
refreshAlertBadge(); setInterval(refreshAlertBadge, 10*60*1000);
const lb2=document.querySelector('.lkbtn');if(lb2)lb2.addEventListener('click',()=>openView('LEAK'));
document.querySelectorAll('.blk').forEach(b=>b.addEventListener('click',()=>openView(b.dataset.code)));
// map
const map=L.map('map',{zoomControl:true});
L.esri.basemapLayer('Imagery').addTo(map);L.esri.basemapLayer('ImageryLabels').addTo(map);
map.createPane('landuse'); map.getPane('landuse').style.zIndex=250; map.getPane('landuse').style.pointerEvents='none';
let landuseLayer=null;
if(typeof LANDUSE!=='undefined' && LANDUSE){
  landuseLayer=L.imageOverlay(LANDUSE, LANDUSE_BOUNDS, {pane:'landuse', opacity:0.72, interactive:false}).addTo(map);
  const lc=L.control({position:'bottomright'});
  lc.onAdd=function(){ const d=L.DomUtil.create('div','lu-legend');
    const items=(typeof LANDUSE_LEGEND!=='undefined'?LANDUSE_LEGEND:[]).map(e=>`<div class="lu-i"><span style="background:rgb(${e.color[0]},${e.color[1]},${e.color[2]})"></span>${e.zone}</div>`).join('');
    d.innerHTML='<div class="lu-hd"><b>Landuse zoning</b><label class="lu-tg"><input type="checkbox" id="luTog" checked>show</label><span id="luExp">\\u25be</span></div><div class="lu-body" id="luBody">'+items+'</div>';
    L.DomEvent.disableClickPropagation(d); L.DomEvent.disableScrollPropagation(d); return d; };
  lc.addTo(map);
  setTimeout(()=>{ const t=document.getElementById('luTog'); if(t)t.onchange=e=>{ if(e.target.checked)landuseLayer.addTo(map); else map.removeLayer(landuseLayer); };
    const hd=document.querySelector('.lu-hd'), body=document.getElementById('luBody'), exp=document.getElementById('luExp');
    if(hd)hd.addEventListener('click',ev=>{ if(ev.target.tagName==='INPUT')return; const open=body.style.display!=='none'; body.style.display=open?'none':'block'; if(exp)exp.textContent=open?'\\u25b8':'\\u25be'; }); },120);
}
const pts=[];
MAN.forEach(m=>{const mk=L.circleMarker([m.lat,m.lon],{radius:8,color:'#06121f',weight:1.5,fillColor:ZC[m.zone]||'#19C6F0',fillOpacity:.92}).addTo(map);
  mk.bindPopup('<div class="pop"><b>'+m.zone+' \\u00b7 '+m.block+'</b><div class="ps">'+m.pipes.toLocaleString()+' pipes \\u00b7 '+m.mh.toLocaleString()+' MH</div><button onclick="openView(\\''+m.code+'\\')">Open in viewer \\u2192</button></div>');
  mk.on('click',()=>{mk.openPopup();openView(m.code);});pts.push([m.lat,m.lon]);});
if(pts.length)map.fitBounds(pts,{padding:[40,40]});
if(typeof TRUNKGEO!=='undefined' && TRUNKGEO.length){
  const cv=L.canvas({padding:0.5}), tg=L.layerGroup();
  TRUNKGEO.forEach(s=>{ L.polyline([[s[0],s[1]],[s[2],s[3]]],{color:'#19C6F0',weight:1.6,opacity:0.85,renderer:cv}).addTo(tg); });
  tg.addTo(map);
}
if(typeof BLDG_GLB!=='undefined' && BLDG_GLB && pts.length){
  const clat=pts.reduce((a,p)=>a+p[0],0)/pts.length, clon=pts.reduce((a,p)=>a+p[1],0)/pts.length;
  try{ const sv=localStorage.getItem('wtpBldgLL'); if(sv) bldgLL=JSON.parse(sv); }catch(e){}
  if(!bldgLL) bldgLL=(typeof BLDG_LL_DEFAULT!=='undefined'&&BLDG_LL_DEFAULT)?BLDG_LL_DEFAULT:{lat:clat,lon:clon};
  const bico=L.divIcon({className:'',iconSize:[30,30],iconAnchor:[15,28],html:'<svg width="30" height="30" viewBox="0 0 24 24" fill="#f5c542" stroke="#0c1e33" stroke-width="1"><path d="M12 2 3 8v14h6v-6h6v6h6V8Z"/><rect x="6.5" y="10" width="2" height="2" fill="#0c1e33"/><rect x="11" y="10" width="2" height="2" fill="#0c1e33"/><rect x="15.5" y="10" width="2" height="2" fill="#0c1e33"/></svg>'});
  const bm=L.marker([bldgLL.lat,bldgLL.lon],{icon:bico,zIndexOffset:1000,draggable:true}).addTo(map);
  const pop='<div class="pop"><b>WTP Admin Building</b><div class="ps">Georeferenced (EPSG:32644 \\u2192 WGS84), placed at the network centre. Drag to fine-tune \\u2014 the 3D model in the city view moves with it. Position saved.</div><button onclick="openView(\\'BUILDING\\')">Open 3D model \\u2192</button></div>';
  bm.bindPopup(pop);
  bm.on('dragend',()=>{ const ll=bm.getLatLng(); bldgLL={lat:ll.lat,lon:ll.lng}; try{localStorage.setItem('wtpBldgLL',JSON.stringify(bldgLL));}catch(e){} bm.setPopupContent('<div class="pop"><b>WTP Admin Building</b><div class="ps">Location set \\u2713 &nbsp;'+ll.lat.toFixed(5)+', '+ll.lng.toFixed(5)+'<br>Open the Entire City view to see it here.</div></div>'); bm.openPopup(); });
  try{ map.fitBounds(pts.concat([[bldgLL.lat,bldgLL.lon]]),{padding:[45,45]}); }catch(e){}
}
const mapcol=document.getElementById('mapcol');
document.getElementById('mcollapse').addEventListener('click',()=>mapcol.classList.add('collapsed'));
document.getElementById('mtoggle').addEventListener('click',()=>{mapcol.classList.remove('collapsed');setTimeout(()=>map.invalidateSize(),200);});
(function(){const z='1A',box=document.getElementById('zb-'+z),car=document.querySelector('.caret[data-zone="'+z+'"]');
  if(box){box.style.display='block';if(car)car.classList.add('open');}openView('ZONE_1A');})();
'''

html=('<!doctype html><html lang="en"><head>\n<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">\n'
'<title>Amaravati Utility Digital Twin \u2014 Kreayotoo</title>\n'
'<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"/>\n<style>'+CSS+'</style></head>\n<body>\n<header>\n'
f'  <img class="logo" src="data:image/png;base64,{LOGO}" alt="Kreayotoo">\n'
f'  <div class="htxt"><b>Amaravati Utility Digital Twin</b><span>Capital City \u00b7 {len(man)} Blocks \u00b7 {len(zones)} Zones</span></div>\n'
'  <div class="sum">\n'
f'    <div class="kpi"><b>{len(man)}</b><span>Blocks</span></div>\n'
f'    <div class="kpi"><b>{T["pipes"]:,}</b><span>Pipes</span></div>\n'
f'    <div class="kpi"><b>{T["mh"]:,}</b><span>Manholes</span></div>\n'
f'    <div class="kpi"><b>{T["km"]}</b><span>km</span></div>\n  </div>\n</header>\n<div class="wrap">\n'
f'  <aside class="side">{side}</aside>\n'
'  <section class="viewer"><div class="vbar"><span class="vt" id="vt"></span><span class="vhint" id="vhint"></span></div>\n'
'    <div class="frwrap"><iframe id="fr" allowfullscreen allow=\"fullscreen\" title="twin"></iframe><div class="loading" id="ld"><div class="spin"></div><div>building 3D scene\u2026</div></div></div>\n  </section>\n'
'  <aside class="mapcol" id="mapcol"><div class="maphead"><b>Overview</b><span>'+str(len(man))+' blocks</span>'
'<button id="mcollapse" style="margin-left:auto;background:none;border:0;color:#9bb1c6;cursor:pointer;font-size:15px">\u2192</button></div>\n'
'    <div id="map"></div></aside>\n  <button class="mtoggle" id="mtoggle">\u2039</button>\n</div>\n'
'<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>\n'
'<script src="https://unpkg.com/esri-leaflet@3.0.10/dist/esri-leaflet.js"></script>\n<script>\n'
f'const TPL={esc(TPL)};\nconst LOGO={esc(LOGO)};\nconst BLK={json.dumps(BLK,separators=(",",":"))};\n'
f'const MAN={MANJS};\nconst ZC={json.dumps(ZC)};\nconst ZONEBLOCKS={json.dumps(ZONEBLOCKS)};\nconst MANMAP={json.dumps(MANMAP)};\n'
f'const ALLCODES={json.dumps([m["code"] for m in man])};\nconst CITYCODES={json.dumps([m["code"] for m in man]+(["TRUNK"] if HAS_TRUNK else []))};\nconst FIRST={json.dumps(first)};\n'
+(f'const BLDG_LL_DEFAULT={json.dumps({"lat":json.load(open("bldg_loc.json"))["lat"],"lon":json.load(open("bldg_loc.json"))["lon"]})};\n' if os.path.exists("bldg_loc.json") else 'const BLDG_LL_DEFAULT=null;\n')
+(f'const BVIEW={esc(BVIEW)};\nconst BLDG_GLB={esc(BLDG_GLB)};\nconst BLDG_LEVEL={BLDG_LEVEL};\n' if HAS_BLDG else 'const BVIEW="";\nconst BLDG_GLB="";\nconst BLDG_LEVEL=0;\n')
+(f'const TRUNKGEO={json.dumps(BLK["TRUNK"]["geo"]["water"])};\n' if (HAS_TRUNK and "TRUNK" in BLK) else 'const TRUNKGEO=[];\n')
+(f'const WVIEW={esc(WVIEW)};\n' if HAS_WEATHER else 'const WVIEW="";\n')
+(f'const DVIEW={esc(DVIEW)};\n' if HAS_DECISION else 'const DVIEW="";\n')
+f'const OMVIEW={esc(OMVIEW)};\n'
+(f'const ZONESTORM={json.dumps(zone_storm)};\nconst NLAT={NLAT};\nconst NLON={NLON};\n')
+(f'const LKVIEW={esc(LKVIEW)};\n' if HAS_LEAK else 'const LKVIEW="";\n')
+(f'const LANDUSE={esc(LANDUSE_URL)};\nconst LANDUSE_BOUNDS={json.dumps(LANDUSE_BOUNDS)};\nconst LANDUSE_LEGEND={json.dumps(LANDUSE_LEGEND)};\n' if HAS_LANDUSE else 'const LANDUSE="";\nconst LANDUSE_BOUNDS=[[0,0],[0,0]];\nconst LANDUSE_LEGEND=[];\n')
+JS+'\n</script>\n</body></html>')

out='/mnt/user-data/outputs/Amaravati_Twins_App.html'
open(out,'w').write(html)
print('unified app written:',round(os.path.getsize(out)/1024/1024,1),'MB ·',len(man),'blocks · individual+zone+city all in one file')
