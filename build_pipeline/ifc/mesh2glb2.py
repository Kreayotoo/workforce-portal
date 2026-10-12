"""Tessellated IFC -> GLB, one mesh per IFC surface style (Revit material).
Colour = the IfcSurfaceStyleRendering SurfaceColour exactly as written in the IFC (REAL).
Metalness / roughness / transparency are assigned by material class (glass, metal, concrete, ...).
Optional: decimation target (0 = none), type/family exclusions, plan-polygon exclusion."""
import pickle, numpy as np, trimesh, sys, json, os, collections, fast_simplification
src, out, target = sys.argv[1], sys.argv[2], int(sys.argv[3])
EXCL_T=set((sys.argv[4] if len(sys.argv)>4 else "").split(","))-{""}
EXCL_F=tuple(x for x in (sys.argv[5] if len(sys.argv)>5 else "").split(",") if x)
POLY=np.array(json.load(open(sys.argv[6]))) if len(sys.argv)>6 and sys.argv[6] else None
STYLES=json.load(open(sys.argv[7])) if len(sys.argv)>7 else {}
d=pickle.load(open(src,"rb")); V=d["V"]; F=d["F"]; C=d["C"]; RID=d["RID"]; META=d["META"]; MNAMES=d.get("MNAMES",[])
BYNAME={v[0]:v for v in STYLES.values() if v[0]}          # material name -> (name, colour, transparency)
def in_poly(pt,P):
    x,y=pt; inside=False; n=len(P)
    for i in range(n):
        x1,y1=P[i]; x2,y2=P[(i+1)%n]
        if (y1>y)!=(y2>y) and x < (x2-x1)*(y-y1)/(y2-y1+1e-12)+x1: inside=not inside
    return inside
keep=np.ones(len(F),dtype=bool); off=0; npoly=0
for t,name,nt,mn,mx in META:
    fam=str(name).split(":")[0]; drop=t in EXCL_T or fam.startswith(EXCL_F)
    if not drop and POLY is not None and mx[2]>-6 and in_poly(((mn[0]+mx[0])/2,(mn[1]+mx[1])/2),POLY): drop=True; npoly+=1
    if drop: keep[off:off+nt]=False
    off+=nt
F=F[keep]; C=C[keep]; RID=RID[keep]
print("kept %d triangles (excluded %d; %d elements inside polygon)"%(len(F),(~keep).sum(),npoly))

# material class -> PBR
def pbr(name):
    n=name.lower()
    if "glass" in n or "mirror" in n: return dict(metallic=0.0,rough=0.05,alpha=0.42)
    if any(k in n for k in ("steel","metal","aluminium","aluminum","iron","copper","chrome","stainless","deck")): return dict(metallic=0.85,rough=0.35,alpha=1.0)
    if any(k in n for k in ("concrete","screed","granite","default floor","default wall","stud")): return dict(metallic=0.0,rough=0.92,alpha=1.0)
    if "brick" in n: return dict(metallic=0.0,rough=0.95,alpha=1.0)
    if any(k in n for k in ("asphalt","bitumen")): return dict(metallic=0.0,rough=0.98,alpha=1.0)
    if any(k in n for k in ("grass","earth","sand","soil")): return dict(metallic=0.0,rough=1.0,alpha=1.0)
    if any(k in n for k in ("wood","birch","cherry","laminate","door","sash")): return dict(metallic=0.0,rough=0.6,alpha=1.0)
    if "paint" in n or "clad" in n or "plastic" in n or "ceramic" in n or "cotto" in n: return dict(metallic=0.05,rough=0.45,alpha=1.0)
    return dict(metallic=0.1,rough=0.8,alpha=1.0)

groups=collections.defaultdict(list)
for i,r in enumerate(RID.tolist()): groups[r].append(i)
ratio=1.0 if target<=0 else min(1.0,target/len(F))
scene=trimesh.Scene(); tot=0; report=collections.Counter(); used_names=collections.Counter()
for r,idx in sorted(groups.items(),key=lambda t:-len(t[1])):
    idx=np.array(idx); faces=F[idx]
    mname=MNAMES[r] if 0<=r<len(MNAMES) else ""
    import re as _re; mm=_re.match(r"IfcSurfaceStyleRendering-(\d+)$",mname)
    st=STYLES.get(mm.group(1)) if mm else BYNAME.get(mname)
    name=(st[0] if st and st[0] else mname)
    sc=st[1] if st and st[1] else None
    if sc is None:                                       # unstyled in the IFC: class colour, not the tessellator's muted default
        sc=(0.55,0.58,0.62) if "railing" in name.lower() else (0.753,0.753,0.753)
        if name in ("DefaultMaterial",""): name="Concrete (unstyled in IFC)"
        elif "railing" in name.lower(): name="Railing, painted steel (unstyled in IFC)"
    tr=float(st[2]) if st and st[2] not in ("",None,"$") else 0.0
    used=np.unique(faces); remap=-np.ones(len(V),dtype=np.int64); remap[used]=np.arange(len(used))
    v=V[used]; f=remap[faces]
    if len(f)>2000 and ratio<0.98:
        try:
            v2,f2=fast_simplification.simplify(v.astype(np.float32),f.astype(np.int32),target_reduction=1-ratio,agg=5)
            if len(f2)>0: v,f=v2,f2
        except Exception as e: print("  simplify failed",r,e)
    m=trimesh.Trimesh(vertices=v,faces=f,process=False)
    m.vertices=np.column_stack([m.vertices[:,0],m.vertices[:,2],-m.vertices[:,1]])   # Z-up -> Y-up
    p=pbr(name or "unknown"); alpha=min(p["alpha"],1.0-tr) if tr>0 else p["alpha"]
    col=[int(round(sc[0]*255)),int(round(sc[1]*255)),int(round(sc[2]*255)),int(round(alpha*255))]
    mat=trimesh.visual.material.PBRMaterial(name=name or ("style-%d"%r),baseColorFactor=col,metallicFactor=p["metallic"],roughnessFactor=p["rough"],doubleSided=True,alphaMode=("BLEND" if alpha<0.999 else "OPAQUE"))
    m.visual=trimesh.visual.TextureVisuals(material=mat)
    scene.add_geometry(m,node_name=(name or "style-%d"%r).replace(" ","_")[:60]+"_%d"%r,geom_name=(name or "style-%d"%r)+" #%d"%r)
    tot+=len(f); report[name or "?"]+=len(f)
scene.export(out)
print("wrote %s: %d triangles, %d materials, %.2f MB"%(out,tot,len(groups),os.path.getsize(out)/1048576))
for n,c in report.most_common(12): print("   %-40s %8d tris"%(n[:40],c))
