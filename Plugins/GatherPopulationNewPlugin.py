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
        
        self.set_pair('gather_population', self.converge_population)
        self.distance_map = {}
        self.weights_map = {}


    def update_time_step(self, cycle_step, simulation_step):
        return #super().update_time_step(cycle_step, simulation_step)

    def get_distance(self, name1, name2, pos1, pos2):
        if name1 + name2 is self.distance_map:
            return self.distance_map[name1 + name2]
        
        if name2 + name1 is self.distance_map:
            return self.distance_map[name2 + name1]
        
        self.distance_map[name1+name2] = util.distance2D(pos1, pos2)
        return self.distance_map[name1+name2]

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

    def compute_weights(self, target_region, regions):
        if target_region.name in self.weights_map:
            return self.weights_map[target_region.name]
        
        distance_list = []

        for region in self.graph.region_list:
            current_region_dist = 200
            
            if region.id != target_region.id:
                current_region_dist = self.get_distance(region.name, target_region.name, region.position, target_region.position)

            for node_aux in region.node_list:
                distance_list.append((node_aux, current_region_dist))
                   
        total_dist = sum([ (1/d) for (n, d) in distance_list])
        weight_list = [(n,  ( (1/d) / total_dist)) for (n, d) in distance_list]
        self.weights_map[target_region.name] = weight_list

        return self.weights_map[target_region.name]
    
    ## Complex time action. Will be broken up into smaller actions
    def converge_population(self, values, hour, time):
        #print(values)
        assert 'region' in values, "region is not defined in Gather Population TimeAction"
        assert 'node' in values, "node is not defined in Gather Population TimeAction"
        
        target_region = self.graph.get_region_by_name(values['region'])
        target_node = target_region.get_node_by_name(values['node'])
            
        if self.DEBUG_OPERATION_OUTPUT and target_node.containing_region_name in self.DEBUG_OPERATION_REGIONS:
            print("########## CONVERGE_POPULATION")
            print('converge Values: \n', values)
            
        sub_list = [] 
        quantity = values['quantity']
        pop_template = PopTemplate()
        if 'population_template' in values:
            pop_template = values['population_template']
        
        weight_list = self.compute_weights(target_region, self.graph.region_list)
        #filtering undesired nodes
        weight_list = [(n, w) for (n,w) in weight_list if (n.get_population_size(pop_template) > 0)]
        if 'only_locals' in values and values['only_locals'] == "true":
            weight_list = [(n, w) for (n,w) in weight_list if (n.containing_region_name == target_node.containing_region_name)]
        if 'different_node_name' in values and bool(values['different_node_name']):
            weight_list = [(n, w) for (n,w) in weight_list if (n.name != target_node.name)]
        
        available_pop = [node.get_population_size(pop_template) for (node,w) in weight_list]
        if sum(available_pop) < quantity:
            quantity = sum(available_pop)
            
        if quantity == 0:
            return sub_list
        int_weights = util.distribute_ints_from_weights_with_limit(quantity, [w for (n, w) in weight_list],available_pop)
        
        total_weight = sum([w for (n, w) in weight_list])
        #node_targets = [(n, w / total_weight) for (n, w) in weight_list]
        node_targets = [(weight_list[i][0], weight_list[i][1] / total_weight,int_weights[i]) for  i in range(len(int_weights))]
        
        list_count = 0
        total_quant = 0
        remainder = 0.0
        
        for node_aux, w, i in node_targets:
            
            region = self.graph.get_region_by_name(node_aux.containing_region_name)
            isolation_factor = self.isolation_rate
            new_action_values = {}
            
            new_action_type = 'move_population'
            new_action_values['origin_region'] = region.name
            new_action_values['origin_node'] = node_aux.name
            new_action_values['destination_region'] = target_region.name
            new_action_values['destination_node'] = target_node.name
           
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

            temp = pop_template

            if self.locals_only:
                temp = copy.deepcopy(pop_template)
                temp.mother_blob_id = target_region.id

            new_action_values['population_template'] = temp
            total_quant += new_action_values['quantity']
            new_action = environment.TimeAction(_type = new_action_type, _values = new_action_values)
            #print(new_action_values)
            
            #sub_list.append(new_action)
            self.graph.direct_action_invoke(new_action, hour, time)
            #list_count +=1 

        if self.DEBUG_ALL_REQUESTS or target_region.name in self.DEBUG_REGIONS:
            print(f'To {target_region.name}\tReq: {quantity} Sent: {total_quant}')
        return sub_list
    