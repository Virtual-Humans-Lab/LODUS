import copy
import sys
import time
sys.path.append('../')

import environment 
from population import PopTemplate

class SendPopulationBackPlugin(environment.TimeActionPlugin):

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
        self.set_pair('send_population_back', self.send_population_back)

    def update_time_step(self, cycle_step, simulation_step):
        return #super().update_time_step(cycle_step, simulation_step)
    
    def send_population_back(self, pop_template, values:dict, cycle_step:int, sim_step:int):
        start_time = time.perf_counter()
        
        assert 'region' in values, "region is not defined in Send Population Back TimeAction"
        assert 'node' in values, "node is not defined in Send Population Back TimeAction"
        assert 'quantity' in values or 'percentage' in values, "quantity or percentage is not defined in Send Population Back TimeAction"
        
        acting_region = self.graph.get_region_by_name(values['region'])
        acting_node = acting_region.get_node_by_name(values['node'])

        sub_list = []
        for b in acting_node.contained_blobs:
            #pop_template = PopTemplate()
            #if 'population_template' in values:
            #    pop_template = values['population_template']
            
            


            new_action_values = {}
            new_action_type = 'move_population'
            
            new_action_values['origin_region'] = acting_region.name
            new_action_values['origin_node'] = acting_node.name
            
            node_of_origin = self.graph.get_node_by_id(b.node_of_origin)
            region_of_origin = self.graph.get_region_by_name(node_of_origin.containing_region_name)
           
            if node_of_origin.get_unique_name() == acting_node.get_unique_name():
                # print("Avoid shit", node_of_origin.get_unique_name())
                continue
            
            new_action_values['destination_region'] = region_of_origin.name
            new_action_values['destination_node'] = node_of_origin.name
            
            temp = copy.deepcopy(pop_template)
            total_population = b.get_population_size(temp)
            if 'quantity' in values:
                quant = values['quantity']
            else:
                quant = int(total_population * values['percentage'])

            new_action_values['quantity'] = quant
            temp.set_mother_blob_id(region_of_origin.id)
            new_action_values['population_template'] = pop_template
            #print(new_action_values)
            new_action = environment.TimeAction(action_type = new_action_type, 
                                                pop_template = temp,
                                                values = new_action_values)
            sub_list.append(new_action)
        
        self.add_execution_time(time.perf_counter() - start_time)
        return sub_list