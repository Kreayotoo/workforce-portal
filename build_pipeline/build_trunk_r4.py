#!/usr/bin/env python3
"""2058_R4_bypass.dxf (WaterGEMS export) -> trunk_network.json, same schema as the RINGMAIN build.
REAL from the DXF: pipe geometry, ID/diameter/length labels, flow arrows, node positions/IDs,
junction invert levels (IL:) and pressures (Pr:). Carried over by node ID from the previous
revision: the 76 tapping-point demands (not present in either DXF). Hydraulics re-run in EPANET."""
import ezdxf, json, math, re, sys, collections, copy
import numpy as np
from scipy.spatial import cKDTree
from pyproj import Transformer

DXF  = "/mnt/user-data/uploads/2058_R4_bypass.dxf"
OLD  = json.load(open("pkg/Amaravati_DigitalTwin_FullPackage/server/trunk_network.json"))
OUT  = "trunk_r4.json"
CE, CN = OLD["meta"]["center_E"], OLD["meta"]["center_N"]          # keep the scene origin
COVER = 2.7                                                          # rim = IL + cover (previous convention)
to_wgs = Transformer.from_crs("EPSG:32644", "EPSG:4326", always_xy=True)
doc = ezdxf.readfile(DXF); msp = doc.modelspace()
rep = {}

# ───────────────────────── 1. pipes + labels ─────────────────────────
polys = []                                    # [(x,y),...] per pipe
for e in msp:
    if e.dxftype() == "POLYLINE" and e.dxf.layer == "pipe":
        v = [(p.dxf.location.x, p.dxf.location.y) for p in e.vertices]
        v = [q for i, q in enumerate(v) if i == 0 or q != v[i-1]]
        if len(v) >= 2: polys.append(v)
def cum(v):
    c = [0.0]
    for a, b in zip(v, v[1:]): c.append(c[-1] + math.hypot(b[0]-a[0], b[1]-a[1]))
    return c
def point_at(v, c, s):
    for i in range(len(c)-1):
        if s <= c[i+1]:
            t = 0 if c[i+1] == c[i] else (s-c[i])/(c[i+1]-c[i])
            return (v[i][0]+(v[i+1][0]-v[i][0])*t, v[i][1]+(v[i+1][1]-v[i][1])*t)
    return v[-1]
plen = [cum(v) for v in polys]
mids = np.array([point_at(v, c, c[-1]/2) for v, c in zip(polys, plen)])
mtree = cKDTree(mids)
lab = {"ID": [None]*len(polys), "D": [None]*len(polys), "L": [None]*len(polys)}
unassigned = 0
for e in msp:
    if e.dxftype() == "TEXT" and e.dxf.layer == "pipe":
        t = e.dxf.text.strip(); m = re.match(r"(ID|D|L):\s*([\d,]+(?:\.\d+)?)", t)
        if not m: continue
        k = m.group(1); val = float(m.group(2).replace(",", ""))
        d, i = mtree.query([e.dxf.insert.x, e.dxf.insert.y], k=8)
        placed = False
        for dd, ii in zip(d, i):                       # nearest free slot within 80 m
            if dd < 80 and lab[k][ii] is None: lab[k][ii] = val; placed = True; break
        if not placed: unassigned += 1
rep["pipes"] = len(polys); rep["labels_unassigned"] = unassigned
rep["pipes_missing_labels"] = {k: sum(1 for x in v if x is None) for k, v in lab.items()}
# length label vs geometry
dev = [abs(lab["L"][i] - plen[i][-1]) for i in range(len(polys)) if lab["L"][i]]
rep["length_label_vs_geom_m"] = {"median": round(float(np.median(dev)), 2), "p95": round(float(np.percentile(dev, 95)), 2), "max": round(max(dev), 2)}

# flow arrows: direction of the arrow nearest each pipe midpoint
arrows = [(e.dxf.insert.x, e.dxf.insert.y, math.radians(e.dxf.rotation)) for e in msp
          if e.dxftype() == "INSERT" and e.dxf.name == "FLOWARROW"]
atree = cKDTree(np.array([[a[0], a[1]] for a in arrows]))
flow_dir = [0]*len(polys)                     # +1 = polyline order, -1 = reversed
for i, (v, c) in enumerate(zip(polys, plen)):
    d, j = atree.query(mids[i]); 
    if d > 40: continue
    ax, ay = math.cos(arrows[j][2]), math.sin(arrows[j][2])
    p0 = point_at(v, c, max(0, c[-1]/2-5)); p1 = point_at(v, c, min(c[-1], c[-1]/2+5))
    tx, ty = p1[0]-p0[0], p1[1]-p0[1]
    flow_dir[i] = 1 if (ax*tx+ay*ty) >= 0 else -1
rep["flow_arrows_matched"] = sum(1 for f in flow_dir if f)
# orient every polyline in the WaterGEMS flow direction, so EPANET "+" = arrow direction
for i, f in enumerate(flow_dir):
    if f == -1: polys[i] = polys[i][::-1]; plen[i] = cum(polys[i])

# ───────────────────────── 2. nodes + labels ─────────────────────────
ins = [(e.dxf.name, e.dxf.insert.x, e.dxf.insert.y) for e in msp if e.dxftype() == "INSERT" and e.dxf.layer == "node"]
itree = cKDTree(np.array([[a[1], a[2]] for a in ins]))
ntext = [dict(name=n, x=x, y=y, id=None, IL=None, Pr=None) for n, x, y in ins]
# WaterGEMS places each label at a fixed offset from its symbol; match on that, not "nearest"
OFF = {("FILLED_CIRCLE","ID"):(0.5,0.5), ("FILLED_CIRCLE","IL"):(0.5,-1.0), ("FILLED_CIRCLE","Pr"):(0.5,-2.0),
       ("AIRVALVE","ID"):(6.0,2.44), ("VALVETCV","ID"):(2.44,2.44), ("PUMP","ID"):(2.44,2.44),
       ("RESERVOIR","ID"):(2.44,2.44), ("XINCIRCLE","ID"):(2.44,2.44)}
il_zero = []
for e in msp:
    if e.dxftype() == "TEXT" and e.dxf.layer == "node":
        t = e.dxf.text.strip(); tx, ty = e.dxf.insert.x, e.dxf.insert.y
        m = re.match(r"(IL|Pr):\s*([\d.]+|\(N/A\))", t)
        kind = m.group(1) if m else "ID"
        # candidate symbols: those whose fixed offset lands on this text
        best = None
        for (blk, kk), (ox, oy) in OFF.items():
            if kk != kind: continue
            d, j = itree.query([tx-ox, ty-oy])
            if d < 0.08 and ins[j][0] == blk and (best is None or d < best[0]): best = (d, j)
        if best is None:
            d, j = itree.query([tx, ty])                # fall back to nearest, tight
            if d > 3.0: continue
            best = (d, j)
        j = best[1]
        if m:
            if m.group(2).startswith("("): continue
            v = float(m.group(2))
            if kind == "IL" and v == 0.0: il_zero.append((tx, ty)); continue      # unset elevation in the model
            ntext[j][kind] = v
        else:
            if ntext[j]["id"] is None or len(t) > len(ntext[j]["id"]): ntext[j]["id"] = t
rep["IL_zero_ignored"] = len(il_zero)
rep["nodes_in_dxf"] = len(ntext)
rep["junctions_with_IL"] = sum(1 for n in ntext if n["IL"] is not None)
rep["nodes_by_block"] = dict(collections.Counter(n["name"] for n in ntext))

# ── node graph: polyline ends snap to symbols (0.5 m); levels propagate along pipes ──
sym_tree = cKDTree(np.array([[n["x"], n["y"]] for n in ntext]))
adj = collections.defaultdict(list)                   # node index -> [(neighbour index, length)]
end_node = []                                         # per polyline: (start node idx, end node idx)
for v, c in zip(polys, plen):
    da, a = sym_tree.query(v[0]); db, b = sym_tree.query(v[-1])
    a = a if da <= 0.5 else None; b = b if db <= 0.5 else None
    end_node.append((a, b))
    if a is not None and b is not None and a != b:
        adj[a].append((b, c[-1])); adj[b].append((a, c[-1]))
known = {i: n["IL"] for i, n in enumerate(ntext) if n["IL"] is not None}
il = dict(known)
for _ in range(60):                                   # inverse-length weighted relaxation
    ch = 0
    for i in range(len(ntext)):
        if i in known or not adj[i]: continue
        w = [(il[j], 1.0/max(1.0, L)) for j, L in adj[i] if j in il]
        if not w: continue
        v = sum(a*b for a, b in w)/sum(b for a, b in w)
        if i not in il or abs(il[i]-v) > 1e-3: il[i] = v; ch += 1
    if not ch: break
rep["nodes_with_IL_after_propagation"] = len(il)
def il_at(x, y, r=1.5):
    d, j = sym_tree.query([x, y])
    return (il[j], d) if (d <= r and j in il) else (None, d)

# ───────────────────────── 3. segments with inverts ──────────────────
segs, dims, geo, seg_of_poly = [], [], [], []
no_il_ends = 0
for i, (v, c) in enumerate(zip(polys, plen)):
    ia, da = il_at(*v[0]); ib, db = il_at(*v[-1])
    if ia is None and ib is None:                       # neither end labelled: nearest IL within 60 m
        ia = il_at(*v[0], 60)[0] or il_at(*v[-1], 60)[0] or 23.0; ib = ia; no_il_ends += 1
    elif ia is None: ia = ib; no_il_ends += 1
    elif ib is None: ib = ia; no_il_ends += 1
    dia = lab["D"][i] or 600.0
    first = len(segs)
    for k in range(len(v)-1):
        ta, tb = c[k]/c[-1], c[k+1]/c[-1]
        za, zb = ia + (ib-ia)*ta, ia + (ib-ia)*tb
        (xs, ys), (xe, ye) = v[k], v[k+1]
        segs.append([round(xs-CE, 2), round(ys-CN, 2), round(za, 2), round(xe-CE, 2), round(ye-CN, 2), round(zb, 2)])
        dims.append([0, int(round(dia)), int(round(dia))])
        slon, slat = to_wgs.transform(xs, ys); elon, elat = to_wgs.transform(xe, ye)
        geo.append([round(slat, 6), round(slon, 6), round(elat, 6), round(elon, 6)])
    seg_of_poly.append((first, len(segs)))
rep["segments"] = len(segs); rep["polylines_with_an_unlabelled_end"] = no_il_ends

# ───────────────────────── 4. named nodes ────────────────────────────
old_by_id = {}
def norm(s): return re.sub(r"\s+", "", s.upper())
for n in OLD["nodes"]: old_by_id[norm(n["sid"])] = n
old_demand = {norm(n["sid"]): float(re.search(r"demand ([\d.]+)", n["desc"]).group(1))
              for n in OLD["nodes"] if "demand" in n.get("desc", "")}
# fallback demand key: just the WDC-nn / J-nnn token
old_demand_tok = {}
for k, v in old_demand.items():
    m = re.match(r"(WDC-?\d+[A-Z]?|J-\d+)", k)
    if m: old_demand_tok.setdefault(m.group(1), v)

seg_ends = np.array([[s[0]+CE, s[1]+CN] for s in segs] + [[s[3]+CE, s[4]+CN] for s in segs])
end_tree = cKDTree(seg_ends)
def seg_inv_near(x, y):
    d, j = end_tree.query([x, y]); s = segs[j % len(segs)]; return s[2] if j < len(segs) else s[5]
KIND = [("R-", "R"), ("INTAKE", "INTAKE"), ("PMP", "PMP"), ("AV-", "AV"), ("TCV", "TCV"), ("TCMS", "TCMS"),
        ("SV", "SV"), ("WDC", "WDC"), ("J-", "J")]
nodes, matched, unmatched_demand, carried = [], 0, [], 0
for n in ntext:
    sid = n["id"]
    if not sid: continue
    kind = next((k for p, k in KIND if sid.upper().startswith(p)), None)
    if kind is None or (kind == "J" and n["name"] != "FILLED_CIRCLE" and n["name"] != "XINCIRCLE"):
        if kind is None: continue
    x, y = n["x"], n["y"]
    inv = n["IL"] if n["IL"] is not None else round(seg_inv_near(x, y), 2)
    lon, lat = to_wgs.transform(x, y)
    deg = int(len(end_tree.query_ball_point([x, y], 1.0)))
    base = {"u": "water", "sid": sid, "x": round(x-CE, 2), "z": round(y-CN, 2), "coneH": 0, "rot": 0, "pipes": "",
            "lat": round(lat, 6), "lon": round(lon, 6), "E": round(x, 3), "N": round(y, 3),
            "inv": inv, "rim": round(inv+COVER, 2), "frl": round(inv+COVER, 2), "len": 0, "mh": True, "deg": max(1, deg)}
    old = old_by_id.get(norm(sid))
    if kind in ("R", "INTAKE", "PMP"):
        if old and old.get("inv") is not None: inv, rim = old["inv"], old["rim"]; carried += 1
        else: inv, rim = (round(inv, 2), round(inv + (8.0 if kind != "PMP" else 5.0), 2))
        base.update(inv=inv, rim=rim, frl=rim, dia=10 if kind != "PMP" else 5, neck=1 if kind != "PMP" else 0.5,
                    shape="cyl" if kind != "PMP" else "box", real=1,
                    desc={"R": "Source reservoir / headworks", "INTAKE": "Raw water intake", "PMP": "Pumping station"}[kind])
    elif kind in ("AV", "TCV", "TCMS", "SV"):
        base.update(dia=1.2, neck=0.4, shape="", real=0,
                    desc={"AV": "Line valve (AV)", "TCV": "Line valve (TCV)", "TCMS": "Control valve (TCMS)", "SV": "Line valve (SV)"}[kind])
    else:                                                        # WDC / J tapping points
        dem = old_demand.get(norm(sid))
        if dem is None:
            m = re.match(r"(WDC-?\d+[A-Z]?|J-\d+)", norm(sid)); dem = old_demand_tok.get(m.group(1)) if m else None
        if dem is not None: matched += 1; desc = "Tapping point \u00b7 demand %.1f MLD" % dem
        else: unmatched_demand.append(sid); desc = "Tapping point \u00b7 demand pending"
        base.update(dia=2.6, neck=0.5, shape="cyl", real=1, desc=desc)
        if n["Pr"] is not None: base["press"] = n["Pr"]; base["hgl"] = round(inv + n["Pr"], 2)
    nodes.append(base)
rep["nodes_kept"] = len(nodes); rep["nodes_by_kind"] = dict(collections.Counter(re.sub(r"[\d\s(].*", "", n["sid"]).strip("-") for n in nodes))
rep["demands_matched"] = matched; rep["demands_unmatched"] = unmatched_demand
rep["demand_total_MLD"] = round(sum(float(re.search(r"demand ([\d.]+)", n["desc"]).group(1)) for n in nodes if "MLD" in n["desc"]), 1)
rep["reservoir_pump_levels_carried_from_R3"] = carried

# ───────────────────────── 5. assemble ───────────────────────────────
length = sum(math.hypot(s[3]-s[0], s[4]-s[1]) for s in segs)
dia_l = [d[1] for d in dims]; inv_l = [s[2] for s in segs] + [s[5] for s in segs]
NET = copy.deepcopy(OLD)
NET["meta"] = {"zone": "", "block": "", "grid": "44N", "center_E": CE, "center_N": CN, "aboveground": False}
NET["stats"] = {"water": {"label": "Trunk + Ring Main", "count": len(polys), "segments": len(segs), "length_m": round(length, 1),
                          "avg_dia": int(round(sum(dia_l)/len(dia_l))), "max_dia": max(dia_l), "min_dia": min(dia_l),
                          "min_inv": round(min(inv_l), 2), "max_inv": round(max(inv_l), 2)}}
NET["networks"] = {"water": segs, "sewer": [], "strom": [], "reuse": [], "power": []}
NET["dims"] = {"water": dims, "sewer": [], "strom": [], "reuse": [], "power": []}
NET["geo"] = {"water": geo, "sewer": [], "strom": [], "reuse": [], "power": []}
NET["nodes"] = nodes; NET["nodes_src"] = "RINGMAIN R4 bypass (WaterGEMS · 2058_R4_bypass.dxf)"; NET["nodes_frl"] = True
NET["frl"] = {"level": 23.37, "note": "transmission corridor", "src": "RINGMAIN tables"}
NET["map"] = None; NET["road"] = None; NET["hydw"] = []
NET["revision"] = {"id": "R4 bypass", "source": "2058_R4_bypass.dxf", "built": "2026-09-09",
                   "replaces": "RINGMAIN (Trunk_Model.dxf)", "pipe_ids": [lab["ID"][i] for i in range(len(polys))],
                   "seg_of_poly": seg_of_poly}
json.dump(NET, open(OUT, "w"), separators=(",", ":"))
rep["stats"] = NET["stats"]["water"]
print(json.dumps(rep, indent=1))
