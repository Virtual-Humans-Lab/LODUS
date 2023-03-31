# LODUS core
import json
import sys
sys.path.append("/../../")
from environment import EnvironmentGraph, EnvNode, EnvRegion, RoutinePlugin
from logger_plugin import LoggerPlugin
from population import Blob, PopTemplate

from pathlib import Path
from enum import Enum

class OffCycleRoutinePlugin(RoutinePlugin):

    def __init__(self, env_graph: EnvironmentGraph):
        '''
        Plugin that ....
        '''
        super().__init__()
        self.graph = env_graph

        if "off_cycle_routine_plugin" not in self.graph.experiment_config:
            print("Experiment config should have a 'off_cycle_routine_plugin' key. Using an empty entry (default plugin values)")
        
        # Loads experiment configuration, if any
        self.config:dict = self.graph.experiment_config.get("off_cycle_routine_plugin", {})

        self.start_files = self.config.get("start_of_step_routine_files", [])
        self.end_files = self.config.get("end_of_step_routine_files", [])

        self.start_actions = []
        self.end_actions = []
        self.start_global_actions = []
        self.end_global_actions = []
        self.__header = "---OffCycleRoutinePlugin:"

        self.load_routine_files()

    def load_routine_files(self):
        data_path =  Path(__file__).parent.parent.parent / "data_input"

        for sf in self.start_files:
            _content = open(data_path / sf, 'r', encoding='utf8')
            _data = json.load(_content)
            print(self.__header, "Loading Start of Step Routine:", sf)
            print(_data)

        for ef in self.end_files:
            print("Loading End of Step Routine:", ef)
        exit()

        pass

    def process_start_of_step_actions(self, cycle_step, simulation_step):
        return super().process_start_of_step_actions(cycle_step, simulation_step)
    
    def process_end_of_step_actions(self, cycle_step, simulation_step):
        return super().process_end_of_step_actions(cycle_step, simulation_step)