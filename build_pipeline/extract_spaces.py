#!/usr/bin/env python3
import ifcopenshell, ifcopenshell.geom as geom, ifcopenshell.util.element as EU
import numpy as np, json
R=json.load(open('recenter.json')); cx,by,cz=R['cx'],R['by'],R['cz']
order=json.load(open('floor_order.json'))['order']; name2idx={nm:i for i,(nm,ev) in enumerate(order)}
f=ifcopenshell.open("/mnt/user-data/uploads/WTP-ADMIN-AR_09.ifc")
# space -> storey
s2f={}
for rel in f.by_type('IfcRelAggregates'):
    if rel.RelatingObject and rel.RelatingObject.is_a('IfcBuildingStorey'):
        for o in rel.RelatedObjects:
            if o.is_a('IfcSpace'): s2f[o.id()]=rel.RelatingObject.Name
for rel in f.by_type('IfcRelContainedInSpatialStructure'):
    rs=rel.RelatingStructure
    if rs and rs.is_a('IfcBuildingStorey'):
        for el in rel.RelatedElements:
            if el.is_a('IfcSpace'): s2f[el.id()]=rs.Name
def area_of(s):
    try:
        for q in EU.get_psets(s).values():
            for k,v in q.items():
                if 'area' in k.lower() and isinstance(v,(int,float)) and v>1: return round(v,1)
    except: pass
    return None
def clean(nm):
    import re; nm=re.sub(r'^(GF|FF|SF|TF|FoF|FiF|\d+)\s+','',nm or ''); return nm.strip()
s=geom.settings(); s.set("use-world-coords", True)
out=[]
for sp in f.by_type('IfcSpace'):
    ln=(sp.LongName or sp.Name or '').strip()
    if not ln: continue
    try:
        sh=geom.create_shape(s, sp); v=np.asarray(sh.geometry.verts,dtype=np.float64).reshape(-1,3)
    except Exception: continue
    if not len(v): continue
    # raw Z-up -> glb coords (match build): (x-cx, z-by, -y-cz)
    fx=v[:,0]-cx; fy=v[:,2]-by; fz=-v[:,1]-cz
    px=float((fx.min()+fx.max())/2); pz=float((fz.min()+fz.max())/2); pyf=float(fy.min()+1.2)
    st=s2f.get(sp.id()); fidx=name2idx.get(st,-1)
    out.append({'floor':fidx,'name':clean(ln),'full':ln,'area':area_of(sp),'x':round(px,2),'y':round(pyf,2),'z':round(pz,2)})
json.dump(out, open('spaces.json','w'))
from collections import Counter
print("extracted", len(out), "rooms across floors:", dict(Counter(o['floor'] for o in out)))
for o in out[:6]: print("  F%d %-24s area=%s at (%.1f,%.1f,%.1f)"%(o['floor'],o['name'][:24],o['area'],o['x'],o['y'],o['z']))
