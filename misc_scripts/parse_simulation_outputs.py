"""
Parse simulation output logs and generate summary statistics.

This script processes all output files in a specified experiment folder,
extracts timing metrics, and generates a CSV file with statistics.
"""

import os
import re
import csv
import argparse
from pathlib import Path
from typing import Dict, List, Tuple
import statistics


def find_output_files(output_logs_path: str) -> List[str]:
    """Find all output files matching the pattern output_YYYYMMDD-HHMMSS.txt"""
    output_files = []
    pattern = re.compile(r'output_\d{8}-\d{6}\.txt$')
    
    for root, dirs, files in os.walk(output_logs_path):
        for file in files:
            if pattern.match(file):
                output_files.append(os.path.join(root, file))
    
    return sorted(output_files)


def parse_output_file(filepath: str) -> Dict[str, float]:
    """
    Parse a single output file and extract timing metrics.
    
    Returns a dictionary with keys:
    - 'file': filename
    - 'total_simulation_time': float
    - 'average_cycle_time': float
    - 'import_to_simulation_time': float
    - 'total_time': float
    """
    metrics = {'file': Path(filepath).name}
    
    try:
        with open(filepath, 'r') as f:
            content = f.read()
        
        # Extract metrics using regex
        patterns = {
            'total_simulation_time': r'Total Simulation Time:\s*([\d.]+)',
            'average_cycle_time': r'Average Cycle Time:\s*([\d.]+)',
            'import_to_simulation_time': r'Import To Simulation Start Time:\s*([\d.]+)',
            'total_time': r'Total Time:\s*([\d.]+)'
        }
        
        for key, pattern in patterns.items():
            match = re.search(pattern, content)
            if match:
                metrics[key] = float(match.group(1))
            else:
                metrics[key] = None
    
    except Exception as e:
        print(f"Error parsing {filepath}: {e}")
        return None
    
    return metrics


def calculate_statistics(data: List[Dict[str, float]]) -> Tuple[Dict, Dict, Dict]:
    """Calculate average, min, and max for each metric."""
    metric_keys = ['total_simulation_time', 'average_cycle_time', 
                   'import_to_simulation_time', 'total_time']
    
    stats = {
        'average': {},
        'min': {},
        'max': {}
    }
    
    for key in metric_keys:
        values = [d[key] for d in data if d[key] is not None]
        
        if values:
            stats['average'][key] = statistics.mean(values)
            stats['min'][key] = min(values)
            stats['max'][key] = max(values)
        else:
            stats['average'][key] = None
            stats['min'][key] = None
            stats['max'][key] = None
    
    return stats


def write_csv_report(data: List[Dict[str, float]], output_file: str, 
                     stats: Dict) -> None:
    """Write the data and statistics to a CSV file."""
    
    fieldnames = ['file', 'total_simulation_time', 'average_cycle_time', 
                  'import_to_simulation_time', 'total_time']
    
    with open(output_file, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        
        # Write header
        writer.writeheader()
        
        # Write data rows
        for row in data:
            writer.writerow(row)
        
        # Write statistics rows
        stats_data = {
            'file': 'AVERAGE',
            'total_simulation_time': stats['average']['total_simulation_time'],
            'average_cycle_time': stats['average']['average_cycle_time'],
            'import_to_simulation_time': stats['average']['import_to_simulation_time'],
            'total_time': stats['average']['total_time']
        }
        writer.writerow(stats_data)
        
        stats_data['file'] = 'MIN'
        stats_data['total_simulation_time'] = stats['min']['total_simulation_time']
        stats_data['average_cycle_time'] = stats['min']['average_cycle_time']
        stats_data['import_to_simulation_time'] = stats['min']['import_to_simulation_time']
        stats_data['total_time'] = stats['min']['total_time']
        writer.writerow(stats_data)
        
        stats_data['file'] = 'MAX'
        stats_data['total_simulation_time'] = stats['max']['total_simulation_time']
        stats_data['average_cycle_time'] = stats['max']['average_cycle_time']
        stats_data['import_to_simulation_time'] = stats['max']['import_to_simulation_time']
        stats_data['total_time'] = stats['max']['total_time']
        writer.writerow(stats_data)


def main():
    """Main execution function."""
    # Parse command-line arguments
    parser = argparse.ArgumentParser(
        description='Parse simulation output logs and generate summary statistics.'
    )
    parser.add_argument(
        'experiment_path',
        help='Path to the experiment folder containing output_logs'
    )
    args = parser.parse_args()
    
    # Get the experiment path and output_logs subdirectory
    experiment_path = Path(args.experiment_path)
    output_logs_path = Path('output_logs') / experiment_path
    
    if not output_logs_path.exists():
        print(f"Error: output_logs folder not found at {output_logs_path}")
        return
    
    print(f"Searching for output files in: {output_logs_path}")
    
    # Find all output files
    output_files = find_output_files(str(output_logs_path))
    print(f"Found {len(output_files)} output files")
    
    if not output_files:
        print("No output files found matching the pattern output_YYYYMMDD-HHMMSS.txt")
        return
    
    # Parse all files
    data = []
    for filepath in output_files:
        metrics = parse_output_file(filepath)
        if metrics:
            data.append(metrics)
            print(f"Parsed: {metrics['file']}")
    
    if not data:
        print("No data could be parsed from the output files")
        return
    
    # Calculate statistics
    stats = calculate_statistics(data)
    
    # Get the Performance folder in the project root
    script_dir = Path(__file__).parent.parent
    performance_dir = script_dir / 'performance'
    performance_dir.mkdir(parents=True, exist_ok=True)
    
    # Use experiment name for the output filename (replace path separators with underscores)
    experiment_name = str(experiment_path).replace('/', '_').replace('\\', '_')
    output_file = performance_dir / f'{experiment_name}_simulation_times.csv'
    
    write_csv_report(data, str(output_file), stats)
    
    print(f"\nReport generated: {output_file}")
    print(f"Total simulations processed: {len(data)}")
    print(f"\nStatistics:")
    print(f"Average Total Simulation Time: {stats['average']['total_simulation_time']:.6f}s")
    print(f"Average Cycle Time: {stats['average']['average_cycle_time']:.6f}s")
    print(f"Average Import Time: {stats['average']['import_to_simulation_time']:.6f}s")
    print(f"Average Total Time: {stats['average']['total_time']:.6f}s")


if __name__ == '__main__':
    main()
