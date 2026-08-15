# Popular Times V2 Stage 6 Results

This directory is the portable Gate 6 evidence package for the completed
flood-aware commuting matrix. All ten 13- and 94-region scenario families use
matched seeds 0–4, giving 50 validated domain runs of 56 daily cycles.

## Contents

- `REPORT.md`: methods, scenario results, contrasts, and Gate 6 status.
- `stage6_runs.csv`: run-level outcomes and validation status.
- `stage6_scenario_statistics.csv`: five-seed scenario estimates.
- `stage6_baseline_effects.csv`: paired flood-minus-reference effects.
- `stage6_cross_version_effects.csv`: comparisons with Stage 4 and Stage 5.
- `stage6_levy_groups.csv`: worker and student commute outcomes.
- `stage6_unmet_reasons.csv`: audited reasons for unmet commute demand.

Raw run folders remain outside Git under
`output_logs/popular_times_v2_stage6/`. Resume the domain matrix with:

```powershell
.\.venv\Scripts\python.exe .\misc_scripts\run_popular_times_v2_stage6.py
```

The separate controlled performance matrix uses up to four concurrent workers
and is managed by `misc_scripts/run_quantitative_performance.py`.
