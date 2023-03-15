import copy
import sys
from typing import Optional

import numpy
sys.path.append('../')

import environment
from population import PopTemplate
import util
from scipy.stats import levy as scipy_levy
import random
import time
from pathlib import Path
import seaborn as sns
import matplotlib.pyplot as plt
import numpy as np

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
        #self.bucket_size:float = 0.015
        self.bucket_size:float = 500
        self.use_buckets:bool  = True

        self.distribution_sampler = scipy_levy
        # self.distribution_scale = 50
        # self.distribution_location = 30
        self.distribution_scale = 0.005
        self.distribution_location = 0.0

        self.levy_probability = 0.05

        # Performance log for quantity of sub-actions
        self.sublist_count = []

        self.calculate_all_distances()
        self.generate_distante_distribution_figure()
        exit(0)

    def update_time_step(self, cycle_step, simulation_step):
        return

    def levy_walk(self, pop_template, values, cycle_step, sim_step):
        start_time = time.perf_counter()
        assert 'region' in values, "region is not defined in Gather Population TimeAction"
        assert 'node' in values, "node is not defined in Gather Population TimeAction"

        if values['region'] == "Azenha" and values['node'] == "home":
            print("LEVY WALKING", cycle_step)

        acting_region = self.graph.get_region_by_name(values['region'])
        acting_node = acting_region.get_node_by_name(values['node'])
        sub_list = [] 

        node_population = acting_node.get_population_size(pop_template)
        if node_population == 0:
            return sub_list
        
        if self.use_buckets:
            distances = self.get_node_distance_bucket(acting_node, self.graph)
        else:
            distances = self.get_node_distance(acting_node, self.graph)

        # Divides the population amount in packets to be sent to other nodes
        packets = node_population // self.mobility_scale

        # Generates sub-actions for each packet
        for i in range(packets):

            # Reduces the chance for a levy walk to occur bor each packet
            if self.levy_probability < random.random():
                continue
            
            #print("TYPE", type(self.distribution_sampler.rvs()))
            if 'dist_location' in values and 'dist_scale' in values:
                distance = self.levy_sample(location=float(values['dist_location']),
                                            scale=float(values['dist_scale']))
            else:
                distance = self.levy_sample()

            if self.use_buckets:
                selected = self.bucket_search(distances, distance)
                if selected == None:
                    continue
                target_node_u_name:str = selected[1]
            else:
                ix = self.binary_search(distances, distance)
                if ix == -1:
                    continue
                target_node_u_name:str =  distances[ix][1]

            target_region, target_node = target_node_u_name.split('//')
            target_region = self.graph.get_region_by_name(target_region)
            target_node = target_region.get_node_by_name(target_node)

            # Creates a Move Population action
            new_action_type = 'move_population'
            new_action_values = {'origin_region': acting_region.name,
                                 'origin_node': acting_node.name,
                                 'destination_region': target_region.name,
                                 'destination_node': target_node.name,
                                 'quantity': self.mobility_scale}
            temp = copy.deepcopy(pop_template)
            #temp.mother_blob_id = acting_region.id

            new_action = environment.TimeAction(action_type = new_action_type,
                                                pop_template = temp,
                                                values = new_action_values)
            #print(new_action)
            sub_list.append(new_action)

        self.add_execution_time(time.perf_counter() - start_time)
        self.sublist_count.append(len(sub_list))
        return sub_list

    def calculate_all_distances(self):
        for node in self.graph.node_list:
            self.get_node_distance(node, self.graph)
            self.get_node_distance_bucket(node, self.graph)

    # Gets distances between current node and all other nodes
    def get_node_distance(self, node:environment.EnvNode, graph:environment.EnvironmentGraph):
        unique_name = node.get_unique_name()
        # Checks if the distance was calculated previously
        if unique_name in self.dist_dict:
            return self.dist_dict[unique_name]
        
        distance_list = []
        node_pos = node.long_lat
        for other in graph.node_list:
            if unique_name == other.get_unique_name():
                continue
            distance_list.append((util.pyproj_distance_metre(node_pos, other.long_lat), other.get_unique_name()))
        distance_list = sorted(distance_list)

        self.dist_dict[unique_name] = distance_list
        return self.dist_dict[unique_name]
    
    # Gets distances in buckets (based on overall distance)
    def get_node_distance_bucket(self, node:environment.EnvNode, graph:environment.EnvironmentGraph):
        unique_name = node.get_unique_name()
        # Checks if the distance was calculated previously
        if unique_name in self.dist_buckets:
            return self.dist_buckets[unique_name]
        
        # Gets distances in buckets (based on overall distance)
        distance_list = self.get_node_distance(node, graph)
        max_bucket = int(distance_list[-1][0] // self.bucket_size)
        self.dist_buckets[unique_name] = {}
        for i in range(max_bucket+1):
            self.dist_buckets[unique_name][i] = []
        for d in distance_list:
            bucket = d[0] // self.bucket_size
            self.dist_buckets[unique_name][bucket] += [d]

        return self.dist_buckets[unique_name]

    def levy_sample(self, location:Optional[float] = None,
                    scale:Optional[float] = None):
        if location is not None and scale is not None:
            return self.distribution_sampler.rvs(loc=location,
                                                 scale= scale)
        else:
            return self.distribution_sampler.rvs(loc=self.distribution_location,
                                                 scale= self.distribution_scale)
        
    def bucket_search(self, buckets_dict, distance):
        bucket = int(distance // self.bucket_size)
        if bucket not in buckets_dict:
            return None
        
        target_bucket = buckets_dict[bucket]

        if len(target_bucket) == 0:
            return None

        random_index = random.randint(0, len(target_bucket)-1)

        if target_bucket[0][0] > distance:
            return None
        return target_bucket[random_index]
    
    def binary_search(self, buckets_dict, distance):
        l = 0
        u = len(buckets_dict) - 1

        while l < u and l != (u-1):
            m = (l + u) // 2
            v2 = buckets_dict[m][0]
            if v2 > distance:
                u = m
            else:
                l = m

        if l == 0:
            l =  ( -1 if buckets_dict[0][0] > distance else 0)
        
        return l
    
    def print_execution_time_data(self):
        super().print_execution_time_data()
        print("---Total subactions count:", sum(self.sublist_count))
        if len(self.sublist_count) > 0:
            print("---Average subaction count:", sum(self.sublist_count)/len(self.sublist_count))

    def generate_distante_distribution_figure(self) -> None:
        dir_path = Path(__file__).parent / "levy_distribution"
        dir_path.mkdir(parents=True, exist_ok=True)
        
        distances = []
        for node in self.graph.node_list:
            distances.extend([x[0] for x in self.get_node_distance(node, self.graph)])
        max_distante = max(distances) * 1.05
        bins = np.arange(0, max_distante, self.bucket_size)
        s = sns.histplot(distances, bins=bins) # type: ignore
        self.graph.experiment_name
        fig_path = dir_path / f"{self.graph.experiment_name}_node_distances_{self.bucket_size}.png"
        print(fig_path)
        plt.savefig(fig_path, dpi=400)
        plt.clf()

def generate_levy_distribution_figure(dir_path:Path, location: int, scale: int, size: int,
                            bin_start:float, bin_stop: float, bin_step:float) -> None:
    dist = np.array(scipy_levy.rvs(loc=location, scale= scale, size = size))
    bins = np.arange(bin_start, bin_stop, bin_step)
    s = sns.histplot(dist, bins=bins) # type: ignore
    fig_path = dir_path / f"levy-distribution-l{location}-s{scale}-q{size}.png"
    print(f'Levy Distribution: Location {location}, Scale {scale}, Mean {sum(dist)/size}, Max {max(dist)}')
    plt.savefig(fig_path, dpi=400)
    plt.clf()

if __name__ == "__main__":
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
                    {"location":0, "scale":50, "start":0, "stop":1200, "step":10},
                    {"location":0, "scale":0.025, "start":0, "stop":2, "step":0.01}]
    
    for config in dist_configs:
        generate_levy_distribution_figure(
            dir_path=dir_path, location=config["location"],
            scale=config["scale"], size=10000, bin_start=config["start"],
            bin_stop=config["stop"], bin_step=config["step"])