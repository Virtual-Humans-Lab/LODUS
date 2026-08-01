# Popular Times V2 Stage 4 Results

This directory is the portable Gate 4 evidence package for the completed 130-run
core production matrix. All 130 simulations ran for 56 daily cycles and passed the
full automated invariant suite.

## Contents

- `REPORT.md`: methodology, scenario estimates, 95% intervals, contrasts, and the
  Gate 4 status.
- `production_runs.csv`: run-level metrics, runtime, memory, validation, and commit
  provenance.
- `production_poi_type.csv`: run metrics split by POI type.
- `production_region.csv`: destination-region demand and occupancy aggregates.
- `production_region_od.csv`: Popular Times region-to-region flows.
- `production_scenario_statistics.csv`: deterministic estimates and stochastic
  means with 95% intervals.
- `production_effects.csv`: Levy, flood, flood-interaction, and Levy-by-flood
  contrasts.
- `plots/`: portable comparison figures.

## Raw artifacts and regeneration

The losslessly compressed raw run directories occupy approximately 14 GiB and are
intentionally excluded from Git. On the execution machine they are stored at:

`output_logs/popular_times_v2_stage4_production/`

The production runner is resumable. Recreate or resume the matrix with:

```bash
MPLCONFIGDIR=/tmp/lodus-matplotlib .venv/bin/python \
  misc_scripts/run_popular_times_v2_production.py --workers 4
```

Regenerate the aggregate package from existing run folders without launching new
simulations with:

```bash
MPLCONFIGDIR=/tmp/lodus-matplotlib .venv/bin/python \
  misc_scripts/run_popular_times_v2_production.py --skip-runs
```

Stage 5 rerouting adaptation is not included in this package.
