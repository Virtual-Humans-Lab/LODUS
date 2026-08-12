# Popular Times V2 Stage 5 Flood Adaptation

## Status

COMPLETE: 12 of 12 runs have completion artifacts; 12 pass every invariant.

The 13- and 94-region homes-and-POIs flood scenarios are evaluated with nearest enabled same-type POI rerouting. Levy off is deterministic; Levy on uses matched seeds 0–4. All runs use 56 daily cycles of 24 hourly steps. Confidence intervals are 95% t intervals, while the deterministic result has no artificial interval.

| Scenario | n | Fulfillment | Rerouted fulfilled | Remaining rerouted unmet | POI displacement/traveler (m) | Peak receiving load |
|---|---:|---:|---:|---:|---:|---:|
| 13_levy_off_flood_both_reroute | 1 | 1.0000 | 169736.0 | 0.0 | 293.50 | 142.0 |
| 13_levy_on_flood_both_reroute | 5 | 1.0000 [1.0000, 1.0000] | 169736.0 [169736.0, 169736.0] | 0.0 [0.0, 0.0] | 293.50 [293.50, 293.50] | 142.0 [142.0, 142.0] |
| 94_levy_off_flood_both_reroute | 1 | 1.0000 | 1212703.0 | 2.0 | 1174.45 | 1097.0 |
| 94_levy_on_flood_both_reroute | 5 | 1.0000 [1.0000, 1.0000] | 1212699.8 [1212699.2, 1212700.4] | 5.2 [4.6, 5.8] | 1174.45 [1174.45, 1174.45] | 1097.0 [1097.0, 1097.0] |

## Adaptation versus Stage 4 suppression

Effects are paired absolute differences: rerouting minus the matching Stage 4 homes-and-POIs suppression run.

| Levy stratum | Metric | n | Mean difference | 95% CI |
|---|---|---:|---:|---:|
| 13_levy_off | unmet | 1 | -83445.0000 | deterministic |
| 13_levy_off | fulfillment_rate | 1 | 0.0351 | deterministic |
| 13_levy_off | travelers_per_capita | 1 | 0.6324 | deterministic |
| 13_levy_off | distance_per_requested_visit | 1 | 4.5770 | deterministic |
| 13_levy_off | occupancy_per_requested_visit | 1 | 0.0351 | deterministic |
| 13_levy_on | unmet | 5 | -83445.0000 | [-83445.0000, -83445.0000] |
| 13_levy_on | fulfillment_rate | 5 | 0.0351 | [0.0351, 0.0351] |
| 13_levy_on | travelers_per_capita | 5 | 0.6324 | [0.6324, 0.6324] |
| 13_levy_on | distance_per_requested_visit | 5 | 4.5839 | [4.5708, 4.5969] |
| 13_levy_on | occupancy_per_requested_visit | 5 | 0.0351 | [0.0351, 0.0351] |

## Outputs

`stage5_runs.csv` contains run-level mobility, rerouting, runtime, memory, and validation results. `stage5_poi_type.csv` splits outcomes by POI type. `stage5_receivers.csv` records original-to-receiving POI flows and receiving load. `stage5_scenario_statistics.csv` and `stage5_adaptation_effects.csv` contain the estimates and paired comparisons.

## Gate 5 boundary

The complete adaptation matrix is ready for Gate 5 review.
