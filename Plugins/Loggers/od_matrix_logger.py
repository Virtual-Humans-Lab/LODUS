# LODUS core
import sys

from core.simulator import LodusSimulation
sys.path.append("/../../")
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


class ODMovementRecordKey(Enum):
    REGION_TO_REGION = 0,
    NODE_TO_NODE = 0

class ODMatrixLogger(LoggerPlugin):

    def __init__(self):
        # Which data is being recorded
        self.data_to_record:set[ODMovementRecordKey] = set()

        # OD Dicts: SimulationStep > Origin > Destination > Quantities
        self.region_od_matrix:dict[int,dict[str,dict[str,dict[str,int]]]] = {}
        self.node_od_matrix:dict[int,dict[str,dict[str,dict[str,int]]]] = {}

        # Custom PopTemplates
        self.region_custom_templates: dict[str,PopulationTemplate] = {}
        self.node_custom_templates: dict[str,PopulationTemplate] = {}
        
    def load_plugin(self, simulation: LodusSimulation):
        # Attaches itself to the EnvGraph
        self.env_graph: EnvironmentGraph = simulation.env_graph
        self.env_graph.movement_logger_dict["od_logger"] = self.log_od_movement
        #graph.od_matrix_logger = self

        # Cycle length and Current SimulationStep
        self.cycle_lenght:int = simulation.cycle_lenght
        self.sim_step: int = 0 

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

        # Create sparse buckets for this step; entries are added only when movement happens.
        if ODMovementRecordKey.REGION_TO_REGION in self.data_to_record:
            self.region_od_matrix[self.sim_step] = {}

        if ODMovementRecordKey.NODE_TO_NODE in self.data_to_record:
            self.node_od_matrix[self.sim_step] = {}

    def _get_region_step_entry(self, origin_region: str, destination_region: str) -> dict[str, int]:
        step_data = self.region_od_matrix[self.sim_step]
        origin_data = step_data.setdefault(origin_region, {})
        if destination_region not in origin_data:
            origin_data[destination_region] = {"Total": 0}
            for _key in self.region_custom_templates:
                origin_data[destination_region][_key] = 0
        return origin_data[destination_region]

    def _get_node_step_entry(self, origin_node: str, destination_node: str) -> dict[str, int]:
        step_data = self.node_od_matrix[self.sim_step]
        origin_data = step_data.setdefault(origin_node, {})
        if destination_node not in origin_data:
            origin_data[destination_node] = {"Total": 0}
            for _key in self.node_custom_templates:
                origin_data[destination_node][_key] = 0
        return origin_data[destination_node]
            
    def log_simulation_step(self):
        pass

    def log_od_movement(self, _ori:EnvNode, _dest:EnvNode, _blobs:list[Blob]):
        # Total population in all Blobs
        total = sum([b.get_population_size() for b in _blobs])

        if total == 0:
            return
        
        # Record Region-Region movement 
        if ODMovementRecordKey.REGION_TO_REGION in self.data_to_record:
            _x = self._get_region_step_entry(_ori.containing_region_name, _dest.containing_region_name)
            _x["Total"] += total
            for _b in _blobs:
                for _key, _pt in self.region_custom_templates.items():
                    _x[_key] += _b.get_population_size(_pt)
        
        # Record Node-Node movement
        if ODMovementRecordKey.NODE_TO_NODE in self.data_to_record:
            _x = self._get_node_step_entry(_ori.get_complete_name(), _dest.get_complete_name())
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
               
    
    def write_od_matrix_to_csv(self, label:str, custom_columns:list[str], od_matrix:dict[int,dict[str,dict[str,dict[str,int]]]]):
        
        # Columns and Data Setup
        _columns = ["SimulationStep", "CycleStep", "Cycle", "Origin", "Destination", "Total"] + custom_columns
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
        if df.empty:
            df.to_csv(self.data_frames_path + "od_matrix_" + label + "_step.csv", sep=";", encoding="utf-8-sig", index=False)
            df.to_csv(self.data_frames_path + "od_matrix_" + label + "_cycle.csv", sep=";", encoding="utf-8-sig", index=False)
            df.to_csv(self.data_frames_path + "od_matrix_" + label + ".csv", sep=";", encoding="utf-8-sig", index=False)
            return

        df.to_csv(self.data_frames_path + "od_matrix_" + label + "_step.csv", sep=";", encoding="utf-8-sig")

        # Data per Cycle
        df.drop("SimulationStep", inplace=True, axis=1) 
        df.drop("CycleStep", inplace=True, axis=1) 
        df_cycle = df.groupby(["Cycle", "Origin", "Destination"]).sum().reset_index()
        df_cycle.to_csv(self.data_frames_path + "od_matrix_" + label + "_cycle.csv", sep=";", encoding="utf-8-sig")

        # Data in entire Simulation
        df_cycle.drop("Cycle", inplace=True, axis=1) 
        df_sim = df_cycle.groupby(["Origin", "Destination"]).sum().reset_index()
        df_sim.to_csv(self.data_frames_path + "od_matrix_" + label + ".csv", sep=";", encoding="utf-8-sig")

    def unload_plugin(self):
        return super().unload_plugin()