import sys
from pathlib import Path

# Add parent directory to path for imports
MODULE_DIR = Path(__file__).parent.absolute()
sys.path.insert(0, str(MODULE_DIR.parent))

import argparse
from typing import Optional, List

import matplotlib.pyplot as plt
import numpy as np
import seaborn as sns

from data_parse_util import Generate_EnvironmentGraph
from util import DistanceType

# Constants
MAX_DISTANCE_PADDING = 1.05
FIGURE_WIDTH = 8
FIGURE_HEIGHT = 3
DPI = 400


def save_histogram_figure(distances: List[float], bins: np.ndarray, fig_path: Path,
                          cumulative: bool = False, y_limit: Optional[float] = None) -> None:
    '''Helper function to create and save histogram figures.
    
    Parameters:
    ----------
    distances (List[float]): List of distance values
    bins (np.ndarray): Bin edges for histogram
    fig_path (Path): Path where to save the figure
    cumulative (bool): Whether to create a cumulative histogram
    y_limit (Optional[float]): Y-axis limit for the histogram
    
    Returns:
    ----------
    None.
    '''
    sns.set_theme()
    plt.figure(figsize=(FIGURE_WIDTH, FIGURE_HEIGHT))
    sns.histplot(distances, bins=bins, cumulative=cumulative)  # type: ignore
    plt.xlabel("Distance (m)")
    plt.ylabel("Cumulative Count" if cumulative else "Count")
    if not cumulative and y_limit is not None:
        plt.ylim(0, y_limit)
    plt.tight_layout()
    plt.savefig(fig_path, dpi=DPI)
    plt.clf()


def create_node_distance_distribution_figure(experiment_configuration_file: str,
                                              distance_type: int = 1,
                                              bucket_size: float = 0.005,
                                              y_limit: Optional[float] = None) -> None:
    '''Generate frequency and cumulative frequency histograms of distances between nodes.

    Parameters:
    ----------
    experiment_configuration_file (str): Path to configuration file to load an EnvGraph
    distance_type (int): Distance type enum value (converted to util.DistanceType)
    bucket_size (float): Bucket size for histogram binning
    y_limit (Optional[float]): Y-axis limit for the frequency histogram

    Returns:
    ----------
    None
    
    Raises:
    ------
    ValueError: If experiment_configuration_file is None or distances list is empty
    Exception: If configuration file cannot be loaded
    '''
    if experiment_configuration_file is None:
        raise ValueError("experiment_configuration_file cannot be None")
    
    # Setup
    header = "Node Distances:"
    dist_type = DistanceType(distance_type)
    print(f"{header} Experiment Config: {experiment_configuration_file}, Distance Type: {dist_type},"
          f" Bucket Size: {bucket_size}, Y-Limit: {y_limit}")
    
    # Creates the directory if necessary
    dir_path = MODULE_DIR / "node_distances" / experiment_configuration_file
    dir_path.mkdir(parents=True, exist_ok=True)

    try:
        # Load an EnvironmentGraph using the experiment configuration
        env_graph = Generate_EnvironmentGraph(experiment_configuration_file)
            
        # Calculates distances between nodes
        distances = []
        for node in env_graph.node_list:
            distances.extend([x[1] for x in env_graph.get_node_distances(node, dist_type).distance_to_others.items()])
        
        if not distances:
            raise ValueError("No distances calculated from environment graph")
        
        max_distance_value = max(distances)
        max_distance = max_distance_value * MAX_DISTANCE_PADDING
        print(f"{header} Max distance: {max_distance_value}")

        # Creates histograms of distances between nodes
        bins = np.arange(0, max_distance, bucket_size)
        
        # Frequency histogram
        fig_path = dir_path / f"node_distances_{experiment_configuration_file}_{dist_type.name}_{bucket_size}.png"
        print(f"{header} Saving node distance figure to:\\n\\t{fig_path}")
        save_histogram_figure(distances, bins, fig_path, cumulative=False, y_limit=y_limit)

        # Cumulative histogram
        fig_path = dir_path / f"node_distances_{experiment_configuration_file}_{dist_type.name}_{bucket_size}_cumulative.png"
        print(f"{header} Saving cumulative node distance figure to:\\n\\t{fig_path}")
        save_histogram_figure(distances, bins, fig_path, cumulative=True)
        
    except Exception as e:
        print(f"{header} Error processing configuration: {e}", file=sys.stderr)
        raise

if __name__ == '__main__':
    arg_parser = argparse.ArgumentParser(description="Create Node Distance Distribution Figure.")
    arg_parser.add_argument('--e', metavar="E", type=str, default=None, help='Experiment Configuration File.')
    arg_parser.add_argument('--d', metavar="D", type=int, default=1, help='Distance Type used for calculations.')
    arg_parser.add_argument('--b', metavar="B", type=float, default=0.005, help='Bucket size used for calculations.')
    arg_parser.add_argument('--y', metavar="y", type=float, default=None, help='Y-Limit for frequency histogram.')
    args = vars(arg_parser.parse_args())
    
    try:
        create_node_distance_distribution_figure(args['e'], args['d'], args['b'], args['y'])
    except Exception as e:
        print(f"Fatal error: {e}", file=sys.stderr)
        sys.exit(1)