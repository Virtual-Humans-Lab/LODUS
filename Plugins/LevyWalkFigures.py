from pathlib import Path
from typing import TYPE_CHECKING

import matplotlib.pyplot as plt
import numpy as np
import seaborn as sns
from scipy.stats import levy as scipy_levy

if TYPE_CHECKING:
    from LevyWalkPlugin import LevyWalkPlugin

class LevyWalkFigures:
    ''' Auxiliary class to generate figures from a levy distribution or a LevyWalkPlugin'''

    @staticmethod
    def generate_levy_distribution_figure(dir_path:Path, location: int, scale: int, size: int,
                            bin_start:float, bin_stop: float, bin_step:float) -> None:
        dist = np.array(scipy_levy.rvs(loc=location, scale= scale, size = size))
        bins = np.arange(bin_start, bin_stop, bin_step)
        s = sns.histplot(dist, bins=bins) # type: ignore
        fig_path = dir_path / f"levy-distribution-l{location}-s{scale}-q{size}.png"
        print(f'Levy Distribution: Location {location}, Scale {scale}, Mean {dist.mean()}, Max {dist.max()}')
        plt.savefig(fig_path, dpi=400)
        plt.clf()
        bins = np.arange(bin_start, bin_stop/2.0, bin_step)
        s = sns.histplot(dist, bins=bins, cumulative=True) # type: ignore
        fig_path = dir_path / f"levy-distribution-l{location}-s{scale}-q{size}-cumulative.png"
        print(f'Levy Distribution: Location {location}, Scale {scale}, Mean {dist.mean()}, Max {dist.max()}')
        plt.ylim(0, size)
        plt.savefig(fig_path, dpi=400)
        plt.clf()

    @staticmethod
    def generate_node_distante_distribution_figure(levy_plugin:'LevyWalkPlugin', y_limit = 15000) -> None:
        dir_path = Path(__file__).parent / "levy_distribution"
        dir_path.mkdir(parents=True, exist_ok=True)

        distances = []
        for node in levy_plugin.graph.node_list:
            distances.extend([x[0] for x in levy_plugin.get_node_distance(node, levy_plugin.graph)])
        max_distante = max(distances) * 1.05

        bins = np.arange(0, max_distante, levy_plugin.bucket_size)
        s = sns.histplot(distances, bins=bins) # type: ignore
        levy_plugin.graph.experiment_name
        fig_path = dir_path / f"node_distances_{levy_plugin.graph.experiment_name}_{levy_plugin.bucket_size}.png"
        plt.ylim(0, y_limit)
        plt.savefig(fig_path, dpi=400)
        plt.clf()
        s = sns.histplot(distances, bins=bins, cumulative=True) # type: ignore
        levy_plugin.graph.experiment_name
        fig_path = dir_path / f"node_distances_{levy_plugin.graph.experiment_name}_{levy_plugin.bucket_size}_cumulative.png"
        plt.savefig(fig_path, dpi=400)
        plt.clf()

if __name__ == "__main__":
    print("Generating Levy Walk sampling figures")
    dir_path = Path("./levy_distribution")
    dir_path.mkdir(parents=True, exist_ok=True)
    dist_configs = []
    # dist_configs.extend([{"location":1, "scale":1, "start":0, "stop":10, "step":0.1},
    #                     {"location":50, "scale":50, "start":0, "stop":600, "step":1},
    #                     {"location":100, "scale":50, "start":0, "stop":600, "step":1},
    #                     {"location":50, "scale":100, "start":0, "stop":600, "step":1},
    #                     {"location":75, "scale":75, "start":0, "stop":600, "step":1},
    #                     {"location":400, "scale":100, "start":390, "stop":1000, "step":1},
    #                     {"location":0, "scale":600, "start":0, "stop":2500, "step":10},
    #                     {"location":0, "scale":100, "start":0, "stop":1200, "step":10},
    #                     {"location":0, "scale":200, "start":0, "stop":1200, "step":10},
    #                     {"location":0, "scale":50, "start":0, "stop":1200, "step":10},
    #                     {"location":0, "scale":0.025, "start":0, "stop":2, "step":0.01}])

    # Tests for long-lat distance type
    dist_configs.extend([{"location":0, "scale":0.0075, "start":0, "stop":0.4, "step":0.0075},
                         {"location":0, "scale":0.010, "start":0, "stop":0.4, "step":0.0075},
                         {"location":0, "scale":0.015, "start":0, "stop":0.4, "step":0.0075},
                         {"location":0, "scale":0.020, "start":0, "stop":0.4, "step":0.0075}])
    
    # Tests for Geopy/PyProj distance type
    dist_configs.extend([{"location":0, "scale":500, "start":0, "stop":40000, "step":500},
                         {"location":0, "scale":750, "start":0, "stop":40000, "step":500},
                         {"location":0, "scale":1000, "start":0, "stop":40000, "step":500}])

    for config in dist_configs:
        LevyWalkFigures.generate_levy_distribution_figure(
            dir_path=dir_path, location=config["location"],
            scale=config["scale"], size=10000, bin_start=config["start"],
            bin_stop=config["stop"], bin_step=config["step"])