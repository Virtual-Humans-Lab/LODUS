# Popular Times V2 Stage 5 Results

This directory is the portable Gate 5 evidence package for the completed flood
adaptation sensitivity. All 12 simulations ran for 56 daily cycles and passed every
legacy and rerouting-specific invariant.

## Method and findings

Disabled or imminently flooded POIs redirect their original demand to the nearest
safe POI of the same type. Demand remains scaled by the original POI's paired home;
receiving POIs have no capacity limit.

- In the 13-region comparison, all 83,445 visits suppressed in the matching
  Stage 4 scenario were recovered; the 94-region comparison likewise recovered
  all suppressed demand.
- Fulfillment increased from 96.49% to 100%.
- Remaining rerouted unmet demand was zero.
- Mean POI displacement was 297.89 metres per rerouted traveler.
- Peak observed receiving load was 92 travelers.

## Contents

- `REPORT.md`: methodology, results, 95% intervals, paired Stage 4 comparisons,
  and Gate 5 status.
- `stage5_runs.csv`: run-level mobility, rerouting, resource, and validation data.
- `stage5_poi_type.csv`: metrics by POI type.
- `stage5_receivers.csv`: requested-to-receiving POI flows and receiving loads.
- `stage5_scenario_statistics.csv`: deterministic and stochastic estimates.
- `stage5_adaptation_effects.csv`: paired rerouting-minus-suppression effects.
- `plots/`: fulfillment-recovery and reroute-displacement figures.

## Raw artifacts and regeneration

The approximately 3 GiB losslessly compressed raw run tree is intentionally excluded
from Git. On the execution machine it is stored at:

`output_logs/popular_times_v2_stage5/`

Recreate or resume the matrix with:

```bash
MPLCONFIGDIR=/tmp/lodus-matplotlib .venv/bin/python \
  misc_scripts/run_popular_times_v2_stage5.py --workers 4
```

Regenerate analysis from existing run folders without launching simulations with:

```bash
MPLCONFIGDIR=/tmp/lodus-matplotlib .venv/bin/python \
  misc_scripts/run_popular_times_v2_stage5.py --skip-runs
```

This package is the Gate 5 boundary; it does not authorize further adaptation work.
