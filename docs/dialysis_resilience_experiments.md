# Dialysis resilience experiments

This experiment package implements the K00–K11 core catalog and the
capacity-ratio sensitivity catalog. Configurations inherit from
`experiments/dialysis_core/ReducedBase.json` or `CompleteBase.json`; the
resolved configuration is copied into every run's `run_metadata.json`.

## Run the catalog

From a clean checkout with the virtual environment installed:

```bash
PYTHONPATH=. .venv/bin/pytest -q Tests tests
.venv/bin/python dialysis_experiments.py --catalog core --seeds 0-29
.venv/bin/python dialysis_analysis.py
```

Use `--catalog demand` for the 0.25, 0.50, approximately 0.90, 1.00, and
1.25 demand-to-capacity sweeps in both environments. A quick deterministic
check can be run with:

```bash
.venv/bin/python dialysis_experiments.py \
  --scenarios dialysis_core/K00_ReducedReference \
  --seeds 0
```

Runs are stored at `results/dialysis/<scenario-id>/seed_<seed>/`. Completed
runs are skipped. A partial run is preserved with a timestamp before it is
retried. `summary.csv` is rebuilt from all completed runs, so resuming a
subset does not discard earlier results.

`dialysis_analysis.py` writes:

- `analysis/scenario_summary.csv`, including bootstrap confidence intervals;
- `analysis/paired_comparisons.csv`, using matched seeds;
- `analysis/redistribution.csv`, reporting paired origin-clinic flow changes;
- HTML plots for coverage, due-wait exposure, disabled clinic-hours, and
  runtime.

## Core scenarios

| ID | Behavior |
|---|---|
| K00 | Reduced 120-patient reference |
| K01 | Reduced moderate-demand control |
| K02 | ETA Moinhos outage without recovery |
| K03 | ETA Moinhos outage with four-hour recovery |
| K04 | Historical flood applied directly to clinics |
| K05 | Synthetic 10.1 m flood applied only to ETAs |
| K06 | Scheduled Moinhos outage plus 9.3 m Menino flood |
| K07 | Reduced above-capacity demand |
| K08 | Controlled high-capacity clinic failure |
| K09 | Capacity-matched low-capacity clinic failures |
| K10 | Complete-environment moderate-demand control |
| K11 | Complete-environment combined disruption |

All controlled disruptions begin at simulation step 78: day 3 at 06:00.
The topology comparison uses one shared schedule file so the failed
high-capacity clinic and the four low-capacity clinics each remove 128
daily slots.

## Availability semantics

Nodes maintain independent disable blockers. The currently used causes are
`manual`, `off_cycle`, `flood`, and `dependency`. Enabling a node removes
only the matching blocker. Dependency blockers are recalculated after every
state action, and a node is usable only when no blockers remain.

Off-cycle start actions execute before water and dialysis updates. End
actions execute afterward. Rising water adds `flood`; falling water removes
it. Missing node water thresholds mean non-vulnerable. Flood configurations
can restrict `target_node_types` and `target_regions`.

Already-admitted dialysis patients continue to complete one step later if
their clinic becomes disabled. This is an explicit preserved model rule.

## Metric definitions

- `Due Demand` in `dialysis_cycle.csv` is the number of newly due treatment
  sessions and does not double-count waiting patients.
- `Due-Wait Patient-Hours` is the sum of due patients still waiting after
  each hourly step.
- `Admission Delay Steps` is the number of hours from the start of the due
  day to admission.
- “Untreated” is represented by overdue demand at the experiment horizon;
  the model does not permanently reject patients.
- Redistribution is calculated as a paired change in aggregate
  origin-clinic flows. It is not a patient-level reassignment count.

State changes and their causes are written to
`node_state_transitions.csv`; the water series is written to
`water_level_step.csv`.

## Adding a scenario

Create a small JSON file under `experiments/`:

```json
{
  "extends": "dialysis_core/K01_ReducedModerate",
  "dialysis_plugin": {
    "max_patients_per_node": 1
  }
}
```

Nested objects are merged recursively, while scalar and list values replace
their inherited values. Run the new experiment by passing its path relative
to `experiments/`, without `.json`, to `--scenarios`.
