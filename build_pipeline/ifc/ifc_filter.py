#!/usr/bin/env python3
"""Stream-filter a huge IFC2x3 file down to structural + process elements.
Pass 1: one line per entity -> id, type, forward references (kept as flat int32 pairs).
Closure: forward BFS from selected roots (+ project/site/building/storey), then IfcStyledItem
whose styled item is kept (and its forward closure), then IfcRelAggregates among spatial elements.
Pass 2: rewrite header + kept lines."""
import re, sys, time, numpy as np, array
from scipy.sparse import csr_matrix
src, dst = sys.argv[1], sys.argv[2]
KEEP_TYPES = {"IFCSLAB","IFCWALLSTANDARDCASE","IFCWALL","IFCCOLUMN","IFCBEAM","IFCMEMBER","IFCPLATE","IFCROOF",
              "IFCSTAIR","IFCSTAIRFLIGHT","IFCRAILING","IFCCOVERING","IFCFLOWSEGMENT","IFCFLOWFITTING","IFCFLOWCONTROLLER"}
PROXY_KEEP_PREFIX = ("Toposolid","Air Slab","OP1","825x1450","1725x1450","1000x1450")
SPATIAL = {"IFCPROJECT","IFCSITE","IFCBUILDING","IFCBUILDINGSTOREY"}
ent_re = re.compile(rb"^#(\d+)=([A-Z0-9]+)\(")
ref_re = re.compile(rb"#(\d+)")
t=time.time()
ids=array.array("i"); tcode=array.array("h"); types={}; tlist=[]
rs=array.array("i"); rd=array.array("i")
roots=[]; styled=[]; rel_aggr=[]; spatial=[]
proxy_re = re.compile(rb"^#\d+=IFCBUILDINGELEMENTPROXY\('[^']*',#\d+,'([^:']*)")
n=0; maxid=0
with open(src,"rb") as f:
    in_data=False
    for line in f:
        if not in_data:
            if line.startswith(b"DATA;"): in_data=True
            continue
        m=ent_re.match(line)
        if not m: continue
        i=int(m.group(1)); ty=m.group(2).decode()
        if ty not in types: types[ty]=len(tlist); tlist.append(ty)
        ids.append(i); tcode.append(types[ty]); maxid=max(maxid,i)
        for r in ref_re.findall(line[m.end():]):
            rs.append(i); rd.append(int(r))
        if ty in KEEP_TYPES: roots.append(i)
        elif ty=="IFCBUILDINGELEMENTPROXY":
            pm=proxy_re.match(line)
            if pm and pm.group(1).decode().startswith(PROXY_KEEP_PREFIX): roots.append(i)
        elif ty in SPATIAL: spatial.append(i)
        elif ty=="IFCSTYLEDITEM": styled.append(i)
        elif ty=="IFCRELAGGREGATES": rel_aggr.append(i)
        n+=1
        if n%500000==0: print("  parsed %d entities %.0fs"%(n,time.time()-t),flush=True)
print("pass1: %d entities, %d refs, maxid %d, roots %d, %.0fs"%(n,len(rs),maxid,len(roots),time.time()-t),flush=True)
N=maxid+1
A=csr_matrix((np.ones(len(rs),dtype=np.int8),(np.frombuffer(rs,dtype=np.int32),np.frombuffer(rd,dtype=np.int32))),shape=(N,N))
del rs, rd
def closure(seed, keep):
    frontier=np.array(sorted(set(seed)),dtype=np.int64); frontier=frontier[~keep[frontier]]
    keep[frontier]=True
    while len(frontier):
        nxt=np.unique(A[frontier].indices); nxt=nxt[~keep[nxt]]; keep[nxt]=True; frontier=nxt
keep=np.zeros(N,dtype=bool)
closure(roots+spatial, keep)
print("after roots closure: %d kept"%keep.sum(),flush=True)
# styled items whose target (first ref) is kept
st=np.array(styled,dtype=np.int64); tgt=[]
for s in st:
    r=A[s].indices                      # sorted column ids, not attribute order
    if len(r) and keep[r].any(): tgt.append(s)
closure(tgt, keep)
print("after styled items: %d kept (+%d styled)"%(keep.sum(),len(tgt)),flush=True)
# spatial aggregation rels whose refs are all kept
ok=[r for r in rel_aggr if keep[A[r].indices].all()]
keep[np.array(ok,dtype=np.int64)]=True
print("rel aggregates kept: %d ; total kept %d of %d"%(len(ok),keep.sum(),n),flush=True)
# pass 2
with open(src,"rb") as f, open(dst,"wb") as o:
    in_data=False; w=0
    for line in f:
        if not in_data:
            o.write(line)
            if line.startswith(b"DATA;"): in_data=True
            continue
        m=ent_re.match(line)
        if m:
            if keep[int(m.group(1))]: o.write(line); w+=1
        else: o.write(line)
print("wrote %s: %d entities, %.0fs total"%(dst,w,time.time()-t))
import collections
c=collections.Counter(tlist[tcode[k]] for k in range(len(ids)) if keep[ids[k]])
print("kept products:",{k:v for k,v in c.items() if k.startswith("IFC") and (k in KEEP_TYPES or k=="IFCBUILDINGELEMENTPROXY")})
