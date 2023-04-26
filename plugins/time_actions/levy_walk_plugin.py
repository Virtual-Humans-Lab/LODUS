import copy
import sys
from typing import Optional

from random_inst import FixedRandom

sys.path.append('../')

import random
import time

from scipy.stats import levy as scipy_levy

import environment
from util import DistanceType

import pandas as pd


class LevyWalkPlugin(environment.TimeActionPlugin):

    def __init__(self, env_graph: environment.EnvironmentGraph):
        '''
        Plugin that consumes a 'levy_walk' TimeAction type.
        Complex TimeAction that returns multiple 'move_population' actions.

        Moves population from the acting node to other nodes using distances sampled from a levy distribution.
        The distance sampled indicates the 'desired travel distance', and the function identifies nodes in that distance.
        Population is divided into packets, with each packet having a probability of moving to other nodes.
        Can use buckets to group nodes based of distances (e.g., nodes from 0 to 500 metres, 501 to 1000 and so on).
        
        Requirements:
            EnvNodes must have a 'long_lat' position value, represented as a list of 2 floats.

        Plugin Parameters (default values can be overriden by the experiment configuration):
            distance_type (enum): represents the distance type used to measure distances between EnvNodes (either Long_Lat or Metres with Geopy or PyProj)
            use_buckets (bool): represents if the action with use distance buckets or a simples distance list
            bucket_size (float): represents the size (width/range) for each distance bucket
            population_group_size (int): represents the size of each population group trying to move to other nodes
            movement_probability (float): represents the probability of a group moving to other node.
            distribution_location (float): represents the location parameter of a levy distribution
            distribution_scale (float): represents the scale parameter of a levy distirbution
            
        'levy_walk' Parameters:
            region (str): acting_region (origin of population movement).
            node (str): acting_node (origin of population movement).
            population_template: PopTemplate to be matched by the operation (population moved).
            ignore_acting_node_type (list[str]): optional parameter. If the acting_node type is in this list, 
                the levy walk function returns an empty subaction list
            target_node_type (list[str]): optional parameter used to filter possible destination for the population.
                Can be used, e.g., to select only 'work' nodes as a possible destination

            ***The action may also receive the plugin parameters to override their values. 
                Otherwise, the default plugin values are used.
                This includes 'use_buckets', 'population_group_size', 'movement_probability', 
                'distribution_location' and 'distribution_scale'.
                The 'distance_type' and 'bucket_size' cannot be overridden.
        '''
        super().__init__()
        
        self.distribution_sampler = scipy_levy
        self.graph = env_graph
        self.set_pair('levy_walk', self.levy_walk)
        
        if "levy_walk_plugin" not in self.graph.experiment_config:
            print("Experiment config should have a 'levy_walk_plugin' key. Using an empty entry (default plugin values)")

        # Loads experiment configuration, if any
        self.config:dict = self.graph.experiment_config.get("levy_walk_plugin", {})
        
        self.distance_type:DistanceType = DistanceType(self.config.get("distance_type",
                                                                       DistanceType.LONG_LAT))
        self.use_buckets:bool = self.config.get("use_buckets", True)
        self.population_group_size:int = self.config.get("population_group_size", 50)
        self.movement_probability:float = self.config.get("movement_probability", 0.05)
        self.distribution_location:float = self.config.get("distribution_location", 0.0)

        if self.distance_type == DistanceType.LONG_LAT:
            self.bucket_size:float = self.config.get("distance_bucket_size", 0.005)
            self.distribution_scale:float = self.config.get("distribution_scale", 0.005)
        else:
            self.bucket_size:float = self.config.get("distance_bucket_size", 500)
            self.distribution_scale:float = self.config.get("distribution_scale", 200.0)

        # Distaces buckets from one EnvNode to others
        self.dist_buckets:dict[int, list[tuple[float,str]]] = {}

        # Performance log for quantity of sub-actions
        self.sublist_count = []

        self.sampled_distances = []
        self.random = FixedRandom.instance

    def update_time_step(self, cycle_step, simulation_step):
        return

    def levy_walk(self, pop_template, values:dict, cycle_step:int, sim_step:int):
        '''Function to consume a 'levy_walk' TimeAction type.'''
        start_time = time.perf_counter()
        assert 'region' in values, "region is not defined in Levy Walk TimeAction"
        assert 'node' in values, "node is not defined in Levy Walk TimeAction"

        acting_region = self.graph.get_region_by_name(values['region'])
        acting_node = acting_region.get_node_by_name(values['node'])
        sub_list = [] 

        if "ignore_acting_node_type" in values and acting_node.name in values["ignore_acting_node_type"]:
            return sub_list

        node_population = acting_node.get_population_size(pop_template)
        if node_population == 0:
            return sub_list
        
        # Loads optional action parameters, otherwise, use default values
        _use_buckets:bool = values.get("use_buckets", self.use_buckets)
        _pop_group_size:int = values.get("population_group_size", self.population_group_size)
        _mov_probability:float = values.get("movement_probability", self.movement_probability)
        _dist_location:float = values.get("distribution_location", self.distribution_location)
        _dist_scale:float = values.get("distribution_scale", self.distribution_scale)
    
        if _use_buckets:
            distances = self.get_node_distance_bucket(acting_node, self.graph)
        else:
            distances = self.get_node_distance(acting_node, self.graph)
        
        if "target_node_type" in values:
            distances = self.filter_target_node_types(buckets_dict=distances,
                                                      target_nodes=values["target_node_type"])

        # if 'node_type' in values and 'home' in values['node_type']:
        #     print(distances)
        #     exit()

        # Divides the population amount in packets to be sent to other nodes
        packets = node_population // _pop_group_size

        # if values['region'] == "Azenha" and values['node'] == "home":
        #    print("LEVY WALKING", cycle_step, packets, _mov_probability)

        # Generates sub-actions for each packet
        for i in range(packets):
            
            # Reduces the chance for a levy walk to occur bor each packet
            _random_number = self.random.random()
            if _mov_probability < _random_number:
                continue

            target_node_u_name = self.select_valid_target(location=_dist_location, 
                                                          scale=_dist_scale,
                                                          use_buckets=_use_buckets,
                                                          distances=distances)
            
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
    
    def select_valid_target(self, location:float, scale:float, use_buckets:bool, distances) -> str:
        target_unique_name = ''
        count = 0
        sampled_dist = 0.0
        while target_unique_name == '':
            sampled_dist = self.levy_sample(location=location, scale=scale)
            count += 1
            if count > 100:
                print("Levy Walk Plugin: could not find valid target in 100 tries")
                exit()
            if use_buckets:
                selected = self.bucket_search(distances, sampled_dist)
                if selected == None:
                    continue
                target_unique_name =  selected[0]
            else:
                ix = self.binary_search(distances, sampled_dist)
                if ix == -1:
                    continue
                target_unique_name = distances[ix][0]
        self.sampled_distances.append(sampled_dist)
        return target_unique_name
    
    def get_node_distance_bucket(self, target_node:environment.EnvNode, graph:environment.EnvironmentGraph):
        '''Gets distances in buckets (based on overall distance)'''
        unique_name = target_node.get_unique_name()
        
        # Checks if the distance was calculated previously
        if unique_name in self.dist_buckets:
            return self.dist_buckets[unique_name].copy()
        
        # Gets distances in buckets (based on overall distance)
        distance_list = self.graph.get_node_distances(target_node, self.distance_type).get_distance_tuples()
        max_bucket = int(distance_list[-1][1] // self.bucket_size)
        self.dist_buckets[unique_name] = {}
        for i in range(max_bucket+1):
            self.dist_buckets[unique_name][i] = []
        for d in distance_list:
            bucket = d[1] // self.bucket_size
            self.dist_buckets[unique_name][bucket] += [d]
        
        return self.dist_buckets[unique_name].copy()

    def filter_target_node_types(self, buckets_dict:dict, target_nodes:list[str]):
        ''' 
        Filters a distance bucket dict to only include entries where the node type is is 'target_nodes'
        Raises an exception if the plugin shouldn't be using buckets
        '''
        __filtered = {}
        if not self.use_buckets:
            raise Exception("Error in filter_target_node_types - Levy Walk Plugin")
        for bucket in buckets_dict:
            __filtered[bucket] = [dist for dist in buckets_dict[bucket] if 
                                    str(dist[0]).split("//")[1] in target_nodes]
        return __filtered

    def levy_sample(self, location:Optional[float] = None,
                    scale:Optional[float] = None):
        '''
        Samples from a levy distribution using the distribution sampler (from scipy_levy)

        Parameters:
        ------
        location: optional location parameter for the distribution. Only used if 'scale' is also provided.
        scale: optional scale parameter for the distribution. Only used if 'location' is also provided.
        '''
        if location is not None and scale is not None:
            return self.distribution_sampler.rvs(loc=location,
                                                 scale= scale)
        else:
            return self.distribution_sampler.rvs(loc=self.distribution_location,
                                                 scale= self.distribution_scale)
        
    def bucket_search(self, buckets_dict:dict, distance:float) -> list[tuple[float,str]]:
        '''
        This function performs a bucket search to find the EnvNode with a distance value >= to the input distance. 
        
        Parameters:
        -----------
        buckets_dict: a dictionary of buckets (lists based of distances) of distances to other EnvNodes (tuples)
        distance: distance to search for.

        Returns:
        -----------
        A tuple (int, str) containing the distance to the selected EnvNode and the EnvNode unique name.
        Return None if the distance input is lower or larger than all distances
        Return None if no EnvNode is within the selected bucket
        
        '''
        # Gets the bucket index based on distance and bucket sizes
        bucket = int(distance // self.bucket_size)
        if bucket not in buckets_dict: # bucket not found (index too large)
            return None
        
        # Gets the target bucket
        target_bucket = buckets_dict[bucket]
        if len(target_bucket) == 0: # empty bucket
            return None

        # Gets a random valid entry in the target bucket and returns it
        random_index = self.random.randint(0, len(target_bucket)-1)
        return target_bucket[random_index]
    
    def binary_search(self, distances_dict:list[tuple[float, str]], distance: float) -> int:
        '''
        This function implements a binary search algorithm to find the EnvNode with a distance value >= to the input distance. 
        
        Parameters:
        -----------
        distances_dict: a dictionary of distances to other EnvNodes (tuples)
        distance: distance to search for.

        Returns:
        -----------
        The key of the distances_dict.
        Return -1 if the distance input is lower than the lowest distances
        '''
        # Target distance is lower than minimun distance
        if distances_dict[0][0] > distance:
            return -1
        
        # Standard binary search
        _lower = 0
        _upper = len(distances_dict) - 1

        while _lower < _upper and _lower != (_upper-1):
            _middle = (_lower + _upper) // 2
            v2 = distances_dict[_middle][0]
            if v2 > distance:
                _upper = _middle
            else:
                _lower = _middle
        return _lower
    
    def print_execution_time_data(self):
        super().print_execution_time_data()
        print("---Total subactions count:", sum(self.sublist_count))
        if len(self.sublist_count) > 0:
            print("---Average subaction count:", sum(self.sublist_count)/len(self.sublist_count))

if __name__ == "__main__":
    pass