"""
Parse memory profiling results from performance/memory_consumption folder.

This script processes memory_profiler and tracemalloc output files,
extracts memory consumption metrics, and generates a CSV summary.

Usage Examples:
    
    Basic usage with experiment folder:
        python misc_scripts/parse_memory_profiles.py isolation_tests/Baseline
    
    Parse memory profiles from nested experiment:
        python misc_scripts/parse_memory_profiles.py levy_parameter_tests_94/WorkSchool94-BW_500-S_250
    
    Parse memory profiles from isolation tests:
        python misc_scripts/parse_memory_profiles.py isolation_tests/Baseline-Iso_50
    
    Parse memory profiles from epidemic experiments:
        python misc_scripts/parse_memory_profiles.py epidemic_tests/High_Transmission

Arguments:
    experiment_path : Path to the experiment folder (relative to performance/memory_consumption directory)

Output:
    CSV file saved to: Performance/{experiment_name}_memory_summary.csv
    
    The CSV contains:
    - Individual metrics for each profiler run (memory_profiler and tracemalloc)
    - MIN, MAX, AVG, and STDDEV statistics rows for each profiler type
    - Columns: file, profiler_type, min_memory_mb, max_memory_mb, 
               avg_memory_mb, peak_memory_mb

Command Line Examples:
    python misc_scripts/parse_memory_profiles.py isolation_tests/Baseline
    python misc_scripts/parse_memory_profiles.py isolation_tests/Baseline-Iso_25
    python misc_scripts/parse_memory_profiles.py levy_tests/WorkSchool94-BW_500-S_1000
"""

import os
import re
import csv
import argparse
from pathlib import Path
from typing import Dict, List, Optional
import statistics


def parse_memory_profiler_file(filepath: str) -> Optional[Dict]:
    """
    Parse memory_profiler output file.
    
    Format:
    [memory_values_list]
    max_value
    
    Returns dict with min, max, average memory in MB.
    """
    try:
        with open(filepath, 'r') as f:
            content = f.read().strip()
        
        lines = content.split('\n')
        if len(lines) < 2:
            print(f"Warning: {filepath} has unexpected format")
            return None
        
        # Parse the list of memory values
        mem_list_str = lines[0]
        mem_values = eval(mem_list_str)  # Safe here since we control the file content
        
        if not mem_values:
            return None
        
        return {
            'file': Path(filepath).name,
            'profiler_type': 'memory_profiler',
            'min_memory_mb': min(mem_values),
            'max_memory_mb': max(mem_values),
            'avg_memory_mb': statistics.mean(mem_values),
            'peak_memory_mb': max(mem_values)
        }
    
    except Exception as e:
        print(f"Error parsing memory_profiler file {filepath}: {e}")
        return None


def parse_tracemalloc_file(filepath: str) -> Optional[Dict]:
    """
    Parse tracemalloc output file.
    
    Format:
    Current memory usage is <current>; Peak was <peak>
    Top 10 lines
    ...
    
    Returns dict with current and peak memory in MB.
    """
    try:
        with open(filepath, 'r') as f:
            content = f.read()
        
        # Extract current and peak memory from first line
        pattern = r'Current memory usage is (\d+); Peak was (\d+)'
        match = re.search(pattern, content)
        
        if not match:
            print(f"Warning: {filepath} has unexpected format")
            return None
        
        current = int(match.group(1))
        peak = int(match.group(2))
        
        # Convert bytes to MB
        current_mb = current / (1024 * 1024)
        peak_mb = peak / (1024 * 1024)
        
        return {
            'file': Path(filepath).name,
            'profiler_type': 'tracemalloc',
            'min_memory_mb': current_mb,  # Current is typically the final/min after cleanup
            'max_memory_mb': peak_mb,
            'avg_memory_mb': (current_mb + peak_mb) / 2,  # Rough estimate
            'peak_memory_mb': peak_mb
        }
    
    except Exception as e:
        print(f"Error parsing tracemalloc file {filepath}: {e}")
        return None


def find_profiler_files(base_path: str) -> Dict[str, List[str]]:
    """Find all memory profiler files in the directory."""
    files = {
        'memory_profiler': [],
        'tracemalloc': []
    }
    
    for root, dirs, filenames in os.walk(base_path):
        for filename in filenames:
            filepath = os.path.join(root, filename)
            if 'memory_profiler_' in filename and filename.endswith('.txt'):
                files['memory_profiler'].append(filepath)
            elif 'tracemalloc_' in filename and filename.endswith('.txt'):
                files['tracemalloc'].append(filepath)
    
    return files


def calculate_statistics(data: List[Dict]) -> Dict:
    """Calculate statistics for each profiler type separately."""
    if not data:
        return {}
    
    metrics = ['min_memory_mb', 'max_memory_mb', 'avg_memory_mb', 'peak_memory_mb']
    stats = {
        'memory_profiler': {},
        'tracemalloc': {}
    }
    
    # Calculate stats for each profiler type
    for profiler_type in ['memory_profiler', 'tracemalloc']:
        profiler_data = [d for d in data if d['profiler_type'] == profiler_type]
        
        if not profiler_data:
            continue
        
        for metric in metrics:
            values = [d[metric] for d in profiler_data if d[metric] is not None]
            if values:
                stats[profiler_type][f'{metric}_min'] = min(values)
                stats[profiler_type][f'{metric}_max'] = max(values)
                stats[profiler_type][f'{metric}_avg'] = statistics.mean(values)
                stats[profiler_type][f'{metric}_std'] = statistics.stdev(values) if len(values) > 1 else 0.0
            else:
                stats[profiler_type][f'{metric}_min'] = None
                stats[profiler_type][f'{metric}_max'] = None
                stats[profiler_type][f'{metric}_avg'] = None
                stats[profiler_type][f'{metric}_std'] = None
    
    return stats


def write_csv_report(data: List[Dict], output_file: str, stats: Dict) -> None:
    """Write the parsed data and statistics to CSV."""
    fieldnames = ['file', 'profiler_type', 'min_memory_mb', 'max_memory_mb', 
                  'avg_memory_mb', 'peak_memory_mb']
    
    with open(output_file, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        
        # Write data rows
        for row in data:
            writer.writerow(row)
        
        # Write summary statistics rows for each profiler type
        for profiler_type in ['memory_profiler', 'tracemalloc']:
            if profiler_type not in stats or not stats[profiler_type]:
                continue
            
            profiler_stats = stats[profiler_type]
            
            # Min across all runs for this profiler
            writer.writerow({
                'file': f'{profiler_type.upper()}_MIN',
                'profiler_type': profiler_type,
                'min_memory_mb': profiler_stats.get('min_memory_mb_min'),
                'max_memory_mb': profiler_stats.get('max_memory_mb_min'),
                'avg_memory_mb': profiler_stats.get('avg_memory_mb_min'),
                'peak_memory_mb': profiler_stats.get('peak_memory_mb_min')
            })
            
            # Max across all runs for this profiler
            writer.writerow({
                'file': f'{profiler_type.upper()}_MAX',
                'profiler_type': profiler_type,
                'min_memory_mb': profiler_stats.get('min_memory_mb_max'),
                'max_memory_mb': profiler_stats.get('max_memory_mb_max'),
                'avg_memory_mb': profiler_stats.get('avg_memory_mb_max'),
                'peak_memory_mb': profiler_stats.get('peak_memory_mb_max')
            })
            
            # Average across all runs for this profiler
            writer.writerow({
                'file': f'{profiler_type.upper()}_AVG',
                'profiler_type': profiler_type,
                'min_memory_mb': profiler_stats.get('min_memory_mb_avg'),
                'max_memory_mb': profiler_stats.get('max_memory_mb_avg'),
                'avg_memory_mb': profiler_stats.get('avg_memory_mb_avg'),
                'peak_memory_mb': profiler_stats.get('peak_memory_mb_avg')
            })
            
            # Standard deviation across all runs for this profiler
            writer.writerow({
                'file': f'{profiler_type.upper()}_STDDEV',
                'profiler_type': profiler_type,
                'min_memory_mb': profiler_stats.get('min_memory_mb_std'),
                'max_memory_mb': profiler_stats.get('max_memory_mb_std'),
                'avg_memory_mb': profiler_stats.get('avg_memory_mb_std'),
                'peak_memory_mb': profiler_stats.get('peak_memory_mb_std')
            })


def main():
    parser = argparse.ArgumentParser(
        description='Parse memory profiling results and generate CSV summary.'
    )
    parser.add_argument(
        'experiment_path',
        help='Path to the experiment folder in performance/memory_consumption'
    )
    args = parser.parse_args()
    
    # Get paths
    script_dir = Path(__file__).parent.parent
    memory_base = script_dir / 'performance' / 'memory_consumption'
    experiment_path = memory_base / args.experiment_path
    
    if not experiment_path.exists():
        print(f"Error: Experiment path not found: {experiment_path}")
        return
    
    print(f"Searching for profiler files in: {experiment_path}")
    
    # Find all profiler files
    files = find_profiler_files(str(experiment_path))
    
    total_files = len(files['memory_profiler']) + len(files['tracemalloc'])
    print(f"Found {len(files['memory_profiler'])} memory_profiler files")
    print(f"Found {len(files['tracemalloc'])} tracemalloc files")
    print(f"Total: {total_files} files")
    
    if total_files == 0:
        print("No profiler files found")
        return
    
    # Parse all files
    all_data = []
    
    for filepath in files['memory_profiler']:
        result = parse_memory_profiler_file(filepath)
        if result:
            all_data.append(result)
            print(f"Parsed: {result['file']} - Peak: {result['peak_memory_mb']:.2f} MB")
    
    for filepath in files['tracemalloc']:
        result = parse_tracemalloc_file(filepath)
        if result:
            all_data.append(result)
            print(f"Parsed: {result['file']} - Peak: {result['peak_memory_mb']:.2f} MB")
    
    if not all_data:
        print("No data could be parsed")
        return
    
    # Calculate statistics
    stats = calculate_statistics(all_data)
    
    # Write CSV report to Performance folder
    performance_dir = script_dir / 'Performance'
    performance_dir.mkdir(exist_ok=True)
    
    # Use full experiment path with underscores instead of slashes
    experiment_name = args.experiment_path.replace('/', '_').replace('\\', '_')
    output_file = performance_dir / f'{experiment_name}_memory_summary.csv'
    
    write_csv_report(all_data, str(output_file), stats)
    
    print(f"\nReport generated: {output_file}")
    print(f"Total files processed: {len(all_data)}")
    
    # Print statistics for each profiler type
    for profiler_type in ['memory_profiler', 'tracemalloc']:
        if profiler_type in stats and stats[profiler_type]:
            print(f"\n{profiler_type.upper()} Statistics:")
            prof_stats = stats[profiler_type]
            if prof_stats.get('peak_memory_mb_avg') is not None:
                print(f"  Peak Memory (avg): {prof_stats['peak_memory_mb_avg']:.2f} MB")
                print(f"  Peak Memory (min): {prof_stats['peak_memory_mb_min']:.2f} MB")
                print(f"  Peak Memory (max): {prof_stats['peak_memory_mb_max']:.2f} MB")
                print(f"  Peak Memory (std): {prof_stats['peak_memory_mb_std']:.2f} MB")


if __name__ == '__main__':
    main()
