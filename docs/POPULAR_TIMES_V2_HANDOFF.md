# Popular Times V2 Handoff

## Repository state

- Branch: `refactoring`
- Stage 4 implementation commit: `2cae9365151e95c6d28fc08ea6c38510b38dc902`.
- Gate 4 was approved and Stage 5 is complete.
- Work is intentionally stopped at Gate 5 for review.
- The full approved study specification is in `docs/PLAN.md`.

Stages 1–4 are committed on the branch. Portable Stage 4 and Stage 5 evidence is
stored under `docs/results/`. The raw run trees remain under ignored `output_logs/`
on the machine that executed the matrices.

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

## Historical Stage 3 resume point

The following was the resume point before Stage 4 began:

1. Check out the committed `refactoring` branch.
2. Install `requirements.txt` dependencies if needed.
3. Run the verification commands above.
4. Read `docs/PLAN.md` and this handoff.
5. Confirm whether Stage 4's 94-region production runs remain at 56 cycles or should
   also use a shorter horizon.
6. Implement a resumable/parallel production runner for the originally planned
   155-run Stage 4 matrix; this was subsequently revised to 130 runs in the Stage 4
   continuation below.
7. Stop again at Gate 4 before implementing Stage 5 rerouting adaptation.

## Stage 4 continuation (2026-08-01)

Stage 4 has now started on the newer machine. The pilot scenarios remain unchanged:
the two 94-region pilot configurations still run for five cycles. Separate production
configurations under `experiments/popular_times_v2/production/` explicitly restore
all ten scenario families, including both 94-region families, to the approved 56
cycles x 24 hours.

`misc_scripts/run_popular_times_v2_production.py` now provides:

- the revised 130-run matrix (five deterministic Levy-off runs, 120 13-region
  Levy-on runs using seeds 0–29, and five 94-region Levy-on runs using seeds 0–4);
- matched Levy seeds across the four 13-region flood variants;
- resumability based on matching experiment, seed, 56-cycle metadata, and invariant
  artifacts;
- configurable process parallelism and seed/scenario batching;
- a continuously updated production manifest;
- lossless `.csv.gz` archival of the largest raw files after each validated run;
- run, POI-type, destination-region, and region-OD aggregates;
- paired Levy, flood, flood-interaction, and Levy-by-flood contrasts;
- means and 95% t intervals for stochastic scenarios, with no artificial intervals
  on deterministic values;
- plots and an interim/final `REPORT.md` that only declares Gate 4 ready when all
  130 runs exist and pass validation.

All 130 production runs completed and passed every invariant. The final losslessly
compressed raw run tree occupies about 14 GiB. It remains under ignored
`output_logs/` and will not travel with Git.

Run or resume the complete matrix conservatively with:

```bash
MPLCONFIGDIR=/tmp/lodus-matplotlib .venv/bin/python \
  misc_scripts/run_popular_times_v2_production.py --workers 4
```

The machine observed during continuation has 12 logical CPUs, 15 GiB RAM, about
6.8 GiB available memory, and 240 GiB free disk. Four workers leave ample memory
headroom relative to the Stage 3 peak measurements. For explicit batches, combine
`--only` with `--seeds-13` or `--seeds-94`; completed runs are skipped automatically.
Rebuild analysis without launching simulations with `--skip-runs`.

The targeted Stage 1–4 suite currently passes 29 tests. Stage 5 has not started.

## Gate 4 findings and preservation

The portable report, aggregate CSVs, regional and region-OD outputs, and plots are
tracked under `docs/results/popular_times_v2_stage4/`. The package is approximately
3 MiB and contains enough evidence to review the matrix without the ignored raw
logs.

Principal findings:

- POI flooding suppressed 3.51% of requested visits, reducing fulfillment from
  100% to 96.49%.
- Home-only flooding preserved fulfillment but increased mean sourcing distance.
- Levy changed sourcing distance without changing fulfillment or occupancy per
  requested visit.
- The 94-region Levy interval uses five seeds and must be interpreted as less
  precise than the 30-seed 13-region intervals.

This was the Gate 4 review boundary. Stage 5 began only after Gate 4 was explicitly
approved.

## Stage 5 completion (2026-08-01)

Gate 4 was explicitly approved before Stage 5 began. Stage 5 adds destination
adaptation behind `popular_times_v2_plugin.reroute_disabled_destinations`, which
defaults to `false`. When enabled, a disabled POI—or one known to flood before the
one-hour visit expires—redirects its original demand to the nearest currently safe
POI of the same type. Candidate selection spans all regions and resolves distance
ties by complete node name. Demand continues to use the original POI's paired home.

The logger now records the requested and receiving POIs, reroute reason, POI
displacement, receiving load, fulfilled rerouted demand, and remaining unmet demand.
It also validates that every receiving POI differs from the requested POI, has the
same type, and is enabled when movement occurs.

The 31-run matrix contains one deterministic Levy-off run and Levy-on seeds 0–29,
all using the 13-region homes-and-POIs flood scenario for 56 cycles x 24 hours. All
31 runs completed and passed every invariant.

Key results:

- All 83,445 visits suppressed by POI flooding in the matching Stage 4 scenario
  were rerouted successfully in every Stage 5 run.
- Fulfillment increased from 96.49% to 100%, with zero remaining rerouted unmet
  demand.
- Mean POI-to-POI displacement was 297.89 metres per rerouted traveler.
- The maximum observed receiving-POI load was 92 Popular Times travelers.
- Relative to Stage 4 suppression, distance per requested visit increased by 5.04
  metres without Levy and by a mean 4.84 metres with Levy.
- Population conservation, one-hour visits, weekly demand, enabled-node movement,
  unmet-reason, and rerouted-destination checks all passed.

The losslessly compressed Stage 5 raw tree occupies approximately 3 GiB under
`output_logs/popular_times_v2_stage5/`. The portable report, aggregate CSVs,
receiving-POI flows, paired effects, and plots are under
`docs/results/popular_times_v2_stage5/`.

The complete adaptation matrix is ready for Gate 5 review. No further adaptation
work is approved beyond this boundary.

## Stage 6 implementation and execution (2026-08-01)

Gate 5 was followed by an explicitly approved Levy Walk V2 stage. The new
`LevyWalkV2Plugin` and `levy_walk_v2` action are isolated from the legacy Levy
implementation. Legacy routines, packet-flooring behavior, configurations,
runners, and Stage 4/5 artifacts remain unchanged.

Levy V2 calculates an exact global attendance target every cycle from original
worker/student population, then allocates it deterministically to homes and
normalized hourly profiles by largest remainders. Workers use attendance rate
`1.0` and an eight-hour stay; students use rate `1.0`, the combined
08:00/13:00/19:00 profile, and a four-hour stay. Outbound demand uses packets of
at most 50 and retains the last partial packet.

The V2 lifecycle suppresses disabled origins, disabled or imminently flooded
destinations, and unavailable population with explicit reasons. Optional nearest
enabled same-type destination routing is available across regions with complete
node-name tie breaking, although production work/school demand uses suppression.
Returns preserve original-home provenance, use the nearest enabled home when
necessary, retry blocked returns, and automatically repatriate temporary residents
when their original home reopens.

The resumable runner is:

```bash
.venv/bin/python misc_scripts/run_popular_times_v2_stage6.py --workers 4
```

Use `--smoke` for the five seed-0 scenarios or `--skip-runs` to rebuild analysis.
The full matrix has five 13-region families x seeds 0–29 = 150 runs, each using 56
cycles. Both `popular_times_validation.json` and `levy_v2_validation.json` must
pass before a run is considered complete. Large demand, movement, and OD files are
gzip-compressed after validation. Raw outputs stay under ignored
`output_logs/popular_times_v2_stage6/`; portable Gate 6 outputs are copied to
`docs/results/popular_times_v2_stage6/` after execution.

Stage 6 stops at Gate 6. Stage 4 and Stage 5 outputs must not be removed or
replaced.
