#!/usr/bin/env python3
"""Apply the UTILITIES.xlsx manhole design standards to every block:
 - STORM: parse 'SMH WxL' from description -> true access-shaft dims (fixes 1.2 m default guesses)
 - POWER: parse '(LxW)' / infer from standards types 13-18 (fixes generic 2.4 m boxes)
 - SEWER: types A-D by description or by depth where dims are off-standard; validation report
Only nodes carrying fallback/guessed dimensions are changed; measured dims are left alone."""
import json, re, glob, os
from collections import Counter

# ---- the standards from UTILITIES.xlsx ----
STD = {
  'sewer_types': {'A':{'dia':0.9,'h':1.65},'B':{'dia':1.2,'h':2.29},
                  'C':{'dia':1.5,'h':5.0},'D':{'dia':1.8,'h':8.0}},
  'power_L': [2.2,2.5,3.0,3.75],          # standard chamber lengths
  'power_W_main': 2.2,                     # types 13-16
  'power_W_row17': 1.25, 'power_W_row18': 1.3,
  'storm_shafts': [[0.6,1.2],[0.75,1.2]],  # access shaft W x L
  'storm_inlet': [0.6,0.6],
}
json.dump(STD, open('manhole_standards.json','w'), indent=1)

CH = Counter(); VAL = Counter()

def snapL(x):
    return min(STD['power_L'], key=lambda s: abs(s-x))

def enrich(nodes):
    for n in nodes:
        u=n['u']; desc=str(n.get('desc','') or '')
        dia=n['dia']; ln=n.get('len',0)
        if u=='strom':
            if not (dia in (1.2,2.4) or ln==0): continue
            m=re.search(r'([\d.]+)\s*[Xx×]\s*([\d.]+)', desc)
            if m:
                a,b=float(m.group(1)),float(m.group(2))
                if 0.3<=min(a,b)<=2 and max(a,b)<=3:
                    n['dia']=round(min(a,b),3); n['len']=round(max(a,b),3); CH['strom']+=1
            elif 'INLET' in desc.upper() or desc.upper().startswith('IC'):
                n['dia'],n['len']=STD['storm_inlet']; CH['strom_inlet']+=1
        elif u=='power':
            if not (dia==2.4 and ln==0): continue
            m=re.search(r'([\d.]+)\s*[Xx×]\s*([\d.]+)', desc)
            if m:
                a,b=float(m.group(1)),float(m.group(2))
                n['dia']=round(min(a,b),3); n['len']=round(max(a,b),3); CH['power_exact']+=1
            else:
                m2=re.search(r'\(\s*([\d.]+)', desc)
                L=snapL(float(m2.group(1))) if m2 else 2.5
                W=STD['power_W_row17'] if '1.25' in desc else STD['power_W_main']
                n['dia']=W; n['len']=L; CH['power_inferred']+=1
        elif u=='sewer':
            mt=re.search(r'TYPE[\s-]*([ABCD])\b', desc.upper())
            std_dias={v['dia'] for v in STD['sewer_types'].values()}
            if mt:
                t=mt.group(1); sd=STD['sewer_types'][t]['dia']
                depth=n['rim']-n['inv']
                if depth > STD['sewer_types'][t]['h']+0.7: VAL[f'sewer_{t}_too_deep']+=1
                if abs(dia-sd)>0.05 and not any(abs(dia-x)<=0.05 for x in std_dias):
                    n['dia']=sd; CH['sewer_typed']+=1
            elif not any(abs(dia-x)<=0.05 for x in std_dias):
                depth=n['rim']-n['inv']
                for t in 'ABCD':
                    if depth <= STD['sewer_types'][t]['h']+0.6:
                        n['dia']=STD['sewer_types'][t]['dia']; CH['sewer_by_depth']+=1; break
                else:
                    n['dia']=STD['sewer_types']['D']['dia']; CH['sewer_by_depth']+=1
    return nodes

def patch_html(path):
    h=open(path).read()
    m=re.search(r'const NET\s*=\s*(\{.*?\});', h, re.S)
    if not m: return False
    net=json.loads(m.group(1))
    if not net.get('nodes'): return False
    enrich(net['nodes'])
    for nd in net['nodes']: nd.pop('_g', None)
    compact=json.dumps(net, separators=(',',':'))
    h2=h[:m.start()]+'const NET='+compact+';'+h[m.end():]
    open(path,'w').write(h2)
    return True

# ---- pass 1: zone5pkg individual blocks (authoritative counts) ----
man=json.load(open('zone5pkg/Amaravati_Twins/manifest.json'))
patched=0
for m in man:
    p=f"zone5pkg/Amaravati_Twins/blocks/AmaravatiTwin_{m['code']}.html"
    if patch_html(p): patched+=1
print(f"individual blocks patched: {patched}")
print("changes:")
for k,v in sorted(CH.items()): print(f"  {k}: {v} nodes")
print("validation flags:", dict(VAL) if VAL else "none")
# ---- pass 2: everything else (zone files, webapp mirror, data_json) ----
CH.clear(); VAL.clear()
done={f"zone5pkg/Amaravati_Twins/blocks/AmaravatiTwin_{m['code']}.html" for m in man}
extra=0
for d in ['zone5pkg/Amaravati_Twins/blocks',
          'restore/Amaravati_DigitalTwin_FullPackage/webapp/blocks']:
    for p in sorted(glob.glob(os.path.join(d,'AmaravatiTwin_*.html'))):
        if p in done: continue
        if patch_html(p): extra+=1
for p in glob.glob('restore/Amaravati_DigitalTwin_FullPackage/datasets/data_json/*_network.json'):
    net=json.load(open(p))
    if net.get('nodes'):
        enrich(net['nodes'])
        json.dump(net, open(p,'w'), separators=(',',':'))
        extra+=1
print(f"mirrors/zone/data_json files updated: {extra}")
