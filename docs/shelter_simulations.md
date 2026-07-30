# Shelter simulations

The dedicated shelter workflow uses the current `LodusSimulation` and
`ActionPlugin` lifecycle. It does not use or modify `sector_simulation.py`.

## Current data

The refactored Porto Alegre inputs contain 94 regions, 598 base points of
interest, and 1,409,464 simulated people.

| Input | Exposure or shelter state |
|---|---:|
| Affected neighborhoods | 31 regions |
| Original flooded census sectors | 385 sectors; 160,542 people |
| 5.30 m flooded census sectors | 438 sectors; 186,522 people |
| Shelter v1 after configured imputation | capacity 10,803; occupancy 8,062 |
| Shelter v2 | capacity 14,958; occupancy 12,224 |
| Shelter v3 | 104 shelters; capacity 12,519; occupancy 10,963 |

The census tables contain 2,649 sector identifiers. The bundled geometry
matches 2,557 of them, leaving 92 unmatched identifiers. This is written to
the shelter input audit and displayed on the exposure map.

Region matching is deterministic: normalized exact matching runs first, then
the versioned `porto-alegre-v1` alias table. Unknown region names stop a run.
Known variants include `PASSO DA AREIA`, `Jardim Ypu`, and `Rio Banco`.

Mapped exposure is capped by the available home population independently in
each region. The compatibility configurations therefore select 126,466 people
from the original census request (140-person shortfall) and 182,936 people
from the 5.30 m request (3,586-person shortfall). Shortfalls are not moved to
another region.

## Compatibility runs

Run the established configurations in this order:

1. `initial_test`
2. `load_shelters_test`
3. `census_areas_test`
4. `census_shelters_v2_test`
5. `census_5m30_shelters_v3_test`
6. `census_5m30_shelters_v3_daily_1%_test`
7. `census_5m30_shelters_v3_daily_1%_reallocate_test`

For a single deterministic run:

```bash
./.venv/bin/python shelter_simulator.py \
  --e shelter_tests/initial_test \
  --n shelter-initial-seed0 \
  --seed 0
```

Use `--no-shelter-png` when only HTML plots are needed. Each run writes
`output.txt`, `run_metadata.json`, data tables under `data_frames/`, HTML
plots under `html_plots/shelter/`, and optional PNGs under
`figures/shelter/`.

To run or resume all compatibility configurations:

```bash
./.venv/bin/python shelter_experiments.py \
  --catalog compatibility \
  --seeds 0
```

Batch runs are staged in `output_logs/shelter_batch/` and moved after
completion to `results/shelter/<scenario>/seed_<seed>/`. The batch summary is
written to `results/shelter/summary.csv`. Direct `shelter_simulator.py` runs
continue to write to `output_logs/<run-name>/`.

The daily routines move at step 7, admit at step 8, reallocate once globally
at step 9, and admit reallocated people at step 10.

## Logged outputs

`ShelterLogger` writes aggregated records:

- `shelter_events.csv`: selection, requests, arrivals, admissions, denials,
  reallocations, and departures.
- `shelter_step.csv`: status populations, demand, waitlist, capacity,
  utilization, protection, and conservation.
- `shelter_node_step.csv`: capacity, occupancy, queues, arrivals, admissions,
  denials, and reallocations by shelter.
- `shelter_region_step.csv`: exposure, unresolved demand, protected
  population, rates, and travel distance by population origin.
- `shelter_cycle.csv`: daily outcomes, waiting-person-steps, peak queues,
  constrained steps, and distance summaries.
- `shelter_origin_shelter.csv` and `shelter_locations.csv`: geographic flows
  and coordinates.
- `shelter_input_audit.csv`: aliases, dropped or disabled shelters,
  imputation, shortfalls, and spatial coverage.
- `shelter_group_step.csv`: sparse age- and occupation-stratified status
  outcomes.

The generated plots cover the status/capacity dashboard, daily outcomes,
occupancy heatmap, constrained shelters, Sankey and origin-destination
heatmaps, geographic flows, flood sectors, distance, demographic equity, and
input quality.

## Research catalog

The research catalog runs for 14 days and includes reference runs with and
without reallocation, fixed-initial and remaining-demand evacuation,
0.5%–5% daily response rates, 25%–100% exposure, 0.5x–15x capacity,
empty/half/observed occupancy, 500–3,000 m Levy scales, and largest/top-10%/
regional shelter failures with and without reallocation.

Screen with seeds 0–4:

```bash
./.venv/bin/python shelter_experiments.py \
  --catalog research \
  --seeds 0-4
```

Run confirmed paired comparisons with seeds 0–29:

```bash
./.venv/bin/python shelter_experiments.py \
  --catalog research \
  --confirmed
```

Both commands resume completed run directories. Use `--scenario PATTERN` to
select a subset and `--jobs N` to control parallel runs.

Analyze the resulting batch with:

```bash
./.venv/bin/python shelter_analysis.py \
  --input results/shelter/summary.csv
```

Analysis output is written to `results/shelter/analysis/`.

The analysis reports coverage, unresolved demand, peak waitlist,
waiting-person-steps, utilization, mean/P95 distance, equity gaps, runtime,
memory, bootstrap confidence intervals, and paired-seed differences.

Nearest and capacity-aware destination selection, demographic admission
priority, dynamic water/dependency closures, return/recovery, and infection
under crowding remain explicit follow-on policy extensions. Static closures,
capacity scaling, and reallocation are available in the current catalog.
