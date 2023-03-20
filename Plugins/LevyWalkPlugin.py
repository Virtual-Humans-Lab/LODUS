import copy
import sys
from enum import Enum
from typing import Optional

from LevyWalkFigures import LevyWalkFigures

sys.path.append('../')

import random
import time

from scipy.stats import levy as scipy_levy

import environment
import util


class LevyDistance(Enum):
    LONG_LAT = 1
    METRES_GEOPY = 2
    METRES_PYPROJ = 3

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
        
        self.distribution_sampler = scipy_levy
        if "levy_walk_plugin" not in self.graph.experiment_config:
            print("Experiment config should have a 'levy_walk_plugin' key. Using an empty entry")

        # Loads experiment configuration, if any
        self.config:dict = self.graph.experiment_config.get("levy_walk_plugin", {})
        
        self.distance_type:LevyDistance = LevyDistance(self.config.get("distance_type",
                                                                       LevyDistance.LONG_LAT))
        self.use_buckets:bool = self.config.get("use_buckets", True)
        self.population_group_size:int = self.config.get("population_group_size", 50)
        self.movement_probability:float = self.config.get("movement_probability", 0.05)
        self.distribution_location:float = self.config.get("distribution_location", 0.0)

        if self.distance_type == LevyDistance.LONG_LAT:
            self.bucket_size:float = self.config.get("distance_bucket_size", 0.0075)
            self.distribution_scale:float = self.config.get("distribution_scale", 0.005)
        else:
            self.bucket_size:float = self.config.get("distance_bucket_size", 500)
            self.distribution_scale:float = self.config.get("distribution_scale", 200.0)
        
        # Distaces from one EnvNode to others
        self.dist_dict = {}
        self.dist_buckets = {}

        # Performance log for quantity of sub-actions
        self.sublist_count = []

        # Generate figures for debug
        # self.calculate_all_distances()
        # LevyWalkFigures.generate_node_distante_distribution_figure(self, y_limit=20000)
        # exit(0)

    def update_time_step(self, cycle_step, simulation_step):
        return

    def levy_walk(self, pop_template, values:dict, cycle_step:int, sim_step:int):
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
        
        if "ignore_acting_node_type" in values and acting_node.name in values["ignore_acting_node_type"]:
            return sub_list
        
        # Loads optional action parameters, otherwise, use default values
        _use_buckets:bool = values.get("use_buckets", self.use_buckets)
        _pop_group_size:int = values.get("population_group_size", self.population_group_size)
        _mov_probability:float = values.get("movement_probability", self.movement_probability)
        _dist_location:float = values.get("distribution_location", self.distribution_location)
        _dist_scale:float = values.get("distribution_location", self.distribution_scale)
        
        if _use_buckets:
            distances = self.get_node_distance_bucket(acting_node, self.graph)
        else:
            distances = self.get_node_distance(acting_node, self.graph)
        
        if "target_node_type" in values:
            distances = self.filter_target_node_types(distances=distances,
                                                      target_nodes=values["target_node_type"])

        # Divides the population amount in packets to be sent to other nodes
        packets = node_population // _pop_group_size

        # Generates sub-actions for each packet
        for i in range(packets):

            # Reduces the chance for a levy walk to occur bor each packet
            if _mov_probability < random.random():
                continue
            
            sampled_dist = self.levy_sample(location=_dist_location, scale=_dist_scale)
            
            if _use_buckets:
                selected = self.bucket_search(distances, sampled_dist)
                if selected == None:
                    continue
                target_node_u_name:str = selected[1]
            else:
                ix = self.binary_search(distances, sampled_dist)
                if ix == -1:
                    continue
                target_node_u_name:str =  distances[ix][1]

            target_region, target_node = target_node_u_name.split('//')
            target_region = self.graph.get_region_by_name(target_region)
            target_node = target_region.get_node_by_name(target_node)

            # Creates a Move Population action from the Acting Nodo to the Target Node
            new_action_type = 'move_population'
            new_action_values = {'origin_region': acting_region.name,
                                 'origin_node': acting_node.name,
                                 'destination_region': target_region.name,
                                 'destination_node': target_node.name,
                                 'quantity': self.population_group_size}
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

    # Gets distances based on selected distance type
    def get_distance(self, p1, p2):
        if self.distance_type == LevyDistance.LONG_LAT:
            return util.distance2D(p1, p2)
        elif self.distance_type == LevyDistance.METRES_GEOPY:
            return util.geopy_distance_metre(p1, p2)
        elif self.distance_type == LevyDistance.METRES_PYPROJ:
            return util.pyproj_distance_metre(p1, p2)
        else:
            exit("Levy Distance Type is invalid")

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
            distance_list.append((self.get_distance(node_pos, other.long_lat), other.get_unique_name()))
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

    def filter_target_node_types(self, distances, target_nodes:list[str]):
        if self.use_buckets:
            for bucket in distances:
                distances[bucket] = [dist for dist in distances[bucket] if 
                                     str(dist[1]).split("//")[1] in target_nodes]
                
        else: 
            raise Exception("Error in filter_target_node_types - Levy Walk Plugin")
        return distances

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

if __name__ == "__main__":
    pass