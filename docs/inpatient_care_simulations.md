# Inpatient care simulations

This module reconstructs the hospital-bed experiments from the reference study
and ports their movement model to the current LODUS plugin architecture.

## Provenance

The capacity source is the LODUS-Health file
`leitos-hospitais-especialidade.csv`, described as a January 2024 CNES extract
enriched with hospital coordinates. The normalized copy contains:

- 253 hospital/specialty/bed-type rows;
- 28 hospitals in 22 Porto Alegre regions;
- 7,529 total beds, including 4,689 SUS beds.

The source checkout also contained the three configuration files used for the
reference experiments. Exact copies are kept under
`data_input/inpatient_care/provenance`; canonical demand-only versions are
used by the modern experiments. They came from LODUS-Health commit `78946ad0`:
`config-simulacao1.json`, `config-10abril20242.json`, and
`config-HAHAHA.json`.

The source region labels `Centro` and `Menino Deus` are normalized to the
current environment's `Centro Histórico` and `Menino-Deus`.

The original random seed and generated per-step admission arrays were not
preserved. Consequently, the modern runs reconstruct the configured totals
and length-of-stay process, but do not claim byte-for-byte reproduction of the
published figures or exact overload step. Seed 0 is the default reference.

Simulation 3 assigns Hospital Santa Ana a synthetic Psychiatry / Outras
Especialidades pool of 264 total and 159 SUS beds. That pool is an experiment
override and is not present in the source capacity data.

## Model

People are selected once from `home` nodes in their origin region. Cohorts are
formed from people sharing demand, CID, payer, destination, and discharge
step. A simulation step:

1. returns cohorts whose stay has ended to their original home node;
2. creates the step's new demand;
3. routes waiting cohorts and admits available quantities;
4. records events and the resulting occupancy.

`total_beds` includes SUS beds. The private pool is therefore
`total_beds - sus_beds`; the two payer pools are never shared.

With `capacity_policy: overflow`, all compatible demand is admitted and
overflow is measured. With `capacity_policy: queue`, admission is limited to
free compatible beds and the rest remains at home in a FIFO queue. A preferred
hospital is used first. If `allow_hospital_change` is true, compatible
alternatives are ranked by geographic distance.

CID-to-specialty mapping is supplied by each experiment. It is simulation
configuration, not clinical advice or embedded medical inference.

## Experiment catalog

- `inpatient_care/ReferenceDemandOverflow` and `ReferenceDemandQueue`: HEPA, 500
  Psychiatry admissions (300 SUS) and 50 Mental Health admissions (all SUS).
- `inpatient_care/HighDemandOverflow` and `HighDemandQueue`: HEPA stress test,
  2,640 Psychiatry admissions (1,590 SUS) and 150 Mental Health admissions
  (all SUS).
- `inpatient_care/TwoFacilityOverflow` and `TwoFacilityQueue`: 1,320 Psychiatry
  admissions (795 SUS) at each of HEPA and synthetic Santa Ana.
- `inpatient_care/CIDRoutingQueue`: a small, explicitly synthetic psychiatric CID
  routing demonstration using the real hospital capacities.

Run one experiment with:

```bash
python sector_simulation.py \
  --e inpatient_care/ReferenceDemandOverflow \
  --n inpatient_care/reference_demand_seed0 \
  --seed 0 \
  --no-inpatient-care-png
```

Run the catalog, or a seed range, with:

```bash
python inpatient_care_experiments.py --seeds 0
python inpatient_care_experiments.py --seeds 0-29 --jobs 4
```

The batch runner disables each run's individual plots, verifies byte-stable
specialized CSV output by repeating the first scenario/seed, and writes runs
under `results/inpatient_care`. Completed runs are skipped when the same
command is resumed.

Generate the cross-scenario evaluation package after the batch completes:

```bash
python inpatient_care_analysis.py \
  --results-root results/inpatient_care \
  --expected-seeds 0-29
```

## Outputs

The inpatient care logger writes semicolon-separated UTF-8 CSV files under the
experiment's `data_frames` directory:

- `inpatient_events.csv`: demand, queue, rerouting, admission, and discharge;
- `inpatient_step.csv`: global demand, occupancy, overflow, queue, and delays;
- `inpatient_bed_step.csv`: hospital/specialty/type/payer capacity state;
- `inpatient_region_step.csv`: region-level state for future maps;
- `inpatient_locations.csv`: hospital coordinates.

Reference-study occupancy/capacity charts, queue charts, and delay charts are
exported to `html_plots/inpatient_care`, with optional PNG output.

The multi-seed analysis is written to `results/inpatient_care/analysis`. It
contains:

- scenario-by-seed and aggregate mean/median/standard-deviation/5th/95th
  percentile tables;
- paired overflow-versus-queue comparisons using the same seeds;
- specialty, bed-type, payer, hospital, and CID/origin breakdowns;
- occupancy, capacity, overflow, queue, delay, admission-coverage, and travel
  distance plots;
- demand, population, occupancy, payer-pool, policy, seed-completeness, and
  deterministic-output audits;
- `report.md`, which records the main comparisons, limitations, and provenance.

The evaluation command returns a non-zero status if any integrity audit fails.
The evaluation covers only the seven catalog scenarios; it does not create
demand sweeps, recovery horizons, dynamic routing, or other proposed
experiments.

## Historical CID fixture

`legacy_cid_counts.csv` is the normalized surviving 915-case file used by the
old plugin. Its codes are B342, J180, and J189, so it is not treated as a
psychiatric study. The legacy region label
`Jardim Botânico Avenida Ipiranga - de 2581 a 6699 - lado ímpar` must be
provided as a `region_aliases` entry mapping to `Jardim Botânico`. Unknown
regions and CIDs now fail validation instead of silently dropping demand.
`legacy_cid_source.fixture.json` contains this complete compatibility adapter
configuration. Its CID mapping is deliberately labeled as compatibility-only
and must not be interpreted clinically.

The Flask UI, generated medical text, individual patient UUIDs, mortality,
bed transfers, insurance networks, and `HealthExamplePlugin` are intentionally
outside this backend milestone.
