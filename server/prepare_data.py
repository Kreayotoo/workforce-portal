#!/usr/bin/env python3
"""
Prepare static data for the FastAPI server.
Run once (or after any network data update):
  python3 prepare_data.py

Reads from your existing twin build outputs and
writes lightweight JSON files into server/static/
"""
import json, re, os, math, glob, shutil
from pyproj import Transformer

BASE   = os.path.dirname(__file__)
STATIC = os.path.join(BASE, 'static')
BDIR   = os.path.join(STATIC, 'blocks')
DDIR   = os.path.join(STATIC, 'data')
os.makedirs(BDIR, exist_ok=True)
os.makedirs(DDIR, exist_ok=True)

# ── locate source files ───────────────────────────────────────────────
PARENT  = os.path.dirname(BASE)
ZONE_DIR = os.path.join(PARENT, 'zone5pkg', 'Amaravati_Twins')
RESTORE  = os.path.join(PARENT, 'restore', 'Amaravati_DigitalTwin_FullPackage')

def find_manifest():
    for d in [ZONE_DIR, os.path.join(RESTORE,'webapp'), RESTORE]:
        p = os.path.join(d, 'manifest.json')
        if os.path.exists(p): return p, d
    return None, None

def find_block_html(code, zone_dir):
    p = os.path.join(zone_dir, 'blocks', f'AmaravatiTwin_{code}.html')
    if os.path.exists(p): return p
    for d in [RESTORE]:
        p2 = os.path.join(d, 'webapp', 'blocks', f'AmaravatiTwin_{code}.html')
        if os.path.exists(p2): return p2
    return None

def extract_net(html_path):
    h = open(html_path).read()
    m = re.search(r'const NET\s*=\s*(\{.*?\});', h, re.S)
    return json.loads(m.group(1)) if m else None

# ── 1. manifest ───────────────────────────────────────────────────────
mpath, zdir = find_manifest()
if not mpath:
    print("ERROR: manifest.json not found. Run from the project directory."); exit(1)
man = json.load(open(mpath))
shutil.copy(mpath, os.path.join(DDIR, 'manifest.json'))
print(f"manifest: {len(man)} blocks")

# ── 2. per-block network JSON (split from HTML) ───────────────────────
ok = 0
for m in man:
    bp = find_block_html(m['code'], zdir)
    if not bp:
        print(f"  [skip] {m['code']} — HTML not found"); continue
    net = extract_net(bp)
    if not net:
        print(f"  [skip] {m['code']} — NET not found"); continue
    json.dump(net, open(os.path.join(BDIR, f"{m['code']}.json"), 'w'), separators=(',',':'))
    ok += 1
print(f"block JSONs: {ok}/{len(man)} written to static/blocks/")

# ── 3. plots.json (95k plot centroids + coordinate transform) ─────────
src_plots = os.path.join(PARENT, 'plots.json')
if not os.path.exists(src_plots):
    src_plots = os.path.join(RESTORE, 'datasets', 'decision', 'plots.json')
if os.path.exists(src_plots):
    shutil.copy(src_plots, os.path.join(DDIR, 'plots.json'))
    p = json.load(open(src_plots))
    print(f"plots.json: {len(p['dx'])} plots copied")
else:
    print("plots.json not found — buffer analysis will be unavailable")

# ── 4. incident_net.json (78k pipes + 43k chambers) ──────────────────
src_net = os.path.join(PARENT, 'incident_net.json')
if not os.path.exists(src_net):
    src_net = os.path.join(RESTORE, 'datasets', 'decision', 'incident_net.json')
if os.path.exists(src_net):
    shutil.copy(src_net, os.path.join(DDIR, 'incident_net.json'))
    n = json.load(open(src_net))
    print(f"incident_net.json: {len(n['pipes'])} pipes, {len(n['mh'])} chambers copied")
else:
    print("incident_net.json not found — buffer analysis will be unavailable")

# ── 5. zone_storm.json (Manning capacity per zone) ───────────────────
import sys
sys.path.insert(0, PARENT)
try:
    zone_storm = {}
    for m2 in man:
        bp2 = find_block_html(m2['code'], zdir)
        if not bp2: continue
        net2 = extract_net(bp2)
        if not net2: continue
        z = m2['zone']
        if z not in zone_storm:
            zone_storm[z] = {'count':0,'length_m':0,'area_m2':0,'capacity_m3s':0.0,'max_dia':0}
        segs = net2['networks'].get('strom', [])
        dm   = net2['dims'].get('strom', [])
        cE, cN = net2['meta']['center_E'], net2['meta']['center_N']
        Es, Ns = [], []
        for i,s in enumerate(segs):
            Es += [s[0]+cE, s[3]+cE]; Ns += [s[1]+cN, s[4]+cN]
            L = math.hypot(s[3]-s[0], s[4]-s[1])
            D = dm[i][1] if i < len(dm) else 300
            slope = abs(s[2]-s[5])/L if L > 0.5 else 0.0015
            S = max(slope, 0.0008)
            Dv = D/1000.0
            q = (1/0.014)*math.pi*Dv*Dv/4*(Dv/4)**(2/3)*S**0.5
            zone_storm[z]['capacity_m3s'] += q
            zone_storm[z]['count'] += 1
            zone_storm[z]['length_m'] += L
            if D > zone_storm[z]['max_dia']: zone_storm[z]['max_dia'] = D
        if Es: zone_storm[z]['area_m2'] = (max(Es)-min(Es))*(max(Ns)-min(Ns))
    for z in zone_storm:
        zone_storm[z]['capacity_m3s'] = round(zone_storm[z]['capacity_m3s'], 3)
        zone_storm[z]['length_m']     = round(zone_storm[z]['length_m'])
        zone_storm[z]['area_m2']      = round(zone_storm[z]['area_m2'])
    json.dump(zone_storm, open(os.path.join(DDIR, 'zone_storm.json'), 'w'), separators=(',',':'))
    print(f"zone_storm.json: {len(zone_storm)} zones with real Manning capacity")
except Exception as e:
    print(f"zone_storm: ERROR — {e}")

# ── 6. copy logo ──────────────────────────────────────────────────────
for lp in [os.path.join(PARENT,'logo_b64.txt'),
           os.path.join(RESTORE,'build_pipeline','logo_b64.txt')]:
    if os.path.exists(lp):
        import base64
        b64 = open(lp).read().strip()
        logo_bytes = base64.b64decode(b64)
        open(os.path.join(STATIC,'logo.png'),'wb').write(logo_bytes)
        print("logo.png written"); break

# ── summary ───────────────────────────────────────────────────────────
print("\n=== Data preparation complete ===")
for f in os.listdir(DDIR):
    sz = os.path.getsize(os.path.join(DDIR,f))
    print(f"  data/{f}: {sz//1024} KB")
print(f"  blocks/: {len(os.listdir(BDIR))} JSON files")
print("\nStart the server:  python3 -m uvicorn main:app --host 0.0.0.0 --port 8000")
