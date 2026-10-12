"""
Amaravati Digital Twin — FastAPI Backend
Kreayotoo Solutions (P) Ltd

Endpoints:
  GET  /               → monitoring dashboard HTML
  GET  /api/status     → server health + last update times
  GET  /api/weather    → cached Open-Meteo weather (refreshed every 10 min)
  GET  /api/storm      → per-zone storm status (updated with each weather refresh)
  GET  /api/alerts     → current alert feed (sensor sim + live rainfall)
  GET  /api/blocks     → manifest of all 21 blocks
  GET  /api/block/{code} → single block network JSON (lazy load)
  POST /api/buffer     → GIS buffer analysis {lat, lon, radius, scenario}
  WS   /ws/alerts      → WebSocket — pushes alerts the moment they change
  WS   /ws/sensors     → WebSocket — pushes sensor readings every 20s
"""

import asyncio, json, math, os, random, time, hashlib
from datetime import datetime, timezone
from typing import Optional
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.responses import Response, HTMLResponse, JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import aiofiles

# ── paths ──────────────────────────────────────────────────────────────
BASE   = os.path.dirname(__file__)
STATIC = os.path.join(BASE, "static")
DATA   = os.path.join(STATIC, "data")
BLOCKS = os.path.join(STATIC, "blocks")

# ── in-memory state ────────────────────────────────────────────────────
STATE = {
    "weather":    None,
    "weather_ts": 0,
    "storm":      {},
    "alerts":     [],
    "alerts_hash": "",
    "sensors":    {},
    "last_tick":  None,
}

# load manifest + plots + network once at startup
MANIFEST = []; PLOTS = None; NET = None; ZONE_STORM = {}
def load_static():
    global MANIFEST, PLOTS, NET, ZONE_STORM
    mf = os.path.join(DATA, "manifest.json")
    if os.path.exists(mf):
        MANIFEST = json.load(open(mf))
    pf = os.path.join(DATA, "plots.json")
    if os.path.exists(pf):
        PLOTS = json.load(open(pf))
    nf = os.path.join(DATA, "incident_net.json")
    if os.path.exists(nf):
        NET = json.load(open(nf))
    zf = os.path.join(DATA, "zone_storm.json")
    if os.path.exists(zf):
        ZONE_STORM = json.load(open(zf))

# ── virtual sensor network ─────────────────────────────────────────────
DIU = [0.42,0.33,0.29,0.28,0.34,0.62,1.15,1.68,1.72,1.48,1.22,1.10,
       1.05,0.98,0.92,0.95,1.10,1.35,1.52,1.40,1.18,0.95,0.72,0.55]
FAULTS: dict = {}     # sid -> {t0, ramp, dur, mag}

def seed_val(s: str) -> float:
    h = int(hashlib.md5(s.encode()).hexdigest(), 16)
    return (h % 10000) / 10000.0

def init_sensors():
    sensors = {}
    for b in MANIFEST:
        z, bl = b["zone"], b["block"]
        t = f"Z{z}-{bl}"
        sensors[f"PT-{t}"] = {"kind":"pressure","base":2.9+seed_val(b["code"]+"p")*0.7,"b":b,"unit":"bar"}
        sensors[f"FM-{t}"] = {"kind":"flow","base":18+seed_val(b["code"]+"f")*46,"b":b,"unit":"L/s"}
        if hash(b["code"]) % 2 == 0:
            sensors[f"CL-{t}"] = {"kind":"chlorine","base":0.42+seed_val(b["code"]+"c")*0.26,"b":b,"unit":"mg/L"}
        if hash(b["code"]) % 4 == 0:
            sensors[f"PU-{t}"] = {"kind":"pump","base":140+seed_val(b["code"]+"u")*130,"b":b,"unit":"kW"}
    return sensors

def read_sensor(sid: str, sn: dict, now_ts: float) -> dict:
    hr = datetime.now().hour + datetime.now().minute/60
    d  = DIU[int(hr) % 24]
    r  = random.gauss(0, 1)
    k, base = sn["kind"], sn["base"]
    if k == "pressure":   v = base*(1.08-0.10*d) + r*0.06
    elif k == "flow":      v = base*d + r*base*0.05
    elif k == "chlorine":  v = base + r*0.03
    else:                  v = base*(0.85+0.20*d) + r*4
    f = FAULTS.get(sid)
    prog = 0.0
    if f:
        age_min = (now_ts - f["t0"]) / 60.0
        if age_min > f["dur"]:
            FAULTS.pop(sid, None)
        else:
            prog = min(1.0, age_min / f["ramp"])
            if k == "pressure":  v = v*(1-0.62*f["mag"]*prog)
            elif k == "flow":    v = v*(1+1.25*f["mag"]*prog)
            elif k == "chlorine":v = max(0.03, v*(1-0.80*f["mag"]*prog))
            else:                v = v*(1-f["mag"]*prog)
    return {"v": round(v, 3), "prog": round(prog, 3), "ts": now_ts}

def sensor_to_alert(sid: str, sn: dict, reading: dict):
    v, prog = reading["v"], reading["prog"]
    if prog == 0: return None
    k, b, base = sn["kind"], sn["b"], sn["base"]
    THRESHOLDS = {
        "pressure":  (2.35, lambda v,b: ("burst",
            "critical" if v<1.5 else ("high" if v<1.95 else "medium"),
            f"Pressure {round((1-v/base)*100)}% below normal — suspected burst (Zone {b['zone']} · {b['block']})",
            f"{v:.2f}", f"bar (normal {base:.1f})")),
        "flow":      (1.45, lambda v,b: ("pressure",
            "critical" if v/base>2.1 else ("high" if v/base>1.75 else "medium"),
            f"Flow +{round((v/base-1)*100)}% at DMA inlet — probable leak (Zone {b['zone']} · {b['block']})",
            f"+{round((v/base-1)*100)}", f"% vs baseline ({v:.0f} L/s)")),
        "chlorine":  (0.20, lambda v,b: ("quality",
            "critical" if v<0.08 else ("high" if v<0.14 else "medium"),
            f"Chlorine residual below limit (Zone {b['zone']} · {b['block']})",
            f"{v:.2f}", "mg/L (min 0.20)")),
        "pump":      (0.35, lambda v,b: ("power",
            "critical" if v<8 else "high",
            f"Pump station {v:.0f} kW — supply fault (Zone {b['zone']} · {b['block']})",
            f"{v:.0f}", f"kW (normal {base:.0f})")),
    }
    thr_fn = THRESHOLDS.get(k)
    if not thr_fn: return None
    thr, fn = thr_fn
    # check threshold
    triggered = (k=="pressure" and v<thr) or (k=="flow" and v/base>1+thr-1) or \
                (k=="chlorine" and v<thr) or (k=="pump" and v/base<thr)
    if not triggered: return None
    atype, sev, msg, val, unit = fn(v, b)
    r_seed = seed_val(sid+"lat")
    return {
        "id":  f"SEN-{sid}",
        "type": atype,
        "live": False,
        "severity": sev,
        "lat":  b["lat"] + (r_seed - 0.5)*0.004,
        "lon":  b["lon"] + (seed_val(sid+"lon") - 0.5)*0.004,
        "radius": 600 if atype=="power" else (400 if atype=="quality" else 250),
        "ts":   datetime.now(timezone.utc).isoformat(),
        "source": f"Demo sensor {sid} — SCADA placeholder",
        "msg":  msg,
        "value": val,
        "unit": unit,
    }

async def tick_sensors():
    """Called every 20 s — update all sensor readings and spawn/expire faults."""
    if not STATE["sensors"]: return
    now_ts = time.time()
    # maybe spawn a fault
    if len(FAULTS) < 4 and random.random() < 0.20:
        cands = [sid for sid in STATE["sensors"] if sid not in FAULTS]
        if cands:
            sid = random.choice(cands)
            FAULTS[sid] = {
                "t0":   now_ts,
                "ramp": 2 + random.random()*6,
                "dur":  8 + random.random()*26,
                "mag":  0.55 + random.random()*0.42,
            }
    # read all sensors
    readings = {}
    for sid, sn in STATE["sensors"].items():
        readings[sid] = read_sensor(sid, sn, now_ts)
    STATE["sensors_data"] = readings
    STATE["last_tick"] = datetime.now(timezone.utc).isoformat()

async def build_alerts():
    """Build the alert list from sensor readings + live weather storm."""
    alerts = []
    if STATE.get("sensors_data"):
        for sid, sn in STATE["sensors"].items():
            rd = STATE["sensors_data"].get(sid)
            if rd:
                a = sensor_to_alert(sid, sn, rd)
                if a: alerts.append(a)
    # add live weather storm alerts
    wx = STATE.get("weather")
    if wx and ZONE_STORM:
        try:
            H = wx["hourly"]
            now = datetime.now()
            now_str = now.strftime("%Y-%m-%dT%H:%M")
            i0 = next((i for i,t in enumerate(H["time"]) if t >= now_str), 1)
            ante = sum(H["precipitation"][max(0,i0-48):i0])
            nxt  = H["precipitation"][i0:i0+24]
            peak1 = max(nxt) if nxt else 0
            peak3 = max((sum(nxt[i:i+3])/3 for i in range(len(nxt)-2)), default=0)
            iPk = max(peak1, peak3)
            C = min(0.95, 0.70 + min(ante/60, 1)*0.22)
            if iPk > 0.4:
                for z, s in ZONE_STORM.items():
                    A = max(s.get("area_m2", 50000), 50000)
                    Qcap = max(0.02, s.get("capacity_m3s", 0.1))
                    util = min(200, C*iPk*A/3.6e6/Qcap*100)
                    if util < 50: continue
                    sev = "critical" if util>100 else ("high" if util>70 else "medium")
                    b = next((m for m in MANIFEST if m["zone"]==z), None)
                    if not b: continue
                    alerts.append({
                        "id": f"WX-{z}",
                        "type": "flood",
                        "live": True,
                        "severity": sev,
                        "lat": b["lat"], "lon": b["lon"],
                        "radius": 400,
                        "ts": datetime.now(timezone.utc).isoformat(),
                        "source": "Open-Meteo (live rainfall)",
                        "msg": f"Zone {z} storm drains at {util:.0f}% capacity",
                        "value": f"{iPk:.1f}",
                        "unit": f"mm/hr peak · {ante:.0f} mm antecedent",
                    })
        except Exception as e:
            print(f"[storm alerts] {e}")
    rank = {"critical":0,"high":1,"medium":2}
    alerts.sort(key=lambda a: (rank.get(a["severity"],9), 0 if a["live"] else 1))
    STATE["alerts"] = alerts
    new_hash = hashlib.md5(json.dumps(alerts, sort_keys=True).encode()).hexdigest()
    changed = new_hash != STATE["alerts_hash"]
    STATE["alerts_hash"] = new_hash
    return changed

# ── GIS buffer (runs in thread pool so it doesn't block) ───────────────
def run_buffer(lat: float, lon: float, radius: float, scenario: str) -> dict:
    if not PLOTS or not NET:
        return {"error": "GIS data not loaded"}
    LAT0, LON0 = PLOTS["origin"]
    FWD = PLOTS["fwd"]; INV = PLOTS["inv"]
    dlon = lon - LON0; dlat = lat - LAT0
    mx = INV[0]*dlon + INV[1]*dlat
    my = INV[2]*dlon + INV[3]*dlat
    R2 = radius * radius
    ZN = PLOTS["zones"]; dens_map = {
        'R1-Village planning zone':120,'R3-Medium to high density zone':250,
        'R4-High density zone':400,'R5-Affordable / EWS Housing Zone':350,
        'SR2 Low Density Housing':60,'SR4 - High Density Private':300,
        'C1 -Mixed use zone':150,'C2- General commercial zone':80,
        'C3-Neighbourhood centre zone':100,'C4-Town centre zone':90,
        'C5-Regional centre zone':70,'C6-Central business district zone':120,
        'S2-Education zone':150,'SS2a- Education Zone':150,'SS2c Health Zone':100,
        'SS1 - Government Zone':90,'I1-Business park zone':40,'I2-Logistics zone':25,
        'P1-Passive zone':2,'P2-Active zone':3,'P3-Protected zone':1,
        'U2- Road reserve zone':0,'SU2 - Road Network':0,
    }
    by_zone = {}; plots = 0; area = 0.0; pop = 0.0; fac = {}; road_area = 0.0
    D = PLOTS["dx"]; Y = PLOTS["dy"]; Z = PLOTS["z"]; A = PLOTS["a"]
    for i in range(len(D)):
        dx = D[i]-mx; dy = Y[i]-my
        if dx*dx+dy*dy > R2: continue
        z = ZN[Z[i]]; a = A[i]; p = a/10000*dens_map.get(z,50)
        if z not in by_zone: by_zone[z] = {"n":0,"a":0,"pop":0}
        by_zone[z]["n"]+=1; by_zone[z]["a"]+=a; by_zone[z]["pop"]+=p
        plots+=1; area+=a; pop+=p
        zl = z.lower()
        if "education" in zl: fac["Schools"]=fac.get("Schools",0)+1
        if "health" in zl:    fac["Hospitals"]=fac.get("Hospitals",0)+1
        if "government" in zl:fac["Government"]=fac.get("Government",0)+1
        if "road" in zl:      road_area+=a
    UT = NET["utils"]; u_stat = {u:{"len":0,"n":0,"max_d":0} for u in UT}
    scen_u = {"burst":"water","contam":"water","power":"power","flood":"strom","fire":"water"}.get(scenario,"water")
    iso_cand = []
    for p in NET["pipes"]:
        cx=(p[0]+p[2])/2; cy=(p[1]+p[3])/2
        if (cx-mx)**2+(cy-my)**2>R2: continue
        u=UT[p[4]]; L=math.hypot(p[2]-p[0],p[3]-p[1])
        s=u_stat[u]; s["len"]+=L; s["n"]+=1
        if p[5]>s["max_d"]: s["max_d"]=p[5]
    for m in NET["mh"]:
        d=math.hypot(m[0]-mx,m[1]-my)
        if d < radius*1.6 and UT[m[2]]==scen_u:
            iso_cand.append({"d":round(d),"mx":m[0],"my":m[1]})
    iso_cand.sort(key=lambda x: x["d"])
    risk = min(100, pop/220 + sum(v*w for k,v in fac.items()
        for w in [3 if k=="Hospitals" else 1.5 if k=="Schools" else 1])
        + sum(s["len"] for s in u_stat.values())/1000*1.4)
    if scenario in ("contam","fire"): risk=min(100,risk*1.25)
    return {
        "plots": plots,
        "area_ha": round(area/10000,1),
        "population": round(pop),
        "households": round(pop/4.2),
        "demand_mld": round(pop*135/1e6,2),
        "road_km": round(road_area/12/1000,2),
        "facilities": fac,
        "by_zone": {k:{"n":v["n"],"ha":round(v["a"]/10000,1),"pop":round(v["pop"])} for k,v in
                    sorted(by_zone.items(), key=lambda x:-x[1]["a"])[:12]},
        "network": {u:{"pipes":s["n"],"km":round(s["len"]/1000,2),"max_mm":s["max_d"]}
                    for u,s in u_stat.items() if s["n"]>0},
        "isolation": iso_cand[:4],
        "risk_score": round(risk),
    }

# ── background tasks ───────────────────────────────────────────────────
async def fetch_weather():
    import urllib.request
    lat = sum(m["lat"] for m in MANIFEST)/max(len(MANIFEST),1)
    lon = sum(m["lon"] for m in MANIFEST)/max(len(MANIFEST),1)
    url = (f"https://api.open-meteo.com/v1/forecast?latitude={lat:.4f}&longitude={lon:.4f}"
           f"&current=temperature_2m,relative_humidity_2m,apparent_temperature,precipitation,"
           f"rain,weather_code,wind_speed_10m&hourly=precipitation,temperature_2m"
           f"&daily=precipitation_sum,temperature_2m_max,temperature_2m_min,weather_code"
           f"&timezone=auto&past_days=2&forecast_days=7")
    try:
        with urllib.request.urlopen(url, timeout=10) as r:
            STATE["weather"] = json.loads(r.read())
            STATE["weather_ts"] = time.time()
            print(f"[weather] refreshed at {datetime.now().strftime('%H:%M:%S')}")
    except Exception as e:
        print(f"[weather] fetch error: {e}")

async def background_loop():
    await asyncio.sleep(1)
    await fetch_weather()
    STATE["sensors"] = init_sensors()
    STATE["sensors_data"] = {}
    print(f"[sensors] {len(STATE['sensors'])} virtual sensors initialised")
    while True:
        await tick_sensors()
        changed = await build_alerts()
        if changed:
            await alert_manager.broadcast()
        await sensor_manager.broadcast()
        if time.time() - STATE["weather_ts"] > 600:
            await fetch_weather()
            await build_alerts()
        await asyncio.sleep(20)

# ── WebSocket connection managers ──────────────────────────────────────
class WSManager:
    def __init__(self, topic: str):
        self.topic = topic
        self.connections: list[WebSocket] = []
    async def connect(self, ws: WebSocket):
        await ws.accept(); self.connections.append(ws)
        print(f"[ws/{self.topic}] +1 client ({len(self.connections)} total)")
    def disconnect(self, ws: WebSocket):
        if ws in self.connections: self.connections.remove(ws)
        print(f"[ws/{self.topic}] -1 client ({len(self.connections)} total)")
    async def broadcast(self):
        if not self.connections: return
        data = self._payload()
        dead = []
        for ws in self.connections:
            try: await ws.send_json(data)
            except: dead.append(ws)
        for ws in dead: self.disconnect(ws)
    def _payload(self):
        if self.topic == "alerts":
            return {"type":"alerts","data":STATE["alerts"],"ts":datetime.now(timezone.utc).isoformat()}
        if self.topic == "sensors":
            sdata = STATE.get("sensors_data",{})
            out = {}
            for sid,sn in STATE.get("sensors",{}).items():
                rd = sdata.get(sid,{})
                out[sid] = {"kind":sn["kind"],"unit":sn["unit"],"base":round(sn["base"],2),
                            "v":rd.get("v",sn["base"]),"prog":rd.get("prog",0),
                            "zone":sn["b"]["zone"],"block":sn["b"]["block"]}
            return {"type":"sensors","data":out,"ts":datetime.now(timezone.utc).isoformat()}
        return {}

alert_manager  = WSManager("alerts")
sensor_manager = WSManager("sensors")

# ── app lifecycle ──────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    load_static()
    task = asyncio.create_task(background_loop())
    print("=" * 56)
    print("  Amaravati Digital Twin — Backend Server")
    print("  Kreayotoo Solutions (P) Ltd")
    print(f"  Blocks loaded: {len(MANIFEST)}")
    print(f"  GIS data: {'✓ plots+net' if PLOTS and NET else '✗ missing'}")
    print("=" * 56)
    try:
        msg=ING.start_background(asyncio.get_event_loop()); print('INGEST:',msg)
    except Exception as e:
        print('INGEST start failed:',e)
    yield
    task.cancel()

# ══ SECURITY LAYER (Phase A-1) ══════════════════════════════════════════
import hmac as _hmac, base64 as _b64x, secrets as _sec
SEC_FILE=os.path.join(BASE,"security.json"); USERS_FILE=os.path.join(BASE,"users.json")
AUDIT_FILE=os.path.join(BASE,"audit.log"); KEY_FILE=os.path.join(BASE,"secret.key")
BK_DIR=os.path.join(BASE,"backups"); os.makedirs(BK_DIR,exist_ok=True)
def _jload(f,d):
    try:
        with open(f) as fh: return json.load(fh)
    except Exception: return d
def _jsave(f,d):
    t=f+".tmp"
    with open(t,"w") as fh: json.dump(d,fh,indent=1)
    os.replace(t,f)
SEC=_jload(SEC_FILE,{"require_auth":True,"token_hours":8,
    "allow_origins":["null","http://localhost:8000","http://127.0.0.1:8000"]})
_jsave(SEC_FILE,SEC)
if not os.path.exists(KEY_FILE):
    open(KEY_FILE,"w").write(_sec.token_hex(32))
SECRET=open(KEY_FILE).read().strip().encode()
def _hash_pw(pw,salt=None):
    salt=salt or _sec.token_hex(8)
    return salt+":"+hashlib.pbkdf2_hmac("sha256",pw.encode(),salt.encode(),120000).hex()
def _check_pw(pw,stored):
    try: salt=stored.split(":")[0]; return _hmac.compare_digest(_hash_pw(pw,salt),stored)
    except Exception: return False
USERS=_jload(USERS_FILE,None)
if USERS is None:
    USERS={"admin":{"pw":_hash_pw("admin123"),"role":"Admin","name":"Administrator"}}
    _jsave(USERS_FILE,USERS)
    print("SECURITY: seeded default user admin / admin123 — CHANGE IT (POST /api/auth/password)")
ROLES=["Admin","Engineer","Operator","Viewer"]
def _mint(u):
    exp=int(time.time())+int(SEC.get("token_hours",8))*3600
    body=_b64x.urlsafe_b64encode(json.dumps({"u":u,"r":USERS[u]["role"],"exp":exp}).encode()).decode()
    sig=_hmac.new(SECRET,body.encode(),hashlib.sha256).hexdigest()
    return body+"."+sig, exp
def _verify(tok):
    try:
        body,sig=tok.split(".")
        if not _hmac.compare_digest(sig,_hmac.new(SECRET,body.encode(),hashlib.sha256).hexdigest()): return None
        d=json.loads(_b64x.urlsafe_b64decode(body))
        if d["exp"]<time.time(): return None
        if d["u"] not in USERS: return None
        d["r"]=USERS[d["u"]]["role"]
        return d
    except Exception: return None
def _audit(user,action,detail="",ip=""):
    try:
        with open(AUDIT_FILE,"a") as f:
            f.write(json.dumps({"ts":datetime.now(timezone.utc).isoformat(),"user":user,
                "action":action,"detail":detail,"ip":ip})+"\n")
    except Exception: pass
from fastapi import Request, Depends
def auth_user(request: Request):
    if not SEC.get("require_auth",True):
        return {"u":"anonymous","r":"Engineer"}
    tok=(request.headers.get("authorization") or "").replace("Bearer ","").strip()
    d=_verify(tok)
    if not d: raise HTTPException(401,"login required")
    return d
def need_role(d,roles):
    if d["r"] not in roles: raise HTTPException(403,"insufficient role ("+d["r"]+")")
# ═══════════════════════════════════════════════════════════════════════
import ingest as ING
def _om_append_wo(wo, dedupe_key=None):
    d=_om_load()
    if dedupe_key:
        for w in d["wos"]:
            if w.get("status")!="Closed" and dedupe_key in (w.get("asset") or ""):
                return False
    d["wos"].insert(0, wo); _om_save(d); return True
ING._om_hook=_om_append_wo
ING._audit_hook=lambda u,a,det="": _audit(u,a,det)

app = FastAPI(title="Amaravati Digital Twin API", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=SEC.get("allow_origins",["null"]), allow_methods=["*"], allow_headers=["*"])
app.mount("/static", StaticFiles(directory=STATIC), name="static")

# ── O&M store (Phase 2 — shared work orders / PM across users) ─────────
OM_FILE = os.path.join(BASE, "om_store.json")
def _om_load():
    try:
        with open(OM_FILE) as f: return json.load(f)
    except Exception:
        return {"wos": [], "pm": {}, "comm": "2024-06-01", "stock": []}
def _om_save(d):
    tmp = OM_FILE + ".tmp"
    with open(tmp, "w") as f: json.dump(d, f)
    os.replace(tmp, OM_FILE)

class OMStore(BaseModel):
    wos: list
    pm: dict
    comm: str
    stock: list = []

class LoginIn(BaseModel):
    username: str
    password: str
class PwIn(BaseModel):
    old: str
    new: str
class UserIn(BaseModel):
    username: str
    password: str
    role: str
    name: str = ""

class DeviceIn(BaseModel):
    id: str
    name: str
    kind: str = "other"
    utility: str = "water"
    unit: str = ""
    protocol: str = "rest"
    block: str = "-"
    enabled: bool = True
    config: dict = {}
    thresholds: dict = {}

class ReadingIn(BaseModel):
    device_id: str
    value: float
    ts: float | None = None

@app.get("/api/devices")
async def dev_list(d=Depends(auth_user)):
    return ING.DEVICES

@app.post("/api/devices")
async def dev_add(b: DeviceIn, d=Depends(auth_user)):
    need_role(d, ["Admin","Engineer"])
    ING.DEVICES[b.id]=b.dict(exclude={"id"})
    ING._jsave(ING.DEV_FILE, ING.DEVICES); _audit(d["u"],"device_upsert",b.id)
    return {"ok": True, "devices": len(ING.DEVICES)}

@app.delete("/api/devices/{dev_id}")
async def dev_del(dev_id: str, d=Depends(auth_user)):
    need_role(d, ["Admin","Engineer"])
    ING.DEVICES.pop(dev_id, None); ING._jsave(ING.DEV_FILE, ING.DEVICES)
    _audit(d["u"],"device_delete",dev_id)
    return {"ok": True}

@app.post("/api/ingest")
async def ingest_one(b: ReadingIn):
    ok=ING.push_reading(b.device_id, b.value, b.ts)
    if not ok: raise HTTPException(400,"unknown/disabled device or bad value")
    return {"ok": True}

@app.post("/api/ingest/batch")
async def ingest_batch(items: list[ReadingIn]):
    n=sum(1 for b in items if ING.push_reading(b.device_id, b.value, b.ts))
    return {"ok": True, "accepted": n, "of": len(items)}

@app.get("/api/ingest")
async def ingest_get(device_id: str, value: float):
    if not ING.push_reading(device_id, value): raise HTTPException(400,"unknown device")
    return {"ok": True}

@app.get("/api/live")
async def live(d=Depends(auth_user)):
    return ING.live_snapshot()

# ── history · export · retention (declared before the generic /api/readings/{dev_id}) ──
@app.get("/api/readings/{dev_id}.csv")
async def readings_csv(dev_id: str, request: Request, frm: float = None, to: float = None,
                       hours: float = None, res: str = "auto", d=Depends(auth_user)):
    if dev_id not in ING.DEVICES: raise HTTPException(404, "unknown device")
    if hours and not frm: frm = time.time() - hours*3600
    csv, h = ING.history_csv(dev_id, frm, to, res)
    _audit(d["u"], "export_csv", f"{dev_id} res={h['res']} n={len(h['points'])}",
           request.client.host if request.client else "")
    fn = f"{dev_id}_{h['res']}_{int(h['from'])}_{int(h['to'])}.csv"
    return Response(content=csv, media_type="text/csv",
                    headers={"Content-Disposition": f'attachment; filename="{fn}"'})

@app.get("/api/history/{dev_id}")
async def history(dev_id: str, frm: float = None, to: float = None, hours: float = None,
                  res: str = "auto", max_pts: int = 2000, d=Depends(auth_user)):
    """Time series at automatic resolution: raw ≤ 2 d, hourly ≤ 120 d, daily beyond.
    res=raw|hour|day forces a table. Times are epoch seconds UTC."""
    if dev_id not in ING.DEVICES: raise HTTPException(404, "unknown device")
    if hours and not frm: frm = time.time() - hours*3600
    return ING.history(dev_id, frm, to, res, max(10, min(max_pts, 20000)))

@app.get("/api/retention")
async def retention(d=Depends(auth_user)):
    return ING.retention_status()

@app.post("/api/retention/rollup")
async def retention_rollup(request: Request, d=Depends(auth_user)):
    need_role(d, ["Admin", "Engineer"])
    out = ING.rollup_once()
    _audit(d["u"], "rollup", str(out), request.client.host if request.client else "")
    return {"ok": True, "deleted": out, "status": ING.retention_status()}

@app.get("/api/readings/{dev_id}")
async def readings(dev_id: str, hours: int = 24, d=Depends(auth_user)):
    return ING.series(dev_id, hours)

@app.get("/api/alarms")
async def alarms(n: int = 100, d=Depends(auth_user)):
    return ING.alarms_tail(n)

import hydraulics as HYD

class WhatIfIn(BaseModel):
    pipes: list

@app.get("/api/hydraulics/run")
async def hyd_run(d=Depends(auth_user)):
    return HYD.baseline()

@app.post("/api/hydraulics/whatif")
async def hyd_whatif(b: WhatIfIn, d=Depends(auth_user)):
    need_role(d, ["Admin","Engineer","Operator"])
    _audit(d["u"], "hyd_whatif", "close " + ",".join(str(x) for x in b.pipes[:10]))
    return HYD.whatif([int(x) for x in b.pipes][:20])

@app.get("/api/hydraulics/assumptions")
async def hyd_assump():
    return {"status": "UNCALIBRATED", "assumptions": HYD.ASSUMPTIONS}

@app.get("/api/om/ping")
async def om_ping():
    return {"auth_required": bool(SEC.get("require_auth",True)), "roles": ROLES}

@app.post("/api/auth/login")
async def login(b: LoginIn, request: Request):
    u=USERS.get(b.username)
    if not u or not _check_pw(b.password,u["pw"]):
        _audit(b.username,"login_fail","",request.client.host if request.client else "")
        raise HTTPException(401,"invalid credentials")
    tok,exp=_mint(b.username)
    _audit(b.username,"login","",request.client.host if request.client else "")
    return {"token":tok,"role":u["role"],"name":u.get("name",b.username),"expires":exp}

@app.post("/api/auth/password")
async def change_pw(b: PwIn, d=Depends(auth_user)):
    u=USERS.get(d["u"]);
    if not u or not _check_pw(b.old,u["pw"]): raise HTTPException(401,"old password incorrect")
    u["pw"]=_hash_pw(b.new); _jsave(USERS_FILE,USERS); _audit(d["u"],"password_change")
    return {"ok":True}

@app.get("/api/auth/users")
async def users_list(d=Depends(auth_user)):
    need_role(d,["Admin"])
    return [{"username":k,"role":v["role"],"name":v.get("name","")} for k,v in USERS.items()]

@app.post("/api/auth/users")
async def users_add(b: UserIn, d=Depends(auth_user)):
    need_role(d,["Admin"])
    if b.role not in ROLES: raise HTTPException(400,"role must be one of "+",".join(ROLES))
    USERS[b.username]={"pw":_hash_pw(b.password),"role":b.role,"name":b.name or b.username}
    _jsave(USERS_FILE,USERS); _audit(d["u"],"user_add",b.username+":"+b.role)
    return {"ok":True}

@app.delete("/api/auth/users/{uname}")
async def users_del(uname: str, d=Depends(auth_user)):
    need_role(d,["Admin"])
    if uname=="admin": raise HTTPException(400,"cannot delete admin")
    USERS.pop(uname,None); _jsave(USERS_FILE,USERS); _audit(d["u"],"user_del",uname)
    return {"ok":True}

@app.get("/api/audit")
async def audit_tail(d=Depends(auth_user)):
    need_role(d,["Admin"])
    try:
        with open(AUDIT_FILE) as f: lines=f.readlines()[-200:]
        return [json.loads(x) for x in lines]
    except Exception: return []

_last_bk=[0.0]
@app.get("/api/om/store")
async def om_get(d=Depends(auth_user)):
    return _om_load()

@app.post("/api/om/store")
async def om_set(s: OMStore, request: Request, d=Depends(auth_user)):
    need_role(d,["Admin","Engineer","Operator"])
    _om_save(s.dict())
    _audit(d["u"],"om_write","wos="+str(len(s.wos))+" stock="+str(len(s.stock)),
           request.client.host if request.client else "")
    if time.time()-_last_bk[0]>6*3600:
        _last_bk[0]=time.time()
        try:
            import shutil
            bks=sorted(os.listdir(BK_DIR))
            shutil.copy(OM_FILE,os.path.join(BK_DIR,"om_store_"+datetime.now().strftime("%Y%m%d_%H%M")+".json"))
            for old in bks[:-29]: os.remove(os.path.join(BK_DIR,old))
        except Exception: pass
    return {"ok": True, "wos": len(s.wos)}

# ── REST endpoints ─────────────────────────────────────────────────────
@app.get("/", response_class=HTMLResponse)
async def dashboard():
    f = os.path.join(BASE, "templates", "monitor.html")
    if os.path.exists(f):
        async with aiofiles.open(f) as fh: return await fh.read()
    return HTMLResponse("<h2>Monitor template not found</h2>")

@app.get("/api/status")
async def status():
    return {"ok":True,"blocks":len(MANIFEST),"sensors":len(STATE.get("sensors",{})),
            "alerts":len(STATE["alerts"]),"weather_age_s":round(time.time()-STATE["weather_ts"]),
            "last_tick":STATE.get("last_tick"),"ts":datetime.now(timezone.utc).isoformat()}

@app.get("/api/weather")
async def weather():
    if not STATE["weather"]: raise HTTPException(503,"Weather not yet loaded")
    return STATE["weather"]

@app.get("/api/storm")
async def storm():
    wx = STATE.get("weather")
    if not wx or not ZONE_STORM: return {}
    try:
        H = wx["hourly"]
        now_str = datetime.now().strftime("%Y-%m-%dT%H:%M")
        i0 = next((i for i,t in enumerate(H["time"]) if t >= now_str), 1)
        ante = sum(H["precipitation"][max(0,i0-48):i0])
        nxt  = H["precipitation"][i0:i0+24]
        peak1 = max(nxt) if nxt else 0
        peak3 = max((sum(nxt[i:i+3])/3 for i in range(max(1,len(nxt)-2))), default=0)
        iPk = max(peak1, peak3)
        C = min(0.95, 0.70 + min(ante/60,1)*0.22)
        out = {}
        for z,s in ZONE_STORM.items():
            A = max(s.get("area_m2",50000),50000)
            Qcap = max(0.02, s.get("capacity_m3s",0.1))
            util = min(200, C*iPk*A/3.6e6/Qcap*100)
            out[z] = {"util_pct":round(util,1),"capacity_m3s":s.get("capacity_m3s",0),
                      "max_dia":s.get("max_dia",0),"peak_intensity":round(iPk,2),
                      "antecedent_mm":round(ante,1),"C_eff":round(C,3)}
        return out
    except Exception as e:
        return {"error": str(e)}

@app.get("/api/alerts")
async def alerts():
    return STATE["alerts"]

@app.get("/api/blocks")
async def blocks():
    return MANIFEST

@app.get("/api/block/{code}")
async def block(code: str):
    p = os.path.join(BLOCKS, f"{code}.json")
    if not os.path.exists(p):
        raise HTTPException(404, f"Block {code} not found")
    async with aiofiles.open(p) as f:
        return JSONResponse(content=json.loads(await f.read()))

@app.get("/api/sensors")
async def sensors():
    sdata = STATE.get("sensors_data", {})
    out = {}
    for sid, sn in STATE.get("sensors", {}).items():
        rd = sdata.get(sid, {})
        out[sid] = {"kind":sn["kind"],"unit":sn["unit"],"base":round(sn["base"],2),
                    "v":rd.get("v",sn["base"]),"prog":rd.get("prog",0),
                    "zone":sn["b"]["zone"],"block":sn["b"]["block"]}
    return out

class BufferReq(BaseModel):
    lat: float; lon: float; radius: float = 250; scenario: str = "burst"

@app.post("/api/buffer")
async def buffer(req: BufferReq):
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(None, run_buffer, req.lat, req.lon, req.radius, req.scenario)
    return result

# ── WebSocket endpoints ────────────────────────────────────────────────
@app.websocket("/ws/alerts")
async def ws_alerts(ws: WebSocket):
    await alert_manager.connect(ws)
    await ws.send_json(alert_manager._payload())   # immediate snapshot
    try:
        while True: await ws.receive_text()
    except WebSocketDisconnect:
        alert_manager.disconnect(ws)

@app.websocket("/ws/sensors")
async def ws_sensors(ws: WebSocket):
    await sensor_manager.connect(ws)
    await ws.send_json(sensor_manager._payload())
    try:
        while True: await ws.receive_text()
    except WebSocketDisconnect:
        sensor_manager.disconnect(ws)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=False, log_level="info")
