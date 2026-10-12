"""Merge tessellated IFC elements by colour, decimate each colour group, write a GLB (Y-up, metres).
Model coordinates are kept as-is (local); georeferencing is applied at placement time in the twin."""
import pickle, numpy as np, trimesh, sys, json, fast_simplification, collections
src, out, target = sys.argv[1], sys.argv[2], int(sys.argv[3])
d=pickle.load(open(src,"rb")); V=d["V"]; F=d["F"]; C=d["C"]; META=d["META"]
# ---- engineering material palette by element family (the IFC carries only Revit default greys) ----
PAL={"concrete":(201,196,184),"concrete_dark":(176,172,162),"brick":(176,112,90),"steel":(96,108,120),"railing":(150,158,166),
     "pipe":(47,111,168),"fitting":(41,98,150),"valve":(183,71,42),"gate":(74,107,130),"ground":(126,139,94),"future":(154,163,122),
     "pavement":(128,128,126),"earth":(139,125,107),"filter":(217,211,199),"roof":(168,162,154),"sand":(194,178,128),"glass":(159,197,232)}
def palette(t,name):
    n=str(name).lower()
    if t in("IfcFlowSegment",) or "pipe types" in n or "dia pipe" in n or "water pipe" in n: return PAL["pipe"]
    if t=="IfcFlowFitting" or "elbow" in n or "flange" in n or "tee" in n: return PAL["fitting"]
    if t=="IfcFlowController" or "valve" in n: return PAL["valve"]
    if "sluice" in n or "gate" in n: return PAL["gate"]
    if t=="IfcRailing" or "railing" in n or "ladder" in n: return PAL["railing"]
    if "toposolid" in n or "floor_earth" in n or "earth" in n:
        return PAL["future"] if "future" in n else PAL["ground"]
    if "pavement" in n or "road" in n: return PAL["pavement"]
    if "air slab" in n or "filter" in n: return PAL["filter"]
    if "sand" in n: return PAL["sand"]
    if "bwk" in n or "brick" in n: return PAL["brick"]
    if t in("IfcPlate","IfcMember") or "steel" in n or "ms " in n or "support" in n or "plate" in n or "deck" in n: return PAL["steel"]
    if t=="IfcRoof" or "roof" in n: return PAL["roof"]
    if t in("IfcSlab","IfcWall","IfcWallStandardCase","IfcColumn","IfcBeam","IfcStair","IfcStairFlight","IfcCovering","IfcFooting"):
        return PAL["concrete_dark"] if ("foundation" in n or "plug" in n or "curb" in n) else PAL["concrete"]
    return None
if len(sys.argv)>7 and sys.argv[7]=="palette":
    off=0; C=C.copy(); hit=0
    for t,name,nt,mn,mx in META:
        c=palette(t,name)
        if c is not None: C[off:off+nt]=np.array(c)/255.0; hit+=nt
        off+=nt
    print("palette applied to %d of %d triangles"%(hit,len(C)))
A=np.ones(len(C),dtype=np.float32)                       # per-triangle opacity
HELPER=("Clearance Zone","Cutting geometry")
if len(sys.argv)>7 and sys.argv[7].startswith("ifc:"):
    tag=sys.argv[7][4:]; ST=json.load(open("ifc_styles.json"))[tag]
    names=list(ST); SC=np.array([ST[n][:3] for n in names]); TR=np.array([ST[n][3] for n in names])
    U,inv=np.unique(np.round(C,3),axis=0,return_inverse=True); inv=inv.ravel()
    styled=np.zeros(len(U),dtype=bool); u_alpha=np.ones(len(U)); u_drop=np.zeros(len(U),dtype=bool); used_names=set()
    for i,u in enumerate(U):
        dd=np.abs(SC-u).max(1); j=dd.argmin()
        if dd[j]<0.006:
            styled[i]=True; used_names.add(names[j])
            if names[j] in HELPER: u_drop[i]=True
            if TR[j]>0: u_alpha[i]=max(0.30,1.0-TR[j])          # Revit 90% transparent glass -> 0.30 opacity (still readable)
    tri_styled=styled[inv]; A=u_alpha[inv].astype(np.float32)
    # palette only where the IFC gave no surface style
    off=0; C=C.copy(); pal=0
    for t,name,nt,mn,mx in META:
        seg=slice(off,off+nt)
        if nt and not tri_styled[off]:
            c=palette(t,name)
            if c is not None: C[seg]=np.array(c)/255.0; pal+=nt
        off+=nt
    keep_h=~u_drop[inv]
    print("IFC colours kept on %.1f%% of triangles (%d styles used); palette fallback on %d unstyled triangles; helper geometry dropped %d; transparent %d"%(
        100*tri_styled.mean(),len(used_names),pal,(~keep_h).sum(),(A<1).sum()))
    if (~keep_h).any():
        # drop helper triangles from F/C/A while keeping META offsets valid -> mark them for exclusion below
        HDROP=~keep_h
    else: HDROP=None
else: HDROP=None
# optional exclusions: element types / family prefixes that are invisible or too fine for a city-scale twin
EXCL_T=set((sys.argv[4] if len(sys.argv)>4 else "").split(",")) - {""}
EXCL_F=tuple(x for x in (sys.argv[5] if len(sys.argv)>5 else "").split(",") if x)
POLY=None
if len(sys.argv)>6 and sys.argv[6]:
    import json as _j; POLY=np.array(_j.load(open(sys.argv[6])))       # plan polygon in model coords (m)
def in_poly(pt,P):
    x,y=pt; inside=False; n=len(P)
    for i in range(n):
        x1,y1=P[i]; x2,y2=P[(i+1)%n]
        if (y1>y)!=(y2>y) and x < (x2-x1)*(y-y1)/(y2-y1+1e-12)+x1: inside=not inside
    return inside
if EXCL_T or EXCL_F or POLY is not None or HDROP is not None:
    keep=np.ones(len(F),dtype=bool) if HDROP is None else ~HDROP; off=0; npoly=0
    for t,name,nt,mn,mx in META:
        fam=str(name).split(":")[0]
        drop = t in EXCL_T or (fam.startswith(EXCL_F) or str(name).startswith(EXCL_F))
        if not drop and POLY is not None and mx[2]>-6 and in_poly(((mn[0]+mx[0])/2,(mn[1]+mx[1])/2),POLY): drop=True; npoly+=1
        if drop: keep[off:off+nt]=False
        off+=nt
    F=F[keep]; C=C[keep]; A=A[keep]; print("excluded %d triangles by type/family/polygon (%d elements inside polygon)"%((~keep).sum(),npoly))
# quantise colours to group
key=np.round(C*255).astype(np.int64); ak=np.round(A*20).astype(np.int64)
keys=(key[:,0]*65536+key[:,1]*256+key[:,2])*32+ak               # exact 8-bit colour + opacity
groups=collections.defaultdict(list)
for i,k in enumerate(keys): groups[k].append(i)
print("triangles %d in %d colour groups"%(len(F),len(groups)))
ratio=1.0 if target<=0 else min(1.0,target/len(F))
scene=trimesh.Scene(); tot=0
for k,idx in sorted(groups.items(),key=lambda t:-len(t[1])):
    idx=np.array(idx); faces=F[idx]
    used=np.unique(faces); remap=-np.ones(len(V),dtype=np.int64); remap[used]=np.arange(len(used))
    v=V[used]; f=remap[faces]
    if len(f)>2000 and ratio<0.98:
        try:
            v2,f2=fast_simplification.simplify(v.astype(np.float32),f.astype(np.int32),target_reduction=1-ratio,agg=5)
            if len(f2)>0: v,f=v2,f2
        except Exception as e: print("  simplify failed group",k,e)
    col=(C[idx[0]]*255).astype(np.uint8)
    m=trimesh.Trimesh(vertices=v,faces=f,process=False)
    # Z-up (IFC) -> Y-up (glTF): (x,y,z) -> (x,z,-y)
    m.vertices=np.column_stack([m.vertices[:,0],m.vertices[:,2],-m.vertices[:,1]])
    m.visual=trimesh.visual.ColorVisuals(m,face_colors=np.tile(np.append(col,255),(len(f),1)))
    m.visual.material=None
    alpha=float(A[idx[0]]); colf=C[idx[0]]
    col=np.clip(np.round(colf*255),0,255).astype(np.uint8)
    lum=0.2126*colf[0]+0.7152*colf[1]+0.0722*colf[2]
    metal=0.55 if (alpha>=1 and abs(colf[0]-colf[1])<.02 and abs(colf[1]-colf[2])<.02 and lum>.9) else 0.05
    mat=trimesh.visual.material.PBRMaterial(baseColorFactor=[int(col[0]),int(col[1]),int(col[2]),int(round(alpha*255))],
        metallicFactor=metal,roughnessFactor=0.35 if alpha<1 else 0.78,doubleSided=True,alphaMode=("BLEND" if alpha<1 else "OPAQUE"))
    m.visual=trimesh.visual.TextureVisuals(material=mat)
    scene.add_geometry(m,node_name="g%d"%k); tot+=len(f)
scene.export(out)
import os; print("wrote %s: %d triangles, %.2f MB"%(out,tot,os.path.getsize(out)/1048576))
b=scene.bounds; print("glb bounds (Y-up) min",np.round(b[0],2),"max",np.round(b[1],2))
