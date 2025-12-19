# LODUS core
from fileinput import filename
import os
from platform import node
import sys

import environment
from population import PopTemplate
import util
sys.path.append('/../../')
from environment import EnvironmentGraph
from logger_plugin import LoggerPlugin

import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
pd.options.plotting.backend = "plotly"

from pathlib import Path
from enum import Enum
from time import sleep

class GiniCoefficientRecordKey(Enum):
    GINI_COEFFICIENT_GLOBAL = 0
    GINI_COEFFICIENT_REGION = 1
    GINI_COEFFICIENT_NODE = 2

class GiniCoefficientLogger(LoggerPlugin):
    
    def __init__(self, base_filename, graph:environment.EnvironmentGraph, time_cycle=24):
        self.graph = graph

        # Sets paths and create folders
        self.base_path = 'output_logs/' + base_filename + '/'
        self.data_frames_path = self.base_path + "/data_frames/"
        self.figures_path = self.base_path + "/figures/"
        self.html_plots_path = self.base_path + "/html_plots/"
        #self.generate_figures = generate_figures
        
        # Which data is being recorded
        self.data_to_record:set[GiniCoefficientRecordKey] = set()
               
        # Gini Coefficient Logging
        self.gini_global_coefficient = []
        self.gini_region_coefficient = {}
        self.gini_node_coefficient = {}

        # Custom Logging
        self.global_sampled_characteristics: dict[str, list[PopTemplate]] = {}
        self.region_sampled_characteristics: dict[str, list[PopTemplate]] = {}
        self.node_sampled_characteristics: dict[str, list[PopTemplate]] = {}
        
        self.custom_line_plots: dict = {}
        self.global_custom_line_plots: dict = {}
        self.region_custom_line_plots: dict = {}
        self.node_custom_line_plots: dict = {}

    # def add_global_sampled_characteristic(self, characteristic_name:str):
    #     """Adds a characteristic to be sampled globally for Gini calculation."""
    #     if characteristic_name not in self.global_sampled_characteristics:
    #         self.global_sampled_characteristics[characteristic_name] = []
    #     print("Possible values for", characteristic_name, ":", end=" ")
    #     print(self.graph.original_block_template.buckets[characteristic_name])
    #     possible_values = self.graph.original_block_template.buckets[characteristic_name]
    #     for value in possible_values:
    #         print(" - Creating template for", characteristic_name, "=", value)
    #         temp_template = PopTemplate(sampled_properties={characteristic_name: value})
    #         self.global_sampled_characteristics[characteristic_name].append(temp_template)

    def add_sampled_characteristic_logging(self, characteristic_name:str, level:GiniCoefficientRecordKey):
        """Adds a characteristic to be sampled at a given level for Gini calculation."""

        print("Possible values for", characteristic_name, ":", end=" ")
        print(self.graph.original_block_template.buckets[characteristic_name])
        possible_values = self.graph.original_block_template.buckets[characteristic_name]
        templates = []
        for value in possible_values:
            print(" - Creating template for", characteristic_name, "=", value)
            templates.append(PopTemplate(sampled_properties={characteristic_name: value}))

        if level == GiniCoefficientRecordKey.GINI_COEFFICIENT_GLOBAL:
            self.global_sampled_characteristics[characteristic_name] = templates
        elif level == GiniCoefficientRecordKey.GINI_COEFFICIENT_REGION:
            self.region_sampled_characteristics[characteristic_name] = templates
        elif level == GiniCoefficientRecordKey.GINI_COEFFICIENT_NODE:
            self.node_sampled_characteristics[characteristic_name] = templates
        else:
            raise ValueError("Invalid GiniCoefficientRecordKey level.")


    def load_to_enviroment(self, env:EnvironmentGraph):
        # Attaches itself to the EnvGraph
        self.graph = env

        # Cycle length and Current SimulationStep
        self.cycle_length:int = self.graph.routine_cycle_length
        self.sim_step: int = 0 

        self.gini_global_coefficient = []
        self.gini_region_coefficient = {r:[] for r in self.graph.region_dict}
        self.gini_node_coefficient = {n:[] for n in self.graph.node_dict}

    def start_logger(self):
        Path(self.base_path).mkdir(parents=True, exist_ok=True)
        Path(self.data_frames_path).mkdir(parents=True, exist_ok=True)
        # Path(self.figures_path).mkdir(parents=True, exist_ok=True)
        # Path(self.html_plots_path).mkdir(parents=True, exist_ok=True)

        # Remove existing files
        try:
            os.remove(self.base_path + "gini_global.csv")
            os.remove(self.base_path + "gini_region.csv")
            os.remove(self.base_path + "gini_node.csv")
        except OSError:
            pass

        # Global data file
        if self.global_sampled_characteristics:
            header = "Simulation_Step;Cycle_Step;Cycle"
            if self.global_sampled_characteristics: 
                header += ';' + ';'.join(list(self.global_sampled_characteristics.keys()))
            self.global_f = open(self.base_path + "gini_global.csv", 'w', encoding='utf8')
            self.global_f.write(header + '\n')

    def update_time_step(self, cycle_step, simulation_step):
        self.sim_step = simulation_step

    def log_simulation_step(self):
        if GiniCoefficientRecordKey.GINI_COEFFICIENT_GLOBAL in self.data_to_record:
            self.global_frame(self.graph, self.sim_step)
            #self.gini_global_coefficient.append(self.calculate_global_gini_coefficient)
        # if GiniCoefficientRecordKey.GINI_COEFFICIENT_REGION in self.data_to_record:
        #     for region_id, region in self.graph.region_dict.items():
        #         gini_value = self.graph.calculate_gini_coefficient(region=region)
        #         self.gini_region_coefficient[region_id].append(gini_value)
        # if GiniCoefficientRecordKey.GINI_COEFFICIENT_NODE in self.data_to_record:
        #     for node_id, node in self.graph.node_dict.items():
        #         gini_value = self.graph.calculate_gini_coefficient(node=node)
        #         self.gini_node_coefficient[node_id].append(gini_value)



    def global_frame(self, graph: environment.EnvironmentGraph, simulation_step:int):
        """
        Logs a global frame for Gini Coefficient calculation.
        """
        # Sets the default row
        _row = f"{simulation_step};{simulation_step % self.cycle_length};{simulation_step // self.cycle_length}"
        
        for char, pts in self.global_sampled_characteristics.items():
            populations = []
            for pt in pts:
                populations.append(graph.get_population_size(pt))
            gini_value = util.gini_coefficient(populations)
            _row += ";" + str(gini_value)

        self.global_f.write(_row + '\n')


    def stop_logger(self, show_figures: bool = False, export_html: bool = True, export_figures: bool = True):   
        self.global_f.close()


    def calculate_gini_coefficient(self, values:list[float]) -> float:
        """Calculates the Gini Coefficient for a list of values."""
        if len(values) == 0:
            return 0.0
        sorted_values = sorted(values)
        n = len(values)
        cumulative_values = [sum(sorted_values[:i+1]) for i in range(n)]
        cumulative_sum = sum(cumulative_values)
        total_sum = sum(sorted_values)
        gini_index = (n + 1 - 2 * (cumulative_sum / total_sum)) / n
        return gini_index