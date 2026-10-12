#!/usr/bin/env python3
"""Build compact datasets for the Decision Support module:
   - PLOTS: every masterplan plot centroid + zone + area (real GIS -> buffer analysis)
   - NET:   every pipe + manhole as metre offsets (real network -> impact analysis)"""
import shapefile, json, math, re
import numpy as np
from pyproj import Transformer

# ---------- 1. plots ----------
sf=shapefile.Reader('mp/Masterplan Mosaic data/Masterplan_Mosaic_01082025.shp')
flds=[f[0] for f in sf.fields[1:]]; zi=flds.index('zoning')
leg=json.load(open('landuse_legend.json'))
zones=[e['zone'] for e in leg]; zidx={z:i for i,z in enumerate(zones)}
colors=[e['color'] for e in leg]

to_wgs=Transformer.from_crs("EPSG:32644","EPSG:4326",always_xy=True)
cx=[];cy=[];cz=[];ca=[]
for sr in sf.iterShapeRecords():
    sh=sr.shape
    if not sh.points: continue
    z=str(sr.record[zi]).strip()
    if z not in zidx: continue
    P=np.array(sh.points)
    # shoelace area + centroid of the outer ring
    parts=list(sh.parts)+[len(P)]
    R=P[parts[0]:parts[1]]
    if len(R)<3: continue
    x=R[:,0]; y=R[:,1]
    a=0.5*np.sum(x[:-1]*y[1:]-x[1:]*y[:-1])
    if abs(a)<1: continue
    Cx=np.sum((x[:-1]+x[1:])*(x[:-1]*y[1:]-x[1:]*y[:-1]))/(6*a)
    Cy=np.sum((y[:-1]+y[1:])*(x[:-1]*y[1:]-x[1:]*y[:-1]))/(6*a)
    cx.append(Cx); cy.append(Cy); cz.append(zidx[z]); ca.append(abs(a))
cx=np.array(cx); cy=np.array(cy)
# origin = SW of the plot cloud (UTM), everything stored as metre offsets
E0=float(cx.min()); N0=float(cy.min())
lon0,lat0=to_wgs.transform(E0,N0)
dx=np.round(cx-E0).astype(int); dy=np.round(cy-N0).astype(int)
area=np.round(np.array(ca)).astype(int)
plots={'origin':[round(lat0,6),round(lon0,6)],'zones':zones,'colors':colors,
       'dx':dx.tolist(),'dy':dy.tolist(),'z':cz,'a':area.tolist()}
json.dump(plots, open('plots.json','w'), separators=(',',':'))
print("plots:",len(dx),"· origin lat %.5f lon %.5f"%(lat0,lon0))

# ---------- 2. network (all utilities, metre offsets from the same origin) ----------
man=json.load(open('zone5pkg/Amaravati_Twins/manifest.json'))
def load_net(c):
    return json.loads(re.search(r'const NET\s*=\s*(\{.*?\});',
        open(f'zone5pkg/Amaravati_Twins/blocks/AmaravatiTwin_{c}.html').read(), re.S).group(1))
UT=['water','sewer','strom','reuse','power']
P=[];M=[]
for m in man:
    net=load_net(m['code']); cE=net['meta']['center_E']; cN=net['meta']['center_N']
    for ui,u in enumerate(UT):
        dims=net['dims'].get(u,[])
        for i,s in enumerate(net['networks'].get(u,[])):
            x1=int(round(s[0]+cE-E0)); y1=int(round(s[1]+cN-N0))
            x2=int(round(s[3]+cE-E0)); y2=int(round(s[4]+cN-N0))
            d=int(dims[i][1]) if i<len(dims) else 200
            P.append([x1,y1,x2,y2,ui,d])
    for n in net['nodes']:
        try: ui=UT.index(n['u'])
        except ValueError: continue
        M.append([int(round(n['x']+cE-E0)), int(round(n['z']+cN-N0)), ui,
                  int(round((n.get('rim',0)-n.get('inv',0))*10))])   # depth in dm
net={'utils':UT,'pipes':P,'mh':M}
json.dump(net, open('incident_net.json','w'), separators=(',',':'))
import os
print("pipes:",len(P),"· manholes:",len(M))
print("plots.json %.1f MB · incident_net.json %.1f MB"%(os.path.getsize('plots.json')/1e6, os.path.getsize('incident_net.json')/1e6))
