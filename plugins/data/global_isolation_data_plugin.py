import copy
import sys
from typing import Optional

from random_inst import FixedRandom

sys.path.append('../')

import random
import time

from scipy.stats import levy as scipy_levy

import environment
from util import DistanceType

import pandas as pd



class GlobalIsolationDataPlugin(environment.TimeActionPlugin):

    def __init__(self, env_graph: environment.EnvironmentGraph):
        super().__init__()
        
        self.distribution_sampler = scipy_levy
        self.graph = env_graph
        #self.set_pair('levy_walk', self.levy_walk)

        # Loads experiment configuration, if any
        self.config:dict = self.graph.experiment_config.get("global_isolation_data_plugin", {})
        
        self.global_isolation:float = self.config.get("global_isolation", 0.0)
        self.graph.data_action_map["isolation"] = self.get_isolation
        print("GLOBAL ISOLATION", self.global_isolation)
       
    def update_time_step(self, cycle_step, simulation_step):
        return
    
    def get_isolation(self, region, node):
        return self.global_isolation