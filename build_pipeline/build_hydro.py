#!/usr/bin/env python3
"""Join the WaterGEMS result tables (4 demand scenarios) to the R4 trunk model already in the twin.
 pipes     : CSV ID == DXF pipe ID label (ID:nnnn)  -> segments via revision.seg_of_poly
 junctions : CSV Label == DXF node text               -> position from the DXF node symbols
 direction : my segments are oriented to the DXF flow arrows (= 2058 scenario). A scenario flow that
             has the opposite sign to the 2058 flow runs against the drawn direction."""
import ezdxf, csv, json, re, sys, collections, math, numpy as np
from scipy.spatial import cKDTree
from pyproj import Transformer
U="/mnt/user-data/uploads/"
T=json.load(open("trunk_app.json")); CE,CN=T["meta"]["center_E"],T["meta"]["center_N"]
SC=[("2028","2028 demand","1791785926852_pipe_table_2028.csv","1791785926852_junction_table_2028.csv"),
    ("2043","2043 demand","1791785926852_2043_pipe_table.csv","1791785926852_2043_junction_table.csv"),
    ("2043X","2043 · without Undavalli & Tadepalli","1791785926852_2043__no_undavalli_tadepalli_pipe_table.csv","1791785926852_2043__no_undavalli_tadepalli_junction_table.csv"),
    ("2058","2058 ultimate demand","1791785926851_2058_pipetable.csv","1791785926851_2058_junction_table.csv")]
def num(x):
    x=(x or "").strip().replace(",","")
    try: return float(x)
    except: return None
# ---------- DXF: node symbol positions + labels, pipe polylines ----------
doc=ezdxf.readfile(U+"2058_R4_bypass.dxf"); msp=doc.modelspace()
ins=[(e.dxf.name,e.dxf.insert.x,e.dxf.insert.y) for e in msp if e.dxftype()=="INSERT" and e.dxf.layer=="node"]
itree=cKDTree(np.array([[a[1],a[2]] for a in ins])); nlab=[None]*len(ins)
OFF={("FILLED_CIRCLE","ID"):(0.5,0.5),("AIRVALVE","ID"):(6.0,2.44),("VALVETCV","ID"):(2.44,2.44),("PUMP","ID"):(2.44,2.44),("RESERVOIR","ID"):(2.44,2.44),("XINCIRCLE","ID"):(2.44,2.44)}
for e in msp:
    if e.dxftype()=="TEXT" and e.dxf.layer=="node":
        t=e.dxf.text.strip()
        if re.match(r"(IL|Pr):",t): continue
        tx,ty=e.dxf.insert.x,e.dxf.insert.y; best=None
        for (blk,kk),(ox,oy) in OFF.items():
            d,j=itree.query([tx-ox,ty-oy])
            if d<0.08 and ins[j][0]==blk and (best is None or d<best[0]): best=(d,j)
        if best is None:
            d,j=itree.query([tx,ty]);
            if d>3: continue
            best=(d,j)
        j=best[1]
        if nlab[j] is None or len(t)>len(nlab[j]): nlab[j]=t
lab2xy={}
for (n,x,y),l in zip(ins,nlab):
    if l: lab2xy.setdefault(l.strip(),(x,y))
print("DXF node labels:",len(lab2xy))
# pipe polylines in DXF order with their ID label (as build_trunk_r4 did) and drawn direction
polys=[]
for e in msp:
    if e.dxftype()=="POLYLINE" and e.dxf.layer=="pipe":
        v=[(p.dxf.location.x,p.dxf.location.y) for p in e.vertices]; v=[q for i,q in enumerate(v) if i==0 or q!=v[i-1]]
        if len(v)>=2: polys.append(v)
pid=T["revision"]["pipe_ids"]; sop=T["revision"]["seg_of_poly"]; S=T["networks"]["water"]
assert len(polys)==len(pid)==len(sop)
# was each polyline flipped at build time? compare drawn first vertex with my segment start
flipped=[]
for k,(v,(a,b)) in enumerate(zip(polys,sop)):
    s=S[a]; d0=math.hypot(s[0]+CE-v[0][0],s[1]+CN-v[0][1]); d1=math.hypot(s[0]+CE-v[-1][0],s[1]+CN-v[-1][1])
    flipped.append(d1<d0)
print("polylines flipped to arrow at build:",sum(flipped))
# ---------- scenarios ----------
tr=Transformer.from_crs("EPSG:32644","EPSG:4326",always_xy=True)
idx_by_id={int(p):k for k,p in enumerate(pid) if p is not None}
out={"scenarios":[],"pipes":{},"junctions":{}}
P58={int(r["ID"]):num(r["Flow (MLD)"]) for r in csv.DictReader(open(U+SC[3][2],encoding="utf-8-sig"))}
# sign convention check: in 2058, negative CSV flow should coincide with polylines that were flipped
chk=collections.Counter()
for i,q in P58.items():
    if i in idx_by_id and q is not None and abs(q)>0.05: chk[(q<0,flipped[idx_by_id[i]])]+=1
print("2058 sign vs flip (neg,flipped):",dict(chk))
static={}   # per pipe id: label,len,dia,mat,C
for key,label,pf,jf in SC:
    P=list(csv.DictReader(open(U+pf,encoding="utf-8-sig"))); J=list(csv.DictReader(open(U+jf,encoding="utf-8-sig")))
    hyd=[None]*len(S); fd=["+"]*len(S); miss=0
    jun={}
    for r in J:
        l=r["Label"].strip(); jun[l]={"el":num(r["Elevation (m)"]),"dem":num(r["Demand (MLD)"]),"hgl":num(r["Hydraulic Grade (m)"]),"p":num(r["Pressure (m H2O)"])}
    for r in P:
        i=int(r["ID"]); static.setdefault(i,{"label":r["Label"],"len":num(r["Length (Scaled) (m)"]),"dia":num(r["Diameter (mm)"]),"mat":r["Material"],"C":num(r["Hazen-Williams C"])})
        if i not in idx_by_id: miss+=1; continue
        q=num(r["Flow (MLD)"]); v=num(r["Velocity (m/s)"]); g=num(r["Headloss Gradient (m/km)"]); h=num(r["Headloss (m)"])
        k=idx_by_id[i]; a,b=sop[k]
        # direction relative to my orientation: CSV sign is relative to the drawn polyline; drawn was flipped if arrow disagreed
        sign = 0 if q is None or abs(q)<0.005 else (1 if q>0 else -1)
        rel = 0 if sign==0 else (sign*(-1 if flipped[k] else 1))
        for s_ in range(a,b):
            hyd[s_]=[round(abs(q)*1000/86.4,2) if q is not None else None, v, g, rel, h]   # LPS, m/s, m/km, dir(+1/-1/0), m
            fd[s_]="-" if rel<0 else "+"
    nmiss=sum(1 for x in hyd if x is None)
    tot=sum(j["dem"] or 0 for j in jun.values())
    prs=[j["p"] for j in jun.values() if j["p"] is not None]
    out["scenarios"].append({"key":key,"label":label,"src":pf,"hyd":hyd,"fdir":"".join(fd),"jun":jun,
        "stats":{"demand_mld":round(tot,1),"p_min":round(min(prs),1),"p_max":round(max(prs),1),"p_mean":round(sum(prs)/len(prs),1),
                 "rev_segs":fd.count("-"),"na_segs":sum(1 for x in hyd if x and x[0] is None),"pipes_unmatched":miss}})
    print("%-6s pipes->segs ok, unmatched csv pipes %d, segs without data %d, reversed %d, demand %.1f MLD, P %.1f..%.1f"%(key,miss,nmiss,fd.count("-"),tot,min(prs),max(prs)))
# junction positions
jpos={}
for l in set().union(*[set(s["jun"]) for s in out["scenarios"]]):
    if l in lab2xy: x,y=lab2xy[l]; lon,lat=tr.transform(x,y); jpos[l]={"x":round(x-CE,2),"z":round(y-CN,2),"E":round(x,3),"N":round(y,3),"lat":round(lat,6),"lon":round(lon,6)}
print("junctions located in DXF: %d of %d"%(len(jpos),len(set().union(*[set(s["jun"]) for s in out["scenarios"]]))))
unl=[l for l in set().union(*[set(s["jun"]) for s in out["scenarios"]]) if l not in lab2xy]; print("  unlocated:",unl[:15])
out["jpos"]=jpos; out["pipe_static"]={str(k):v for k,v in static.items()}; out["pipe_of_seg"]=[None]*len(S)
for k,(a,b) in enumerate(sop):
    for s_ in range(a,b): out["pipe_of_seg"][s_]=int(pid[k]) if pid[k] is not None else None
json.dump(out,open("hydro.json","w"),separators=(",",":"))
print("hydro.json %.2f MB"%(len(json.dumps(out,separators=(",",":")))/1048576))
