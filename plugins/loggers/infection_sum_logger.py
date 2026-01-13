import sys

sys.path.append("/../../")
from pathlib import Path

# Graphic and data libraries
import pandas as pd
from time_actions.levy_walk_plugin import LevyWalkPlugin
from time_actions.infection_plugin import InfectionPlugin

from environment import EnvironmentGraph
from logger_plugin import LoggerPlugin

class InfectionSumLogger(LoggerPlugin):

    def __init__(self, base_filename:str):
        # Paths for folders
        self.base_path = "output_logs/" + base_filename + "/"
        self.data_frames_path = self.base_path + "/data_frames/"
        self.infection_plugin = None
        self.infection_sums = []

    def load_to_enviroment(self, env:EnvironmentGraph):
         # Attaches itself to the EnvGraph
        self.graph: EnvironmentGraph = env
        self.cycle_length = self.graph.routine_cycle_length
        self.infection_plugin:InfectionPlugin = self.graph.get_first_plugin(InfectionPlugin)
        if self.infection_plugin is None:
            exit("INFECTION PLUGIN NOT LOADED")

    def start_logger(self):
        # Create the required directories
        Path(self.base_path).mkdir(parents=True, exist_ok=True)
        Path(self.data_frames_path).mkdir(parents=True, exist_ok=True)

    def update_time_step(self, cycle_step, simulation_step) -> None:
        # Update SimulationStep
        self.sim_step = simulation_step
                    
    def log_simulation_step(self):
        self.infection_sums.append((self.sim_step, 
                                    self.sim_step % self.cycle_length,
                                    self.infection_plugin.sum_infected))
 
    def stop_logger(self):
        df = pd.DataFrame(self.infection_sums)
        df.to_csv(self.data_frames_path + "infection_sum.csv", 
                  sep=";", 
                  encoding="utf-8-sig",
                  header=["Simulation Step", "Cycle Step", "Infection Sum"],
                  index = False)