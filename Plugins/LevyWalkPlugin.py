import sys
sys.path.append('../')

import environment 
from population import PopTemplate
import util
from scipy.stats import levy as scipy_levy
import random
import time
from pathlib import Path   

class LevyWalkPlugin(environment.TimeActionPlugin):

    def __init__(self, env_graph: environment.EnvironmentGraph):   
        '''levy_walk
            Pushes population to nearby nodes into a requesting node.


                Requirements:
                    Nodes must have position values in their characteristic dictionaries.

                Params:
                    region: origin region.
                    node: origin node.
                    dist_location: optional levy distribution location parameter.
                    dist_scale: optional levy distribution scale parameter.
                    population_template: PopTemplate to be matched by the operation.

                    isolation_rate: the quantity to reduce movements by. simulates social isolation.
                
                iso_mode: Can be:
                    'regular'
                        Normal plugin operation
        '''
        super().__init__()
        
        self.graph = env_graph
        self.set_pair('levy_walk', self.levy_walk)

        self.mobility_scale = 50

        self.dist_dict = {}
        self.dist_buckets = {}
        self.bucket_size:int = 0.015
        self.use_buckets:bool  = True

        self.distribution_sampler = scipy_levy
        self.distribution_scale = 50
        self.distribution_location = 30
        
        self.levy_probability = 0.05

    def update_time_step(self, cycle_step, simulation_step):
        return

    def levy_walk(self, pop_template, values, cycle_step, sim_step):
        start_time = time.perf_counter()
        assert 'region' in values, "region is not defined in Gather Population TimeAction"
        assert 'node' in values, "node is not defined in Gather Population TimeAction"
        
        if values['region'] == "Azenha" and values['node'] == "home":
            print("LEVY WALKING", cycle_step)

        target_region = self.graph.get_region_by_name(values['region'])
        target_node = target_region.get_node_by_name(values['node'])
        pop_template = PopTemplate(pop_template)

        node_population = target_node.get_population_size(pop_template)
        distances = self.get_distances(target_node, self.graph)

        if values['region'] == "Azenha" and values['node'] == "home":
            print(distances)
        

        return[]

    def get_distances(self, node:environment.EnvNode, graph:environment.EnvironmentGraph):
        unique_name = node.get_unique_name()
        # Checks if the distance was calculated previously
        if self.use_buckets and unique_name in self.dist_buckets:
            return self.dist_buckets[unique_name]
        if not self.use_buckets and unique_name in self.dist_dict:
            return self.dist_dict[unique_name]
        
        # Gets distances between current node and all other nodes
        distance_list = []
        node_pos = node.long_lat
        for other in graph.node_list:
            if unique_name == other.get_unique_name():
                continue
            distance_list.append((util.distance2D(node_pos, other.long_lat), other.get_unique_name()))
        distance_list = sorted(distance_list)
        self.dist_dict[unique_name] = distance_list

        # Gets distances in buckets (based on overall distance)
        max_bucket = int(distance_list[-1][0] // self.bucket_size)
        self.dist_buckets[unique_name] = {}
        for i in range(max_bucket+1):
            self.dist_buckets[unique_name][i] = []
        for d in distance_list:
            bucket = d[0] // self.bucket_size
            self.dist_buckets[unique_name][bucket] += [d]

        # Adds new entry and returns it
        if self.use_buckets:
            return self.dist_buckets[unique_name]
        else:
            return self.dist_dict[unique_name]
        
    

def generate_levy_distribution(dir_path:Path, location: int, scale: int, size: int,
                               bin_start:float, bin_stop: float, bin_step:float) -> None:
    dist = np.array(scipy_levy.rvs(loc=location, scale= scale, size = size))
    bins = np.arange(bin_start, bin_stop, bin_step)
    s = sns.histplot(dist, bins=bins)
    fig_path = dir_path / f"levy-distribution-l{location}-s{scale}-q{size}.png"
    print(f'Levy Distribution: Location {location}, Scale {75}, Mean {sum(dist)/size}')
    plt.savefig(fig_path, dpi=400)
    plt.clf()

if __name__ == "__main__":
    import seaborn as sns
    import matplotlib.pyplot as plt
    import numpy as np 

    print("Generating Levy Walk sampling figures")
    dir_path = Path("./levy_distribution")
    dir_path.mkdir(parents=True, exist_ok=True)
    dist_configs = [ {"location":1, "scale":1, "start":0, "stop":10, "step":0.1},
                    {"location":50, "scale":50, "start":0, "stop":600, "step":1},
                    {"location":100, "scale":50, "start":0, "stop":600, "step":1},
                    {"location":50, "scale":100, "start":0, "stop":600, "step":1},
                    {"location":75, "scale":75, "start":0, "stop":600, "step":1},
                    {"location":400, "scale":100, "start":390, "stop":1000, "step":1},
                    {"location":0, "scale":600, "start":0, "stop":2500, "step":10},
                    {"location":0, "scale":100, "start":0, "stop":1200, "step":10},
                    {"location":0, "scale":200, "start":0, "stop":1200, "step":10},
                    {"location":0, "scale":50, "start":0, "stop":1200, "step":10}]
    
    for config in dist_configs:
        generate_levy_distribution(dir_path=dir_path, location=config["location"], 
                                   scale=config["scale"], size=10000, bin_start=config["start"], 
                                   bin_stop=config["stop"], bin_step=config["step"])