# LODUS core
import sys
sys.path.append("/../../")
from environment import EnvironmentGraph, EnvNode, EnvRegion
from logger_plugin import LoggerPlugin
from population import Blob, PopTemplate

# Graphic and data libraries
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
pd.options.plotting.backend = "plotly"
import numpy as np

from pathlib import Path
from enum import Enum

class CharacteristicChangeLogger(LoggerPlugin):

    def __init__(self, base_filename:str):
              
        # Charactirstic Change logging
        self.char_change_logs = []

        # Paths for folders
        self.base_path = "output_logs/" + base_filename + "/"
        self.data_frames_path = self.base_path + "/data_frames/"

    def load_to_enviroment(self, env:EnvironmentGraph):
        # Attaches itself to the EnvGraph
        self.graph: EnvironmentGraph = env
        self.graph.characteristic_change_logger["characteristic_change_logger"] = self.log_characteristic_change

        # Cycle length and Current SimulationStep
        self.cycle_lenght:int = env.routine_cycle_length
        self.sim_step: int = 0 


    def start_logger(self):
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
        for n in self.graph.node_dict.values():
            if blob in n.contained_blobs:
                node = n
                break
        
        self.char_change_logs.append([self.sim_step,
                                        self.sim_step % self.cycle_lenght,
                                        self.sim_step//self.cycle_lenght,
                                        node.containing_region_name,
                                        node.get_unique_name(),
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