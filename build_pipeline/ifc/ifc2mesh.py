import ifcopenshell, ifcopenshell.geom, numpy as np, sys, time, json, pickle, multiprocessing, re
f=sys.argv[1]; out=sys.argv[2]; scale=float(sys.argv[3]) if len(sys.argv)>3 else 1.0
m=ifcopenshell.open(f)
s=ifcopenshell.geom.settings()
s.set("use-world-coords",True); s.set("weld-vertices",True); s.set("apply-default-materials",True)
it=ifcopenshell.geom.iterator(s,m,multiprocessing.cpu_count())
t=time.time(); n=0; V=[]; F=[]; C=[]; RID=[]; META=[]; off=0; skipped=0; MNAMES=[]; MIDX={}
if it.initialize():
    while True:
        sh=it.get()
        try:
            g=sh.geometry
            v=np.array(g.verts,dtype=np.float64).reshape(-1,3)*scale
            fc=np.array(g.faces,dtype=np.int64).reshape(-1,3)
            mats=g.materials; mids=np.array(g.material_ids,dtype=np.int64)
            cols=np.zeros((len(fc),3),dtype=np.float32)+0.7
            rids=np.zeros(len(fc),dtype=np.int64)-1           # index into MNAMES per triangle
            for i,mt in enumerate(mats):
                try:
                    d=mt.diffuse; cols[mids==i]=[d.r(),d.g(),d.b()]
                    nm=str(mt.name)
                    if nm not in MIDX: MIDX[nm]=len(MNAMES); MNAMES.append(nm)
                    rids[mids==i]=MIDX[nm]
                except Exception: pass
            if len(v) and len(fc):
                V.append(v); F.append(fc+off); C.append(cols); RID.append(rids); off+=len(v)
                META.append((sh.type,sh.name,len(fc),v.min(0).tolist(),v.max(0).tolist()))
                n+=1
        except Exception as e:
            skipped+=1
        if n%500==0: print("  %d elements, %d tris, %.0fs"%(n,sum(len(x) for x in F),time.time()-t),flush=True)
        if not it.next(): break
V=np.vstack(V); F=np.vstack(F); C=np.vstack(C); RID=np.concatenate(RID)
print("elements %d skipped %d  verts %d  tris %d  in %.0fs"%(n,skipped,len(V),len(F),time.time()-t))
print("bbox min",np.round(V.min(0),3),"max",np.round(V.max(0),3),"size",np.round(V.max(0)-V.min(0),3))
pickle.dump({"V":V,"F":F,"C":C,"RID":RID,"MNAMES":MNAMES,"META":META},open(out,"wb"),protocol=4)
print("materials recorded:",len(MNAMES),MNAMES[:8])
