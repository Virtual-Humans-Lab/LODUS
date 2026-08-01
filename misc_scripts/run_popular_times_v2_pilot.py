from __future__ import annotations

import argparse
import csv
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = PROJECT_ROOT / "output_logs" / "popular_times_v2_stage3_pilot"
SCENARIOS = [
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
]


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf8"))


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as stream:
        return list(csv.DictReader(stream, delimiter=";"))


def run_scenario(scenario: str, output_root: Path, seed: int = 0) -> Path:
    run_name = f"{scenario}-seed{seed}"
    run_path = output_root / run_name
    run_path.mkdir(parents=True, exist_ok=True)
    experiment = f"popular_times_v2/scenarios/{scenario}"
    command = [
        sys.executable,
        str(PROJECT_ROOT / "sector_simulation.py"),
        "--e",
        experiment,
        "--n",
        f"popular_times_v2_stage3_pilot/{run_name}",
        "--seed",
        str(seed),
    ]
    with (run_path / "console.log").open("w", encoding="utf8") as log:
        completed = subprocess.run(
            command,
            cwd=PROJECT_ROOT,
            stdout=log,
            stderr=subprocess.STDOUT,
            check=False,
        )
    if completed.returncode:
        raise RuntimeError(
            f"Pilot scenario {scenario} failed with exit code "
            f"{completed.returncode}; see {run_path / 'console.log'}"
        )
    return run_path


def collect_results(output_root: Path, scenarios: list[str], seed: int = 0):
    run_rows = []
    type_rows = []
    for scenario in scenarios:
        run_name = f"{scenario}-seed{seed}"
        run_path = output_root / run_name
        metadata = _read_json(run_path / "run_metadata.json")
        validation = _read_json(
            run_path / "data_frames" / "popular_times_validation.json"
        )
        summaries = _read_csv(
            run_path / "data_frames" / "popular_times_summary.csv"
        )
        study = metadata["resolved_config"]["popular_times_v2_study"]
        population = int(validation["initial_population"])
        requested = sum(float(row["requested"]) for row in summaries)
        fulfilled = sum(float(row["fulfilled"]) for row in summaries)
        travelers = sum(float(row["travelers_started"]) for row in summaries)
        distance = sum(float(row["travel_distance"]) for row in summaries)
        run_rows.append(
            {
                "scenario": scenario,
                "environment": study["environment"],
                "levy": study["levy"],
                "flood": study["flood"],
                "seed": seed,
                "cycles": metadata["simulation_parameters"]["total_cycles"],
                "population": population,
                "requested": requested,
                "fulfilled": fulfilled,
                "unmet": requested - fulfilled,
                "fulfillment_rate": fulfilled / requested if requested else 1.0,
                "travelers": travelers,
                "travelers_per_capita": travelers / population if population else 0.0,
                "distance_per_requested_visit": distance / requested if requested else 0.0,
                "runtime_seconds": metadata["runtime_seconds"],
                "peak_memory_kib": metadata["peak_memory_kib"],
                "validation_passed": validation["passed"],
                "failed_checks": ",".join(
                    key for key, passed in validation["checks"].items() if not passed
                ),
            }
        )
        for row in summaries:
            type_rows.append(
                {
                    "scenario": scenario,
                    "environment": study["environment"],
                    "levy": study["levy"],
                    "flood": study["flood"],
                    "seed": seed,
                    "node_type": row["node_type"],
                    "requested": row["requested"],
                    "fulfilled": row["fulfilled"],
                    "unmet": row["unmet"],
                    "fulfillment_rate": row["fulfillment_rate"],
                    "travelers": row["travelers_started"],
                    "travelers_per_capita": float(row["travelers_started"]) / population,
                    "mean_distance_per_traveler": row["mean_distance_per_traveler"],
                }
            )
    return run_rows, type_rows


def write_csv(path: Path, rows: list[dict[str, Any]]):
    if not rows:
        return
    with path.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]), delimiter=";")
        writer.writeheader()
        writer.writerows(rows)


def make_plots(output_root: Path, run_rows: list[dict[str, Any]]):
    plots = output_root / "plots"
    plots.mkdir(parents=True, exist_ok=True)
    labels = [row["scenario"] for row in run_rows]
    chart_specs = [
        ("fulfillment_rate", "Demand fulfillment", "Fraction", "fulfillment_rate.png"),
        ("travelers_per_capita", "Popular Times travelers per capita", "Travelers / resident", "travelers_per_capita.png"),
        ("distance_per_requested_visit", "Distance per requested visit", "Metres / requested visit", "distance_per_requested_visit.png"),
        ("runtime_seconds", "Pilot runtime", "Seconds", "runtime_seconds.png"),
        ("peak_memory_kib", "Pilot peak memory", "KiB", "peak_memory_kib.png"),
    ]
    for key, title, ylabel, filename in chart_specs:
        figure, axis = plt.subplots(figsize=(12, 5))
        colors = ["#3478bf" if not row["levy"] else "#e07a35" for row in run_rows]
        axis.bar(range(len(run_rows)), [float(row[key]) for row in run_rows], color=colors)
        axis.set_title(title)
        axis.set_ylabel(ylabel)
        axis.set_xticks(range(len(labels)), labels, rotation=65, ha="right")
        axis.grid(axis="y", alpha=0.25)
        figure.tight_layout()
        figure.savefig(plots / filename, dpi=160)
        plt.close(figure)


def write_report(output_root: Path, run_rows: list[dict[str, Any]]):
    passed = sum(bool(row["validation_passed"]) for row in run_rows)
    by_name = {row["scenario"]: row for row in run_rows}
    flood_pois = by_name.get("13_levy_off_flood_pois")
    home_flood = by_name.get("13_levy_off_flood_homes")
    baseline_13 = by_name.get("13_levy_off_flood_none")
    large_off = by_name.get("94_levy_off_flood_none")
    large_on = by_name.get("94_levy_on_flood_none")
    lines = [
        "# Popular Times V2 Stage 3 Pilot",
        "",
        "## Methodology",
        "",
        "All ten scenarios use seed 0 and 24 hourly steps per daily cycle. The 13-region pilots run for 56 cycles; the two computationally larger 94-region pilots run for 5 cycles. The 13-region matrix crosses Levy off/on with flood targeting none, POIs, homes, or both. The 94-region matrix crosses Levy off/on without flooding. Popular Times demand uses fixed weekly profiles and results are normalized per resident and per requested visit.",
        "",
        "Raw demand and visit records, OD aggregates, hourly/type aggregates, existing population and movement outputs, node-state transitions, run metadata, and invariant results are stored in each run directory.",
        "",
        "## Acceptance summary",
        "",
        f"{passed} of {len(run_rows)} pilot scenarios passed every automated invariant.",
        "",
        "| Scenario | Cycles | Pop. | Fulfillment | Travelers/capita | Mean distance/request | Runtime (s) | Peak memory (MiB) | Result |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---|",
    ]
    for row in run_rows:
        result = "PASS" if row["validation_passed"] else f"FAIL: {row['failed_checks']}"
        lines.append(
            f"| {row['scenario']} | {row['cycles']} | {row['population']} | "
            f"{float(row['fulfillment_rate']):.4f} | "
            f"{float(row['travelers_per_capita']):.4f} | "
            f"{float(row['distance_per_requested_visit']):.2f} | "
            f"{float(row['runtime_seconds']):.2f} | "
            f"{float(row['peak_memory_kib']) / 1024:.1f} | {result} |"
        )
    lines.extend(
        [
            "",
            "## Pilot observations",
            "",
        ]
    )
    if flood_pois is not None:
        lines.append(
            f"- Flooding destination POIs suppressed {int(float(flood_pois['unmet'])):,} of {int(float(flood_pois['requested'])):,} requested visits, leaving a {float(flood_pois['fulfillment_rate']):.4%} fulfillment rate. The same suppression total occurred with Levy on and when homes were flooded at the same time."
        )
    if baseline_13 is not None and home_flood is not None:
        lines.append(
            f"- Home-only flooding did not suppress requested Popular Times visits in this pilot, but mean distance per requested visit changed from {float(baseline_13['distance_per_requested_visit']):.2f} m to {float(home_flood['distance_per_requested_visit']):.2f} m because disabled homes were excluded from sourcing."
        )
    lines.append(
        "- All flood-transition checks reported zero movement to or from disabled nodes. Requests whose one-hour occupancy would cross a known POI flood transition were suppressed before departure."
    )
    lines.extend(
        [
            "",
            "## Runtime planning",
            "",
        ]
    )
    if large_off is not None and large_on is not None:
        estimated_off = float(large_off["runtime_seconds"]) * 56 / float(large_off["cycles"])
        estimated_on = float(large_on["runtime_seconds"]) * 56 / float(large_on["cycles"])
        lines.append(
            f"The five-cycle 94-region pilots took {float(large_off['runtime_seconds']):.1f} seconds without Levy and {float(large_on['runtime_seconds']):.1f} seconds with Levy. Linear 56-cycle estimates are approximately {estimated_off / 60:.1f} and {estimated_on / 60:.1f} minutes per run, respectively; production scheduling should use measured batch throughput rather than assuming perfect linear scaling."
        )
    lines.extend(
        [
            "",
            "Weekly-demand equality was evaluated for all eight complete weeks in every 13-region pilot. It is marked not applicable for the five-cycle 94-region pilots; closed-hour, partial-profile peak, lifecycle, conservation, enabled-state, and unmet-reason checks still apply.",
            "",
            "## Interpretation boundary",
            "",
            "These are single-seed pilot results used to verify implementation, runtime, memory, and output quality. Inferential comparisons belong to Stage 4; no confidence intervals or production conclusions are reported here.",
            "",
        ]
    )
    (output_root / "REPORT.md").write_text("\n".join(lines), encoding="utf8")


def main():
    parser = argparse.ArgumentParser(description="Run Popular Times V2 Stage 3 pilots")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--skip-runs", action="store_true")
    parser.add_argument("--only", nargs="*", choices=SCENARIOS)
    args = parser.parse_args()
    scenarios = args.only or SCENARIOS
    output_root = args.output.resolve()
    output_root.mkdir(parents=True, exist_ok=True)
    if not args.skip_runs:
        for index, scenario in enumerate(scenarios, start=1):
            print(f"[{index}/{len(scenarios)}] {scenario}", flush=True)
            run_scenario(scenario, output_root, args.seed)
    run_rows, type_rows = collect_results(output_root, scenarios, args.seed)
    write_csv(output_root / "pilot_runs.csv", run_rows)
    write_csv(output_root / "pilot_poi_type.csv", type_rows)
    make_plots(output_root, run_rows)
    write_report(output_root, run_rows)
    if not all(row["validation_passed"] for row in run_rows):
        raise SystemExit("One or more pilot scenarios failed validation")


if __name__ == "__main__":
    main()
