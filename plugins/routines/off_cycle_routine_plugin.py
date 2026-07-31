from __future__ import annotations
import json
import sys
from typing import Any


from core.routine import Action, GlobalAction
from util.data_parse import parse_global_routines, parse_local_routines

sys.path.append("/../../")
from pathlib import Path

from core.simulator import LodusSimulation
from core.environment import EnvironmentGraph
from core.plugin import RoutinePlugin


class OffCycleRoutinePlugin(RoutinePlugin):

    def __init__(self):
        '''
        Plugin that ....
        '''
        super().__init__()
        self.__header = "Off Cycle Routine Plugin:"


    def load_plugin(self, simulation: LodusSimulation):
        self.graph = simulation.env_graph
        if "off_cycle_routine_plugin" not in simulation.experiment_config:
            print(self.__header, "Experiment config should have a 'off_cycle_routine_plugin' key. Using an empty entry (default plugin values)")
        
        # Loads experiment configuration, if any
        self.config: dict[str, Any] = simulation.experiment_config.get("off_cycle_routine_plugin", {})
        self.start_of_step_global_actions:list[GlobalAction] = []
        self.end_of_step_global_actions:list[GlobalAction] = []

        self.start_of_step_actions:list[tuple[int, str, Action]] = []
        self.end_of_step_actions:list[tuple[int, str, Action]] = []

        self.start_files = self.config.get("start_of_step_routine_files", [])
        self.end_files = self.config.get("end_of_step_routine_files", [])


        self.load_routine_files()

    def unload_plugin(self):
        return super().unload_plugin()

    def update_time_step(self, cycle_step: int, simulation_step: int):
        return super().update_time_step(cycle_step, simulation_step)

    def load_routine_files(self):
        data_path =  Path(__file__).parent.parent.parent / "data_input"

        for sf in self.start_files:
            with open(data_path / sf, 'r', encoding='utf8') as content:
                _data = json.load(content)
            self.start_of_step_global_actions.extend(parse_global_routines(_data))
            self.start_of_step_actions.extend(parse_local_routines(_data))
            print("Start of step actions:", self.start_of_step_actions)
            #_global_actions, _actions = parse_routines(_data)
            #self.start_of_step_global_actions.extend(_global_actions)
            #self.start_of_step_actions.extend(_actions)

        for ef in self.end_files:
            with open(data_path / ef, 'r', encoding='utf8') as content:
                _data = json.load(content)
            self.end_of_step_global_actions.extend(parse_global_routines(_data))
            #_global_actions, _actions = parse_routines(_data)
            #self.end_of_step_global_actions.extend(_global_actions)
            #self.end_of_step_actions.extend(_actions)

    def process_start_of_step_actions(self, cycle_step, simulation_step):
        action_list = []
        for _a in self.start_of_step_actions:
            if _a[0] == simulation_step:
                action_list.append(_a[2])
        return action_list
    
    def process_end_of_step_actions(self, cycle_step, simulation_step):
        action_list = []
        for _a in self.end_of_step_actions:
            if _a[0] == simulation_step:
                action_list.append(_a[2])
        return action_list
