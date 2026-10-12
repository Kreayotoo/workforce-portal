# Amaravati Digital Twin — FastAPI Backend Server
**Kreayotoo Solutions (P) Ltd**

A lightweight backend that makes the twin run **smoothly 24/7** without the browser getting stuck.
Instead of loading 33 MB at once, the browser gets only what it needs, when it needs it.

---

## What this server does

| Without server | With server |
|---|---|
| 33 MB HTML loads at once | Each block loads on demand (~1–3 MB) |
| Browser does all computation | Server runs GIS buffer, storm model |
| Alert polling every 20s | WebSocket push — alerts arrive instantly |
| Tab close = data lost | All logs and history persist |
| One user only | Multiple users, same live data |

---

## Quick start (trial — run on your laptop)

### 1. Install dependencies (once)
```bash
pip install fastapi uvicorn websockets aiofiles python-multipart pyproj --break-system-packages
```

### 2. Prepare the data (once, or after any network update)
```bash
cd server/
python3 prepare_data.py
```
This extracts block JSONs, plots, network data and zone storm capacity from your twin build outputs.

### 3. Start the server
```bash
python3 -m uvicorn main:app --host 0.0.0.0 --port 8000
```
Or use the start script:
```bash
./start.sh
```

### 4. Open in browser
```
http://localhost:8000          ← live monitoring dashboard
http://localhost:8000/docs     ← auto-generated API documentation
```

From another computer on the same network:
```
http://YOUR_PC_IP:8000
```

---

## API endpoints

| Method | Endpoint | What it returns |
|---|---|---|
| GET | `/` | Live monitoring dashboard HTML |
| GET | `/api/status` | Server health, last update times |
| GET | `/api/weather` | Cached Open-Meteo weather (refreshed every 10 min) |
| GET | `/api/storm` | Per-zone storm utilisation (live rainfall → real Manning capacity) |
| GET | `/api/alerts` | Current alert feed (sensor sim + live rainfall) |
| GET | `/api/blocks` | Manifest of all 21 blocks |
| GET | `/api/block/{code}` | Single block network JSON (lazy load) |
| GET | `/api/sensors` | All sensor readings (snapshot) |
| POST | `/api/buffer` | GIS buffer analysis → `{lat, lon, radius, scenario}` |
| WS | `/ws/alerts` | WebSocket — alerts pushed every time they change |
| WS | `/ws/sensors` | WebSocket — sensor readings pushed every 20s |

---

## Connecting to real SCADA

Edit `main.py` and set your endpoint:
```python
# In main.py, replace the sensor tick with a real feed:
SCADA_ENDPOINT = "http://your-scada-server/api/alerts"
```

Or use the ALERT_FEED_URL pattern — the server will poll it every 20 seconds and
push any changes to all connected WebSocket clients immediately.

---

## Deploying to a cloud server (production)

### Option A — Hetzner CX22 (~₹800/month, recommended)
```bash
# On the server:
git clone your-repo / scp the server/ folder
pip install -r requirements.txt
# Run with systemd so it restarts automatically:
sudo systemctl enable amaravati-twin
sudo systemctl start amaravati-twin
```

### Option B — Docker (any cloud)
```bash
docker-compose up -d
```
Access at `http://server-ip:8000`

### Option C — Vercel + Railway (free tier)
- Frontend (monitor.html) → Vercel (free)
- Backend (FastAPI) → Railway (free tier, 500 hours/month)

---

## Requirements

```
fastapi>=0.100.0
uvicorn>=0.23.0
websockets>=11.0
aiofiles>=23.0
python-multipart>=0.0.6
pyproj>=3.5.0
```

---

## File structure

```
server/
├── main.py              ← FastAPI backend (all endpoints + WebSocket + sensor sim)
├── prepare_data.py      ← One-time data extraction from your twin build
├── start.sh             ← Quick start script
├── README.md            ← This file
├── requirements.txt     ← Python dependencies
├── templates/
│   └── monitor.html     ← Live monitoring dashboard
└── static/
    ├── logo.png          ← Kreayotoo logo (copied from build)
    ├── data/
    │   ├── manifest.json      ← 21 block metadata
    │   ├── plots.json         ← 95,935 plot centroids (GIS buffer)
    │   ├── incident_net.json  ← 78,053 pipes + 43,685 chambers
    │   └── zone_storm.json    ← Real Manning capacity per zone
    └── blocks/
        ├── 5C_B1.json         ← Block network (lazy loaded)
        ├── 5C_B2.json
        └── ...                ← (21 block JSONs)
```

---

*Engineering · Solutions · Innovation — Kreayotoo Solutions (P) Ltd*

## O&M Phase 2 (shared store)
When this server runs (`./start.sh`, port 8000), the app's **O&M · Maintenance** screen auto-detects it and switches from the browser-local store to the shared server store (`om_store.json`): work orders, PM completions and the commissioning date become common across all users on the network. Endpoints: `GET/POST /api/om/store`.
