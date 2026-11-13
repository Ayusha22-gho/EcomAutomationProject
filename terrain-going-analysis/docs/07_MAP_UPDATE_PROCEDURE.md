# 07 - Map Update Procedure

**UNCLASSIFIED // EXERCISE ONLY**

## 1. Principles
1. **Data-driven.** Every product can be regenerated from the terrain database plus configuration
   (`run_pipeline.py` or the QGIS models). Change the inputs, never the output pixels by hand.
2. **Versioned.** Every release increments `v<NN>`. The previous version is marked SUPERSEDED, not deleted.
3. **Traceable.** Each update records its trigger, the changed layers, the criteria version, the analyst
   and the date in the metadata lineage and in the change log below.

## 2. Update triggers

| Type | Trigger | Action | Priority |
|---|---|---|---|
| Scheduled | Validity period reached (docs/06) | Review; re-run the GOING model with the current season; re-validate a sample | Routine |
| Weather | Rainfall > 25 mm/24 h, flood, freeze/thaw | Switch the season parameter; mark wet-ground and crossings RECCE; task recce | Priority |
| Ground report | Patrol or engineer report that contradicts the map (for example a ford found deeper than the limit) | Edit the attribute (crossing depth/MLC known), re-run; feed the report into validation | Priority |
| Physical change | New obstacle, demolished bridge, cratering, flooding, harvest, construction | Re-fly the affected tiles; update the database features; re-run | Immediate if on a route |
| Criteria change | New vehicle data or doctrine | Update `going_criteria.json` (new version); re-run every affected product | Routine |
| Data improvement | Leaf-off flight, LiDAR, new public DEM | Replace or merge the DTM; re-run; compare the change map | Routine |

## 3. Procedure
1. **Log the trigger** in the change log (DTG, source, location, description).
2. **Assess the extent.** Is the change local (a few features) or AOI-wide (season, criteria)?
3. **Update the inputs:**
   * Local feature change: edit the `terrain_db.gpkg` layer in QGIS (with editing tracked through the
     GeoPackage `last_change` or an `edit_log` layer). Set `source` and `capture_date`.
   * New imagery: process the new block (docs/02), clip it to the changed tiles, mosaic it into the
     DTM/DSM with a feathered seam, and record the per-tile dates.
   * Season or criteria: edit the configuration only.
4. **Re-run** `run_pipeline.py` or the QGIS models with identical settings apart from the change.
5. **Change detection.** Difference the new GOING raster against the previous version (QGIS Raster
   Calculator `"new@1" != "old@1"`) and review every changed area. Large unexplained changes block the release.
6. **Re-validate** if more than 5 % of the AOI or any route section changed: at least 10 new ground
   observations in the changed area.
7. **Release.** Update the metadata (version, data currency, lineage, checksums) and the A3 layouts.
   Supersede the old version. Notify the users of what changed (map extract plus a short text).

## 4. Change log template

| Version | DTG | Trigger | Layers changed | Criteria version | Analyst | Validation | Released by |
|---|---|---|---|---|---|---|---|
| v01 | 131200ZNOV26 | Initial production | all | 1.0 | GEO-1 | 200 sim. obs. | MC |
| v02 | | | | | | | |
