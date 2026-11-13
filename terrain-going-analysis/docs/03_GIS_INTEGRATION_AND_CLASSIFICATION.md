# 03 - GIS Integration, GOING Classification and Mobility Assessment (Requirements 3, 4 and 5)

**UNCLASSIFIED // EXERCISE ONLY - criteria are illustrative, not doctrine**

## 1. Unified geospatial database

All vector data live in one OGC GeoPackage, `outputs/vector/terrain_db.gpkg`. Its 23 layers are listed in
blueprint §4.1. All rasters are on a single 1 m grid in EPSG:32630 (1000 × 1000 cells). Keeping one grid
and one database avoids misalignment errors and makes the product portable as two folders: `rasters/`
and `vector/`. Every file has a metadata record in `outputs/metadata/` (docs/05).

Recommended QGIS layer groups (implemented in `AOI_KESTREL_GOING.qgz`):
`01 Survey planning`, `02 UAS products`, `03 Terrain derivatives`, `04 Terrain database`,
`05 GOING analysis`, `06 Mobility assessment`, `07 Validation`.

## 2. Factor layers

| Factor | Layer | Derivation | QGIS equivalent |
|---|---|---|---|
| Slope | `slope_deg.tif` | DTM smoothed (Gaussian σ = 2 m, a vehicle-scale baseline), then the gradient | GRASS `r.neighbors` (5 × 5 mean) then `native:slope` |
| Drainage | `drainage_derived` layer, `flow_accumulation_m2.tif` | Priority-flood depression filling with ε, D8 flow accumulation at 2 m, threshold 15,000 m² | GRASS `r.watershed` |
| Wetness | `twi.tif` | TWI = ln(a / tan β), with a in m²/m and β ≥ 0.5° | `r.watershed` output `tci` |
| Vegetation structure | `vegetation_class.tif`, `canopy_cover.tif` | CHM = DSM − DTM. Cover = share of cells ≥ 3 m in a 15 m window. Scrub = ≥ 0.6 m in more than 40 % of a 5 m window. | Raster Calculator, `r.neighbors` |
| Vegetation vigour | `vari.tif` | VARI from RGB | Raster Calculator |
| Surface features | roads, fields, built-up, water, marsh, quarry | Digitised from the orthomosaic | Digitising toolbar; QuickOSM for comparison |
| Obstacles | `linear_obstacles`, `buildings`, `vertical_obstructions`, steep slope | Digitised (with a visibility test), DSM heights, slope ≥ NO-GO limit | Digitising, zonal statistics on the CHM |
| Data confidence | `data_confidence.tif` | Local share of ground actually observed | From point-cloud classification density |

## 3. Classification model

### 3.1 Classes

| Code | Class | Meaning | Doctrinal analogue |
|---|---|---|---|
| 1 | GO | Movement at or near the planned speed | Unrestricted |
| 2 | SLOW-GO | Movement possible but speed or formation reduced | Restricted |
| 3 | NO-GO | Not passable without engineer effort | Severely restricted |
| 4 | REQUIRES RECONNAISSANCE | Data insufficient to decide; must be checked on the ground | (information state) |

### 3.2 Illustrative criteria (`config/going_criteria.json`)

| Factor | Wheeled 4x4 | Tracked | Class |
|---|---|---|---|
| Slope | ≥ 15° | ≥ 20° | SLOW-GO |
| Slope | ≥ 30° | ≥ 35° | NO-GO |
| Canopy cover (trees ≥ 3 m) | ≥ 0.20 | ≥ 0.20 | SLOW-GO (light woodland) |
| Canopy cover | ≥ 0.65 | ≥ 0.80 | NO-GO (dense woodland) |
| Scrub (≥ 0.6 m / ≥ 1.5 m) | yes | yes | SLOW-GO |
| Linear obstacle height or depth | 0.3-0.6 m / ≥ 0.6 m | 0.3-0.9 m / ≥ 0.9 m | SLOW-GO / NO-GO |
| Built-up area (not buildings) | yes | yes | SLOW-GO |
| Buildings, water, pylon footings | - | - | NO-GO |

| Seasonal factor | Dry | Wet |
|---|---|---|
| TWI, flat ground (< 5°), SLOW-GO | ≥ 9.5 | ≥ 7.8 |
| TWI, very flat ground (< 3°), RECCE | ≥ 11.0 | ≥ 9.0 |
| Cultivated fields | GO | SLOW-GO |
| Marsh | RECCE | NO-GO |

| Data-confidence rule | Class |
|---|---|
| Ground confidence < 0.45 | RECCE |
| Within 15 m of a stream and confidence < 0.7 (banks hidden) | RECCE |
| Bridge or ford with unknown MLC or depth | RECCE |

### 3.3 Precedence and generalisation

1. Start with GO everywhere.
2. Apply the SLOW-GO rules, then the RECCE rules, then the NO-GO rules, so that the most restrictive
   condition wins (NO-GO > RECCE > SLOW-GO > GO).
3. Generalise with a **100 m² minimum mapping unit** (GDAL sieve, 8-connected).
4. Burn in the narrow features *after* generalisation so they survive: linear obstacles, then pylons,
   then tracks and roads (GO, except over water), then crossings (RECCE).
5. Record the deciding rule for every cell in `going_reason.tif` (codes in `reports/reason_codes.csv`).
   Any cell on the map can then be explained, for example with the QGIS Identify tool.

### 3.4 Implementations

* **Reference:** `src/going/classify.py::classify_going` (Python and NumPy).
* **QGIS:** Processing script `script:goingclassify` (`qgis/scripts/going_classify.py`, GDAL and NumPy
  only), wrapped in the model `going_terrain_analysis.model3`:

  `r.neighbors` (smooth) → `native:slope` → `r.watershed` (TWI) → `script:goingclassify` →
  `gdal:polygonize` → `native:fieldcalculator` (label) → `native:fieldcalculator` (area) →
  `native:rasterlayeruniquevaluesreport`

* **Cross-check:** `qgis/run_models.py` compares both implementations cell by cell. The reference run
  gives 97.0 % agreement. The differences come from the smoothing kernel and the TWI algorithm.

### 3.5 Manual QGIS method (no scripts)

For syndicates that want to build the model by hand in the Graphical Modeler:
1. `r.neighbors` (average, 5) on the DTM, then **Slope**.
2. **Reclassify by table** of slope: 0-15 → 1, 15-30 → 2, 30-90 → 3.
3. **Raster Calculator** on the CHM for cover/scrub masks (`"chm@1" >= 3`, then `r.neighbors` average 15).
4. **Rasterize** each vector layer (water, buildings, roads, obstacles with buffer) to the DTM grid.
5. **Raster Calculator** combining the masks with `max()` for restrictive classes and overrides for roads.
6. **Sieve** (threshold 100), **Polygonize**, **Field calculator** for labels.

## 4. Mobility assessment and route comparison

### 4.1 Speed and cost
Illustrative cross-country speeds (wheeled): road 40, track 25, GO 18, SLOW-GO 7, RECCE 5 km/h.
Speeds are reduced by slope (factor 1 − slope / (1.4 × NO-GO limit), with a floor of 0.3). NO-GO is
impassable. Cost = time per metre = 3.6 / speed (s/m).

### 4.2 Route definitions

| Route | Cost surface | Question it answers |
|---|---|---|
| A-DIRECT | 1 per metre, NO-GO impassable | What is the shortest physically possible route? |
| B-FASTEST | Time, with RECCE cells × 1.5 | What is the quickest, accepting unverified ground? |
| C-ASSURED | Time, RECCE impassable, SLOW-GO × 1.5 | What is the quickest route using only verified ground? |
| D-CONCEALED | Fastest × (1 + 6 × visible from OP) | What is the quickest route that stays out of observation? |

The routes are computed with 8-connected least-cost paths (`skimage.graph.MCP_Geometric`). In QGIS,
`going_route_analysis.model3` uses GRASS `r.cost` with Knight's move and `r.drain`.

### 4.3 Metrics and scoring
For each route: length, estimated time, average speed, share of GO/SLOW-GO/RECCE, share on roads,
maximum slope, number of RECCE sections, water crossings and share of the route exposed to OP SIERRA.
The weighted score (0 = best) normalises time (35 %), risk (25 %), exposure (25 %) and crossings (15 %)
across the candidate routes. The weights represent the commander's priorities. The ranking supports a
decision but does not replace one. Results are in `reports/ROUTE_ASSESSMENT.md`.

### 4.4 Line of sight
The line of sight is a ray-cast over the DSM at 4 m from OP SIERRA (observer 3 m, target 2.5 m,
range 1.5 km), with a 5 × 5 majority (median) smoothing. The same function supports C-UAS or ISR sensor
siting, and it identifies UAS launch sites masked by terrain.

## 5. Sensitivity

`reports/sensitivity_analysis.csv` shows the class areas when the slope limits shift by ±5° or the TWI
thresholds by ±1. In the reference run, lowering the slope limits by 5° moves about 6.5 % of the AOI
from GO to SLOW-GO. Criteria must therefore be tied to the vehicle and recorded in the metadata.
