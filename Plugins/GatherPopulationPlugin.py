import sys
sys.path.append('../')

import environment 
from population import PopTemplate
import copy
import random
import math
import numpy as np
import util

class GatherPopulationPlugin(environment.TimeActionPlugin):


    def __init__(self, env_graph, isolation_rate = 0.0, to_total_ratio_correction = 0.2, locals_only = False):
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

        self.set_pair('gather_population', self.converge_population)

        self.distance_map = {}
        self.weights_map = {}



    def get_distance(self, name1, name2, pos1, pos2):
        if name1 + name2 is self.distance_map:
            return self.distance_map[name1 + name2]
        
        if name2 + name1 is self.distance_map:
            return self.distance_map[name2 + name1]
        
        self.distance_map[name1+name2] = util.distance2D(pos1, pos2)
        return self.distance_map[name1+name2]

    def compute_weights(self, target_region, regions):

        if target_region.name in self.weights_map:
            return self.weights_map[target_region.name]

        distance_list = []

        if self.DEBUG_OPERATION_OUTPUT:
            debug_node_ids = []

        for x in range(len(self.graph.region_list)):
            region = self.graph.region_list[x]
            current_region_dist = 10000000
            if region.id != target_region.id:
                current_region_dist = self.get_distance(region.name, target_region.name, region.position, target_region.position)

            for node_aux in region.node_list:
                distance_list.append(current_region_dist)
                if self.DEBUG_OPERATION_OUTPUT:
                    debug_node_ids.append(node_aux.id)

        total_dist = sum(distance_list)

        weight_list = [(total_dist / d) for d in distance_list]

        if self.DEBUG_OPERATION_OUTPUT:
            print("node_list :", debug_node_ids, '\n')
            print('dist: \n', total_dist, '\n', "weights: ", weight_list, '\n', "ratio pop: ", ratioed_pop, '\n')
            print("moves: ", '\n')

        self.weights_map[target_region.name] = weight_list

        return self.weights_map[target_region.name]


     ## Complex time action. Will be broken up into smaller actions
    def converge_population(self, values, hour, time):
        #print("CONVERGING")
        if self.DEBUG_OPERATION_OUTPUT :
            print("########## CONVERGE_POPULATION")
            print('converge Values: \n', values, '\n')

        target_region = values['origin_region']
        if isinstance(target_region, str):
            target_region = self.graph.get_region_by_name(values['origin_region'])

        target_node = values['origin_node']
        if isinstance(target_node, str):
            target_node = target_region.get_node_by_name(target_node)

        quantity = values['quantity']
        pop_template = values['population_template']


        sub_list = []
        available_pop = []
        for region in  self.graph.region_list:
            for node in region.node_list:
                available_pop.append(node.get_population_size(pop_template))


        weight_list = self.compute_weights(target_region, self.graph.region_list)
        #print (available_pop)
        #print (quantity)
        #print (weight_list)
        ratioed_pop = util.weighted_int_distribution_with_weights(available_pop, quantity, weight_list)

        if self.DEBUG_OPERATION_OUTPUT :
            print(f'converge Values: \n{ratioed_pop}\n')

        list_count = 0
        for x in range(len(self.graph.region_list)):
            region = self.graph.region_list[x]
            for node_aux in region.node_list:

                new_action_values = {}
                new_action_type = 'move_population'
                
                new_action_values['origin_region'] = region.name

                new_action_values['origin_node'] = node_aux.name
                new_action_values['destination_region'] = target_region.name

                new_action_values['destination_node'] = target_node.name
                
                ### regular iso factor
                if self.iso_mode == 'regular':
                    new_action_values['quantity'] = ratioed_pop[list_count] * (1 - self.isolation_rate)
                elif self.iso_mode == 'quantity_correction':
                    iso_factor = ( 1 - self.isolation_rate) / (1 - self.to_total_ratio_correction) 
                    new_action_values['quantity'] = ratioed_pop[list_count] * iso_factor

                temp = pop_template

                if self.locals_only:
                    temp = copy.deepcopy(pop_template)
                    temp.mother_blob_id = region.id

                new_action_values['population_template'] = temp

                new_action = environment.TimeAction(_type = new_action_type, _values = new_action_values)
                sub_list.append(new_action)
                list_count +=1 

                if self.DEBUG_OPERATION_OUTPUT :
                    print("origin: ", region.name + '\\\\' + node_aux.name, ", target: ", region.name + '\\\\' + node_aux.name, ", quantity: ", new_action_values['quantity'])

        if self.DEBUG_OPERATION_OUTPUT :
            print("########## END CONVERGE_POPULATION")
            print('\n\n\n')
        return sub_list

    