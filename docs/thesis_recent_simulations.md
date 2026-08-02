# Recent Simulation Experiments

This section summarizes the most recent simulation experiments conducted with
LODUS. The experiments examine the resilience of urban health services and
population mobility under capacity limitations, facility disruption, and
flooding. All models use the same graph-based representation of Porto Alegre,
in which regions contain activity or service nodes and population groups move
between nodes in discrete hourly steps. The individual experiment families add
domain-specific demand, capacity, disruption, and adaptation rules to this
common simulation structure.

## Overview of the experiment batches

| Experiment batch | Experimental design | Runs | Main outcome |
|---|---|---:|---|
| Dialysis resilience | Twelve reference, demand, clinic-failure, recovery, and flood scenarios (K00--K11), evaluated primarily with 30 matched seeds | 361 completed records, including one additional K03 run | Service remained complete under moderate demand and short disruptions, but persistent or widespread failures reduced treatment coverage to 50--71% in the most severe scenarios. |
| Inpatient care | Seven demand-and-routing scenarios under unconstrained overflow and capacity-constrained queue policies, with 30 seeds per scenario | 210 | Reference demand was almost fully served; high demand reduced queue-policy coverage to 52.1%, while distributing psychiatric demand across two facilities increased coverage to 97.1%. |
| Popular Times V2: core matrix (Stage 4) | Thirteen- and 94-region mobility models; Levy movement on/off; no flood, flooded homes, flooded points of interest (POIs), or both | 130 | Flooded POIs reduced visit fulfillment from 100% to 96.49%; flooded homes changed travel distance but did not reduce fulfillment. |
| Popular Times V2: destination adaptation (Stage 5) | Thirteen-region combined home-and-POI flood scenario, comparing suppressed visits with nearest-safe, same-type POI rerouting | 31 | All 83,445 previously suppressed visits were rerouted, restoring 100% fulfillment at a mean POI displacement of 297.89 m. |
| Popular Times V2 and Levy Walk V2 (Stage 6) | Five 13-region flood/adaptation families, each evaluated with 30 matched seeds for 56 simulated days | 150 | Commute fulfillment fell from approximately 100% without flooding to 89.15% when all node types were exposed; POI rerouting restored activity-visit fulfillment but not disrupted work and school trips. |

## Dialysis-service resilience

The dialysis experiments modeled patients with recurring treatment demand,
clinic schedules and capacities, admission delay, and travel from their region
of origin. Clinic availability was altered by scheduled outages, flooding, and
dependencies on water-treatment facilities. Twelve scenarios compared reduced
and complete city networks, moderate and above-capacity demand, isolated clinic
failures, rapid recovery, different failure topologies, and combined
disruptions. Disruptions began on the third simulated day, and scenarios were
compared using matched random seeds.

The reference and moderate-demand scenarios achieved complete treatment
coverage. A persistent outage at the Moinhos facility reduced coverage to
68.52%, whereas recovery after four hours restored it to 100%. The synthetic
water-treatment failure and the combined reduced-network disruption produced
50% coverage, while the combined disruption in the complete network produced
71.43% coverage. Failures removing equal aggregate capacity also produced
different travel patterns: the distributed failure of several smaller clinics
increased mean admission distance relative to the failure of one large clinic,
even though both maintained complete coverage.

## Inpatient-care capacity and routing

The inpatient-care model represented hospital demand as cohorts sharing an
origin, diagnosis category, payer, preferred destination, and length of stay.
Separate public (SUS) and private bed pools were enforced. The experiments
compared an unconstrained *overflow* policy, used to measure latent bed
shortages, with a *queue* policy that limited admissions to available beds and
retained unserved cohorts in a first-in, first-out queue. The batch included
reference demand, a high-demand stress test, a two-facility allocation, and a
small synthetic CID-based routing demonstration.

At reference demand, the queue model admitted 99.96% of demand and ended with
almost no waiting patients. Under high demand, coverage fell to 52.10%, the
mean final queue reached 1,336.5 patients, and mean admission delay was 2.44
steps. Allocating psychiatric demand between HEPA and a synthetic Santa Ana
capacity pool raised mean coverage to 97.08% and reduced the final queue to
77.2 patients. These results show that both total capacity and its spatial
distribution strongly affect access; however, the Santa Ana capacity and CID
routing inputs are experimental assumptions rather than observed clinical
behavior.

## Routine mobility, flooding, and destination adaptation

Popular Times V2 modeled weekly hourly visits to marketplaces, restaurants,
and pharmacies. Visit demand was derived from the population associated with
each home node and fixed weekly profiles. Travelers were selected from enabled
homes, occupied a destination for one hour, and then returned. The core matrix
combined this activity demand with Levy-based population movement and applied
the historical water-level series to homes, POIs, both groups, or neither.
Each stochastic 13-region condition used 30 matched seeds; deterministic
conditions were run once, and the larger 94-region Levy condition used five
seeds.

All 130 core runs passed the population-conservation and enabled-node movement
checks. Flooding POIs suppressed 3.51% of requested visits and reduced
fulfillment to 96.49%. Home-only flooding maintained complete fulfillment but
increased the distance required to source travelers. Activating Levy movement
changed sourcing distances but did not change visit fulfillment or POI
occupancy per requested visit.

The subsequent adaptation batch allowed demand assigned to a disabled or
imminently flooded POI to be redirected to the nearest safe POI of the same
type. Across 31 runs, all 83,445 suppressed visits were successfully rerouted,
raising fulfillment from 96.49% to 100%. The additional destination
displacement averaged 297.89 m per rerouted traveler, and the largest receiving
load was 92 travelers.

## Flood-aware commuting with Levy Walk V2

The final batch replaced the legacy Levy routine with a flood-aware commute
model while preserving the earlier results for comparison. Worker and student
attendance targets were allocated exactly across homes and hourly departure
profiles; trips were divided into population packets of at most 50. The model
recorded suppressed origins, unavailable or imminently flooded destinations,
temporary return homes, blocked returns, and later repatriation. Five scenario
families represented no flood, destination flooding, home flooding, flooding
of all node types, and all-node flooding with Popular Times rerouting.

The 150 runs passed both the Popular Times and Levy Walk V2 validation checks.
Mean commute fulfillment was approximately 100% without flooding, 93.54% with
destination flooding, 94.06% with home flooding, and 89.15% with all-node
flooding. In the all-node adaptation scenario, POI visit fulfillment returned
to 100%, while commute fulfillment remained approximately 89.05%. Thus,
destination substitution was effective for discretionary activity visits but
could not compensate for the simultaneous loss of homes, workplaces, and
schools.

## Current scope and next steps

The reported results are simulation outcomes and should be interpreted as
comparisons between modeled scenarios, not as direct forecasts of patient or
population behavior. The inpatient and dialysis analyses quantify uncertainty
with repeated seeds, while deterministic demand components naturally produce
little or no between-run variation. Future expansion of this chapter should
describe input-data provenance, parameter calibration, statistical intervals,
spatial differences, and sensitivity analyses for each experiment family.

A shelter-allocation workflow has also been implemented for the 94-region
environment, including exposure, capacity, evacuation-rate, reallocation, and
shelter-failure scenarios. Its compatibility and research catalogs are defined,
but no completed shelter batch summary is currently preserved in the repository;
therefore, no shelter outcome is reported here.

## Internal result sources

- Dialysis: `results/dialysis/analysis/scenario_summary.csv` and
  `results/dialysis/analysis/paired_comparisons.csv`.
- Inpatient care: `results/inpatient_care/analysis/report.md`.
- Popular Times Stage 4: `docs/results/popular_times_v2_stage4/REPORT.md`.
- Popular Times Stage 5: `docs/results/popular_times_v2_stage5/REPORT.md`.
- Popular Times and Levy Walk V2 Stage 6:
  `output_logs/popular_times_v2_stage6/REPORT.md`.
