# Decision Support & Impact Simulation
### Amaravati Underground Utility Digital Twin — Kreayotoo Solutions (P) Ltd

---

## 1. What was added

A new **Decision Support** view in the app (purple button in the sidebar). It turns the twin from a
*visualisation* tool into a *decision* tool: you place an incident on the map, and the twin answers
**who is affected, what is affected, and what should be done.**

This implements, on real data, the core of the DSS architecture you outlined:
**buffer analysis · impact simulation · locality-based simulation · scenario simulator · risk map ·
recommended actions.**

---

## 2. How to use it

1. Open `Amaravati_Twins_App.html` → click **Decision Support**.
2. Pick a **scenario** at the top: Pipe Burst · Contamination · Power Failure · Heavy Rain/Flood · Fire.
3. **Tap anywhere on the map** to place the incident.
4. Adjust the **buffer radius** slider (50 m – 1000 m).

The twin instantly recalculates and shows:

The header always shows **which zone/block the incident is in**, the coordinates, and a **risk gauge**
(0–100 → LOW / MEDIUM / HIGH / CRITICAL). Below it are **four tabs**:

**① IMPACT** — who is affected
- Population · households · plots · hectares · **water demand at risk (MLD)** · **road reserve (km)**
- **Critical facilities** with the distance to the nearest one (schools, hospitals, government, cultural)
- **Breakdown by distance ring** (inner / middle / outer third of the buffer)
- **Full landuse table** — every zone in the buffer with plots, hectares and population
- **📋 Generate incident report** button

**② NETWORK** — what is affected
- Every utility in the buffer: pipe count, km, largest diameter, chambers
- Deepest chamber (excavation depth)
- The affected utility broken down **by diameter class**
- **Isolation points V1–V4** with distances

**③ ACTIONS** — what to do
- An **interactive checklist** with a progress bar — tick actions off as they're done
- Each action has a **time window** ("within 15 min") and a **confidence** level
- Below it, the full **reasoning** for every recommendation

**④ TIMELINE** — what happens next
- A **predicted chart** over time (e.g. supply % and cumulative water lost after a burst;
  contaminant front and population exposed; tank drawdown with and without DG backup)
- **Milestones** — "0 min burst begins · 25 min valves closed, 12,400 people lose supply ·
  9.4 hr repair complete · 10.4 hr supply restored"

**Map controls:** toggle **Landuse / Network / Affected plots**, **Jump to block**, and
**⚡ Random incident**. The map shows buffer rings, **affected pipes in red**, the **isolation valves**,
and **every affected plot as a coloured dot** in its zoning colour.

**Incident report** — one click produces a full text report (impact, landuse breakdown, network,
isolation points, actions, timeline, and the real-vs-modelled caveats) ready to copy into an email
or a log.

---

## 2A. Alert-driven operation (new)

The dashboard now opens with a **🔔 Alert feed**. Click any alert and the twin **automatically**
places the incident at the alert's location, selects the matching scenario, sets the buffer, and runs
the full impact analysis — a banner shows *"Responding to WX-10 · Zone 10 storm drains at 118% capacity"*.

**alert → location → buffer → impact → recommended action**, in one click.

### Where the alerts come from

| Alert type | Source | Status |
|---|---|---|
| **Flood / storm** | **Open-Meteo live rainfall** vs your **real Manning drain capacity** per zone | **● LIVE — genuinely real.** Fires when forecast peak intensity (with antecedent-wetness correction) pushes a zone's drains past 50% of capacity. If it isn't going to rain, there is no alert — which is the honest behaviour. |
| **Burst / pressure / quality / power** | **Demo sensor network** — a virtual SCADA of ~50 sensors across your 21 blocks | **◐ SIMULATED, but genuinely dynamic.** Not a fixed list: readings move every 20 s and faults appear, escalate and clear on their own. |

### The demo sensor network (why the alerts keep changing)

The twin runs a **virtual SCADA** so the demo behaves like the real thing:

- **~50 virtual sensors** across the 21 blocks — **pressure transmitters (PT)**, **DMA flow meters (FM)**,
  **chlorine analysers (CL)** and **pump monitors (PU)**.
- Every reading follows a **real diurnal pattern** (night trough, morning and evening peaks) with noise,
  recomputed **every 20 seconds**.
- **Faults spawn at random**, **ramp up** over 2–8 minutes, and **clear** after 8–35 minutes.
- **Every alert in the feed is a threshold breach on one of those readings** — pressure below 2.35 bar →
  burst; flow +45% → leak; chlorine below 0.20 mg/L → quality; pump below 35% load → power.
  **This is exactly how SCADA alerting works.**

So the alert count genuinely moves (2 → 5 → 3), alerts **escalate** as a fault worsens
(medium → high → critical), and they **disappear** when the fault clears — and because the decision
engine re-runs on every change, **the impact analysis, risk score and actions follow along by themselves.**

The **Sensors tab** shows every reading live, with the ones in alarm at the top — so you can see the
alert being born from the data.

**When you connect SCADA:** set `ALERT_FEED_URL` — the simulator switches off and the identical
machinery runs on your real telemetry. Nothing else changes.

### Continuous operation — the decision updates itself

The feed is re-checked **every 60 seconds** and the twin *diffs* it against the previous poll:

| What happens in the feed | What the twin does |
|---|---|
| **New alert arrives** | A **toast** pops up (click it to analyse). The alert is tagged **NEW** in the feed. Logged as `received`. |
| **New CRITICAL alert** | With **auto-analyse** on (default), the twin **immediately switches the analysis to it** — new buffer, new population, new actions. Logged as `auto-analysed`. |
| **An alert escalates** (e.g. medium → critical, or rainfall rises so a zone goes 70% → 118% of drain capacity) | If you are working on that alert, the **impact is recalculated automatically** — risk score, affected population, actions and timeline all update. Logged as `escalated` + `re-analysed`. |
| **An alert clears** | Marked resolved; logged as `resolved`. |
| **Nothing changed** | The active analysis still refreshes against the latest data, so the numbers never go stale. |

You never have to re-click anything: **as the feed moves, the decision moves with it.**

### Acknowledge + audit log

- Each alert has an **ACK** button (acknowledged alerts are marked, so a team knows it's been seen).
- **Auto-analyse new critical alerts** can be switched off if you'd rather stay on your current incident.
- The **Log** tab is a full **audit trail** of the session: every alert `received`, `escalated`,
  `acknowledged`, `analysed`, `re-analysed`, `auto-analysed`, each **action ticked off**, every
  `report` generated, and every `resolved` — each with a timestamp and the alert ID.
- **⬇ Export log** produces a plain-text audit record you can file or email.

### In the main app

The **Decision Support** button in the sidebar carries a **live alert badge**. It counts the real
rainfall alerts (checked against your actual drain capacity every 10 minutes) plus the simulated
SCADA placeholders, and **pulses red** when any alert is critical — so you see trouble without
opening anything.

### Connecting your real SCADA/IoT feed

In `decision_dashboard.html` there is one line:

```js
const ALERT_FEED_URL = "";   // ← your SCADA / MQTT bridge endpoint
```

Set it to an endpoint that returns this JSON and the twin goes **fully live** — the simulated alerts
disappear and every alert becomes a real one:

```json
[
  {
    "id":       "A-1042",
    "type":     "burst",           // burst | pressure | quality | power | flood | fire
    "severity": "critical",        // critical | high | medium
    "lat":      16.5124,
    "lon":      80.5088,
    "ts":       "2026-07-11T09:14:00Z",
    "source":   "SCADA:PT-3312",
    "msg":      "Pressure drop 41% on the 600 mm trunk main",
    "value":    "1.9",
    "unit":     "bar (was 3.2)",
    "radius":   250
  }
]
```

The twin polls it every 10 minutes (and on open). Anything your MQTT broker, InfluxDB rule, or
.NET API can emit in that shape will drive the decision engine. **That is the whole integration** —
the rest of the chain (buffer, impact, population, isolation valves, actions) already works.

---

## 2B. Fault localisation & uncertainty (new)

**A single sensor cannot tell you *where* on the pipe the fault is** — only that pressure/quality
changed somewhere in its hydraulic zone. The twin now shows this honestly:

- When a sensor alert is opened, the twin **traces the hydraulically connected pipe run** around
  that sensor (BFS over shared pipe endpoints, ≈2.6 km) and draws it as a **dashed orange
  "suspected section"** — the burst is *somewhere on this run*, not at the marker.
- If **two or more sensors of the same utility** are in alarm and their runs share pipes, the twin
  shows only the **overlap in yellow** — "narrowed by N sensors to X.XX km". This is exactly how
  real multi-sensor localisation starts.
- The header states the uncertainty explicitly, and that precise location (±45 m, SIWA-level)
  needs high-frequency transient loggers — roadmap Phase 2–4.

| Localisation stage | Accuracy | Twin status |
|---|---|---|
| Single sensor → connected run | ~2.6 km section | ✅ built (this update) |
| Multi-sensor overlap | few hundred m | ✅ built — narrows automatically |
| EPANET model matching | 100–200 m | Phase 3 (needs hydraulic model) |
| Transient wave timing | ~45 m | Phase 2/4 (needs high-freq loggers) |
| Acoustic correlation on site | 1–2 m | Field crew equipment |

Manual map-tap incidents clear the sensor context (no run is drawn — you chose the point yourself).

---

## 3. How it works — the data flow

```
        Masterplan shapefile              Civil 3D network
     (95,935 zoned plots, QML)        (78,409 pipes, 44,122 chambers)
                 │                                │
                 ▼                                ▼
        plots.json (centroid,              incident_net.json
         zone, area, in metres)        (pipes + chambers, in metres)
                 │                                │
                 └──────────────┬─────────────────┘
                                ▼
                    Incident point (lat/lon from your tap)
                                │
                    converted to local metre grid
                                ▼
              ┌─────────────────────────────────────┐
              │  SPATIAL QUERY (real GIS buffer)    │
              │  • plots  within radius             │
              │  • pipes  within radius             │
              │  • chambers within radius           │
              └─────────────────────────────────────┘
                                │
              ┌─────────────────┴─────────────────┐
              ▼                                   ▼
      IMPACT MODEL                          RULE ENGINE
  population = Σ(plot area ×             IF/THEN rules per scenario
    zoning density)                      → recommended actions
  leak rate, spread, drawdown            → confidence
  risk score                             → reasoning shown to you
              └─────────────────┬─────────────────┘
                                ▼
                        Decision dashboard
```

### 3.1 The buffer analysis (this is a genuine GIS query)

Every one of the **95,935 masterplan plots** is stored with its **centroid, zoning class and area**.
When you tap the map, the twin computes the distance from the incident to every plot and selects
those inside the radius. It then groups them by zoning class and sums the areas. This is exactly
the *"pipe bursts → 100 m buffer → what's inside"* analysis in your brief — done on your real
masterplan, not a mock-up.

The same query runs against the **network**: pipe mid-points and chambers inside the radius give the
km of each utility affected, the largest diameter present, and the chamber count.

### 3.2 Population estimate

Population is **not** measured — it is derived:

```
population = Σ over plots in buffer ( plot area (ha) × density of its zoning class )
```

Densities are planning assumptions per zone, e.g. R3 (medium-high density) 250 persons/ha,
R4 (high density) 400, C2 (general commercial) 80, parks ~2, roads 0. **Swap in census or
consumer-connection data and this becomes exact.**

### 3.3 Critical facilities

Plots whose zoning is an **Education**, **Health**, **Government** or **Cultural** zone are counted
separately — this is what drives the "hospital in the buffer → priority" rule.

### 3.4 Isolation points

The nearest chambers on the affected utility are ranked by distance and marked **V1–V4**. These are
*candidate* isolation points from the real network geometry.
*(A true minimum-valve-set calculation needs the valve register — see §6.)*

### 3.5 The rule engine

Each scenario runs a transparent set of IF/THEN rules. Nothing is hidden — every card shows the
reasoning. Examples:

**Pipe Burst**
- Discharge from the rupture is estimated with the orifice equation
  `Q = Cd · A · √(2gH)` — assuming 20% of the bore open at 30 m head, Cd = 0.62.
- → "Isolate the main" (confidence High if ≥600 mm), "Notify N consumers",
  "Priority: health facility in the zone" (only if a health plot is inside), "Estimated restoration".

**Contamination**
- Advance along the main at a typical 0.9 m/s ≈ **3.2 km/hr**; flushing volume from pipe bore × length.
- → isolate, public-health advisory, flush & re-chlorinate to 0.5 mg/L.

**Power Failure**
- Demand from affected population at 135 LPCD; typical 8-hour storage → time to supply loss.
- → DG backup within 30 min, restoration priority ranked by population and critical facilities.

**Heavy Rain / Flood**
- Storm-drain km and max diameter in the buffer; chambers at risk of surcharge.
- Links to the **live rainfall** already in the Weather dashboard.

**Fire**
- Nearest water chamber as hydrant point; fire-flow requirement 30–60 L/s at 2 bar residual.

### 3.6 Risk score

```
risk = population/220  +  4 × (weighted critical facilities)  +  1.4 × (km of network in buffer)
       × 1.25 for contamination / fire
```
Capped at 100 → LOW / MEDIUM / HIGH / CRITICAL.

---

## 4. What is REAL vs MODELLED — read this

| | |
|---|---|
| **● REAL** (your data) | Plot geometry, zoning class, plot areas (masterplan shapefile, 95,935 plots) · pipe geometry, diameters, lengths, chamber positions & depths (Civil 3D) · the buffer intersection itself · landuse map · satellite imagery |
| **◐ MODELLED** (assumptions, clearly labelled) | Population (plot area × zoning density — *not* census) · leak discharge, contaminant travel, tank drawdown (standard hydraulic formulae, not a solved network) · restoration times · the risk-score weights |
| **○ NOT A TRAINED AI** | The "decision engine" is a **deterministic rule engine**, not a machine-learning model. It is honest, explainable and useful — but it does not learn. Confidence levels are rule-based, not statistical. |
| **✗ NOT POSSIBLE YET** | Live sensor values (no SCADA/IoT feed) · true hydraulic pressure/flow after a break (needs EPANET) · flood **depth** (needs a DEM) · predictive maintenance (needs failure history) · leak *pre-location* (needs DMA meters) |

**In short:** the *spatial intelligence* is real and running on your data today. The *sensor
intelligence* is waiting on instrumentation.

---

## 5. Your 16 modules — where each one stands

| # | Module | Status |
|---|---|---|
| 1 | Live monitoring | ⚠️ Needs SCADA/IoT. Twin is ready to receive it. |
| 2 | AI decision engine | ✅ **Built** — as a transparent rule engine (upgrade to ML later) |
| 3 | **Buffer analysis** | ✅ **Built, fully real** — plots, population, schools, hospitals, roads |
| 4 | Impact simulation | ✅ **Built** (spatial + network). Hydraulic re-solve needs EPANET |
| 5 | Locality-based simulation | ✅ **Built** — zoning, density, network per locality |
| 6 | Predictive maintenance | ✗ Needs failure history + asset condition data |
| 7 | Water-quality simulation | ◐ Contamination scenario models spread/flush. Real quality needs sensors |
| 8 | Leak detection | ⚙️ Was built (DMA night-flow) — **removed at your request**, can be restored |
| 9 | Flood simulation | ◐ Storm capacity + live rain done. **Depth needs a DEM** |
| 10 | Fire-hydrant decision | ✅ **Built** — nearest point, pressure requirement |
| 11 | Water-demand prediction | ◐ Weather-driven demand is in the Weather dashboard |
| 12 | Valve optimisation | ◐ Nearest isolation points shown. Minimum-valve-set needs the valve register |
| 13 | Scenario simulator | ✅ **Built** — 5 scenarios |
| 14 | Time travel | ✗ Needs a time-series database of history |
| 15 | Risk map | ✅ **Built** — risk score + colour-coded buffer |
| 16 | AI chat assistant | ✗ Needs the live data layer first (would otherwise invent answers) |

---

## 6. What you need next (in priority order)

1. **DEM / terrain model** → unlocks real flood depth, evacuation routes, and pressure-by-elevation.
2. **Valve & hydrant register** (locations + type) → turns "nearest chamber" into true valve optimisation.
3. **SCADA / IoT feed** (flow, pressure, level, quality) → replaces every ◐ with live measured values.
4. **Consumer/connection data** → replaces the zoning-density population estimate with real consumers.
5. **EPANET model** (buildable from data you already have) → real hydraulic re-solve after a break.
6. **Failure & maintenance history** → enables predictive maintenance and burst-risk models.

Items 1, 2 and 4 are **data you likely already have** — they would sharply increase accuracy without
any new hardware.

---

## 7. Files added to the package

| File | Purpose |
|---|---|
| `build_pipeline/decision_dashboard.html` | The Decision Support dashboard (template) |
| `build_pipeline/build_incident_data.py` | Extracts plot centroids + network into the compact analysis datasets |
| `datasets/decision/plots.json` | 95,935 plot centroids, zoning class, area, coordinate transform |
| `datasets/decision/incident_net.json` | 78,409 pipes + 44,122 chambers as metre offsets |
| `docs/DECISION_SUPPORT.md` | This document |

Everything is embedded in `Amaravati_Twins_App.html` — the app still runs **offline by double-click**
(internet only for the map tiles).

---

*Kreayotoo Solutions (P) Ltd · Engineering · Solutions · Innovation*
