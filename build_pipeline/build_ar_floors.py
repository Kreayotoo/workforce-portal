#!/usr/bin/env python3
import ifcopenshell, ifcopenshell.geom as geom
import numpy as np, os, time, json, pickle, re
from collections import defaultdict
AR="/mnt/user-data/uploads/WTP-ADMIN-AR_09.ifc"; ST="/mnt/user-data/uploads/WTP-ADMIN-ST_09.ifc"
AR_COL={int(k):v for k,v in json.load(open('elem_color.json')).items()}
f_ar=ifcopenshell.open(AR); f_st=ifcopenshell.open(ST)     # HOLD references (avoid GC segfault)
def storeys(f):
    e2s={}
    for rel in f.by_type('IfcRelContainedInSpatialStructure'):
        rs=rel.RelatingStructure
        if rs and rs.is_a('IfcBuildingStorey'):
            for el in rel.RelatedElements: e2s[el.id()]=rs.Name
    return e2s, {s.Name:(s.Elevation or 0)/1000.0 for s in f.by_type('IfcBuildingStorey')}
ar_e2s, ar_st = storeys(f_ar); st_e2s, st_st = storeys(f_st)
allst={**ar_st, **st_st}; order=sorted(allst.items(), key=lambda kv:kv[1])
name2idx={nm:i for i,(nm,ev) in enumerate(order)}
floors=[{'idx':i,'name':nm,'elev':round(ev,2),'label':re.sub(r'^\d+\s*','',nm).strip().title()} for i,(nm,ev) in enumerate(order)]
json.dump(floors, open('floors.json','w')); json.dump({'order':order}, open('floor_order.json','w'))

s=geom.settings(); s.set("use-world-coords", True)
try: s.set("mesher-linear-deflection", 0.04)
except Exception: pass
groups=defaultdict(lambda:{'v':[],'f':[],'off':0}); amn=np.array([1e18]*3); amx=-amn
it=geom.iterator(s, f_ar, 6, exclude=['IfcOpeningElement','IfcSpace','IfcGrid','IfcAnnotation','IfcFurnishingElement','IfcFlowTerminal','IfcFlowSegment','IfcFlowFitting','IfcDistributionElement','IfcFurniture','IfcSystemFurnitureElement'])
n=0;t0=time.time()
if it.initialize():
    while True:
        sh=it.get(); v=np.asarray(sh.geometry.verts,dtype=np.float64).reshape(-1,3); fac=np.asarray(sh.geometry.faces,dtype=np.int64).reshape(-1,3)
        if len(v) and len(fac):
            col=AR_COL.get(sh.id,[0.74,0.73,0.71,1.0]); nm=ar_e2s.get(sh.id); fidx=name2idx.get(nm,-1)
            vy=np.column_stack([v[:,0],v[:,2],-v[:,1]])
            if fidx<0: ev=v[:,2].min(); fidx=max(0,sum(1 for _,e in order if e<=ev+0.3)-1)
            amn=np.minimum(amn,vy.min(0)); amx=np.maximum(amx,vy.max(0))
            key=(fidx,round(col[0],3),round(col[1],3),round(col[2],3),round(col[3],2))
            G=groups[key]; G['v'].append(vy); G['f'].append(fac+G['off']); G['off']+=len(vy); n+=1
        if not it.next(): break
print(f"AR: {n} elements in {time.time()-t0:.0f}s", flush=True)
out={k:{'v':np.vstack(g['v']),'f':np.vstack(g['f'])} for k,g in groups.items()}
pickle.dump({'groups':out,'amn':amn,'amx':amx}, open('ar_groups.pkl','wb'))
print("saved ar_groups.pkl · floors:", len(floors), flush=True)
