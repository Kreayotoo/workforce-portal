# ═══════════════════════════════════════════════════════════════════════
#  HYDRAULICS — live EPANET (WNTR) service for the Trunk + Ring Main
#  Real: geometry, diameters, lengths, elevations, 76 tapping demands.
#  ASSUMED (until Tier-1 data): reservoir heads (from WaterGEMS HGL),
#  pumps bypassed, valves open, Hazen-Williams C=130. → UNCALIBRATED.
# ═══════════════════════════════════════════════════════════════════════
import os, re, json, math, time, copy

BASE = os.path.dirname(__file__)
_TRUNK = None
for cand in (os.path.join(BASE, "trunk_network.json"),
             os.path.join(BASE, "..", "datasets", "data_json", "Trunk_Main_network.json")):
    if os.path.exists(cand):
        _TRUNK = json.load(open(cand)); break

_model = None
_baseline = None
_base_ts = 0
ASSUMPTIONS = [
    "Reservoir heads taken from WaterGEMS HGL at source nodes (ASSUMED until R-1/2/3 operating levels supplied)",
    "Pumps bypassed — head is applied at the source (pump curves pending)",
    "All line/control valves fully open (TCV settings pending)",
    "Hazen-Williams C = 130 uniform (material-wise C on receipt of pipe schedule)",
    "Steady-state, single demand condition (real 76-point demands, 985 MLD scale)",
]

def _build():
    """Trunk JSON → WNTR network. Junction merge tolerance 0.10 m."""
    global _model
    import wntr
    segs = _TRUNK["networks"]["water"]; dims = _TRUNK["dims"]["water"]
    wn = wntr.network.WaterNetworkModel()
    wn.options.hydraulic.headloss = "H-W"
    jmap, jelev = {}, {}
    def jid(x, z, e):
        k = (round(x, 1), round(z, 1))
        if k not in jmap:
            jmap[k] = "J%d" % len(jmap); jelev[jmap[k]] = e
            wn.add_junction(jmap[k], base_demand=0.0, elevation=float(e))
        return jmap[k]
    for i, s in enumerate(segs):
        a = jid(s[0], s[1], s[2]); b = jid(s[3], s[4], s[5])
        L = max(0.5, math.hypot(s[3]-s[0], s[4]-s[1]))
        dia = max(0.05, float(dims[i][1]) / 1000.0)
        if a == b:  # zero-length artefact → no hydraulic link; results return zeros for this index
            continue
        wn.add_pipe("P%d" % i, a, b, length=L, diameter=dia, roughness=130)
    # demands from tapping-point nodes (desc: 'demand X MLD') → nearest junction
    total_mld = 0.0
    keys = list(jmap.keys())
    def nearest(x, z):
        best, bd = None, 1e9
        for k in keys:
            d = (k[0]-x)**2 + (k[1]-z)**2
            if d < bd: bd, best = d, k
        return jmap[best], math.sqrt(bd)
    for n in _TRUNK["nodes"]:
        m = re.search(r"demand\s+([\d.]+)\s*MLD", n.get("desc", "") or "")
        if m:
            mld = float(m.group(1)); total_mld += mld
            j, dist = nearest(n["x"], n["z"])
            if dist < 60:
                wn.get_node(j).demand_timeseries_list[0].base_value += mld * 1e6 / 86400 / 1000.0  # MLD→m3/s
    # reservoirs at R-x nodes (head = their HGL, else max tap HGL + 3 m)
    hgl_max = max([n.get("hgl") or 0 for n in _TRUNK["nodes"]] + [90.0])
    r_count = 0
    for n in _TRUNK["nodes"]:
        sid = str(n.get("sid", ""))
        if re.match(r"^R-\d", sid):
            j, dist = nearest(n["x"], n["z"])
            if dist < 120:
                head = float(n.get("hgl") or (hgl_max + 3.0))
                rn = "RES_" + sid.replace("-", "")
                wn.add_reservoir(rn, base_head=head)
                wn.add_pipe("PR_" + sid.replace("-", ""), rn, j, length=5,
                            diameter=2.0, roughness=140)
                r_count += 1
    # raw-water system: intake (source) -> WTP inlet (sink); hydraulically separate from treated water
    raw_mld = 0.0
    for n in _TRUNK["nodes"]:
        if n.get("source") == "raw":
            j, dist = nearest(n["x"], n["z"])
            if dist < 120:
                wn.add_reservoir("RES_INTAKE", base_head=float(n.get("head", (n.get("rim") or 30) + 3)))
                wn.add_pipe("PR_INTAKE", "RES_INTAKE", j, length=5, diameter=2.0, roughness=140)
                r_count += 1
        if n.get("sink_mld"):
            j, dist = nearest(n["x"], n["z"])
            if dist < 60:
                raw_mld += float(n["sink_mld"])
                wn.get_node(j).demand_timeseries_list[0].base_value += float(n["sink_mld"]) * 1e6 / 86400 / 1000.0
    if raw_mld:
        ASSUMPTIONS.append("Raw-water main intake \u2192 WTP inlet: %.1f MLD = 190 MLD plant + 5%% process losses; intake source head %.1f m (SIMULATED until intake pump duty supplied)"
                           % (raw_mld, max([float(n.get("head", 0)) for n in _TRUNK["nodes"] if n.get("source") == "raw"] or [0])))
    if r_count == 0:  # safety: feed at the junction with highest recorded HGL
        cand = max(_TRUNK["nodes"], key=lambda n: n.get("hgl") or 0)
        j, _ = nearest(cand["x"], cand["z"])
        wn.add_reservoir("RES_A", base_head=float(cand.get("hgl") or hgl_max) + 2)
        wn.add_pipe("PR_A", "RES_A", j, length=5, diameter=2.0, roughness=140)
        r_count = 1
    # ── connectivity repair: EPANET cannot solve islands ──
    import networkx as nx
    G = nx.Graph()
    for ln in wn.link_name_list:
        l = wn.get_link(ln); G.add_edge(l.start_node_name, l.end_node_name)
    for n in wn.node_name_list: G.add_node(n)
    comps = list(nx.connected_components(G))
    resset = set(wn.reservoir_name_list)
    mains = [c for c in comps if c & resset]
    main = max(mains, key=len) if mains else max(comps, key=len)
    anchor = next(n for n in main if n in wn.junction_name_list)
    islanded_mld = 0.0; bridges = 0
    for c in comps:
        if c is main or (c & resset): continue          # a component with its own source solves on its own
        n0 = None
        for n in c:
            if n in wn.junction_name_list:
                if n0 is None: n0 = n
                dt = wn.get_node(n).demand_timeseries_list[0]
                islanded_mld += dt.base_value * 86400 * 1000 / 1e6
                dt.base_value = 0.0
        if n0:
            wn.add_pipe("PX%d" % bridges, n0, anchor, length=3000,
                        diameter=0.015, roughness=100)
            bridges += 1
    _model = wn
    info = {"junctions": len(jmap), "pipes": len(segs), "reservoirs": r_count,
            "demand_MLD": round(total_mld, 1), "islands_bridged": bridges,
            "islanded_demand_MLD": round(islanded_mld, 2)}
    if bridges:
        ASSUMPTIONS.append(
            "%d disconnected sub-networks bridged with token links; %.2f MLD of demand on them zeroed (ring-chord stubs pending DXF route data)" % (bridges, islanded_mld))
    return info

def _run(wn):
    import wntr
    sim = wntr.sim.EpanetSimulator(wn)
    res = sim.run_sim()
    q = res.link["flowrate"].iloc[-1]      # m3/s, + = start→end
    v = res.link["velocity"].iloc[-1]
    hl = res.link["headloss"].iloc[-1]
    p = res.node["pressure"].iloc[-1]
    segs = _TRUNK["networks"]["water"]
    hydw, press = [], {}
    for name in p.index:
        press[name] = float(p[name])
    for i in range(len(segs)):
        nm = "P%d" % i
        try:
            fl = float(q[nm]) * 1000.0                    # → LPS
            vel = float(v[nm]); h = float(hl[nm])
            l = wn.get_link(nm)
            p1 = press.get(l.start_node_name, 0.0); p2 = press.get(l.end_node_name, 0.0)
            hydw.append([round(fl, 2), round(vel, 3), round(h, 3), round(p1, 1), round(p2, 1)])
        except Exception:
            hydw.append([0, 0, 0, 0, 0])
    pr = [x for x in press.values() if x > -50]
    return {"hydw": hydw,
            "pressure": {"min": round(min(pr), 1), "max": round(max(pr), 1),
                         "mean": round(sum(pr)/len(pr), 1)},
            "solver": "EPANET 2.2 via WNTR", "status": "UNCALIBRATED",
            "assumptions": ASSUMPTIONS}

def baseline(force=False):
    global _baseline, _base_ts, _model
    if _TRUNK is None:
        return {"error": "trunk_network.json not found on server"}
    if _model is None:
        _build()
    if force or _baseline is None or time.time() - _base_ts > 300:
        _baseline = _run(_model); _base_ts = time.time()
        _baseline["model"] = {"junctions": len(_model.junction_name_list),
                              "pipes": len(_TRUNK["networks"]["water"]),
                              "reservoirs": len(_model.reservoir_name_list)}
    return _baseline

def whatif(close_pipes):
    if _TRUNK is None:
        return {"error": "trunk data missing"}
    base = baseline()
    wn = copy.deepcopy(_model)
    for i in close_pipes:
        try: wn.get_link("P%d" % int(i)).initial_status = "Closed"
        except Exception: pass
    try:
        res = _run(wn)
    except Exception as e:
        return {"error": "solver failed with closure (network may be islanded): %s" % e}
    b, w = base["hydw"], res["hydw"]
    zero = sum(1 for i in range(len(w)) if abs(w[i][0]) < 0.05 and abs(b[i][0]) >= 0.05)
    dps = [(max(b[i][3]-w[i][3], b[i][4]-w[i][4]), i) for i in range(len(w))]
    dps.sort(reverse=True)
    worst = dps[0] if dps else (0, -1)
    hit = sum(1 for d, _ in dps if d > 5.0)
    return {"hydw": res["hydw"], "closed": close_pipes,
            "impact": {"pipes_stopped": zero, "pipes_dp_gt5": hit,
                       "worst_dp_m": round(worst[0], 1), "worst_pipe": worst[1],
                       "pressure_after": res["pressure"]},
            "status": "UNCALIBRATED", "assumptions": ASSUMPTIONS}
