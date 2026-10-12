#!/usr/bin/env python3
"""Merge AR+ST IFCs into ONE Y-up glb, real colours, tagged FLOOR-WISE (by IFC storey)."""
import ifcopenshell, ifcopenshell.geom as geom
import numpy as np, trimesh, os, time, json
from collections import defaultdict

AR="/mnt/user-data/uploads/WTP-ADMIN-AR_09.ifc"; ST="/mnt/user-data/uploads/WTP-ADMIN-ST_09.ifc"
AR_COL={int(k):v for k,v in json.load(open('elem_color.json')).items()}
ST_COL={int(k):v for k,v in json.load(open('elem_color_st.json')).items()}

# ---- unified floor list (AR & ST share storey names/elevations) ----
def storeys(path):
    f=ifcopenshell.open(path)
    e2s={}
    for rel in f.by_type('IfcRelContainedInSpatialStructure'):
        rs=rel.RelatingStructure
        if rs and rs.is_a('IfcBuildingStorey'):
            for el in rel.RelatedElements: e2s[el.id()]=rs.Name
    st={s.Name:(s.Elevation or 0)/1000.0 for s in f.by_type('IfcBuildingStorey')}
    return e2s, st
ar_e2s, ar_st = storeys(AR); st_e2s, st_st = storeys(ST)
allst={**ar_st, **st_st}
order=sorted(allst.items(), key=lambda kv:kv[1])                 # (name,elev) bottom->top
name2idx={nm:i for i,(nm,ev) in enumerate(order)}
floors=[{'idx':i,'name':nm,'elev':round(ev,2)} for i,(nm,ev) in enumerate(order)]
NF=len(floors)
def clean(nm):
    import re; return re.sub(r'^\d+\s*','',nm).strip().title()
for fl in floors: fl['label']=clean(fl['name'])

s=geom.settings(); s.set("use-world-coords", True)
groups=defaultdict(lambda:{'v':[],'f':[],'off':0}); amn=np.array([1e18]*3); amx=-amn

def process(path, colmap, e2s, structural=False):
    global amn,amx
    f=ifcopenshell.open(path)
    it=geom.iterator(s, f, 6, exclude=['IfcOpeningElement','IfcSpace','IfcGrid','IfcAnnotation'])
    DEF=[0.62,0.63,0.66,1.0] if structural else [0.74,0.73,0.71,1.0]
    n=0; t0=time.time()
    if it.initialize():
        while True:
            sh=it.get()
            v=np.asarray(sh.geometry.verts,dtype=np.float64).reshape(-1,3)
            fac=np.asarray(sh.geometry.faces,dtype=np.int64).reshape(-1,3)
            if len(v) and len(fac):
                col=[0.62,0.63,0.66,1.0] if structural else colmap.get(sh.id, DEF)
                nm=e2s.get(sh.id); fidx=name2idx.get(nm, -1)
                vy=np.column_stack([v[:,0], v[:,2], -v[:,1]])            # Z-up -> Y-up
                if fidx<0:                                              # fallback: nearest storey below by elevation
                    ev=v[:,2].min()
                    fidx=max(0,sum(1 for _,e in order if e<=ev+0.3)-1)
                amn=np.minimum(amn,vy.min(0)); amx=np.maximum(amx,vy.max(0))
                key=(fidx, round(col[0],3),round(col[1],3),round(col[2],3),round(col[3],2))
                G=groups[key]; G['v'].append(vy); G['f'].append(fac+G['off']); G['off']+=len(vy)
                n+=1
            if not it.next(): break
    print(f"  {os.path.basename(path)}: {n} elements in {time.time()-t0:.0f}s", flush=True)

process(AR, AR_COL, ar_e2s); process(ST, ST_COL, st_e2s, structural=True)
print(f"groups: {len(groups)} · floors: {NF}", flush=True)

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
for g_ in scene.geometry.values(): g_.apply_transform(T)
print("footprint X %.1f Y %.1f Z %.1f m"%tuple(amx-amn), flush=True)
scene.export("/home/claude/building.glb")
json.dump(floors, open('/home/claude/floors.json','w'))
print("building.glb:", round(os.path.getsize("/home/claude/building.glb")/1024/1024,2),"MB · floors.json saved", flush=True)
