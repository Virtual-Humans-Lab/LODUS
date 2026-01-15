"""
Movement Displacement Comparison Script

This script generates histogram comparison plots for movement displacement data
from multiple experiments. It reads CSV files with distance and frequency data
and creates overlaid line plots for visual comparison.

Usage Examples:
    
    Basic comparison with default bin size:
        python movement_displacement_comparison.py --e exp1 exp2 exp3
    
    Comparison with custom bin size:
        python movement_displacement_comparison.py --e exp1 exp2 --b 1000
    
    Comparison with custom labels:
        python movement_displacement_comparison.py --e exp1 exp2 --l "Label A" "Label B"
    
    Comparison with subdirectory path:
        python movement_displacement_comparison.py --p levy_tests --e exp1 exp2
    
    Full example with all parameters:
        python movement_displacement_comparison.py \
            --p levy_parameter_tests_94 \
            --b 500 \
            --e WorkSchool94-BW_500-S_250 WorkSchool94-BW_500-S_500 WorkSchool94-BW_500-S_1000 \
            --x 25000 \
            --y 5000 \
            --l "Scale = 0.5" "Scale = 1" "Scale = 2"
    
    Comparison with axis limits:
        python movement_displacement_comparison.py --e exp1 exp2 --x 10000 --y 3000

Arguments:
    --e : List of experiment names (required)
    --l : List of custom labels for the legend (optional, must match --e length)
    --p : Subdirectory path under output_logs (optional)
    --b : Histogram bin size in meters (default: 500)
    --x : Maximum x-axis value (optional)
    --y : Maximum y-axis value (optional)

Output:
    PNG file saved to: misc_scripts/movement_displacement_comparison/{path}/

Command Line Example:
    python movement_displacement_comparison.py --p levy_parameter_tests_94 
        --b 500 --e WorkSchool94-BW_500-S_250 WorkSchool94-BW_500-S_500 WorkSchool94-BW_500-S_1000 WorkSchool94-BW_500-S_2500 WorkSchool94-BW_500-S_5000 
        --x 25000 --l "Scale = 0.5" "Scale = 1" "Scale = 2" "Scale = 5" "Scale = 10"
"""
import sys
import argparse
from pathlib import Path

import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import seaborn as sns
import plotly.express as px

_repo_root = Path(__file__).resolve().parent.parent
if str(_repo_root) not in sys.path:
    sys.path.insert(0, str(_repo_root))

# Constants
MAX_DISPLACEMENT_MULTIPLIER = 1.05
DEFAULT_DPI = 400
DEFAULT_FIGURE_SIZE = (8, 3)
DEFAULT_LINE_WIDTH = 1.5

def displacement_histogram_comparison(experiment_names: list[str], 
                                      label_list: list[str],
                                      additional_exp_path: str = '', 
                                      bin_size: float = 500, 
                                      x_limit: int | None = None, 
                                      y_limit: int | None = None) -> None:
    """
    Generate comparison histogram plots for multiple experiments.
    
    Args:
        experiment_names: List of experiment directory names
        label_list: Custom labels for plot legend (must match experiment_names length)
        additional_exp_path: Subdirectory path under output_logs
        bin_size: Histogram bin width in meters (default: 500)
        x_limit: Maximum x-axis value (optional)
        y_limit: Maximum y-axis value (optional)
    """
    log_prefix: str = "Displacement Histogram Comparison:"

    # Setup
    # Creates the output directory if necessary
    base_dir = Path(__file__).resolve().parent
    dir_path = base_dir / "movement_displacement_comparison" / additional_exp_path
    dir_path.mkdir(parents=True, exist_ok=True)
    # store (label, x_values, weights)
    data_list:list[tuple[str,np.ndarray,np.ndarray]] = []
    for exp in experiment_names:
        _exp_path = Path(__file__).parent.parent / "output_logs" / additional_exp_path / exp / "data_frames"
        csv_path = _exp_path / "movement_counter.csv"
        if not csv_path.exists():
            print(log_prefix, f"Skipping '{exp}': file not found -> {csv_path}")
            continue
        _df = pd.read_csv(csv_path, sep=';')
        if _df.empty:
            print(log_prefix, f"Skipping '{exp}': empty dataset -> {csv_path}")
            continue
        # assume first column = distance, second column = count
        x_vals = _df.iloc[:, 0].to_numpy(dtype=float)
        weights = _df.iloc[:, 1].to_numpy(dtype=float)
        data_list.append((exp, x_vals, weights))

    # Validate and apply custom labels
    if label_list:
        if len(label_list) != len(experiment_names):
            raise ValueError("label_list length must match experiment_names length")
        # map original experiment name -> label
        name_to_label = {orig: lab for orig, lab in zip(experiment_names, label_list)}
        data_list = [ (name_to_label.get(name, name), x, w) for (name, x, w) in data_list ]
        experiment_names = label_list
    
    # Validate we have data to plot
    if not data_list:
        print(log_prefix, "No valid data found. Skipping plot generation.")
        return
    
    # Find max displacement to create bins
    max_displacement = 0.0
    for (_, x_vals, _weights) in data_list:
        if x_vals.size > 0:
            max_displacement = max(max_displacement, float(np.max(x_vals)) * MAX_DISPLACEMENT_MULTIPLIER)
    # include upper edge to prevent off-by-one issues
    bins = np.arange(0.0, max_displacement + bin_size, bin_size)

    # Plot multiple histograms
    sns.set_theme()
    plt.figure(figsize=DEFAULT_FIGURE_SIZE)
    for (exp, x_vals, weights) in data_list:
        counts, edges = np.histogram(x_vals, bins=bins, weights=weights)
        # Use bin centers and connect as a line (less bar-like than steps)
        centers = 0.5 * (edges[:-1] + edges[1:])
        plt.plot(centers, counts, label=exp, linewidth=DEFAULT_LINE_WIDTH)
    plt.legend(fancybox=True, shadow=True, fontsize='x-small')
    plt.xlabel("Distance (m)")
    plt.ylabel("Total Displacements")
    
    # Create sanitized filename from experiment names
    sanitized_names = '_'.join(experiment_names).replace(' ', '_')
    fig_path = dir_path / f"disp_comp_{sanitized_names}.png"
    
    if x_limit is not None:
        plt.xlim(0, x_limit)
    if y_limit is not None:
        plt.ylim(0, y_limit)
    
    plt.tight_layout()
    
    try:
        plt.savefig(fig_path, dpi=DEFAULT_DPI)
        print(log_prefix, "Saved displacement histogram comparison at:\n\t", fig_path)
    except Exception as e:
        print(log_prefix, f"Error saving figure: {e}")
    finally:
        plt.close()


def _bin_movement_data(df: pd.DataFrame, bin_size: float) -> dict:
    """
    Helper function to bin movement data into histogram buckets.
    
    Args:
        df: DataFrame with distance and frequency columns
        bin_size: Size of each bin
        
    Returns:
        Dictionary mapping bin limits to aggregated frequencies
    """
    max_distance = float(df.iloc[:, 0].max())
    bins_limits = np.arange(0.0, max_distance + bin_size, bin_size).tolist()
    data = {b: 0 for b in bins_limits}
    
    keys_list = list(data.keys())
    last_idx = len(keys_list) - 1
    
    distances = df.iloc[:, 0].to_numpy()
    frequencies = df.iloc[:, 1].to_numpy()
    key_indices = (distances // bin_size).astype(int)
    key_indices = np.clip(key_indices, 0, last_idx)
    bin_sums = np.bincount(key_indices, weights=frequencies, minlength=len(keys_list))
    
    for idx, key in enumerate(keys_list):
        data[key] = int(bin_sums[idx])
    
    return data


def combined_movement_displacement_barchart(experiment_name: str, 
                                            bin_size: float = 0.005,
                                            x_limit: int | None = None, 
                                            y_limit: int | None = None) -> None:
    """
    Generate bar chart visualization for movement displacement data.
    
    Args:
        experiment_name: Name of the experiment directory
        bin_size: Size of histogram bins (default: 0.005)
        x_limit: Maximum x-axis value (optional)
        y_limit: Maximum y-axis value (optional)
    """
    header: str = "Experiment Movement Displacement:"
    dir_path = Path(__file__).parent.parent / "output_logs" / experiment_name / "data_frames"
    output_path = Path(__file__).parent.parent / "output_logs" / experiment_name / "results"
    dir_path.mkdir(parents=True, exist_ok=True)
    output_path.mkdir(parents=True, exist_ok=True)

    xaxis = dict(tickmode = 'linear',
                 tick0 = 0.0,
                 dtick = bin_size * 2)

    # Load dataframe from CSVs
    df_movement = pd.read_csv(dir_path / "movement_counter.csv", sep=';')
    
    # Bin the movement data
    data = _bin_movement_data(df_movement, bin_size)
    df = pd.DataFrame.from_dict(data, orient='index')

    # Creates and save html
    fig = px.bar(df, y = 0, title=f'Movement displacement data - {experiment_name}')
    fig.update_layout(xaxis = xaxis, hovermode="x")
    if x_limit is not None:
        fig.update_xaxes(range=[0, x_limit])
    if y_limit is not None:
        fig.update_yaxes(range=[0, y_limit])
    
    fig_path = output_path / f"movement_distance_bar_chart_size{len(df.index)}_bin{bin_size}.html"
    fig.write_html(fig_path)
    print(header, "Saving movement displacement chart at:\n\t", fig_path)
    
    # Repeats process for the group movement data
    df_group_movement = pd.read_csv(dir_path / "group_movement_counter.csv", sep=';')
    data = _bin_movement_data(df_group_movement, bin_size)
    df = pd.DataFrame.from_dict(data, orient='index')
    
    fig = px.bar(df, title=f'Group movement displacement data - {experiment_name}')
    fig.update_layout(xaxis=xaxis, hovermode="x")
    if y_limit is not None:
        fig.update_yaxes(range=[0, y_limit])
    
    fig_path = output_path / f"group_movement_distance_bar_chart_size{len(df.index)}_bin{bin_size}.html"
    fig.write_html(fig_path)
    print(header, "Saving group movement displacement bar chart at:\n\t", fig_path)


if __name__ == '__main__':
    arg_parser = argparse.ArgumentParser(description="Create Node Distance Distribution Figure.")
    arg_parser.add_argument('--e', metavar="E", nargs='+', type=str, default=[], 
                            help='Experiment Name List (same as experiment configuration file)')
    arg_parser.add_argument('--l', metavar="L", nargs='+', type=str, default=[], 
                            help='Label List (to replace experiment name)')
    arg_parser.add_argument('--p', metavar="P", type=str, default='', 
                            help='Additional experiment path')
    arg_parser.add_argument('--b', metavar="B", type=float, default=500, 
                            help='Bin Size')
    arg_parser.add_argument('--x', metavar="X", type=float, default=None, 
                            help='X-Limit')
    arg_parser.add_argument('--y', metavar="Y", type=float, default=None, 
                            help='Y-Limit')
    args = vars(arg_parser.parse_args())
    
    displacement_histogram_comparison(
        experiment_names=args['e'], 
        label_list=args['l'],
        additional_exp_path=args['p'],
        bin_size=args['b'], 
        x_limit=args['x'], 
        y_limit=args['y']
    )