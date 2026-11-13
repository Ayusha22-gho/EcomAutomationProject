# Validation and Accuracy Assessment Report - AOI KESTREL

**UNCLASSIFIED // EXERCISE ONLY // SYNTHETIC DATA**

> **Status of these results: SIMULATED.** The reference observations below were generated from a hidden
> "ground truth" model (true terrain, soil wetness, understorey density and crossing capacities that the
> UAS could not see). The *method* is real and transferable; the *numbers* only show how the method behaves.
> They are not evidence of how accurate the approach would be on real ground.

Product assessed: `rasters/going_class.tif` (profile `wheeled_4x4`, season `wet`). Generated automatically by
`run_pipeline.py`. Re-running with the same configuration reproduces these figures exactly (fixed seed).

## 1. Elevation model accuracy (independent check points)

25 independent check points (ICPs, *not* used as GCPs) were "surveyed" by simulated GNSS RTK
(sigma 0.02 m) and split into non-vegetated and vegetated strata,
following the ASPRS Positional Accuracy Standards (2023) reporting convention.

| Stratum | n | mean_error_m | std_m | rmse_z_m | nva_95_m | p95_abs_m |
|---|---|---|---|---|---|---|
| non-vegetated | 15 | 0.001 | 0.052 | 0.05 | 0.098 | 0.082 |
| vegetated | 10 | 0.172 | 0.661 | 0.65 | 1.275 | 1.224 |

Horizontal (orthomosaic) accuracy: RMSEr = 0.046 m, CE95 = 0.079 m.

**Interpretation.** The non-vegetated vertical accuracy is consistent with a GCP-controlled RGB survey at
~2.7 cm GSD. Under canopy the photogrammetric DTM is interpolated rather than observed. Its error is an order of
magnitude larger and positively biased (ground modelled too high), so slopes inside woodland are unreliable.
This is why canopy areas carry low data-confidence values.

## 2. GOING classification accuracy

* Design: stratified random sampling by **map class**, 50 points per class,
  minimum spacing 20 m (total 200 points).
* Reference: simulated patrol observation (handheld GNSS error ~3 m; observer error rate
  4% between adjacent classes).
* REQUIRES RECCE is an *information* state, not a terrain state. Its points are reported separately to show
  what the ground actually was. They are excluded from overall accuracy.

### Confusion matrix (counts)

| Mapped \ Observed | GO | SLOW-GO | NO-GO |
|---|---|---|---|
| GO | 41 | 9 | 0 |
| SLOW-GO | 16 | 30 | 4 |
| NO-GO | 2 | 11 | 37 |
| REQUIRES RECCE | 19 | 19 | 12 |

| Metric | Value |
|---|---|
| Overall accuracy (determinate classes) | **72.0%** (95% CI 0.64-0.79) |
| Cohen's kappa | 0.580 |
| Area-weighted overall accuracy (Olofsson et al. 2014) | 75.0% |
| Wall-to-wall agreement with truth model (excl. RECCE cells) | 81.3% |
| Safety-critical errors (mapped GO/SLOW-GO, actually NO-GO) | 4 points |
| RECCE points that were in fact SLOW-GO or NO-GO ("flag efficiency") | 62% |

### Per-class accuracy

| class | users_accuracy | ua_95ci | producers_accuracy | pa_95ci | n_mapped |
|---|---|---|---|---|---|
| GO | 0.82 | 0.69-0.90 | 0.695 | 0.57-0.80 | 50 |
| SLOW-GO | 0.6 | 0.46-0.72 | 0.6 | 0.46-0.72 | 50 |
| NO-GO | 0.74 | 0.60-0.84 | 0.902 | 0.77-0.96 | 50 |

### What the RECCE points turned out to be

GO: 19, SLOW-GO: 19, NO-GO: 12.
Flagging is working when a high share of RECCE points proves to be problematic ground. A low share means
the flag is too cautious and is spending reconnaissance effort on ground that would have been GO.

## 3. Sensitivity of the class areas to the illustrative thresholds (% of AOI)

| variant | GO | SLOW-GO | NO-GO | REQUIRES RECCE |
|---|---|---|---|---|
| baseline | 60.7 | 27.9 | 10.2 | 1.2 |
| slope limits -5 deg | 54.2 | 34.1 | 10.5 | 1.2 |
| slope limits +5 deg | 61.7 | 27.1 | 10.0 | 1.2 |
| TWI thresholds -1 | 58.0 | 29.3 | 10.2 | 2.5 |
| TWI thresholds +1 | 61.4 | 27.5 | 10.2 | 0.8 |

The class areas move noticeably when thresholds shift by plus or minus 5 degrees, or when the wetness
threshold shifts by plus or minus 1 TWI unit. Thresholds must therefore be set from vehicle-specific data and
doctrine, and recorded in the product metadata.

## 4. Contribution of each rule to the map (% of AOI)

| reason | area_pct |
|---|---|
| Open, firm, gentle slope | 56.59 |
| Light woodland | 7.51 |
| Cultivated (soft when wet) | 7.03 |
| Dense woodland | 6.88 |
| Scrub | 5.91 |
| Generalised (MMU) | 4.08 |
| Slope SLOW-GO band | 2.71 |
| Built-up area | 2.07 |
| Wet ground (TWI) | 1.3 |
| Marsh (wet season) | 1.24 |
| Water | 1.16 |
| Paved road | 0.81 |
| Unpaved track | 0.66 |
| Stream banks obscured by vegetation | 0.5 |
| Very wet ground (TWI) - soil unknown | 0.45 |
| Slope above NO-GO limit | 0.44 |
| Linear obstacle above step limit | 0.28 |
| Low UAS data confidence | 0.17 |
| Building | 0.15 |
| Crossing - capacity/depth unknown | 0.05 |
| Pylon footing | 0.02 |

## 5. Known error sources and accuracy limitations

1. **Canopy occlusion.** RGB photogrammetry cannot see the ground under closed canopy, stem spacing or
   undergrowth. Dense understorey in "light" woodland is the largest source of GO/SLOW-GO versus NO-GO
   confusion. Linear obstacles under canopy were missed: W2, W3.
2. **Soil strength is not observable from imagery.** TWI is a topographic proxy for wetness and does not
   measure bearing capacity, so soft ground away from drainage lines is under-predicted.
3. **Water.** Photogrammetry produces voids over water. Stream depth, bed material, bank height under
   vegetation and bridge classification (MLC) cannot be derived and are always flagged for reconnaissance.
4. **Temporal validity.** The product describes the conditions at capture date only (see
   docs/06_TERRAIN_SEASONALITY.md).
5. **Generalisation.** A minimum mapping unit of 100 m2 removes
   small patches. Narrow linear obstacles are burned back in after generalisation, but gaps narrower than
   about 2 m may still be closed.
6. **Reference data quality.** Ground observations have their own positional and judgement errors, and
   handheld GNSS error near class boundaries produces apparent disagreement.
7. **Sample size.** With 50 points per class, the 95% confidence
   intervals on per-class accuracy are roughly plus or minus 10-14 percentage points.

## 6. Recommendation

Release the product as **"UAS-derived, partially validated"**. All REQUIRES RECCE areas on selected routes,
and all woodland, must be checked on the ground before being relied upon for movement.
