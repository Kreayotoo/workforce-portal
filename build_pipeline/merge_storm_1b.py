#!/usr/bin/env python3
"""Merge the new full storm dataset (Z1B_B5.xlsx: 517 pipes + 518 MH)
into the existing 1B_B5 block, replacing the old incomplete storm data (161 pipes).
Keeps the existing coordinate centre so all other utilities stay valid."""
import openpyxl, json, re, math, os, shutil
import numpy as np
from pyproj import Transformer

SRC_X = '/mnt/user-data/uploads/Z1B_B5.xlsx'
CODE  = '1B_B5'
JPATH = 'restore/Amaravati_DigitalTwin_FullPackage/datasets/data_json/Z1B_B5_network.json'
HPATH = f'zone5pkg/Amaravati_Twins/blocks/AmaravatiTwin_{CODE}.html'
T = Transformer.from_crs("EPSG:32644","EPSG:4326",always_xy=True)

# ---- helpers (mirror build_block.py exactly) ----
def f(v):
    if v is None: return None
    s=str(v).strip().replace(',','')
    if s in ('','<None>'): return None
    m=re.match(r'^(-?\d+\.?\d*)',s)
    return float(m.group(1)) if m else None
def mm(v):
    if v is None: return None
    s=str(v).strip().replace(',','')
    if s in ('','<None>'): return None
    if s.endswith('mm'): return f(s[:-2])
    if s.endswith('in'): return f(s[:-2])*25.4
    return f(s)
def meters(v):
    x=mm(v); return None if x is None else x/1000.0
def ang(v):
    if not v: return 0.0
    m=re.match(r'^(-?\d+)\D+(\d+)\D+([\d.]+)',str(v))
    if m: return float(m.group(1))+float(m.group(2))/60+float(m.group(3))/3600
    return f(v) or 0.0
def rows_of(ws):
    allrows=list(ws.iter_rows(values_only=True))
    hdr=[str(c).strip() if c is not None else '' for c in allrows[0]]
    ix={h:i for i,h in enumerate(hdr)}
    return allrows[1:], ix
def get(r,ix,name):
    i=ix.get(name); return r[i] if (i is not None and i<len(r)) else None

# ---- load existing block ----
NET=json.load(open(JPATH))
cE,cN = NET['meta']['center_E'], NET['meta']['center_N']
old_strom = NET['stats']['strom'].copy()
old_nodes_strom = sum(1 for n in NET['nodes'] if n['u']=='strom')

# ---- parse new PIPE sheet ----
wb=openpyxl.load_workbook(SRC_X, read_only=True, data_only=True)
rows,ix = rows_of(wb['PIPE'])
segs=[]; dims=[]
for r in rows:
    if not r or r[0] in (None,''): continue
    se=f(get(r,ix,'Start Easting')); sn=f(get(r,ix,'Start Northing'))
    ee=f(get(r,ix,'End Easting'));   en=f(get(r,ix,'End Northing'))
    if None in (se,sn,ee,en): continue
    si=f(get(r,ix,'Start Invert')) or 0.0; ei=f(get(r,ix,'End Invert')) or 0.0
    iw=mm(get(r,ix,'Inner Width')) or 200.0; ih=mm(get(r,ix,'Inner Height')) or iw
    segs.append([se,sn,si,ee,en,ei]); dims.append([1, round(iw,1), round(ih,1)])
arr=np.array(segs)

# networks (relative to EXISTING centre), geo, stats
NET['networks']['strom']=[[round(s[0]-cE,2),round(s[1]-cN,2),round(s[2],3),
                           round(s[3]-cE,2),round(s[4]-cN,2),round(s[5],3)] for s in segs]
NET['dims']['strom']=dims
sl,so=T.transform(arr[:,0],arr[:,1]); el,eo=T.transform(arr[:,3],arr[:,4])
NET['geo']['strom']=[[round(so[i],6),round(sl[i],6),round(eo[i],6),round(el[i],6)] for i in range(len(segs))]
L=float(np.hypot(arr[:,3]-arr[:,0],arr[:,4]-arr[:,1]).sum())
d=np.array([x[1] for x in dims]); invs=np.concatenate([arr[:,2],arr[:,5]])
NET['stats']['strom']={'label':NET['stats']['strom']['label'],'count':len(segs),
    'length_m':round(L,1),'avg_dia':int(d.mean()),'max_dia':int(d.max()),'min_dia':int(d.min()),
    'min_inv':round(float(invs.min()),2),'max_inv':round(float(invs.max()),2)}

# ---- parse new MH sheet ----
rows,ix = rows_of(wb['MH'])
new_nodes=[]; skipped=0
for i,r in enumerate(rows):
    if not r or r[0] in (None,''): continue
    E=f(get(r,ix,'Easting')); N=f(get(r,ix,'Northing'))
    if E is None or N is None: skipped+=1; continue
    rim=f(get(r,ix,'Rim Elevation')); sump=f(get(r,ix,'Sump Elevation'))
    r2s=f(get(r,ix,'Rim to Sump Height'))
    if rim is None and sump is not None: rim=sump+2.0
    if rim is None: rim=f(get(r,ix,'Surface Elevation'))
    if rim is None: skipped+=1; continue
    if sump is None: sump=rim-(r2s if r2s else 2.0)
    if sump>=rim: sump=rim-0.6
    iw=meters(get(r,ix,'Inner Width')); il=meters(get(r,ix,'Inner Length'))
    shp=str(get(r,ix,'Shape') or '').strip().lower()
    circ = shp.startswith('cyl') if shp else False   # storm defaults to box
    lon,lat=T.transform(E,N)
    pipes=str(get(r,ix,'Connected Pipes') or '').strip()
    new_nodes.append({'u':'strom','sid':str(get(r,ix,'Structure Name') or ('strom-'+str(i+1))),
        'desc':str(get(r,ix,'Description') or ''),
        'x':round(E-cE,2),'z':round(N-cN,2),'E':round(E,3),'N':round(N,3),
        'inv':round(sump,2),'rim':round(rim,2),'frl':round(rim,2),
        'dia':round(iw or 1.2,3),'len':round(il,3) if il else 0,
        'coneH':round(meters(get(r,ix,'Cone Height')) or 0,3),
        'neck':round(meters(get(r,ix,'Frame Length')) or 0.45,3),
        'rot':round(ang(get(r,ix,'Rotation Angle')),2),
        'shape':'cyl' if circ else 'box','pipes':pipes,
        'deg':max(1,len([p for p in pipes.split(',') if p.strip() and p.strip()!='<None>'])),
        'mh':True,'real':1,'lat':round(lat,6),'lon':round(lon,6)})

NET['nodes']=[n for n in NET['nodes'] if n['u']!='strom'] + new_nodes

# ---- write JSON + patch the block HTML(s) ----
json.dump(NET, open(JPATH,'w'), separators=(',',':'))
compact=json.dumps(NET, separators=(',',':'))
for hp in [HPATH, f'restore/Amaravati_DigitalTwin_FullPackage/webapp/blocks/AmaravatiTwin_{CODE}.html']:
    if not os.path.exists(hp): print(f'  ! missing {hp}'); continue
    h=open(hp).read()
    h2=re.sub(r'const NET\s*=\s*\{.*?\};', 'const NET='+compact+';', h, count=1, flags=re.S)
    assert h2!=h or compact in h, f'NET replace failed in {hp}'
    open(hp,'w').write(h2)

# ---- update manifest entries ----
ORDER=['water','sewer','strom','reuse','power']
st=NET['stats']
pipes_total=sum(st[k]['count'] for k in ORDER)
km_total=round(sum(st[k]['length_m'] for k in ORDER)/1000,2)
utils={k:{'pipes':st[k]['count'],'km':round(st[k]['length_m']/1000,2)} for k in ORDER}
for mp in ['zone5pkg/Amaravati_Twins/manifest.json',
           'restore/Amaravati_DigitalTwin_FullPackage/webapp/manifest.json']:
    if not os.path.exists(mp): continue
    man=json.load(open(mp))
    for m in man:
        if m['code']==CODE:
            m['pipes']=pipes_total; m['manholes']=len(NET['nodes'])
            m['length_km']=km_total; m['utils']=utils
    json.dump(man, open(mp,'w'), separators=(',',':'))

# ---- Manning capacity report (same formula as make_app zone_storm) ----
def manning_q(seg, dia_mm):
    Lm=math.hypot(seg[3]-seg[0],seg[4]-seg[1])
    slope=abs(seg[2]-seg[5])/Lm if Lm>0.5 else 0.0015
    S=max(slope,0.0008); Dv=dia_mm/1000.0
    return (1/0.014)*math.pi*Dv*Dv/4*(Dv/4)**(2/3)*S**0.5
qcap=sum(manning_q(s,dims[i][1]) for i,s in enumerate(NET['networks']['strom']))

print(f"STORM before → after")
print(f"  pipes:  {old_strom['count']} → {st['strom']['count']}")
print(f"  length: {old_strom['length_m']/1000:.2f} → {st['strom']['length_m']/1000:.2f} km")
print(f"  dia:    {old_strom['min_dia']}–{old_strom['max_dia']} → {st['strom']['min_dia']}–{st['strom']['max_dia']} mm")
print(f"  invert: {st['strom']['min_inv']}–{st['strom']['max_inv']} m")
print(f"  MH:     {old_nodes_strom} → {len(new_nodes)}  (skipped {skipped})")
print(f"BLOCK totals: {pipes_total} pipes · {len(NET['nodes'])} MH · {km_total} km")
print(f"Zone 1B storm outfall capacity (Manning): {qcap:.1f} m³/s")

# copy the source workbook into the package
shutil.copy(SRC_X, 'restore/Amaravati_DigitalTwin_FullPackage/datasets/source_workbooks/Z1B_B5.xlsx')
print("source workbook archived")
