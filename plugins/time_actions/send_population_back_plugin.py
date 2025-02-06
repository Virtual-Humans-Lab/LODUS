import copy
import sys
import time

from core.routine import Action
from core.simulator import LodusSimulation
sys.path.append('../')

from core.environment import EnvironmentGraph
from core.plugin import ActionPlugin

class SendPopulationBackPlugin(ActionPlugin):

    def __init__(self):
        '''
        Plugin that consumes a 'send_population_back' TimeAction type.
        Complex TimeAction that returns multiple 'move_population' actions.

        Requirements:

        Plugin Parameters: (default values can be overriden by the experiment configuration):
            This plugin doesn't have default parameters

        'send_population_back' Parameters:
            region (str): acting_region (origin of population movement).
            node (str): acting_node (origin of population movement).
            population_template: PopTemplate to be matched by the operation (population moved).
            quantity (int): population quantity to be moved. Either 'quantity' or 'percentage' should be defined.
            percentage (float): population percentage to be moved.  Either 'quantity' or 'percentage' should be defined.
        '''
        super().__init__()

    def load_plugin(self, simulation: LodusSimulation):    
        self.env_graph = simulation.env_graph
        simulation.add_action_type_to_function('send_population_back', self.send_population_back, False)

        if "send_population_back_plugin" not in simulation.experiment_config:
            print("Experiment config should have a 'send_population_back' key.")

        # Performance log for quantity of sub-actions
        self.sublist_count = []

    def setup_logger(self, logger):
        return super().setup_logger(logger)
    
    def update_time_step(self, cycle_step, simulation_step):
        return super().update_time_step(cycle_step, simulation_step)
    
    def log_simulation_step(self, logger):
        return super().log_simulation_step(logger)
    
    def stop_logger(self, logger):
        return super().stop_logger(logger)
    
    def unload_plugin(self):
        return super().unload_plugin()
    
    def send_population_back(self, pop_template, values:dict, cycle_step:int, sim_step:int):
        '''Function to consume a 'send_population_back' TimeAction type.'''
        start_time = time.perf_counter()
        
        assert 'region' in values, "region is not defined in Send Population Back TimeAction"
        assert 'node' in values, "node is not defined in Send Population Back TimeAction"
        assert 'quantity' in values or 'percentage' in values, "quantity or percentage is not defined in Send Population Back TimeAction"
        
        acting_region = self.env_graph.get_region_by_name(values['region'])
        acting_node = acting_region.get_first_node_with_name(values['node'])

        sub_list = []
        for b in acting_node.contained_blobs:
            destination_node = self.env_graph.get_node_by_id(b.node_of_origin)
            destination_region = self.env_graph.get_region_by_name(destination_node.containing_region_name)
           
            if destination_node.get_complete_name() == acting_node.get_complete_name():
                continue
            
            temp = copy.deepcopy(pop_template)
            temp.set_mother_blob_id(destination_region.id)

            # Calculates the population to be moved based on 
            total_population = b.get_population_size(temp)
            if 'quantity' in values:
                quant = values['quantity']
            else: # assumes 'percentage' is in values from assert
                quant = int(total_population * values['percentage'])

            # Creates a 'move_population' TimeAction
            new_action_type = 'move_population'
            new_action_values = {'origin_region': acting_region.name,
                                 'origin_node': acting_node.unique_name,
                                 'destination_region': destination_region.name,
                                 'destination_node': destination_node.unique_name,
                                 'quantity': quant}
            new_action = Action(action_type = new_action_type, 
                                                pop_template = temp,
                                                values = new_action_values)
            sub_list.append(new_action)
        
        self.add_execution_time('send_population_back',time.perf_counter() - start_time)
        self.sublist_count.append(len(sub_list))
        return sub_list
    
    def print_execution_time_data(self):
        out = super().print_execution_time_data()
        out += "---Total subactions count:" + str(sum(self.sublist_count)) + "\n"
        if len(self.sublist_count) > 0:
            out += "---Average subaction count:" + str(sum(self.sublist_count)/len(self.sublist_count)) + "\n"
        return out