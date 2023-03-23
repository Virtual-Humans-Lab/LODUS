import argparse
from typing import Optional
import environment
from util import *
from data_parse_util import *
import population

import matplotlib.pyplot as plt
import numpy as np
import seaborn as sns
from scipy.stats import levy as scipy_levy

def create_node_distante_distribution_figure(experiment_configuration_file:str, y_limit:Optional(int) = None) -> None:
    '''This function takes a LevyWalkPlugin object and an optional y_limit parameter and generates two histograms: first histogram shows the frequency of distances between nodes, while the second histogram shows the cumulative frequency of distances between nodes. 

    Parameters:
    ----------
    environment_file_name: 
    levy_plugin: a LevyWalkPlugin object, linked to an EnvGraph
    y_limit: a integer representing the y_limit the first histogram.

    Returns:
    ----------
    None.
    '''
    
    # Creates the directory if necessary
    dir_path = Path(__file__).parent / "levy_distribution"
    dir_path.mkdir(parents=True, exist_ok=True)

    # Calculates distances between nodes
    distances = []
    for node in levy_plugin.graph.node_list:
        distances.extend([x[0] for x in levy_plugin.get_node_distance(node, levy_plugin.graph)])
    max_distante = max(distances) * 1.05

    # Creates a histogram of distance between notes
    bins = np.arange(0, max_distante, levy_plugin.bucket_size)
    s = sns.histplot(distances, bins=bins) # type: ignore
    levy_plugin.graph.experiment_name
    fig_path = dir_path / f"node_distances_{levy_plugin.graph.experiment_name}_{levy_plugin.distance_type.name}_{levy_plugin.bucket_size}.png"
    plt.ylim(0, y_limit)
    plt.savefig(fig_path, dpi=400)
    plt.clf()

    # Creates a second histogram with the cumulative values
    s = sns.histplot(distances, bins=bins, cumulative=True) # type: ignore
    levy_plugin.graph.experiment_name
    fig_path = dir_path / f"node_distances_{levy_plugin.graph.experiment_name}_{levy_plugin.distance_type.name}_{levy_plugin.bucket_size}_cumulative.png"
    plt.savefig(fig_path, dpi=400)
    plt.clf()

if __name__ == '__main__':
    arg_parser = argparse.ArgumentParser(description="Create Node Distante Distribution Figure.")
    arg_parser.add_argument('--e', metavar="E", type=str, default = None, help='Experiment Configuration File.')
    args = vars(arg_parser.parse_args())
    create_node_distante_distribution_figure(args['e'])
    sys.exit(0) 