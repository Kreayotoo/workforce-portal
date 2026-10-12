# ═══════════════════════════════════════════════════════════════════════
#  INGEST — universal, brand-agnostic device connectivity (Phase A-2)
#  Protocols: REST/webhook (universal) · MQTT · Modbus-TCP · OPC-UA · SIM
#  Any vendor works: mapping lives in config, never in code.
# ═══════════════════════════════════════════════════════════════════════
import os, json, time, math, random, sqlite3, asyncio, threading, queue
from datetime import datetime, timezone

BASE = os.path.dirname(__file__)
DEV_FILE   = os.path.join(BASE, "devices.json")
CFG_FILE   = os.path.join(BASE, "ingest.json")
DB_FILE    = os.path.join(BASE, "readings.db")
ALARM_FILE = os.path.join(BASE, "alarms.log")

def _jload(f, d):
    try:
        with open(f) as fh: return json.load(fh)
    except Exception: return d
def _jsave(f, d):
    t = f + ".tmp"
    with open(t, "w") as fh: json.dump(d, fh, indent=1)
    os.replace(t, f)

# ── device registry ────────────────────────────────────────────────────
DEVICES = _jload(DEV_FILE, None)
if DEVICES is None:
    DEVICES = {  # three SIMULATED demo devices so the chain is visible day-1
      "SIM-FLOW-1":  {"name":"Demo bulk flow (SIMULATED)","kind":"flow","utility":"water","unit":"LPS",
                      "protocol":"sim","enabled":True,"block":"Z1B_B5",
                      "config":{"base":120,"amp":25,"period_s":600,"noise":4},
                      "thresholds":{"lo":60,"hi":170}},
      "SIM-PRES-1":  {"name":"Demo pressure (SIMULATED)","kind":"pressure","utility":"water","unit":"m",
                      "protocol":"sim","enabled":True,"block":"Z1B_B5",
                      "config":{"base":32,"amp":6,"period_s":420,"noise":1.2},
                      "thresholds":{"lo":15,"hi":45}},
      "SIM-CL2-1":   {"name":"Demo residual chlorine (SIMULATED)","kind":"quality","utility":"water","unit":"mg/L",
                      "protocol":"sim","enabled":True,"block":"Z1B_B5",
                      "config":{"base":0.8,"amp":0.25,"period_s":900,"noise":0.05},
                      "thresholds":{"lo":0.2,"hi":1.5}},
    }
    _jsave(DEV_FILE, DEVICES)

CFG = _jload(CFG_FILE, None)
if CFG is None:
    CFG = {
      "mqtt":   {"enabled": False, "host": "127.0.0.1", "port": 1883,
                 "username": "", "password": "",
                 "topics": [
                   {"topic": "utility/+/reading",
                    "device_from": "json:device_id", "value_from": "json:value",
                    "_note": "any-brand JSON: {\"device_id\":\"X\",\"value\":12.3}"},
                   {"topic": "sensors/#",
                    "device_from": "topic:-1", "value_from": "payload",
                    "_note": "bare-number payloads: device id = last topic segment"}
                 ]},
      "retention": {"raw_days": 90, "hourly_days": 730, "daily_days": 0,
                    "_note": "raw kept 90 d, hourly averages 2 y, daily for ever (0 = never delete)"},
      "note": "Modbus-TCP and OPC-UA are configured per-device in devices.json (see INGEST.md)."
    }
    _jsave(CFG_FILE, CFG)
if "retention" not in CFG:                       # upgrade older ingest.json in place
    CFG["retention"] = {"raw_days": 90, "hourly_days": 730, "daily_days": 0}
    _jsave(CFG_FILE, CFG)

# ── readings store (SQLite time-series) ────────────────────────────────
_db = sqlite3.connect(DB_FILE, check_same_thread=False)
_lock = threading.Lock()
with _lock:
    _db.execute("PRAGMA journal_mode=WAL")
    _db.execute("CREATE TABLE IF NOT EXISTS readings(device_id TEXT, ts REAL, value REAL)")
    _db.execute("CREATE INDEX IF NOT EXISTS ix_dt ON readings(device_id, ts)")
    # roll-ups: one row per device per hour / per day (UTC buckets)
    for t in ("readings_h", "readings_d"):
        _db.execute(f"CREATE TABLE IF NOT EXISTS {t}(device_id TEXT, ts REAL, avg REAL, min REAL, max REAL, n INTEGER, "
                    f"PRIMARY KEY(device_id, ts))")
    _db.execute("CREATE TABLE IF NOT EXISTS rollup_meta(key TEXT PRIMARY KEY, ts REAL)")
    _db.commit()
_wq: "queue.Queue" = queue.Queue()
LATEST = {}          # device_id -> {"value","ts","state"}
ALSTATE = {}         # device_id -> "OK"/"ALARM"
_om_hook = None      # set by main.py: fn(wo_dict) appends into om_store
_audit_hook = None

def _writer():
    while True:
        batch = [_wq.get()]
        try:
            while len(batch) < 500: batch.append(_wq.get_nowait())
        except queue.Empty: pass
        try:
            with _lock:
                _db.executemany("INSERT INTO readings VALUES(?,?,?)", batch)
                _db.commit()
        except Exception: pass
threading.Thread(target=_writer, daemon=True).start()

# ── retention & roll-ups ───────────────────────────────────────────────
#  raw  ──(completed hours)──▶ readings_h ──(completed days)──▶ readings_d
#  raw older than raw_days and hourly older than hourly_days are deleted,
#  but never before they have been rolled up. Buckets are UTC.
HOUR, DAY = 3600.0, 86400.0
def _meta_get(k, default=0.0):
    r = _db.execute("SELECT ts FROM rollup_meta WHERE key=?", (k,)).fetchone()
    return r[0] if r else default
def _meta_set(k, v):
    _db.execute("INSERT OR REPLACE INTO rollup_meta VALUES(?,?)", (k, v))

def rollup_once(now=None):
    """Roll completed hours/days into the aggregate tables and apply retention. Idempotent."""
    now = now or time.time()
    r = CFG.get("retention", {})
    raw_days, h_days, d_days = float(r.get("raw_days", 90)), float(r.get("hourly_days", 730)), float(r.get("daily_days", 0))
    with _lock:
        # 1) raw -> hourly, for every complete hour since the last watermark
        h_end = math.floor(now / HOUR) * HOUR                  # start of the current (incomplete) hour
        h_from = _meta_get("hour_wm", 0.0)
        if h_end > h_from:
            _db.execute(
              "INSERT OR REPLACE INTO readings_h(device_id,ts,avg,min,max,n) "
              "SELECT device_id, CAST(ts/3600 AS INTEGER)*3600.0, AVG(value), MIN(value), MAX(value), COUNT(*) "
              "FROM readings WHERE ts>=? AND ts<? GROUP BY device_id, CAST(ts/3600 AS INTEGER)", (h_from, h_end))
            _meta_set("hour_wm", h_end)
        # 2) hourly -> daily, for every complete day since the last watermark
        d_end = math.floor(now / DAY) * DAY
        d_from = _meta_get("day_wm", 0.0)
        if d_end > d_from:
            _db.execute(
              "INSERT OR REPLACE INTO readings_d(device_id,ts,avg,min,max,n) "
              "SELECT device_id, CAST(ts/86400 AS INTEGER)*86400.0, SUM(avg*n)/SUM(n), MIN(min), MAX(max), SUM(n) "
              "FROM readings_h WHERE ts>=? AND ts<? GROUP BY device_id, CAST(ts/86400 AS INTEGER)", (d_from, d_end))
            _meta_set("day_wm", d_end)
        # 3) retention — only delete what has already been rolled up
        deleted = {"raw": 0, "hourly": 0, "daily": 0}
        if raw_days > 0:
            cut = min(now - raw_days*DAY, _meta_get("hour_wm", 0.0))
            deleted["raw"] = _db.execute("DELETE FROM readings WHERE ts<?", (cut,)).rowcount
        if h_days > 0:
            cut = min(now - h_days*DAY, _meta_get("day_wm", 0.0))
            deleted["hourly"] = _db.execute("DELETE FROM readings_h WHERE ts<?", (cut,)).rowcount
        if d_days > 0:
            deleted["daily"] = _db.execute("DELETE FROM readings_d WHERE ts<?", (now - d_days*DAY,)).rowcount
        _meta_set("last_rollup", now)
        _db.commit()
    return deleted

async def _rollup_loop():
    await asyncio.sleep(20)
    while True:
        try: rollup_once()
        except Exception: pass
        await asyncio.sleep(600)                               # every 10 minutes

def retention_status():
    with _lock:
        c = lambda t: _db.execute(f"SELECT COUNT(*), MIN(ts), MAX(ts) FROM {t}").fetchone()
        raw, hr, dy = c("readings"), c("readings_h"), c("readings_d")
        st = {"config": CFG.get("retention", {}),
              "raw":    {"rows": raw[0], "from": raw[1], "to": raw[2]},
              "hourly": {"rows": hr[0],  "from": hr[1],  "to": hr[2]},
              "daily":  {"rows": dy[0],  "from": dy[1],  "to": dy[2]},
              "last_rollup": _meta_get("last_rollup", None),
              "db_bytes": os.path.getsize(DB_FILE) if os.path.exists(DB_FILE) else 0}
    return st

def _alarm(dev_id, d, value, kind_msg):
    line = {"ts": datetime.now(timezone.utc).isoformat(), "device": dev_id,
            "name": d.get("name",""), "value": value, "msg": kind_msg}
    try:
        with open(ALARM_FILE, "a") as f: f.write(json.dumps(line) + "\n")
    except Exception: pass
    if _audit_hook: _audit_hook("system", "sensor_alarm", dev_id + " " + kind_msg)
    if _om_hook:  # auto-WO, deduped: one open auto-WO per device
        pri = "P1" if d.get("kind") in ("pressure", "quality") else "P2"
        _om_hook({"id": "WO-" + format(int(time.time()*1000), "x").upper(),
                  "asset": dev_id + " · " + d.get("name",""), "utility": d.get("utility","water"),
                  "kind": "sensor", "block": d.get("block","-"), "type": "Auto",
                  "priority": pri, "sla_h": 24 if pri=="P1" else 72,
                  "desc": "AUTO · " + kind_msg, "assignee": "", "status": "Open",
                  "opened": datetime.now(timezone.utc).isoformat(), "closed": None,
                  "origin": "Auto: sensor alarm", "docs": [], "materials": [],
                  "log": [{"ts": int(time.time()*1000), "m": "auto-created · " + kind_msg}]},
                 dedupe_key=dev_id)

def push_reading(dev_id, value, ts=None):
    """Single entry point every adapter funnels into — alarms + store + live."""
    d = DEVICES.get(dev_id)
    if not d or not d.get("enabled", True): return False
    try: value = float(value)
    except Exception: return False
    ts = float(ts) if ts else time.time()
    _wq.put((dev_id, ts, value))
    th = d.get("thresholds") or {}
    lo, hi = th.get("lo"), th.get("hi")
    state = "OK"
    if (lo is not None and value < lo) or (hi is not None and value > hi):
        state = "ALARM"
    prev = ALSTATE.get(dev_id, "OK")
    if state == "ALARM" and prev == "OK":
        which = "below low limit" if (lo is not None and value < lo) else "above high limit"
        _alarm(dev_id, d, value, f"{d.get('kind','value')} {value:g} {d.get('unit','')} {which} ({lo}–{hi})")
    if state == "OK" and prev == "ALARM":
        # 2% hysteresis before clearing
        if (lo is not None and value < lo*1.02) or (hi is not None and value > hi*0.98):
            state = "ALARM"
    ALSTATE[dev_id] = state
    LATEST[dev_id] = {"value": value, "ts": ts, "state": state}
    return True

# ── SIM adapter (demo; clearly labelled SIMULATED) ─────────────────────
async def _sim_loop():
    while True:
        now = time.time()
        for dev_id, d in DEVICES.items():
            if d.get("protocol") == "sim" and d.get("enabled", True):
                c = d.get("config", {})
                v = c.get("base",50) + c.get("amp",10)*math.sin(2*math.pi*now/max(60,c.get("period_s",600))) \
                    + random.uniform(-1,1)*c.get("noise",1)
                push_reading(dev_id, round(v,3), now)
        await asyncio.sleep(10)

# ── MQTT adapter (any broker · any brand via topic/JSON mapping) ───────
def _start_mqtt():
    m = CFG.get("mqtt", {})
    if not m.get("enabled"): return "mqtt: disabled"
    try:
        import paho.mqtt.client as mqtt
    except Exception:
        return "mqtt: paho-mqtt not installed (pip install paho-mqtt)"
    def resolve(rule, topic, payload):
        src = rule or ""
        if src == "payload":
            return payload.strip()
        if src.startswith("topic:"):
            parts = topic.split("/"); i = int(src.split(":")[1])
            return parts[i]
        if src.startswith("json:"):
            try:
                obj = json.loads(payload); cur = obj
                for k in src[5:].split("."):
                    cur = cur[int(k)] if isinstance(cur, list) else cur.get(k)
                return cur
            except Exception: return None
        return None
    def on_msg(cl, ud, msg):
        p = msg.payload.decode("utf-8", "ignore")
        for t in m.get("topics", []):
            dev = resolve(t.get("device_from"), msg.topic, p)
            val = resolve(t.get("value_from"), msg.topic, p)
            if dev is not None and val is not None:
                if push_reading(str(dev), val): break
    cl = mqtt.Client()
    if m.get("username"): cl.username_pw_set(m["username"], m.get("password",""))
    cl.on_connect = lambda c,u,f,rc: [c.subscribe(t["topic"]) for t in m.get("topics",[])]
    cl.on_message = on_msg
    try:
        cl.connect_async(m.get("host","127.0.0.1"), int(m.get("port",1883)), 30)
        cl.loop_start()
        return "mqtt: connecting to %s:%s" % (m.get("host"), m.get("port"))
    except Exception as e:
        return "mqtt: " + str(e)

# ── Modbus-TCP poller (per-device register mapping · any make) ─────────
async def _modbus_loop():
    try:
        from pymodbus.client import AsyncModbusTcpClient
    except Exception:
        return
    import struct
    def decode(regs, dt):
        if dt == "uint16": return regs[0]
        if dt == "int16":  return struct.unpack(">h", struct.pack(">H", regs[0]))[0]
        raw = struct.pack(">HH", regs[0], regs[1])
        if dt == "float32le": raw = struct.pack(">HH", regs[1], regs[0])
        return struct.unpack(">f", raw)[0]
    while True:
        for dev_id, d in DEVICES.items():
            if d.get("protocol") != "modbus" or not d.get("enabled", True): continue
            c = d.get("config", {})
            try:
                cl = AsyncModbusTcpClient(c.get("host"), port=int(c.get("port",502)))
                await cl.connect()
                fn = cl.read_input_registers if c.get("table")=="input" else cl.read_holding_registers
                rr = await fn(int(c.get("address",0)), count=2 if "32" in c.get("datatype","float32be") else 1,
                              slave=int(c.get("unit",1)))
                cl.close()
                if not rr.isError():
                    v = decode(rr.registers, c.get("datatype","float32be"))
                    push_reading(dev_id, v*float(c.get("scale",1))+float(c.get("offset",0)))
            except Exception:
                pass
        await asyncio.sleep(15)

# ── OPC-UA poller (WTP PLC tags · optional dependency) ─────────────────
async def _opcua_loop():
    try:
        from asyncua import Client as UaClient
    except Exception:
        return
    while True:
        for dev_id, d in DEVICES.items():
            if d.get("protocol") != "opcua" or not d.get("enabled", True): continue
            c = d.get("config", {})
            try:
                async with UaClient(url=c.get("endpoint")) as cl:
                    node = cl.get_node(c.get("node_id"))
                    v = await node.read_value()
                    push_reading(dev_id, float(v)*float(c.get("scale",1)))
            except Exception:
                pass
        await asyncio.sleep(max(5, int(CFG.get("opcua_poll_s", 30))))

def start_background(loop):
    loop.create_task(_rollup_loop())
    loop.create_task(_sim_loop())
    loop.create_task(_modbus_loop())
    loop.create_task(_opcua_loop())
    return _start_mqtt()

# ── query helpers for the API layer ────────────────────────────────────
def live_snapshot():
    out = []
    now = time.time()
    for dev_id, d in DEVICES.items():
        if not d.get("enabled", True): continue
        l = LATEST.get(dev_id)
        state = (l or {}).get("state", "—")
        if l and now - l["ts"] > 900: state = "STALE"
        out.append({"id": dev_id, "name": d.get("name",""), "kind": d.get("kind",""),
                    "utility": d.get("utility",""), "unit": d.get("unit",""),
                    "protocol": d.get("protocol",""), "block": d.get("block","-"),
                    "value": (l or {}).get("value"), "ts": (l or {}).get("ts"), "state": state})
    return out

def _pick_res(t_from, t_to, res):
    """auto: raw if the window is inside raw retention and short, else hourly, else daily."""
    if res in ("raw", "hour", "day"): return res
    span = t_to - t_from
    r = CFG.get("retention", {})
    raw_ok = (time.time() - t_from) <= float(r.get("raw_days", 90)) * DAY
    if span <= 2*DAY and raw_ok: return "raw"
    if span <= 120*DAY: return "hour"
    return "day"

def history(dev_id, t_from=None, t_to=None, res="auto", max_pts=2000):
    t_to = float(t_to) if t_to else time.time()
    t_from = float(t_from) if t_from else t_to - DAY
    res = _pick_res(t_from, t_to, res)
    with _lock:
        if res == "raw":
            rows = _db.execute("SELECT ts,value,value,value,1 FROM readings WHERE device_id=? AND ts>=? AND ts<=? ORDER BY ts",
                               (dev_id, t_from, t_to)).fetchall()
            # the current, not-yet-rolled hour is still in raw; nothing else needed
        else:
            tbl = "readings_h" if res == "hour" else "readings_d"
            rows = _db.execute(f"SELECT ts,avg,min,max,n FROM {tbl} WHERE device_id=? AND ts>=? AND ts<=? ORDER BY ts",
                               (dev_id, t_from, t_to)).fetchall()
            if res == "hour":       # append the live, incomplete hour from raw so the chart reaches "now"
                wm = _meta_get("hour_wm", 0.0)
                tail = _db.execute("SELECT CAST(ts/3600 AS INTEGER)*3600.0, AVG(value), MIN(value), MAX(value), COUNT(*) "
                                   "FROM readings WHERE device_id=? AND ts>=? AND ts<=? GROUP BY CAST(ts/3600 AS INTEGER) ORDER BY 1",
                                   (dev_id, max(wm, t_from), t_to)).fetchall()
                rows = rows + [r for r in tail if not rows or r[0] > rows[-1][0]]
    step = max(1, len(rows) // max_pts)
    d = DEVICES.get(dev_id, {})
    return {"device": dev_id, "name": d.get("name", ""), "unit": d.get("unit", ""), "kind": d.get("kind", ""),
            "thresholds": d.get("thresholds"), "res": res, "from": t_from, "to": t_to,
            "points": [{"ts": r[0], "v": r[1], "min": r[2], "max": r[3], "n": r[4]} for r in rows[::step]]}

def history_csv(dev_id, t_from=None, t_to=None, res="auto"):
    h = history(dev_id, t_from, t_to, res, max_pts=10**9)
    out = ["timestamp_utc,epoch_s,value,min,max,samples"]
    for p in h["points"]:
        iso = datetime.fromtimestamp(p["ts"], timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        out.append(f'{iso},{p["ts"]:.0f},{p["v"]:.6g},{p["min"]:.6g},{p["max"]:.6g},{p["n"]}')
    return "\n".join(out) + "\n", h

def series(dev_id, hours=24, max_pts=500):
    """Kept for the existing /api/readings endpoint: same shape as before, auto resolution."""
    h = history(dev_id, time.time() - hours*3600, None, "auto", max_pts)
    return [{"ts": p["ts"], "v": p["v"]} for p in h["points"]]

def alarms_tail(n=100):
    try:
        with open(ALARM_FILE) as f: lines = f.readlines()[-n:]
        return [json.loads(x) for x in lines]
    except Exception: return []
