# Illustrative Mobility Assessment - Route Comparison (SP ALPHA to OBJ BRAVO)

**UNCLASSIFIED // EXERCISE ONLY // SYNTHETIC DATA**

Profile `wheeled_4x4`, season `wet`. Routes are least-cost paths across `going_class.tif` and
`speed_kmh.tif`, with 8-connected moves, computed with the cost definitions below.

| Route | Definition |
|---|---|
| A-DIRECT | Shortest passable distance (avoids NO-GO only) |
| B-FASTEST | Minimum estimated transit time (RECCE cells allowed at reduced speed) |
| C-ASSURED | Minimum time avoiding all REQUIRES-RECCE cells (no unverified crossings) |
| D-CONCEALED | Minimum time weighted by exposure to OP SIERRA line of sight |

## Metrics

| route | length_m | est_time_min | avg_speed_kmh | pct_GO | pct_SLOW_GO | pct_RECCE | pct_on_road_track | max_slope_deg | recce_sections | water_crossings | pct_exposed_to_OP | risk_index | weighted_score | rank |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| A-DIRECT | 1340.0 | 8.5 | 9.5 | 67.6 | 27.8 | 4.6 | 6.3 | 29.2 | 5 | 1 | 35.4 | 68.5 | 0.974 | 4 |
| B-FASTEST | 1439.0 | 4.2 | 20.7 | 92.6 | 6.4 | 1.0 | 86.2 | 14.4 | 1 | 1 | 39.2 | 14.2 | 0.449 | 3 |
| C-ASSURED | 1878.0 | 5.8 | 19.6 | 97.8 | 2.2 | 0.0 | 50.1 | 14.4 | 0 | 0 | 32.1 | 1.1 | 0.331 | 1 |
| D-CONCEALED | 1957.0 | 8.0 | 14.6 | 87.5 | 12.4 | 0.1 | 23.6 | 24.7 | 1 | 0 | 2.8 | 16.3 | 0.366 | 2 |

Weighted score (0 = best) = 0.35 x time + 0.25 x risk + 0.25 x exposure +
0.15 x crossings. Each term is min-max normalised across the candidate routes, and the risk index is
%RECCE + 0.5 x %SLOW-GO + 10 x number of RECCE sections.

## Assessment

* Highest-ranked route under these illustrative weights: **C-ASSURED**
  (1878 m, about 5.8 min, 0.0% on unverified ground,
  32.1% exposed to OP SIERRA).
* Any route with RECCE sections, especially crossings at FORD F1 or BRIDGE B1, should not be committed to
  until engineer or patrol reconnaissance confirms ford depth, bed and banks, or bridge classification.
* The weights express the commander's priorities. Changing them changes the ranking. The tool supports the
  decision but does not make it.
* Transit times use an illustrative speed table and exclude halts, obstacle breaching, navigation errors and
  the effects of enemy action.
