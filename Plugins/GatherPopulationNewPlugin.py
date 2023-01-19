import sys
sys.path.append('../')

import environment 
from population import PopTemplate
from random_inst import FixedRandom
import copy
import random
import math
import numpy as np
import util
import time

class GatherPopulationNewPlugin(environment.TimeActionPlugin):


    def __init__(self, env_graph: environment.EnvironmentGraph, isolation_rate = 0.0, to_total_ratio_correction = 0.2, locals_only = False):
        '''gather_population
            TODO WARNING IS CURRENTLY OFF BY ONE!
            
            Gathers population from nearby nodes into a requesting node.
                Params:
                    region: destination region.
                    node: destination node.
                    quantity: population size requested.
                    population_template: PopTemplate to be matched by the operation.
                    isolation_rate: the quantity to reduce movements by. simulates social isolation.
                    to_total_ratio_correction: corrects the ratio for gather_population operations, so that operations are based on the entire 
                        population of the node. a value between 0 and 1. However many % the original operation leaves in the node.
                    locals_only: forces gathering to only pull from native populations for each node.
                
                iso_mode: Can be:
                    'regular'
                        changes movement quantities by isolation rate percentage. global.
                    'quantity_correction'
                        corrects to assume the operation requested x% of the population, but wanted the entire population.
        '''
        super().__init__()
        self.graph = env_graph

        self.iso_mode = 'regular'
        self.to_total_ratio_correction = to_total_ratio_correction


        self.isolation_rate = isolation_rate

        self.locals_only = locals_only

        self.DEBUG_OPERATION_OUTPUT = False
        self.DEBUG_OPERATION_REGIONS = ["Azenha"]
        self.DEBUG_ALL_REQUESTS = False
        self.DEBUG_REGIONS = []
        
        self.set_pair('gather_population', self.gather_population)
        # Distances between EnvNodes
        self.distances_map = {}
        self.weights_map = {}

        self.sublist_count = []


    def update_time_step(self, cycle_step, simulation_step):
        return

    # Returns the distance between two regions
    def get_distance(self, region1:str, region2:str, pos1:list[float], pos2:list[float])->float:
        # Checks if the distance was calculated previously
        if region1 + region2 in self.distances_map:
            return self.distances_map[region1 + region2]
        if region2 + region1 in self.distances_map:
            return self.distances_map[region2 + region1]

        # Adds new entry and returns it
        self.distances_map[region1+region2] = util.distance2D(pos1, pos2)
        return self.distances_map[region1+region2]

    # Returns the distance between two nodes
    def get_nodes_distance(self, node1:environment.EnvNode, node2:environment.EnvNode)->float:
        n1_name = node1.get_unique_name()
        n2_name = node2.get_unique_name()
        # Checks if the distance was calculated previously
        if n1_name + n2_name in self.distances_map:
            return self.distances_map[n1_name + n2_name]
        if n2_name + n1_name in self.distances_map:
            return self.distances_map[n2_name + n1_name]

        # Adds new entry and returns it
        self.distances_map[n1_name+n2_name] = util.distance2D(node1.long_lat, node2.long_lat)
        return self.distances_map[n1_name+n2_name]

    def compute_weights_old(self, target_region, regions):
    
        if target_region.name in self.weights_map:
            return self.weights_map[target_region.name]

        distance_list = []

        if self.DEBUG_OPERATION_OUTPUT:
            debug_node_ids = []

        for x in range(len(self.graph.region_list)):
            region = self.graph.region_list[x]
            current_region_dist = 200
            if region.id != target_region.id:
                current_region_dist = self.get_distance(region.name, target_region.name, region.position, target_region.position)

            for node_aux in region.node_list:
                distance_list.append(current_region_dist)
                if self.DEBUG_OPERATION_OUTPUT:
                    debug_node_ids.append(node_aux.id)

        total_dist = sum(distance_list)

        weight_list = [(total_dist / d) for d in distance_list]

        self.weights_map[target_region.name] = weight_list

        return self.weights_map[target_region.name]

    def compute_node_weights(self, target_node:environment.EnvNode)->list[tuple[environment.EnvNode,float]]:
        
        # Checks if weights were calculated previously
        unique_name = target_node.get_unique_name()
        if unique_name in self.weights_map:
            return self.weights_map[unique_name]
        
        distance_list:list[tuple[environment.EnvNode,float]] = []

        for other in self.graph.node_list:
            distance_to_other = 0.01
            
            if other.get_unique_name() != unique_name:
                distance_to_other = self.get_nodes_distance(target_node, other)

            distance_list.append((other,distance_to_other))

        #for region in self.graph.region_list:
        #    distance_to_other = 0.01
        #    
        #    if region.name != target_region.name:
        #        distance_to_other = self.get_distance(region.name, 
        #                                                target_region.name, 
        #                                                region.position, 
        #                                                target_region.position)#
        #
        #    for node_aux in region.node_list:
        #        distance_list.append((node_aux, distance_to_other))
        #print("distances")
        #print([ d for (n, d) in distance_list])
        total_dist = sum([ (1/d) for (n, d) in distance_list])
        weight_list = [(n,  ( (1/d) / total_dist)) for (n, d) in distance_list]

        # Adds new entry and returns it
        self.weights_map[unique_name] = weight_list
        return self.weights_map[unique_name]
    
    ## Complex time action. Will be broken up into smaller actions
    def gather_population(self, pop_template, values, cycle_step, sim_step):
        start_time = time.perf_counter()
        assert 'region' in values, "region is not defined in Gather Population TimeAction"
        assert 'node' in values, "node is not defined in Gather Population TimeAction"
        
        target_region = self.graph.get_region_by_name(values['region'])
        target_node = target_region.get_node_by_name(values['node'])
            
        if self.DEBUG_OPERATION_OUTPUT and target_node.containing_region_name in self.DEBUG_OPERATION_REGIONS:
            print("########## CONVERGE_POPULATION")
            print('converge Values: \n', values)
            
        sub_list = [] 
        quantity = values['quantity']

        if quantity == 0: 
            return sub_list

        # Get node weights
        weight_list = self.compute_node_weights(target_node)

        # Filters undesired EnvNodes
        if 'only_locals' in values and bool(values['only_locals']):
            weight_list = [(node, weight) for (node,weight) in weight_list if (node.containing_region_name == target_node.containing_region_name)]
        if 'different_node_name' in values and bool(values['different_node_name']):
            weight_list = [(node, weight) for (node,weight) in weight_list if (node.name != target_node.name)]
        
        # Adds available population and remove entries where available = 0
        weight_and_available = [(n, w, n.get_population_size(pop_template)) for (n,w) in weight_list]
        weight_and_available = [(n, w, a) for (n,w, a) in weight_and_available if a > 0]

        # Gets total population available and adjusts quantity if necessary
        total_pop_available = sum([a for (n, w, a) in weight_and_available])
        if total_pop_available < quantity:
            quantity = total_pop_available
        if quantity == 0: 
            return sub_list

        #available_pop = [a for (n, w, a) in weight_and_available if a > 0]
        #weight_list = [(n, w) for (n, w, a) in weight_and_available]

        int_weights = util.distribute_ints_from_weights_with_limit(quantity, 
            [w for (n, w, a) in weight_and_available],
            [a for (n, w, a) in weight_and_available])
        
        total_weight = sum([w for (n, w, a) in weight_and_available])
        node_targets = [(weight_and_available[i][0], 
                        weight_and_available[i][1] / total_weight,
                        int_weights[i]) 
                        for i in range(len(int_weights)) if int_weights[i] > 0]
        # print([a for (n,w,a) in weight_and_available]) # Available population
        # print([w for (n,w,a) in weight_and_available]) # EnvNode weights
        # print([b for (a,b,c) in node_targets]) # Weight proportion
        # print([c for (a,b,c) in node_targets]) # Int weight
        # exit(0)
        list_count = 0
        total_quant = 0
        remainder = 0.0
        
        for node_aux, w, i in node_targets:
            
            region = self.graph.get_region_by_name(node_aux.containing_region_name)
            isolation_factor = self.isolation_rate
            
            new_action_type = 'move_population'
            new_action_values = { 'origin_region': region.name,
                                'origin_node': node_aux.name,
                                'destination_region': target_region.name,
                                'destination_node': target_node.name}
           
            if self.iso_mode == 'regular':
                new_action_values['quantity'] = i
            elif self.iso == 'regular_isolation':
                quant_float = float(i) + remainder
                new_action_values['quantity'] = int(round(quant_float, 5))
                remainder = quant_float % 1.0
            elif self.iso_mode == 'quantity_correction':
                iso_factor = (1 - isolation_factor) / (1 - self.to_total_ratio_correction) 
                new_action_values['quantity'] = int(quantity * w * iso_factor)
            elif self.iso_mode == 'random_nudge':
                #iso_factor = ( 1 - (self.isolation_rate + (random.random() * 0.05  - 0.025))) / (1 - self.to_total_ratio_correction) 
                iso_factor = ( 1 - (self.isolation_rate + (FixedRandom.instance.random() * 0.05  - 0.025))) / (1 - self.to_total_ratio_correction) 
                new_action_values['quantity'] = quantity * w * iso_factor

            if new_action_values['quantity'] == 0:
                continue

            temp = pop_template

            if self.locals_only:
                temp = copy.deepcopy(pop_template)
                temp.mother_blob_id = target_region.id

            total_quant += new_action_values['quantity']
            new_action = environment.TimeAction(action_type = new_action_type, 
                                                pop_template = pop_template,
                                                values = new_action_values)
            #print(new_action_values)
            
            sub_list.append(new_action)
            #self.graph.direct_action_invoke(new_action, hour, time)
            #list_count +=1 

        if self.DEBUG_ALL_REQUESTS or target_region.name in self.DEBUG_REGIONS:
            print(f'To {target_region.name}\tReq: {quantity} Sent: {total_quant}')
        self.add_execution_time(time.perf_counter() - start_time)
        self.sublist_count.append(len(sub_list))
        return sub_list
    
    def print_execution_time_data(self):
        super().print_execution_time_data()
        print("---Total subactions count:", sum(self.sublist_count))
        if len(self.sublist_count) > 0:
            print("---Average subaction count:", sum(self.sublist_count)/len(self.sublist_count))