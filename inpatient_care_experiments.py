"""Run the reconstructed and capacity-constrained inpatient care scenarios."""

from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import csv
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

import pandas as pd


REPO_ROOT = Path(__file__).resolve().parent
SCENARIOS = [
    "inpatient_care/ReferenceDemandOverflow",
    "inpatient_care/ReferenceDemandQueue",
    "inpatient_care/HighDemandOverflow",
    "inpatient_care/HighDemandQueue",
    "inpatient_care/TwoFacilityOverflow",
    "inpatient_care/TwoFacilityQueue",
    "inpatient_care/CIDRoutingQueue",
]
SPECIALIZED_CSVS = [
    "inpatient_events.csv",
    "inpatient_step.csv",
    "inpatient_bed_step.csv",
    "inpatient_region_step.csv",
    "inpatient_locations.csv",
]


def parse_seeds(value: str) -> list[int]:
    seeds = []
    for item in value.split(","):
        item = item.strip()
        if not item:
            continue
        if "-" in item:
            start_text, end_text = item.split("-", 1)
            start, end = int(start_text), int(end_text)
            if end < start:
                raise ValueError("Seed range end must be >= start")
            seeds.extend(range(start, end + 1))
        else:
            seeds.append(int(item))
    return sorted(set(seeds))


def _is_complete(path: Path) -> bool:
    metadata = path / "run_metadata.json"
    data_frames = path / "data_frames"
    required = tuple(
        data_frames / filename for filename in SPECIALIZED_CSVS
    )
    if not metadata.is_file() or not all(item.is_file() for item in required):
        return False
    try:
        complete = (
            json.loads(metadata.read_text(encoding="utf8")).get("status")
            == "complete"
        )
        with (data_frames / "inpatient_step.csv").open(
            encoding="utf-8-sig"
        ) as handle:
            step_header = handle.readline()
        return complete and {
            "Global Population",
            "Population Delta From Initial",
        }.issubset(step_header.rstrip("\n").split(";"))
    except (OSError, json.JSONDecodeError):
        return False


def _preserve_partial(path: Path):
    if not path.exists():
        return
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    path.rename(path.with_name(f"{path.name}.partial-{timestamp}"))


def run_one(
    scenario: str,
    seed: int,
    results_root: Path,
    python_executable: str,
) -> dict:
    scenario_id = Path(scenario).name
    run_path = results_root / scenario_id / f"seed_{seed:03d}"
    if _is_complete(run_path):
        return {
            "scenario": scenario,
            "scenario_id": scenario_id,
            "seed": seed,
            "status": "skipped",
            "path": str(run_path),
        }
    temporary_name = f"inpatient_care_batch/{scenario_id}/seed_{seed:03d}"
    temporary_path = REPO_ROOT / "output_logs" / temporary_name
    _preserve_partial(run_path)
    _preserve_partial(temporary_path)
    command = [
        python_executable,
        str(REPO_ROOT / "sector_simulation.py"),
        "--e",
        scenario,
        "--n",
        temporary_name,
        "--seed",
        str(seed),
        "--no-inpatient-care-png",
        "--no-inpatient-care-plots",
    ]
    completed = subprocess.run(
        command, cwd=REPO_ROOT, capture_output=True, text=True
    )
    run_path.parent.mkdir(parents=True, exist_ok=True)
    if completed.returncode == 0 and _is_complete(temporary_path):
        shutil.move(str(temporary_path), str(run_path))
        status = "complete"
    else:
        run_path.mkdir(parents=True, exist_ok=True)
        (run_path / "run_metadata.json").write_text(
            json.dumps(
                {
                    "status": "failed",
                    "scenario": scenario,
                    "seed": seed,
                    "return_code": completed.returncode,
                },
                indent=2,
            ),
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


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def verify_determinism(
    scenario: str,
    seed: int,
    results_root: Path,
    python_executable: str,
) -> bool:
    scenario_id = Path(scenario).name
    reference = results_root / scenario_id / f"seed_{seed:03d}"
    if not _is_complete(reference):
        raise ValueError(
            f"Cannot verify determinism for incomplete run: {reference}"
        )
    with tempfile.TemporaryDirectory(
        prefix="lodus-inpatient-determinism-"
    ) as temporary:
        repeated_root = Path(temporary)
        repeated = run_one(
            scenario, seed, repeated_root, python_executable
        )
        if repeated["status"] != "complete":
            raise RuntimeError(
                f"Determinism rerun failed: {repeated['path']}"
            )
        repeated_path = Path(repeated["path"])
        rows = []
        for filename in SPECIALIZED_CSVS:
            reference_hash = _sha256(
                reference / "data_frames" / filename
            )
            repeated_hash = _sha256(
                repeated_path / "data_frames" / filename
            )
            rows.append(
                {
                    "scenario": scenario,
                    "seed": seed,
                    "file": filename,
                    "reference_sha256": reference_hash,
                    "repeated_sha256": repeated_hash,
                    "passed": reference_hash == repeated_hash,
                }
            )
    with (results_root / "determinism_audit.csv").open(
        "w", encoding="utf8", newline=""
    ) as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    return all(row["passed"] for row in rows)


def write_summary(results_root: Path, records: list[dict]):
    rows = []
    for record in records:
        row = record.copy()
        if record["status"] not in {"complete", "skipped"}:
            rows.append(row)
            continue
        path = Path(record["path"])
        events = pd.read_csv(
            path / "data_frames" / "inpatient_events.csv",
            sep=";",
            encoding="utf-8-sig",
        )
        steps = pd.read_csv(
            path / "data_frames" / "inpatient_step.csv",
            sep=";",
            encoding="utf-8-sig",
        )
        row.update(
            {
                "demand": int(
                    events.loc[
                        events["Event"] == "demanded", "Population"
                    ].sum()
                ),
                "admitted": int(
                    events.loc[
                        events["Event"] == "admitted", "Population"
                    ].sum()
                ),
                "discharged": int(
                    events.loc[
                        events["Event"] == "discharged", "Population"
                    ].sum()
                ),
                "waiting_end": int(steps.iloc[-1]["Waiting"]),
                "maximum_occupancy": int(steps["Occupancy"].max()),
                "maximum_overflow": int(steps["Overflow"].max()),
                "maximum_admission_delay": int(
                    steps["Maximum Admission Delay Steps"].max()
                ),
            }
        )
        rows.append(row)
    results_root.mkdir(parents=True, exist_ok=True)
    fields = sorted({key for row in rows for key in row})
    with (results_root / "summary.csv").open(
        "w", encoding="utf8", newline=""
    ) as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--scenarios", nargs="*", default=SCENARIOS)
    parser.add_argument(
        "--seeds",
        default="0",
        help="Comma-separated seeds or inclusive range, such as 0-29.",
    )
    parser.add_argument(
        "--results-root",
        type=Path,
        default=REPO_ROOT / "results" / "inpatient_care",
    )
    parser.add_argument("--python", default=sys.executable)
    parser.add_argument(
        "--jobs",
        type=int,
        default=1,
        help="Number of scenario subprocesses to run concurrently.",
    )
    parser.add_argument(
        "--skip-determinism-check",
        action="store_true",
        help="Do not repeat the first run and compare specialized CSV hashes.",
    )
    args = parser.parse_args()
    if args.jobs < 1:
        parser.error("--jobs must be at least 1")
    seeds = parse_seeds(args.seeds)
    tasks = [
        (scenario, seed)
        for scenario in args.scenarios
        for seed in seeds
    ]
    records = []
    if args.jobs == 1:
        for scenario, seed in tasks:
            record = run_one(
                scenario, seed, args.results_root, args.python
            )
            records.append(record)
            print(f"{scenario} seed={seed}: {record['status']}")
    else:
        with ThreadPoolExecutor(max_workers=args.jobs) as executor:
            futures = {
                executor.submit(
                    run_one,
                    scenario,
                    seed,
                    args.results_root,
                    args.python,
                ): (scenario, seed)
                for scenario, seed in tasks
            }
            for future in as_completed(futures):
                scenario, seed = futures[future]
                record = future.result()
                records.append(record)
                print(f"{scenario} seed={seed}: {record['status']}")
    records.sort(key=lambda row: (row["scenario"], row["seed"]))
    write_summary(args.results_root, records)
    deterministic = True
    if records and not args.skip_determinism_check:
        deterministic = verify_determinism(
            args.scenarios[0],
            seeds[0],
            args.results_root,
            args.python,
        )
    (args.results_root / "batch_manifest.json").write_text(
        json.dumps(
            {
                "scenarios": args.scenarios,
                "seeds": seeds,
                "records": records,
                "determinism_check_passed": deterministic,
            },
            indent=2,
        ),
        encoding="utf8",
    )
    return int(
        any(row["status"] == "failed" for row in records)
        or not deterministic
    )


if __name__ == "__main__":
    raise SystemExit(main())
