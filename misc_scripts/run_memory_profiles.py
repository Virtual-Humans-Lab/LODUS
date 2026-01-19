"""
Run TOMACS_simulation memory profiling multiple times for p=1 and p=2.

Example:
    python misc_scripts/run_memory_profiles.py --experiment isolation_tests/Baseline --runs 5
"""

import argparse
import subprocess
from pathlib import Path


def run_cmd(cmd, cwd: Path) -> int:
    """Run a command and stream output; return the exit code."""
    print(f"Running: {' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=cwd)
    if result.returncode != 0:
        print(f"Command failed with exit code {result.returncode}")
    return result.returncode


def main() -> None:
    parser = argparse.ArgumentParser(description="Run TOMACS_simulation memory profiling batches.")
    parser.add_argument("--experiment", "-e", required=True, help="Experiment path (e.g., isolation/Baseline)")
    parser.add_argument("--runs", "-n", type=int, default=1, help="Number of times to run each profiler mode")
    parser.add_argument("--python-exe", default="python", help="Python executable to use")
    parser.add_argument("--sim-script", default="TOMACS_simulation.py", help="Simulation script name")
    args = parser.parse_args()

    project_root = Path(__file__).resolve().parent.parent
    sim_script_path = project_root / args.sim_script

    if not sim_script_path.exists():
        raise FileNotFoundError(f"Simulation script not found: {sim_script_path}")

    total_runs = 0
    failures = 0

    for profiler_mode in (1, 2):
        for i in range(1, args.runs + 1):
            total_runs += 1
            print(f"\n[{total_runs}] Mode p={profiler_mode}, iteration {i}/{args.runs}")
            cmd = [args.python_exe, str(sim_script_path), "--e", args.experiment, "--p", str(profiler_mode)]
            rc = run_cmd(cmd, cwd=project_root)
            if rc != 0:
                failures += 1

    print("\nBatch complete")
    print(f"Total runs: {total_runs}")
    print(f"Failures: {failures}")
    if failures:
        print("Some runs failed; check the console output above for details.")


if __name__ == "__main__":
    main()
