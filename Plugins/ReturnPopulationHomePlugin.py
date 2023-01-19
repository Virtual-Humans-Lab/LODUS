import copy
import sys
import time
from types import new_class
sys.path.append('../')

import environment 
from population import PopTemplate

class ReturnPopulationHomePlugin(environment.TimeActionPlugin):

    def __init__(self, env_graph: environment.EnvironmentGraph):
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

        self.graph = env_graph
        self.set_pair('return_population_home', self.return_population_home)

    def update_time_step(self, cycle_step, simulation_step):
        return #super().update_time_step(cycle_step, simulation_step)

        ## returns everyone home
    def return_population_home(self, pop_template, values, cycle_step, simulation_step):
        start_time = time.perf_counter()
        # print(values)
        target_region = values['region']
        if isinstance(target_region, str):
            target_region = self.graph.get_region_by_name(target_region)

        node = values['node']
        if isinstance(node, str):
            node = target_region.get_node_by_name(node)
        
        #pop_template = PopTemplate()
        #if 'population_template' in values:
        #    pop_template = values['population_template']

        sub_list = []
        
        for region in self.graph.region_list:
            for origin_node in region.node_list:
                if node.id != origin_node.id:
                    new_action_values = {}
                    new_action_type = 'move_population'
                    
                    new_action_values['origin_region'] = region.name

                    # TODO placeholder 
                    new_action_values['origin_node'] = origin_node.name
                    new_action_values['destination_region'] = target_region.name

                    # TODO placeholder 
                    new_action_values['destination_node'] = node.name
                    
                    new_action_values['quantity'] = -1
                    pop_template.set_mother_blob_id(target_region.id)

                    new_action = environment.TimeAction(action_type = new_action_type, 
                                                        pop_template = pop_template,
                                                        values = new_action_values)
                    sub_list.append(new_action)
        self.add_execution_time(time.perf_counter() - start_time)
        return sub_list
