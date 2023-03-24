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

class MovementDisplacementLogger(LoggerPlugin):

    def __init__(self, base_filename:str):

        # Movement dicts 
        self.movement_counter = {}
        self.group_movement_counter = {}

        # OD Dicts: SimulationStep > Origin > Destination > Quantities
        self.region_od_matrix:dict[str,dict[str,dict[str,dict[str,int]]]] = {}
        self.node_od_matrix:dict[str,dict[str,dict[str,dict[str,int]]]] = {}

        # Custom PopTemplates
        self.region_custom_templates: dict[str,PopTemplate] = {}
        self.node_custom_templates: dict[str,PopTemplate] = {}

        # Paths for folders
        self.base_path = "output_logs/" + base_filename + "/"
        self.data_frames_path = self.base_path + "/data_frames/"

    def load_to_enviroment(self, env:EnvironmentGraph):
         # Attaches itself to the EnvGraph
        self.graph: EnvironmentGraph = env
        self.graph.movement_logger_dict["displacement"] = self.log_od_movement
        #graph.od_matrix_logger = self
        
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

    def log_od_movement(self, _ori:EnvNode, _dest:EnvNode, _blobs:list[Blob]):
        # Total population in all Blobs
        total = sum([b.get_population_size() for b in _blobs])
        node_distances = self.graph.get_node_distances(_ori)
        distance = node_distances.distance_to_others[_dest.get_unique_name()]
        
        self.movement_counter[distance] = self.movement_counter.get(distance,0) + total
        self.group_movement_counter[distance] = self.group_movement_counter.get(distance,0) + len(_blobs)

    
    def stop_logger(self):
        self.movement_counter = dict(sorted(self.movement_counter.items()))
        movement_df = pd.DataFrame.from_dict(self.movement_counter, orient='index')
        movement_df.to_csv(self.data_frames_path + "movement_counter.csv", sep=";", encoding="utf-8-sig")
        
        self.group_movement_counter = dict(sorted(self.group_movement_counter.items()))
        group_movement_df = pd.DataFrame.from_dict(self.group_movement_counter, orient='index')
        group_movement_df.to_csv(self.data_frames_path + "group_movement_counter.csv", sep=";", encoding="utf-8-sig")

    
    def write_od_matrix_to_csv(self, label:str, custom_columns:list[str], od_matrix:dict[str,dict[str,dict[str,dict[str,int]]]]):
        
        # Columns and Data Setup
        _columns = ["SimulationStep", "Cycle Step", "Cycle", "Origin", "Destination", "Total"] + custom_columns
        _data = []
        
        # Get data entries in dict: SimulationStep > Origin > Destination > Quantities
        for _sim_step_key, _sim_step_val in od_matrix.items():
            for _or_key, _or_val in _sim_step_val.items():
                for _dest_key, _dest_val in _or_val.items():
                    _row = [_sim_step_key, _sim_step_key % self.cycle_lenght, _sim_step_key // self.cycle_lenght, _or_key, _dest_key]
                    for _key, _val in _dest_val.items():
                        _row.append(_val)
                    _data.append(_row)

        # Data per SimulationStep
        df = pd.DataFrame(data = _data, columns= _columns)
        df.to_csv(self.data_frames_path + "od_matrix_" + label + "_step.csv", sep=";", encoding="utf-8-sig")

        # Data per Cycle
        df.drop("SimulationStep", inplace=True, axis=1) 
        df.drop("Cycle Step", inplace=True, axis=1) 
        df_cycle = df.groupby(["Cycle", "Origin", "Destination"]).sum().reset_index()
        df_cycle.to_csv(self.data_frames_path + "od_matrix_" + label + "_cycle.csv", sep=";", encoding="utf-8-sig")

        # Data in entire Simulation
        df_cycle.drop("Cycle", inplace=True, axis=1) 
        df_sim = df_cycle.groupby(["Origin", "Destination"]).sum().reset_index()
        df_sim.to_csv(self.data_frames_path + "od_matrix_" + label + ".csv", sep=";", encoding="utf-8-sig")
