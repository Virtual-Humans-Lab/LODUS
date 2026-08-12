"""Run and report the controlled quantitative-performance benchmark matrix.

The default command repairs the two known incomplete shelter domain runs, then
executes the benchmark catalog serially.  The controlled output tree is kept
separate from production batches and every run is safe to resume.
"""

from __future__ import annotations

import argparse
import csv
from dataclasses import dataclass, field
from datetime import datetime, timezone
import io
import json
from pathlib import Path
import statistics
import subprocess
import sys
from typing import Any, Iterable


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
OUTPUT_LOGS = PROJECT_ROOT / "output_logs"
DEFAULT_OUTPUT = OUTPUT_LOGS / "quantitative_performance"
RESULTS_DIR = PROJECT_ROOT / "docs" / "results" / "quantitative_performance"
TEX_PATH = (
    PROJECT_ROOT
    / "thesis"
    / "flood_chapter"
    / "_5e-quantitative-performance-evaluation.tex"
)
BEGIN_MARKER = "% BEGIN GENERATED PERFORMANCE TABLES"
END_MARKER = "% END GENERATED PERFORMANCE TABLES"
REPETITIONS = tuple(range(5))
EXPECTED_CONFIGURATIONS = 48
EXPECTED_RUNS = EXPECTED_CONFIGURATIONS * len(REPETITIONS)
SHELTER_DOMAIN_REPAIRS = (
    ("demand_0.5x", 2),
    ("response_0.05", 4),
)


@dataclass(frozen=True)
class PerformanceConfig:
    code: str
    table_group: str
    key: str
    description: str
    regions: int
    cycles: int
    simulator: str
    experiment: str
    validation_json: tuple[str, ...] = ()
    required_csv: tuple[str, ...] = ()
    overrides: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class RunInspection:
    status: str
    detail: str
    path: Path
    runtime_seconds: float | None = None
    peak_memory_mib: float | None = None
    max_blob_count: int | None = None
    commit_sha: str | None = None


def _stage_config(
    code: str,
    group: str,
    stage: str,
    scenario: str,
    description: str,
) -> PerformanceConfig:
    validations = ["popular_times_validation.json"]
    if stage == "stage6":
        validations.append("levy_v2_validation.json")
    directory = "production" if stage == "stage4" else stage
    return PerformanceConfig(
        code=code,
        table_group=group,
        key=f"{stage}_{scenario}",
        description=description,
        regions=int(scenario.split("_", 1)[0]),
        cycles=56,
        simulator="sector",
        experiment=f"popular_times_v2/{directory}/{scenario}",
        validation_json=tuple(validations),
    )


def build_catalog() -> tuple[PerformanceConfig, ...]:
    """Return the fixed 48-configuration, inpatient-free benchmark catalog."""
    catalog: list[PerformanceConfig] = []

    routine = (
        ("R01", "stage4", "13_levy_off_flood_none", "Popular Times only"),
        ("R02", "stage4", "13_levy_on_flood_none", "Popular Times + probabilistic Lévy"),
        ("R03", "stage6", "13_levy_v2_flood_none", "Popular Times + attendance Lévy V2"),
        ("R04", "stage4", "94_levy_off_flood_none", "Popular Times only"),
        ("R05", "stage4", "94_levy_on_flood_none", "Popular Times + probabilistic Lévy"),
        ("R06", "stage6", "94_levy_v2_flood_none", "Popular Times + attendance Lévy V2"),
    )
    catalog.extend(
        _stage_config(code, "routine", stage, scenario, description)
        for code, stage, scenario, description in routine
    )

    adaptations: list[tuple[str, str, str, str]] = []
    index = 1
    for regions in (13, 94):
        for flood, description in (
            ("pois", "POI flood; demand suppression"),
            ("homes", "Home flood; demand suppression"),
            ("both", "Home + POI flood; demand suppression"),
        ):
            adaptations.append(
                (
                    f"A{index:02d}",
                    "stage4",
                    f"{regions}_levy_on_flood_{flood}",
                    description,
                )
            )
            index += 1
        for levy, description in (
            ("off", "Home + POI flood; nearest-POI adaptation"),
            ("on", "Home + POI flood; Lévy + nearest-POI adaptation"),
        ):
            adaptations.append(
                (
                    f"A{index:02d}",
                    "stage5",
                    f"{regions}_levy_{levy}_flood_both_reroute",
                    description,
                )
            )
            index += 1
    catalog.extend(
        _stage_config(code, "adaptation", stage, scenario, description)
        for code, stage, scenario, description in adaptations
    )

    disruptions: list[tuple[str, str, str, str]] = []
    index = 1
    for regions in (13, 94):
        for flood, description in (
            ("destinations", "Flooded activity and commute destinations"),
            ("homes", "Flooded homes"),
            ("all", "Flooded homes and destinations"),
            ("all_pt_reroute", "All-node flood + nearest-POI adaptation"),
        ):
            disruptions.append(
                (
                    f"F{index:02d}",
                    "stage6",
                    f"{regions}_levy_v2_flood_{flood}",
                    description,
                )
            )
            index += 1
    catalog.extend(
        _stage_config(code, "disruption", stage, scenario, description)
        for code, stage, scenario, description in disruptions
    )

    # Import lazily so catalog-only tests do not initialize shelter experiment
    # dependencies unless this section of the catalog is requested.
    from shelter_experiments import research_catalog

    shelter_names = (
        ("S01", "v3_reference", "Reference"),
        ("S02", "v3_reference_reallocate", "Reference with reallocation"),
        ("S03", "capacity_0.5x", "Capacity 0.5x"),
        ("S04", "capacity_2x", "Capacity 2x"),
        ("S05", "capacity_5x", "Capacity 5x"),
        ("S06", "capacity_15x", "Capacity 15x"),
        ("S07", "response_0.005", "Daily response 0.5%"),
        ("S08", "response_0.02", "Daily response 2%"),
        ("S09", "response_0.05", "Daily response 5%"),
        ("S10", "demand_0.25x", "Exposure demand 0.25x"),
        ("S11", "demand_0.5x", "Exposure demand 0.5x"),
        ("S12", "failure_largest_with_reallocation", "Largest-shelter failure"),
        (
            "S13",
            "failure_top_10_percent_capacity_with_reallocation",
            "Top-10% capacity failures",
        ),
    )
    shelter_catalog = research_catalog()
    for code, scenario, description in shelter_names:
        experiment, overrides = shelter_catalog[scenario]
        catalog.append(
            PerformanceConfig(
                code=code,
                table_group="shelter",
                key=scenario,
                description=description,
                regions=94,
                cycles=14,
                simulator="shelter",
                experiment=experiment,
                required_csv=("shelter_cycle.csv",),
                overrides=overrides,
            )
        )

    dialysis_names = (
        ("D01", "K01_ReducedModerate", "Reduced moderate"),
        ("D02", "K02_MoinhosNoRecovery", "Moinhos persistent outage"),
        ("D03", "K03_MoinhosFastRecovery", "Moinhos rapid recovery"),
        ("D04", "K04_HistoricalClinicFlood", "Historical clinic flood"),
        ("D05", "K05_SyntheticETAFlood", "Synthetic water-source flood"),
        ("D06", "K06_CombinedMoinhosMenino", "Combined reduced disruption"),
        ("D07", "K07_ReducedAboveCapacity", "Reduced above capacity"),
        ("D08", "K08_HighCapacityClinicFailure", "One high-capacity failure"),
        ("D09", "K09_MatchedLowCapacityFailures", "Matched small failures"),
        ("D10", "K10_CompleteModerate", "Complete-network moderate"),
        ("D11", "K11_CompleteCombined", "Complete-network combined"),
    )
    for code, experiment_name, description in dialysis_names:
        catalog.append(
            PerformanceConfig(
                code=code,
                table_group="dialysis",
                key=experiment_name,
                description=f"{description} ({experiment_name.split('_', 1)[0]})",
                regions=94 if code in {"D10", "D11"} else 13,
                cycles=10,
                simulator="sector",
                experiment=f"dialysis_core/{experiment_name}",
                required_csv=("dialysis_cycle.csv", "dialysis_events.csv"),
            )
        )

    if len(catalog) != EXPECTED_CONFIGURATIONS:
        raise AssertionError(
            f"performance catalog has {len(catalog)} configurations, expected "
            f"{EXPECTED_CONFIGURATIONS}"
        )
    if len({item.key for item in catalog}) != len(catalog):
        raise AssertionError("performance catalog configuration keys are not unique")
    if any("inpatient" in repr(item).lower() for item in catalog):
        raise AssertionError("inpatient-care simulations are excluded")
    return tuple(catalog)


def expand_runs(
    catalog: Iterable[PerformanceConfig] | None = None,
) -> tuple[tuple[PerformanceConfig, int], ...]:
    selected = tuple(catalog or build_catalog())
    return tuple((config, repetition) for config in selected for repetition in REPETITIONS)


def run_path(output_root: Path, config: PerformanceConfig, repetition: int) -> Path:
    return output_root / config.table_group / config.key / f"seed_{repetition:03d}"


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _nonempty_csv(path: Path) -> bool:
    if not path.is_file():
        return False
    with path.open("r", encoding="utf-8-sig", newline="") as stream:
        return sum(1 for _ in csv.reader(stream)) > 1


def inspect_run(
    config: PerformanceConfig,
    repetition: int,
    output_root: Path = DEFAULT_OUTPUT,
    expected_commit: str | None = None,
) -> RunInspection:
    """Check every artifact needed before a controlled run may be skipped."""
    path = run_path(output_root, config, repetition)
    metadata_path = path / "run_metadata.json"
    blob_path = path / "data_frames" / "blob_count_global.csv"
    if not metadata_path.is_file():
        return RunInspection("pending", "run_metadata.json is missing", path)
    try:
        metadata = _read_json(metadata_path)
    except (OSError, json.JSONDecodeError) as error:
        return RunInspection("pending", f"metadata is unreadable: {error}", path)
    try:
        runtime = float(metadata["runtime_seconds"])
        peak_mib = float(metadata["peak_memory_kib"]) / 1024.0
        max_blob = int(metadata["max_blob_count"])
        cycles = int(metadata.get("simulation_parameters", {}).get("total_cycles"))
        seed = int(metadata["seed"])
    except (KeyError, TypeError, ValueError) as error:
        return RunInspection("pending", f"metadata performance field is missing: {error}", path)
    commit_sha = metadata.get("commit_sha")
    expected = (
        metadata.get("status") == "complete"
        and metadata.get("experiment") == config.experiment
        and seed == repetition
        and cycles == config.cycles
        and runtime >= 0
        and peak_mib > 0
        and max_blob >= 0
    )
    if not expected:
        return RunInspection("pending", "metadata does not match the catalog run", path)
    if expected_commit and commit_sha != expected_commit:
        return RunInspection(
            "pending",
            f"run commit {commit_sha or 'unknown'} does not match {expected_commit}",
            path,
        )
    if not blob_path.is_file():
        return RunInspection("pending", "blob_count_global.csv is missing", path)
    try:
        with blob_path.open("r", encoding="utf-8-sig", newline="") as stream:
            rows = list(csv.DictReader(stream, delimiter=";"))
        recorded = [int(float(row["Blob Count"])) for row in rows]
    except (OSError, KeyError, TypeError, ValueError) as error:
        return RunInspection("pending", f"global blob counts are unreadable: {error}", path)
    if not recorded:
        return RunInspection("pending", "global blob count series is empty", path)
    if max(recorded) != max_blob:
        return RunInspection(
            "invalid",
            f"metadata maximum {max_blob} differs from recorded maximum {max(recorded)}",
            path,
        )
    data_path = path / "data_frames"
    for name in config.validation_json:
        artifact = data_path / name
        try:
            validation = _read_json(artifact)
        except (OSError, json.JSONDecodeError) as error:
            return RunInspection("pending", f"{name} is missing or unreadable: {error}", path)
        if validation.get("passed") is not True:
            return RunInspection("invalid", f"{name} reports a failed validation", path)
    for name in config.required_csv:
        if not _nonempty_csv(data_path / name):
            return RunInspection("pending", f"{name} is missing or empty", path)
    return RunInspection(
        "complete",
        "all controlled performance artifacts are complete",
        path,
        runtime_seconds=runtime,
        peak_memory_mib=peak_mib,
        max_blob_count=max_blob,
        commit_sha=commit_sha,
    )


def git_commit() -> str | None:
    try:
        return subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=PROJECT_ROOT,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return None


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _atomic_write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(content, encoding="utf-8", newline="\n")
    temporary.replace(path)


def preserve_partial(path: Path) -> Path | None:
    if not path.exists():
        return None
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    candidate = path.with_name(f"{path.name}.partial-{timestamp}")
    suffix = 1
    while candidate.exists():
        candidate = path.with_name(f"{path.name}.partial-{timestamp}-{suffix}")
        suffix += 1
    path.rename(candidate)
    return candidate


def _relative_run_name(path: Path) -> str:
    try:
        return path.resolve().relative_to(OUTPUT_LOGS.resolve()).as_posix()
    except ValueError as error:
        raise ValueError("benchmark output must remain under output_logs") from error


def _command(config: PerformanceConfig, repetition: int, path: Path) -> list[str]:
    command = [
        sys.executable,
        str(PROJECT_ROOT / ("shelter_simulator.py" if config.simulator == "shelter" else "sector_simulation.py")),
        "--e",
        config.experiment,
        "--n",
        _relative_run_name(path),
        "--seed",
        str(repetition),
    ]
    if config.simulator == "shelter":
        command.append("--no-shelter-png")
        if config.overrides:
            command.extend(
                ["--overrides-json", json.dumps(config.overrides, ensure_ascii=False)]
            )
    else:
        command.append("--no-dialysis-png")
    return command


def _run_streaming(command: list[str], log_path: Path) -> int:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("w", encoding="utf-8", newline="\n") as log:
        process = subprocess.Popen(
            command,
            cwd=PROJECT_ROOT,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            bufsize=1,
        )
        assert process.stdout is not None
        for line in process.stdout:
            print(line, end="", flush=True)
            log.write(line)
        return process.wait()


def execute_run(
    config: PerformanceConfig,
    repetition: int,
    output_root: Path,
    expected_commit: str | None,
) -> RunInspection:
    existing = inspect_run(config, repetition, output_root, expected_commit)
    if existing.status == "complete":
        return existing
    preserve_partial(existing.path)
    existing.path.mkdir(parents=True, exist_ok=True)
    return_code = _run_streaming(
        _command(config, repetition, existing.path),
        existing.path / "orchestrator.log",
    )
    inspected = inspect_run(config, repetition, output_root, expected_commit)
    if return_code or inspected.status != "complete":
        failure = {
            "status": inspected.status,
            "detail": inspected.detail,
            "return_code": return_code,
            "updated_at_utc": _utc_now(),
        }
        _atomic_write(
            existing.path / "orchestrator_failure.json",
            json.dumps(failure, indent=2, ensure_ascii=False) + "\n",
        )
    return inspected


def shelter_domain_repair_state() -> list[tuple[str, int, bool]]:
    result = []
    for scenario, seed in SHELTER_DOMAIN_REPAIRS:
        metadata = (
            PROJECT_ROOT
            / "results"
            / "shelter"
            / scenario
            / f"seed_{seed:03d}"
            / "run_metadata.json"
        )
        try:
            complete = _read_json(metadata).get("status") == "complete"
        except (OSError, json.JSONDecodeError):
            complete = False
        result.append((scenario, seed, complete))
    return result


def repair_shelter_domain_runs() -> bool:
    missing = [row for row in shelter_domain_repair_state() if not row[2]]
    if not missing:
        return True
    command = [
        sys.executable,
        str(PROJECT_ROOT / "shelter_experiments.py"),
        "--catalog",
        "research",
        "--seeds",
        "0-4",
        "--jobs",
        "1",
        "--scenario",
        "demand_0.5x",
        "--scenario",
        "response_0.05",
    ]
    print("Repairing the two selected shelter domain scenarios serially.", flush=True)
    completed = subprocess.run(command, cwd=PROJECT_ROOT, check=False)
    return completed.returncode == 0 and all(
        row[2] for row in shelter_domain_repair_state()
    )


def collect_inspections(
    catalog: Iterable[PerformanceConfig],
    output_root: Path,
    expected_commit: str | None,
) -> dict[tuple[str, int], RunInspection]:
    return {
        (config.key, repetition): inspect_run(
            config, repetition, output_root, expected_commit
        )
        for config, repetition in expand_runs(catalog)
    }


def scenario_summaries(
    catalog: Iterable[PerformanceConfig],
    inspections: dict[tuple[str, int], RunInspection],
) -> list[dict[str, Any]]:
    summaries = []
    for config in catalog:
        runs = [inspections[(config.key, repetition)] for repetition in REPETITIONS]
        complete = [run for run in runs if run.status == "complete"]
        missing = [
            repetition
            for repetition, run in zip(REPETITIONS, runs)
            if run.status != "complete"
        ]
        summary: dict[str, Any] = {
            "code": config.code,
            "table_group": config.table_group,
            "scenario": config.key,
            "description": config.description,
            "experiment": config.experiment,
            "regions": config.regions,
            "cycles": config.cycles,
            "required_repetitions": len(REPETITIONS),
            "completed_repetitions": len(complete),
            "missing_repetitions": ",".join(map(str, missing)),
            "mean_max_blob_count": "",
            "mean_runtime_seconds": "",
            "runtime_seconds_per_cycle": "",
            "mean_peak_working_set_mib": "",
            "commit_sha": "",
        }
        if len(complete) == len(REPETITIONS):
            mean_runtime = statistics.fmean(
                run.runtime_seconds for run in complete if run.runtime_seconds is not None
            )
            summary.update(
                {
                    "mean_max_blob_count": statistics.fmean(
                        run.max_blob_count for run in complete if run.max_blob_count is not None
                    ),
                    "mean_runtime_seconds": mean_runtime,
                    "runtime_seconds_per_cycle": mean_runtime / config.cycles,
                    "mean_peak_working_set_mib": statistics.fmean(
                        run.peak_memory_mib for run in complete if run.peak_memory_mib is not None
                    ),
                    "commit_sha": complete[0].commit_sha or "",
                }
            )
        summaries.append(summary)
    return summaries


def _csv_text(rows: list[dict[str, Any]], fieldnames: list[str]) -> str:
    output = io.StringIO(newline="")
    writer = csv.DictWriter(output, fieldnames=fieldnames, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return output.getvalue()


def write_aggregates(
    catalog: tuple[PerformanceConfig, ...],
    inspections: dict[tuple[str, int], RunInspection],
    summaries: list[dict[str, Any]],
) -> None:
    run_rows: list[dict[str, Any]] = []
    for config, repetition in expand_runs(catalog):
        run = inspections[(config.key, repetition)]
        run_rows.append(
            {
                "code": config.code,
                "table_group": config.table_group,
                "scenario": config.key,
                "experiment": config.experiment,
                "repetition": repetition,
                "status": run.status,
                "detail": run.detail,
                "runtime_seconds": "" if run.runtime_seconds is None else run.runtime_seconds,
                "runtime_seconds_per_cycle": "" if run.runtime_seconds is None else run.runtime_seconds / config.cycles,
                "peak_working_set_mib": "" if run.peak_memory_mib is None else run.peak_memory_mib,
                "max_blob_count": "" if run.max_blob_count is None else run.max_blob_count,
                "commit_sha": run.commit_sha or "",
            }
        )
    _atomic_write(
        RESULTS_DIR / "performance_runs.csv",
        _csv_text(run_rows, list(run_rows[0])),
    )
    _atomic_write(
        RESULTS_DIR / "performance_scenarios.csv",
        _csv_text(summaries, list(summaries[0])),
    )
    complete_runs = sum(row["status"] == "complete" for row in run_rows)
    complete_scenarios = sum(
        row["completed_repetitions"] == len(REPETITIONS) for row in summaries
    )
    report = "\n".join(
        [
            "# Controlled Quantitative Performance Benchmarks",
            "",
            f"Updated: {_utc_now()}",
            "",
            f"- Catalog: {len(catalog)} configurations, {len(run_rows)} serial runs.",
            f"- Complete runs: {complete_runs}/{EXPECTED_RUNS}.",
            f"- Complete configurations: {complete_scenarios}/{EXPECTED_CONFIGURATIONS}.",
            "- Repetitions: matched seeds 0–4 for computational performance.",
            "- Metrics: runtime, runtime per cycle, peak process working set, and maximum global blob count.",
            "- Exclusions: inpatient care and TraceMalloc.",
            "",
            "Run or resume the full matrix from the repository root:",
            "",
            "```powershell",
            r".\.venv\Scripts\python.exe .\misc_scripts\run_quantitative_performance.py",
            "```",
            "",
        ]
    )
    _atomic_write(RESULTS_DIR / "REPORT.md", report)


def _tex_escape(value: Any) -> str:
    text = str(value)
    replacements = {
        "\\": r"\textbackslash{}",
        "&": r"\&",
        "%": r"\%",
        "$": r"\$",
        "#": r"\#",
        "_": r"\_",
        "{": r"\{",
        "}": r"\}",
    }
    return "".join(replacements.get(char, char) for char in text)


TABLES = (
    ("routine", "Routine mobility", "tab:quantitative-performance-routine"),
    ("adaptation", "Popular Times suppression and Stage 5 adaptation", "tab:quantitative-performance-adaptation"),
    ("disruption", "Stage 6 flood-aware commuting", "tab:quantitative-performance-disruption"),
    ("shelter", "Shelter simulations", "tab:quantitative-performance-shelter"),
    ("dialysis", "Dialysis simulations", "tab:quantitative-performance-dialysis"),
)


def render_generated_tables(summaries: list[dict[str, Any]]) -> str:
    lines = [
        "\\begingroup",
        "\\footnotesize",
        "\\setlength{\\tabcolsep}{2.6pt}",
    ]
    for group, caption, label in TABLES:
        rows = [row for row in summaries if row["table_group"] == group]
        lines.extend(
            [
                "\\begin{table}[htbp]",
                "\\centering",
                f"\\caption{{Controlled performance for {caption.lower()}.}}",
                f"\\label{{{label}}}",
                "\\begin{tabularx}{\\textwidth}{@{}>{\\raggedright\\arraybackslash}Xrrrrrrr@{}}",
                "\\toprule",
                "Configuration & Regions & Cycles & Reps. & "
                "\\begin{tabular}[c]{@{}c@{}}Mean max.\\\\blobs\\end{tabular} & "
                "\\begin{tabular}[c]{@{}c@{}}Mean runtime\\\\(s)\\end{tabular} & "
                "s/cycle & "
                "\\begin{tabular}[c]{@{}c@{}}Mean peak\\\\working set\\\\(MiB)\\end{tabular} \\\\",
                "\\midrule",
            ]
        )
        for row in rows:
            if row["completed_repetitions"] == len(REPETITIONS):
                lines.append(
                    f"{_tex_escape(row['code'] + ' ' + row['description'])} & "
                    f"{row['regions']} & {row['cycles']} & {len(REPETITIONS)} & "
                    f"{float(row['mean_max_blob_count']):.1f} & "
                    f"{float(row['mean_runtime_seconds']):.3f} & "
                    f"{float(row['runtime_seconds_per_cycle']):.4f} & "
                    f"{float(row['mean_peak_working_set_mib']):.1f} \\\\" 
                )
            else:
                missing = row["missing_repetitions"] or "unknown"
                notice = (
                    f"MISSING DATA: {row['code']} scenario {row['scenario']} "
                    f"({row['experiment']}) requires "
                    f"repetitions 0--4; missing repetitions: {missing}."
                )
                lines.append(
                    "\\multicolumn{8}{p{0.96\\textwidth}}"
                    f"{{\\textcolor{{red}}{{\\textbf{{{_tex_escape(notice)}}}}}}} \\\\"
                )
        lines.extend(
            [
                "\\bottomrule",
                "\\end{tabularx}",
                "\\end{table}",
                "",
            ]
        )
    lines.append("\\endgroup")
    return "\n".join(lines).rstrip() + "\n"


def replace_generated_block(tex_path: Path, generated: str) -> None:
    content = tex_path.read_text(encoding="utf-8")
    if content.count(BEGIN_MARKER) != 1 or content.count(END_MARKER) != 1:
        raise ValueError("TeX generated-table markers must each occur exactly once")
    before, remainder = content.split(BEGIN_MARKER, 1)
    _, after = remainder.split(END_MARKER, 1)
    replacement = (
        before
        + BEGIN_MARKER
        + "\n"
        + generated.rstrip()
        + "\n"
        + END_MARKER
        + after
    )
    _atomic_write(tex_path, replacement)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run the 48-scenario controlled performance matrix serially"
    )
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--audit",
        action="store_true",
        help="write summaries and TeX missing-data notices without running simulations",
    )
    mode.add_argument(
        "--dry-run",
        action="store_true",
        help="print the audit without running simulations or writing files",
    )
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    output_root = args.output.resolve()
    _relative_run_name(output_root / "path-check")
    catalog = build_catalog()
    runs = expand_runs(catalog)
    commit = git_commit()
    inspections = collect_inspections(catalog, output_root, commit)
    missing = [
        (config, repetition, inspections[(config.key, repetition)])
        for config, repetition in runs
        if inspections[(config.key, repetition)].status != "complete"
    ]
    domain_missing = [row for row in shelter_domain_repair_state() if not row[2]]
    print(
        f"Catalog: {len(catalog)} configurations, {len(runs)} runs; "
        f"{len(missing)} controlled runs and {len(domain_missing)} selected "
        "shelter domain runs are missing.",
        flush=True,
    )
    if args.dry_run:
        for scenario, seed, _ in domain_missing:
            print(f"DOMAIN MISSING: {scenario}/seed_{seed:03d}")
        for config, repetition, inspection in missing:
            print(
                f"PERFORMANCE MISSING: {config.code} repetition {repetition}: "
                f"{inspection.detail}"
            )
        return 0

    domain_ok = True
    if not args.audit:
        domain_ok = repair_shelter_domain_runs()
        for index, (config, repetition) in enumerate(runs, start=1):
            current = inspect_run(config, repetition, output_root, commit)
            if current.status == "complete":
                print(f"[{index}/{EXPECTED_RUNS}] {config.code} repetition {repetition}: complete; skipping")
                continue
            print(f"[{index}/{EXPECTED_RUNS}] {config.code} repetition {repetition}: running", flush=True)
            result = execute_run(config, repetition, output_root, commit)
            if result.status != "complete":
                print(f"FAILED: {config.code} repetition {repetition}: {result.detail}", flush=True)

    inspections = collect_inspections(catalog, output_root, commit)
    summaries = scenario_summaries(catalog, inspections)
    write_aggregates(catalog, inspections, summaries)
    replace_generated_block(TEX_PATH, render_generated_tables(summaries))
    remaining = sum(run.status != "complete" for run in inspections.values())
    print(
        f"Controlled performance status: {EXPECTED_RUNS - remaining}/{EXPECTED_RUNS} "
        "runs complete; summaries and TeX tables refreshed.",
        flush=True,
    )
    if args.audit:
        return 0
    return 0 if domain_ok and remaining == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
