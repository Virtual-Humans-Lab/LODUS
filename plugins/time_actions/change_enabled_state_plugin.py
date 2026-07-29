from core.simulator import LodusSimulation
from core.plugin import ActionPlugin
import time

class ChangeEnabledStatePlugin(ActionPlugin):
    """Plugin to change the enabled state of nodes in the environment graph."""
    def __init__(self):
        super().__init__()

    def load_plugin(self, simulation: LodusSimulation):
        self.simulation = simulation
        self.env_graph = simulation.env_graph
        simulation.add_action_type_to_function('set_node_enabled', self.set_node_enabled, True)
        simulation.add_action_type_to_function('set_nodes_enabled_by_type', self.set_nodes_enabled_by_type, True)

    def update_time_step(self, cycle_step, simulation_step):
        return super().update_time_step(cycle_step, simulation_step)

    def unload_plugin(self):
        return super().unload_plugin()

    def set_node_enabled(self, pop_template ,values, cycle_step, simulation_step):
        """ Set node enabled state. Base Operation. """
        assert 'enabled' in values, "Missing 'enabled' in values"
        execute_once = (
            values.get("execution_scope") == "once"
            or (
                "node_complete_name" in values
                and "region" not in values
                and "node_unique_name" not in values
            )
        )
        if not execute_once:
            assert 'region' in values, "Missing 'region' in values"
            assert 'node_unique_name' in values, "Missing 'node_unique_name' in values"
            expected_name = (
                f"{values['region']}//{values['node_unique_name']}"
            )
            if (
                "node_complete_name" in values
                and values["node_complete_name"] != expected_name
            ):
                return  # Skip if the node_complete_name does not match the expected format
        
        start_time = time.perf_counter()
        
        node_complete_name = values.get("node_complete_name")
        if node_complete_name is None:
            node_complete_name = (
                f"{values['region']}//{values['node_unique_name']}"
            )
        target_node = self.env_graph.get_node_by_complete_name(node_complete_name)
        enabled_state = values['enabled']
        cascade = values.get('cascade_reenable', False)
        cause = values.get("cause", "off_cycle")


        self.env_graph.set_node_enabled(
            target_node.get_complete_name(),
            enabled=enabled_state,
            cascade_reenable=cascade,
            cause=cause,
            simulation_step=simulation_step,
            cycle_step=cycle_step,
        )
        self.add_execution_time('set_node_enabled', time.perf_counter() - start_time)

    def set_nodes_enabled_by_type(self, pop_template ,values, cycle_step, simulation_step):
        """ Set the enabled state of nodes by type. Base Operation. """
        assert 'enabled' in values, "Missing 'enabled' in values"
        assert 'node_type' in values, "Missing 'node_type' in values"
        
        start_time = time.perf_counter()

        node_type = values['node_type']
        if not isinstance(node_type, list):
            node_type = [node_type]

        target_regions = values.get('target_regions', None)
        enabled_state = values['enabled']
        cascade = values.get('cascade_reenable', False)
        cause = values.get("cause", "off_cycle")

        for node_type_name in node_type:
            nodes = self.env_graph.get_nodes_by_type(node_type_name)

            for node in nodes:
                if target_regions and node.containing_region_name not in target_regions:
                    continue  # Skip nodes not in the target regions

                self.env_graph.set_node_enabled(node.get_complete_name(), 
                                                enabled=enabled_state,
                                                cascade_reenable=cascade,
                                                cause=cause,
                                                simulation_step=simulation_step,
                                                cycle_step=cycle_step)

        self.add_execution_time('set_nodes_enabled_by_type', time.perf_counter() - start_time)
