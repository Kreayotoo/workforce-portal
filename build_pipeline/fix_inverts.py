#!/usr/bin/env python3
"""Derive missing manhole inverts (inv<1) from connected pipe inverts. Fixes Zone 10 storm/power sumps."""
import json, re, glob, os
def get_net(fp): return json.loads(re.search(r'const NET\s*=\s*(\{.*?\});', open(fp).read(), re.S).group(1))
def fix_net(net):
    # index pipe endpoints -> inverts, per utility (0.1 m cells)
    idx={}
    for u,segs in net['networks'].items():
        d={}
        for s in segs:
            for x,y,inv in ((s[0],s[1],s[2]),(s[3],s[4],s[5])):
                if inv is None or inv<1: continue
                d.setdefault((round(x,1),round(y,1)),[]).append(inv)
        idx[u]=d
    fixed=0
    for n in net['nodes']:
        if n.get('inv') is None or n['inv']>=1: continue
        u=n['u']; d=idx.get(u,{}); x,z=n['x'],n['z']; cand=[]
        for dx in (-0.1,0,0.1):
            for dz in (-0.1,0,0.1):
                cand+=d.get((round(x+dx,1),round(z+dz,1)),[])
        if cand: n['inv']=round(min(cand),2)                         # sump = deepest connected pipe
        elif n.get('rim') is not None: n['inv']=round(n['rim']-2.0,2) # fallback typical depth
        fixed+=1
    return fixed
tot=0
for fp in glob.glob('zone5pkg/Amaravati_Twins/blocks/AmaravatiTwin_*.html'):
    if any(k in fp for k in ('ZONE','CITY','TRUNK')): continue
    try: net=get_net(fp)
    except: continue
    f=fix_net(net)
    if f:
        html=open(fp).read()
        html=re.sub(r'const NET\s*=\s*\{.*?\};', 'const NET='+json.dumps(net,separators=(',',':'))+';', html, count=1, flags=re.S)
        open(fp,'w').write(html); tot+=f
        print(f"  {os.path.basename(fp)}: fixed {f} node inverts")
print("total node inverts derived:", tot)
# verify Zone 10
net=get_net('zone5pkg/Amaravati_Twins/blocks/AmaravatiTwin_10_B3.html')
import statistics
d=[n['rim']-n['inv'] for n in net['nodes'] if n.get('inv') and n.get('rim')]
print("10_B3 manhole depth now: min=%.1f median=%.1f max=%.1f m"%(min(d),statistics.median(d),max(d)))
