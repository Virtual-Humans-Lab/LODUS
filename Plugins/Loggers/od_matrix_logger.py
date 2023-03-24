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


class ODMovementRecordKey(Enum):
    REGION_TO_REGION = 0,
    NODE_TO_NODE = 0

class ODMatrixLogger(LoggerPlugin):

    def __init__(self, base_filename:str):
        # Which data is being recorded
        self.data_to_record:set[ODMovementRecordKey] = set()

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
        self.graph.movement_logger_dict["od_logger"] = self.log_od_movement
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

        # Setup Region-Region dict: SimulationStep > Origin > Destination > Quantities
        if ODMovementRecordKey.REGION_TO_REGION in self.data_to_record:
            self.region_od_matrix[self.sim_step] = {}
            for orig in self.graph.region_list:
                self.region_od_matrix[self.sim_step][orig.name] = {}
                for dest in self.graph.region_list:
                    self.region_od_matrix[self.sim_step][orig.name][dest.name] = {"Total" : 0}
                    for _key in self.region_custom_templates:
                        self.region_od_matrix[self.sim_step][orig.name][dest.name][_key] = 0
        
        # Setup Node-Node dict: SimulationStep > Origin > Destination > Quantities
        if ODMovementRecordKey.NODE_TO_NODE in self.data_to_record:
            self.node_od_matrix[self.sim_step] = {}
            for orig in self.graph.node_list:
                self.node_od_matrix[self.sim_step][orig.get_unique_name()] = {}
                for dest in self.graph.node_list:
                    self.node_od_matrix[self.sim_step][orig.get_unique_name()][dest.get_unique_name()] = {"Total" : 0}
                    for _key in self.node_custom_templates:
                        self.node_od_matrix[self.sim_step][orig.get_unique_name()][dest.get_unique_name()][_key] = 0
            
    def log_simulation_step(self):
        pass

    def log_od_movement(self, _ori:EnvNode, _dest:EnvNode, _blobs:list[Blob]):
        # Total population in all Blobs
        total = sum([b.get_population_size() for b in _blobs])
        
        # Record Region-Region movement 
        if ODMovementRecordKey.REGION_TO_REGION in self.data_to_record:
            _x = self.region_od_matrix[self.sim_step][_ori.containing_region_name][_dest.containing_region_name]
            _x["Total"] += total
            for _b in _blobs:
                for _key, _pt in self.region_custom_templates.items():
                    _x[_key] += _b.get_population_size(_pt)
        
        # Record Node-Node movement
        if ODMovementRecordKey.NODE_TO_NODE in self.data_to_record:
            _x = self.node_od_matrix[self.sim_step][_ori.get_unique_name()][_dest.get_unique_name()]
            _x["Total"] += total
            for _b in _blobs:
                for _key, _pt in self.node_custom_templates.items():
                    _x[_key] += _b.get_population_size(_pt)
    
    def stop_logger(self):
        
        # Write Region to Region files
        if ODMovementRecordKey.REGION_TO_REGION in self.data_to_record:
            self.write_od_matrix_to_csv("region", list(self.region_custom_templates.keys()), self.region_od_matrix)

        # Write Node to Node files
        if ODMovementRecordKey.NODE_TO_NODE in self.data_to_record:
            self.write_od_matrix_to_csv("node", list(self.node_custom_templates.keys()), self.node_od_matrix)
               
    
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
