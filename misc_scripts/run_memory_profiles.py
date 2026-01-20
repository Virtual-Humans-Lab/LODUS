"""
Run TOMACS_simulation memory profiling multiple times for p=1 and p=2.

This script allows running memory profiling on one or multiple experiments,
executing each experiment multiple times with profiler modes p=1 and p=2.

Usage Examples:
    
    Single experiment with 5 runs:
        python misc_scripts/run_memory_profiles.py --experiment isolation_tests/Baseline --runs 5
    
    Multiple experiments with default 1 run each:
        python misc_scripts/run_memory_profiles.py --experiment isolation_tests/Baseline isolation_tests/Baseline-Iso_25 isolation_tests/Baseline-Iso_50
    
    Multiple experiments with 3 runs each:
        python misc_scripts/run_memory_profiles.py --experiment epidemic_tests/Baseline epidemic_tests/High_Transmission --runs 3
    
    Using short flags:
        python misc_scripts/run_memory_profiles.py -e levy_tests/exp1 levy_tests/exp2 -n 10

Arguments:
    --experiment, -e : One or more experiment paths (e.g., isolation_tests/Baseline)
    --runs, -n : Number of times to run each profiler mode per experiment (default: 1)
    --python-exe : Python executable to use (default: python)
    --sim-script : Simulation script name (default: TOMACS_simulation.py)

Output:
    Memory profiling results are saved to output_logs/{experiment_path}/
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
    parser.add_argument("--experiment", "-e", nargs="+", required=True, help="One or more experiment paths (e.g., isolation/Baseline)")
    parser.add_argument("--runs", "-n", type=int, default=1, help="Number of times to run each profiler mode")
    parser.add_argument("--python-exe", default="python", help="Python executable to use")
    parser.add_argument("--sim-script", default="TOMACS_simulation.py", help="Simulation script name")
    args = parser.parse_args()

    project_root = Path(__file__).resolve().parent.parent
    sim_script_path = project_root / args.sim_script

    if not sim_script_path.exists():
        raise FileNotFoundError(f"Simulation script not found: {sim_script_path}")

    experiments = args.experiment if isinstance(args.experiment, list) else [args.experiment]
    total_runs = 0
    failures = 0

    print(f"Running {len(experiments)} experiment(s) with {args.runs} run(s) each for profiler modes 1 and 2")
    print(f"Total expected runs: {len(experiments) * args.runs * 2}\n")

    for exp_idx, experiment in enumerate(experiments, 1):
        print(f"\n{'='*60}")
        print(f"Experiment {exp_idx}/{len(experiments)}: {experiment}")
        print(f"{'='*60}")
        
        for profiler_mode in (1, 2):
            for i in range(1, args.runs + 1):
                total_runs += 1
                print(f"\n[Run {total_runs}] {experiment} | Mode p={profiler_mode} | Iteration {i}/{args.runs}")
                cmd = [args.python_exe, str(sim_script_path), "--e", experiment, "--p", str(profiler_mode)]
                rc = run_cmd(cmd, cwd=project_root)
                if rc != 0:
                    failures += 1

    print(f"\n{'='*60}")
    print("Batch complete")
    print(f"{'='*60}")
    print(f"Experiments processed: {len(experiments)}")
    print(f"Total runs: {total_runs}")
    print(f"Successful: {total_runs - failures}")
    print(f"Failures: {failures}")
    if failures:
        print("\nSome runs failed; check the console output above for details.")


if __name__ == "__main__":
    main()
