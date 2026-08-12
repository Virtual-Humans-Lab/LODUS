from __future__ import annotations

import argparse
import csv
import gzip
import json
import os
import shutil
import subprocess
import sys
from collections import Counter, defaultdict
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
from util.data_parse import load_experiment_config


DEFAULT_OUTPUT = OUTPUT_LOGS / "popular_times_v2_stage6"
STAGE4_RESULTS = (
    PROJECT_ROOT / "docs" / "results" / "popular_times_v2_stage4" / "production_runs.csv"
)
STAGE5_RESULTS = (
    PROJECT_ROOT / "docs" / "results" / "popular_times_v2_stage5" / "stage5_runs.csv"
)
EXPECTED_RUNS = 50
SCENARIOS = (
    "13_levy_v2_flood_none",
    "13_levy_v2_flood_destinations",
    "13_levy_v2_flood_homes",
    "13_levy_v2_flood_all",
    "13_levy_v2_flood_all_pt_reroute",
    "94_levy_v2_flood_none",
    "94_levy_v2_flood_destinations",
    "94_levy_v2_flood_homes",
    "94_levy_v2_flood_all",
    "94_levy_v2_flood_all_pt_reroute",
)
RAW_V2_FILES = (
    "data_frames/levy_v2_demand.csv",
    "data_frames/levy_v2_movements.csv",
)
RUN_METRICS = (
    "pt_fulfillment_rate",
    "pt_unmet",
    "pt_mean_distance_per_traveler",
    "pt_rerouted_fulfilled",
    "levy_fulfillment_rate",
    "levy_unmet",
    "levy_population_moved",
    "levy_packet_count",
    "levy_actual_blob_fragments",
    "levy_mean_outbound_distance",
    "levy_occupancy_person_hours",
    "levy_temporary_returns",
    "levy_return_blocked",
    "levy_repatriations",
)
CROSS_VERSION_METRICS = (
    "fulfillment_rate",
    "unmet",
    "mean_distance_per_traveler",
    "travelers_per_capita",
    "occupancy_per_requested_visit",
)
LEGACY_MATCH = {
    "13_levy_v2_flood_none": ("stage4", "13_levy_on_flood_none"),
    "13_levy_v2_flood_destinations": ("stage4", "13_levy_on_flood_pois"),
    "13_levy_v2_flood_homes": ("stage4", "13_levy_on_flood_homes"),
    "13_levy_v2_flood_all": ("stage4", "13_levy_on_flood_both"),
    "13_levy_v2_flood_all_pt_reroute": (
        "stage5", "13_levy_on_flood_both_reroute"
    ),
    "94_levy_v2_flood_none": ("stage4", "94_levy_on_flood_none"),
    "94_levy_v2_flood_destinations": ("stage4", "94_levy_on_flood_pois"),
    "94_levy_v2_flood_homes": ("stage4", "94_levy_on_flood_homes"),
    "94_levy_v2_flood_all": ("stage4", "94_levy_on_flood_both"),
    "94_levy_v2_flood_all_pt_reroute": (
        "stage5", "94_levy_on_flood_both_reroute"
    ),
}


@dataclass(frozen=True)
class RunSpec:
    scenario: str
    seed: int

    @property
    def run_name(self) -> str:
        return f"{self.scenario}-seed{self.seed}"

    @property
    def experiment(self) -> str:
        return f"popular_times_v2/stage6/{self.scenario}"


def stage6_specs(
    seeds_13: Iterable[int] = range(5),
    seeds_94: Iterable[int] = range(5),
) -> list[RunSpec]:
    seeds = {"13": sorted(set(seeds_13)), "94": sorted(set(seeds_94))}
    return [
        RunSpec(scenario, seed)
        for scenario in SCENARIOS
        for seed in seeds[scenario.split("_", 1)[0]]
    ]


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def completion_state(spec: RunSpec, output_root: Path) -> tuple[str, str]:
    run_path = output_root / spec.run_name
    data_path = run_path / "data_frames"
    paths = (
        run_path / "run_metadata.json",
        data_path / "popular_times_validation.json",
        data_path / "levy_v2_validation.json",
    )
    if not all(path.exists() for path in paths):
        return "pending", "completion artifacts are missing"
    try:
        metadata, popular_validation, levy_validation = map(_read_json, paths)
    except (OSError, json.JSONDecodeError) as error:
        return "pending", f"completion artifacts are unreadable: {error}"
    resolved = metadata.get("resolved_config", {})
    study = resolved.get("popular_times_v2_stage6", {})
    actual_groups = resolved.get("levy_walk_v2_plugin", {}).get("groups", {})
    expected_groups = load_experiment_config(spec.experiment)[
        "levy_walk_v2_plugin"
    ]["groups"]
    attendance_rates_match = all(
        actual_groups.get(group, {}).get("cycle_attendance_rate")
        == config["cycle_attendance_rate"]
        for group, config in expected_groups.items()
    )
    expected = (
        metadata.get("status") == "complete"
        and metadata.get("experiment") == spec.experiment
        and int(metadata.get("seed", -1)) == spec.seed
        and int(metadata.get("simulation_parameters", {}).get("total_cycles", -1))
        == TOTAL_CYCLES
        and study.get("environment") == spec.scenario.split("_", 1)[0]
        and study.get("levy_model") == "v2"
        and attendance_rates_match
        and "levy_walk_plugin" not in resolved
        and "send_population_back_plugin" not in resolved
    )
    if not expected:
        return "pending", "metadata does not match the Stage 6 run specification"
    if not popular_validation.get("passed") or not levy_validation.get("passed"):
        return "invalid", "simulation completed but an invariant failed"
    return "complete", "both validation suites passed"


def compress_stage6_raw(run_path: Path) -> list[str]:
    compressed = compress_raw_outputs(run_path)
    for relative in RAW_V2_FILES:
        source = run_path / relative
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
    return sorted(set(compressed))


def _run_one(spec: RunSpec, output_root: Path, compress_raw: bool) -> dict[str, Any]:
    run_path = output_root / spec.run_name
    run_path.mkdir(parents=True, exist_ok=True)
    command = [
        sys.executable,
        str(PROJECT_ROOT / "sector_simulation.py"),
        "--e", spec.experiment,
        "--n", _relative_experiment_name(run_path),
        "--seed", str(spec.seed),
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
    compressed = (
        compress_stage6_raw(run_path)
        if compress_raw and state in {"complete", "invalid"}
        else []
    )
    return {
        **asdict(spec),
        "run_name": spec.run_name,
        "status": state,
        "detail": detail,
        "returncode": completed.returncode,
        "started_at_utc": started,
        "finished_at_utc": _utc_now(),
        "compressed_files": compressed,
    }


def _write_manifest(path: Path, runs: dict[str, dict[str, Any]]):
    counts = Counter(row["status"] for row in runs.values())
    payload = {
        "stage": 6,
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
    manifest_path = output_root / "stage6_manifest.json"
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
                **asdict(spec), "run_name": spec.run_name, "status": state,
                "detail": detail,
                "compressed_files": (
                    compress_stage6_raw(output_root / spec.run_name)
                    if compress_raw else []
                ),
            }
            print(f"[resume] {spec.run_name}: {state}", flush=True)
        else:
            queued.append(spec)
            all_rows[spec.run_name] = {
                **asdict(spec), "run_name": spec.run_name,
                "status": "queued", "detail": detail,
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
                    **asdict(spec), "run_name": spec.run_name,
                    "status": "failed", "detail": repr(error),
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


def _safe_ratio(numerator: float, denominator: float) -> float:
    return numerator / denominator if denominator else 0.0


def collect_run(spec: RunSpec, output_root: Path):
    run_path = output_root / spec.run_name
    data_path = run_path / "data_frames"
    metadata = _read_json(run_path / "run_metadata.json")
    popular_validation = _read_json(data_path / "popular_times_validation.json")
    levy_validation = _read_json(data_path / "levy_v2_validation.json")
    study = metadata["resolved_config"]["popular_times_v2_stage6"]
    population = int(levy_validation["initial_population"])

    pt_rows = list(_read_csv(data_path / "popular_times_summary.csv"))
    pt_step_rows = list(_read_csv(data_path / "popular_times_step_type.csv"))
    pt_requested = sum(float(row["requested"]) for row in pt_rows)
    pt_fulfilled = sum(float(row["fulfilled"]) for row in pt_rows)
    pt_unmet = sum(float(row["unmet"]) for row in pt_rows)
    pt_travelers = sum(float(row["travelers_started"]) for row in pt_rows)
    pt_distance = sum(float(row["travel_distance"]) for row in pt_rows)
    pt_occupancy = sum(float(row["destination_occupancy"]) for row in pt_step_rows)
    pt_rerouted = sum(float(row["rerouted_fulfilled"]) for row in pt_rows)

    levy_group_rows = []
    for row in _read_csv(data_path / "levy_v2_summary.csv"):
        converted = {
            "scenario": spec.scenario,
            "seed": spec.seed,
            **row,
        }
        levy_group_rows.append(converted)
    levy_steps = list(_read_csv(data_path / "levy_v2_step_group.csv"))
    numeric = defaultdict(float)
    for row in levy_group_rows:
        for key in (
            "original_population", "exact_cycle_demand", "requested", "fulfilled",
            "unmet", "packet_count", "actual_blob_fragments", "population_moved",
            "population_returned", "temporary_returns", "return_blocked",
            "repatriations", "outbound_traveler_distance",
            "return_traveler_distance", "temporary_home_traveler_distance",
            "repatriation_traveler_distance", "destination_reroutes",
            "rerouted_fulfilled",
        ):
            numeric[key] += float(row[key])
    occupancy_person_hours = sum(float(row["occupancy"]) for row in levy_steps)
    peak_occupancy = max((float(row["occupancy"]) for row in levy_steps), default=0.0)
    reason_rows = []
    reason_counts: dict[tuple[str, str], dict[str, float]] = defaultdict(
        lambda: defaultdict(float)
    )
    for row in _read_csv(data_path / "levy_v2_demand.csv"):
        reason = row["reason"] or "fulfilled"
        values = reason_counts[(row["group"], reason)]
        values["packets"] += 1
        values["requested"] += float(row["requested"])
        values["fulfilled"] += float(row["fulfilled"])
        values["unmet"] += float(row["unmet"])
    for (group, reason), values in sorted(reason_counts.items()):
        reason_rows.append(
            {"scenario": spec.scenario, "seed": spec.seed,
             "group": group, "reason": reason, **values}
        )

    levy_requested = numeric["requested"]
    levy_moved = numeric["population_moved"]
    run_row = {
        "scenario": spec.scenario,
        "environment": study["environment"],
        "levy_model": study["levy_model"],
        "flood": study["flood"],
        "adaptation": study["adaptation"],
        "seed": spec.seed,
        "cycles": metadata["simulation_parameters"]["total_cycles"],
        "population": population,
        "pt_requested": pt_requested,
        "pt_fulfilled": pt_fulfilled,
        "pt_unmet": pt_unmet,
        "pt_fulfillment_rate": _safe_ratio(pt_fulfilled, pt_requested),
        "pt_travelers": pt_travelers,
        "pt_travelers_per_capita": _safe_ratio(pt_travelers, population),
        "pt_traveler_distance": pt_distance,
        "pt_mean_distance_per_traveler": _safe_ratio(pt_distance, pt_travelers),
        "pt_occupancy_person_hours": pt_occupancy,
        "pt_occupancy_per_requested_visit": _safe_ratio(pt_occupancy, pt_requested),
        "pt_rerouted_fulfilled": pt_rerouted,
        "levy_original_population": numeric["original_population"],
        "levy_exact_cycle_demand": numeric["exact_cycle_demand"],
        "levy_requested": levy_requested,
        "levy_fulfilled": numeric["fulfilled"],
        "levy_unmet": numeric["unmet"],
        "levy_fulfillment_rate": _safe_ratio(numeric["fulfilled"], levy_requested),
        "levy_packet_count": numeric["packet_count"],
        "levy_actual_blob_fragments": numeric["actual_blob_fragments"],
        "levy_population_moved": levy_moved,
        "levy_population_returned": numeric["population_returned"],
        "levy_temporary_returns": numeric["temporary_returns"],
        "levy_return_blocked": numeric["return_blocked"],
        "levy_repatriations": numeric["repatriations"],
        "levy_outbound_traveler_distance": numeric["outbound_traveler_distance"],
        "levy_mean_outbound_distance": _safe_ratio(
            numeric["outbound_traveler_distance"], levy_moved
        ),
        "levy_return_traveler_distance": numeric["return_traveler_distance"],
        "levy_temporary_home_traveler_distance": numeric["temporary_home_traveler_distance"],
        "levy_repatriation_traveler_distance": numeric["repatriation_traveler_distance"],
        "levy_occupancy_person_hours": occupancy_person_hours,
        "levy_peak_occupancy": peak_occupancy,
        "levy_destination_reroutes": numeric["destination_reroutes"],
        "levy_rerouted_fulfilled": numeric["rerouted_fulfilled"],
        "runtime_seconds": float(metadata["runtime_seconds"]),
        "peak_memory_kib": float(metadata["peak_memory_kib"]),
        "popular_validation_passed": bool(popular_validation["passed"]),
        "levy_validation_passed": bool(levy_validation["passed"]),
        "commit_sha": metadata.get("commit_sha") or "",
    }
    return run_row, levy_group_rows, reason_rows


def collect_available(output_root: Path):
    runs, groups, reasons, missing = [], [], [], []
    for spec in stage6_specs():
        state, detail = completion_state(spec, output_root)
        if state not in {"complete", "invalid"}:
            missing.append({"run_name": spec.run_name, "state": state, "detail": detail})
            continue
        run, group_rows, reason_rows = collect_run(spec, output_root)
        runs.append(run)
        groups.extend(group_rows)
        reasons.extend(reason_rows)
    return runs, groups, reasons, missing


def scenario_statistics(run_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in run_rows:
        grouped[row["scenario"]].append(row)
    results = []
    for scenario, rows in sorted(grouped.items()):
        for metric in RUN_METRICS:
            results.append(
                {"scenario": scenario, "metric": metric,
                 **_interval([float(row[metric]) for row in rows], True)}
            )
    return results


def baseline_effects(run_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    indexed = {(row["scenario"], int(row["seed"])): row for row in run_rows}
    results = []
    for environment in ("13", "94"):
        family = [s for s in SCENARIOS if s.startswith(f"{environment}_")]
        baseline = f"{environment}_levy_v2_flood_none"
        for scenario in family:
            if scenario == baseline:
                continue
            pairs = [
                (indexed[(scenario, seed)], indexed[(baseline, seed)])
                for seed in range(5)
                if (scenario, seed) in indexed and (baseline, seed) in indexed
            ]
            for metric in RUN_METRICS:
                values = [float(flood[metric]) - float(none[metric]) for flood, none in pairs]
                results.append(
                    {"contrast": f"{scenario}_minus_{baseline}", "metric": metric,
                     **_interval(values, True)}
                )
    return results


def cross_version_effects(run_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    legacy_sources = {
        "stage4": list(_read_csv(STAGE4_RESULTS)),
        "stage5": list(_read_csv(STAGE5_RESULTS)),
    }
    legacy = {
        (source, row["scenario"], int(row["seed"])): row
        for source, rows in legacy_sources.items()
        for row in rows
    }
    grouped: dict[str, list[tuple[dict[str, Any], dict[str, str]]]] = defaultdict(list)
    for row in run_rows:
        source, scenario = LEGACY_MATCH[row["scenario"]]
        old = legacy.get((source, scenario, int(row["seed"])))
        if old is not None:
            grouped[row["scenario"]].append((row, old))
    results = []
    for scenario, pairs in sorted(grouped.items()):
        source, legacy_scenario = LEGACY_MATCH[scenario]
        for metric in CROSS_VERSION_METRICS:
            new_key = f"pt_{metric}"
            values = [float(new[new_key]) - float(old[metric]) for new, old in pairs]
            results.append(
                {
                    "contrast": "levy_v2_minus_legacy",
                    "scenario": scenario,
                    "legacy_stage": source,
                    "legacy_scenario": legacy_scenario,
                    "comparison_scope": "combined_model_revision",
                    "metric": metric,
                    **_interval(values, True),
                }
            )
    return results


def make_plots(output_root: Path, statistics_rows: list[dict[str, Any]]):
    import matplotlib.pyplot as plt

    plots = output_root / "plots"
    plots.mkdir(parents=True, exist_ok=True)
    indexed = {(row["scenario"], row["metric"]): row for row in statistics_rows}
    labels = ["No flood", "Destinations", "Homes", "All", "All + PT reroute"]
    for environment in ("13", "94"):
        scenarios = [s for s in SCENARIOS if s.startswith(f"{environment}_")]
        for metric, title, ylabel, filename in (
            ("levy_fulfillment_rate", "Levy V2 commute fulfillment", "Fulfillment rate", "levy_fulfillment.png"),
            ("pt_fulfillment_rate", "Popular Times fulfillment", "Fulfillment rate", "popular_times_fulfillment.png"),
            ("levy_mean_outbound_distance", "Levy V2 outbound sourcing distance", "Metres / traveler", "levy_distance.png"),
        ):
            rows = [indexed.get((scenario, metric)) for scenario in scenarios]
            if not all(rows):
                continue
            means = [float(row["mean"]) for row in rows]
            errors = [
                [mean - float(row["ci95_lower"]) if row["ci95_lower"] != "" else 0.0 for mean, row in zip(means, rows)],
                [float(row["ci95_upper"]) - mean if row["ci95_upper"] != "" else 0.0 for mean, row in zip(means, rows)],
            ]
            figure, axis = plt.subplots(figsize=(9, 5))
            axis.bar(range(len(labels)), means, yerr=errors, capsize=3, color="#3478bf")
            axis.set_xticks(range(len(labels)), labels, rotation=15, ha="right")
            axis.set_ylabel(ylabel)
            axis.set_title(f"{title} ({environment} regions)")
            axis.grid(axis="y", alpha=0.25)
            figure.tight_layout()
            figure.savefig(plots / f"{Path(filename).stem}_{environment}.png", dpi=160)
            plt.close(figure)


def _display(row: dict[str, Any] | None, digits: int = 4) -> str:
    if row is None:
        return "—"
    mean = f"{float(row['mean']):.{digits}f}"
    if row["ci95_lower"] == "":
        return mean
    return f"{mean} [{float(row['ci95_lower']):.{digits}f}, {float(row['ci95_upper']):.{digits}f}]"


def write_report(
    output_root: Path,
    run_rows: list[dict[str, Any]],
    statistics_rows: list[dict[str, Any]],
    effects: list[dict[str, Any]],
    cross_version: list[dict[str, Any]],
    missing: list[dict[str, str]],
):
    complete = (
        len(run_rows) == EXPECTED_RUNS
        and all(row["popular_validation_passed"] and row["levy_validation_passed"] for row in run_rows)
        and not missing
    )
    indexed = {(row["scenario"], row["metric"]): row for row in statistics_rows}
    lines = [
        "# Popular Times V2 Stage 6 — Levy Walk V2",
        "",
        "## Status",
        "",
        f"{'COMPLETE' if complete else 'IN PROGRESS'}: {len(run_rows)} of {EXPECTED_RUNS} runs are preserved; all preserved runs pass both Popular Times and Levy V2 invariants.",
        "",
        "All scenarios use 56 daily cycles and flood-aware commute lifecycles. The 13- and 94-region families use paired seeds 0–4. Levy V2 uses a maximum packet size of 50 and exact cycle-level worker/student attendance. Intervals are paired or scenario-level 95% t intervals.",
        "",
        "| Scenario | n | Levy fulfillment | Levy unmet | Moved population | Mean commute distance (m) | PT fulfillment |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for scenario in SCENARIOS:
        levy = indexed.get((scenario, "levy_fulfillment_rate"))
        if levy is None:
            continue
        lines.append(
            f"| {scenario} | {levy['n']} | {_display(levy)} | "
            f"{_display(indexed.get((scenario, 'levy_unmet')), 1)} | "
            f"{_display(indexed.get((scenario, 'levy_population_moved')), 1)} | "
            f"{_display(indexed.get((scenario, 'levy_mean_outbound_distance')), 2)} | "
            f"{_display(indexed.get((scenario, 'pt_fulfillment_rate')))} |"
        )
    lines.extend([
        "", "## Flood effects versus the Levy V2 no-flood baseline", "",
        "Effects below are paired by seed and reported as flood condition minus no flood.",
        "", "| Contrast | Metric | n | Mean difference | 95% CI |",
        "|---|---|---:|---:|---:|",
    ])
    for row in effects:
        if row["metric"] not in {
            "levy_fulfillment_rate", "levy_unmet", "levy_mean_outbound_distance",
            "pt_fulfillment_rate", "pt_unmet",
        }:
            continue
        interval = (
            "insufficient n"
            if row["ci95_lower"] == ""
            else f"[{float(row['ci95_lower']):.4f}, {float(row['ci95_upper']):.4f}]"
        )
        lines.append(
            f"| {row['contrast']} | {row['metric']} | {row['n']} | "
            f"{float(row['mean']):.4f} | {interval} |"
        )
    lines.extend([
        "", "## Cross-version comparisons", "",
        "Each new family is paired to the matching Stage 4 suppression or Stage 5 Popular Times rerouting family. These are deliberately labeled combined model revisions because Levy V2 changes commute demand/lifecycle and destination flooding newly includes work and school. Legacy outputs do not contain the Levy V2 demand audit fields, so cross-version tables compare the shared Popular Times outcome metrics.",
        "", "| New scenario | Legacy | Metric | n | V2 − legacy | 95% CI |",
        "|---|---|---|---:|---:|---:|",
    ])
    for row in cross_version:
        if row["metric"] not in {"fulfillment_rate", "unmet", "mean_distance_per_traveler"}:
            continue
        interval = (
            "insufficient n"
            if row["ci95_lower"] == ""
            else f"[{float(row['ci95_lower']):.4f}, {float(row['ci95_upper']):.4f}]"
        )
        lines.append(
            f"| {row['scenario']} | {row['legacy_stage']}:{row['legacy_scenario']} | "
            f"{row['metric']} | {row['n']} | {float(row['mean']):.4f} | {interval} |"
        )
    lines.extend([
        "", "## Audit outputs", "",
        "`stage6_runs.csv` contains paired run metrics, runtime, memory, and both validation results. `stage6_levy_groups.csv` preserves worker/student outcomes. `stage6_unmet_reasons.csv` audits suppressed and partially fulfilled demand. Scenario estimates and paired effects are in the two statistics tables and the cross-version comparison table.",
        "", "Raw run directories remain under `output_logs/popular_times_v2_stage6/` and are resumable with `python3 misc_scripts/run_popular_times_v2_stage6.py`. High-volume demand, movement, and OD CSVs are gzip-compressed after validation.",
        "", "## Gate 6 boundary", "",
        ("The complete Stage 6 matrix is ready for Gate 6 review. No prior result was replaced or deleted." if complete else "This is an interim report. Resume the missing runs before Gate 6 review."),
        "",
    ])
    (output_root / "REPORT.md").write_text("\n".join(lines), encoding="utf8")


def analyze(output_root: Path):
    runs, groups, reasons, missing = collect_available(output_root)
    statistics_rows = scenario_statistics(runs)
    effects = baseline_effects(runs)
    cross_version = cross_version_effects(runs)
    _write_csv(output_root / "stage6_runs.csv", runs)
    _write_csv(output_root / "stage6_levy_groups.csv", groups)
    _write_csv(output_root / "stage6_unmet_reasons.csv", reasons)
    _write_csv(output_root / "stage6_scenario_statistics.csv", statistics_rows)
    _write_csv(output_root / "stage6_baseline_effects.csv", effects)
    _write_csv(output_root / "stage6_cross_version_effects.csv", cross_version)
    make_plots(output_root, statistics_rows)
    write_report(output_root, runs, statistics_rows, effects, cross_version, missing)
    return runs, missing


def main():
    parser = argparse.ArgumentParser(
        description="Run and analyze the resumable Popular Times V2 Stage 6 matrix"
    )
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--workers", type=int, default=1)
    parser.add_argument("--seeds", type=int, nargs="*", default=list(range(5)), help="13-region seeds")
    parser.add_argument("--seeds-94", type=int, nargs="*", default=list(range(5)), help="94-region seeds")
    parser.add_argument("--only", nargs="*", choices=SCENARIOS)
    parser.add_argument("--smoke", action="store_true", help="Run seed 0 for all ten scenarios")
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
    seeds_13 = [0] if args.smoke else args.seeds
    seeds_94 = [0] if args.smoke else args.seeds_94
    selected = stage6_specs(seeds_13, seeds_94)
    if args.only:
        selected = [spec for spec in selected if spec.scenario in set(args.only)]
    if args.dry_run:
        for spec in selected:
            state, detail = completion_state(spec, output_root)
            print(f"{spec.run_name}: {state} ({detail})")
        print(f"Selected {len(selected)} runs; full matrix contains {EXPECTED_RUNS} runs.")
        return
    failures = []
    if not args.skip_runs:
        completed = execute_runs(
            selected, output_root, args.workers, args.rerun_invalid,
            not args.keep_raw_uncompressed,
        )
        failures = [row for row in completed if row["status"] != "complete"]
    if not args.no_analysis:
        runs, missing = analyze(output_root)
        print(
            f"Analysis contains {len(runs)}/{EXPECTED_RUNS} runs; {len(missing)} remain.",
            flush=True,
        )
    if failures:
        raise SystemExit(f"{len(failures)} selected runs failed or were invalid")


if __name__ == "__main__":
    main()
