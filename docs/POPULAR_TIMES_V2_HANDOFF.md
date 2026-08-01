# Popular Times V2 Handoff

## Repository state

- Branch: `refactoring`
- HEAD when this handoff was written: `27a3f8196036e38c6c3135e995dd7b354f0e2620`
- Work is intentionally stopped after Gate 3.
- Stage 4 and Stage 5 have not started.
- The full approved study specification is in `docs/PLAN.md`.
- No Stage 3 changes have been committed by Codex.

The Stage 1 and Stage 2 implementation is already part of the branch baseline. The
working tree contains the uncommitted Stage 3 implementation listed below. Preserve
unrelated user changes when committing.

## Decisions carried forward

- Preserve the original `PopularTimesPlugin` and `popular_times` action.
- Use `PopularTimesV2Plugin`, action `popular_times_v2`, and configuration key
  `popular_times_v2_plugin` for this study.
- Demand uses fixed seven-day POI-type profiles, per-type weekly visit rates, and
  one-hour visits.
- Default weekly visit rates remain marketplace `1.0`, restaurant `1.0`, and
  pharmacy `0.25`.
- The default demand basis remains `initial_population`; legacy multiplier CSVs
  remain optional.
- Source homes are selected deterministically using inverse-distance x matching
  population priority, with all homes considered when constructing the compact
  candidate set and live availability used as a cap.
- Popular Times requests execute at end of step, after water updates, expired-visit
  releases, and regular Levy actions.
- Disabled homes cannot source Popular Times visits. Disabled POIs cannot receive
  visits.
- In POI-flood scenarios, a request is also suppressed when known water data shows
  that the destination will become disabled before the one-hour visit expires. This
  keeps the literal invariant that no movement enters or leaves disabled nodes.
- Levy and send-back enabled-state checks are opt-in and enabled by the study
  configurations, preserving backward compatibility for older experiments.
- No additional simulator-core changes were made during Stage 3.

## Stage 3 implementation

### Logging and validation

`plugins/loggers/popular_times_v2_logger.py` incrementally writes:

- `popular_times_demand.csv`
- `popular_times_visits.csv`
- `popular_times_disabled_movement.csv`
- `popular_times_step_type.csv`
- `popular_times_summary.csv`
- `popular_times_od.csv`
- `popular_times_validation.json`

It records demand, fulfillment, unmet reasons, source homes, travelers, distances,
destination occupancy, releases, reroutes, OD flows, and invariant results. Raw rows
are streamed so the 94-region simulations do not retain millions of records in RAM.

The existing enumeration-area OD logger was changed to stream step and cycle output
incrementally. The movement displacement logger now calculates only the requested
origin/destination distance instead of caching a graph-wide distance table per source.

### Performance changes

- Popular Times sourcing uses a compact deterministic weighted candidate set and
  avoids creating many one-person blobs.
- Levy distance caches are target-type-specific and store compact NumPy node-ID
  arrays rather than graph-wide Python tuple dictionaries.
- `Routine-POA-EnumArea-PopularTimes.json` is a derived copy of the existing routine
  with every global Levy action filtered to `home` nodes before expansion.
- The source routine and source environments remain unchanged.

### Scenario matrix

The ten pilot configurations are under
`experiments/popular_times_v2/scenarios/`:

- 13 regions: Levy off/on x flood none/POIs/homes/both.
- 94 regions: Levy off/on, no flooding.
- Seed `0` is used throughout.
- The eight 13-region pilots use 56 cycles x 24 hours.
- At the user's request, the two 94-region **pilot** configurations use only
  5 cycles x 24 hours.
- This five-cycle change applies only to the pilots. Stage 4 still specifies
  56-cycle 94-region production runs unless the user changes that decision.

## Gate 3 pilot evidence

All ten pilot scenarios passed their applicable automated checks.

| Scenario | Cycles | Fulfillment | Runtime (s) | Peak memory (MiB) |
|---|---:|---:|---:|---:|
| 13, Levy off, no flood | 56 | 1.0000 | 249.57 | 212.8 |
| 13, Levy off, POI flood | 56 | 0.9649 | 231.88 | 211.2 |
| 13, Levy off, home flood | 56 | 1.0000 | 231.97 | 270.0 |
| 13, Levy off, both flooded | 56 | 0.9649 | 220.40 | 239.8 |
| 13, Levy on, no flood | 56 | 1.0000 | 291.80 | 244.9 |
| 13, Levy on, POI flood | 56 | 0.9649 | 270.12 | 242.7 |
| 13, Levy on, home flood | 56 | 1.0000 | 279.44 | 302.3 |
| 13, Levy on, both flooded | 56 | 0.9649 | 262.69 | 271.5 |
| 94, Levy off, no flood | 5 | 1.0000 | 213.12 | 314.5 |
| 94, Levy on, no flood | 5 | 1.0000 | 330.16 | 448.9 |

Key observations:

- Every run conserved population and recorded zero movement to or from disabled
  nodes.
- All completed visits lasted exactly one hour and all unmet requests had a reason.
- Closed-hour and profile-peak checks passed.
- Weekly demand equality passed for all eight complete weeks in every 13-region run.
- Weekly equality is explicitly marked not applicable for the five-day 94-region
  pilots; their partial-profile checks still passed.
- POI flooding suppressed 83,445 of 2,374,616 requested visits, for 96.4860%
  fulfillment. Home-only flooding did not suppress demand in seed 0 but changed
  sourcing distance.
- Linear estimates for a 56-cycle 94-region run are about 39.8 minutes without Levy
  and 61.6 minutes with Levy. Stage 4's 30 seeded 94-region Levy runs therefore need
  a deliberate batch/parallelization decision.

## Pilot artifacts and portability

The pilot report, CSVs, plots, and per-run raw logs are under:

`output_logs/popular_times_v2_stage3_pilot/`

`output_logs` is ignored by Git. Those files will **not** appear on another machine
after cloning or pulling the commit. The table above preserves the essential Gate 3
results. To preserve every raw artifact, copy or archive that directory separately.

The report can be regenerated from existing run folders with:

```powershell
python misc_scripts\run_popular_times_v2_pilot.py --skip-runs
```

The derived Levy routine can be regenerated with:

```powershell
python misc_scripts\generate_popular_times_v2_levy_routine.py
```

## Verification

The final targeted regression command passed 24 tests:

```powershell
python -m unittest Tests.popular_times_v2_stage3_test Tests.popular_times_v2_stage2_test Tests.popular_times_v2_plugin_test -v
python -m compileall -q core plugins misc_scripts Tests
git diff --check
```

Only line-ending warnings were emitted by `git diff --check`.

## Uncommitted Stage 3 files

Modified:

- `Tests/popular_times_v2_plugin_test.py`
- `experiments/popular_times_v2/Base13.json`
- `experiments/popular_times_v2/Base94.json`
- `experiments/popular_times_v2/FloodBoth13.json`
- `experiments/popular_times_v2/FloodPOIs13.json`
- `experiments/popular_times_v2/Levy13.json`
- `experiments/popular_times_v2/Levy94.json`
- `plugins/loggers/enumeration_area_od_matrix_logger.py`
- `plugins/loggers/movement_displacement_logger.py`
- `plugins/time_actions/levy_walk_plugin.py`
- `plugins/time_actions/popular_times_v2_plugin.py`
- `plugins/time_actions/send_population_back_plugin.py`
- `sector_simulation.py`

Added:

- `Tests/popular_times_v2_stage3_test.py`
- `data_input/enumeration_area/Routine-POA-EnumArea-PopularTimes.json`
- `experiments/popular_times_v2/scenarios/*.json`
- `misc_scripts/generate_popular_times_v2_levy_routine.py`
- `misc_scripts/run_popular_times_v2_pilot.py`
- `plugins/loggers/popular_times_v2_logger.py`
- `docs/POPULAR_TIMES_V2_HANDOFF.md`

`docs/PLAN.md` is also currently untracked and contains the original approved plan.
Review and include it deliberately when committing.

## Resume point

Do not start Stage 4 without fresh approval. On the next machine:

1. Check out the committed `refactoring` branch.
2. Install `requirements.txt` dependencies if needed.
3. Run the verification commands above.
4. Read `docs/PLAN.md` and this handoff.
5. Confirm whether Stage 4's 94-region production runs remain at 56 cycles or should
   also use a shorter horizon.
6. Implement a resumable/parallel production runner for the 155-run Stage 4 matrix;
   the current runner is a seed-0 pilot runner only.
7. Stop again at Gate 4 before implementing Stage 5 rerouting adaptation.

