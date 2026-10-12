"""Per-segment flow direction for every network ('+' = start->end, '-' = reversed).
 trunk water : WaterGEMS flow arrows (segments were oriented to the arrows at build time) -> all '+'; raw main intake->WTP '+'
 block water : shortest-path tree from the block's feed point = block vertex nearest its nearest WDC tapping node (ASSUMED feed)
 sewer/storm : gravity, from the higher to the lower design invert (REAL)
 reuse/power : unchanged (drawn direction)"""
import json, numpy as np, collections, heapq, sys
from scipy.spatial import cKDTree
APP=sys.argv[1]
A=open(APP,encoding="utf8").read(); L=A.split("\n")
bi=[k for k,x in enumerate(L) if x.startswith("const BLK=")][0]
blk=json.loads(L[bi][len("const BLK="):].rstrip(";")); T=blk["TRUNK"]
taps=[n for n in T["nodes"] if "Tapping point" in n.get("desc","") or n["sid"].startswith("WDC")]
TP=np.array([[n["E"],n["N"]] for n in taps]); ttree=cKDTree(TP)
rep={"blocks":0,"water_segs":0,"water_rev":0,"components":0,"sewer_segs":0,"sewer_rev":0,"strom_segs":0,"strom_rev":0,"flat":0}
feeds={}
def graph(S,tol=0.3):
    P=np.vstack([S[:,0:2],S[:,3:5]]); t=cKDTree(P); g=t.query_ball_point(P,tol); nid=-np.ones(len(P),dtype=int); k=0
    for i,gg in enumerate(g):
        if nid[i]<0:
            for j in gg: nid[j]=k
            k+=1
    return nid[:len(S)],nid[len(S):],k,P
for code,N in blk.items():
    fd={}
    if code=="TRUNK":
        fd["water"]="+"*len(N["networks"]["water"]); N["fdir"]=fd; continue
    cE,cN=N["meta"]["center_E"],N["meta"]["center_N"]
    W=N["networks"].get("water",[])
    if W:
        S=np.array(W,dtype=float); a,b,k,P=graph(S)
        pos=np.zeros((k,2)); pos[a]=S[:,0:2]; pos[b]=S[:,3:5]
        Ln=np.hypot(S[:,3]-S[:,0],S[:,4]-S[:,1])
        adj=collections.defaultdict(list)
        for i in range(len(S)): adj[a[i]].append((b[i],Ln[i])); adj[b[i]].append((a[i],Ln[i]))
        d,j=ttree.query(pos+[cE,cN]); wdc=taps[j[d.argmin()]]; wE,wN=wdc["E"],wdc["N"]
        dist=np.full(k,np.inf); comp=-np.ones(k,dtype=int); nc=0
        # every connected component gets its own feed: its vertex nearest the block's WDC
        dw=np.hypot(pos[:,0]+cE-wE,pos[:,1]+cN-wN)
        for start in np.argsort(dw):
            if comp[start]>=0: continue
            # flood the component, then Dijkstra from its vertex nearest the WDC
            st=[start]; comp[start]=nc; members=[start]
            while st:
                x=st.pop()
                for y,_ in adj[x]:
                    if comp[y]<0: comp[y]=nc; st.append(y); members.append(y)
            src=min(members,key=lambda m:dw[m]); dist[src]=0; pq=[(0.0,src)]
            while pq:
                dd,x=heapq.heappop(pq)
                if dd>dist[x]: continue
                for y,w in adj[x]:
                    if dd+w<dist[y]: dist[y]=dd+w; heapq.heappush(pq,(dd+w,y))
            if nc==0: feeds[code]={"wdc":wdc["sid"],"E":round(float(pos[src,0]+cE),2),"N":round(float(pos[src,1]+cN),2),"dist_m":round(float(dw[src]),1)}
            nc+=1
        s="".join("+" if dist[a[i]]<=dist[b[i]] else "-" for i in range(len(S)))
        fd["water"]=s; rep["water_segs"]+=len(s); rep["water_rev"]+=s.count("-"); rep["components"]+=nc; rep["blocks"]+=1
    for u in ("sewer","strom"):
        U=N["networks"].get(u,[])
        if U:
            s="".join("-" if q[5]>q[2]+1e-6 else "+" for q in U)
            rep[u+"_segs"]+=len(s); rep[u+"_rev"]+=s.count("-"); rep["flat"]+=sum(1 for q in U if abs(q[5]-q[2])<1e-6)
            fd[u]=s
    N["fdir"]=fd
    if code in feeds: N["meta"]["feed"]=feeds[code]
L[bi]="const BLK="+json.dumps(blk,separators=(",",":"))+";"
open(APP+".fdir.tmp","w",encoding="utf8").write("\n".join(L))
json.dump(feeds,open("block_feeds.json","w"),indent=0)
print(json.dumps(rep,indent=1)); print("feeds:",len(feeds)); print(list(feeds.items())[:3])
