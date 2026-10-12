# 190 MLD WTP — Georeferencing & Provenance Record

**Source drawing:** `WTP Site Plan R0 01-09-26_O1 (M)-F1 - 3D View - {3D}.dxf`
**Supplied coordinates:** `190_MLD_WTP_Coordinates.txt` (3 site corners)
**Grid:** UTM Zone 44N — EPSG:32644
**Integrated:** 01-09-2026

---

## 1. Georeferencing solution

The DXF is drawn in **millimetres** with its origin at the centre of the site
bounding box. Solving the DXF header extents against the three supplied survey
corners gives:

```
UTM_E = DXF_X / 1000 + 452067.3818
UTM_N = DXF_Y / 1000 + 1824054.9438
```

**Residuals on the independent check corner:**

| Axis | DXF span | Survey span | Residual |
|------|----------|-------------|----------|
| Easting  | 422.0137 m | 422.0135 m | **0.0002 m** |
| Northing | 666.5541 m | 666.5490 m | **0.0051 m** |

No rotation and no scale factor are required — the drawing is already
axis-aligned to the UTM grid. Sub-centimetre agreement.

**Site corners (EPSG:32644 → WGS84):**

| Corner | Easting | Northing | Latitude | Longitude |
|--------|---------|----------|----------|-----------|
| SW | 451856.21 | 1823721.44 | 16.494791 | 80.548900 |
| SE | 452278.23 | 1823721.44 | 16.494799 | 80.552854 |
| NE | 452278.23 | 1824388.00 | 16.500825 | 80.552840 |
| NW | 451856.21 | 1824388.00 | 16.500816 | 80.548886 |
| **Centre** | 452067.22 | 1824054.72 | **16.497808** | **80.550870** |

Site is a triangular plot, 422.01 × 666.55 m envelope.

---

## 2. What the DXF contains

Revit/AutoCAD 3D export, **27,884 polyface meshes / 246,426 vertices** on five
layers:

| Layer | Count | Content |
|-------|-------|---------|
| A-GENM | 27,740 | Generic model — mostly **vectorised text labels**, kerbs, small detail |
| C-TOPO | 490 | Topography, paving, hardstanding |
| A-FLOR | 316 | Floor slabs, roads, plot outlines |
| A-WALL | 42 | Boundary wall (admin compound) |
| L-SITE | 17 | Site boundary |

**Vertical extent is only −10.00 m to +2.39 m.** Apart from a datum pad at
−10 m, 99% of geometry sits between −0.09 m and +1.15 m. This is a **2D site
layout drawn in 3D space** — roads, kerbs, plinths and plot outlines. The
drawing does **not** contain modelled tank walls, basins or building volumes.

---

## 3. How it is represented in the twin

### REAL (taken directly from the DXF / survey / hydraulic model)
- Site boundary triangle — from the three supplied survey coordinates
- **Full CAD linework**, rendered to a georeferenced texture at 3072 × 4852 px
  (0.137 m/pixel) and draped at true scale and true position. Every line and
  every text label in the drawing is preserved.
- **Plan footprint and position of all 17 unit-process blocks**, digitised from
  the drawing and snapped to its own dominant grid lines.
- **9 trunk tie-in nodes** from the RINGMAIN WaterGEMS model that fall inside
  the site boundary.

### SIMULATED (not present in the source data — engineering-typical values)
- **All structure heights and depths.** The drawing has no vertical structure
  above 2.39 m, so extrusion heights are typical values for a conventional
  190 MLD surface-water treatment works. Every parameter panel states this.
- Process parameters (capacities, residuals, duty/standby splits) except where
  marked REAL.

---

## 4. Trunk-main tie-in — independently verified

Nine nodes of the existing WaterGEMS trunk model fall **inside** the WTP site
boundary. They were not moved or created for this integration:

| Node | Easting | Northing | Local X, Y | Description |
|------|---------|----------|-----------|-------------|
| R-1  | 452264.5 | 1824145.7 | 197.1, 90.7 | Source reservoir / headworks |
| R-3  | 452267.6 | 1824144.7 | 200.2, 89.8 | Source reservoir / headworks |
| PMP-1 | 452264.1 | 1824174.1 | 196.7, 119.2 | Pumping station |
| PMP-2 | 452267.6 | 1824188.1 | 200.2, 133.2 | Pumping station |
| J-86 | 452261.7 | 1824213.0 | 194.3, 158.1 | Tapping point |
| J-87 | 452261.7 | 1824202.8 | 194.3, 147.9 | Tapping point |
| J-92 | 452265.9 | 1824230.3 | 198.5, 175.4 | Tapping point |
| J-93 | 452265.6 | 1824292.1 | 198.2, 237.1 | Tapping point |
| AV-83 | 452064.5 | 1824319.6 | −2.9, 264.7 | Line valve (AV) |

R-1, R-3, PMP-1 and PMP-2 land on the **Clear Water Reservoir → Clear Water
Pump House** interface at the eastern edge of the drawing — exactly where a
reservoir outlet and pump suction belong. **The CAD drawing and the hydraulic
model, produced independently, agree on the plant location.**

Outlet main: **pipe #103, 2400 mm dia, invert 25.00 m** (REAL, WaterGEMS).
Pad level adopted: **23.40 m** (matches node rims 23.2–24.2 m; corridor FRL 23.37 m).

---

## 5. Unit-process schedule

Footprints REAL (DXF). Heights and depths SIMULATED.

| # | Unit | Plan (m) | Height | Depth |
|---|------|----------|--------|-------|
| 1 | Clear Water Reservoir | 167.4 × 89.2 | 5.5 | 4.0 |
| 2 | Future CWR (reserved) | 167.4 × 51.0 | — | — |
| 3 | Clear Water Pump House | 8.0 × 144.2 | 9.5 | — |
| 4 | Filter Backwash Pump House | 39.8 × 33.8 | 8.5 | — |
| 5 | Filter — Twin Beds | 39.8 × 98.0 | 6.0 | 3.0 |
| 6 | Backwash WW Recycling PH | 20.0 × 32.6 | 6.5 | — |
| 7 | Filter Annexe Building | 19.8 × 32.6 | 7.0 | — |
| 8 | Inclined Plate Settlers | 39.1 × 82.9 | 6.5 | 4.0 |
| 9 | Flocculator Tanks | 33.7 × 82.9 | 6.0 | 4.0 |
| 10 | Clarifier / Sludge | 29.1 × 41.8 | 4.5 | 3.0 |
| 11 | Chlorination Room | 30.9 × 17.9 | 5.5 | — |
| 12 | Chlorine Tonner Room | 24.9 × 19.3 | 5.5 | — |
| 13 | Chemical House & Central Lab | 17.7 × 49.9 | 9.0 | — |
| 14 | Cascade Aerator | 36.9 × 34.2 | 7.5 | — |
| 15 | Admin Building | 46.0 × 40.0 | 24.0 | — |
| 16 | Substation Building A | 17.0 × 42.0 | 6.0 | — |
| 17 | Substation Building B | 19.0 × 43.0 | 6.0 | — |

The "FUTURE WTP" plot in the north-west of the site contains roads only and is
left as reserved land.

---

## 6. Files

| File | Purpose |
|------|---------|
| `WTPSITE.json` | Georeferenced site package consumed by the twin (boundary, 17 units, 9 ties, embedded plan texture) |
| `wtp_plan.png` | CAD site plan raster, 3072 × 4852, transparent, for the ground drape |
| `190_MLD_WTP_Coordinates.txt` | Supplied survey corners (as received) |


---

## 7. Admin building BIM placement

The Revit/IFC admin building model is placed at the **ADMIN. BLD.** footprint of
the site plan, not at the coordinates embedded in the IFC.

**Three coordinates were found in the delivered files. None of them is inside
the WTP site:**

| Source | Easting | Northing | Distance from site-plan footprint |
|---|---|---|---|
| `IFCMAPCONVERSION` (georeferenced IFC) | 445865.02 | 1822709.30 | 6,463 m |
| `IFCSITE` RefLatitude / RefLongitude | 446307.65 | 1824518.03 | 5,853 m |
| `bldg_loc.json` / `BLDG_LL_DEFAULT` (in app) | 445576.67 | 1811499.51 | 14,308 m |
| **Site-plan DXF footprint (adopted)** | **452139.91** | **1824212.16** | **0 m** |

**Adopted placement**

| Property | Value | Source |
|---|---|---|
| Insertion point | E 452139.91, N 1824212.16 | DXF site plan |
| WGS84 | 16.499185 N, 80.551665 E | derived |
| Plan rotation | −27.17° from grid east | DXF minimum-area oriented bounding box |
| Scene rotation (`B.rot`) | 62.83° | 90° − 27.17° |
| Base level | 23.40 m | WTP pad |
| Scale | 1.0 — **no stretch applied** | — |

**Footprint reconciliation.** The drawing's building outline is 30.00 × 20.00 m.
The BIM model's lowest slab (node `FL03_6`, the FRL level) is 37.04 × 27.04 m —
exactly **3.5 m larger on every side**, i.e. the building plus its surrounding
apron. The building core measured from the model (5th–95th percentile of mesh
extents) is 22.3 × 32.3 m, consistent with a 20 × 30 m envelope plus roughly
1 m of eaves. The two datasets agree; the model is placed at true scale.

**Independent check on rotation.** The site plan's `MAIN_GATE_01` block is
inserted at 62.830442°. The rotation derived independently from the admin
building's oriented bounding box is 62.83°. The site's building grid and the
adopted BIM rotation agree to two decimal places.

Model: 118 meshes, 16 levels (`floors.json`, pile cut-off −2.70 m to terrace),
overall height 33.38 m, Draco-compressed glTF from IFC4 / Revit 2026.


---

## 8. Trunk main revision R4 bypass (09-09-2026)

The RINGMAIN trunk model was replaced by **2058_R4_bypass.dxf** (WaterGEMS export, EPSG:32644).
1,106 pipes / 2,291 segments / 121.2 km; 323 named nodes; every pipe carries its model ID,
diameter, length and flow arrow; 867 junctions carry invert level and pressure. The bypass is a
new main from the WTP headworks (R-1 / PMP-1) north-east to the raw-water **INTAKE** node
(E 453075.62, N 1826060.23), replacing the previous eastward alignment. R-3 and PMP-2 no
longer exist in the model.

Trunk nodes now inside the WTP site (12):

| Node | Easting | Northing | Local X, Y | Description |
|---|---|---|---|---|
| R-1 | 452261.0 | 1824108.1 | 193.6, 53.2 | Source reservoir / headworks |
| PMP-1 | 452260.9 | 1824123.3 | 193.5, 68.4 | Pumping station |
| J-86 | 452261.2 | 1824212.5 | 193.8, 157.6 | Tapping point · demand 0.0 MLD |
| J-87 | 452261.2 | 1824202.3 | 193.8, 147.4 | Tapping point · demand 0.0 MLD |
| J-92 | 452265.4 | 1824229.8 | 198.0, 174.9 | Tapping point · demand 0.0 MLD |
| J-93 | 452265.2 | 1824291.8 | 197.8, 236.9 | Tapping point · demand 0.0 MLD |
| J-184 | 452265.4 | 1824219.6 | 198.0, 164.7 | Tapping point · demand pending |
| J-186 | 452265.2 | 1824290.7 | 197.8, 235.8 | Tapping point · demand pending |
| J-190 | 452261.3 | 1824140.0 | 193.9, 85.1 | Tapping point · demand pending |
| J-192 | 452265.2 | 1824139.9 | 197.8, 85.0 | Tapping point · demand pending |
| J-196 | 452265.6 | 1824025.5 | 198.2, -29.4 | Tapping point · demand pending |
| AV-83 | 452058.5 | 1824317.1 | -8.9, 262.2 | Line valve (AV) |

R-1 now falls inside the Clear Water Reservoir footprint (previously 25 m east of it); PMP-1 at
the Clear Water Pump House. The 76 tapping-point demands (982.5 MLD) were carried over by node
ID from the previous revision; ten new J-nodes have no demand yet. EPANET re-run: flow direction
agrees with the WaterGEMS arrows on 2,188 of 2,204 flowing segments (99.3%).


---

## 9. WTP site model and intake headworks from IFC (22-09-2026)

Two Revit 2026 IFC2x3 exports replace the simulated extrusions: the treatment plant is now
real 3D geometry with real heights, and the raw-water intake is modelled for the first time.

| Model | File | Elements | Web mesh |
|---|---|---|---|
| WTP site (19 linked buildings) | `KSPL-NCC-ADCL-WTP_01 Site Layout R0 22-09-26_O1 (M)-F2B.ifc` (381 MB) | 13,138 kept of 100,811 (97,920 filter-floor air nozzles, rungs, trims, furniture, RPC figures omitted) | **Full detail 1,217,742 triangles** (piles below ground omitted; the 2,661 admin-building elements cut out of the site mesh and carried by the detailed admin model), Draco 16-bit, 1.41 MB. City view: 336 k-triangle version, 0.49 MB |
| Intake wells 1 & 2 + headworks | `KSPL-NCC-ADCL-WTP_Intake HW_ASM_R0 15-09-26_F1.ifc` (43 MB) | 1,810 | **Full detail 605,688 triangles**, Draco 16-bit, 0.79 MB. City view: 288 k-triangle version, 0.37 MB |

Neither file carries usable georeferencing (Revit's default London / Boston `IfcSite` placeholders,
no `IfcMapConversion` in IFC2x3). Both were placed from the surveyed coordinates supplied on
22-09-2026.

**WTP site.** The IFC's plan extent is X −211.17 … 210.843, Y −333.499 … 333.055 m — identical to the
site-plan DXF to the millimetre, i.e. the same Revit shared-coordinate origin. The transform solved
in Section 1 therefore applies unchanged: **E = X + 452067.3818, N = Y + 1824054.9438**, rotation 0.
Vertical datum: the storey named `00 +21.00 FGL` sits at model z = 0, and every RL-named storey is
offset by exactly −21.00 m, so **RL = z + 21.00**. The plant's design finished ground level is
+21.00 m; the trunk model's node rims at the plant (23.2–24.2 m) differ from this by about 2.4 m and
the IFC value has been adopted for the pad. The site model contains the administration building
(2,661 elements on the ADMIN. BLD. plot, top +30.4 m), which independently confirms the placement derived
from the DXF in Section 7. Those elements are removed from the site mesh (plan polygon = BIM apron
+ 0.5 m) so that the detailed 827,010-triangle admin model, kept at its original quality, occupies the plot
without duplication.

**Intake.** The model's two intake wells (`Well Curb Plugging 2750mm`, 16.7 m diameter) are 29.00 m
apart; the surveyed INTAKE WELL-1 and WELL-2 are 29.00 m apart. A rigid fit on the two wells gives
rotation **52.420°** and translation (**E 452884.529, N 1825979.830**) with residual 0.000 m on both wells. As an
independent check, the model's MS 2000 mm raw-water pipe runs along model −X; after the fit its
bearing agrees with the surveyed MS 2000 DIA PIPE to **0.06°**. Model levels are reduced levels
(site level 0, well bottom plug +3.0 m, deck +27.7 m) and are used as such. The surveyed head-works
outline (17 points) encloses the model; points 1–4 form the site rectangle drawn on the map.

The R4 trunk model's INTAKE node lies 20 m from WELL-1 and its bypass alignment runs 10–15 m from
the surveyed MS 2000 pipe — the hydraulic model is schematic here; the survey and the IFC are the
geometry of record.

Files: `datasets/wtp/ifc/` (web meshes, fit parameters, descriptors, survey coordinates);
`build_pipeline/ifc/` (stream filter, tessellation, decimation scripts). The source IFC files are
not included in the package because of size; they are held with the design consultant's issue.


**Detail policy (23-09-2026).** All three models are delivered at their full tessellated detail in the
Trunk and Plant views, with Draco 16-bit positions (≤ 1 cm quantisation over the largest extent). The
Entire City view — 130,000 pipes already in the scene — loads lighter versions of the plant (336 k) and
intake (288 k) meshes automatically; the admin model is the same in every view.

**Materials (23-09-2026).** Each mesh is built per Revit material, using the `IfcSurfaceStyleRendering`
surface colour written in the IFC — 81 materials at the plant, 60 at the intake (concrete greys, brick,
grass, sand, earth, asphalt, the designer's pink for future-phase areas). Metalness, roughness and
glass transparency are assigned by material class. Elements the IFC leaves unstyled (about 18 %:
railings and a set of concrete elements) are drawn as painted steel and concrete grey and named as
such in the model. A first pass had lost 97 % of the styling because the stream filter tested only
the lowest-numbered reference of each `IfcStyledItem`; corrected, the filter retains 18,328 styled items.

**Colours (07-10-2026).** The IFC files carry the designers' Revit material colours as `IfcSurfaceStyle`
definitions — 58 styles in the plant model, 55 in the intake (Grass, Brick Common, Earth, Granite, Render
Beige, Sand, Gravel, Glass, Aluminium, Paint Blue and several concretes). Every triangle whose colour matches
one of these styles keeps it exactly (8-bit RGB), with the style's transparency (glass at 30 % opacity). The
modeller's `_Future` variants (pink / light magenta) mark future-phase areas and are kept as issued. Elements
exported without a surface style — railings, pipe segments, fittings and valves in the plant, some railings in
the intake — fall back to an engineering palette (blue pipe, red-brown valves, grey railings). Two
non-physical helper volumes in the intake model (`Clearance Zone`, `Cutting geometry`, 636 triangles) are
removed. The 10 m-thick `Floor_Earth` solid under the plant is omitted so the trunk pipes crossing the site
stay visible; the toposolid and pavement surfaces form the ground.


## 10. Flow direction (07-10-2026)

Every pipe in every view now animates in its physical flow direction. Directions are stored per segment
(`fdir`, '+' along the drawn segment, '-' against it) and carried through the zone, city and plant views.

| Network | Direction from | Status | Segments reversed vs drawing |
|---|---|---|---|
| Raw-water main | intake wells -> WTP inlet J-196 (20 segments, ends at the plant; not connected to treated water) | REAL | 0 |
| Trunk main | WaterGEMS flow arrows (all 85 WDC / tapping points reachable from R-1 following the arrows); EPANET supplies speed only | REAL | 16 that EPANET (uncalibrated) ran backwards now follow the arrows; 70 zero-flow segments now move slowly instead of standing still |
| Block distribution (40 blocks) | shortest-path tree from the block's feed point = block vertex nearest its nearest WDC tapping node; 93 connected components each fed separately | feed location ASSUMED | 5,053 of 25,480 |
| Sewerage | gravity: higher to lower design invert | REAL | 864 of 12,193 (0 uphill after the fix) |
| Storm water | gravity: higher to lower design invert | REAL | 55 of 50,211 |
| Reuse, power | unchanged | — | — |

Inside the plant a schematic arrow path shows the treatment sequence: inlet -> cascade aerator ->
flocculators -> inclined-plate settlers -> filters -> chlorination -> clear water reservoir (R-1) ->
pump house (PMP-1). Block feed points are marked FEED <- WDC-xx in block and zone views. Live EPANET
runs (server) still show EPANET's own directions, labelled LIVE · UNCALIBRATED. `build_pipeline/build_fdir.py`
regenerates the directions.


## 11. WaterGEMS result tables joined to the trunk model (12-10-2026)

Four demand scenarios of the RINGMAIN R4 bypass model were supplied as WaterGEMS pipe and junction
result tables (CSV). They replace the uncalibrated EPANET baseline as the trunk main's hydraulics.

| Scenario | Demand served (MLD) | P min (m) | P mean (m) | P max (m) | Segments against the 2058 direction |
|---|---|---|---|---|---|
| 2028 demand | 325.1 | 32.1 | 50.0 | 61.8 | 260 |
| 2043 demand | 1091.5 | 29.7 | 48.5 | 59.4 | 74 |
| 2043 · without Undavalli & Tadepalli | 883.9 | 23.2 | 43.5 | 61.3 | 260 |
| 2058 ultimate demand | 2336.0 | 20.3 | 45.5 | 61.7 | 2 |

**Join.** Pipes: the CSV `ID` is the DXF pipe label `ID:nnnn` — 1,105 of 1,106 drawn pipes matched
(the drawn pipe 4631 is absent from the tables; CSV pipes 4555 and 4561 are short 1,100 mm stubs with no
result and no drawn geometry). Junctions: the CSV `Label` is the DXF node text — all 856 junctions located,
771 of them (the `JN-*` model junctions) added to the twin as junction nodes. Per pipe: flow, velocity,
headloss gradient, headloss, material and Hazen-Williams C. Per junction: elevation, demand, hydraulic grade,
pressure. Pressures at pipe ends are taken from the end junctions; where a pipe ends at a valve node (436
pipes) the pressure is propagated across the valve from the adjacent pipe.

**Direction.** The drawn segments were oriented to the DXF flow arrows at build time (84 polylines flipped).
In the 2058 table 82 of the 84 flipped pipes carry negative flow and 1,021 of 1,022 unflipped pipes carry
positive flow, which confirms that the arrows are the 2058 result and fixes the sign convention. A scenario
flow whose sign differs from 2058 runs against the drawn direction: 260 segments in 2028, 74 in 2043.
The raw-water main (intake to WTP) is not in the model and keeps its intake record.

In the twin a **WaterGEMS** selector in the twin footer switches scenario; pipe tooltips, map popups and the
junction panel show the selected scenario's values, tagged REAL. The Live EPANET button still runs the
server model, tagged uncalibrated. Source tables: `datasets/source_workbooks/watergems_results/`;
`build_pipeline/build_hydro.py` regenerates the join.

**Entire City flow and a direction bug (12-10-2026).** The city view drew solid pipes with no flow for
performance; it now draws every utility as a flowing core at the same instance count (one mesh per utility,
136,000 instances, 5 draw calls, 3.0 M triangles — verified headless, no context loss). A second defect was
found in the process: the routine that clips pipes around power-chamber footprints splits segments at run
time, which shifted every index-based array (direction string, hydraulics, map geometry) after the first split
in any view containing power chambers. The split now carries those arrays with it. Headless checks after the
fix: direction mismatches 0 of 30,367 water, 12,193 sewer and 51,625 storm segments in the city view.
