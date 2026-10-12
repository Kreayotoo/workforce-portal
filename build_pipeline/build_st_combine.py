#!/usr/bin/env python3
import ifcopenshell, ifcopenshell.geom as geom
import numpy as np, os, time, json, pickle
from collections import defaultdict
ST="/mnt/user-data/uploads/WTP-ADMIN-ST_09.ifc"
order=json.load(open('floor_order.json'))['order']; name2idx={nm:i for i,(nm,ev) in enumerate(order)}
AR=pickle.load(open('ar_groups.pkl','rb')); groups=defaultdict(lambda:{'v':[],'f':[],'off':0})
for k,g in AR['groups'].items():
    G=groups[k]; G['v'].append(g['v']); G['f'].append(g['f']); G['off']+=len(g['v'])
amn=AR['amn'].copy(); amx=AR['amx'].copy()
# ST storeys
f_st=ifcopenshell.open(ST); st_e2s={}
for rel in f_st.by_type('IfcRelContainedInSpatialStructure'):
    rs=rel.RelatingStructure
    if rs and rs.is_a('IfcBuildingStorey'):
        for el in rel.RelatedElements: st_e2s[el.id()]=rs.Name
s=geom.settings(); s.set("use-world-coords", True)
try: s.set("mesher-linear-deflection", 0.04)
except Exception: pass
it=geom.iterator(s, f_st, 6, exclude=['IfcOpeningElement','IfcSpace','IfcGrid','IfcAnnotation'])
n=0;t0=time.time()
if it.initialize():
    while True:
        sh=it.get(); v=np.asarray(sh.geometry.verts,dtype=np.float64).reshape(-1,3); fac=np.asarray(sh.geometry.faces,dtype=np.int64).reshape(-1,3)
        if len(v) and len(fac):
            col=[0.62,0.63,0.66,1.0]; nm=st_e2s.get(sh.id); fidx=name2idx.get(nm,-1)
            vy=np.column_stack([v[:,0],v[:,2],-v[:,1]])
            if fidx<0: ev=v[:,2].min(); fidx=max(0,sum(1 for _,e in order if e<=ev+0.3)-1)
            amn=np.minimum(amn,vy.min(0)); amx=np.maximum(amx,vy.max(0))
            key=(fidx,0.62,0.63,0.66,1.0)
            G=groups[key]; G['v'].append(vy); G['f'].append(fac+G['off']); G['off']+=len(vy); n+=1
        if not it.next(): break
print(f"ST: {n} elements in {time.time()-t0:.0f}s", flush=True)
import trimesh
scene=trimesh.Scene(); gi=0
for (fidx,r,g_,b,a),G in groups.items():
    V=np.vstack(G['v']); F=np.vstack(G['f'])
    m=trimesh.Trimesh(vertices=V, faces=F, process=False)
    metal=0.7 if (abs(r-g_)<0.05 and abs(g_-b)<0.05 and 0.35<r<0.75 and a>=0.99) else 0.0
    m.visual=trimesh.visual.TextureVisuals(material=trimesh.visual.material.PBRMaterial(
        baseColorFactor=[int(r*255),int(g_*255),int(b*255),int(a*255)],
        metallicFactor=metal, roughnessFactor=(0.45 if a<0.99 else 0.82),
        alphaMode=('BLEND' if a<0.99 else 'OPAQUE'), doubleSided=True))
    scene.add_geometry(m, geom_name=f"FL{fidx:02d}_{gi}"); gi+=1
cx=(amn[0]+amx[0])/2; cz=(amn[2]+amx[2])/2; by=amn[1]
T=np.eye(4); T[:3,3]=[-cx,-by,-cz]
import json as _j; _j.dump({"cx":float(cx),"by":float(by),"cz":float(cz)}, open("recenter.json","w"))
for g_ in scene.geometry.values(): g_.apply_transform(T)
print("footprint X %.1f Y %.1f Z %.1f m · groups %d"%(amx[0]-amn[0],amx[1]-amn[1],amx[2]-amn[2],len(groups)), flush=True)
scene.export("/home/claude/building.glb")
print("building.glb:", round(os.path.getsize("/home/claude/building.glb")/1024/1024,2),"MB", flush=True)
