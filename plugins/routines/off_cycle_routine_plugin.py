# LODUS core
import json
import sys

from data_parse_util import parse_routines

sys.path.append("/../../")
from pathlib import Path

from environment import EnvironmentGraph, RoutinePlugin


class OffCycleRoutinePlugin(RoutinePlugin):

    def __init__(self, env_graph: EnvironmentGraph):
        '''
        Plugin that ....
        '''
        super().__init__()
        self.graph = env_graph
        self.__header = "---OffCycleRoutinePlugin:"

        if "off_cycle_routine_plugin" not in self.graph.experiment_config:
            print(self.__header, "Experiment config should have a 'off_cycle_routine_plugin' key. Using an empty entry (default plugin values)")
        
        # Loads experiment configuration, if any
        self.config:dict = self.graph.experiment_config.get("off_cycle_routine_plugin", {})

        self.start_files = self.config.get("start_of_step_routine_files", [])
        self.end_files = self.config.get("end_of_step_routine_files", [])


        self.load_routine_files()

    def load_routine_files(self):
        data_path =  Path(__file__).parent.parent.parent / "data_input"

        for sf in self.start_files:
            _content = open(data_path / sf, 'r', encoding='utf8')
            _data = json.load(_content)
            _global_actions, _actions = parse_routines(_data)
            self.start_of_step_global_actions.extend(_global_actions)
            self.start_of_step_actions.extend(_actions)

        for ef in self.end_files:
            _content = open(data_path / ef, 'r', encoding='utf8')
            _data = json.load(_content)
            _global_actions, _actions = parse_routines(_data)
            self.end_of_step_global_actions.extend(_global_actions)
            self.end_of_step_actions.extend(_actions)

    def process_start_of_step_actions(self, cycle_step, simulation_step):
        action_list = []
        for _a in self.start_of_step_actions:
            if _a[0] == simulation_step:
                action_list.append(_a[1])
        return action_list
    
    def process_end_of_step_actions(self, cycle_step, simulation_step):
        action_list = []
        for _a in self.end_of_step_actions:
            if _a[0] == simulation_step:
                action_list.append(_a[1])
        return action_list