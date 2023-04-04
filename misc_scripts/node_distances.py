import sys

sys.path.append('../')

import argparse
from typing import Optional

import matplotlib.pyplot as plt
import numpy as np
import seaborn as sns

from data_parse_util import *
from util import *


def create_node_distante_distribution_figure(experiment_configuration_file:str,
                                             distance_type:int = 1,
                                             bucket_size:float = 0.005,
                                             y_limit:Optional[int] = None) -> None:
    '''This function takes a experiment configuration file and an optional y_limit parameter and generates two histograms: first histogram shows the frequency of distances between nodes, while the second histogram shows the cumulative frequency of distances between nodes. 

    Parameters:
    ----------
    experiment_configuration_file (str): configuration file to load an EnvGraph
    distance_type (int): converted to util.DistanceType, used to calculate distances
    bucket_size (float): bucket size for the histograms
    y_limit (int): optional parameter representing the y_limit the first histogram.

    Returns:
    ----------
    None.
    '''
    # Setup
    __header:str = "Node Distances:"
    _dist_type:DistanceType = DistanceType(distance_type)
    print(__header, f'Experiment Config: {experiment_configuration_file}, Distance Type: {_dist_type},',
          f'Bucket Size: {bucket_size}, Y-Limit: {y_limit}')
    
    # Creates the directory if necessary
    dir_path = Path(__file__).parent / "node_distances" / experiment_configuration_file
    dir_path.mkdir(parents=True, exist_ok=True)

    # Load an EnvironmentGraph using the experiment configuration
    env_graph = Generate_EnvironmentGraph(experiment_configuration_file)
        
    # Calculates distances between nodes
    distances = []
    for node in env_graph.node_list:
        distances.extend([x[1] for x in env_graph.get_node_distances(node, _dist_type).distance_to_others.items()])
    max_distante = max(distances) * 1.05

    # Creates a histogram of distance between notes
    bins = np.arange(0, max_distante, bucket_size)
    s = sns.histplot(distances, bins=bins) # type: ignore
    fig_path = dir_path / f"node_distances_{experiment_configuration_file}_{_dist_type.name}_{bucket_size}.png"
    plt.ylim(0, y_limit)
    print(__header, f'Saving node distance figure to:\n\t', fig_path)
    plt.savefig(fig_path, dpi=400)
    plt.clf()

    # Creates a second histogram with the cumulative values
    s = sns.histplot(distances, bins=bins, cumulative=True) # type: ignore
    fig_path = dir_path / f"node_distances_{experiment_configuration_file}_{_dist_type.name}_{bucket_size}_cumulative.png"
    print(__header, f'Saving comulative node distance figure to:\n\t', fig_path)
    plt.savefig(fig_path, dpi=400)
    plt.clf()

if __name__ == '__main__':
    arg_parser = argparse.ArgumentParser(description="Create Node Distante Distribution Figure.")
    arg_parser.add_argument('--e', metavar="E", type=str, default = None, help='Experiment Configuration File.')
    arg_parser.add_argument('--d', metavar="D", type=int, default = 1, help='Distance Type used for calculations.')
    arg_parser.add_argument('--b', metavar="B", type=float, default = 0.005, help='Bucket size used for calculations.')
    arg_parser.add_argument('--y', metavar="y", type=float, default = None, help='Y-Limit.')
    args = vars(arg_parser.parse_args())
    create_node_distante_distribution_figure(args['e'], args['d'], args['b'], args['y'])