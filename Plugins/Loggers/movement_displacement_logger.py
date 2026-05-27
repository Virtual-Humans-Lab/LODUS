import sys

from core.simulator import LodusSimulation
sys.path.append("/../../")
from core.environment import EnvironmentGraph, EnvNode
from core.plugin import LoggerPlugin
from core.population import Blob, PopulationTemplate

# Graphic and data libraries
import pandas as pd
pd.options.plotting.backend = "plotly"

from pathlib import Path

class MovementDisplacementLogger(LoggerPlugin):

    def __init__(self):
        # Movement dicts 
        self.movement_counter = {}
        self.group_movement_counter = {}

        # OD Dicts: SimulationStep > Origin > Destination > Quantities
        self.region_od_matrix:dict[str,dict[str,dict[str,dict[str,int]]]] = {}
        self.node_od_matrix:dict[str,dict[str,dict[str,dict[str,int]]]] = {}

        # Custom PopTemplates
        self.region_custom_templates: dict[str,PopulationTemplate] = {}
        self.node_custom_templates: dict[str,PopulationTemplate] = {}

    def load_plugin(self, simulation: LodusSimulation):
         # Attaches itself to the EnvGraph
        self.env_graph: EnvironmentGraph = simulation.env_graph
        self.env_graph.movement_logger_dict["displacement"] = self.log_od_movement
        #graph.od_matrix_logger = self
        
        # Cycle length and Current SimulationStep
        self.cycle_lenght:int = simulation.time_status.cycle_length
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

                    
    def log_simulation_step(self):
        pass

    def log_od_movement(self, _ori:EnvNode, _dest:EnvNode, _blobs:list[Blob]):
        # Total population in all Blobs
        total = sum([b.get_population_size() for b in _blobs])
        node_distances = self.env_graph.get_node_distances(target_node=_ori, dist_type=self.env_graph.default_distance_type)
        distance = node_distances.distance_to_others[_dest.get_complete_name()]
        
        self.movement_counter[distance] = self.movement_counter.get(distance,0) + total
        self.group_movement_counter[distance] = self.group_movement_counter.get(distance,0) + len(_blobs)

    
    def stop_logger(self):
        if len(self.movement_counter.items()) == 0:
            empty_df = pd.DataFrame()
            #pd.DataFrame().to_csv
            pd.DataFrame().to_csv(self.data_frames_path + "movement_counter.csv", 
                           sep=";", 
                           encoding="utf-8-sig")
            pd.DataFrame().to_csv(self.data_frames_path + "group_movement_counter.csv", 
                                 sep=";", 
                                 encoding="utf-8-sig")
            return
        self.movement_counter = dict(sorted(self.movement_counter.items()))
        movement_df = pd.DataFrame.from_dict(self.movement_counter, orient='index')
        movement_df.index.name = "distance"
        movement_df.to_csv(self.data_frames_path + "movement_counter.csv", 
                           sep=";", 
                           encoding="utf-8-sig",
                           header=["frequency"])
        
        
        self.group_movement_counter = dict(sorted(self.group_movement_counter.items()))
        group_movement_df = pd.DataFrame.from_dict(self.group_movement_counter, orient='index')
        group_movement_df.index.name = "distance"
        group_movement_df.to_csv(self.data_frames_path + "group_movement_counter.csv", 
                                 sep=";", 
                                 encoding="utf-8-sig",
                                 header=["frequency"])

    def unload_plugin(self):
        return super().unload_plugin()