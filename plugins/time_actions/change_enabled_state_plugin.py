import sys

from core.environment import EnvRegion
from core.simulator import LodusSimulation
sys.path.append('../')

from core.plugin import ActionPlugin
import time

class ChangeEnabledStatePlugin(ActionPlugin):
    
    def __init__(self):
        super().__init__()

    def load_plugin(self, simulation: LodusSimulation):
        self.simulation = simulation
        self.env_graph = simulation.env_graph
        simulation.add_action_type_to_function('change_node_enabled_state', self.change_node_enabled_state, True)

    def update_time_step(self, cycle_step, simulation_step):
        return super().update_time_step(cycle_step, simulation_step)

    def unload_plugin(self):
        return super().unload_plugin()

    def change_node_enabled_state(self, pop_template ,values, cycle_step, simulation_step):
        """ Change node enabled state. Base Operation. """
        assert 'enabled' in values, "Missing 'enabled' in values"
        assert 'node_complete_name' in values, "Missing 'node_complete_name' in values"
        
        start_time = time.perf_counter()
        
        target_node = self.env_graph.get_node_by_complete_name(values['node_complete_name'])
        enabled_state = values['enabled']
        cascade = values.get('cascade_reenable', False)


        self.env_graph.change_node_enabled_state(target_node.get_complete_name(), enabled=enabled_state, cascade_reenable=cascade)
        self.add_execution_time('change_node_enabled_state', time.perf_counter() - start_time)