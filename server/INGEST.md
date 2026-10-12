# Connecting Devices — Any Brand, Any Protocol

The platform is **vendor-agnostic by design**: all mapping lives in configuration
(`devices.json`, `ingest.json`), never in code. Four doors in, one pipeline inside:
every reading flows through the same threshold → alarm → auto-work-order engine,
into the SQLite time-series (`readings.db`) and the Live Data screen.

## 1 · Universal REST / webhook (works with EVERYTHING)
Any datalogger, gateway, or vendor cloud that can make an HTTP call:
    POST /api/ingest            {"device_id":"FM-Z1B-01","value":118.4}
    POST /api/ingest/batch      [{"device_id":"FM-1","value":10}, ...]
    GET  /api/ingest?device_id=FM-1&value=10.5      (for the dumbest loggers)
Register the device first (Admin/Engineer):
    POST /api/devices {"id":"FM-Z1B-01","name":"Bulk flow Z1B","kind":"flow",
      "utility":"water","unit":"LPS","protocol":"rest","block":"Z1B_B5",
      "thresholds":{"lo":60,"hi":170}}

## 2 · MQTT (any broker · any payload shape)
Enable in `ingest.json` and describe how to find the device id and value:
  - JSON payloads:   "device_from":"json:device_id", "value_from":"json:data.flow"
  - Bare numbers:    "device_from":"topic:-1",       "value_from":"payload"
Wildcards (`+`, `#`) supported — one rule can serve a thousand sensors.

## 3 · Modbus-TCP (meters, RTUs, VFD-driven pumps — any make)
Per device in `devices.json`:
    "protocol":"modbus","config":{"host":"10.0.0.21","port":502,"unit":1,
      "table":"holding","address":3000,"datatype":"float32be","scale":1,"offset":0}
Datatypes: uint16 · int16 · float32be · float32le. Take address/datatype from the
vendor register map — that is the only brand-specific fact ever needed.

## 4 · OPC-UA (WTP / plant PLCs)
    pip install asyncua      then per device:
    "protocol":"opcua","config":{"endpoint":"opc.tcp://10.0.0.5:4840",
      "node_id":"ns=2;s=Plant.ClearWater.FlowLPS"}
**Monitoring first.** Writing setpoints back to plant equipment is deliberately
NOT enabled — control belongs with the PLC/SCADA interlocks until a joint
commissioning + safety review authorises specific write tags.

## Simulated demo devices
Three `protocol:"sim"` devices ship enabled so the whole chain is visible with
zero hardware. They are labelled SIMULATED — delete or disable them when real
devices arrive.

## Sizing honesty
5,000 devices at 1-minute reporting ≈ 83 msg/s — one office server. For that
scale run an MQTT broker (Mosquitto) in front and move `readings.db` to
PostgreSQL/TimescaleDB; the code path stays identical.

## Historical data · retention · export

Every reading is stored in `readings.db` (SQLite, WAL mode) and rolled up automatically:

| Table        | Bucket          | Kept for          | Config key     |
|--------------|-----------------|-------------------|----------------|
| `readings`   | raw, as received| 90 days           | `raw_days`     |
| `readings_h` | 1 hour (UTC)    | 730 days          | `hourly_days`  |
| `readings_d` | 1 day (UTC)     | for ever (`0`)    | `daily_days`   |

Roll-ups run every 10 minutes for completed hours/days only, and raw data is never
deleted before it has been rolled up. Each aggregate row carries `avg · min · max · n`.
Edit the `retention` block in `ingest.json` to change the policy; `POST /api/retention/rollup`
(Admin/Engineer) runs a cycle immediately.

### Query
    GET /api/history/{device}?hours=168            auto resolution
    GET /api/history/{device}?frm=<epoch>&to=<epoch>&res=raw|hour|day
    GET /api/retention                              row counts, date ranges, policy, DB size
Auto resolution: raw for windows ≤ 2 days (inside raw retention), hourly ≤ 120 days, daily beyond.
The current, incomplete hour is appended from raw so charts reach "now".

### Export
    GET /api/readings/{device}.csv?hours=720&res=hour
Returns `timestamp_utc, epoch_s, value, min, max, samples` with a download filename.
Every export is written to the audit log with user, device, resolution and row count.

### In the app
O&M → Live Data → HISTORY: pick a device (or click its row), choose a range and resolution,
Load, then Download CSV. Min–max band is drawn for hourly/daily; threshold lines from the
device's `lo`/`hi` are overlaid.

### Sizing
At 1-minute reporting, one device adds ~1.4 MB of raw data per 90 days and ~1 KB per year of
daily history. 200 devices ≈ 280 MB raw steady-state. Beyond ~5,000 devices move to
PostgreSQL/TimescaleDB — the API and roll-up logic are unchanged.
