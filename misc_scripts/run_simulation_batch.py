"""
Run TOMACS simulation multiple times for batch testing.

Example:
    python misc_scripts/run_simulation_batch.py --experiment isolation_tests/Baseline --runs 5
    python misc_scripts/run_simulation_batch.py --experiments isolation_tests/Baseline isolation_tests/Baseline-Iso_25 --runs 3
    python misc_scripts/run_simulation_batch.py --experiment isolation_tests/Baseline --runs 5 --args --p 1
    python misc_scripts/run_simulation_batch.py --experiments isolation_tests/Baseline --runs 3 --args --p 2
"""

import argparse
import subprocess
import time
from pathlib import Path
from datetime import datetime


def run_simulation(experiment: str, script_path: Path, python_exe: str, extra_args: list = None) -> tuple:
    """
    Run a single TOMACS simulation and return execution time and exit code.
    
    Args:
        experiment: Experiment path
        script_path: Path to simulation script
        python_exe: Python executable
        extra_args: Additional arguments to pass to the simulation
    
    Returns:
        tuple: (elapsed_time, exit_code)
    """
    cmd = [python_exe, str(script_path), "--e", experiment]
    
    # Add extra arguments if provided
    if extra_args:
        cmd.extend(extra_args)
    
    print(f"  Running: {experiment}")
    if extra_args:
        print(f"  Args: {' '.join(extra_args)}")
    start_time = time.time()
    
    result = subprocess.run(cmd, cwd=script_path.parent)
    
    elapsed_time = time.time() - start_time
    
    if result.returncode != 0:
        print(f"  ⚠ Failed with exit code {result.returncode}")
    else:
        print(f"  ✓ Completed in {elapsed_time:.2f} seconds")
    
    return elapsed_time, result.returncode


def main():
    parser = argparse.ArgumentParser(
        description='Run TOMACS simulation multiple times for batch experiments.'
    )
    
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        '--experiment', '-e',
        help='Single experiment path (e.g., isolation_tests/Baseline)'
    )
    group.add_argument(
        '--experiments', '-es',
        nargs='+',
        help='Multiple experiment paths'
    )
    
    parser.add_argument(
        '--runs', '-n',
        type=int,
        default=1,
        help='Number of times to run each experiment (default: 1)'
    )
    parser.add_argument(
        '--python-exe',
        default='python',
        help='Python executable to use (default: python)'
    )
    parser.add_argument(
        '--sim-script',
        default='TOMACS_simulation.py',
        help='Simulation script name (default: TOMACS_simulation.py)'
    )
    parser.add_argument(
        '--args',
        nargs='+',
        help='Additional arguments to pass to the simulation (e.g., --args --p 1)'
    )
    
    args = parser.parse_args()
    
    # Get experiment list
    experiments = [args.experiment] if args.experiment else args.experiments
    
    # Get paths
    project_root = Path(__file__).resolve().parent.parent
    sim_script_path = project_root / args.sim_script
    
    if not sim_script_path.exists():
        raise FileNotFoundError(f"Simulation script not found: {sim_script_path}")
    
    # Statistics tracking
    total_runs = 0
    total_time = 0
    failures = 0
    run_times = []
    
    start_timestamp = datetime.now()
    print(f"Starting TOMACS experiment suite at {start_timestamp.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Experiments: {len(experiments)}")
    print(f"Runs per experiment: {args.runs}")
    print(f"Total simulations: {len(experiments) * args.runs}\n")
    
    # Run simulations
    for run in range(1, args.runs + 1):
        print(f"{'='*60}")
        print(f"RUN {run}/{args.runs}")
        print(f"{'='*60}")
        
        for experiment in experiments:
            total_runs += 1
            elapsed, exit_code = run_simulation(
                experiment, 
                sim_script_path, 
                args.python_exe,
                args.args
            )
            
            total_time += elapsed
            run_times.append(elapsed)
            
            if exit_code != 0:
                failures += 1
            
            print()
        
        print(f"Run {run}/{args.runs} completed\n")
    
    # Print summary
    end_timestamp = datetime.now()
    duration = (end_timestamp - start_timestamp).total_seconds()
    
    print(f"{'='*60}")
    print("BATCH EXECUTION SUMMARY")
    print(f"{'='*60}")
    print(f"Started:  {start_timestamp.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Finished: {end_timestamp.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Duration: {duration:.2f} seconds ({duration/60:.2f} minutes)")
    print(f"\nTotal simulations: {total_runs}")
    print(f"Successful: {total_runs - failures}")
    print(f"Failed: {failures}")
    
    if run_times:
        print(f"\nSimulation times:")
        print(f"  Average: {sum(run_times)/len(run_times):.2f} seconds")
        print(f"  Minimum: {min(run_times):.2f} seconds")
        print(f"  Maximum: {max(run_times):.2f} seconds")
        print(f"  Total:   {total_time:.2f} seconds")
    
    if failures > 0:
        print(f"\n⚠ {failures} simulation(s) failed")
        return 1
    else:
        print("\n✓ All simulations completed successfully")
        return 0


if __name__ == '__main__':
    exit(main())


# python misc_scripts/run_simulation_batch.py --experiments isolation_tests/Baseline isolation_tests/Baseline-Iso_25 isolation_tests/Baseline-Iso_50 isolation_tests/Baseline-Iso_75 isolation_tests/Baseline-Iso_100 --runs 5
# python misc_scripts/run_simulation_batch.py --experiment isolation_tests/Baseline --runs 2 --args --p 1 --someOtherFlag value
# python misc_scripts/run_simulation_batch.py --experiments isolation_tests/Baseline isolation_tests/Baseline-Iso_25 --runs 5 --args --p 1