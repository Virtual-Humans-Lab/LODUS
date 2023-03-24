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

class MovePopulationPlugin(environment.TimeActionPlugin):
    
    def __init__(self, env_graph: environment.EnvironmentGraph):
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
        self.set_pair('move_population', self.move_population)
        self.graph.base_actions.add('move_population')

    def update_time_step(self, cycle_step, simulation_step):
        return

    ## Pre-condition: assumes move population operation is valid
    def move_population(self, pop_template ,values, cycle_step, simulation_step):
        """ Move population. Base Operation.
            Grabs population according to a population template. and moves between nodes.
            quantity -1 moves every person matching template.
        """
        start_time = time.perf_counter()

        quantity = values['quantity']
        if quantity == 0:
            self.execution_times.append(time.perf_counter() - start_time)
            return
        
        origin_region = self.graph.get_region_by_name(values['origin_region'])
        origin_node = origin_region.get_node_by_name(values['origin_node'])
        destination_region = self.graph.get_region_by_name(values['destination_region'])
        destination_node = destination_region.get_node_by_name(values['destination_node'])

        if quantity == -1:
            quantity = origin_node.get_population_size(pop_template)
        
        # available_total = origin_node.get_population_size()
        # available = origin_node.get_population_size(pop_template)
        
        grabbed_population = origin_node.grab_population(quantity, pop_template)     
        for grab_pop in grabbed_population:
            #if grab_pop.previous_node != origin_node.id:
            #    grab_pop.previous_node = origin_node.id
            grab_pop.frame_origin_node = origin_node.id
        
        self.graph.log_blob_movement(origin_node, destination_node, grabbed_population)
        destination_node.add_blobs(grabbed_population)
        self.execution_times.append(time.perf_counter() - start_time)