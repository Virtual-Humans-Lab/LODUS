import sys
sys.path.append('../')

import environment 
from population import PopTemplate
import copy
import random
from random_inst import FixedRandom
import math
import numpy as np
import util

class ReverseSocialIsolationPlugin(environment.TimeActionPlugin):

    def __init__(self, env_graph,  isolation_table_path = '', isolation_rate = 0.0, to_total_ratio_correction = 0.0, locals_only = False):
        '''gather_population
            Pushes population to nearby nodes into a requesting node.
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
                        changes movement quantities following an isolation table.
                    'quantity_correction'
                        same as 'regular' but
                        corrects to assume the operation requested x% of the population, but wanted the entire population.
                    'random_nudge' 
                        fixed isolation rate with a random nudge to the isolation rate
        '''
        super().__init__()
        self.day_cycle = 24
        self.graph = env_graph
    
        self.iso_mode = 'regular'
        self.isolation_rate = isolation_rate
        self.locals_only = locals_only
        self.to_total_ratio_correction = to_total_ratio_correction

        self.blob_ratio = 1.0

        self.region_isolation_per_day = None

        self.DEBUG_OPERATION_OUTPUT = False
        if isolation_table_path != '':
            self.load_table(isolation_table_path)
        #self.graph.remove_action('gather_population')
        self.set_pair('push_population', self.reverse_gather_population_with_isolation)

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

        for x in range(len(self.graph.region_list)):
            region = self.graph.region_list[x]
            current_region_dist = 200
            if region.id != target_region.id:
                current_region_dist = self.get_distance(region.name, target_region.name, region.position, target_region.position)

            for node_aux in region.node_list:
                distance_list.append((node_aux, current_region_dist))
                   
        # negatives to give closest places the largest weights
        total_dist = sum([ (1/d) for (n, d) in distance_list])

        weight_list = [(n,  ( (1/d) / total_dist)) for (n, d) in distance_list]

        self.weights_map[target_region.name] = weight_list

        return self.weights_map[target_region.name]

    def load_table(self, table_path):
        f = open(table_path, 'r', encoding='utf-8')
        self.region_isolation_per_day = {}
        lines = f.readlines()

        for line in lines[1:]:
            region_list = []
            data  = line.split(';')

            region = data[0]
            for day_value in data[1:]:
                try:
                    v = float(day_value)
                except Exception:
                    pass
                else:
                    region_list.append(float(day_value))

            self.region_isolation_per_day[region]  = region_list


    def reverse_gather_population_with_isolation(self, values, hour, time):

        origin_region = values['origin_region']
        if isinstance(origin_region, str):
            origin_region = self.graph.get_region_by_name(origin_region)

        origin_node = values['origin_node']
        if isinstance(origin_node, str):
            origin_node = origin_region.get_node_by_name(origin_node)

        destination_node_name = values['destination_node']
        #if isinstance(destination_node, str):
        #    destination_node = origin_region.get_node_by_name(destination_node)

        quantity = values['quantity']
        if origin_region.name == "Centro" and self.DEBUG_OPERATION_OUTPUT:
            print(f'{quantity}\n')
        pop_template = values['population_template']

        av = origin_node.get_population_size(pop_template)
        if quantity > av:
            quantity = av
            
        sub_list = []

        node_targets = []
        for region in  self.graph.region_list:
            for node in region.node_list:
                node_targets.append(node)

        weight_list = self.compute_weights(origin_region, self.graph.region_list)

        weight_list = [(n, w) for (n,w) in weight_list if n.name == destination_node_name]
        
        total_weight = sum([w for (n, w) in weight_list])

        node_targets = [(n, w / total_weight) for (n, w) in weight_list]


        list_count = 0
        total_quant = 0
        for node_aux, w in node_targets:
            region = self.graph.get_region_by_name(node_aux.containing_region_name)

            if self.region_isolation_per_day is not None:
                isolation_factor = self.region_isolation_per_day[origin_region.name][time // self.day_cycle]
            else:
                isolation_factor = self.isolation_rate

            new_action_values = {}
            new_action_type = 'move_population'
            
            new_action_values['origin_region'] = origin_region.name

            # TODO placeholder 
            new_action_values['origin_node'] = origin_node.name
            new_action_values['destination_region'] = region.name

            # TODO placeholder 
            new_action_values['destination_node'] = node_aux.name


            ### regular iso factor
            if self.iso_mode == 'regular':
                new_action_values['quantity'] = int(quantity * w *  (1 - isolation_factor))
            elif self.iso_mode == 'quantity_correction':
                iso_factor = (1 - isolation_factor) / (1 - self.to_total_ratio_correction) 
                new_action_values['quantity'] = quantity * w * iso_factor
            elif self.iso_mode == 'random_nudge':
                #iso_factor = ( 1 - (self.isolation_rate + (random.random() * 0.05  - 0.025))) / (1 - self.to_total_ratio_correction) 
                iso_factor = ( 1 - (self.isolation_rate + (FixedRandom.instance.random() * 0.05  - 0.025))) / (1 - self.to_total_ratio_correction) 
                new_action_values['quantity'] = quantity * w * iso_factor

            #print(quantity, new_action_values['quantity'])
            temp = pop_template

            if self.locals_only:
                temp = copy.deepcopy(pop_template)
                temp.mother_blob_id = origin_region.id

            new_action_values['population_template'] = temp
            total_quant += new_action_values['quantity']
            new_action = environment.TimeAction(_type = new_action_type, _values = new_action_values)
            sub_list.append(new_action)
            list_count +=1 

        if origin_region.name == "Centro" and self.DEBUG_OPERATION_OUTPUT:
            print(f'{total_quant}\n')

        return sub_list

    