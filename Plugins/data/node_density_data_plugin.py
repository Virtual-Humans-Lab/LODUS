from itertools import count
from pathlib import Path
from types import NoneType
import environment
from population import PopTemplate
import copy
from random_inst import FixedRandom
import math
import numpy as np
import csv
import util
import json

class NodeDensityDataPlugin(environment.TimeActionPlugin):
    
    def __init__(self, env_graph: environment.EnvironmentGraph):

        super().__init__()
        # JSON file containing the configuration of the Node Density Plugin
        self.graph = env_graph
        self.config = self.graph.experiment_config.get("node_density_data_plugin", {})
        self.graph.data_action_map["node_density"] = self.get_node_density
        
        if "configuration_file" in self.config:
            _path =  Path(__file__).parent.parent.parent / "data_input"
            _content = open(_path / self.config["configuration_file"], 'r', encoding='utf8')
            self.config = json.load(_content)

        # Sets the density of each EnvNode at the start of the simulation
        self.default_density = self.config['default_density']
        self.custom_density = {t[0]:t[1] for t in self.config['custom_density_values']}
        

    def update_time_step(self, cycle_step, simulation_step):
        return #super().update_time_step(cycle_step, simulation_step)
    
    def get_node_density(self, region:environment.EnvRegion, node:environment.EnvNode):
        _unique_name = node.get_unique_name()

        if _unique_name in self.custom_density:
            return self.custom_density[_unique_name]
        elif node.containing_region_name in self.custom_density:
            return self.custom_density[node.containing_region_name]
        elif node.name in self.custom_density:
            return self.custom_density[node.name]
        else:
            return self.default_density