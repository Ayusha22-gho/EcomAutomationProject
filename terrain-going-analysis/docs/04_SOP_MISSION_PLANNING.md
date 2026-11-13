# 04 - STANDARD OPERATING PROCEDURE
## UAS Rapid Terrain Mapping Mission: Planning, Execution, Processing and Dissemination

**UNCLASSIFIED // EXERCISE ONLY**

| | |
|---|---|
| SOP number | GEO-SOP-01 (course) |
| Applies to | Geospatial cell, UAS crew, terrain analysts |
| References | docs/01 (survey design), docs/02 (processing), docs/03 (analysis), docs/05 (metadata), docs/07 (update), docs/08 (QA checklist); national UAS regulations and airspace orders |
| Note | Adapt to national regulations, unit orders and the authorised platform. This SOP does not authorise flight. |

## 1. Purpose
To produce a terrain package (orthomosaic, DEM, GOING map, route assessment) for an AOI of up to
about 1 km² quickly, safely and repeatably, to a known quality.

## 2. Roles

| Role | Responsibilities |
|---|---|
| Mission commander (MC) | Accepts the task, approves the plan, accepts the risk, releases the product |
| Remote pilot (RP) | Flight planning, pre-flight, flight, aircraft logs |
| Payload/data operator (DO) | Camera settings, image QA, data custody |
| Survey NCO | GCP and ICP placement and GNSS survey |
| Terrain analyst (TA) | Processing, GIS analysis, validation, map production |
| Airspace/C-UAS liaison | Airspace coordination, friendly C-UAS deconfliction |

## 3. Procedure

### Phase A: Receive the task (MC, TA)
A1. Record the task: AOI (polygon file), purpose (for example mobility for a wheeled 4x4 company group),
    vehicle profile, season, deadline (latest time information is of value), marking and dissemination.
A2. Check existing holdings (GIM catalogue): a current product may already exist (docs/07).
A3. Confirm the product specification: GSD ≤ 5 cm, DTM RMSEz ≤ 0.10 m (open), 1 m analysis grid.

### Phase B: Authorisation and airspace (MC, airspace liaison)
B1. Obtain flight authorisation (operating category, range/landowner permission, privacy assessment).
B2. Request the airspace reservation (ROZ/temporary segregated area), with altitude block and time window.
B3. **Friendly C-UAS deconfliction:** notify the C-UAS cell of the platform type, Remote ID/IFF,
    launch site, routes, times and lost-link behaviour. Obtain a deconfliction code word or "weapons hold".
B4. Threat assessment: adversary C-UAS, EW/GNSS jamming, observation, indirect fire. Decide EMCON and
    launch-site selection (use the line-of-sight analysis where available).
B5. Weather check: wind < 10 m/s (platform-dependent), no precipitation, cloud base above flight height,
    sun elevation > 25°, Kp index for GNSS.

### Phase C: Mission planning (RP, TA)
C1. Run the survey design (docs/01): GSD, overlaps, line spacing, trigger distance, blur, endurance, sorties.
C2. Generate the terrain-following flight lines and geofence. Export the `.plan` or KML.
C3. Plot hazards: power lines, masts, pylons, buildings, terrain above the flight height, no-fly areas.
C4. Select the launch/recovery site and an alternate. Both must be flat, clear, out of observation, with
    line of sight to the whole block.
C5. Plan the GCPs (≥ 5; 9 for 1 km²) and ICPs (≥ 20, stratified open/vegetated).
C6. Define the contingencies: lost link (RTH at a height that clears the pylons), GNSS loss (hold, then
    land or attitude mode by RP decision), low battery, an incursion by manned aircraft, a C-UAS
    engagement (abort, land, report).
C7. Brief the crew: task, plan, hazards, contingencies, roles, comms, timings. MC signs the plan.

### Phase D: Pre-flight (RP, DO, survey NCO)
D1. Lay out and survey the GCPs and ICPs (GNSS RTK, 3 min occupation, record photographs and sketches).
D2. Aircraft checks: airframe, propellers, batteries (cycle count, temperature), firmware, compass/IMU
    calibration if prompted, RTK fix.
D3. Camera checks: mechanical shutter, fixed focus, shutter ≤ 1/1000 s, ISO ≤ 400, white balance fixed,
    storage formatted, time synchronised.
D4. Upload the mission. Verify the altitudes, geofence and trigger distance on the ground station.

### Phase E: Flight (RP, DO)
E1. Take off, hover check and climb. Start the mission.
E2. Monitor: battery, RTK status, link quality, image counter, wind, airspace.
E3. Change batteries between sorties. Resume at the correct line.
E4. Abort criteria: lost RTK for more than 30 s, wind above the limit, airspace intrusion, C-UAS warning,
    unexpected people under the flight path.

### Phase F: Post-flight and field QA (DO)
F1. Download and back up the images (two copies) with checksums. Log flight times and battery data.
F2. Field QA: image count compared with the plan, sample blur check, coverage map (WebODM quick preview
    or low-resolution ortho). Re-fly any gaps before leaving the site.
F3. Recover the GCP targets (or leave them for a repeat survey if authorised).

### Phase G: Processing (TA)
G1. Process in WebODM/ODM with GCPs (docs/02). Keep the ICPs out of the adjustment.
G2. Accuracy check at the ICPs: RMSEz by stratum and RMSEr. Compare with the specification.
    Fail: investigate the GCPs, re-process, or re-fly.
G3. Resample and clip to the analysis grid. Generate the hillshade and contours.

### Phase H: GIS analysis (TA)
H1. Update the terrain database: digitise or confirm roads, water, buildings, obstacles and crossings
    from the ortho. Record the confidence of each feature.
H2. Run **GOING terrain analysis** (profile, season and criteria version recorded).
H3. Run **GOING route analysis** for the nominated points. Use the line of sight if a threat or OP is known.
H4. Review the RECCE areas and produce the reconnaissance tasking list (crossings, woodland edges, wet ground).

### Phase I: Validation (TA, patrols)
I1. Generate the stratified sample points (at least 50 per class where time allows; 20 as a minimum).
I2. Patrols record the observed class, photographs and notes in QField/Mergin, or on paper with grid references.
I3. Compute the confusion matrix, OA, kappa, per-class accuracy and unsafe errors. Update the product
    status ("UAS-derived, partially validated" or "validated").

### Phase J: Production and dissemination (TA, MC)
J1. Produce the A3 GOING map and route sheet from the QGIS layouts (marking, legend, grid, scale, north
    arrow, criteria version, validity, lineage).
J2. Write the metadata (docs/05) and complete the data-quality checklist (docs/08).
J3. The MC releases the product. Disseminate through the GIM catalogue / file share with the agreed naming:
    `AOI_<name>_GOING_<profile>_<season>_v<NN>_<DTG>`.
J4. Brief the user (operator briefing): the BLUF, the map, the routes, the limitations and the validity period.

### Phase K: Maintenance
K1. Monitor the change triggers (docs/07). Re-task the survey or re-run the model as required.
K2. Archive the raw images, processing logs, products and metadata according to retention rules.

## 4. Timelines (planning guide, 1 km², 3-person team)

| Activity | Typical duration |
|---|---|
| Phases A-C (task to approved plan) | 1-2 h, dominated by authorisation and deconfliction |
| Phases D-F (GCPs, 3 sorties, QA) | 2-3 h |
| Phase G (processing on a 32 GB workstation) | 2-4 h for about 1,500 images |
| Phase H (analysis, models, maps) | < 1 h (automated) |
| Phase I (validation patrols) | 2-6 h, depending on access |

## 5. Safety and security
* Never fly over people not involved in the operation. Maintain visual line of sight unless authorised otherwise.
* Treat imagery of people, vehicles and private property under the applicable privacy and security rules.
* Mark every product. Do not mix exercise and real data in one database.
