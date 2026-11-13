# 05 - GIS Metadata Standard (course profile)

**UNCLASSIFIED // EXERCISE ONLY**

Profile based on the ISO 19115-1 core elements, extended with the military handling fields needed for
terrain products. `run_pipeline.py` writes one JSON record per product to `outputs/metadata/`, plus
`catalogue.json`. Records must be completed or confirmed by the terrain analyst before release.

## 1. Mandatory elements

| Element | Key in JSON | Content rule | Example |
|---|---|---|---|
| File identifier | `file_identifier` | Unique, stable, matches the file stem | `going_class` |
| Title | `title` | What, where, profile, season | GOING class wheeled_4x4/wet |
| Abstract | `abstract` | Purpose, content, method in 1-3 sentences | |
| Security marking | `security_marking` | Classification and caveats exactly as on the map | UNCLASSIFIED // EXERCISE ONLY // SYNTHETIC DATA |
| Point of contact | `point_of_contact` | Producing cell | Course Syndicate GEO-1 |
| Date created | `date_created_utc` | ISO 8601 UTC | 2026-11-13T20:00:00Z |
| Data currency / validity | `data_currency` | Capture date and validity period (docs/06, 07) | Capture D-day 0; wet season; valid 14 days |
| Reference system | `reference_system` | EPSG code | EPSG:32630 |
| Vertical datum | `vertical_datum` | Datum and geoid model | Ellipsoidal reduced to local geoid |
| Extent | `extent_bbox` | xmin, ymin, xmax, ymax in the reference system | |
| Resolution | `spatial_resolution_m` | Ground cell size | 1.0 |
| Lineage | `lineage` | Ordered processing steps, software and versions, inputs | |
| Positional accuracy | `positional_accuracy` | RMSEz by stratum, RMSEr, and how they were measured | RMSEz 0.05 m non-veg (n = 15 ICPs) |
| Thematic accuracy | (report link) | OA, kappa, sample size, date | VALIDATION_REPORT.md |
| Data status | `data_status` | SIMULATED / UAS-derived unvalidated / partially validated / validated / superseded | SIMULATED |
| Keywords | `keywords` | Controlled list: terrain, GOING, UAS, DEM, orthomosaic, route, validation | |
| Checksum | `checksum_sha256` | SHA-256 of the file as released | |
| Software | `software` | Name and version | going-pipeline v1.0, QGIS 3.34.4 |

## 2. Conditional elements (GOING and route products)

| Element | Rule |
|---|---|
| Criteria version | Name and version of `going_criteria.json` (commit hash) |
| Vehicle profile | `wheeled_4x4` / `tracked` / specific vehicle |
| Season / ground state | dry / wet / frozen / snow, and the observation that justified it |
| Minimum mapping unit | m² |
| Route weights | Time, risk, exposure and crossing weights used |
| Validation status | Number of ground observations, date, observer unit |

## 3. File naming

`AOI_<AOI>_<PRODUCT>_<PROFILE>_<SEASON>_v<NN>_<DTG>.<ext>`, for example
`AOI_KESTREL_GOING_WHL_WET_v01_131200ZNOV26.tif`. Inside the repository the short working names are used
(`going_class.tif`) and the full name is applied on release.

## 4. Formats

| Data | Format | Settings |
|---|---|---|
| Raster | GeoTIFF (tiled 256, DEFLATE, overviews 2/4/8; COG for web) | Float32 with predictor 3; class rasters UInt8 with a colour table |
| Vector | GeoPackage, one file per AOI | Layer names as in blueprint §4.1; no shapefiles |
| Maps | PDF (vector) + PNG preview | Marking top and bottom; grid, scale, north arrow, legend, lineage box |
| Styles | QML alongside the project | `qgis/styles/` |

## 5. Quality control of metadata
* Before release, check every record against the table above (checklist item R5, docs/08).
* Recompute the checksums after any edit; a mismatch means the file has changed.
* Keep metadata with the data in the same folder or GeoPackage. Never send data without metadata.
