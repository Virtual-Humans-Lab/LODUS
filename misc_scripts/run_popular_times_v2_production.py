from __future__ import annotations

import argparse
import csv
import gzip
import json
import math
import os
import shutil
import statistics
import subprocess
import sys
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_LOGS = PROJECT_ROOT / "output_logs"
DEFAULT_OUTPUT = OUTPUT_LOGS / "popular_times_v2_stage4_production"
TOTAL_CYCLES = 56
EXPECTED_RUNS = 130
SCENARIOS = (
    "13_levy_off_flood_none",
    "13_levy_off_flood_pois",
    "13_levy_off_flood_homes",
    "13_levy_off_flood_both",
    "13_levy_on_flood_none",
    "13_levy_on_flood_pois",
    "13_levy_on_flood_homes",
    "13_levy_on_flood_both",
    "94_levy_off_flood_none",
    "94_levy_on_flood_none",
)
METRICS = (
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
COMPRESSED_RAW_FILES = (
    "data_frames/popular_times_demand.csv",
    "data_frames/popular_times_visits.csv",
    "data_frames/od_matrix_enumeration_area_step.csv",
    "data_frames/od_matrix_enumeration_area_cycle.csv",
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
        return f"popular_times_v2/production/{self.scenario}"

    @property
    def levy(self) -> bool:
        return "_levy_on_" in self.scenario


def production_specs(
    seeds_13: Iterable[int] = range(30),
    seeds_94: Iterable[int] = range(5),
) -> list[RunSpec]:
    levy_seeds = {
        "13": sorted(set(seeds_13)),
        "94": sorted(set(seeds_94)),
    }
    specs = []
    for scenario in SCENARIOS:
        environment = scenario.split("_", 1)[0]
        scenario_seeds = levy_seeds[environment] if "_levy_on_" in scenario else [0]
        specs.extend(RunSpec(scenario, seed) for seed in scenario_seeds)
    return specs


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf8"))


def _read_csv(path: Path):
    if path.exists():
        stream = path.open(encoding="utf-8-sig", newline="")
    elif path.with_suffix(path.suffix + ".gz").exists():
        stream = gzip.open(
            path.with_suffix(path.suffix + ".gz"),
            mode="rt",
            encoding="utf-8-sig",
            newline="",
        )
    else:
        raise FileNotFoundError(path)
    with stream:
        yield from csv.DictReader(stream, delimiter=";")


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        return
    with path.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]), delimiter=";")
        writer.writeheader()
        writer.writerows(rows)


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _relative_experiment_name(run_path: Path) -> str:
    try:
        return run_path.resolve().relative_to(OUTPUT_LOGS.resolve()).as_posix()
    except ValueError as error:
        raise ValueError(
            f"Production output must be inside {OUTPUT_LOGS} because legacy loggers "
            "construct their paths relative to output_logs"
        ) from error


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
    )
    if not expected:
        return "pending", "metadata does not match the production run specification"
    if not validation.get("passed", False):
        return "invalid", "simulation completed but an invariant failed"
    return "complete", "validated completion artifacts found"


def compress_raw_outputs(run_path: Path) -> list[str]:
    compressed = []
    for relative_name in COMPRESSED_RAW_FILES:
        source = run_path / relative_name
        archive = source.with_suffix(source.suffix + ".gz")
        if archive.exists() and not source.exists():
            compressed.append(str(archive.relative_to(run_path)))
            continue
        if not source.exists():
            continue
        temporary = archive.with_suffix(archive.suffix + ".tmp")
        with source.open("rb") as input_stream, gzip.open(
            temporary, "wb", compresslevel=6
        ) as output_stream:
            shutil.copyfileobj(input_stream, output_stream, length=1024 * 1024)
        temporary.replace(archive)
        source.unlink()
        compressed.append(str(archive.relative_to(run_path)))
    return compressed


def _run_one(
    spec: RunSpec, output_root: Path, compress_raw: bool
) -> dict[str, Any]:
    run_path = output_root / spec.run_name
    run_path.mkdir(parents=True, exist_ok=True)
    experiment_name = _relative_experiment_name(run_path)
    command = [
        sys.executable,
        str(PROJECT_ROOT / "sector_simulation.py"),
        "--e",
        spec.experiment,
        "--n",
        experiment_name,
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
        "console_log": str(run_path / "console.log"),
        "compressed_files": compressed_files,
    }


def _write_manifest(path: Path, runs: dict[str, dict[str, Any]]) -> None:
    counts = defaultdict(int)
    for row in runs.values():
        counts[row["status"]] += 1
    payload = {
        "stage": 4,
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
    manifest_path = output_root / "production_manifest.json"
    all_rows: dict[str, dict[str, Any]] = {}
    if manifest_path.exists():
        try:
            prior = _read_json(manifest_path)
            all_rows = {row["run_name"]: row for row in prior.get("runs", [])}
        except (OSError, json.JSONDecodeError, KeyError):
            all_rows = {}

    queued = []
    for spec in specs:
        state, detail = completion_state(spec, output_root)
        if state == "complete" or (state == "invalid" and not rerun_invalid):
            compressed_files = (
                compress_raw_outputs(output_root / spec.run_name)
                if compress_raw
                else []
            )
            all_rows[spec.run_name] = {
                **asdict(spec),
                "run_name": spec.run_name,
                "status": state,
                "detail": detail,
                "compressed_files": compressed_files,
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
        try:
            for index, future in enumerate(as_completed(futures), start=1):
                spec = futures[future]
                try:
                    row = future.result()
                except Exception as error:  # Preserve other runs and the resume record.
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
        except KeyboardInterrupt:
            _write_manifest(manifest_path, all_rows)
            raise
    return completed_rows


def _region(node_name: str) -> str:
    return node_name.split("//", 1)[0]


def collect_run(spec: RunSpec, output_root: Path):
    run_path = output_root / spec.run_name
    metadata = _read_json(run_path / "run_metadata.json")
    validation = _read_json(
        run_path / "data_frames" / "popular_times_validation.json"
    )
    study = metadata["resolved_config"]["popular_times_v2_study"]
    population = int(validation["initial_population"])
    type_rows = []
    hourly_occupancy: dict[int, float] = defaultdict(float)
    occupancy_by_type: dict[str, float] = defaultdict(float)
    peak_by_type: dict[str, float] = defaultdict(float)
    for row in _read_csv(run_path / "data_frames" / "popular_times_step_type.csv"):
        occupancy = float(row["destination_occupancy"])
        simulation_step = int(row["simulation_step"])
        node_type = row["node_type"]
        hourly_occupancy[simulation_step] += occupancy
        occupancy_by_type[node_type] += occupancy
        peak_by_type[node_type] = max(peak_by_type[node_type], occupancy)

    for row in _read_csv(run_path / "data_frames" / "popular_times_summary.csv"):
        requested = float(row["requested"])
        travelers = float(row["travelers_started"])
        distance = float(row["travel_distance"])
        node_type = row["node_type"]
        type_rows.append(
            {
                "scenario": spec.scenario,
                "environment": study["environment"],
                "levy": bool(study["levy"]),
                "flood": study["flood"],
                "seed": spec.seed,
                "node_type": node_type,
                "population": population,
                "requested": requested,
                "fulfilled": float(row["fulfilled"]),
                "unmet": float(row["unmet"]),
                "fulfillment_rate": float(row["fulfillment_rate"]),
                "trips": float(row["visit_starts"]),
                "travelers": travelers,
                "travelers_per_capita": travelers / population if population else 0.0,
                "traveler_distance": distance,
                "distance_per_requested_visit": distance / requested if requested else 0.0,
                "mean_distance_per_traveler": distance / travelers if travelers else 0.0,
                "occupancy_person_hours": occupancy_by_type[node_type],
                "occupancy_per_requested_visit": occupancy_by_type[node_type] / requested if requested else 0.0,
                "peak_hourly_occupancy": peak_by_type[node_type],
            }
        )

    totals = {key: sum(float(row[key]) for row in type_rows) for key in (
        "requested", "fulfilled", "unmet", "trips", "travelers",
        "traveler_distance", "occupancy_person_hours",
    )}
    requested = totals["requested"]
    travelers = totals["travelers"]
    run_row = {
        "scenario": spec.scenario,
        "environment": study["environment"],
        "levy": bool(study["levy"]),
        "flood": study["flood"],
        "seed": spec.seed,
        "cycles": metadata["simulation_parameters"]["total_cycles"],
        "population": population,
        **totals,
        "fulfillment_rate": totals["fulfilled"] / requested if requested else 1.0,
        "travelers_per_capita": travelers / population if population else 0.0,
        "distance_per_requested_visit": totals["traveler_distance"] / requested if requested else 0.0,
        "mean_distance_per_traveler": totals["traveler_distance"] / travelers if travelers else 0.0,
        "occupancy_per_requested_visit": totals["occupancy_person_hours"] / requested if requested else 0.0,
        "peak_hourly_occupancy": max(hourly_occupancy.values(), default=0.0),
        "runtime_seconds": float(metadata["runtime_seconds"]),
        "peak_memory_kib": float(metadata["peak_memory_kib"]),
        "validation_passed": bool(validation["passed"]),
        "failed_checks": ",".join(
            key for key, passed in validation["checks"].items() if not passed
        ),
        "commit_sha": metadata.get("commit_sha") or "",
    }

    region_values: dict[tuple[str, str], dict[str, float]] = defaultdict(
        lambda: defaultdict(float)
    )
    for row in _read_csv(run_path / "data_frames" / "popular_times_demand.csv"):
        key = (_region(row["destination"]), row["node_type"])
        for field in ("requested", "fulfilled", "unmet", "destination_occupancy"):
            region_values[key][field] += float(row[field])
    region_rows = []
    for (destination_region, node_type), values in sorted(region_values.items()):
        requested = values["requested"]
        region_rows.append(
            {
                "scenario": spec.scenario,
                "environment": study["environment"],
                "levy": bool(study["levy"]),
                "flood": study["flood"],
                "seed": spec.seed,
                "destination_region": destination_region,
                "node_type": node_type,
                "requested": requested,
                "fulfilled": values["fulfilled"],
                "unmet": values["unmet"],
                "fulfillment_rate": values["fulfilled"] / requested if requested else 1.0,
                "occupancy_person_hours": values["destination_occupancy"],
            }
        )

    od_values: dict[tuple[str, str, str], dict[str, float]] = defaultdict(
        lambda: defaultdict(float)
    )
    for row in _read_csv(run_path / "data_frames" / "popular_times_od.csv"):
        key = (_region(row["origin"]), _region(row["destination"]), row["node_type"])
        for field in ("trips", "travelers", "traveler_distance"):
            od_values[key][field] += float(row[field])
    od_rows = []
    for (origin, destination, node_type), values in sorted(od_values.items()):
        travelers = values["travelers"]
        od_rows.append(
            {
                "scenario": spec.scenario,
                "environment": study["environment"],
                "levy": bool(study["levy"]),
                "flood": study["flood"],
                "seed": spec.seed,
                "origin_region": origin,
                "destination_region": destination,
                "node_type": node_type,
                "trips": values["trips"],
                "travelers": travelers,
                "traveler_distance": values["traveler_distance"],
                "mean_distance_per_traveler": values["traveler_distance"] / travelers if travelers else 0.0,
            }
        )
    return run_row, type_rows, region_rows, od_rows


def collect_available(output_root: Path, specs: list[RunSpec]):
    run_rows, type_rows, region_rows, od_rows = [], [], [], []
    missing = []
    for spec in specs:
        state, detail = completion_state(spec, output_root)
        if state not in {"complete", "invalid"}:
            missing.append({"run_name": spec.run_name, "state": state, "detail": detail})
            continue
        run, types, regions, ods = collect_run(spec, output_root)
        run_rows.append(run)
        type_rows.extend(types)
        region_rows.extend(regions)
        od_rows.extend(ods)
    return run_rows, type_rows, region_rows, od_rows, missing


def _interval(values: list[float], inferential: bool) -> dict[str, Any]:
    mean = statistics.fmean(values)
    if not inferential or len(values) < 2:
        return {
            "n": len(values), "mean": mean, "standard_deviation": "",
            "ci95_lower": "", "ci95_upper": "", "inferential": False,
        }
    standard_deviation = statistics.stdev(values)
    try:
        from scipy.stats import t

        critical = float(t.ppf(0.975, len(values) - 1))
    except ImportError:
        critical = 1.96
    margin = critical * standard_deviation / math.sqrt(len(values))
    return {
        "n": len(values), "mean": mean,
        "standard_deviation": standard_deviation,
        "ci95_lower": mean - margin, "ci95_upper": mean + margin,
        "inferential": True,
    }


def scenario_statistics(run_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in run_rows:
        grouped[row["scenario"]].append(row)
    results = []
    for scenario, rows in sorted(grouped.items()):
        inferential = bool(rows[0]["levy"])
        for metric in METRICS:
            results.append(
                {
                    "scenario": scenario,
                    "environment": rows[0]["environment"],
                    "levy": rows[0]["levy"],
                    "flood": rows[0]["flood"],
                    "metric": metric,
                    **_interval([float(row[metric]) for row in rows], inferential),
                }
            )
    return results


def effect_statistics(run_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    indexed = {(row["scenario"], int(row["seed"])): row for row in run_rows}
    contrasts: list[tuple[str, str, str, bool, list[tuple[dict, dict, dict | None, dict | None]]]] = []

    for environment, floods in (("13", ("none", "pois", "homes", "both")), ("94", ("none",))):
        for flood in floods:
            off = indexed.get((f"{environment}_levy_off_flood_{flood}", 0))
            pairs = []
            if off:
                for seed in range(30):
                    on = indexed.get((f"{environment}_levy_on_flood_{flood}", seed))
                    if on:
                        pairs.append((on, off, None, None))
            if pairs:
                contrasts.append(("levy_on_minus_off", environment, flood, True, pairs))

    for levy in (False, True):
        mode = "on" if levy else "off"
        seeds = range(30) if levy else (0,)
        for effect, flood in (("flood_pois_minus_none", "pois"), ("flood_homes_minus_none", "homes"), ("flood_both_minus_none", "both")):
            pairs = []
            for seed in seeds:
                flooded = indexed.get((f"13_levy_{mode}_flood_{flood}", seed))
                none = indexed.get((f"13_levy_{mode}_flood_none", seed))
                if flooded and none:
                    pairs.append((flooded, none, None, None))
            if pairs:
                contrasts.append((effect, "13", mode, levy, pairs))

        interaction_pairs = []
        for seed in seeds:
            both = indexed.get((f"13_levy_{mode}_flood_both", seed))
            pois = indexed.get((f"13_levy_{mode}_flood_pois", seed))
            homes = indexed.get((f"13_levy_{mode}_flood_homes", seed))
            none = indexed.get((f"13_levy_{mode}_flood_none", seed))
            if both and pois and homes and none:
                interaction_pairs.append((both, pois, homes, none))
        if interaction_pairs:
            contrasts.append(("flood_pois_x_homes", "13", mode, levy, interaction_pairs))

    for flood in ("pois", "homes", "both"):
        pairs = []
        off_flood = indexed.get((f"13_levy_off_flood_{flood}", 0))
        off_none = indexed.get(("13_levy_off_flood_none", 0))
        if off_flood and off_none:
            for seed in range(30):
                on_flood = indexed.get((f"13_levy_on_flood_{flood}", seed))
                on_none = indexed.get(("13_levy_on_flood_none", seed))
                if on_flood and on_none:
                    pairs.append((on_flood, on_none, off_flood, off_none))
        if pairs:
            contrasts.append((f"levy_x_flood_{flood}", "13", flood, True, pairs))

    results = []
    for contrast, environment, stratum, inferential, pairs in contrasts:
        for metric in METRICS:
            values = []
            for first, second, third, fourth in pairs:
                value = float(first[metric]) - float(second[metric])
                if third is not None and fourth is not None:
                    if contrast == "flood_pois_x_homes":
                        value = value - float(third[metric]) + float(fourth[metric])
                    else:
                        value -= float(third[metric]) - float(fourth[metric])
                values.append(value)
            results.append(
                {
                    "contrast": contrast,
                    "environment": environment,
                    "stratum": stratum,
                    "metric": metric,
                    **_interval(values, inferential),
                }
            )
    return results


def make_plots(output_root: Path, statistics_rows: list[dict[str, Any]]) -> None:
    import matplotlib.pyplot as plt

    plots = output_root / "plots"
    plots.mkdir(parents=True, exist_ok=True)
    for metric, title, ylabel in (
        ("fulfillment_rate", "Demand fulfillment", "Fraction"),
        ("travelers_per_capita", "Popular Times travelers per capita", "Travelers / resident"),
        ("distance_per_requested_visit", "Distance per requested visit", "Metres / request"),
        ("occupancy_per_requested_visit", "POI occupancy per requested visit", "Person-hours / request"),
    ):
        rows = [row for row in statistics_rows if row["metric"] == metric]
        if not rows:
            continue
        labels = [row["scenario"] for row in rows]
        means = [float(row["mean"]) for row in rows]
        errors = []
        for row in rows:
            if row["ci95_lower"] == "":
                errors.append(0.0)
            else:
                errors.append(float(row["mean"]) - float(row["ci95_lower"]))
        figure, axis = plt.subplots(figsize=(13, 6))
        colors = ["#e07a35" if row["levy"] else "#3478bf" for row in rows]
        axis.bar(range(len(rows)), means, yerr=errors, capsize=3, color=colors)
        axis.set_title(title)
        axis.set_ylabel(ylabel)
        axis.set_xticks(range(len(rows)), labels, rotation=65, ha="right")
        axis.grid(axis="y", alpha=0.25)
        figure.tight_layout()
        figure.savefig(plots / f"{metric}.png", dpi=160)
        plt.close(figure)


def write_report(
    output_root: Path,
    run_rows: list[dict[str, Any]],
    statistics_rows: list[dict[str, Any]],
    effects: list[dict[str, Any]],
    missing: list[dict[str, str]],
) -> None:
    expected = EXPECTED_RUNS
    valid = sum(bool(row["validation_passed"]) for row in run_rows)
    complete = len(run_rows) == expected and valid == expected and not missing
    summary_index = {
        (row["scenario"], row["metric"]): row for row in statistics_rows
    }
    lines = [
        "# Popular Times V2 Stage 4 Core Production Matrix",
        "",
        "## Status",
        "",
        f"{'COMPLETE' if complete else 'IN PROGRESS'}: {len(run_rows)} of {expected} runs have completion artifacts; {valid} completed runs pass every invariant.",
        "",
        "All production configurations use 56 daily cycles of 24 hourly steps. Levy-off scenarios are deterministic and run once. The 13-region Levy-on scenarios use matched seeds 0–29; the 94-region Levy-on scenario uses seeds 0–4. Where applicable, 95% t intervals are calculated across paired stochastic runs. Deterministic results are reported without artificial confidence intervals.",
        "",
        "| Scenario | n | Fulfillment (95% CI) | Travelers/capita (95% CI) | Distance/request (95% CI) | Occupancy/request (95% CI) |",
        "|---|---:|---:|---:|---:|---:|",
    ]

    def display(row):
        if row is None:
            return "—"
        mean = float(row["mean"])
        if row["ci95_lower"] == "":
            return f"{mean:.4f}"
        return f"{mean:.4f} [{float(row['ci95_lower']):.4f}, {float(row['ci95_upper']):.4f}]"

    for scenario in SCENARIOS:
        fulfillment = summary_index.get((scenario, "fulfillment_rate"))
        if fulfillment is None:
            continue
        lines.append(
            f"| {scenario} | {fulfillment['n']} | {display(fulfillment)} | "
            f"{display(summary_index.get((scenario, 'travelers_per_capita')))} | "
            f"{display(summary_index.get((scenario, 'distance_per_requested_visit')))} | "
            f"{display(summary_index.get((scenario, 'occupancy_per_requested_visit')))} |"
        )

    lines.extend(["", "## Contrasts", ""])
    selected_metrics = {"fulfillment_rate", "travelers_per_capita", "distance_per_requested_visit", "occupancy_per_requested_visit"}
    selected = [row for row in effects if row["metric"] in selected_metrics]
    if selected:
        lines.extend([
            "Effects are absolute differences (first condition minus reference); fulfillment-rate differences are percentage-point fractions.",
            "",
            "| Contrast | Environment | Stratum | Metric | n | Mean difference | 95% CI |",
            "|---|---|---|---|---:|---:|---:|",
        ])
        for row in selected:
            interval = "deterministic" if row["ci95_lower"] == "" else f"[{float(row['ci95_lower']):.4f}, {float(row['ci95_upper']):.4f}]"
            lines.append(
                f"| {row['contrast']} | {row['environment']} | {row['stratum']} | {row['metric']} | {row['n']} | {float(row['mean']):.4f} | {interval} |"
            )
    else:
        lines.append("Contrasts will appear when the required matching runs are available.")

    lines.extend([
        "",
        "## Outputs",
        "",
        "`production_runs.csv` contains run-level demand, trips, travelers, distance, occupancy, runtime, memory, and validation results. `production_poi_type.csv` provides the same mobility outcomes by POI type. `production_region.csv` aggregates demand and occupancy geographically by destination region, and `production_region_od.csv` contains Popular Times origin–destination flows. `production_scenario_statistics.csv` and `production_effects.csv` contain descriptive estimates and the pre-specified 95% intervals.",
        "",
        "The per-run directories retain the raw Popular Times, movement, enumeration-area OD, population, and node-state records needed for audit or alternative analyses. The largest raw CSVs are stored losslessly as `.csv.gz` by default to keep the production matrix within practical disk bounds.",
        "",
        "## Gate 4 boundary",
        "",
    ])
    if complete:
        lines.append("The complete core matrix is ready for Gate 4 review. Stage 5 rerouting adaptation has not been started.")
    else:
        lines.append("This is a resumable interim report, not Gate 4 evidence. Re-run the production command to complete missing runs; completed validated runs will be skipped.")
        if missing:
            lines.extend(["", f"Missing or incomplete runs: {len(missing)}."])
    lines.append("")
    (output_root / "REPORT.md").write_text("\n".join(lines), encoding="utf8")


def analyze(output_root: Path) -> tuple[list[dict[str, Any]], list[dict[str, str]]]:
    specs = production_specs()
    run_rows, type_rows, region_rows, od_rows, missing = collect_available(
        output_root, specs
    )
    statistics_rows = scenario_statistics(run_rows)
    effects = effect_statistics(run_rows)
    _write_csv(output_root / "production_runs.csv", run_rows)
    _write_csv(output_root / "production_poi_type.csv", type_rows)
    _write_csv(output_root / "production_region.csv", region_rows)
    _write_csv(output_root / "production_region_od.csv", od_rows)
    _write_csv(output_root / "production_scenario_statistics.csv", statistics_rows)
    _write_csv(output_root / "production_effects.csv", effects)
    make_plots(output_root, statistics_rows)
    write_report(output_root, run_rows, statistics_rows, effects, missing)
    return run_rows, missing


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run and analyze the resumable Popular Times V2 Stage 4 matrix"
    )
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--workers", type=int, default=1)
    parser.add_argument("--seeds-13", type=int, nargs="*", default=list(range(30)))
    parser.add_argument("--seeds-94", type=int, nargs="*", default=list(range(5)))
    parser.add_argument("--only", nargs="*", choices=SCENARIOS)
    parser.add_argument("--skip-runs", action="store_true")
    parser.add_argument("--no-analysis", action="store_true")
    parser.add_argument("--rerun-invalid", action="store_true")
    parser.add_argument(
        "--keep-raw-uncompressed",
        action="store_true",
        help="Do not gzip the largest raw CSVs after each completed run",
    )
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    if args.workers < 1:
        parser.error("--workers must be at least 1")
    if any(seed < 0 or seed > 29 for seed in args.seeds_13):
        parser.error("--seeds-13 must be between 0 and 29")
    if any(seed < 0 or seed > 4 for seed in args.seeds_94):
        parser.error("--seeds-94 must be between 0 and 4")

    output_root = args.output.resolve()
    _relative_experiment_name(output_root / "path-check")
    output_root.mkdir(parents=True, exist_ok=True)
    selected = production_specs(args.seeds_13, args.seeds_94)
    if args.only:
        allowed = set(args.only)
        selected = [spec for spec in selected if spec.scenario in allowed]
    if args.dry_run:
        for spec in selected:
            state, detail = completion_state(spec, output_root)
            print(f"{spec.run_name}: {state} ({detail})")
        print(
            f"Selected {len(selected)} runs; full matrix contains "
            f"{EXPECTED_RUNS} runs."
        )
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
