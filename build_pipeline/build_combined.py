#!/usr/bin/env python3
"""Merge per-block datasets into combined 3D twins: one per zone (all its blocks) + one whole-city (all zones)."""
import json, re, os
import numpy as np
from pyproj import Transformer

PKG='/home/claude/zone5pkg/Amaravati_Twins'; BLOCKS=PKG+'/blocks'
TPL=open('/home/claude/dashboard_template.html').read()
LOGO=open('/home/claude/logo_b64.txt').read().strip()
T=Transformer.from_crs(32644,4326,always_xy=True)
ORDER=['water','sewer','strom','reuse','power']
LABEL={'water':'Water','sewer':'Sewer','strom':'Storm','reuse':'Reuse','power':'Power'}
man=json.load(open(PKG+'/manifest.json'))

def load_net(code):
    h=open(f'{BLOCKS}/AmaravatiTwin_{code}.html').read()
    return json.loads(re.search(r'const NET\s*=\s*(\{.*?\});', h, re.S).group(1))

def merge(codes):
    nets=[load_net(c) for c in codes]
    Es=[];Ns=[]
    for net in nets:
        cE,cN=net['meta']['center_E'],net['meta']['center_N']
        for u in ORDER:
            for s in net['networks'].get(u,[]): Es+=[s[0]+cE,s[3]+cE]; Ns+=[s[1]+cN,s[4]+cN]
    CE=float(np.mean(Es)); CN=float(np.mean(Ns))
    networks={u:[] for u in ORDER}; dims={u:[] for u in ORDER}; geo={u:[] for u in ORDER}
    for net in nets:
        cE,cN=net['meta']['center_E'],net['meta']['center_N']
        for u in ORDER:
            segs=net['networks'].get(u,[]); dm=net['dims'].get(u,[]); gg=net['geo'].get(u,[])
            for i,s in enumerate(segs):
                networks[u].append([round(s[0]+cE-CE,2),round(s[1]+cN-CN,2),s[2],round(s[3]+cE-CE,2),round(s[4]+cN-CN,2),s[5]])
                dims[u].append(dm[i] if i<len(dm) else [0,200,200])
                geo[u].append(gg[i] if i<len(gg) else [0,0,0,0])
    nodes=[]
    for net in nets:
        cE,cN=net['meta']['center_E'],net['meta']['center_N']
        for n in net.get('nodes',[]):
            m=dict(n); m['x']=round(n['x']+cE-CE,2); m['z']=round(n['z']+cN-CN,2); nodes.append(m)
    stats={}
    for u in ORDER:
        segs=networks[u]; dias=[d[1] for d in dims[u]] if dims[u] else []
        invs=[s[2] for s in segs]+[s[5] for s in segs]
        length=sum(float(np.hypot(s[3]-s[0],s[4]-s[1])) for s in segs)
        stats[u]={'label':LABEL[u],'count':len(segs),'length_m':round(length,1),
          'avg_dia':int(np.mean(dias)) if dias else 0,'max_dia':int(max(dias)) if dias else 0,
          'min_dia':int(min(dias)) if dias else 0,'min_inv':round(min(invs),2) if invs else 0,'max_inv':round(max(invs),2) if invs else 0}
    lon0,lat0=T.transform(CE,CN); lonE,latE=T.transform(CE+1,CN); lonN,latN=T.transform(CE,CN+1)
    relx=[s[0] for u in ORDER for s in networks[u]]+[s[3] for u in ORDER for s in networks[u]]
    relz=[s[1] for u in ORDER for s in networks[u]]+[s[4] for u in ORDER for s in networks[u]]
    sw_lon,sw_lat=T.transform(CE+min(relx),CN+min(relz)); ne_lon,ne_lat=T.transform(CE+max(relx),CN+max(relz))
    return {'meta':{'zone':'','block':'','grid':'44N','center_E':round(CE,2),'center_N':round(CN,2),'aboveground':False,'combined':True},
      'stats':stats,'networks':networks,'geo':geo,'dims':dims,'nodes':nodes,'nodes_src':'combined multi-block view','nodes_frl':True,
      'frl':{'level':round(float(np.mean([n['rim'] for n in nodes])),2) if nodes else 25,'note':'combined view (no single surveyed road surface)','src':'combined'},
      'map':{'center':[round(lat0,6),round(lon0,6)],'bounds':[[round(sw_lat,6),round(sw_lon,6)],[round(ne_lat,6),round(ne_lon,6)]],
             'lonPerM_x':lonE-lon0,'latPerM_x':latE-lat0,'lonPerM_n':lonN-lon0,'latPerM_n':latN-lat0},'road':None}

def write_twin(NET, code, pill):
    html=TPL.replace('__NETDATA__',json.dumps(NET,separators=(',',':'))).replace('__LOGO__','data:image/png;base64,'+LOGO)
    html=html.replace('ZONE 1B · BLOCK 5 · GRID 44N', pill).replace('Z1B-B5 (44N)', code.replace('_','-')+' (44N)')
    fn=f'{BLOCKS}/AmaravatiTwin_{code}.html'; open(fn,'w').write(html)
    return fn, os.path.getsize(fn)

def _zkey(z):
    m=re.match(r'(\d+)(.*)',str(z)); return (int(m.group(1)),m.group(2)) if m else (999,str(z))

zones={}
for m in man:
    if m['code'].startswith('ZONE_') or m['code']=='CITY': continue
    zones.setdefault(m['zone'],[]).append(m['code'])
combined=[]
for zone in sorted(zones,key=_zkey):
    codes=zones[zone]
    NET=merge(codes)
    p=sum(NET['stats'][u]['count'] for u in ORDER); mh=len(NET['nodes']); km=round(sum(NET['stats'][u]['length_m'] for u in ORDER)/1000,2)
    fn,sz=write_twin(NET, f'ZONE_{zone}', f'ZONE {zone} · ALL BLOCKS')
    combined.append({'code':f'ZONE_{zone}','kind':'zone','zone':zone,'file':'blocks/'+os.path.basename(fn),
                     'pipes':p,'manholes':mh,'km':km,'blocks':len(codes)})
    print(f'  ZONE_{zone}: {len(codes)} blocks -> {p} pipes, {mh} MH ({sz//1024//1024} MB)')
allcodes=[m['code'] for m in man if not m['code'].startswith('ZONE_') and m['code']!='CITY']
city_codes=allcodes+(['TRUNK'] if os.path.exists(f'{BLOCKS}/AmaravatiTwin_TRUNK.html') else [])
NET=merge(city_codes)
p=sum(NET['stats'][u]['count'] for u in ORDER); mh=len(NET['nodes']); km=round(sum(NET['stats'][u]['length_m'] for u in ORDER)/1000,2)
fn,sz=write_twin(NET,'CITY','AMARAVATI · ALL ZONES')
combined.append({'code':'CITY','kind':'city','zone':'ALL','file':'blocks/'+os.path.basename(fn),
                 'pipes':p,'manholes':mh,'km':km,'blocks':len(allcodes)})
print(f'  CITY: {len(allcodes)} blocks -> {p} pipes, {mh} MH ({sz//1024//1024} MB)')
json.dump(combined, open(PKG+'/combined.json','w'), indent=1)
print('combined.json:', len(combined),'views')
