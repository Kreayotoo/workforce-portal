# Datasets

This folder holds the data behind the twins, in two forms.

## 1. `data_json/` — structured per-block datasets  (`<BLOCK>_network.json`)
One JSON per block. This is the exact data each twin runs on (it is embedded
inside the twin HTML; here it is extracted and pretty-printed so you can read,
query, or re-use it). All coordinates are UTM Zone 44N / WGS-84 (EPSG:32644).

Top-level keys:

- `meta` — `zone`, `block`, `grid`, `center_E`, `center_N` (block centroid in
  UTM, all 3D coords are relative to it), `aboveground` (false = no city layer).

- `stats` — per utility (`water`,`sewer`,`strom`,`reuse`,`power`):
  `label`, `count` (segments), `length_m`, `avg/max/min_dia` (mm),
  `min/max_inv` (invert RL, m).

- `networks` — per utility, an array of pipe segments. Each segment is
  `[relE_start, relN_start, inv_start, relE_end, relN_end, inv_end]`
  where relE/relN are metres from the centroid and inv is the invert level (m).

- `geo` — per utility, the same segments as `[startLat, startLon, endLat, endLon]`
  (for the GIS map).

- `dims` — per utility, per segment `[shapeCode, width_mm, height_mm]`
  (shapeCode 1 = box e.g. storm/power, 0 = circular).

- `nodes` — the manhole / chamber schedule. Each node:
  `u` utility, `sid` structure id, `x,z` (relative metres), `E,N` (UTM),
  `inv` (sump RL), `rim`/`frl` (cover RL), `dia` (m), `len` (m, 0 if circular),
  `coneH`, `neck`, `rot` (deg), `shape` (`cyl`|`box`), `pipes` (connected),
  `deg` (connections), `lat,lon`, `real:1` (from the schedule, not synthetic).

- `road` — the ground / FRL surface as a grid:
  `x0,z0` (grid origin, relative m), `dx` (5 m spacing), `nx,nz` (grid size),
  `emin,emax`, `h` (row-major elevations; h[j*nx + i] at (x0+i*dx, z0+j*dx)).

- `frl` — `level` (representative FRL), `note`, `src`.

- `map` — `center` [lat,lon], `bounds` [[s,w],[n,e]], and linear
  metre→degree factors for overlaying the 3D on the map.

## 2. `source_workbooks/` — raw Civil 3D exports
The original Civil 3D quantities workbooks for the 20 file-based blocks (Zones 5A, 5C, 5D, 10, 12). Each
contains the pipe sheets (Water/Sewer/Storm/Power/Reuse) and the manhole sheets
(Power/Storm/Sewer) with coordinates, inverts, diameters, rim & sump levels,
chamber dimensions, cone height and rotation. `../build_pipeline/build_block.py`
turns these into the `data_json` above.

## Provenance & honesty
- The geometry, diameters, levels and connectivity in these datasets are REAL,
  taken directly from the Civil 3D exports.
- Every file-based block `road` surface is INTERPOLATED from the manhole rim levels (these
  blocks shipped without a LandXML FRL).
- **Z1B-B5**: its `Z1B_B5_network.json` was produced from that block's own
  Civil 3D export **plus a surveyed LandXML FRL surface and structure schedule**;
  those raw source files are not part of this Zone-5 bundle, so only the finished
  dataset is included here.
- Flow / pressure / water-quality / SCADA values are NOT in these datasets — they
  are generated as demo animation in the viewer only.
