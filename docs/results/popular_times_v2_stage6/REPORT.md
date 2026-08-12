# Popular Times V2 Stage 6 — Levy Walk V2

## Status

COMPLETE: 50 of 50 runs are preserved; all runs pass both Popular Times and Levy V2 invariants.

All scenarios use 56 daily cycles and flood-aware commute lifecycles. The 13- and 94-region families use paired seeds 0–4. Levy V2 uses a maximum packet size of 50 and exact cycle-level worker/student attendance. Intervals are paired or scenario-level 95% t intervals.

| Scenario | n | Levy fulfillment | Levy unmet | Moved population | Mean commute distance (m) | PT fulfillment |
|---|---:|---:|---:|---:|---:|---:|
| 13_levy_v2_flood_none | 5 | 1.0000 [1.0000, 1.0000] | 2.8 [1.8, 3.8] | 6829947.6 [6829394.9, 6830500.3] | 1411.15 [1408.36, 1413.95] | 1.0000 [1.0000, 1.0000] |
| 13_levy_v2_flood_destinations | 5 | 0.9247 [0.9241, 0.9253] | 514114.4 [510187.6, 518041.2] | 6315836.0 [6311572.8, 6320099.2] | 1382.67 [1378.92, 1386.41] | 0.9410 [0.9410, 0.9410] |
| 13_levy_v2_flood_homes | 5 | 0.8927 [0.8922, 0.8932] | 733115.8 [729680.3, 736551.3] | 6096834.6 [6093179.7, 6100489.5] | 1408.29 [1405.68, 1410.89] | 1.0000 [1.0000, 1.0000] |
| 13_levy_v2_flood_all | 5 | 0.8489 [0.8479, 0.8498] | 1032192.2 [1025737.6, 1038646.8] | 5797758.2 [5790758.8, 5804757.6] | 1364.93 [1362.80, 1367.07] | 0.9410 [0.9410, 0.9410] |
| 13_levy_v2_flood_all_pt_reroute | 5 | 0.8476 [0.8470, 0.8482] | 1040775.8 [1036693.4, 1044858.2] | 5789174.6 [5784870.5, 5793478.7] | 1364.47 [1362.95, 1365.99] | 1.0000 [1.0000, 1.0000] |
| 94_levy_v2_flood_none | 5 | 1.0000 [1.0000, 1.0000] | 858.4 [755.0, 961.8] | 56911650.4 [56910180.9, 56913119.9] | 3687.91 [3685.82, 3689.99] | 1.0000 [1.0000, 1.0000] |
| 94_levy_v2_flood_destinations | 5 | 0.9436 [0.9435, 0.9437] | 3209072.4 [3203883.9, 3214260.9] | 53703436.4 [53697565.3, 53709307.5] | 3505.32 [3498.81, 3511.82] | 0.9494 [0.9494, 0.9494] |
| 94_levy_v2_flood_homes | 5 | 0.9316 [0.9314, 0.9318] | 3892860.8 [3882967.3, 3902754.3] | 53019648.0 [53009879.8, 53029416.2] | 3654.26 [3649.95, 3658.56] | 1.0000 [1.0000, 1.0000] |
| 94_levy_v2_flood_all | 5 | 0.9031 [0.9030, 0.9033] | 5512150.6 [5503391.0, 5520910.2] | 51400358.2 [51390664.4, 51410052.0] | 3423.69 [3421.03, 3426.35] | 0.9494 [0.9494, 0.9494] |
| 94_levy_v2_flood_all_pt_reroute | 5 | 0.9024 [0.9019, 0.9028] | 5556421.6 [5531328.0, 5581515.2] | 51356087.2 [51330218.5, 51381955.9] | 3423.25 [3421.73, 3424.78] | 1.0000 [1.0000, 1.0000] |

## Flood effects versus the Levy V2 no-flood baseline

Effects below are paired by seed and reported as flood condition minus no flood.

| Contrast | Metric | n | Mean difference | 95% CI |
|---|---|---:|---:|---:|
| 13_levy_v2_flood_destinations_minus_13_levy_v2_flood_none | pt_fulfillment_rate | 5 | -0.0590 | [-0.0590, -0.0590] |
| 13_levy_v2_flood_destinations_minus_13_levy_v2_flood_none | pt_unmet | 5 | 169736.0000 | [169736.0000, 169736.0000] |
| 13_levy_v2_flood_destinations_minus_13_levy_v2_flood_none | levy_fulfillment_rate | 5 | -0.0753 | [-0.0759, -0.0747] |
| 13_levy_v2_flood_destinations_minus_13_levy_v2_flood_none | levy_unmet | 5 | 514111.6000 | [510184.3257, 518038.8743] |
| 13_levy_v2_flood_destinations_minus_13_levy_v2_flood_none | levy_mean_outbound_distance | 5 | -28.4852 | [-32.4991, -24.4714] |
| 13_levy_v2_flood_homes_minus_13_levy_v2_flood_none | pt_fulfillment_rate | 5 | 0.0000 | [0.0000, 0.0000] |
| 13_levy_v2_flood_homes_minus_13_levy_v2_flood_none | pt_unmet | 5 | 0.0000 | [0.0000, 0.0000] |
| 13_levy_v2_flood_homes_minus_13_levy_v2_flood_none | levy_fulfillment_rate | 5 | -0.1073 | [-0.1078, -0.1068] |
| 13_levy_v2_flood_homes_minus_13_levy_v2_flood_none | levy_unmet | 5 | 733113.0000 | [729677.1966, 736548.8034] |
| 13_levy_v2_flood_homes_minus_13_levy_v2_flood_none | levy_mean_outbound_distance | 5 | -2.8646 | [-4.8273, -0.9019] |
| 13_levy_v2_flood_all_minus_13_levy_v2_flood_none | pt_fulfillment_rate | 5 | -0.0590 | [-0.0590, -0.0590] |
| 13_levy_v2_flood_all_minus_13_levy_v2_flood_none | pt_unmet | 5 | 169736.0000 | [169736.0000, 169736.0000] |
| 13_levy_v2_flood_all_minus_13_levy_v2_flood_none | levy_fulfillment_rate | 5 | -0.1511 | [-0.1521, -0.1502] |
| 13_levy_v2_flood_all_minus_13_levy_v2_flood_none | levy_unmet | 5 | 1032189.4000 | [1025734.2297, 1038644.5703] |
| 13_levy_v2_flood_all_minus_13_levy_v2_flood_none | levy_mean_outbound_distance | 5 | -46.2193 | [-51.0440, -41.3947] |
| 13_levy_v2_flood_all_pt_reroute_minus_13_levy_v2_flood_none | pt_fulfillment_rate | 5 | 0.0000 | [0.0000, 0.0000] |
| 13_levy_v2_flood_all_pt_reroute_minus_13_levy_v2_flood_none | pt_unmet | 5 | 0.0000 | [0.0000, 0.0000] |
| 13_levy_v2_flood_all_pt_reroute_minus_13_levy_v2_flood_none | levy_fulfillment_rate | 5 | -0.1524 | [-0.1530, -0.1518] |
| 13_levy_v2_flood_all_pt_reroute_minus_13_levy_v2_flood_none | levy_unmet | 5 | 1040773.0000 | [1036689.8261, 1044856.1739] |
| 13_levy_v2_flood_all_pt_reroute_minus_13_levy_v2_flood_none | levy_mean_outbound_distance | 5 | -46.6818 | [-50.3475, -43.0161] |
| 94_levy_v2_flood_destinations_minus_94_levy_v2_flood_none | pt_fulfillment_rate | 5 | -0.0506 | [-0.0506, -0.0506] |
| 94_levy_v2_flood_destinations_minus_94_levy_v2_flood_none | pt_unmet | 5 | 1212705.0000 | [1212705.0000, 1212705.0000] |
| 94_levy_v2_flood_destinations_minus_94_levy_v2_flood_none | levy_fulfillment_rate | 5 | -0.0564 | [-0.0565, -0.0563] |
| 94_levy_v2_flood_destinations_minus_94_levy_v2_flood_none | levy_unmet | 5 | 3208214.0000 | [3202980.7490, 3213447.2510] |
| 94_levy_v2_flood_destinations_minus_94_levy_v2_flood_none | levy_mean_outbound_distance | 5 | -182.5902 | [-187.1532, -178.0273] |
| 94_levy_v2_flood_homes_minus_94_levy_v2_flood_none | pt_fulfillment_rate | 5 | -0.0000 | [-0.0000, 0.0000] |
| 94_levy_v2_flood_homes_minus_94_levy_v2_flood_none | pt_unmet | 5 | 1.8000 | [-0.5884, 4.1884] |
| 94_levy_v2_flood_homes_minus_94_levy_v2_flood_none | levy_fulfillment_rate | 5 | -0.0684 | [-0.0686, -0.0682] |
| 94_levy_v2_flood_homes_minus_94_levy_v2_flood_none | levy_unmet | 5 | 3892002.4000 | [3882097.3455, 3901907.4545] |
| 94_levy_v2_flood_homes_minus_94_levy_v2_flood_none | levy_mean_outbound_distance | 5 | -33.6523 | [-37.7196, -29.5850] |
| 94_levy_v2_flood_all_minus_94_levy_v2_flood_none | pt_fulfillment_rate | 5 | -0.0506 | [-0.0506, -0.0506] |
| 94_levy_v2_flood_all_minus_94_levy_v2_flood_none | pt_unmet | 5 | 1212705.0000 | [1212705.0000, 1212705.0000] |
| 94_levy_v2_flood_all_minus_94_levy_v2_flood_none | levy_fulfillment_rate | 5 | -0.0968 | [-0.0970, -0.0967] |
| 94_levy_v2_flood_all_minus_94_levy_v2_flood_none | levy_unmet | 5 | 5511292.2000 | [5502549.8954, 5520034.5046] |
| 94_levy_v2_flood_all_minus_94_levy_v2_flood_none | levy_mean_outbound_distance | 5 | -264.2185 | [-265.0777, -263.3592] |
| 94_levy_v2_flood_all_pt_reroute_minus_94_levy_v2_flood_none | pt_fulfillment_rate | 5 | -0.0000 | [-0.0000, 0.0000] |
| 94_levy_v2_flood_all_pt_reroute_minus_94_levy_v2_flood_none | pt_unmet | 5 | 16.6000 | [-9.4098, 42.6098] |
| 94_levy_v2_flood_all_pt_reroute_minus_94_levy_v2_flood_none | levy_fulfillment_rate | 5 | -0.0976 | [-0.0981, -0.0972] |
| 94_levy_v2_flood_all_pt_reroute_minus_94_levy_v2_flood_none | levy_unmet | 5 | 5555563.2000 | [5530503.0038, 5580623.3962] |
| 94_levy_v2_flood_all_pt_reroute_minus_94_levy_v2_flood_none | levy_mean_outbound_distance | 5 | -264.6553 | [-267.8057, -261.5048] |

## Cross-version comparisons

Each new family is paired to the matching Stage 4 suppression or Stage 5 Popular Times rerouting family. These are deliberately labeled combined model revisions because Levy V2 changes commute demand/lifecycle and destination flooding newly includes work and school. Legacy outputs do not contain the Levy V2 demand audit fields, so cross-version tables compare the shared Popular Times outcome metrics.

| New scenario | Legacy | Metric | n | V2 − legacy | 95% CI |
|---|---|---|---:|---:|---:|
| 13_levy_v2_flood_all | stage4:13_levy_on_flood_both | fulfillment_rate | 5 | -0.0238 | [-0.0238, -0.0238] |
| 13_levy_v2_flood_all | stage4:13_levy_on_flood_both | unmet | 5 | 86291.0000 | [86291.0000, 86291.0000] |
| 13_levy_v2_flood_all | stage4:13_levy_on_flood_both | mean_distance_per_traveler | 5 | 6.0660 | [5.5255, 6.6064] |
| 13_levy_v2_flood_all_pt_reroute | stage5:13_levy_on_flood_both_reroute | fulfillment_rate | 5 | 0.0000 | [0.0000, 0.0000] |
| 13_levy_v2_flood_all_pt_reroute | stage5:13_levy_on_flood_both_reroute | unmet | 5 | 0.0000 | [0.0000, 0.0000] |
| 13_levy_v2_flood_all_pt_reroute | stage5:13_levy_on_flood_both_reroute | mean_distance_per_traveler | 5 | 4.9298 | [4.4669, 5.3927] |
| 13_levy_v2_flood_destinations | stage4:13_levy_on_flood_pois | fulfillment_rate | 5 | -0.0238 | [-0.0238, -0.0238] |
| 13_levy_v2_flood_destinations | stage4:13_levy_on_flood_pois | unmet | 5 | 86291.0000 | [86291.0000, 86291.0000] |
| 13_levy_v2_flood_destinations | stage4:13_levy_on_flood_pois | mean_distance_per_traveler | 5 | 5.3363 | [5.3208, 5.3518] |
| 13_levy_v2_flood_homes | stage4:13_levy_on_flood_homes | fulfillment_rate | 5 | 0.0000 | [0.0000, 0.0000] |
| 13_levy_v2_flood_homes | stage4:13_levy_on_flood_homes | unmet | 5 | 0.0000 | [0.0000, 0.0000] |
| 13_levy_v2_flood_homes | stage4:13_levy_on_flood_homes | mean_distance_per_traveler | 5 | 13.7101 | [13.4534, 13.9668] |
| 13_levy_v2_flood_none | stage4:13_levy_on_flood_none | fulfillment_rate | 5 | 0.0000 | [0.0000, 0.0000] |
| 13_levy_v2_flood_none | stage4:13_levy_on_flood_none | unmet | 5 | 0.0000 | [0.0000, 0.0000] |
| 13_levy_v2_flood_none | stage4:13_levy_on_flood_none | mean_distance_per_traveler | 5 | 4.5285 | [4.5146, 4.5423] |
| 94_levy_v2_flood_none | stage4:94_levy_on_flood_none | fulfillment_rate | 5 | 0.0000 | [0.0000, 0.0000] |
| 94_levy_v2_flood_none | stage4:94_levy_on_flood_none | unmet | 5 | 0.0000 | [0.0000, 0.0000] |
| 94_levy_v2_flood_none | stage4:94_levy_on_flood_none | mean_distance_per_traveler | 5 | 6.0008 | [5.9872, 6.0145] |

## Audit outputs

`stage6_runs.csv` contains paired run metrics, runtime, memory, and both validation results. `stage6_levy_groups.csv` preserves worker/student outcomes. `stage6_unmet_reasons.csv` audits suppressed and partially fulfilled demand. Scenario estimates and paired effects are in the two statistics tables and the cross-version comparison table.

Raw run directories remain under `output_logs/popular_times_v2_stage6/` and are resumable with `python3 misc_scripts/run_popular_times_v2_stage6.py`. High-volume demand, movement, and OD CSVs are gzip-compressed after validation.

## Gate 6 boundary

The complete Stage 6 matrix is ready for Gate 6 review. No prior result was replaced or deleted.
