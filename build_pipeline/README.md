# Build pipeline — Amaravati utility digital twins

This regenerates the twins from the Civil 3D **quantities workbooks**, and is
the basis for scaling to all 80 blocks.

## Files
- `dashboard_template.html` — the single-file twin template. Contains two
  placeholder tokens, `__NETDATA__` (the block's data) and `__LOGO__` (the
  logo). All rendering code (Three.js 3D, Leaflet GIS, controls, flow,
  parametric manholes) lives here.
- `logo_b64.txt` — base64 logo injected into `__LOGO__`.
- `build_block.py` — parses each `*_All_Utilities_Quantities.xlsx` into the
  template and writes one twin per block, plus a `manifest.json`.
- `make_index.py` — builds the multi-file launcher (`index.html`) from the
  manifest (for http hosting).
- `make_single.py` — builds the single self-contained `Amaravati_Twins_AllInOne.html`
  (all blocks embedded; works off disk).

## What `build_block.py` does, per block
1. Reads the pipe sheets (Water/Sewer/Storm/Power/Reuse) and manhole sheets
   (Power/Storm/Sewer), fuzzy-matching the inconsistent sheet names
   (`PMH`/`Power Manholes`, `SMH`/`FSMH`/`Storm Drains`, …).
2. Pulls real coordinates, inverts, diameters, rim/sump levels, chamber
   dimensions, cone height and rotation.
3. Converts UTM Zone-44N coordinates to lat/long with `pyproj` (for the map)
   and recenters everything on the block centroid (for precise 3D).
4. Interpolates the manhole rim levels into a 5 m road-surface grid with
   `scipy` (since these blocks have no LandXML FRL).
5. Assembles one compact `network.json` and injects it into the template.

## Requirements
```
pip install openpyxl numpy scipy pyproj
```

## Run
Edit the input/output paths at the top of `build_block.py` (they point at the
upload + package folders used during delivery), put the 8 quantities workbooks
in the input folder, then:
```
python build_block.py     # -> blocks/*.html + manifest.json
python make_index.py      # -> index.html (hosted launcher)
python make_single.py     # -> Amaravati_Twins_AllInOne.html (single file)
```

## Adding a new block
Drop its `*_All_Utilities_Quantities.xlsx` into the input folder and re-run the
three commands. To use a real surveyed road surface instead of the rim
interpolation, supply the block's LandXML FRL and extend the parser to sample
it (Zone 1B-B5 already uses this path).

## Notes
- Geometry, diameters, levels and connectivity are REAL. Flow / quality /
  SCADA values are simulated demo data. The Zone-5 road surface is interpolated
  from rim levels.
- The inconsistent sheet names across the 8 files are exactly why a single
  export **format standard** should be fixed before processing all 80 blocks.

## make_webapp.py
Builds the deployable web app (overview map + on-demand viewer) into webapp/. Run after make_index/make_single.
