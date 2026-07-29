"""Run and resume the core dialysis resilience experiment catalog."""

from __future__ import annotations

import argparse
import csv
from datetime import datetime, timezone
import json
from pathlib import Path
import shutil
import subprocess
import sys

import pandas as pd


REPO_ROOT = Path(__file__).resolve().parent
CORE_SCENARIOS = [
    "dialysis_core/K00_ReducedReference",
    "dialysis_core/K01_ReducedModerate",
    "dialysis_core/K02_MoinhosNoRecovery",
    "dialysis_core/K03_MoinhosFastRecovery",
    "dialysis_core/K04_HistoricalClinicFlood",
    "dialysis_core/K05_SyntheticETAFlood",
    "dialysis_core/K06_CombinedMoinhosMenino",
    "dialysis_core/K07_ReducedAboveCapacity",
    "dialysis_core/K08_HighCapacityClinicFailure",
    "dialysis_core/K09_MatchedLowCapacityFailures",
    "dialysis_core/K10_CompleteModerate",
    "dialysis_core/K11_CompleteCombined",
]
DEMAND_SCENARIOS = [
    "dialysis_sensitivity/ReducedLow",
    "dialysis_core/K01_ReducedModerate",
    "dialysis_sensitivity/ReducedNearCapacity",
    "dialysis_sensitivity/ReducedAtCapacity",
    "dialysis_core/K07_ReducedAboveCapacity",
    "dialysis_sensitivity/CompleteLow",
    "dialysis_core/K10_CompleteModerate",
    "dialysis_sensitivity/CompleteNearCapacity",
    "dialysis_sensitivity/CompleteAtCapacity",
    "dialysis_sensitivity/CompleteAboveCapacity",
]


def parse_seeds(value: str) -> list[int]:
    """Parse ``0-29`` or a comma-separated seed list."""
    seeds: list[int] = []
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


def is_complete(run_path: Path) -> bool:
    metadata_path = run_path / "run_metadata.json"
    if not metadata_path.is_file():
        return False
    try:
        metadata = json.loads(metadata_path.read_text(encoding="utf8"))
    except (OSError, json.JSONDecodeError):
        return False
    required = (
        run_path / "data_frames" / "dialysis_cycle.csv",
        run_path / "data_frames" / "dialysis_events.csv",
    )
    return metadata.get("status") == "complete" and all(
        path.is_file() for path in required
    )


def preserve_partial_run(run_path: Path) -> None:
    if not run_path.exists():
        return
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    preserved = run_path.with_name(f"{run_path.name}.partial-{timestamp}")
    run_path.rename(preserved)


def run_one(
    scenario: str,
    seed: int,
    results_root: Path,
    python_executable: str,
) -> dict:
    scenario_id = Path(scenario).name.split("_", 1)[0]
    run_path = results_root / scenario_id / f"seed_{seed:03d}"
    if is_complete(run_path):
        return {
            "scenario": scenario,
            "scenario_id": scenario_id,
            "seed": seed,
            "status": "skipped",
            "path": str(run_path),
        }

    preserve_partial_run(run_path)
    temporary_name = f"dialysis_batch/{scenario_id}/seed_{seed:03d}"
    temporary_path = REPO_ROOT / "output_logs" / temporary_name
    preserve_partial_run(temporary_path)
    command = [
        python_executable,
        str(REPO_ROOT / "sector_simulation.py"),
        "--e",
        scenario,
        "--n",
        temporary_name,
        "--seed",
        str(seed),
        "--no-dialysis-png",
    ]
    completed = subprocess.run(
        command,
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )
    run_path.parent.mkdir(parents=True, exist_ok=True)
    if completed.returncode == 0 and is_complete(temporary_path):
        shutil.move(str(temporary_path), str(run_path))
        status = "complete"
    else:
        run_path.mkdir(parents=True, exist_ok=True)
        failure = {
            "status": "failed",
            "scenario": scenario,
            "seed": seed,
            "return_code": completed.returncode,
            "command": command,
        }
        (run_path / "run_metadata.json").write_text(
            json.dumps(failure, indent=2),
            encoding="utf8",
        )
        status = "failed"
    (run_path / "run.log").write_text(
        completed.stdout + "\n--- STDERR ---\n" + completed.stderr,
        encoding="utf8",
    )
    return {
        "scenario": scenario,
        "scenario_id": scenario_id,
        "seed": seed,
        "status": status,
        "path": str(run_path),
    }


def write_summary(results_root: Path, records: list[dict]) -> None:
    records_by_path = {
        record["path"]: record.copy() for record in records
    }
    for metadata_path in results_root.glob(
        "K*/seed_*/run_metadata.json"
    ):
        run_path = metadata_path.parent
        if not is_complete(run_path):
            continue
        scenario_id = run_path.parent.name
        seed = int(run_path.name.removeprefix("seed_"))
        metadata = json.loads(metadata_path.read_text(encoding="utf8"))
        records_by_path[str(run_path)] = {
            "scenario": metadata.get("experiment"),
            "scenario_id": scenario_id,
            "seed": seed,
            "status": "complete",
            "path": str(run_path),
        }

    rows = []
    for record in records_by_path.values():
        if record["status"] not in {"complete", "skipped"}:
            rows.append(record.copy())
            continue
        run_path = Path(record["path"])
        cycle_path = run_path / "data_frames" / "dialysis_cycle.csv"
        cycle = pd.read_csv(cycle_path, sep=";", encoding="utf-8-sig")
        events = pd.read_csv(
            run_path / "data_frames" / "dialysis_events.csv",
            sep=";",
            encoding="utf-8-sig",
        )
        clinics = pd.read_csv(
            run_path / "data_frames" / "dialysis_clinic_step.csv",
            sep=";",
            encoding="utf-8-sig",
        )
        metadata = json.loads(
            (run_path / "run_metadata.json").read_text(encoding="utf8")
        )
        due = int(cycle["Due Demand"].sum())
        completed = int(cycle["Completed"].sum())
        admitted_events = events[events["Event"] == "admitted"]
        admitted_population = admitted_events["Population"].sum()
        row = record.copy()
        disabled_by_step = (
            clinics.assign(Disabled=1 - clinics["Enabled"])
            .groupby("Simulation Step")["Disabled"]
            .sum()
        )
        row.update(
            {
                "due_sessions": due,
                "admissions": int(cycle["Admissions"].sum()),
                "completed": completed,
                "coverage": completed / due if due else 1.0,
                "due_wait_patient_hours": int(
                    cycle["Due-Wait Patient-Hours"].sum()
                ),
                "overdue_end": int(cycle.iloc[-1]["Overdue End"]),
                "used_capacity": int(cycle["Used Capacity"].sum()),
                "available_capacity": int(
                    cycle["Available Capacity"].sum()
                ),
                "average_admission_distance_km": (
                    float(
                        (
                            admitted_events["Distance"]
                            * admitted_events["Population"]
                        ).sum()
                        / admitted_population
                    )
                    if admitted_population
                    else 0.0
                ),
                "disabled_clinic_hours": int(
                    (1 - clinics["Enabled"]).sum()
                ),
                "maximum_disabled_clinics": int(
                    disabled_by_step.max()
                ),
                "runtime_seconds": metadata.get("runtime_seconds"),
                "peak_memory_kib": metadata.get("peak_memory_kib"),
            }
        )
        rows.append(row)
    results_root.mkdir(parents=True, exist_ok=True)
    fieldnames = sorted({key for row in rows for key in row})
    with (results_root / "summary.csv").open(
        "w", encoding="utf8", newline=""
    ) as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--scenarios",
        nargs="*",
        default=None,
        help="Experiment names relative to experiments/, without .json.",
    )
    parser.add_argument(
        "--catalog",
        choices=["core", "demand", "all"],
        default="core",
        help="Built-in scenario catalog used when --scenarios is omitted.",
    )
    parser.add_argument(
        "--seeds",
        default="0-29",
        help="Seed list or inclusive range, for example 0-29 or 0,4,9.",
    )
    parser.add_argument(
        "--results-root",
        type=Path,
        default=REPO_ROOT / "results" / "dialysis",
    )
    parser.add_argument(
        "--python",
        default=sys.executable,
        help="Python executable used for sector_simulation.py.",
    )
    args = parser.parse_args()
    if args.scenarios is None:
        args.scenarios = {
            "core": CORE_SCENARIOS,
            "demand": DEMAND_SCENARIOS,
            "all": list(dict.fromkeys(CORE_SCENARIOS + DEMAND_SCENARIOS)),
        }[args.catalog]
    seeds = parse_seeds(args.seeds)
    records = []
    for scenario in args.scenarios:
        for seed in seeds:
            record = run_one(
                scenario,
                seed,
                args.results_root,
                args.python,
            )
            records.append(record)
            write_summary(args.results_root, records)
            print(
                f"{record['scenario_id']} seed={seed}: "
                f"{record['status']}"
            )
    manifest = {
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "scenarios": args.scenarios,
        "seeds": seeds,
        "records": records,
    }
    (args.results_root / "batch_manifest.json").write_text(
        json.dumps(manifest, indent=2),
        encoding="utf8",
    )
    return int(any(record["status"] == "failed" for record in records))


if __name__ == "__main__":
    raise SystemExit(main())
