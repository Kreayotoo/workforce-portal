#!/usr/bin/env python3
"""Replace the POWER utility of Z2B_B4 from the revised Civil 3D export (Structures + Pipes sheets)."""
import openpyxl, json, re, sys, numpy as np
from pyproj import Transformer
SRC=sys.argv[1]; OLD=json.load(open('/home/claude/work/Z2B_B4_old.json'))
T=Transformer.from_crs("EPSG:32644","EPSG:4326",always_xy=True)
def f(v):
    try: return float(v)
    except: return None
def mm(v):
    if v is None: return None
    s=str(v).strip().lower(); n=f(re.sub(r'[^0-9.\-]','',s) or '')
    if n is None: return None
    return n*25.4 if s.endswith('in') else n
def meters(v):
    m=mm(v); return None if m is None else m/1000.0
def ang(v):
    if v is None: return 0.0
    s=str(v); m=re.match(r"\s*(-?\d+)°\s*(\d+)'\s*([\d.]+)",s)
    if m: return float(m.group(1))+float(m.group(2))/60+float(m.group(3))/3600
    n=f(s); return n or 0.0
wb=openpyxl.load_workbook(SRC,read_only=True,data_only=True)
def rows_of(ws):
    allrows=list(ws.iter_rows(values_only=True)); hdr=[str(c).strip() if c is not None else '' for c in allrows[0]]
    return allrows[1:], {h:i for i,h in enumerate(hdr)}
def get(r,ix,n): i=ix.get(n); return r[i] if i is not None and i<len(r) else None
cE,cN=OLD['meta']['center_E'],OLD['meta']['center_N']
# ---- pipes ----
rows,ix=rows_of(wb['Pipes']); segs=[]; dims=[]; names=[]
for r in rows:
    if not r or r[0] in (None,''): continue
    se,sn,ee,en=[f(get(r,ix,k)) for k in ('Start Easting','Start Northing','End Easting','End Northing')]
    if None in (se,sn,ee,en): continue
    si=f(get(r,ix,'Start Invert')) or 0.0; ei=f(get(r,ix,'End Invert')) or 0.0
    iw=mm(get(r,ix,'Inner Width')) or 200.0; ih=mm(get(r,ix,'Inner Height')) or iw
    segs.append([se,sn,si,ee,en,ei]); dims.append([1,round(iw,1),round(ih,1)]); names.append(str(r[0]))
arr=np.array(segs)
networks=[[round(s[0]-cE,2),round(s[1]-cN,2),round(s[2],3),round(s[3]-cE,2),round(s[4]-cN,2),round(s[5],3)] for s in segs]
sl,so=T.transform(arr[:,0],arr[:,1]); el,eo=T.transform(arr[:,3],arr[:,4])
geo=[[round(so[i],6),round(sl[i],6),round(eo[i],6),round(el[i],6)] for i in range(len(segs))]
L=float(np.hypot(arr[:,3]-arr[:,0],arr[:,4]-arr[:,1]).sum()); d=np.array([x[1] for x in dims]); invs=np.concatenate([arr[:,2],arr[:,5]])
stats={'label':'Power','count':len(segs),'length_m':round(L,1),'avg_dia':int(d.mean()),'max_dia':int(d.max()),'min_dia':int(d.min()),'min_inv':round(float(invs.min()),2),'max_inv':round(float(invs.max()),2)}
# ---- structures ----
rows,ix=rows_of(wb['Structures']); nodes=[]
for i,r in enumerate(rows):
    if not r or r[0] in (None,''): continue
    E=f(get(r,ix,'Easting')); N=f(get(r,ix,'Northing'))
    if E is None or N is None: continue
    rim=f(get(r,ix,'Rim Elevation')); sump=f(get(r,ix,'Sump Elevation')); r2s=f(get(r,ix,'Rim to Sump Height'))
    if rim is None and sump is not None: rim=sump+2.0
    if rim is None: rim=f(get(r,ix,'Surface Elevation'))
    if rim is None: continue
    if sump is None: sump=rim-(r2s if r2s else 2.0)
    if sump>=rim: sump=rim-0.6
    iw=meters(get(r,ix,'Inner Width')); il=meters(get(r,ix,'Inner Length'))
    shp=str(get(r,ix,'Shape') or '').strip().lower(); circ=shp.startswith('cyl')
    lon,lat=T.transform(E,N); pipes=str(get(r,ix,'Connected Pipes') or '').strip()
    nodes.append({'u':'power','sid':str(r[0]),'desc':str(get(r,ix,'Description') or ''),
        'x':round(E-cE,2),'z':round(N-cN,2),'E':round(E,3),'N':round(N,3),
        'inv':round(sump,2),'rim':round(rim,2),'frl':round(rim,2),
        'dia':round(iw or 2.4,3),'len':round(il,3) if il else 0,
        'coneH':round(meters(get(r,ix,'Cone Height')) or 0,3),'neck':round(meters(get(r,ix,'Frame Length')) or 0.45,3),
        'rot':round(ang(get(r,ix,'Rotation Angle')),2),'shape':'cyl' if circ else 'box','pipes':pipes,
        'deg':max(1,len([p for p in pipes.split(',') if p.strip() and p.strip()!='<None>'])),
        'mh':True,'real':1,'lat':round(lat,6),'lon':round(lon,6)})
# ---- diff vs old ----
oldp=OLD['networks']['power']; oldn=[n for n in OLD['nodes'] if n['u']=='power']
def key(s): return (round(s[0]),round(s[1]),round(s[3]),round(s[4]))
ok={key(s):s for s in oldp}; nk={key(s):s for s in networks}
same=[k for k in nk if k in ok]; inv_changed=sum(1 for k in same if abs(nk[k][2]-ok[k][2])>0.005 or abs(nk[k][5]-ok[k][5])>0.005)
dia_changed=0
odims={key(s):OLD['dims']['power'][i] for i,s in enumerate(oldp)}; ndims={key(s):dims[i] for i,s in enumerate(networks)}
dia_changed=sum(1 for k in same if odims[k][1:]!=ndims[k][1:])
onk={n['sid']:n for n in oldn}; nnk={n['sid']:n for n in nodes}
rim_changed=sum(1 for s in nnk if s in onk and (abs(nnk[s]['rim']-onk[s]['rim'])>0.005 or abs(nnk[s]['inv']-onk[s]['inv'])>0.005))
moved=sum(1 for s in nnk if s in onk and (abs(nnk[s]['x']-onk[s]['x'])>0.05 or abs(nnk[s]['z']-onk[s]['z'])>0.05))
rep={'old':{'pipes':len(oldp),'mh':len(oldn),'km':round(OLD['stats']['power']['length_m']/1000,2),'inv':[OLD['stats']['power']['min_inv'],OLD['stats']['power']['max_inv']]},
     'new':{'pipes':len(networks),'mh':len(nodes),'km':round(L/1000,2),'inv':[stats['min_inv'],stats['max_inv']]},
     'pipes_same_alignment':len(same),'pipes_removed':len([k for k in ok if k not in nk]),'pipes_added':len([k for k in nk if k not in ok]),
     'pipes_invert_changed':inv_changed,'pipes_size_changed':dia_changed,
     'mh_removed':len([s for s in onk if s not in nnk]),'mh_added':len([s for s in nnk if s not in onk]),'mh_level_changed':rim_changed,'mh_moved':moved,
     'frl_surface_in_file':sorted(set(str(get(r,ix,'Reference Surface')) for r in rows if r and r[0]))}
print(json.dumps(rep,indent=1))
# ---- new NET ----
NEW=json.loads(json.dumps(OLD))
NEW['networks']['power']=networks; NEW['dims']['power']=dims; NEW['geo']['power']=geo; NEW['stats']['power']=stats
NEW['nodes']=[n for n in OLD['nodes'] if n['u']!='power']+nodes
NEW['nodes_src']=OLD.get('nodes_src','')+' · power rev 2026-11-04 (ZONE-2B-BLOCK-4_POWER.xlsx)'
json.dump(NEW,open('/home/claude/work/upd/Z2B_B4_new.json','w'),separators=(',',':'))
json.dump(rep,open('/home/claude/work/upd/report.json','w'),indent=1)
