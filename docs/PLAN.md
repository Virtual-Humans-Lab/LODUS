# Popular Times Mobility Study

## Summary

Create `PopularTimesV2Plugin` while preserving the existing plugin for compatibility. V2 will model weekly hourly demand, one-hour visits, flood-aware node availability, Levy interaction, and auditable mobility outcomes across the 13- and 94-region environments.

Implementation proceeds through five approval gates. Work stops after every stage until explicitly approved.

## Stage 1 — V2 Foundation

- Keep the existing `PopularTimesPlugin` and `popular_times` action unchanged.
- Add `PopularTimesV2Plugin` with action `popular_times_v2` and configuration key `popular_times_v2_plugin`.
- Calculate hourly demand as:
  `effective home population × weekly visit rate × normalized weekly profile`.
- Default weekly rates:
  - Marketplace: `1.0`
  - Restaurant: `1.0`
  - Pharmacy: `0.25`
- Use the fixed seed-0 profiles across all simulations.
- Support two demand bases:
  - `initial_population`, the default.
  - `multiplier_csv`, converting legacy multipliers to effective population with a configurable scale, defaulting to `700`.
- Source visitors from enabled `home` nodes across all regions, weighted by inverse distance × available matching population and capped by availability.
- Tag visiting blobs with visit ID, source/prior node, paired home, POI type, and expiry step.
- Release visitors after exactly one hour:
  - Default: prior source node.
  - Optional: POI’s paired home.
  - If unavailable, try the permanent home and then the nearest enabled home, logging the displacement.
- Suppress demand from disabled POIs and exclude disabled homes from sourcing.
- Add opt-in Levy settings that reject disabled acting nodes and disabled destinations; defaults remain backward compatible.
- Apply the approved small core change: fully consume regular actions before generating and consuming end-of-step actions.
  - Water updates first.
  - Expired visits are released.
  - Regular Levy actions execute.
  - End-of-step Popular Times requests execute.
- Add regression tests proving the phase-order change does not alter unrelated single-phase simulations.

**Gate 1:** Present unit tests, lifecycle examples, demand calculations, and ordering evidence. Stop for approval.

## Stage 2 — Environment and Routine Preparation

- Use `Environment-13-EnumArea.json` unchanged as the flood-capable 13-region environment.
- Generate a derived 94-region Popular Times environment without altering the source:
  - Preserve all 2,711 home/work/school nodes.
  - Add one pharmacy, marketplace, and restaurant for every home suffix.
  - Place new POIs using deterministic, type-specific offset vectors sampled from the observed 13-region layout.
  - Do not assign synthetic water thresholds or run flood scenarios on this environment.
- Generate a cleaned 94-region population input excluding:
  - `Chapéu do Sol//home_9` — 1,023 people.
  - `Hípica//home_40` — 408 people.
- Preserve the original population file and produce an audit showing the 1,431-person, approximately 0.11%, exclusion.
- Validate unique suffix pairing, coordinates, population references, POI counts, and total population.
- Add an end-of-step Popular Times routine covering all 24 hours; closed hours naturally request zero.
- Provide separate no-Levy and Levy routine/configuration families.
- Configure 13-region flooding targets as:
  - Destination POIs: pharmacy, marketplace, restaurant.
  - Origin homes.
  - Both groups.
- Use the existing water series for cycles 0–55, giving eight complete weeks without extrapolation.

**Gate 2:** Present generated-data audits, environment counts, pairing validation, and sample demand schedules. Stop for approval.

## Stage 3 — Experiments, Logging, and Pilot

- Create the primary scenario matrix:
  - 13 regions: Levy off/on × flood none/POIs/homes/both = 8 scenarios.
  - 94 regions: Levy off/on without flooding = 2 scenarios.
- Run every scenario for 56 cycles of 24 hourly steps.
- Add Popular Times records for:
  - Requested, fulfilled, and unmet demand.
  - Unmet reason: disabled destination, no enabled origins, or insufficient population.
  - Source homes, travelers, distances, destination occupancy, releases, and flood reroutes.
- Combine these with existing movement, OD, population, and node-state logging.
- Produce raw CSVs, aggregate CSVs, comparison plots, and a Markdown methodology/results report.
- Normalize cross-environment metrics per capita and per requested visit.
- Run one pilot seed for each of the ten scenarios.
- Pilot acceptance criteria:
  - Global population is conserved.
  - Visits last exactly one hour.
  - No movement enters or leaves disabled nodes in enabled-only scenarios.
  - Weekly requested totals match configured rates within integer-rounding tolerance.
  - Every movement and unmet request has an auditable reason.
  - Runtime and peak memory are acceptable before production execution.

**Gate 3:** Present pilot results, invariant checks, runtime/memory estimates, and sample analysis outputs. Stop for approval.

## Stage 4 — Core Production Matrix

- Run deterministic Levy-off scenarios once:
  - Four 13-region flood conditions.
  - One 94-region no-flood condition.
- Run the Levy-on scenarios with the approved environment-specific seed counts:
  - Seeds `0–29` for four 13-region flood conditions = 120 runs.
  - Seeds `0–4` for the 94-region condition = 5 runs.
- Reuse matching Levy seeds across flood variants for paired comparisons.
- Produce 130 production runs in total.
- Report:
  - Demand fulfillment and flood-related suppression.
  - Trips, travelers, distance, OD flows, and POI occupancy.
  - Differences caused by Levy, each flood target, their interaction, and geographic aggregation.
  - Means and 95% intervals for stochastic scenarios, noting the five-seed
    limitation for the 94-region interval.
  - Deterministic values without artificial confidence intervals.

**Gate 4:** Present and review the complete core-matrix results. Stop before adaptation work.

## Stage 5 — Flood Adaptation Sensitivity

- Add rerouting behavior behind an explicit configuration flag.
- When a destination POI is disabled:
  - Redirect its original demand to the nearest enabled POI of the same type.
  - Retain demand scaling from the original POI’s paired home.
  - Record displacement distance, receiving-node load, and remaining unmet demand.
- Run two 13-region, homes-and-POIs-flooded scenarios:
  - Levy off: one deterministic run.
  - Levy on: 30 seeded runs.
- Compare these 31 runs with their demand-suppression counterparts and add the findings to the report.

**Gate 5:** Present adaptation results and final validation for approval.

## Stage 6 — Levy Walk V2

- Preserve the legacy Levy plugin, routines, experiment configurations, runners,
  and Stage 4/5 results without behavioral changes.
- Add `LevyWalkV2Plugin` and `levy_walk_v2` with exact cycle-level worker and
  student attendance allocated deterministically across homes and hours.
- Normalize the historical worker profile to one cycle and use the combined
  student profile at 08:00, 13:00, and 19:00.
- Split demand into packets of at most 50, including every final partial packet.
- Make commute origins, destinations, anticipated destination flooding, returns,
  temporary homes, and repatriation flood-aware and auditable.
- Run five 13-region families with paired seeds 0–29: no flooding, destination
  flooding including work/school, home flooding, all-node flooding, and all-node
  flooding with Popular Times POI rerouting.
- Validate both mobility models independently and compare each flood condition to
  the new no-flood baseline with paired 95% t intervals.
- Treat comparisons with matching Stage 4/5 runs as combined model revisions,
  because work/school flood exposure and commute behavior both change.
- Keep raw outputs outside Git and preserve the portable report, aggregates, and
  plots under `docs/results/popular_times_v2_stage6/`.

**Gate 6:** Present all 150 validated runs and stop for review. Do not replace or
delete Stage 4/5 artifacts.

## Interfaces and Compatibility

- New action: `popular_times_v2`.
- New action: `levy_walk_v2`; legacy `levy_walk` remains unchanged.
- New configuration: `levy_walk_v2_plugin`.
- New configuration: `popular_times_v2_plugin`.
- Return policy: `prior_node` by default; `paired_home` optional.
- Demand basis: `initial_population` by default; legacy multiplier CSV optional.
- Levy enabled-state checks are opt-in so existing experiments remain unchanged.
- Existing Popular Times, Gather Population, environment structures, and experiment files remain compatible.
- No environment-core changes are planned.
- The only approved simulator-core change is sequential regular/end-of-step consumption.

## Assumptions

- All population categories are eligible unless an action supplies a narrower population template.
- POIs have no explicit capacity limit; availability constrains origins only.
- Fixed hourly profiles isolate behavioral and flood effects from demand-sampling noise.
- Flooded POI demand is suppressed in the core matrix and rerouted only in Stage 5.
- The 94-region environment is used only for non-flood comparisons because citywide flood exposure data is unavailable.
