#!/usr/bin/env python3
"""IFC -> Y-up glb with REAL Revit material colours. Colours resolved via IFC style traversal (no crash);
geometry via the geometry-only iterator (no material access)."""
import ifcopenshell, ifcopenshell.geom as geom
import numpy as np, trimesh, os, time
from collections import defaultdict

IFC="/mnt/user-data/uploads/WTP-ADMIN-AR_09.ifc"
f=ifcopenshell.open(IFC)

# ---- pass 1: element id -> (r,g,b,a) from real Revit surface styles ----
si_by_item={}
for si in f.by_type('IfcStyledItem'):
    if si.Item is not None: si_by_item[si.Item.id()]=si
def si_color(si):
    if si is None: return None
    for sa in si.Styles:
        styles = sa.Styles if sa.is_a('IfcPresentationStyleAssignment') else [sa]
        for st in styles:
            if st.is_a('IfcSurfaceStyle'):
                for r in st.Styles:
                    if r.is_a('IfcSurfaceStyleRendering'):
                        c=r.SurfaceColour; tr=r.Transparency or 0.0
                        return (c.Red,c.Green,c.Blue, max(0.06,1.0-tr))
                    if r.is_a('IfcSurfaceStyleShading'):
                        c=r.SurfaceColour; return (c.Red,c.Green,c.Blue,1.0)
    return None
def item_ids(it):
    if it.is_a('IfcMappedItem'):
        out=[]
        for x in it.MappingSource.MappedRepresentation.Items: out+=item_ids(x)
        return out
    return [it.id()]
elem_color={}
for el in f.by_type('IfcProduct'):
    if not el.Representation: continue
    ids=[]
    for rep in el.Representation.Representations:
        for it in rep.Items: ids+=item_ids(it)
    for i in ids:
        c=si_color(si_by_item.get(i))
        if c: elem_color[el.id()]=c; break
print("colours resolved for", len(elem_color), "elements")

# ---- pass 2: geometry (no material access) + apply colour ----
EXCLUDE=['IfcOpeningElement','IfcSpace','IfcGrid','IfcAnnotation']
s=geom.settings(); s.set("use-world-coords", True)
it=geom.iterator(s, f, 6, exclude=EXCLUDE)
DEF=(0.74,0.73,0.71,1.0)
groups=defaultdict(lambda:{'v':[],'f':[],'off':0})
n=0; t0=time.time()
if it.initialize():
    while True:
        try:
            sh=it.get()
            v=np.asarray(sh.geometry.verts,dtype=np.float64).reshape(-1,3)
            fac=np.asarray(sh.geometry.faces,dtype=np.int64).reshape(-1,3)
            if len(v) and len(fac):
                col=elem_color.get(sh.id, DEF)
                key=(round(col[0],3),round(col[1],3),round(col[2],3),round(col[3],2))
                vy=np.column_stack([v[:,0], v[:,2], -v[:,1]])          # Z-up -> Y-up
                G=groups[key]; G['v'].append(vy); G['f'].append(fac+G['off']); G['off']+=len(vy)
                n+=1
        except Exception: pass
        if not it.next(): break
print(f"tessellated {n} elements in {time.time()-t0:.0f}s -> {len(groups)} colour groups")

scene=trimesh.Scene(); amn=np.array([1e18]*3); amx=-amn
for (r,g_,b,a),G in groups.items():
    V=np.vstack(G['v']); F=np.vstack(G['f'])
    amn=np.minimum(amn,V.min(0)); amx=np.maximum(amx,V.max(0))
    m=trimesh.Trimesh(vertices=V, faces=F, process=False)
    metal=0.7 if (abs(r-g_)<0.05 and abs(g_-b)<0.05 and 0.35<r<0.75 and a>=0.99) else 0.0
    m.visual=trimesh.visual.TextureVisuals(material=trimesh.visual.material.PBRMaterial(
        baseColorFactor=[int(r*255),int(g_*255),int(b*255),int(a*255)],
        metallicFactor=metal, roughnessFactor=(0.45 if a<0.99 else 0.82),
        alphaMode=('BLEND' if a<0.99 else 'OPAQUE'), doubleSided=True))
    scene.add_geometry(m)
cx=(amn[0]+amx[0])/2; cz=(amn[2]+amx[2])/2; by=amn[1]
T=np.eye(4); T[:3,3]=[-cx,-by,-cz]
for g_ in scene.geometry.values(): g_.apply_transform(T)
print("footprint X %.1f  Y %.1f  Z %.1f m"%tuple(amx-amn))
scene.export("/home/claude/building.glb")
print("building.glb:", round(os.path.getsize("/home/claude/building.glb")/1024/1024,2),"MB")
