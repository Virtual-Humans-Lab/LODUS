"""Resumable compatibility and 14-day shelter experiment batches."""

from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
import json
from pathlib import Path
import shutil
import subprocess
import sys

import pandas as pd


REPO_ROOT = Path(__file__).resolve().parent
COMPATIBILITY_EXPERIMENTS = [
    "initial_test",
    "load_shelters_test",
    "census_areas_test",
    "census_shelters_v2_test",
    "census_5m30_shelters_v3_test",
    "census_5m30_shelters_v3_daily_1%_test",
    "census_5m30_shelters_v3_daily_1%_reallocate_test",
]
BASE = "shelter_tests/census_5m30_shelters_v3_daily_1%_test"
REALLOCATE_BASE = (
    "shelter_tests/census_5m30_shelters_v3_daily_1%_reallocate_test"
)


def research_catalog() -> dict[str, tuple[str, dict]]:
    common = {"simulation_parameters": {"total_cycles": 14}}
    catalog: dict[str, tuple[str, dict]] = {
        "v3_reference": (BASE, common),
        "v3_reference_reallocate": (REALLOCATE_BASE, common),
    }
    for mode, label in [(0, "fixed_initial"), (1, "remaining_demand")]:
        catalog[f"evacuation_{label}"] = (
            REALLOCATE_BASE,
            {
                **common,
                "shelter_plugin": {"evacuation_mode": mode},
            },
        )
    for rate in [0.005, 0.01, 0.02, 0.05]:
        catalog[f"response_{rate:g}"] = (
            REALLOCATE_BASE,
            {
                **common,
                "shelter_plugin": {"daily_evacuation_rate": rate},
            },
        )
    for multiplier in [0.25, 0.5, 1.0]:
        catalog[f"demand_{multiplier:g}x"] = (
            REALLOCATE_BASE,
            {
                **common,
                "shelter_plugin": {"exposure_multiplier": multiplier},
            },
        )
    for multiplier in [0.5, 1, 2, 5, 15]:
        catalog[f"capacity_{multiplier:g}x"] = (
            REALLOCATE_BASE,
            {
                **common,
                "shelter_plugin": {"capacity_multiplier": multiplier},
            },
        )
    for mode in ["empty", "half_capacity", "observed"]:
        catalog[f"occupancy_{mode}"] = (
            REALLOCATE_BASE,
            {
                **common,
                "shelter_plugin": {"initial_occupancy_mode": mode},
            },
        )
    for scale in [500, 1000, 3000]:
        catalog[f"levy_{scale}m"] = (
            REALLOCATE_BASE,
            {
                **common,
                "levy_walk_plugin": {"distribution_scale": scale},
            },
        )
    for failure in ["largest", "top_10_percent_capacity", "region:Humaitá"]:
        label = failure.replace(":", "_").replace("á", "a")
        for reallocate, base in [
            ("without_reallocation", BASE),
            ("with_reallocation", REALLOCATE_BASE),
        ]:
            catalog[f"failure_{label}_{reallocate}"] = (
                base,
                {
                    **common,
                    "shelter_plugin": {"failure_scenario": failure},
                },
            )
    return catalog


def parse_seed_spec(value: str) -> list[int]:
    seeds: list[int] = []
    for part in value.split(","):
        if "-" in part:
            start, end = map(int, part.split("-", 1))
            seeds.extend(range(start, end + 1))
        else:
            seeds.append(int(part))
    return sorted(set(seeds))


def completed(run_path: Path) -> bool:
    metadata = run_path / "run_metadata.json"
    if not metadata.is_file():
        return False
    try:
        return json.loads(metadata.read_text(encoding="utf-8")).get(
            "status"
        ) == "complete"
    except (OSError, json.JSONDecodeError):
        return False


def preserve_partial_run(run_path: Path) -> None:
    if not run_path.exists():
        return
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    run_path.rename(
        run_path.with_name(f"{run_path.name}.partial-{timestamp}")
    )


def run_one(
    scenario: str,
    experiment: str,
    overrides: dict,
    seed: int,
    force: bool,
    results_root: Path,
) -> dict:
    run_name = f"shelter-{scenario}-seed{seed}"
    run_path = results_root / scenario / f"seed_{seed:03d}"
    if completed(run_path) and not force:
        status = "resumed"
    else:
        preserve_partial_run(run_path)
        temporary_name = f"shelter_batch/{scenario}/seed_{seed:03d}"
        temporary_path = REPO_ROOT / "output_logs" / temporary_name
        preserve_partial_run(temporary_path)
        command = [
            sys.executable,
            str(REPO_ROOT / "shelter_simulator.py"),
            "--e", experiment,
            "--n", temporary_name,
            "--seed", str(seed),
            "--no-shelter-png",
        ]
        if overrides:
            command.extend([
                "--overrides-json",
                json.dumps(overrides, ensure_ascii=False),
            ])
        result = subprocess.run(
            command, cwd=REPO_ROOT, text=True, capture_output=True
        )
        run_path.parent.mkdir(parents=True, exist_ok=True)
        if result.returncode == 0 and completed(temporary_path):
            shutil.move(str(temporary_path), str(run_path))
            status = "complete"
        else:
            if temporary_path.exists():
                shutil.move(str(temporary_path), str(run_path))
            else:
                run_path.mkdir(parents=True, exist_ok=True)
            (run_path / "run.log").write_text(
                result.stdout + "\n--- STDERR ---\n" + result.stderr,
                encoding="utf-8",
            )
            return {
                "Scenario": scenario, "Seed": seed, "Run Name": run_name,
                "Status": "failed", "Path": str(run_path),
                "Error": result.stderr[-2000:],
            }
    return {
        "Scenario": scenario,
        "Seed": seed,
        "Run Name": run_name,
        "Status": status,
        "Path": str(run_path),
        **summarize_run(run_path),
    }


def summarize_run(run_path: Path) -> dict:
    data_path = run_path / "data_frames"
    metadata = json.loads(
        (run_path / "run_metadata.json").read_text(encoding="utf-8")
    )
    steps = pd.read_csv(data_path / "shelter_step.csv", sep=";")
    cycles = pd.read_csv(data_path / "shelter_cycle.csv", sep=";")
    groups = pd.read_csv(data_path / "shelter_group_step.csv", sep=";")
    last = steps.sort_values("Simulation Step").iloc[-1]
    last_groups = groups[
        groups["Simulation Step"] == groups["Simulation Step"].max()
    ]
    sheltered_rates = last_groups.loc[
        last_groups["Status"] == "sheltered", "Rate Within Group"
    ]
    return {
        "Coverage": (
            last["Sheltered"] / metadata["mapped_exposure"]
            if metadata["mapped_exposure"] else 0
        ),
        "Unresolved Demand": int(last["In Danger"]),
        "Peak Waitlist": int(steps["Waitlist"].max()),
        "Waiting Person Steps": int(steps["Waitlist"].sum()),
        "Peak Utilization": float(steps["Utilization"].max()),
        "Mean Distance Km": float(cycles["Mean Distance Km"].mean()),
        "P95 Distance Km": float(cycles["P95 Distance Km"].max()),
        "Equity Gap": (
            float(sheltered_rates.max() - sheltered_rates.min())
            if not sheltered_rates.empty else 0
        ),
        "Runtime Seconds": metadata["runtime_seconds"],
        "Peak Memory KiB": metadata["peak_memory_kib"],
        "Error": "",
    }


def selected_catalog(args) -> dict[str, tuple[str, dict]]:
    if args.catalog == "compatibility":
        catalog = {
            name: (f"shelter_tests/{name}", {})
            for name in COMPATIBILITY_EXPERIMENTS
        }
    else:
        catalog = research_catalog()
    if args.scenario:
        catalog = {
            name: value for name, value in catalog.items()
            if any(pattern in name for pattern in args.scenario)
        }
    if not catalog:
        raise ValueError("scenario filter selected no experiments")
    return catalog


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--catalog", choices=["compatibility", "research"],
        default="compatibility",
    )
    parser.add_argument(
        "--seeds", default=None,
        help="Comma/range specification; defaults to 0 for compatibility, 0-4 research",
    )
    parser.add_argument(
        "--confirmed", action="store_true",
        help="Use paired seeds 0-29 for confirmed comparisons",
    )
    parser.add_argument("--scenario", action="append")
    parser.add_argument("--jobs", type=int, default=1)
    parser.add_argument("--force", action="store_true")
    parser.add_argument(
        "--results-root", type=Path, default=Path("results/shelter")
    )
    parser.add_argument("--summary", type=Path, default=None)
    args = parser.parse_args()
    seeds = (
        list(range(30)) if args.confirmed
        else parse_seed_spec(args.seeds)
        if args.seeds
        else ([0] if args.catalog == "compatibility" else list(range(5)))
    )
    tasks = [
        (
            scenario, experiment, overrides, seed, args.force,
            args.results_root,
        )
        for scenario, (experiment, overrides) in selected_catalog(args).items()
        for seed in seeds
    ]
    summary = args.summary or args.results_root / "summary.csv"
    existing = (
        pd.read_csv(summary).to_dict("records")
        if summary.is_file()
        else []
    )
    rows = {
        (str(row["Scenario"]), int(row["Seed"])): row
        for row in existing
    }
    with ThreadPoolExecutor(max_workers=max(1, args.jobs)) as executor:
        futures = [executor.submit(run_one, *task) for task in tasks]
        for future in as_completed(futures):
            row = future.result()
            rows[(row["Scenario"], int(row["Seed"]))] = row
            print(row["Run Name"], row["Status"])
            summary.parent.mkdir(parents=True, exist_ok=True)
            pd.DataFrame(rows.values()).sort_values(
                ["Scenario", "Seed"]
            ).to_csv(summary, index=False)


if __name__ == "__main__":
    main()
