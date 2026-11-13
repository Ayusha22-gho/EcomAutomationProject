# 08 - Data-Quality Checklist

**UNCLASSIFIED // EXERCISE ONLY**

Complete this checklist for every product release. Any **No** against an item marked ★ (critical) blocks
the release until it is resolved or the MC accepts the risk in writing. The "Reference run" column
shows the status of the v1.0 demonstration products.

## A. Planning and collection

| # | Check | Criterion | Reference run |
|---|---|---|---|
| A1 ★ | Authorisation and airspace recorded | Authorisation reference in metadata | n/a (simulated) |
| A2 ★ | Friendly C-UAS deconfliction confirmed | Code word / weapons-hold recorded | n/a (simulated) |
| A3 | GSD meets the requirement | ≤ 5 cm | 2.67 cm ✔ |
| A4 | Overlap adequate for the terrain | ≥ 75/65 % (≥ 85/75 % in forest) | 80/70 % ✔ |
| A5 | Motion blur | < 0.5 px | 0.38 px ✔ |
| A6 | Block covers the AOI plus a buffer | ≥ 1 line spacing beyond the AOI | 60 m ✔ |
| A7 | GCPs: number and distribution | ≥ 5, around the perimeter plus the centre | 9 ✔ |
| A8 ★ | ICPs independent of the GCPs | Not used in the adjustment | ✔ |
| A9 | Image count compared with the plan | ≥ 98 % | n/a (simulated) |
| A10 | Weather within limits | Wind, light, precipitation | n/a |

## B. Photogrammetric processing

| # | Check | Criterion | Reference run |
|---|---|---|---|
| B1 | Images calibrated / aligned | ≥ 98 % | n/a |
| B2 | GCP residuals | < 2 × GSD | n/a |
| B3 ★ | DTM vertical accuracy (non-vegetated) | RMSEz ≤ 0.10 m | 0.05 m ✔ |
| B4 | DTM vertical accuracy (vegetated) reported | Reported, flagged if > 0.30 m | 0.65 m (flagged) ✔ |
| B5 ★ | Ortho horizontal accuracy | RMSEr ≤ 0.10 m | 0.046 m ✔ |
| B6 | Voids and artefacts inspected | Water voids filled and flagged; no spikes | ✔ |
| B7 | CRS and vertical datum correct | EPSG and geoid recorded | EPSG:32630 ✔ |
| B8 | Grid alignment | All rasters on the same 1 m grid | ✔ |

## C. GIS database and analysis

| # | Check | Criterion | Reference run |
|---|---|---|---|
| C1 | Schema complete | All mandatory layers present (blueprint §4.1) | 23 layers ✔ |
| C2 | Geometry valid | No invalid geometries (QGIS Check Validity) | ✔ |
| C3 | Feature attributes complete | type, height/depth, width, source, confidence | ✔ |
| C4 ★ | Crossings attributed | Every bridge/ford has an MLC/depth or is flagged RECCE | ✔ |
| C5 | Criteria version recorded | Version / commit in metadata | ✔ |
| C6 | Profile and season stated on the map | Title or subtitle | ✔ |
| C7 | Reason codes produced | `going_reason.tif` | ✔ |
| C8 | Sensitivity reviewed | ±5° slope, ±1 TWI | ✔ |
| C9 | Independent implementation check | ≥ 95 % agreement | 97.0 % ✔ |
| C10 | Low-confidence areas visible | Confidence map and RECCE class | ✔ |

## D. Validation

| # | Check | Criterion | Reference run |
|---|---|---|---|
| D1 | Sampling design | Stratified random by map class, minimum spacing | 50/class, 20 m ✔ |
| D2 ★ | Overall accuracy | ≥ 70 % (course threshold) | 72 % ✔ (simulated) |
| D3 ★ | Unsafe errors (mapped passable, actually NO-GO) | ≤ 5 % of determinate samples | 2.7 % ✔ |
| D4 | Confidence intervals reported | Wilson 95 % | ✔ |
| D5 | Limitations documented | VALIDATION_REPORT §5 | ✔ |

## E. Cartography and release

| # | Check | Criterion | Reference run |
|---|---|---|---|
| R1 ★ | Security marking | Top and bottom of every map and slide, and in the metadata | ✔ |
| R2 | Map furniture | Title, legend, grid with labels, scale bar, north arrow, CRS | ✔ |
| R3 | Lineage and validity on the map | Source, criteria, "validate before use" | ✔ |
| R4 | Colour scheme consistent | GO green, SLOW-GO amber, NO-GO red, RECCE purple | ✔ |
| R5 ★ | Metadata complete for every product | docs/05 table | 20/20 ✔ |
| R6 | Checksums recorded | SHA-256 | ✔ |
| R7 | Naming convention applied on release | docs/05 §3 | on release |
| R8 ★ | Simulated or unvalidated status clear | `data_status`, briefing slide 3 | ✔ |

**Release block**

| Prepared (TA) | Checked (2IC / peer) | Released (MC) |
|---|---|---|
| Name / sig / DTG | Name / sig / DTG | Name / sig / DTG |
