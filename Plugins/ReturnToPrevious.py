import sys
sys.path.append('../')

import environment
from population import PopTemplate
import copy
from random_inst import FixedRandom
import math
import csv
import util

class ReturnToPreviousPlugin(environment.TimeActionPlugin):

    def __init__(self, env_graph: environment.EnvironmentGraph):
        super().__init__()

        self.graph = env_graph
        self.set_pair('return_to_previous', self.return_to_previous)

    def return_to_previous(self, values, hour, time):
        
        node_id = values['node_id']
        blob_id = values['blob_id']
        target_blob = None
        #print("node", node_id, "blob", blob_id)
        current_node = self.graph.get_node_by_id(node_id)
        for x in current_node.contained_blobs:
            if x.blob_id == blob_id:
                target_blob = x
        
        pop_template = values["population_template"]
        target_node = self.graph.get_node_by_id(target_blob.previous_node)
        #print("number ob blobs:", len(target_node.contained_blobs))
        #grabbed = current_node.grab_population(100000, PopTemplate())
        
        grabbed = target_blob.grab_population(target_blob.get_population_size(pop_template), pop_template)
        #print ("available pop:", target_blob.get_population_size(pop_template), "grabbed:", grabbed.get_population_size(pop_template))
        
        grabbed.previous_node = current_node.id
        if grabbed.spawning_node is None:
            grabbed.spawning_node = current_node.id
            grabbed.frame_origin_node = current_node.id
        
        # if current_node.containing_region_name == "Azenha" and current_node.name == "pharmacy":
        #     print(f'wants to go from {current_node.containing_region_name}-{current_node.name} to {target_node.containing_region_name}-{target_node.name}')
        #     print(f'before {target_blob.get_population_size()}') 
        #     print(f'after{grabbed.get_population_size()}',target_blob.get_population_size(values["population_template"]))
        
        
        target_node.add_blob(grabbed)
        current_node.remove_blob(grabbed)
        
        
        
        
        #print(target_blob.previous_node, "------")
        
        return []
        #target_blob = self.graph.
        region = values['region']
        if isinstance(region, str):
            region = self.graph.get_region_by_name(region)

        node = values['node']
        if isinstance(node, str):
            node = region.get_node_by_name(node)

        pop_template = values['population_template']

        new_action_values = {}
        new_action_type = 'move_population'
        new_action_values['origin_region'] = region.name
        new_action_values['origin_node'] = node.name
        new_action_values['destination_region'] = region.name
        new_action_values['destination_node'] = 'home'
        
        new_action_values['quantity'] = 100
        new_action_values['population_template'] = pop_template

        action = environment.TimeAction(_type = new_action_type, _values = new_action_values)
        
        return [action]
        