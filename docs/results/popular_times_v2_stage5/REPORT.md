# Popular Times V2 Stage 5 Flood Adaptation

## Status

COMPLETE: 31 of 31 runs have completion artifacts; 31 pass every invariant.

The 13-region homes-and-POIs flood scenario is evaluated with nearest enabled same-type POI rerouting. Levy off is deterministic; Levy on uses matched seeds 0–29. All runs use 56 daily cycles of 24 hourly steps. Confidence intervals are 95% t intervals, while the deterministic result has no artificial interval.

| Scenario | n | Fulfillment | Rerouted fulfilled | Remaining rerouted unmet | POI displacement/traveler (m) | Peak receiving load |
|---|---:|---:|---:|---:|---:|---:|
| 13_levy_off_flood_both_reroute | 1 | 1.0000 | 83445.0 | 0.0 | 297.89 | 92.0 |
| 13_levy_on_flood_both_reroute | 30 | 1.0000 [1.0000, 1.0000] | 83445.0 [83445.0, 83445.0] | 0.0 [0.0, 0.0] | 297.89 [297.89, 297.89] | 92.0 [92.0, 92.0] |

## Adaptation versus Stage 4 suppression

Effects are paired absolute differences: rerouting minus the matching Stage 4 homes-and-POIs suppression run.

| Levy stratum | Metric | n | Mean difference | 95% CI |
|---|---|---:|---:|---:|
| levy_off | unmet | 1 | -83445.0000 | deterministic |
| levy_off | fulfillment_rate | 1 | 0.0351 | deterministic |
| levy_off | travelers_per_capita | 1 | 0.6325 | deterministic |
| levy_off | distance_per_requested_visit | 1 | 5.0371 | deterministic |
| levy_off | occupancy_per_requested_visit | 1 | 0.0351 | deterministic |
| levy_on | unmet | 30 | -83445.0000 | [-83445.0000, -83445.0000] |
| levy_on | fulfillment_rate | 30 | 0.0351 | [0.0351, 0.0351] |
| levy_on | travelers_per_capita | 30 | 0.6325 | [0.6325, 0.6325] |
| levy_on | distance_per_requested_visit | 30 | 4.8447 | [4.8386, 4.8507] |
| levy_on | occupancy_per_requested_visit | 30 | 0.0351 | [0.0351, 0.0351] |

## Outputs

`stage5_runs.csv` contains run-level mobility, rerouting, runtime, memory, and validation results. `stage5_poi_type.csv` splits outcomes by POI type. `stage5_receivers.csv` records original-to-receiving POI flows and receiving load. `stage5_scenario_statistics.csv` and `stage5_adaptation_effects.csv` contain the estimates and paired comparisons.

## Gate 5 boundary

The complete adaptation matrix is ready for Gate 5 review.
