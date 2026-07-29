
from __future__ import annotations
import enum
from typing import Callable
from core.environment import EnvNode, EnvironmentGraph
from core.plugin import ActionPlugin, BasePlugin, RoutinePlugin, LoggerPlugin
from core.population import CharacteristicsFactory
from core.routine import Action, GlobalAction, GlobalActionExecutionScope
from util.simulation_time import SimulationTimeStatus

class RoutineController:
    def __init__(self, lodus_simulation: LodusSimulation):
        self.simulator = lodus_simulation
        self.env_graph = lodus_simulation.env_graph
        self.plugin_controller = lodus_simulation.plugin_controller
        
        self.base_action_types = set()
        self.action_type_to_function:dict[str, Callable] = { }

        self.action_list = []
        self.queued_actions_first: list[Action] = []
        self.queued_actions_last: list[Action] = []
        self.global_actions: list[GlobalAction] = []

    def add_action_type_to_function(self, action_type: str, function: Callable, is_base_action: bool):
        """Adds an action type to the function mapping."""
        if not callable(function):
            raise ValueError(f"function must be a callable, is {type(function)}")
        if not isinstance(action_type, str):
            raise ValueError(f"action_type must be of type str, is {type(action_type)}")
        self.action_type_to_function[action_type] = function
        if is_base_action:
            self.base_action_types.add(action_type)
        
    def remove_action_type_to_function(self, action_type: str):
        """Removes an action type from the function mapping."""
        self.action_type_to_function.pop(action_type)
        if action_type in self.base_action_types:
            self.base_action_types.remove(action_type)

    def queue_action_to_next_cycle_step(self, action: Action, start_of_frame: bool =True):
        """Queues an action to be executed in the"""
        if not isinstance(action, Action):
            raise ValueError("action must be of type Action")
        if start_of_frame:
            self.queued_actions_first.append(action)
        else:
            self.queued_actions_last.append(action)

    def add_global_action(self, global_action: GlobalAction):
        """Adds a GlobalAction to the list of repeating global actions."""
        if not isinstance(global_action, GlobalAction):
            raise ValueError("global_action must be of type GlobalAction")
        self.global_actions.append(global_action)

    def generate_action_list(self, cycle_step: int, simulation_step: int) -> list[Action]:
        """Generates a list of actions to be executed in the current cycle_step/simulation_step."""
        return (
            self.generate_start_of_step_action_list(
                cycle_step, simulation_step
            )
            + self.generate_regular_action_list(cycle_step)
            + self.generate_end_of_step_action_list(
                cycle_step, simulation_step
            )
        )

    def generate_start_of_step_action_list(
        self, cycle_step: int, simulation_step: int
    ) -> list[Action]:
        """Actions that must take effect before ActionPlugin updates."""
        return (
            self.process_queued_actions(True)
            + self.process_routine_plugins_global_actions(cycle_step, True)
            + self.process_routine_plugins_actions(
                cycle_step, simulation_step, True
            )
        )

    def generate_regular_action_list(self, cycle_step: int) -> list[Action]:
        return (
            self.process_repeating_global_actions(
                self.global_actions, cycle_step
            )
            + self.process_routines(cycle_step)
        )

    def generate_end_of_step_action_list(
        self, cycle_step: int, simulation_step: int
    ) -> list[Action]:
        """Actions that take effect after ActionPlugin updates."""
        return (
            self.process_routine_plugins_actions(
                cycle_step, simulation_step, False
            )
            + self.process_routine_plugins_global_actions(cycle_step, False)
            + self.process_queued_actions(False)
        )

    def process_routines(self, cycle_step: int):
        return [action for region in self.env_graph.region_list for action in region.generate_action_list(cycle_step)]

    def process_queued_actions(self, at_cycle_step_start: bool) ->list[Action]:
        """Processes the queued actions and clears the queue."""
        action_list = self.queued_actions_first if at_cycle_step_start else self.queued_actions_last
        action_list_copy = action_list.copy()
        action_list.clear()
        return action_list_copy

    def process_routine_plugins_actions(self, cycle_step: int, simulation_step: int, at_cycle_step_start: bool) -> list[Action]:
        """Processes the actions of all loaded RoutinePlugins."""
        actions: list[Action] = []
        if at_cycle_step_start:
            for rp in self.plugin_controller.loaded_routine_plugins:
                actions.extend(rp.process_start_of_step_actions(cycle_step=cycle_step, simulation_step=simulation_step))
        else:
            for rp in self.plugin_controller.loaded_routine_plugins:
                actions.extend(rp.process_end_of_step_actions(cycle_step=cycle_step, simulation_step=simulation_step))
        return actions
    
    def process_routine_plugins_global_actions(self, cycle_step: int, at_cycle_step_start: bool) -> list[Action]:
        """Processes the global actions of all loaded RoutinePlugins."""
        actions: list[Action] = []
        if at_cycle_step_start:
            for rp in self.plugin_controller.loaded_routine_plugins:
                actions.extend(self.process_repeating_global_actions(rp.start_of_step_global_actions, cycle_step))
        else:
            for rp in self.plugin_controller.loaded_routine_plugins:
                actions.extend(self.process_repeating_global_actions(rp.end_of_step_global_actions, cycle_step))
        return actions
    
    def process_repeating_global_actions(self, global_action_list: list[GlobalAction], cycle_step: int) -> list[Action]:
        """Processes GlobalActions"""
        action_list = []
        for global_action in global_action_list:
            if not global_action.should_process_action(cycle_step):
                continue

            if global_action.execution_scope == GlobalActionExecutionScope.ONCE:
                action = self._copy_scheduled_global_action(global_action)
                action_list.append(action)
                continue

            for region in self.env_graph.region_list:
                for node in region.node_list:
                    if not self.is_node_matching(node, global_action):
                        continue
                    action = self._copy_scheduled_global_action(global_action)
                    action.values['region'] = region.name
                    action.values['node_type'] = node.node_type
                    action.values['node_unique_name'] = node.unique_name
                    action.values['node_id'] = node.id
                    action_list += [action]
        return action_list

    def _copy_scheduled_global_action(self, global_action: GlobalAction) -> Action:
        action = Action(
            global_action.action_type,
            global_action.pop_template.copy(),
            global_action.values.copy(),
        )
        if isinstance(global_action.cycle_step_definition, list):
            action.values['frames'] = global_action.cycle_step_definition.copy()
        else:
            action.values['cycle_length'] = global_action.cycle_step_definition
        return action

    def is_node_matching(self, node: EnvNode, global_action: GlobalAction):
        if 'node_name' in global_action.values and node.node_type != global_action.values['node_name']:
            return False
        if 'node_type' in global_action.values and node.node_type not in global_action.values['node_type']:
            return False
        return True
    
    def simplify_action_list(self, action_list:list[Action], cycle_step: int, simulation_step: int) -> list[Action]:
        """Simplifies the action list by consuming all complex Actions."""
        while not all([x.action_type in self.base_action_types for x in action_list]):
            print("Simulation Step", simulation_step, "Current action list length:", len(action_list), end='\r')
            i  = action_list.pop(0)
            if i.action_type not in self.base_action_types:
                if i.action_type not in self.action_type_to_function:
                    exit(f"ERROR: TimeAction type {i.action_type} cannot be consumed. Please check if correct plugins are loaded.")
                sub_list = self.action_type_to_function[i.action_type](i.pop_template, i.values, cycle_step, simulation_step)
                action_list += sub_list
            else:
                action_list += [i]
        return action_list
    
    # def balance_action_list(self, action_list):
    #     ## corrects the quantities of agents flow to and from each region
    #     ## TODO not implemented yet
    #     ##print('EnvironmentGraph.balance_action_list not implemented yet')
    #     # TODO probably wrong because of templates
    #     totals = {}
    #     # accumulate totals
    #     for action in action_list:
    #         og_node = action['origin_node']
    #         pop_temp = action['population_template']
    #         node_pop = og_node.get_population_size(pop_temp)
    #         quantity = action['quantity']
    #         interpreted_quantity = max(-1, min(quantity, node_pop))
    #         totals[og_node] += interpreted_quantity
    #     # correct quantities     
    #     for action in action_list:
    #         og_node = action['origin_node']
    #         node_pop = og_node.get_population_size(pop_temp)
    #         quantity = action['quantity']

    #         action['quantity']  = int((quantity / totals[og_node]) * min(node_pop,  totals[og_node]))

    #     return action_list
    
    def consume_action(self, action:Action, hour: int, time: int):
        """Consumes an Action, applying it to the EnvironmentGraph."""
        action_type = action.action_type
        pop_template = action.pop_template
        values = action.values
        
        if action_type in self.base_action_types:
            self.action_type_to_function[action_type](pop_template, values, hour, time)
        else:
            simplified_actions = self.action_type_to_function[action_type](pop_template, values, hour, time)
            for action in simplified_actions:
                self.consume_action(action, hour, time)
    
class PluginType(enum.Enum):
    ACTION = 0,
    LOGGER = 1,
    ROUTINE = 2

class PluginController:
    def __init__(self, lodus_simulation: LodusSimulation):
        self.simulator = lodus_simulation
        self.env_graph = lodus_simulation.env_graph

        self.loaded_action_plugins: list[ActionPlugin] = []
        self.loaded_logger_plugins: list[LoggerPlugin] = []
        self.loaded_routine_plugins: list[RoutinePlugin] = []
        self.loaded_plugins: list[BasePlugin] = []

    def load_plugin(self, plugin: BasePlugin):
        """Loads a Plugin into the PluginController."""
        if plugin in self.loaded_plugins:
            raise ValueError("Plugin is already loaded")
        
        if isinstance(plugin, ActionPlugin):
            self.load_action_plugin(plugin)
        elif isinstance(plugin, LoggerPlugin):
            self.load_logger_plugin(plugin)
        elif isinstance(plugin, RoutinePlugin):
            self.load_routine_plugin(plugin)
        else:
            raise ValueError("Plugin must be of type ActionPlugin, LoggerPlugin or RoutinePlugin")
        self.loaded_plugins.append(plugin)

    def load_action_plugin(self, plugin:ActionPlugin):
        """Loads an ActionPlugin into the PluginController."""
        self.loaded_action_plugins.append(plugin)
        plugin.load_plugin(self.simulator)

    def load_logger_plugin(self, plugin:LoggerPlugin):
        """Loads a LoggerPlugin into the PluginController."""
        self.loaded_logger_plugins.append(plugin)
        plugin.load_plugin(self.simulator)

    def load_routine_plugin(self, plugin:RoutinePlugin):
        """Loads a RoutinePlugin into the PluginController."""
        self.loaded_routine_plugins.append(plugin)
        plugin.load_plugin(self.simulator)

    def has_plugin(self, plugin_cls:type) -> bool:
        """Checks if a Plugin of a given class is loaded."""
        return any(isinstance(x, plugin_cls) for x in self.loaded_plugins)
            
    def get_first_plugin_of_type(self, plugin_cls:type):
        return next(p for p in self.loaded_plugins if isinstance(p,plugin_cls))
        for p in self.loaded_plugins:
            if isinstance(p,plugin_cls): return p
    
    def get_all_plugins_of_type(self, plugin_class:type) -> list:
        """Returns a list of all Plugins of a given class."""
        return [p for p in self.loaded_plugins if isinstance(p,plugin_class)]

    def setup_logging(self):
        """Sets up the logging for all loaded LoggerPlugins."""
        for plugin in self.loaded_logger_plugins:
            plugin.setup_logger()

    def log_simulation_step(self):
        """Logs the current simulation step for all loaded LoggerPlugins."""
        for l in self.loaded_logger_plugins:
            l.log_simulation_step()

    def stop_logging(self):
        """Stops the logging for all loaded LoggerPlugins."""
        for plugin in self.loaded_logger_plugins:
            plugin.stop_logger()

    def update_plugins(self, cycle_step: int, simulation_step: int):
        self.update_loggers_and_routine_plugins(cycle_step, simulation_step)
        self.update_action_plugins(cycle_step, simulation_step)

    def update_loggers_and_routine_plugins(
        self, cycle_step: int, simulation_step: int
    ):
        for plugin in self.loaded_logger_plugins:
            plugin.update_time_step(cycle_step, simulation_step)
        for plugin in self.loaded_routine_plugins:
            plugin.update_time_step(cycle_step, simulation_step)

    def update_action_plugins(self, cycle_step: int, simulation_step: int):
        for plugin in self.loaded_action_plugins:
            plugin.update_time_step(cycle_step, simulation_step)
    

class LodusSimulation:
    def __init__(self, environment_graph: EnvironmentGraph):
        self.env_graph = environment_graph

        self.plugin_controller = PluginController(self)
        self.routine_controller = RoutineController(self)

        self.time_status: SimulationTimeStatus = SimulationTimeStatus(simulation_step=-1, cycle_length=24, total_cycles=1)
        
        self.experiment_name = "Lodus Simulation"
        self.experiment_config = {}

        # Extra logging data (not used for now)
        self.original_population_template = None
        self.original_block_template: CharacteristicsFactory = None # type: ignore
        self.original_repeating_actions = None

    ### Simulation Parameters Methods
    def set_cycle_length(self, cycle_length: int):
        """Sets the cycle length for the simulation."""
        self.time_status = SimulationTimeStatus(
            simulation_step=self.time_status.simulation_step,
            cycle_length=cycle_length,
            total_cycles=self.time_status.total_cycles
        )

    def set_total_cycles(self, total_cycles: int):
        """Sets the total number of cycles for the simulation."""
        self.time_status = SimulationTimeStatus(
            simulation_step=self.time_status.simulation_step,
            cycle_length=self.time_status.cycle_length,
            total_cycles=total_cycles
        )

    ### Simulation Methods
    def update_time_step(self):
        """Updates a time step for a given time.
        Updates Routines and Repeating Global Actions.

        Applies every TimeAction which matches time argument.
        """
        self.time_status = SimulationTimeStatus(
            simulation_step=self.time_status.simulation_step + 1,
            cycle_length=self.time_status.cycle_length,
            total_cycles=self.time_status.total_cycles
        )
        cycle_step = self.time_status.cycle_step
        simulation_step = self.time_status.simulation_step
        self.plugin_controller.update_loggers_and_routine_plugins(
            cycle_step, simulation_step
        )
        self.process_start_of_step_actions(cycle_step, simulation_step)
        self.plugin_controller.update_action_plugins(
            cycle_step, simulation_step
        )
        self.process_regular_and_end_of_step_actions(
            cycle_step, simulation_step
        )

        self.merge_blobs_in_all_nodes()
        self.env_graph.set_frame_origin_of_all_blobs()

    def merge_blobs_in_all_nodes(self):
        self.env_graph.merge_blobs_in_all_envnodes()

    ### Routine Controller Methods
    def add_action_type_to_function(self, action_type: str, function: Callable, is_base_action: bool):
        self.routine_controller.add_action_type_to_function(action_type, function, is_base_action)

    def add_global_action(self, global_action: GlobalAction):
        self.routine_controller.add_global_action(global_action)

    def direct_action_invoke(self, action: Action, cycle_step: int, simulation_step: int):
        self.routine_controller.consume_action(action, cycle_step, simulation_step)

    def queue_action_to_next_cycle_step(self, action: Action, at_cycle_step_start: bool =True):
        """Queues an action to be executed in the next cycle step."""
        self.routine_controller.queue_action_to_next_cycle_step(action, at_cycle_step_start)

    def process_actions(self, cycle_step: int, simulation_step: int):
        """Processes all actions for the given cycle_step and simulation_step."""
        actions = self.routine_controller.generate_action_list(cycle_step, self.time_status.simulation_step)
        self._consume_actions(actions, cycle_step, simulation_step)

    def process_start_of_step_actions(
        self, cycle_step: int, simulation_step: int
    ):
        actions = self.routine_controller.generate_start_of_step_action_list(
            cycle_step, simulation_step
        )
        self._consume_actions(actions, cycle_step, simulation_step)

    def process_regular_and_end_of_step_actions(
        self, cycle_step: int, simulation_step: int
    ):
        actions = (
            self.routine_controller.generate_regular_action_list(cycle_step)
            + self.routine_controller.generate_end_of_step_action_list(
                cycle_step, simulation_step
            )
        )
        self._consume_actions(actions, cycle_step, simulation_step)

    def _consume_actions(
        self,
        actions: list[Action],
        cycle_step: int,
        simulation_step: int,
    ):
        simplified_actions = self.routine_controller.simplify_action_list(actions, cycle_step, simulation_step)
        for action in simplified_actions:
            self.routine_controller.consume_action(action, cycle_step, simulation_step)

    ### Plugin Controller Methods
    def load_plugin(self, plugin: BasePlugin):
        """Loads a Plugin into the LodusSimulation."""
        self. plugin_controller.load_plugin(plugin)

    def setup_logging(self):
        """Sets up the logging for all loaded LoggerPlugins."""
        self.plugin_controller.setup_logging()

    def log_simulation_step(self):    
        """Logs the current simulation step for all loaded LoggerPlugins."""
        self.plugin_controller.log_simulation_step()

    def stop_logging(self):
        """Stops the logging for all loaded LoggerPlugins."""
        self.plugin_controller.stop_logging()

    def has_plugin(self, plugin_cls:type) -> bool:
        """Checks if a Plugin of a given class is loaded."""
        return self.plugin_controller.has_plugin(plugin_cls)
            
    def get_plugins(self, _type:type) -> list:
        """Returns a list of all Plugins of a given class."""
        return self.plugin_controller.get_all_plugins_of_type(_type)
    
    def get_first_plugin(self, _type:type):
        return self.plugin_controller.get_first_plugin_of_type(_type)
