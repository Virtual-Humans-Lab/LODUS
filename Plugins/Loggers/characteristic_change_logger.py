# LODUS core
import sys

from core.simulator import LodusSimulation

from core.environment import EnvironmentGraph, EnvNode, EnvRegion
from core.plugin import LoggerPlugin
from core.population import Blob, PopulationTemplate

# Graphic and data libraries
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
pd.options.plotting.backend = "plotly"
import numpy as np

from pathlib import Path
from enum import Enum

class CharacteristicChangeLogger(LoggerPlugin):

    def __init__(self):
        pass     
        
    def load_plugin(self, simulation: LodusSimulation): 
        # Attaches itself to the EnvGraph
        self.env_graph: EnvironmentGraph = simulation.env_graph
        self.env_graph.characteristic_change_logger["characteristic_change_logger"] = self.log_characteristic_change

        # Cycle length and Current SimulationStep
        self.cycle_lenght:int = simulation.cycle_lenght
        self.sim_step: int = 0 

        # Charactirstic Change logging
        self.char_change_logs = []

        # Paths for folders
        self.base_path = "output_logs/" + simulation.experiment_name + "/"
        self.data_frames_path = self.base_path + "/data_frames/"

    def setup_logger(self):
        # Create the required directories
        Path(self.base_path).mkdir(parents=True, exist_ok=True)
        Path(self.data_frames_path).mkdir(parents=True, exist_ok=True)

    def update_time_step(self, cycle_step, simulation_step) -> None:
        # Update SimulationStep
        self.sim_step = simulation_step

    def log_simulation_step(self):
        pass

    def log_characteristic_change(self, blob:Blob, char_key, prev_value, new_value):
        node = None
        for n in self.env_graph.node_dict.values():
            if blob in n.contained_blobs:
                node = n
                break
        
        self.char_change_logs.append([self.sim_step,
                                        self.sim_step % self.cycle_lenght,
                                        self.sim_step//self.cycle_lenght,
                                        node.containing_region_name,
                                        node.get_complete_name(),
                                        char_key,
                                        prev_value,
                                        new_value,
                                        blob.get_population_size()])       

    def stop_logger(self):
        df = pd.DataFrame(self.char_change_logs,   
                            columns = ["Simulation Step", 
                                        "Cycle Step", 
                                        "Cycle", 
                                        "Region", 
                                        "Node",
                                        "Characteristic",
                                        "Previous Value",
                                        "New Value",
                                        "Population Size"])
        
        df.to_csv(self.data_frames_path + 'characteristic_change_entries.csv', sep = ';', encoding="utf-8-sig")

    def unload_plugin(self):
        return super().unload_plugin()