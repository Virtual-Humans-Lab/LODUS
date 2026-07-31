"""Aggregate inpatient care experiments into research-oriented evaluations."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd
import plotly.express as px


SCENARIOS = {
    "ReferenceDemandOverflow": {
        "family": "ReferenceDemand",
        "policy": "overflow",
    },
    "ReferenceDemandQueue": {
        "family": "ReferenceDemand",
        "policy": "queue",
    },
    "HighDemandOverflow": {
        "family": "HighDemand",
        "policy": "overflow",
    },
    "HighDemandQueue": {
        "family": "HighDemand",
        "policy": "queue",
    },
    "TwoFacilityOverflow": {
        "family": "TwoFacility",
        "policy": "overflow",
    },
    "TwoFacilityQueue": {
        "family": "TwoFacility",
        "policy": "queue",
    },
    "CIDRoutingQueue": {
        "family": "CIDRouting",
        "policy": "queue",
    },
}
SCENARIO_ORDER = list(SCENARIOS)
POLICY_PAIRS = {
    "ReferenceDemand": (
        "ReferenceDemandOverflow",
        "ReferenceDemandQueue",
    ),
    "HighDemand": ("HighDemandOverflow", "HighDemandQueue"),
    "TwoFacility": ("TwoFacilityOverflow", "TwoFacilityQueue"),
}
EXPECTED_DEMAND = {
    "ReferenceDemandOverflow": {
        ("Psiquiatria", "Outras Especialidades", "private"): 200,
        ("Psiquiatria", "Outras Especialidades", "sus"): 300,
        ("Saúde Mental", "Hospital Dia", "sus"): 50,
    },
    "ReferenceDemandQueue": {
        ("Psiquiatria", "Outras Especialidades", "private"): 200,
        ("Psiquiatria", "Outras Especialidades", "sus"): 300,
        ("Saúde Mental", "Hospital Dia", "sus"): 50,
    },
    "HighDemandOverflow": {
        ("Psiquiatria", "Outras Especialidades", "private"): 1050,
        ("Psiquiatria", "Outras Especialidades", "sus"): 1590,
        ("Saúde Mental", "Hospital Dia", "sus"): 150,
    },
    "HighDemandQueue": {
        ("Psiquiatria", "Outras Especialidades", "private"): 1050,
        ("Psiquiatria", "Outras Especialidades", "sus"): 1590,
        ("Saúde Mental", "Hospital Dia", "sus"): 150,
    },
    "TwoFacilityOverflow": {
        ("Psiquiatria", "Outras Especialidades", "private"): 1050,
        ("Psiquiatria", "Outras Especialidades", "sus"): 1590,
    },
    "TwoFacilityQueue": {
        ("Psiquiatria", "Outras Especialidades", "private"): 1050,
        ("Psiquiatria", "Outras Especialidades", "sus"): 1590,
    },
    "CIDRoutingQueue": {
        ("Psiquiatria", "Outras Especialidades", "private"): 20,
        ("Psiquiatria", "Outras Especialidades", "sus"): 115,
        ("Saúde Mental", "Hospital Dia", "sus"): 90,
    },
}
RUN_METRICS = [
    "demand",
    "admitted",
    "admission_coverage",
    "discharged",
    "inpatients_end",
    "peak_occupancy",
    "occupancy_end",
    "occupied_bed_steps",
    "configured_active_bed_steps",
    "available_active_bed_steps",
    "excess_bed_steps",
    "peak_overflow",
    "steps_above_capacity",
    "peak_queue",
    "final_queue",
    "queue_patient_steps",
    "mean_admission_delay",
    "median_admission_delay",
    "maximum_admission_delay",
    "rerouted",
    "mean_admission_distance_km",
]
PAIR_METRICS = [
    "admission_coverage",
    "admitted",
    "final_queue",
    "peak_queue",
    "queue_patient_steps",
    "mean_admission_delay",
    "maximum_admission_delay",
    "peak_overflow",
    "excess_bed_steps",
    "occupied_bed_steps",
    "inpatients_end",
]
KEY_COLUMNS = ["Hospital", "Specialty", "Bed Type", "Payer"]


def parse_seeds(value: str) -> list[int]:
    seeds = []
    for part in value.split(","):
        part = part.strip()
        if not part:
            continue
        if "-" in part:
            start_text, end_text = part.split("-", 1)
            start, end = int(start_text), int(end_text)
            if end < start:
                raise ValueError("Seed range end must be >= start")
            seeds.extend(range(start, end + 1))
        else:
            seeds.append(int(part))
    return sorted(set(seeds))


def weighted_mean(values: Iterable, weights: Iterable) -> float:
    values_array = np.asarray(list(values), dtype=float)
    weights_array = np.asarray(list(weights), dtype=float)
    valid = (
        np.isfinite(values_array)
        & np.isfinite(weights_array)
        & (weights_array > 0)
    )
    if not valid.any():
        return 0.0
    return float(
        np.average(values_array[valid], weights=weights_array[valid])
    )


def weighted_quantile(
    values: Iterable, weights: Iterable, quantile: float
) -> float:
    values_array = np.asarray(list(values), dtype=float)
    weights_array = np.asarray(list(weights), dtype=float)
    valid = (
        np.isfinite(values_array)
        & np.isfinite(weights_array)
        & (weights_array > 0)
    )
    if not valid.any():
        return 0.0
    values_array = values_array[valid]
    weights_array = weights_array[valid]
    order = np.argsort(values_array)
    values_array = values_array[order]
    weights_array = weights_array[order]
    cumulative = np.cumsum(weights_array)
    threshold = quantile * weights_array.sum()
    return float(values_array[np.searchsorted(cumulative, threshold)])


def _read_csv(path: Path) -> pd.DataFrame:
    return pd.read_csv(path, sep=";", encoding="utf-8-sig")


def _event_population(events: pd.DataFrame, event_type: str) -> int:
    return int(
        events.loc[events["Event"] == event_type, "Population"].sum()
    )


def discover_runs(
    results_root: Path,
) -> list[tuple[str, int, Path, dict]]:
    runs = []
    for scenario_id in SCENARIOS:
        for run_path in sorted((results_root / scenario_id).glob("seed_*")):
            metadata_path = run_path / "run_metadata.json"
            if not metadata_path.is_file():
                continue
            metadata = json.loads(metadata_path.read_text(encoding="utf8"))
            if metadata.get("status") != "complete":
                continue
            try:
                seed = int(run_path.name.removeprefix("seed_"))
            except ValueError:
                continue
            runs.append((scenario_id, seed, run_path, metadata))
    return runs


def _active_bed_rows(
    beds: pd.DataFrame, events: pd.DataFrame
) -> pd.DataFrame:
    payer_beds = beds[beds["Payer"].isin(["sus", "private"])].copy()
    activity = (
        payer_beds.groupby(KEY_COLUMNS)[
            ["Occupancy", "Admitted", "Discharged"]
        ]
        .sum()
        .sum(axis=1)
    )
    keys = set(activity[activity > 0].index)
    demanded = events[
        (events["Event"] == "demanded") & events["Hospital"].notna()
    ]
    demanded = demanded[demanded["Hospital"].astype(str) != ""]
    keys.update(
        demanded[KEY_COLUMNS].drop_duplicates().itertuples(
            index=False, name=None
        )
    )
    if not keys:
        return payer_beds.iloc[0:0]
    index = pd.MultiIndex.from_frame(payer_beds[KEY_COLUMNS])
    return payer_beds[index.isin(keys)].copy()


def summarize_run(
    scenario_id: str,
    seed: int,
    run_path: Path,
    metadata: dict,
) -> tuple[dict, dict[str, pd.DataFrame]]:
    data_path = run_path / "data_frames"
    events = _read_csv(data_path / "inpatient_events.csv")
    steps = _read_csv(data_path / "inpatient_step.csv")
    beds = _read_csv(data_path / "inpatient_bed_step.csv")
    active_beds = _active_bed_rows(beds, events)
    admissions = events[events["Event"] == "admitted"].copy()
    demand = _event_population(events, "demanded")
    admitted = _event_population(events, "admitted")
    discharged = _event_population(events, "discharged")
    delays = pd.to_numeric(
        admissions["Admission Delay Steps"], errors="coerce"
    )
    distances = pd.to_numeric(
        admissions["Distance Km"], errors="coerce"
    )
    weights = pd.to_numeric(admissions["Population"], errors="coerce")
    active_by_step = (
        active_beds.groupby("Simulation Step")["Configured Capacity"].sum()
        if not active_beds.empty
        else pd.Series(dtype=float)
    )
    occupied_by_step = (
        active_beds.groupby("Simulation Step")["Occupancy"].sum()
        if not active_beds.empty
        else pd.Series(dtype=float)
    )
    row = {
        "scenario": scenario_id,
        "family": SCENARIOS[scenario_id]["family"],
        "policy": SCENARIOS[scenario_id]["policy"],
        "seed": seed,
        "run_path": str(run_path),
        "demand": demand,
        "admitted": admitted,
        "admission_coverage": admitted / demand if demand else 1.0,
        "discharged": discharged,
        "inpatients_end": admitted - discharged,
        "peak_occupancy": int(steps["Occupancy"].max()),
        "occupancy_end": int(steps.iloc[-1]["Occupancy"]),
        "occupied_bed_steps": int(beds.loc[
            beds["Payer"].isin(["sus", "private"]), "Occupancy"
        ].sum()),
        "configured_active_bed_steps": int(active_by_step.sum()),
        "available_active_bed_steps": int(
            sum(
                max(0, capacity - occupancy)
                for capacity, occupancy in zip(
                    active_by_step.reindex(
                        occupied_by_step.index, fill_value=0
                    ),
                    occupied_by_step,
                )
            )
        ),
        "excess_bed_steps": int(
            beds.loc[
                beds["Payer"].isin(["sus", "private"]), "Overflow"
            ].sum()
        ),
        "peak_overflow": int(steps["Overflow"].max()),
        "steps_above_capacity": int((steps["Overflow"] > 0).sum()),
        "peak_queue": int(steps["Waiting"].max()),
        "final_queue": int(steps.iloc[-1]["Waiting"]),
        "queue_patient_steps": int(steps["Waiting"].sum()),
        "mean_admission_delay": weighted_mean(delays, weights),
        "median_admission_delay": weighted_quantile(delays, weights, 0.5),
        "maximum_admission_delay": (
            float(delays.max()) if len(delays) else 0.0
        ),
        "rerouted": _event_population(events, "rerouted"),
        "mean_admission_distance_km": weighted_mean(distances, weights),
        "runtime_seconds": metadata.get("runtime_seconds"),
        "peak_memory_kib": metadata.get("peak_memory_kib"),
    }
    return row, {
        "events": events,
        "steps": steps,
        "beds": beds,
        "active_beds": active_beds,
    }


def bed_pool_rows(
    scenario_id: str,
    seed: int,
    frames: dict[str, pd.DataFrame],
) -> list[dict]:
    events = frames["events"]
    active = frames["active_beds"]
    rows = []
    for key, group in active.groupby(KEY_COLUMNS, sort=True):
        hospital, specialty, bed_type, payer = key
        admissions = events[
            (events["Event"] == "admitted")
            & (events["Hospital"] == hospital)
            & (events["Specialty"] == specialty)
            & (events["Bed Type"] == bed_type)
            & (events["Payer"] == payer)
        ]
        discharges = events[
            (events["Event"] == "discharged")
            & (events["Hospital"] == hospital)
            & (events["Specialty"] == specialty)
            & (events["Bed Type"] == bed_type)
            & (events["Payer"] == payer)
        ]
        queued = events[
            (events["Event"] == "queued")
            & (events["Preferred Hospital"] == hospital)
            & (events["Specialty"] == specialty)
            & (events["Bed Type"] == bed_type)
            & (events["Payer"] == payer)
        ]
        targeted = events[
            (events["Event"] == "demanded")
            & (events["Hospital"] == hospital)
            & (events["Specialty"] == specialty)
            & (events["Bed Type"] == bed_type)
            & (events["Payer"] == payer)
        ]
        capacity = int(group["Configured Capacity"].max())
        queue_by_step = queued.groupby("Simulation Step")[
            "Population"
        ].sum()
        rows.append(
            {
                "scenario": scenario_id,
                "family": SCENARIOS[scenario_id]["family"],
                "policy": SCENARIOS[scenario_id]["policy"],
                "seed": seed,
                "hospital": hospital,
                "specialty": specialty,
                "bed_type": bed_type,
                "payer": payer,
                "capacity": capacity,
                "targeted_demand": int(targeted["Population"].sum()),
                "admitted": int(admissions["Population"].sum()),
                "discharged": int(discharges["Population"].sum()),
                "peak_occupancy": int(group["Occupancy"].max()),
                "occupancy_end": int(
                    group.sort_values("Simulation Step").iloc[-1][
                        "Occupancy"
                    ]
                ),
                "peak_utilization": (
                    float(group["Occupancy"].max()) / capacity
                    if capacity
                    else 0.0
                ),
                "occupied_bed_steps": int(group["Occupancy"].sum()),
                "available_bed_steps": int(
                    group["Available Capacity"].sum()
                ),
                "excess_bed_steps": int(group["Overflow"].sum()),
                "peak_overflow": int(group["Overflow"].max()),
                "steps_full": int((group["Occupancy"] >= capacity).sum()),
                "steps_above_capacity": int(
                    (group["Occupancy"] > capacity).sum()
                ),
                "queue_patient_steps_for_preferred_demand": int(
                    queued["Population"].sum()
                ),
                "peak_queue_for_preferred_demand": (
                    int(queue_by_step.max()) if len(queue_by_step) else 0
                ),
                "mean_admission_delay": weighted_mean(
                    admissions["Admission Delay Steps"],
                    admissions["Population"],
                ),
                "median_admission_delay": weighted_quantile(
                    admissions["Admission Delay Steps"],
                    admissions["Population"],
                    0.5,
                ),
                "maximum_admission_delay": (
                    float(admissions["Admission Delay Steps"].max())
                    if len(admissions)
                    else 0.0
                ),
                "mean_admission_distance_km": weighted_mean(
                    admissions["Distance Km"], admissions["Population"]
                ),
                "synthetic_capacity": int(
                    group["Synthetic Capacity"].max()
                ),
            }
        )
    return rows


def demand_strata_rows(
    scenario_id: str,
    seed: int,
    frames: dict[str, pd.DataFrame],
) -> list[dict]:
    events = frames["events"]
    active_beds = frames["active_beds"]
    rows = []
    group_columns = ["Specialty", "Bed Type", "Payer"]
    demanded = events[events["Event"] == "demanded"]
    admitted = events[events["Event"] == "admitted"]
    for key, group in demanded.groupby(group_columns, sort=True):
        specialty, bed_type, payer = key
        matching_admissions = admitted[
            (admitted["Specialty"] == specialty)
            & (admitted["Bed Type"] == bed_type)
            & (admitted["Payer"] == payer)
        ]
        matching_discharges = events[
            (events["Event"] == "discharged")
            & (events["Specialty"] == specialty)
            & (events["Bed Type"] == bed_type)
            & (events["Payer"] == payer)
        ]
        matching_queue = events[
            (events["Event"] == "queued")
            & (events["Specialty"] == specialty)
            & (events["Bed Type"] == bed_type)
            & (events["Payer"] == payer)
        ]
        matching_reroutes = events[
            (events["Event"] == "rerouted")
            & (events["Specialty"] == specialty)
            & (events["Bed Type"] == bed_type)
            & (events["Payer"] == payer)
        ]
        matching_beds = active_beds[
            (active_beds["Specialty"] == specialty)
            & (active_beds["Bed Type"] == bed_type)
            & (active_beds["Payer"] == payer)
        ]
        demand = int(group["Population"].sum())
        admission_count = int(matching_admissions["Population"].sum())
        discharge_count = int(matching_discharges["Population"].sum())
        delays = matching_admissions["Admission Delay Steps"]
        weights = matching_admissions["Population"]
        occupancy_by_step = matching_beds.groupby("Simulation Step")[
            "Occupancy"
        ].sum()
        overflow_by_step = matching_beds.groupby("Simulation Step")[
            "Overflow"
        ].sum()
        queue_by_step = matching_queue.groupby("Simulation Step")[
            "Population"
        ].sum()
        rows.append(
            {
                "scenario": scenario_id,
                "family": SCENARIOS[scenario_id]["family"],
                "policy": SCENARIOS[scenario_id]["policy"],
                "seed": seed,
                "specialty": specialty,
                "bed_type": bed_type,
                "payer": payer,
                "demand": demand,
                "admitted": admission_count,
                "discharged": discharge_count,
                "inpatients_end": admission_count - discharge_count,
                "final_waiting": demand - admission_count,
                "admission_coverage": (
                    admission_count / demand if demand else 1.0
                ),
                "peak_occupancy": int(occupancy_by_step.max()),
                "occupancy_end": int(occupancy_by_step.iloc[-1]),
                "occupied_bed_steps": int(matching_beds["Occupancy"].sum()),
                "available_bed_steps": int(
                    matching_beds["Available Capacity"].sum()
                ),
                "excess_bed_steps": int(
                    matching_beds["Overflow"].sum()
                ),
                "peak_overflow": int(overflow_by_step.max()),
                "steps_above_capacity": int(
                    (overflow_by_step > 0).sum()
                ),
                "queue_patient_steps": int(
                    matching_queue["Population"].sum()
                ),
                "peak_queue": (
                    int(queue_by_step.max()) if len(queue_by_step) else 0
                ),
                "mean_admission_delay": weighted_mean(delays, weights),
                "median_admission_delay": weighted_quantile(
                    delays, weights, 0.5
                ),
                "maximum_admission_delay": (
                    float(delays.max()) if len(delays) else 0.0
                ),
                "rerouted": int(matching_reroutes["Population"].sum()),
                "mean_admission_distance_km": weighted_mean(
                    matching_admissions["Distance Km"], weights
                ),
            }
        )
    return rows


def facility_rows(
    scenario_id: str,
    seed: int,
    bed_rows: list[dict],
    events: pd.DataFrame,
) -> list[dict]:
    frame = pd.DataFrame(bed_rows)
    if frame.empty:
        return []
    rows = []
    for hospital, group in frame.groupby("hospital", sort=True):
        admissions = events[
            (events["Event"] == "admitted")
            & (events["Hospital"] == hospital)
        ]
        queued = events[
            (events["Event"] == "queued")
            & (events["Preferred Hospital"] == hospital)
        ]
        targeted_demand = int(group["targeted_demand"].sum())
        admitted = int(group["admitted"].sum())
        rows.append(
            {
                "scenario": scenario_id,
                "family": SCENARIOS[scenario_id]["family"],
                "policy": SCENARIOS[scenario_id]["policy"],
                "seed": seed,
                "hospital": hospital,
                "capacity": int(group["capacity"].sum()),
                "targeted_demand": targeted_demand,
                "admitted": admitted,
                "targeted_admission_coverage": (
                    admitted / targeted_demand
                    if targeted_demand
                    else np.nan
                ),
                "discharged": int(group["discharged"].sum()),
                "inpatients_end": (
                    admitted - int(group["discharged"].sum())
                ),
                "occupied_bed_steps": int(
                    group["occupied_bed_steps"].sum()
                ),
                "available_bed_steps": int(
                    group["available_bed_steps"].sum()
                ),
                "excess_bed_steps": int(
                    group["excess_bed_steps"].sum()
                ),
                "peak_overflow_sum_by_pool": int(
                    group["peak_overflow"].sum()
                ),
                "queue_patient_steps_for_preferred_demand": int(
                    queued["Population"].sum()
                ),
                "mean_admission_delay": weighted_mean(
                    admissions["Admission Delay Steps"],
                    admissions["Population"],
                ),
                "median_admission_delay": weighted_quantile(
                    admissions["Admission Delay Steps"],
                    admissions["Population"],
                    0.5,
                ),
                "maximum_admission_delay": (
                    float(admissions["Admission Delay Steps"].max())
                    if len(admissions)
                    else 0.0
                ),
                "mean_admission_distance_km": weighted_mean(
                    admissions["Distance Km"], admissions["Population"]
                ),
            }
        )
    return rows


def time_step_rows(
    scenario_id: str,
    seed: int,
    frames: dict[str, pd.DataFrame],
) -> list[dict]:
    steps = frames["steps"]
    active_beds = frames["active_beds"]
    active_capacity = active_beds.groupby("Simulation Step")[
        "Configured Capacity"
    ].sum()
    cumulative_demand = steps["New Demand"].cumsum()
    cumulative_admitted = steps["Admitted"].cumsum()
    rows = []
    for position, (_, step) in enumerate(steps.iterrows()):
        demand = int(cumulative_demand.iloc[position])
        admitted = int(cumulative_admitted.iloc[position])
        simulation_step = int(step["Simulation Step"])
        rows.append(
            {
                "scenario": scenario_id,
                "family": SCENARIOS[scenario_id]["family"],
                "policy": SCENARIOS[scenario_id]["policy"],
                "seed": seed,
                "simulation_step": simulation_step,
                "new_demand": int(step["New Demand"]),
                "admitted": int(step["Admitted"]),
                "discharged": int(step["Discharged"]),
                "occupancy": int(step["Occupancy"]),
                "configured_capacity": int(
                    active_capacity.get(simulation_step, 0)
                ),
                "overflow": int(step["Overflow"]),
                "waiting": int(step["Waiting"]),
                "cumulative_demand": demand,
                "cumulative_admitted": admitted,
                "cumulative_admission_coverage": (
                    admitted / demand if demand else 1.0
                ),
            }
        )
    return rows


def aggregate_time_steps(time_steps: pd.DataFrame) -> pd.DataFrame:
    identifiers = ["scenario", "family", "policy", "simulation_step"]
    metrics = [
        "new_demand",
        "admitted",
        "discharged",
        "occupancy",
        "configured_capacity",
        "overflow",
        "waiting",
        "cumulative_demand",
        "cumulative_admitted",
        "cumulative_admission_coverage",
    ]
    grouped = time_steps.groupby(identifiers, sort=True)
    rows = []
    for key, group in grouped:
        row = dict(zip(identifiers, key))
        row["repetitions"] = int(group["seed"].nunique())
        for metric in metrics:
            values = group[metric]
            row[f"{metric}_mean"] = float(values.mean())
            row[f"{metric}_median"] = float(values.median())
            row[f"{metric}_std"] = (
                float(values.std(ddof=1)) if len(values) > 1 else 0.0
            )
            row[f"{metric}_p05"] = float(values.quantile(0.05))
            row[f"{metric}_p95"] = float(values.quantile(0.95))
        rows.append(row)
    return pd.DataFrame(rows)


def cid_rows(
    scenario_id: str,
    seed: int,
    events: pd.DataFrame,
) -> tuple[list[dict], list[dict], list[dict]]:
    if scenario_id != "CIDRoutingQueue":
        return [], [], []
    admissions = events[events["Event"] == "admitted"].copy()
    flows = []
    flow_columns = [
        "Origin Region",
        "CID",
        "Specialty",
        "Bed Type",
        "Hospital",
        "Payer",
    ]
    for key, group in admissions.groupby(flow_columns, sort=True):
        weights = group["Population"]
        flows.append(
            {
                "scenario": scenario_id,
                "seed": seed,
                "origin_region": key[0],
                "cid": key[1],
                "specialty": key[2],
                "bed_type": key[3],
                "hospital": key[4],
                "payer": key[5],
                "admitted": int(weights.sum()),
                "mean_delay": weighted_mean(
                    group["Admission Delay Steps"], weights
                ),
                "p95_delay": weighted_quantile(
                    group["Admission Delay Steps"], weights, 0.95
                ),
                "mean_distance_km": weighted_mean(
                    group["Distance Km"], weights
                ),
                "p95_distance_km": weighted_quantile(
                    group["Distance Km"], weights, 0.95
                ),
            }
        )

    demanded = events[events["Event"] == "demanded"].copy()
    origins = []
    origin_columns = [
        "Origin Region",
        "CID",
        "Specialty",
        "Bed Type",
        "Payer",
    ]
    for key, group in demanded.groupby(origin_columns, sort=True):
        matching = admissions[
            (admissions["Origin Region"] == key[0])
            & (admissions["CID"] == key[1])
            & (admissions["Specialty"] == key[2])
            & (admissions["Bed Type"] == key[3])
            & (admissions["Payer"] == key[4])
        ]
        demand = int(group["Population"].sum())
        admitted_count = int(matching["Population"].sum())
        hospital_counts = matching.groupby("Hospital")["Population"].sum()
        shares = (
            hospital_counts / admitted_count
            if admitted_count
            else pd.Series(dtype=float)
        )
        origins.append(
            {
                "scenario": scenario_id,
                "seed": seed,
                "origin_region": key[0],
                "cid": key[1],
                "specialty": key[2],
                "bed_type": key[3],
                "payer": key[4],
                "demand": demand,
                "admitted": admitted_count,
                "admission_coverage": (
                    admitted_count / demand if demand else 1.0
                ),
                "mean_delay": weighted_mean(
                    matching["Admission Delay Steps"],
                    matching["Population"],
                ),
                "mean_distance_km": weighted_mean(
                    matching["Distance Km"], matching["Population"]
                ),
                "destination_count": int(len(hospital_counts)),
                "largest_destination_share": (
                    float(shares.max()) if len(shares) else 0.0
                ),
                "destination_hhi": (
                    float((shares**2).sum()) if len(shares) else 0.0
                ),
            }
        )

    queued = events[events["Event"] == "queued"].copy()
    queue_rows = []
    if not queued.empty:
        step_groups = (
            queued.groupby(
                [
                    "Origin Region",
                    "CID",
                    "Specialty",
                    "Simulation Step",
                ]
            )["Population"]
            .sum()
            .reset_index()
        )
        for key, group in step_groups.groupby(
            ["Origin Region", "CID", "Specialty"], sort=True
        ):
            queue_rows.append(
                {
                    "scenario": scenario_id,
                    "seed": seed,
                    "origin_region": key[0],
                    "cid": key[1],
                    "specialty": key[2],
                    "queue_patient_steps": int(group["Population"].sum()),
                    "peak_queue": int(group["Population"].max()),
                    "steps_with_queue": int(
                        (group["Population"] > 0).sum()
                    ),
                }
            )
    return flows, origins, queue_rows


def audit_run(
    scenario_id: str,
    seed: int,
    summary: dict,
    frames: dict[str, pd.DataFrame],
) -> tuple[list[dict], list[dict]]:
    events = frames["events"]
    steps = frames["steps"]
    beds = frames["beds"]
    policy = SCENARIOS[scenario_id]["policy"]
    audits = []
    demand_details = []

    def add(
        check: str,
        passed: bool,
        observed,
        expected,
        scope: str = "run",
        detail: str = "",
    ):
        audits.append(
            {
                "scenario": scenario_id,
                "seed": seed,
                "check": check,
                "scope": scope,
                "passed": bool(passed),
                "observed": observed,
                "expected": expected,
                "difference": (
                    float(observed) - float(expected)
                    if isinstance(observed, (int, float, np.number))
                    and isinstance(expected, (int, float, np.number))
                    else None
                ),
                "detail": detail,
            }
        )

    demanded = events[events["Event"] == "demanded"]
    actual_by_stratum = (
        demanded.groupby(["Specialty", "Bed Type", "Payer"])[
            "Population"
        ].sum()
    )
    expected_by_stratum = EXPECTED_DEMAND[scenario_id]
    all_strata = set(actual_by_stratum.index) | set(expected_by_stratum)
    for specialty, bed_type, payer in sorted(all_strata):
        actual = int(
            actual_by_stratum.get((specialty, bed_type, payer), 0)
        )
        expected = expected_by_stratum.get(
            (specialty, bed_type, payer), 0
        )
        scope = f"{specialty}|{bed_type}|{payer}"
        add(
            "configured_demand_conservation",
            actual == expected,
            actual,
            expected,
            scope,
        )
        demand_details.append(
            {
                "scenario": scenario_id,
                "seed": seed,
                "specialty": specialty,
                "bed_type": bed_type,
                "payer": payer,
                "observed_demand": actual,
                "expected_demand": expected,
                "passed": actual == expected,
            }
        )

    add(
        "demand_state_conservation",
        summary["demand"]
        == summary["admitted"] + summary["final_queue"],
        summary["admitted"] + summary["final_queue"],
        summary["demand"],
    )
    add(
        "inpatient_state_conservation",
        summary["admitted"] - summary["discharged"]
        == summary["occupancy_end"],
        summary["admitted"] - summary["discharged"],
        summary["occupancy_end"],
    )

    if {
        "Global Population",
        "Population Delta From Initial",
    }.issubset(steps.columns):
        add(
            "global_population_conservation",
            bool(
                (steps["Population Delta From Initial"] == 0).all()
                and steps["Global Population"].nunique() == 1
            ),
            int(steps["Global Population"].max())
            - int(steps["Global Population"].min()),
            0,
        )
    else:
        add(
            "global_population_conservation",
            False,
            "missing columns",
            "constant population",
        )

    payer_beds = beds[beds["Payer"].isin(["sus", "private"])]
    balance_failures = 0
    overflow_failures = 0
    capacity_failures = 0
    for key, group in payer_beds.groupby(KEY_COLUMNS, sort=False):
        group = group.sort_values("Simulation Step")
        previous = group["Occupancy"].shift(fill_value=0)
        expected_occupancy = (
            previous + group["Admitted"] - group["Discharged"]
        )
        balance_failures += int(
            (expected_occupancy != group["Occupancy"]).sum()
        )
        expected_overflow = (
            group["Occupancy"] - group["Configured Capacity"]
        ).clip(lower=0)
        overflow_failures += int(
            (expected_overflow != group["Overflow"]).sum()
        )
        if policy == "queue":
            capacity_failures += int(
                (
                    group["Occupancy"]
                    > group["Configured Capacity"]
                ).sum()
            )
    add(
        "occupancy_balance",
        balance_failures == 0,
        balance_failures,
        0,
        detail="pool-step mismatches",
    )
    add(
        "overflow_accounting",
        overflow_failures == 0,
        overflow_failures,
        0,
        detail="pool-step mismatches",
    )
    if policy == "overflow":
        add(
            "overflow_policy_has_no_queue",
            bool((steps["Waiting"] == 0).all()),
            int(steps["Waiting"].max()),
            0,
        )
        add(
            "overflow_policy_admits_all_demand",
            summary["admitted"] == summary["demand"],
            summary["admitted"],
            summary["demand"],
        )
    else:
        add(
            "queue_policy_has_no_overflow",
            bool((steps["Overflow"] == 0).all()),
            int(steps["Overflow"].max()),
            0,
        )
        add(
            "queue_policy_respects_payer_capacity",
            capacity_failures == 0,
            capacity_failures,
            0,
            detail="pool-step capacity violations",
        )
    return audits, demand_details


def long_distribution_summary(
    frame: pd.DataFrame,
    group_columns: list[str],
    metrics: list[str],
) -> pd.DataFrame:
    rows = []
    for group_key, group in frame.groupby(group_columns, dropna=False):
        if not isinstance(group_key, tuple):
            group_key = (group_key,)
        identity = dict(zip(group_columns, group_key))
        for metric in metrics:
            values = pd.to_numeric(
                group[metric], errors="coerce"
            ).dropna()
            row = {
                **identity,
                "metric": metric,
                "repetitions": len(values),
                "mean": float(values.mean()) if len(values) else np.nan,
                "median": (
                    float(values.median()) if len(values) else np.nan
                ),
                "std": (
                    float(values.std(ddof=1)) if len(values) > 1 else 0.0
                ),
                "p05": (
                    float(values.quantile(0.05))
                    if len(values)
                    else np.nan
                ),
                "p95": (
                    float(values.quantile(0.95))
                    if len(values)
                    else np.nan
                ),
            }
            rows.append(row)
    return pd.DataFrame(rows)


def paired_policy_tables(
    runs: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    rows = []
    for family, (overflow_id, queue_id) in POLICY_PAIRS.items():
        overflow = runs[runs["scenario"] == overflow_id].set_index("seed")
        queue = runs[runs["scenario"] == queue_id].set_index("seed")
        for seed in sorted(overflow.index.intersection(queue.index)):
            for metric in PAIR_METRICS:
                overflow_value = float(overflow.loc[seed, metric])
                queue_value = float(queue.loc[seed, metric])
                rows.append(
                    {
                        "family": family,
                        "seed": seed,
                        "metric": metric,
                        "overflow": overflow_value,
                        "queue": queue_value,
                        "queue_minus_overflow": (
                            queue_value - overflow_value
                        ),
                    }
                )
    paired = pd.DataFrame(rows)
    summary_rows = []
    for (family, metric), group in paired.groupby(
        ["family", "metric"], sort=True
    ):
        values = group["queue_minus_overflow"]
        summary_rows.append(
            {
                "family": family,
                "metric": metric,
                "paired_repetitions": len(values),
                "mean_difference": float(values.mean()),
                "median_difference": float(values.median()),
                "std_difference": (
                    float(values.std(ddof=1)) if len(values) > 1 else 0.0
                ),
                "p05_difference": float(values.quantile(0.05)),
                "p95_difference": float(values.quantile(0.95)),
            }
        )
    return paired, pd.DataFrame(summary_rows)


def aggregate_cid_flows(flows: pd.DataFrame) -> pd.DataFrame:
    if flows.empty:
        return flows
    group_columns = [
        "origin_region",
        "cid",
        "specialty",
        "bed_type",
        "hospital",
        "payer",
    ]
    rows = []
    for key, group in flows.groupby(group_columns, sort=True):
        admitted = group["admitted"]
        rows.append(
            {
                **dict(zip(group_columns, key)),
                "repetitions": group["seed"].nunique(),
                "admitted_total": int(admitted.sum()),
                "admitted_mean": float(admitted.mean()),
                "mean_delay": weighted_mean(
                    group["mean_delay"], admitted
                ),
                "mean_distance_km": weighted_mean(
                    group["mean_distance_km"], admitted
                ),
            }
        )
    return pd.DataFrame(rows)


def _write_plots(
    analysis_path: Path,
    runs: pd.DataFrame,
    bed_pools: pd.DataFrame,
    cid_origins: pd.DataFrame,
    time_summary: pd.DataFrame,
):
    plots_path = analysis_path / "plots"
    plots_path.mkdir(parents=True, exist_ok=True)
    for metric, title in (
        ("admission_coverage", "Inpatient Admission Coverage"),
        ("peak_overflow", "Peak Overflow"),
        ("final_queue", "Final Queue"),
        ("queue_patient_steps", "Queue Patient-Steps"),
        ("mean_admission_delay", "Mean Admission Delay"),
    ):
        figure = px.box(
            runs,
            x="scenario",
            y=metric,
            color="policy",
            points="all",
            title=title,
            category_orders={"scenario": SCENARIO_ORDER},
        )
        figure.write_html(
            plots_path / f"{metric}.html", include_plotlyjs="cdn"
        )
    trajectory_specs = (
        (
            ["occupancy_mean", "configured_capacity_mean"],
            "Occupancy and Active Configured Capacity",
            "Patients / beds",
            "occupancy_capacity_trajectory.html",
        ),
        (
            ["overflow_mean"],
            "Overflow Trajectory",
            "Patients above capacity",
            "overflow_trajectory.html",
        ),
        (
            ["waiting_mean"],
            "Queue Trajectory",
            "Waiting patients",
            "queue_trajectory.html",
        ),
        (
            ["cumulative_admission_coverage_mean"],
            "Cumulative Admission Coverage",
            "Admission coverage",
            "admission_coverage_trajectory.html",
        ),
    )
    for columns, title, label, filename in trajectory_specs:
        melted = time_summary.melt(
            id_vars=["scenario", "simulation_step"],
            value_vars=columns,
            var_name="measure",
            value_name="mean",
        )
        figure = px.line(
            melted,
            x="simulation_step",
            y="mean",
            color="measure",
            facet_col="scenario",
            facet_col_wrap=2,
            markers=True,
            title=title,
            labels={"mean": label, "simulation_step": "Simulation step"},
            category_orders={"scenario": SCENARIO_ORDER},
        )
        figure.for_each_annotation(
            lambda annotation: annotation.update(
                text=annotation.text.split("=")[-1]
            )
        )
        figure.write_html(plots_path / filename, include_plotlyjs="cdn")
    if not bed_pools.empty:
        figure = px.box(
            bed_pools,
            x="scenario",
            y="peak_utilization",
            color="payer",
            facet_row="specialty",
            points=False,
            title="Peak Bed-Pool Utilization by Specialty and Payer",
            category_orders={"scenario": SCENARIO_ORDER},
        )
        figure.write_html(
            plots_path / "bed_pool_utilization.html",
            include_plotlyjs="cdn",
        )
    if not cid_origins.empty:
        figure = px.scatter(
            cid_origins,
            x="mean_distance_km",
            y="mean_delay",
            size="admitted",
            color="origin_region",
            symbol="payer",
            hover_data=["cid", "specialty", "seed"],
            title="CID Routing Distance and Admission Delay",
        )
        figure.write_html(
            plots_path / "cid_distance_delay.html",
            include_plotlyjs="cdn",
        )


def _scenario_metric(
    summary: pd.DataFrame, scenario: str, metric: str
) -> dict:
    row = summary[
        (summary["scenario"] == scenario)
        & (summary["metric"] == metric)
    ]
    return row.iloc[0].to_dict() if len(row) else {}


def write_report(
    analysis_path: Path,
    runs: pd.DataFrame,
    scenario_summary: pd.DataFrame,
    paired_summary: pd.DataFrame,
    demand_strata: pd.DataFrame,
    demand_summary: pd.DataFrame,
    facility_summary: pd.DataFrame,
    audits: pd.DataFrame,
    determinism: pd.DataFrame,
    cid_flows: pd.DataFrame,
    cid_origins: pd.DataFrame,
):
    def metric_row(
        frame: pd.DataFrame, metric: str, **filters
    ) -> dict:
        selected = frame[frame["metric"] == metric]
        for column, value in filters.items():
            selected = selected[selected[column] == value]
        return selected.iloc[0].to_dict() if len(selected) else {}

    lines = [
        "# Inpatient Care Scenario Evaluation",
        "",
        "## Evaluation design",
        "",
        (
            f"The package contains {len(runs)} completed runs across "
            f"{runs['scenario'].nunique()} existing scenarios and "
            f"{runs['seed'].nunique()} seeds. Overflow runs estimate latent "
            "capacity deficits; queue runs enforce bed limits."
        ),
        "",
        "## Integrity and reproducibility",
        "",
        (
            f"- Integrity checks passed: "
            f"{int(audits['passed'].sum())}/{len(audits)}."
        ),
        (
            f"- Specialized CSV determinism checks passed: "
            f"{int(determinism['passed'].sum())}/{len(determinism)}."
            if not determinism.empty
            else "- Determinism audit was not available."
        ),
        "",
        "## Scenario results",
        "",
        "| Scenario | Coverage mean [P05–P95] | Peak overflow mean [P05–P95] | Final queue mean [P05–P95] | Mean delay [P05–P95] |",
        "|---|---:|---:|---:|---:|",
    ]
    for scenario in SCENARIOS:
        coverage = _scenario_metric(
            scenario_summary, scenario, "admission_coverage"
        )
        overflow = _scenario_metric(
            scenario_summary, scenario, "peak_overflow"
        )
        queue = _scenario_metric(
            scenario_summary, scenario, "final_queue"
        )
        delay = _scenario_metric(
            scenario_summary, scenario, "mean_admission_delay"
        )
        lines.append(
            f"| {scenario} | {coverage.get('mean', np.nan):.4f} "
            f"[{coverage.get('p05', np.nan):.4f}–"
            f"{coverage.get('p95', np.nan):.4f}] | "
            f"{overflow.get('mean', np.nan):.1f} "
            f"[{overflow.get('p05', np.nan):.1f}–"
            f"{overflow.get('p95', np.nan):.1f}] | "
            f"{queue.get('mean', np.nan):.1f} "
            f"[{queue.get('p05', np.nan):.1f}–"
            f"{queue.get('p95', np.nan):.1f}] | "
            f"{delay.get('mean', np.nan):.2f} "
            f"[{delay.get('p05', np.nan):.2f}–"
            f"{delay.get('p95', np.nan):.2f}] |"
        )
    lines.extend(
        [
            "",
            "## Paired policy interpretation",
            "",
        ]
    )
    for family in POLICY_PAIRS:
        family_rows = paired_summary[
            paired_summary["family"] == family
        ]
        coverage = family_rows[
            family_rows["metric"] == "admission_coverage"
        ]
        queue = family_rows[family_rows["metric"] == "final_queue"]
        overflow = family_rows[
            family_rows["metric"] == "peak_overflow"
        ]
        if len(coverage):
            lines.append(
                f"- **{family}:** queue minus overflow mean coverage "
                f"difference {coverage.iloc[0]['mean_difference']:.3f}; "
                f"final queue difference "
                f"{queue.iloc[0]['mean_difference']:.1f}; peak overflow "
                f"difference {overflow.iloc[0]['mean_difference']:.1f}."
            )

    reference_queue = runs[runs["scenario"] == "ReferenceDemandQueue"]
    high_queue = runs[runs["scenario"] == "HighDemandQueue"]
    psychiatry = demand_strata[
        demand_strata["specialty"] == "Psiquiatria"
    ]
    psychiatry_by_run = (
        psychiatry.groupby(["scenario", "seed"])[["demand", "admitted"]]
        .sum()
        .reset_index()
    )
    psychiatry_by_run["coverage"] = (
        psychiatry_by_run["admitted"] / psychiatry_by_run["demand"]
    )
    high_psychiatry = psychiatry_by_run[
        psychiatry_by_run["scenario"] == "HighDemandQueue"
    ]
    two_facility_psychiatry = psychiatry_by_run[
        psychiatry_by_run["scenario"] == "TwoFacilityQueue"
    ]
    lines.extend(
        [
            "",
            "## Demand and facility comparisons",
            "",
            (
                "- Moving from reference to high demand under queue policy "
                f"reduced mean admission coverage from "
                f"{reference_queue['admission_coverage'].mean():.4f} to "
                f"{high_queue['admission_coverage'].mean():.4f}; mean final "
                f"queue increased from "
                f"{reference_queue['final_queue'].mean():.1f} to "
                f"{high_queue['final_queue'].mean():.1f} patients."
            ),
            (
                "- Restricting the comparison to Psychiatry, the "
                f"one-facility high-demand queue admitted "
                f"{high_psychiatry['coverage'].mean():.4f} of demand on "
                f"average; the fixed two-facility allocation admitted "
                f"{two_facility_psychiatry['coverage'].mean():.4f}."
            ),
            "",
            "| Policy | Facility | Mean admitted | Mean coverage | Mean delay | Mean excess bed-steps |",
            "|---|---|---:|---:|---:|---:|",
        ]
    )
    for scenario in ("TwoFacilityOverflow", "TwoFacilityQueue"):
        for hospital in ("HEPA", "Hospital Santa Ana"):
            filters = {"scenario": scenario, "hospital": hospital}
            admitted = metric_row(
                facility_summary, "admitted", **filters
            )
            coverage = metric_row(
                facility_summary,
                "targeted_admission_coverage",
                **filters,
            )
            delay = metric_row(
                facility_summary, "mean_admission_delay", **filters
            )
            excess = metric_row(
                facility_summary, "excess_bed_steps", **filters
            )
            lines.append(
                f"| {SCENARIOS[scenario]['policy']} | {hospital} | "
                f"{admitted.get('mean', np.nan):.1f} | "
                f"{coverage.get('mean', np.nan):.4f} | "
                f"{delay.get('mean', np.nan):.2f} | "
                f"{excess.get('mean', np.nan):.1f} |"
            )

    lines.extend(
        [
            "",
            "## Specialty and payer results under queue policy",
            "",
            "| Scenario | Specialty | Payer | Mean coverage | Mean final waiting | Mean delay |",
            "|---|---|---|---:|---:|---:|",
        ]
    )
    queue_strata = demand_strata[
        demand_strata["policy"] == "queue"
    ][["scenario", "specialty", "bed_type", "payer"]].drop_duplicates()
    for stratum in queue_strata.sort_values(
        ["scenario", "specialty", "payer"]
    ).itertuples(index=False):
        filters = {
            "scenario": stratum.scenario,
            "specialty": stratum.specialty,
            "bed_type": stratum.bed_type,
            "payer": stratum.payer,
        }
        coverage = metric_row(
            demand_summary, "admission_coverage", **filters
        )
        waiting = metric_row(
            demand_summary, "final_waiting", **filters
        )
        delay = metric_row(
            demand_summary, "mean_admission_delay", **filters
        )
        lines.append(
            f"| {stratum.scenario} | {stratum.specialty} | "
            f"{stratum.payer} | {coverage.get('mean', np.nan):.4f} | "
            f"{waiting.get('mean', np.nan):.1f} | "
            f"{delay.get('mean', np.nan):.2f} |"
        )

    lines.extend(
        [
            "",
            "## Spatial and CID interpretation",
            "",
        ]
    )
    if cid_origins.empty:
        lines.append("- No CID routing runs were available.")
    else:
        destination_rows = []
        destination_total = cid_flows["admitted"].sum()
        seed_count = cid_flows["seed"].nunique()
        for hospital, group in cid_flows.groupby("hospital"):
            admitted = group["admitted"].sum()
            destination_rows.append(
                (
                    hospital,
                    admitted / seed_count,
                    admitted / destination_total,
                    weighted_mean(group["mean_delay"], group["admitted"]),
                    weighted_mean(
                        group["mean_distance_km"], group["admitted"]
                    ),
                )
            )
        lines.extend(
            [
                (
                    f"- CID routing evaluated "
                    f"{cid_origins['origin_region'].nunique()} origin regions "
                    f"and {cid_origins['cid'].nunique()} configured CID codes."
                ),
                (
                    f"- Population-weighted mean admission distance: "
                    f"{weighted_mean(cid_origins['mean_distance_km'], cid_origins['admitted']):.2f} km."
                ),
                (
                    f"- Population-weighted mean admission delay: "
                    f"{weighted_mean(cid_origins['mean_delay'], cid_origins['admitted']):.2f} steps."
                ),
                "",
                "| Destination | Mean admissions per seed | Share | Mean delay | Mean distance (km) |",
                "|---|---:|---:|---:|---:|",
            ]
        )
        for hospital, admitted, share, delay, distance in sorted(
            destination_rows, key=lambda row: row[1], reverse=True
        ):
            lines.append(
                f"| {hospital} | {admitted:.1f} | {share:.3f} | "
                f"{delay:.2f} | {distance:.2f} |"
            )
    lines.extend(
        [
            "",
            "## Limitations and provenance",
            "",
            "- Per-step demand and length of stay are stochastic; seed 0 is not treated as an uncertainty estimate.",
            "- Patients still admitted or waiting at step 11 are horizon-censored.",
            "- The two-facility demand is preassigned and does not represent dynamic load balancing.",
            "- Overflow is an unconstrained counterfactual, not an operational admission policy.",
            "- Santa Ana's Psychiatry capacity is synthetic.",
            "- CID demand and CID-to-specialty mappings are synthetic configuration and are not clinical inference.",
            "- The original per-step distributions and random seed were not retained, so exact published timing is not reproducible.",
            "- Capacity data are derived from the January 2024 source imported from LODUS-Health commit `78946ad0`.",
            "",
            "## Files",
            "",
            "CSV tables are stored beside this report. Interactive plots are under `plots/`.",
            "",
        ]
    )
    (analysis_path / "report.md").write_text(
        "\n".join(lines), encoding="utf8"
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--results-root",
        type=Path,
        default=Path("results/inpatient_care"),
    )
    parser.add_argument(
        "--expected-seeds",
        default="0-29",
        help="Expected seeds used for completeness auditing.",
    )
    parser.add_argument(
        "--allow-audit-failures",
        action="store_true",
    )
    args = parser.parse_args()
    discovered = discover_runs(args.results_root)
    if not discovered:
        raise FileNotFoundError(
            f"No completed inpatient care runs found in {args.results_root}"
        )

    run_rows = []
    bed_rows_all = []
    demand_rows_all = []
    facility_rows_all = []
    time_rows_all = []
    cid_flows_all = []
    cid_origins_all = []
    cid_queue_all = []
    audit_rows = []
    demand_audit_rows = []
    for scenario_id, seed, run_path, metadata in discovered:
        summary, frames = summarize_run(
            scenario_id, seed, run_path, metadata
        )
        run_rows.append(summary)
        pools = bed_pool_rows(scenario_id, seed, frames)
        bed_rows_all.extend(pools)
        demand_rows_all.extend(
            demand_strata_rows(scenario_id, seed, frames)
        )
        facility_rows_all.extend(
            facility_rows(scenario_id, seed, pools, frames["events"])
        )
        time_rows_all.extend(
            time_step_rows(scenario_id, seed, frames)
        )
        cid_flows, cid_origins, cid_queue = cid_rows(
            scenario_id, seed, frames["events"]
        )
        cid_flows_all.extend(cid_flows)
        cid_origins_all.extend(cid_origins)
        cid_queue_all.extend(cid_queue)
        audits, demand_audits = audit_run(
            scenario_id, seed, summary, frames
        )
        audit_rows.extend(audits)
        demand_audit_rows.extend(demand_audits)

    runs = pd.DataFrame(run_rows).sort_values(["scenario", "seed"])
    bed_pools = pd.DataFrame(bed_rows_all)
    demand_strata = pd.DataFrame(demand_rows_all)
    facilities = pd.DataFrame(facility_rows_all)
    time_steps = pd.DataFrame(time_rows_all)
    cid_flows = pd.DataFrame(cid_flows_all)
    cid_origins = pd.DataFrame(cid_origins_all)
    cid_queue = pd.DataFrame(cid_queue_all)
    audits = pd.DataFrame(audit_rows)
    demand_audits = pd.DataFrame(demand_audit_rows)

    expected_seeds = set(parse_seeds(args.expected_seeds))
    completeness_rows = []
    for scenario_id in SCENARIOS:
        observed = set(
            runs.loc[runs["scenario"] == scenario_id, "seed"].astype(int)
        )
        completeness_rows.append(
            {
                "scenario": scenario_id,
                "seed": -1,
                "check": "seed_coverage",
                "scope": "batch",
                "passed": observed == expected_seeds,
                "observed": ",".join(map(str, sorted(observed))),
                "expected": ",".join(map(str, sorted(expected_seeds))),
                "difference": len(observed) - len(expected_seeds),
                "detail": "",
            }
        )
    audits = pd.concat(
        [audits, pd.DataFrame(completeness_rows)], ignore_index=True
    )

    determinism_path = args.results_root / "determinism_audit.csv"
    determinism = (
        pd.read_csv(determinism_path)
        if determinism_path.is_file()
        else pd.DataFrame()
    )
    if not determinism.empty:
        determinism["passed"] = determinism["passed"].astype(str).str.lower().map(
            {"true": True, "false": False}
        ).fillna(determinism["passed"].astype(bool))
        audits = pd.concat(
            [
                audits,
                pd.DataFrame(
                    [
                        {
                            "scenario": "batch",
                            "seed": -1,
                            "check": "specialized_csv_determinism",
                            "scope": row["file"],
                            "passed": bool(row["passed"]),
                            "observed": row["repeated_sha256"],
                            "expected": row["reference_sha256"],
                            "difference": None,
                            "detail": "",
                        }
                        for _, row in determinism.iterrows()
                    ]
                ),
            ],
            ignore_index=True,
        )

    analysis_path = args.results_root / "analysis"
    analysis_path.mkdir(parents=True, exist_ok=True)
    scenario_summary = long_distribution_summary(
        runs, ["scenario", "family", "policy"], RUN_METRICS
    )
    paired_runs, paired_summary = paired_policy_tables(runs)
    bed_summary = (
        long_distribution_summary(
            bed_pools,
            ["scenario", "hospital", "specialty", "bed_type", "payer"],
            [
                "peak_utilization",
                "occupied_bed_steps",
                "available_bed_steps",
                "excess_bed_steps",
                "peak_overflow",
                "steps_full",
                "queue_patient_steps_for_preferred_demand",
                "peak_queue_for_preferred_demand",
                "mean_admission_delay",
                "median_admission_delay",
                "maximum_admission_delay",
                "mean_admission_distance_km",
            ],
        )
        if not bed_pools.empty
        else pd.DataFrame()
    )
    demand_summary = long_distribution_summary(
        demand_strata,
        ["scenario", "specialty", "bed_type", "payer"],
        [
            "demand",
            "admitted",
            "admission_coverage",
            "discharged",
            "inpatients_end",
            "final_waiting",
            "peak_occupancy",
            "occupancy_end",
            "occupied_bed_steps",
            "available_bed_steps",
            "excess_bed_steps",
            "peak_overflow",
            "steps_above_capacity",
            "queue_patient_steps",
            "peak_queue",
            "mean_admission_delay",
            "median_admission_delay",
            "maximum_admission_delay",
            "rerouted",
            "mean_admission_distance_km",
        ],
    )
    facility_summary = (
        long_distribution_summary(
            facilities,
            ["scenario", "hospital"],
            [
                "admitted",
                "targeted_admission_coverage",
                "discharged",
                "inpatients_end",
                "occupied_bed_steps",
                "available_bed_steps",
                "excess_bed_steps",
                "queue_patient_steps_for_preferred_demand",
                "mean_admission_delay",
                "median_admission_delay",
                "maximum_admission_delay",
                "mean_admission_distance_km",
            ],
        )
        if not facilities.empty
        else pd.DataFrame()
    )
    cid_flow_summary = aggregate_cid_flows(cid_flows)
    time_summary = aggregate_time_steps(time_steps)
    audit_summary = (
        audits.groupby(["check"])["passed"]
        .agg(total="size", passed="sum")
        .reset_index()
    )
    audit_summary["failed"] = (
        audit_summary["total"] - audit_summary["passed"]
    )

    outputs = {
        "scenario_seed_summary.csv": runs,
        "scenario_summary.csv": scenario_summary,
        "paired_policy_runs.csv": paired_runs,
        "paired_policy_summary.csv": paired_summary,
        "bed_pool_runs.csv": bed_pools,
        "bed_pool_summary.csv": bed_summary,
        "demand_strata_runs.csv": demand_strata,
        "demand_strata_summary.csv": demand_summary,
        "facility_runs.csv": facilities,
        "facility_summary.csv": facility_summary,
        "time_step_runs.csv": time_steps,
        "time_step_summary.csv": time_summary,
        "cid_flow_runs.csv": cid_flows,
        "cid_flow_summary.csv": cid_flow_summary,
        "cid_origin_runs.csv": cid_origins,
        "cid_queue_burden.csv": cid_queue,
        "integrity_audit.csv": audits,
        "integrity_summary.csv": audit_summary,
        "demand_conservation.csv": demand_audits,
    }
    for filename, frame in outputs.items():
        frame.to_csv(analysis_path / filename, index=False)

    _write_plots(
        analysis_path,
        runs,
        bed_pools,
        cid_origins,
        time_summary,
    )
    write_report(
        analysis_path,
        runs,
        scenario_summary,
        paired_summary,
        demand_strata,
        demand_summary,
        facility_summary,
        audits,
        determinism,
        cid_flows,
        cid_origins,
    )
    failures = int((~audits["passed"].astype(bool)).sum())
    print(
        f"Wrote inpatient care analysis to {analysis_path}; "
        f"integrity failures={failures}"
    )
    return int(failures > 0 and not args.allow_audit_failures)


if __name__ == "__main__":
    raise SystemExit(main())
