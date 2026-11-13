# 06 - Terrain Seasonality Limitations

**UNCLASSIFIED // EXERCISE ONLY**

A GOING product describes the ground **as it was at capture, for one vehicle class**. Weather and season
change trafficability faster than terrain shape. This annex sets out the effect of season, how the model
represents it, and how long a product stays valid.

## 1. Seasonal effects by factor

| Factor | Dry / summer | Wet / thaw | Frozen / snow | Model representation |
|---|---|---|---|---|
| Soil bearing strength | High on most soils | Low on clays, peat and ploughed ground; ruts after repeated passes | High when frozen; very low during the thaw | TWI thresholds per season (wet 7.8/9.0, dry 9.5/11.0); cultivated SLOW-GO in wet |
| Streams, ditches | Low water, fordable | High, fast water; banks unstable | Ice of unknown strength | Crossings always RECCE; stream and banks NO-GO |
| Marsh / wet meadows | Often passable with care | NO-GO | Possibly passable if frozen hard | Dry: RECCE; wet: NO-GO |
| Vegetation | Full leaf: concealment, no view of the ground | Leaf-off: better ground view in deciduous wood | Leaf-off; snow masks small obstacles | Canopy cover from leaf-on CHM; re-fly leaf-off to improve the DTM |
| Crops | Tall crops restrict view and movement | Ploughed: soft | Bare/frozen | Fields SLOW-GO in wet |
| Slope | Unchanged | Wet clay and grass slopes reduce the climbable slope | Ice: the safe slope falls sharply | Season-specific slope limits can be added in `going_criteria.json` |
| Imagery (UAS) | Good | Low texture over water; puddles | Snow defeats SfM matching | Confidence layer; plan flights for good conditions |

## 2. Demonstrated seasonal variation (reference run, wheeled 4x4)

| Season | GO % | SLOW-GO % | NO-GO % | RECCE % |
|---|---|---|---|---|
| Dry | 69.2 | 19.9 | 9.0 | 2.0 |
| Wet | 60.7 | 27.9 | 10.2 | 1.2 |

See `outputs/reports/class_area_statistics.csv` and map 10. RECCE falls in the wet season because the
marsh moves from RECCE to NO-GO. Uncertainty about whether it can be crossed is replaced by the knowledge
that it cannot.

## 3. Product validity (planning guide)

| Condition since capture | Validity of GOING product |
|---|---|
| Stable dry weather | 30 days |
| Stable wet season | 14 days |
| Rainfall > 25 mm in 24 h, or flooding | **Invalid** for wet-ground classes; re-run with season = wet; RECCE crossings |
| Freeze/thaw transition | **Invalid**; re-assess on the ground |
| Harvest/ploughing, construction, demolition, combat damage | **Invalid** locally; update the affected features (docs/07) |
| Leaf fall | Re-fly to improve the DTM and vegetation structure (optional) |

The DTM and orthomosaic remain valid much longer (months to years) unless the terrain is physically
changed. Only the derived GOING and route products expire quickly.

## 4. Limitations that season cannot fix
* A UAS RGB survey never measures soil strength. Seasonal criteria only *adjust a proxy*.
* Soil type is not modelled. Add a soil or geology layer (for example national soil maps) to refine the
  wetness rules.
* Climate and soils vary between theatres, so thresholds tuned in one region must not be reused
  elsewhere without calibration.
