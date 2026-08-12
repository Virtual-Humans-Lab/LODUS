from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from misc_scripts.run_popular_times_v2_production import (
    OUTPUT_LOGS,
    PROJECT_ROOT,
    TOTAL_CYCLES,
    _interval,
    _read_csv,
    _read_json,
    _relative_experiment_name,
    _write_csv,
    compress_raw_outputs,
)


DEFAULT_OUTPUT = OUTPUT_LOGS / "popular_times_v2_stage5"
STAGE4_RESULTS = (
    PROJECT_ROOT
    / "docs"
    / "results"
    / "popular_times_v2_stage4"
    / "production_runs.csv"
)
EXPECTED_RUNS = 12
SCENARIOS = (
    "13_levy_off_flood_both_reroute",
    "13_levy_on_flood_both_reroute",
    "94_levy_off_flood_both_reroute",
    "94_levy_on_flood_both_reroute",
)
CORE_METRICS = (
    "requested",
    "fulfilled",
    "unmet",
    "fulfillment_rate",
    "trips",
    "travelers",
    "travelers_per_capita",
    "traveler_distance",
    "distance_per_requested_visit",
    "mean_distance_per_traveler",
    "occupancy_person_hours",
    "occupancy_per_requested_visit",
    "peak_hourly_occupancy",
)
REROUTE_METRICS = (
    "reroute_events",
    "rerouted_requested",
    "rerouted_fulfilled",
    "rerouted_unmet",
    "reroute_traveler_distance",
    "mean_reroute_distance_per_traveler",
    "receiving_destinations",
    "peak_receiving_load",
)


@dataclass(frozen=True)
class RunSpec:
    scenario: str
    seed: int

    @property
    def run_name(self) -> str:
        return f"{self.scenario}-seed{self.seed}"

    @property
    def experiment(self) -> str:
        return f"popular_times_v2/stage5/{self.scenario}"

    @property
    def levy(self) -> bool:
        return "_levy_on_" in self.scenario

    @property
    def environment(self) -> str:
        return self.scenario.split("_", 1)[0]


def stage5_specs(
    seeds_13: Iterable[int] = range(5),
    seeds_94: Iterable[int] = range(5),
) -> list[RunSpec]:
    seeds = {"13": sorted(set(seeds_13)), "94": sorted(set(seeds_94))}
    specs = []
    for scenario in SCENARIOS:
        spec = RunSpec(scenario, 0)
        scenario_seeds = seeds[spec.environment] if spec.levy else [0]
        specs.extend(RunSpec(scenario, seed) for seed in scenario_seeds)
    return specs


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def completion_state(spec: RunSpec, output_root: Path) -> tuple[str, str]:
    run_path = output_root / spec.run_name
    metadata_path = run_path / "run_metadata.json"
    validation_path = run_path / "data_frames" / "popular_times_validation.json"
    if not metadata_path.exists() or not validation_path.exists():
        return "pending", "completion artifacts are missing"
    try:
        metadata = _read_json(metadata_path)
        validation = _read_json(validation_path)
    except (OSError, json.JSONDecodeError) as error:
        return "pending", f"completion artifacts are unreadable: {error}"
    expected = (
        metadata.get("status") == "complete"
        and metadata.get("experiment") == spec.experiment
        and int(metadata.get("seed", -1)) == spec.seed
        and int(metadata.get("simulation_parameters", {}).get("total_cycles", -1))
        == TOTAL_CYCLES
        and metadata.get("resolved_config", {})
        .get("popular_times_v2_plugin", {})
        .get("reroute_disabled_destinations")
        is True
    )
    if not expected:
        return "pending", "metadata does not match the Stage 5 run specification"
    if not validation.get("passed", False):
        return "invalid", "simulation completed but an invariant failed"
    return "complete", "validated completion artifacts found"


def _run_one(spec: RunSpec, output_root: Path, compress_raw: bool) -> dict[str, Any]:
    run_path = output_root / spec.run_name
    run_path.mkdir(parents=True, exist_ok=True)
    command = [
        sys.executable,
        str(PROJECT_ROOT / "sector_simulation.py"),
        "--e",
        spec.experiment,
        "--n",
        _relative_experiment_name(run_path),
        "--seed",
        str(spec.seed),
    ]
    environment = os.environ.copy()
    environment["PYTHONUNBUFFERED"] = "1"
    environment["MPLCONFIGDIR"] = str(run_path / ".matplotlib")
    started = _utc_now()
    with (run_path / "console.log").open("w", encoding="utf8") as log:
        completed = subprocess.run(
            command,
            cwd=PROJECT_ROOT,
            env=environment,
            stdout=log,
            stderr=subprocess.STDOUT,
            check=False,
        )
    state, detail = completion_state(spec, output_root)
    if completed.returncode and state == "pending":
        state = "failed"
        detail = f"simulation exited with code {completed.returncode}"
    compressed_files = []
    if state in {"complete", "invalid"} and compress_raw:
        compressed_files = compress_raw_outputs(run_path)
    return {
        **asdict(spec),
        "run_name": spec.run_name,
        "status": state,
        "detail": detail,
        "returncode": completed.returncode,
        "started_at_utc": started,
        "finished_at_utc": _utc_now(),
        "compressed_files": compressed_files,
    }


def _write_manifest(path: Path, runs: dict[str, dict[str, Any]]) -> None:
    counts = defaultdict(int)
    for row in runs.values():
        counts[row["status"]] += 1
    payload = {
        "stage": 5,
        "expected_runs": EXPECTED_RUNS,
        "total_cycles": TOTAL_CYCLES,
        "updated_at_utc": _utc_now(),
        "status_counts": dict(sorted(counts.items())),
        "runs": [runs[key] for key in sorted(runs)],
    }
    temporary = path.with_suffix(".tmp")
    temporary.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf8"
    )
    temporary.replace(path)


def execute_runs(
    specs: list[RunSpec],
    output_root: Path,
    workers: int,
    rerun_invalid: bool,
    compress_raw: bool,
) -> list[dict[str, Any]]:
    manifest_path = output_root / "stage5_manifest.json"
    all_rows: dict[str, dict[str, Any]] = {}
    if manifest_path.exists():
        try:
            all_rows = {
                row["run_name"]: row
                for row in _read_json(manifest_path).get("runs", [])
            }
        except (OSError, json.JSONDecodeError, KeyError):
            all_rows = {}

    queued = []
    for spec in specs:
        state, detail = completion_state(spec, output_root)
        if state == "complete" or (state == "invalid" and not rerun_invalid):
            all_rows[spec.run_name] = {
                **asdict(spec),
                "run_name": spec.run_name,
                "status": state,
                "detail": detail,
                "compressed_files": (
                    compress_raw_outputs(output_root / spec.run_name)
                    if compress_raw
                    else []
                ),
            }
            print(f"[resume] {spec.run_name}: {state}", flush=True)
        else:
            queued.append(spec)
            all_rows[spec.run_name] = {
                **asdict(spec),
                "run_name": spec.run_name,
                "status": "queued",
                "detail": detail,
            }
    _write_manifest(manifest_path, all_rows)

    completed_rows = []
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {}
        for index, spec in enumerate(queued, start=1):
            print(f"[queue {index}/{len(queued)}] {spec.run_name}", flush=True)
            all_rows[spec.run_name]["status"] = "running"
            futures[pool.submit(_run_one, spec, output_root, compress_raw)] = spec
        _write_manifest(manifest_path, all_rows)
        for index, future in enumerate(as_completed(futures), start=1):
            spec = futures[future]
            try:
                row = future.result()
            except Exception as error:
                row = {
                    **asdict(spec),
                    "run_name": spec.run_name,
                    "status": "failed",
                    "detail": repr(error),
                    "finished_at_utc": _utc_now(),
                }
            all_rows[spec.run_name] = row
            completed_rows.append(row)
            print(
                f"[done {index}/{len(queued)}] {spec.run_name}: {row['status']}",
                flush=True,
            )
            _write_manifest(manifest_path, all_rows)
    return completed_rows


def collect_run(spec: RunSpec, output_root: Path):
    run_path = output_root / spec.run_name
    data_path = run_path / "data_frames"
    metadata = _read_json(run_path / "run_metadata.json")
    validation = _read_json(data_path / "popular_times_validation.json")
    population = int(validation["initial_population"])
    study = metadata["resolved_config"]["popular_times_v2_stage5"]

    occupancy_by_type: dict[str, float] = defaultdict(float)
    peak_by_type: dict[str, float] = defaultdict(float)
    hourly_occupancy: dict[int, float] = defaultdict(float)
    for row in _read_csv(data_path / "popular_times_step_type.csv"):
        node_type = row["node_type"]
        occupancy = float(row["destination_occupancy"])
        occupancy_by_type[node_type] += occupancy
        peak_by_type[node_type] = max(peak_by_type[node_type], occupancy)
        hourly_occupancy[int(row["simulation_step"])] += occupancy

    receiver_rows = []
    peak_receiving_by_type: dict[str, float] = defaultdict(float)
    receiving_destinations_by_type: dict[str, set[str]] = defaultdict(set)
    for row in _read_csv(data_path / "popular_times_rerouting_summary.csv"):
        node_type = row["node_type"]
        peak = float(row["peak_receiving_load"])
        peak_receiving_by_type[node_type] = max(
            peak_receiving_by_type[node_type], peak
        )
        receiving_destinations_by_type[node_type].add(row["receiving_destination"])
        receiver_rows.append(
            {
                "scenario": spec.scenario,
                "levy": spec.levy,
                "seed": spec.seed,
                **row,
            }
        )

    type_rows = []
    for row in _read_csv(data_path / "popular_times_summary.csv"):
        node_type = row["node_type"]
        requested = float(row["requested"])
        travelers = float(row["travelers_started"])
        travel_distance = float(row["travel_distance"])
        type_rows.append(
            {
                "scenario": spec.scenario,
                "levy": spec.levy,
                "seed": spec.seed,
                "node_type": node_type,
                "population": population,
                "requested": requested,
                "fulfilled": float(row["fulfilled"]),
                "unmet": float(row["unmet"]),
                "fulfillment_rate": float(row["fulfillment_rate"]),
                "trips": float(row["visit_starts"]),
                "travelers": travelers,
                "travelers_per_capita": travelers / population,
                "traveler_distance": travel_distance,
                "distance_per_requested_visit": travel_distance / requested,
                "mean_distance_per_traveler": travel_distance / travelers,
                "occupancy_person_hours": occupancy_by_type[node_type],
                "occupancy_per_requested_visit": occupancy_by_type[node_type] / requested,
                "peak_hourly_occupancy": peak_by_type[node_type],
                "reroute_events": float(row["reroute_events"]),
                "rerouted_requested": float(row["rerouted_requested"]),
                "rerouted_fulfilled": float(row["rerouted_fulfilled"]),
                "rerouted_unmet": float(row["rerouted_unmet"]),
                "reroute_traveler_distance": float(row["reroute_traveler_distance"]),
                "mean_reroute_distance_per_traveler": float(row["mean_reroute_distance_per_traveler"]),
                "receiving_destinations": len(receiving_destinations_by_type[node_type]),
                "peak_receiving_load": peak_receiving_by_type[node_type],
            }
        )

    additive = (
        "requested", "fulfilled", "unmet", "trips", "travelers",
        "traveler_distance", "occupancy_person_hours", "reroute_events",
        "rerouted_requested", "rerouted_fulfilled", "rerouted_unmet",
        "reroute_traveler_distance", "receiving_destinations",
    )
    totals = {key: sum(float(row[key]) for row in type_rows) for key in additive}
    requested = totals["requested"]
    travelers = totals["travelers"]
    rerouted_fulfilled = totals["rerouted_fulfilled"]
    run_row = {
        "scenario": spec.scenario,
        "environment": study["environment"],
        "levy": bool(study["levy"]),
        "flood": study["flood"],
        "adaptation": study["adaptation"],
        "seed": spec.seed,
        "cycles": metadata["simulation_parameters"]["total_cycles"],
        "population": population,
        **totals,
        "fulfillment_rate": totals["fulfilled"] / requested,
        "travelers_per_capita": travelers / population,
        "distance_per_requested_visit": totals["traveler_distance"] / requested,
        "mean_distance_per_traveler": totals["traveler_distance"] / travelers,
        "occupancy_per_requested_visit": totals["occupancy_person_hours"] / requested,
        "peak_hourly_occupancy": max(hourly_occupancy.values(), default=0.0),
        "mean_reroute_distance_per_traveler": (
            totals["reroute_traveler_distance"] / rerouted_fulfilled
            if rerouted_fulfilled else 0.0
        ),
        "peak_receiving_load": max(
            (float(row["peak_receiving_load"]) for row in type_rows), default=0.0
        ),
        "runtime_seconds": float(metadata["runtime_seconds"]),
        "peak_memory_kib": float(metadata["peak_memory_kib"]),
        "validation_passed": bool(validation["passed"]),
        "failed_checks": ",".join(
            key for key, passed in validation["checks"].items() if not passed
        ),
        "commit_sha": metadata.get("commit_sha") or "",
    }
    return run_row, type_rows, receiver_rows


def collect_available(output_root: Path):
    run_rows, type_rows, receiver_rows, missing = [], [], [], []
    for spec in stage5_specs():
        state, detail = completion_state(spec, output_root)
        if state not in {"complete", "invalid"}:
            missing.append({"run_name": spec.run_name, "state": state, "detail": detail})
            continue
        run, types, receivers = collect_run(spec, output_root)
        run_rows.append(run)
        type_rows.extend(types)
        receiver_rows.extend(receivers)
    return run_rows, type_rows, receiver_rows, missing


def scenario_statistics(run_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in run_rows:
        grouped[row["scenario"]].append(row)
    results = []
    for scenario, rows in sorted(grouped.items()):
        inferential = bool(rows[0]["levy"])
        for metric in (*CORE_METRICS, *REROUTE_METRICS):
            results.append(
                {
                    "scenario": scenario,
                    "levy": rows[0]["levy"],
                    "metric": metric,
                    **_interval([float(row[metric]) for row in rows], inferential),
                }
            )
    return results


def adaptation_effects(run_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    baselines = {}
    for row in _read_csv(STAGE4_RESULTS):
        if row["scenario"] in {
            "13_levy_off_flood_both", "13_levy_on_flood_both",
            "94_levy_off_flood_both", "94_levy_on_flood_both",
        }:
            baselines[(row["scenario"], int(row["seed"]))] = row
    grouped: dict[str, list[tuple[dict[str, Any], dict[str, str]]]] = defaultdict(list)
    for row in run_rows:
        baseline_scenario = (
            f"{row['environment']}_levy_"
            f"{'on' if row['levy'] else 'off'}_flood_both"
        )
        baseline = baselines.get((baseline_scenario, int(row["seed"])))
        if baseline is not None:
            grouped[
                f"{row['environment']}_levy_"
                f"{'on' if row['levy'] else 'off'}"
            ].append(
                (row, baseline)
            )
    results = []
    for stratum, pairs in sorted(grouped.items()):
        inferential = stratum.endswith("levy_on")
        for metric in CORE_METRICS:
            values = [
                float(adaptation[metric]) - float(baseline[metric])
                for adaptation, baseline in pairs
            ]
            results.append(
                {
                    "contrast": "rerouting_minus_suppression",
                    "stratum": stratum,
                    "metric": metric,
                    **_interval(values, inferential),
                }
            )
    return results


def make_plots(
    output_root: Path,
    run_rows: list[dict[str, Any]],
    statistics_rows: list[dict[str, Any]],
) -> None:
    import matplotlib.pyplot as plt

    plots = output_root / "plots"
    plots.mkdir(parents=True, exist_ok=True)
    baseline_rows = {
        (row["scenario"], int(row["seed"])): row
        for row in _read_csv(STAGE4_RESULTS)
    }
    labels, suppression, rerouting = [], [], []
    for levy, label in ((False, "Levy off"), (True, "Levy on")):
        # The portable Stage 4 baseline currently contains the original
        # 13-region matrix. Keep this paired plot scoped to available baselines.
        rows = [
            row for row in run_rows
            if row["environment"] == "13" and bool(row["levy"]) == levy
        ]
        if not rows:
            continue
        baseline_scenario = (
            "13_levy_on_flood_both" if levy else "13_levy_off_flood_both"
        )
        labels.append(label)
        suppression.append(
            sum(float(baseline_rows[(baseline_scenario, int(row["seed"]))]["fulfillment_rate"]) for row in rows) / len(rows)
        )
        rerouting.append(sum(float(row["fulfillment_rate"]) for row in rows) / len(rows))
    figure, axis = plt.subplots(figsize=(7, 5))
    x = range(len(labels))
    axis.bar([i - 0.18 for i in x], suppression, width=0.36, label="Suppression")
    axis.bar([i + 0.18 for i in x], rerouting, width=0.36, label="Rerouting")
    axis.set_xticks(list(x), labels)
    axis.set_ylabel("Fulfillment rate")
    axis.set_title("Flood adaptation demand fulfillment")
    axis.legend()
    axis.grid(axis="y", alpha=0.25)
    figure.tight_layout()
    figure.savefig(plots / "fulfillment_adaptation.png", dpi=160)
    plt.close(figure)

    rows = [
        row for row in statistics_rows
        if row["metric"] == "mean_reroute_distance_per_traveler"
    ]
    if rows:
        figure, axis = plt.subplots(figsize=(7, 5))
        axis.bar(
            range(len(rows)),
            [float(row["mean"]) for row in rows],
            color=["#e07a35" if row["levy"] else "#3478bf" for row in rows],
        )
        axis.set_xticks(
            range(len(rows)),
            ["Levy on" if row["levy"] else "Levy off" for row in rows],
        )
        axis.set_ylabel("Metres / rerouted traveler")
        axis.set_title("POI rerouting displacement")
        axis.grid(axis="y", alpha=0.25)
        figure.tight_layout()
        figure.savefig(plots / "reroute_displacement.png", dpi=160)
        plt.close(figure)


def write_report(
    output_root: Path,
    run_rows: list[dict[str, Any]],
    statistics_rows: list[dict[str, Any]],
    effects: list[dict[str, Any]],
    missing: list[dict[str, str]],
) -> None:
    valid = sum(bool(row["validation_passed"]) for row in run_rows)
    complete = len(run_rows) == EXPECTED_RUNS and valid == EXPECTED_RUNS and not missing
    indexed = {(row["scenario"], row["metric"]): row for row in statistics_rows}

    def display(row, digits=4):
        if row is None:
            return "—"
        mean = float(row["mean"])
        if row["ci95_lower"] == "":
            return f"{mean:.{digits}f}"
        return f"{mean:.{digits}f} [{float(row['ci95_lower']):.{digits}f}, {float(row['ci95_upper']):.{digits}f}]"

    lines = [
        "# Popular Times V2 Stage 5 Flood Adaptation",
        "",
        "## Status",
        "",
        f"{'COMPLETE' if complete else 'IN PROGRESS'}: {len(run_rows)} of {EXPECTED_RUNS} runs have completion artifacts; {valid} pass every invariant.",
        "",
        "The 13- and 94-region homes-and-POIs flood scenarios are evaluated with nearest enabled same-type POI rerouting. Levy off is deterministic; Levy on uses matched seeds 0–4. All runs use 56 daily cycles of 24 hourly steps. Confidence intervals are 95% t intervals, while the deterministic result has no artificial interval.",
        "",
        "| Scenario | n | Fulfillment | Rerouted fulfilled | Remaining rerouted unmet | POI displacement/traveler (m) | Peak receiving load |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for scenario in SCENARIOS:
        fulfillment = indexed.get((scenario, "fulfillment_rate"))
        if fulfillment is None:
            continue
        lines.append(
            f"| {scenario} | {fulfillment['n']} | {display(fulfillment)} | "
            f"{display(indexed.get((scenario, 'rerouted_fulfilled')), 1)} | "
            f"{display(indexed.get((scenario, 'rerouted_unmet')), 1)} | "
            f"{display(indexed.get((scenario, 'mean_reroute_distance_per_traveler')), 2)} | "
            f"{display(indexed.get((scenario, 'peak_receiving_load')), 1)} |"
        )

    lines.extend([
        "",
        "## Adaptation versus Stage 4 suppression",
        "",
        "Effects are paired absolute differences: rerouting minus the matching Stage 4 homes-and-POIs suppression run.",
        "",
        "| Levy stratum | Metric | n | Mean difference | 95% CI |",
        "|---|---|---:|---:|---:|",
    ])
    selected = {
        "fulfillment_rate", "unmet", "travelers_per_capita",
        "distance_per_requested_visit", "occupancy_per_requested_visit",
    }
    for row in effects:
        if row["metric"] not in selected:
            continue
        interval = (
            "deterministic" if row["ci95_lower"] == ""
            else f"[{float(row['ci95_lower']):.4f}, {float(row['ci95_upper']):.4f}]"
        )
        lines.append(
            f"| {row['stratum']} | {row['metric']} | {row['n']} | {float(row['mean']):.4f} | {interval} |"
        )

    lines.extend([
        "",
        "## Outputs",
        "",
        "`stage5_runs.csv` contains run-level mobility, rerouting, runtime, memory, and validation results. `stage5_poi_type.csv` splits outcomes by POI type. `stage5_receivers.csv` records original-to-receiving POI flows and receiving load. `stage5_scenario_statistics.csv` and `stage5_adaptation_effects.csv` contain the estimates and paired comparisons.",
        "",
        "## Gate 5 boundary",
        "",
        (
            "The complete adaptation matrix is ready for Gate 5 review."
            if complete else
            "This is an interim report. Resume missing runs before Gate 5 review."
        ),
        "",
    ])
    (output_root / "REPORT.md").write_text("\n".join(lines), encoding="utf8")


def analyze(output_root: Path):
    run_rows, type_rows, receiver_rows, missing = collect_available(output_root)
    statistics_rows = scenario_statistics(run_rows)
    effects = adaptation_effects(run_rows)
    _write_csv(output_root / "stage5_runs.csv", run_rows)
    _write_csv(output_root / "stage5_poi_type.csv", type_rows)
    _write_csv(output_root / "stage5_receivers.csv", receiver_rows)
    _write_csv(output_root / "stage5_scenario_statistics.csv", statistics_rows)
    _write_csv(output_root / "stage5_adaptation_effects.csv", effects)
    make_plots(output_root, run_rows, statistics_rows)
    write_report(output_root, run_rows, statistics_rows, effects, missing)
    return run_rows, missing


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run and analyze the resumable Popular Times V2 Stage 5 matrix"
    )
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--workers", type=int, default=1)
    parser.add_argument(
        "--seeds", type=int, nargs="*", default=list(range(5)),
        help="13-region Levy seeds",
    )
    parser.add_argument(
        "--seeds-94", type=int, nargs="*", default=list(range(5)),
        help="94-region Levy seeds",
    )
    parser.add_argument("--only", nargs="*", choices=SCENARIOS)
    parser.add_argument("--skip-runs", action="store_true")
    parser.add_argument("--no-analysis", action="store_true")
    parser.add_argument("--rerun-invalid", action="store_true")
    parser.add_argument("--keep-raw-uncompressed", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    if args.workers < 1:
        parser.error("--workers must be at least 1")
    if any(seed < 0 or seed > 4 for seed in args.seeds):
        parser.error("--seeds must be between 0 and 4")
    if any(seed < 0 or seed > 4 for seed in args.seeds_94):
        parser.error("--seeds-94 must be between 0 and 4")

    output_root = args.output.resolve()
    _relative_experiment_name(output_root / "path-check")
    output_root.mkdir(parents=True, exist_ok=True)
    selected = stage5_specs(args.seeds, args.seeds_94)
    if args.only:
        allowed = set(args.only)
        selected = [spec for spec in selected if spec.scenario in allowed]
    if args.dry_run:
        for spec in selected:
            state, detail = completion_state(spec, output_root)
            print(f"{spec.run_name}: {state} ({detail})")
        print(f"Selected {len(selected)} runs; full matrix contains {EXPECTED_RUNS} runs.")
        return

    failures = []
    if not args.skip_runs:
        completed = execute_runs(
            selected,
            output_root,
            args.workers,
            args.rerun_invalid,
            not args.keep_raw_uncompressed,
        )
        failures = [row for row in completed if row["status"] != "complete"]
    if not args.no_analysis:
        run_rows, missing = analyze(output_root)
        print(
            f"Analysis contains {len(run_rows)}/{EXPECTED_RUNS} completed runs; "
            f"{len(missing)} remain.",
            flush=True,
        )
    if failures:
        raise SystemExit(f"{len(failures)} selected runs failed or were invalid")


if __name__ == "__main__":
    main()
