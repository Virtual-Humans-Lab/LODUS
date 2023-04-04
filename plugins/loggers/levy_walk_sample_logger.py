import sys

sys.path.append("/../../")
from pathlib import Path

# Graphic and data libraries
import pandas as pd
from time_actions.levy_walk_plugin import LevyWalkPlugin

from environment import EnvironmentGraph
from logger_plugin import LoggerPlugin


class LevyWalkSampleLogger(LoggerPlugin):

    def __init__(self, base_filename:str):
        # Paths for folders
        self.base_path = "output_logs/" + base_filename + "/"
        self.data_frames_path = self.base_path + "/data_frames/"
        self.levy_walk_plugin = None

    def load_to_enviroment(self, env:EnvironmentGraph):
         # Attaches itself to the EnvGraph
        self.graph: EnvironmentGraph = env
        self.levy_walk_plugin = self.graph.get_first_plugin(LevyWalkPlugin)
        if self.levy_walk_plugin is None:
            exit("PLUIGIN NOT LOADEWD")
            

    def start_logger(self):
        # Create the required directories
        Path(self.base_path).mkdir(parents=True, exist_ok=True)
        Path(self.data_frames_path).mkdir(parents=True, exist_ok=True)

    def update_time_step(self, cycle_step, simulation_step) -> None:
        # Update SimulationStep
        self.sim_step = simulation_step
                    
    def log_simulation_step(self):
        pass
 
    def stop_logger(self):
        self.distance_samples = self.levy_walk_plugin.sampled_distances # type: ignore
        df = pd.DataFrame(self.distance_samples)
        df.to_csv(self.data_frames_path + "levy_samples.csv", 
                           sep=";", 
                           encoding="utf-8-sig",
                           header=["samples"],
                           index = False)
    