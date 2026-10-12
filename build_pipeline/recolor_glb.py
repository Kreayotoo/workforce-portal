#!/usr/bin/env python3
"""Colour the FBX-derived glb by Revit category (from node names) with proper PBR materials + glass transparency."""
from pygltflib import GLTF2, Material, PbrMetallicRoughness
import os

g=GLTF2().load("building_real.glb")

def cat(name):
    n=(name or '').lower()
    if 'glazed' in n or 'glazing' in n or 'glass' in n or 'curtain panel' in n: return 'glass'
    if 'mullion' in n: return 'mullion'
    if 'window' in n: return 'window'
    if 'door' in n: return 'door'
    if 'rail' in n: return 'railing'
    if 'wall' in n: return 'wall'
    if any(k in n for k in ('floor','ceiling','slab','stair','landing','run','footing','foundation','ramp','roof')): return 'floor'
    if any(k in n for k in ('concrete','precast','cast','monolithic','column','beam','framing','pile','pier','plinth')): return 'concrete'
    if any(k in n for k in ('chair','furniture','desk','table','office','rockworth','sofa','cabinet','shelf','stool','locker','equipment')): return 'furniture'
    return 'default'

# map each mesh -> category via the nodes that reference it (prefer a specific category over default)
mesh_cat={}
for node in g.nodes:
    if node.mesh is not None:
        c=cat(node.name)
        if node.mesh not in mesh_cat or (mesh_cat[node.mesh]=='default' and c!='default'):
            mesh_cat[node.mesh]=c

# palette: baseColorFactor RGBA, roughness, metallic, alphaMode
PAL={
 'glass':    ([0.44,0.62,0.74,0.30], 0.12, 0.05, 'BLEND'),
 'window':   ([0.54,0.69,0.80,0.38], 0.14, 0.08, 'BLEND'),
 'mullion':  ([0.27,0.29,0.32,1.0],  0.42, 0.80, 'OPAQUE'),
 'door':     ([0.51,0.35,0.21,1.0],  0.55, 0.00, 'OPAQUE'),
 'railing':  ([0.23,0.25,0.28,1.0],  0.38, 0.75, 'OPAQUE'),
 'wall':     ([0.87,0.85,0.80,1.0],  0.92, 0.00, 'OPAQUE'),
 'concrete': ([0.67,0.67,0.64,1.0],  0.95, 0.00, 'OPAQUE'),
 'floor':    ([0.74,0.73,0.71,1.0],  0.90, 0.00, 'OPAQUE'),
 'furniture':([0.46,0.50,0.55,1.0],  0.70, 0.05, 'OPAQUE'),
 'default':  ([0.78,0.78,0.76,1.0],  0.85, 0.00, 'OPAQUE'),
}
matidx={}; g.materials=[]
for name,(bc,rough,metal,mode) in PAL.items():
    g.materials.append(Material(name=name, alphaMode=mode, doubleSided=True,
        pbrMetallicRoughness=PbrMetallicRoughness(baseColorFactor=bc, metallicFactor=metal, roughnessFactor=rough)))
    matidx[name]=len(g.materials)-1

from collections import Counter
used=Counter()
for mi,mesh in enumerate(g.meshes):
    c=mesh_cat.get(mi,'default'); used[c]+=1
    for prim in mesh.primitives: prim.material=matidx[c]

g.save("building_real_colored.glb")
print("recoloured by category:", dict(used))
print("building_real_colored.glb:", round(os.path.getsize("building_real_colored.glb")/1024/1024,2),"MB")
