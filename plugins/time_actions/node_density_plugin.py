from itertools import count
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

class NodeDensityPlugin(environment.TimeActionPlugin):
    
    def __init__(self, env_graph: environment.EnvironmentGraph, config_file_path):

        super().__init__()
        # JSON file containing the configuration of the Node Density Plugin
        self.config = json.loads(open(config_file_path ,'r').read())
        
        self.graph = env_graph
        
        # Sets the density of each EnvNode at the start of the simulation
        self.default_density = self.config['default_density']
        _custom_den_values = {t[0]:t[1] for t in self.config['custom_density_values']}
        for _name, _node in self.graph.node_dict.items():
            if _name in _custom_den_values:
                _density = _custom_den_values[_name]
            elif _node.containing_region_name in _custom_den_values:
                _density = _custom_den_values[_node.containing_region_name]
            elif _node.name in _custom_den_values:
                _density = _custom_den_values[_node.name]
            else:
                _density = self.default_density
            _node.add_characteristic('density', _density)

    def update_time_step(self, cycle_step, simulation_step):
        return #super().update_time_step(cycle_step, simulation_step)