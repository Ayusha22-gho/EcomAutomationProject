# 01 - UAS Survey Planning (Requirement 1)

**UNCLASSIFIED // EXERCISE ONLY**

> **Status:** survey design calculations and mission files are **real and reusable**. The mission was
> **not flown**. Imagery and products are simulated (see docs/02).

## 1. Task

Produce photogrammetric imagery of AOI KESTREL (1,000 m × 1,000 m, about 1 km²) to support a 1 m terrain
analysis product. The DTM must reach RMSEz ≤ 0.10 m in the open and the orthomosaic RMSEr ≤ 0.10 m.
Product GSD must be ≤ 5 cm.

## 2. Platform and sensor (illustrative selection)

| Item | Value | Rationale |
|---|---|---|
| Platform | Small multirotor (for example DJI Mavic 3 Enterprise class) | Commonly available; vertical take-off from a small site; RTK capable |
| Camera | 4/3" CMOS, 17.3 × 13.0 mm, 12.29 mm focal length, 5280 × 3956 px, **mechanical shutter** | No rolling-shutter distortion |
| Positioning | Network or base-station RTK, plus GCPs | Absolute accuracy and redundancy |
| Alternative | Small fixed-wing VTOL with a 20-42 MP camera | Better for > 3 km² |

## 3. Design calculations (`src/going/survey.py`, output in `outputs/mission/survey_design.json`)

| Parameter | Formula | Value |
|---|---|---|
| Height above ground (AGL) | chosen | 100 m (terrain-following) |
| Ground sample distance | GSD = sensor_w × H / (f × img_w) = 17.3 × 100 / (12.29 × 5280) | **2.67 cm/px** |
| Footprint across track | GSD × 5280 | 140.8 m |
| Footprint along track | GSD × 3956 | 105.5 m |
| Forward overlap | chosen for mixed vegetation | 80 % |
| Side overlap | chosen | 70 % |
| Trigger distance | footprint_along × (1 − 0.80) | **21.1 m** |
| Line spacing | footprint_across × (1 − 0.70) | **42.2 m** |
| Block (AOI + 60 m buffer each side) | 1,120 m × 1,120 m | |
| Number of lines | ⌈1120 / 42.2⌉ + 1 | **28** |
| Images | 28 × 55 | **~1,540** |
| Ground speed | chosen | 10 m/s |
| Trigger interval | 21.1 / 10 | 2.1 s (camera minimum 0.7 s: OK) |
| Motion blur | v × t_shutter / GSD = 10 × 1/1000 / 0.0267 | **0.38 px** (< 0.5 px: OK) |
| Flight time | lines × (line length / v + 15 s turn) | 59 min |
| Sorties | usable endurance 25 min, minus 5 min reserve | **3** (A, B, C: about 10 lines each) |

**Overlap guidance.** Use 75/65 % for open and built-up ground, 80/70 % for mixed ground (this plan), and
85/75 % for dense forest or low-texture fields, where matching is harder. Raise the height or lower the
overlap only if the GSD and accuracy requirements still hold.

**Terrain following.** AOI relief is about 80 m. At a constant altitude above the launch point, the GSD
would vary by about ±40 %. Waypoint altitudes are therefore set to reference-DEM + 100 m (a smoothed
public DEM such as Copernicus GLO-30). The `.plan` files carry absolute (AMSL) altitudes.

## 4. Ground control

| Type | Number | Layout | Survey |
|---|---|---|---|
| GCPs (control) | 9 | Corners, edge mid-points, centre, in open ground | GNSS RTK, 3 min occupation, 1 m chequerboard targets |
| ICPs (independent check points) | 25 (15 open, 10 vegetated) | Random, stratified | GNSS RTK; **never** used in the adjustment |

## 5. Hazards and constraints shown on the plan (map 01)

* 33 kV overhead power line with 28 m pylons crossing the northern third. The flight height of 100 m
  gives more than 70 m clearance. The launch site must be at least 50 m from the line.
* Escarpment and ridge: the terrain-following profile prevents a loss of clearance on the NE ridge.
* Village: do not overfly gatherings of people; observe local rules on privacy and noise.
* Launch/recovery: SW corner, open, firm, out of the line of sight of the notional OP (map 11).

## 6. UAS and C-UAS considerations

| Area | Consideration | Action in the SOP |
|---|---|---|
| Friendly C-UAS | Friendly counter-UAS systems may detect and engage the survey UAS | Register the flight with the airspace control authority and C-UAS cell; issue the ROZ/time window, IFF/Remote ID details and lost-link behaviour |
| Adversary C-UAS / EW | GNSS jamming or spoofing, and RF link jamming | Pre-brief the jamming indicators; plan RTK-loss fall-back (abort or continue on GNSS with GCP correction); set RTH height above the pylons |
| Signature | The UAS and the crew reveal interest in an area | Fly at an unremarkable time; vary launch sites; minimise time on station; use EMCON for the ground station |
| Terrain products for C-UAS | The DSM and line of sight support C-UAS sensor siting and identify UAS launch sites masked by terrain | Line-of-sight map 11; `viewshed_op_sierra` layer |

## 7. Mission files

* `outputs/mission/AOI_KESTREL_sortie_A.plan`, `_B.plan` and `_C.plan` are QGroundControl plan files.
  Each contains a take-off item, terrain-following waypoints, `DO_SET_CAM_TRIGG_DIST` on and off for
  each line, RTL, an inclusion geofence of AOI + 150 m, and a rally point.
* The `flight_lines`, `photo_centres` and `gcps` layers in `terrain_db.gpkg` can be displayed in QGIS or
  exported to KML for other planners.

To open a mission, start QGroundControl and select **Plan ▸ File ▸ Open ▸ AOI_KESTREL_sortie_A.plan**.
Check the altitudes, geofence and camera trigger distance before upload.
