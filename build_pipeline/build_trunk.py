#!/usr/bin/env python3
"""Parse Trunk_Model.dxf -> trunk_network.json in the twin's network format (water transmission layer)."""
import ezdxf, json, math, re
import numpy as np
from scipy.spatial import cKDTree
from pyproj import Transformer

LEVEL = json.load(open('/tmp/trunk_level.json'))['level']   # place trunk at representative city ground level
DXF = "/mnt/user-data/uploads/Trunk_Model.dxf"
doc = ezdxf.readfile(DXF); msp = doc.modelspace()
to_wgs = Transformer.from_crs("EPSG:32644","EPSG:4326",always_xy=True)

# ---- 1) pipe polylines -> straight segments ----
def verts(e):
    t=e.dxftype()
    if t=='LWPOLYLINE': return [(p[0],p[1]) for p in e.get_points()]
    if t=='POLYLINE':   return [(v.dxf.location.x,v.dxf.location.y) for v in e.vertices]
    if t=='LINE':       return [(e.dxf.start.x,e.dxf.start.y),(e.dxf.end.x,e.dxf.end.y)]
    return []
segs=[]   # (xs,ys,xe,ye)
for e in msp:
    if e.dxftype() in ('POLYLINE','LWPOLYLINE','LINE') and e.dxf.layer=='pipe':
        v=verts(e)
        for i in range(len(v)-1):
            if v[i]!=v[i+1]: segs.append((v[i][0],v[i][1],v[i+1][0],v[i+1][1]))
print("trunk segments:", len(segs))

# ---- 2) diameter labels (D:xxx) -> nearest segment ----
dlabels=[]  # (x,y,dia_mm)
for e in msp:
    if e.dxftype()=='TEXT':
        t=e.dxf.text.strip()
        mm=re.match(r'D:\s*([\d,]+(?:\.\d+)?)',t)
        if mm:
            dia=float(mm.group(1).replace(',',''))
            p=e.dxf.insert; dlabels.append((p.x,p.y,dia))
print("diameter labels:", len(dlabels))
mids=np.array([[ (s[0]+s[2])/2,(s[1]+s[3])/2 ] for s in segs])
seg_dia=[600.0]*len(segs)   # default
if dlabels:
    dpos=np.array([[d[0],d[1]] for d in dlabels]); dval=np.array([d[2] for d in dlabels])
    tree=cKDTree(mids)
    # assign each diameter label to its nearest segment midpoint
    dist,idx=tree.query(dpos, k=1)
    for j,si in enumerate(idx):
        if dist[j] < 60:           # label within 60 m of the segment midpoint
            # prefer the larger diameter if two labels land on one segment
            if dval[j] > (seg_dia[si] if seg_dia[si]!=600.0 else 0): seg_dia[si]=float(dval[j])
# fill any still-default from nearest labelled neighbour
labelled=[i for i,d in enumerate(seg_dia) if d!=600.0 or True]
print("diameters assigned; distinct:", sorted(set(seg_dia))[:15])

# ---- 3) centroid + build arrays ----
allx=[c for s in segs for c in (s[0],s[2])]; ally=[c for s in segs for c in (s[1],s[3])]
CE=sum(allx)/len(allx); CN=sum(ally)/len(ally)
INV=round(LEVEL,2)
networks=[]; dims=[]; geo=[]
for (xs,ys,xe,ye),dia in zip(segs,seg_dia):
    networks.append([round(xs-CE,2),round(ys-CN,2),INV, round(xe-CE,2),round(ye-CN,2),INV])
    dims.append([0,int(round(dia)),int(round(dia))])           # round pipe, W=H=diameter mm
    slon,slat=to_wgs.transform(xs,ys); elon,elat=to_wgs.transform(xe,ye)
    geo.append([round(slat,6),round(slon,6),round(elat,6),round(elon,6)])

# ---- 4) stats + map + assemble ----
def hyp(s): return math.hypot(s[3]-s[0],s[4]-s[1])
length=sum(hyp(n) for n in networks)
dias=[d[1] for d in dims]
stats={'water':{'label':'Trunk Main','count':len(networks),'length_m':round(length,1),
    'avg_dia':int(round(sum(dias)/len(dias))),'max_dia':max(dias),'min_dia':min(dias),
    'min_inv':INV,'max_inv':INV}}
lon0,lat0=to_wgs.transform(CE,CN); lonx,latx=to_wgs.transform(CE+1,CN); lonn,latn=to_wgs.transform(CE,CN+1)
lats=[g[0] for g in geo]+[g[2] for g in geo]; lons=[g[1] for g in geo]+[g[3] for g in geo]
NET={
 'meta':{'zone':'TRUNK','block':'MAIN','grid':'44N','center_E':round(CE,2),'center_N':round(CN,2),
         'aboveground':False,'combined':True,'trunk':True},
 'stats':stats,
 'networks':{'water':networks,'sewer':[],'strom':[],'reuse':[],'power':[]},
 'geo':{'water':geo,'sewer':[],'strom':[],'reuse':[],'power':[]},
 'dims':{'water':dims,'sewer':[],'strom':[],'reuse':[],'power':[]},
 'nodes':[], 'nodes_src':'trunk transmission main (schematic, no invert levels in source)',
 'frl':{'level':INV,'note':'placed at representative city ground level (no levels in DXF)','src':'trunk'},
 'map':{'center':[round(lat0,6),round(lon0,6)],
        'bounds':[[min(lats),min(lons)],[max(lats),max(lons)]],
        'lonPerM_x':lonx-lon0,'latPerM_x':latx-lat0,'lonPerM_n':lonn-lon0,'latPerM_n':latn-lat0},
 'road':None
}
json.dump(NET, open('/home/claude/trunk_network.json','w'))
print("trunk_network.json: %d segments · %.1f km · dia %d-%d mm · center %.0f,%.0f · level %.1f m"%(
    len(networks), length/1000, min(dias), max(dias), CE, CN, INV))
# also save to package datasets
import shutil, os
os.makedirs('/home/claude/fullpkg/Amaravati_DigitalTwin_FullPackage/datasets/data_json', exist_ok=True)
shutil.copy('/home/claude/trunk_network.json','/home/claude/fullpkg/Amaravati_DigitalTwin_FullPackage/datasets/data_json/Trunk_Main_network.json')
