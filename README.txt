================================================================================
  AMARAVATI CAPITAL CITY — UNDERGROUND UTILITY DIGITAL TWIN
  Kreayotoo Solutions (P) Ltd  ·  "We Create for You"
  Full package — app, data, code
================================================================================

WHAT THIS IS
------------
A digital twin of Amaravati's underground utility infrastructure across 21
blocks in 6 zones (78,000+ pipes · 43,000+ manholes · ~2,131 km), plus the
city-wide trunk main transmission network (2,319 pipes · 117 km, 500–2500 mm)
and the WTP Admin building (architectural + structural BIM). Geometry, pipe
diameters, invert levels and connectivity are REAL, from Civil 3D / DXF / Revit.
Flow, pressure, quality and SCADA telemetry are SIMULATED for demonstration.


================================================================================
  1. OPEN THIS FIRST  —  Amaravati_Twins_App.html
================================================================================
One self-contained file. Just DOUBLE-CLICK it (no server, no install).
It contains everything in one app:

  • Sidebar: zone -> block navigator
  • Individual block 3D twin (pick any block)
  • Whole-ZONE combined 3D view (stacked-layers button on each zone)
  • Whole-CITY 3D view ("Entire City" — all 21 blocks in one scene)
  • Trunk Main transmission network (its own button)
  • WTP Admin Building — the BIM model (its own button)
  • Overview GIS map (right) — satellite basemap, block markers, the trunk
    main drawn over it, and the building marker
  • Dark 3D dashboard, free pan/zoom (drag = orbit, 2-finger/right-drag = pan,
    pinch/scroll = zoom — into ANY point, never re-centred)
  • Alerts: tap "locate on map" -> jumps to the GIS map and zooms to that spot
  • Decision Support: place an incident on the map -> REAL GIS buffer against the
    95,935-plot masterplan + your 78,053-pipe network -> population & plots affected,
    schools/hospitals in the zone, pipes & chambers hit, isolation points, and
    recommended actions (rule engine). See docs/DECISION_SUPPORT.md
  • Live Weather & Storm Risk: REAL rainfall/temperature/7-day forecast for
    Amaravati (Open-Meteo, live) driving a SIMULATED storm-drain utilisation,
    water-demand and raw-water response (rational-method + Manning demo model)

  NOTE: needs an internet connection (loads 3D + map libraries and the
  satellite basemap from CDNs). If you see an old version, it is your browser
  cache — hard-refresh (Ctrl+Shift+R) or open in a private/incognito window.


================================================================================
  2. Amaravati_WTP_Admin_Building.html   (the BIM building on its own)
================================================================================
Double-click. The WTP Admin building in 3D — architecture + structure combined:
  • Real Revit material colours (aluminium, glass, concrete, wood, paint, tiles)
  • Structural concrete frame (731 beams, 195 columns, 141 slabs, stairs)
  • Buttons: Building on/off · X-ray (see the frame inside) · Edges · Auto-rotate
  • Orbit + pinch-zoom (desktop + mobile)


================================================================================
  3. webapp/   (the hosted / deployable version)
================================================================================
Same app but as a multi-file web app for hosting (better for scaling to many
blocks later). One page = sidebar + 3D viewer + overview map.
  • Deploy: drag the "webapp" folder onto vercel.com  (or any static host)
  • Or run locally:  cd webapp  &&  python -m http.server 8080
    then open http://localhost:8080
  IMPORTANT: the webapp must be SERVED — double-clicking webapp/index.html will
  not load the twins (browsers block file:// iframes). Use the single-file
  Amaravati_Twins_App.html for double-click use instead.


================================================================================
  4. datasets/   (all the data)
================================================================================
  data_json/            21 block networks + Trunk_Main + (compact JSON each)
  source_workbooks/     original Civil 3D quantity spreadsheets + Trunk_Model.dxf
  building_source/      Revit IFC exports (architectural + structural),
                        resolved material-colour maps (JSON), and the combined
                        building glb (Draco-compressed)
  building_real_draco.glb   the WTP Admin building (AR+ST) used by the app

  network JSON schema is documented in datasets/README.md


================================================================================
  5. build_pipeline/   (all the code)
================================================================================
  dashboard_template.html   the twin template (3D viewer + GIS map + dashboard)
  building_viewer.html      the standalone BIM viewer template
  logo_b64.txt              Kreayotoo logo (base64)

  build_block.py            Civil 3D xlsx  -> per-block network + twin
  build_trunk.py            Trunk_Model.dxf -> trunk network + twin
  build_combined.py         merges blocks  -> per-zone + whole-city twins
  ifc_to_glb.py             IFC style traversal: element -> real Revit colours
  build_glb_geo.py          IFC geometry -> coloured glb (uses colour map)
  build_combined_glb.py     merges architectural + structural IFC -> one glb
  recolor_glb.py            (legacy) colour an FBX glb by Revit category
  make_app.py               builds the single-file Amaravati_Twins_App.html
  make_webapp.py            builds the hosted webapp
  make_single.py / make_index.py   (older builders, kept for reference)

  Rebuild the building glb:
     python3 ifc_to_glb.py            # (resolves AR colours -> elem_color.json)
     python3 build_combined_glb.py    # AR + ST -> building.glb
     # then Draco-compress with gltf-pipeline (npm) and rebuild make_app.py
  Requires: python3 (ifcopenshell, trimesh, numpy, scipy, pyproj, pillow),
            node + npm (gltf-pipeline for Draco).


================================================================================
  HONEST NOTES
================================================================================
  • Real:      geometry, pipe diameters, invert levels, connectivity, building
               material COLOURS (from the IFC surface styles).
  • Simulated: flow, pressure, water quality, energy, SCADA/telemetry (demo).
  • Trunk main is a plan-level schematic (no invert levels in the DXF) — placed
    at the city's representative ground level (~23 m).
  • Zone road surfaces are interpolated from manhole rim levels (not surveyed);
    block 1B-B5 uses a real surveyed LandXML surface.
  • Building placement is APPROXIMATE (city centre) until the Revit survey-point
    Easting/Northing is provided — then it drops onto its true location.
  • Building TEXTURES (brushed metal, concrete/brick texture) are not in the IFC;
    for the fully-rendered Revit look, export glTF from Revit with materials on.
  • The whole-city 3D view is heavy (80,000+ pipes) — best on desktop.

  Kreayotoo Solutions (P) Ltd · Hyderabad · Vijayawada · Guntur
  Engineering · Solutions · Innovation
