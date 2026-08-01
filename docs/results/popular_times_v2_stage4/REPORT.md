# Popular Times V2 Stage 4 Core Production Matrix

## Status

COMPLETE: 130 of 130 runs have completion artifacts; 130 completed runs pass every invariant.

All production configurations use 56 daily cycles of 24 hourly steps. Levy-off scenarios are deterministic and run once. The 13-region Levy-on scenarios use matched seeds 0–29; the 94-region Levy-on scenario uses seeds 0–4. Where applicable, 95% t intervals are calculated across paired stochastic runs. Deterministic results are reported without artificial confidence intervals.

| Scenario | n | Fulfillment (95% CI) | Travelers/capita (95% CI) | Distance/request (95% CI) | Occupancy/request (95% CI) |
|---|---:|---:|---:|---:|---:|
| 13_levy_off_flood_none | 1 | 1.0000 | 17.9997 | 86.7901 | 1.0000 |
| 13_levy_off_flood_pois | 1 | 0.9649 | 17.3672 | 80.3369 | 0.9649 |
| 13_levy_off_flood_homes | 1 | 1.0000 | 17.9997 | 93.3187 | 1.0000 |
| 13_levy_off_flood_both | 1 | 0.9649 | 17.3672 | 80.8061 | 0.9649 |
| 13_levy_on_flood_none | 30 | 1.0000 [1.0000, 1.0000] | 17.9997 [17.9997, 17.9997] | 81.9953 [81.9928, 81.9977] | 1.0000 [1.0000, 1.0000] |
| 13_levy_on_flood_pois | 30 | 0.9649 [0.9649, 0.9649] | 17.3672 [17.3672, 17.3672] | 76.2669 [76.2645, 76.2693] | 0.9649 [0.9649, 0.9649] |
| 13_levy_on_flood_homes | 30 | 1.0000 [1.0000, 1.0000] | 17.9997 [17.9997, 17.9997] | 88.9408 [88.9304, 88.9512] | 1.0000 [1.0000, 1.0000] |
| 13_levy_on_flood_both | 30 | 0.9649 [0.9649, 0.9649] | 17.3672 [17.3672, 17.3672] | 76.8287 [76.8257, 76.8316] | 0.9649 [0.9649, 0.9649] |
| 94_levy_off_flood_none | 1 | 1.0000 | 18.0000 | 89.8840 | 1.0000 |
| 94_levy_on_flood_none | 5 | 1.0000 [1.0000, 1.0000] | 18.0000 [18.0000, 18.0000] | 84.0157 [83.9998, 84.0316] | 1.0000 [1.0000, 1.0000] |

## Contrasts

Effects are absolute differences (first condition minus reference); fulfillment-rate differences are percentage-point fractions.

| Contrast | Environment | Stratum | Metric | n | Mean difference | 95% CI |
|---|---|---|---|---:|---:|---:|
| levy_on_minus_off | 13 | none | fulfillment_rate | 30 | 0.0000 | [0.0000, 0.0000] |
| levy_on_minus_off | 13 | none | travelers_per_capita | 30 | 0.0000 | [0.0000, 0.0000] |
| levy_on_minus_off | 13 | none | distance_per_requested_visit | 30 | -4.7948 | [-4.7973, -4.7923] |
| levy_on_minus_off | 13 | none | occupancy_per_requested_visit | 30 | 0.0000 | [0.0000, 0.0000] |
| levy_on_minus_off | 13 | pois | fulfillment_rate | 30 | 0.0000 | [0.0000, 0.0000] |
| levy_on_minus_off | 13 | pois | travelers_per_capita | 30 | 0.0000 | [0.0000, 0.0000] |
| levy_on_minus_off | 13 | pois | distance_per_requested_visit | 30 | -4.0700 | [-4.0724, -4.0676] |
| levy_on_minus_off | 13 | pois | occupancy_per_requested_visit | 30 | 0.0000 | [0.0000, 0.0000] |
| levy_on_minus_off | 13 | homes | fulfillment_rate | 30 | 0.0000 | [0.0000, 0.0000] |
| levy_on_minus_off | 13 | homes | travelers_per_capita | 30 | 0.0000 | [0.0000, 0.0000] |
| levy_on_minus_off | 13 | homes | distance_per_requested_visit | 30 | -4.3779 | [-4.3883, -4.3675] |
| levy_on_minus_off | 13 | homes | occupancy_per_requested_visit | 30 | 0.0000 | [0.0000, 0.0000] |
| levy_on_minus_off | 13 | both | fulfillment_rate | 30 | 0.0000 | [0.0000, 0.0000] |
| levy_on_minus_off | 13 | both | travelers_per_capita | 30 | 0.0000 | [0.0000, 0.0000] |
| levy_on_minus_off | 13 | both | distance_per_requested_visit | 30 | -3.9774 | [-3.9804, -3.9745] |
| levy_on_minus_off | 13 | both | occupancy_per_requested_visit | 30 | 0.0000 | [0.0000, 0.0000] |
| levy_on_minus_off | 94 | none | fulfillment_rate | 5 | 0.0000 | [0.0000, 0.0000] |
| levy_on_minus_off | 94 | none | travelers_per_capita | 5 | 0.0000 | [0.0000, 0.0000] |
| levy_on_minus_off | 94 | none | distance_per_requested_visit | 5 | -5.8683 | [-5.8842, -5.8524] |
| levy_on_minus_off | 94 | none | occupancy_per_requested_visit | 5 | 0.0000 | [0.0000, 0.0000] |
| flood_pois_minus_none | 13 | off | fulfillment_rate | 1 | -0.0351 | deterministic |
| flood_pois_minus_none | 13 | off | travelers_per_capita | 1 | -0.6325 | deterministic |
| flood_pois_minus_none | 13 | off | distance_per_requested_visit | 1 | -6.4531 | deterministic |
| flood_pois_minus_none | 13 | off | occupancy_per_requested_visit | 1 | -0.0351 | deterministic |
| flood_homes_minus_none | 13 | off | fulfillment_rate | 1 | 0.0000 | deterministic |
| flood_homes_minus_none | 13 | off | travelers_per_capita | 1 | 0.0000 | deterministic |
| flood_homes_minus_none | 13 | off | distance_per_requested_visit | 1 | 6.5286 | deterministic |
| flood_homes_minus_none | 13 | off | occupancy_per_requested_visit | 1 | 0.0000 | deterministic |
| flood_both_minus_none | 13 | off | fulfillment_rate | 1 | -0.0351 | deterministic |
| flood_both_minus_none | 13 | off | travelers_per_capita | 1 | -0.6325 | deterministic |
| flood_both_minus_none | 13 | off | distance_per_requested_visit | 1 | -5.9840 | deterministic |
| flood_both_minus_none | 13 | off | occupancy_per_requested_visit | 1 | -0.0351 | deterministic |
| flood_pois_x_homes | 13 | off | fulfillment_rate | 1 | 0.0000 | deterministic |
| flood_pois_x_homes | 13 | off | travelers_per_capita | 1 | 0.0000 | deterministic |
| flood_pois_x_homes | 13 | off | distance_per_requested_visit | 1 | -6.0595 | deterministic |
| flood_pois_x_homes | 13 | off | occupancy_per_requested_visit | 1 | 0.0000 | deterministic |
| flood_pois_minus_none | 13 | on | fulfillment_rate | 30 | -0.0351 | [-0.0351, -0.0351] |
| flood_pois_minus_none | 13 | on | travelers_per_capita | 30 | -0.6325 | [-0.6325, -0.6325] |
| flood_pois_minus_none | 13 | on | distance_per_requested_visit | 30 | -5.7284 | [-5.7295, -5.7272] |
| flood_pois_minus_none | 13 | on | occupancy_per_requested_visit | 30 | -0.0351 | [-0.0351, -0.0351] |
| flood_homes_minus_none | 13 | on | fulfillment_rate | 30 | 0.0000 | [0.0000, 0.0000] |
| flood_homes_minus_none | 13 | on | travelers_per_capita | 30 | 0.0000 | [0.0000, 0.0000] |
| flood_homes_minus_none | 13 | on | distance_per_requested_visit | 30 | 6.9455 | [6.9355, 6.9556] |
| flood_homes_minus_none | 13 | on | occupancy_per_requested_visit | 30 | 0.0000 | [0.0000, 0.0000] |
| flood_both_minus_none | 13 | on | fulfillment_rate | 30 | -0.0351 | [-0.0351, -0.0351] |
| flood_both_minus_none | 13 | on | travelers_per_capita | 30 | -0.6325 | [-0.6325, -0.6325] |
| flood_both_minus_none | 13 | on | distance_per_requested_visit | 30 | -5.1666 | [-5.1687, -5.1645] |
| flood_both_minus_none | 13 | on | occupancy_per_requested_visit | 30 | -0.0351 | [-0.0351, -0.0351] |
| flood_pois_x_homes | 13 | on | fulfillment_rate | 30 | 0.0000 | [0.0000, 0.0000] |
| flood_pois_x_homes | 13 | on | travelers_per_capita | 30 | 0.0000 | [0.0000, 0.0000] |
| flood_pois_x_homes | 13 | on | distance_per_requested_visit | 30 | -6.3838 | [-6.3935, -6.3741] |
| flood_pois_x_homes | 13 | on | occupancy_per_requested_visit | 30 | 0.0000 | [0.0000, 0.0000] |
| levy_x_flood_pois | 13 | pois | fulfillment_rate | 30 | 0.0000 | [0.0000, 0.0000] |
| levy_x_flood_pois | 13 | pois | travelers_per_capita | 30 | 0.0000 | [0.0000, 0.0000] |
| levy_x_flood_pois | 13 | pois | distance_per_requested_visit | 30 | 0.7248 | [0.7236, 0.7259] |
| levy_x_flood_pois | 13 | pois | occupancy_per_requested_visit | 30 | 0.0000 | [0.0000, 0.0000] |
| levy_x_flood_homes | 13 | homes | fulfillment_rate | 30 | 0.0000 | [0.0000, 0.0000] |
| levy_x_flood_homes | 13 | homes | travelers_per_capita | 30 | 0.0000 | [0.0000, 0.0000] |
| levy_x_flood_homes | 13 | homes | distance_per_requested_visit | 30 | 0.4169 | [0.4068, 0.4269] |
| levy_x_flood_homes | 13 | homes | occupancy_per_requested_visit | 30 | 0.0000 | [0.0000, 0.0000] |
| levy_x_flood_both | 13 | both | fulfillment_rate | 30 | 0.0000 | [0.0000, 0.0000] |
| levy_x_flood_both | 13 | both | travelers_per_capita | 30 | 0.0000 | [0.0000, 0.0000] |
| levy_x_flood_both | 13 | both | distance_per_requested_visit | 30 | 0.8174 | [0.8153, 0.8195] |
| levy_x_flood_both | 13 | both | occupancy_per_requested_visit | 30 | 0.0000 | [0.0000, 0.0000] |

## Outputs

`production_runs.csv` contains run-level demand, trips, travelers, distance, occupancy, runtime, memory, and validation results. `production_poi_type.csv` provides the same mobility outcomes by POI type. `production_region.csv` aggregates demand and occupancy geographically by destination region, and `production_region_od.csv` contains Popular Times origin–destination flows. `production_scenario_statistics.csv` and `production_effects.csv` contain descriptive estimates and the pre-specified 95% intervals.

The per-run directories retain the raw Popular Times, movement, enumeration-area OD, population, and node-state records needed for audit or alternative analyses. The largest raw CSVs are stored losslessly as `.csv.gz` by default to keep the production matrix within practical disk bounds.

## Gate 4 boundary

The complete core matrix is ready for Gate 4 review. Stage 5 rerouting adaptation has not been started.
