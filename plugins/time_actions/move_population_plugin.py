import sys

from core.simulator import LodusSimulation
sys.path.append('../')

from core.plugin import ActionPlugin
import time

class MovePopulationPlugin(ActionPlugin):
    
    def __init__(self):
        super().__init__()

    def load_plugin(self, simulation: LodusSimulation):
        self.simulation = simulation
        self.env_graph = simulation.env_graph
        simulation.add_action_type_to_function('move_population', self.move_population, True)

    def update_time_step(self, cycle_step, simulation_step):
        return super().update_time_step(cycle_step, simulation_step)
    
    def setup_logger(self):
        return super().setup_logger()

    def log_simulation_step(self, logger):
        return super().log_simulation_step(logger)
    
    def stop_logger(self, logger):
        return super().stop_logger(logger)
    
    def unload_plugin(self):
        return super().unload_plugin()

    ## Pre-condition: assumes move population operation is valid
    def move_population(self, pop_template ,values, cycle_step, simulation_step):
        """ Move population. Base Operation.
            Grabs population according to a population template. and moves between nodes.
            quantity -1 moves every person matching template.
        """
        start_time = time.perf_counter()
        quantity = values['quantity']
        if quantity == 0:
            self.add_execution_time('move_population_quantity_0', time.perf_counter() - start_time)
            return
        
        origin_region = self.env_graph.get_region_by_name(values['origin_region'])
        origin_node = origin_region.get_first_node_with_name(values['origin_node'])
        destination_region = self.env_graph.get_region_by_name(values['destination_region'])
        destination_node = destination_region.get_first_node_with_name(values['destination_node'])

        if quantity == -1:
            quantity = origin_node.get_population_size(pop_template)
        
        # available_total = origin_node.get_population_size()
        # available = origin_node.get_population_size(pop_template)
        # print(destination_node)
            
        grabbed_population = origin_node.grab_population(quantity, pop_template)     
        for grab_pop in grabbed_population:
            #if grab_pop.previous_node != origin_node.id:
            #    grab_pop.previous_node = origin_node.id
            grab_pop.frame_origin_node = origin_node.id
        
        self.env_graph.log_blob_movement(origin_node, destination_node, grabbed_population)
        destination_node.add_blobs(grabbed_population)
        self.add_execution_time('move_population', time.perf_counter() - start_time)