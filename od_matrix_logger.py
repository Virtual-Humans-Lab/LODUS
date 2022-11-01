from time import sleep
import environment
from population import Blob, PopTemplate
import os 
import util
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
import csv

import numpy as np
import pandas as pd
pd.options.plotting.backend = "plotly"
from pathlib import Path

import copy
from enum import Enum


class LoggerODRecordKey(Enum):
    REGION_TO_REGION = 0

class ODMatrixLogger():

    def __init__(self, base_filename:str, graph:environment.EnvironmentGraph, time_cycle=24) -> None:
        self.graph = graph
        graph.od_matrix_logger = self
        self.time_cycle = time_cycle
        self.sim_step = 0 # Current Simulation Step
        self.data_to_record:set[LoggerODRecordKey] = set()
        self.region_custom_templates: dict = {}
        self.region_od_matrix = {}

        # Create the required directories
        self.base_path = 'output_logs/' + base_filename + '/'
        self.data_frames_path = self.base_path + "/data_frames/"
        Path(self.base_path).mkdir(parents=True, exist_ok=True)
        Path(self.data_frames_path).mkdir(parents=True, exist_ok=True)
        

    def update_time_step(self, cycle_step, simulation_step) -> None:
        self.sim_step = simulation_step
        print(f"Recording Step {self.sim_step}, Cycle Step {cycle_step}")

        self.region_od_matrix[self.sim_step] = {}
        for orig in self.graph.region_list:
            self.region_od_matrix[self.sim_step][orig.name] = {}
            for dest in self.graph.region_list:
                self.region_od_matrix[self.sim_step][orig.name][dest.name] = {"Total" : 0}
                for _key in self.region_custom_templates:
                    self.region_od_matrix[self.sim_step][orig.name][dest.name][_key] = 0
        
        #if simulation_step == 1:
        #    print (self.region_od_matrix[0]["Azenha"]["Azenha"])
        #    exit(0)


    def log_od_movement(self, _ori:environment.EnvNode, _dest:environment.EnvNode, _blobs:list[Blob]):
        total = sum([b.get_population_size() for b in _blobs])
        
        print(f"Test: from {_ori.get_unique_name()} to {_dest.get_unique_name()}, quant {total}")

        if LoggerODRecordKey.REGION_TO_REGION in self.data_to_record:
            _x = self.region_od_matrix[self.sim_step][_ori.containing_region_name][_dest.containing_region_name]
            _x["Total"] += total
            for _b in _blobs:
                for _key, _pt in self.region_custom_templates.items():
                    _x[_key] += _b.get_population_size(_pt)

    def stop_logging(self):
        
        # Region to Region
        if LoggerODRecordKey.REGION_TO_REGION in self.data_to_record:
            # Header Setup
            #header = "Simulation Step; Cycle Step; Origin; Destination; Total"
            header = ["Simulation Step", "Origin", "Destination", "Total"]
            if self.region_custom_templates: header += list(self.region_custom_templates.keys())
            
            #self.region_od_f = open(self.data_frames_path + "od_matrix_region.csv", 'w', encoding='utf8')

            with open(self.data_frames_path + "od_matrix_region.csv", 'w', newline='', encoding='utf-8') as csvfile:
                spamwriter = csv.writer(csvfile, delimiter=';')

                spamwriter.writerow(header)

                for _ss_key, _ss_val in self.region_od_matrix.items():
                    for _or_key, _or_val in _ss_val.items():
                        for _dest_key, _dest_val in _or_val.items():
                            _row = [_ss_key, _or_key, _dest_key]
                            for _key, _val in _dest_val.items():
                                _row.append(_val)
                            spamwriter.writerow(_row)

            

            df = pd.read_csv(self.data_frames_path + "od_matrix_region.csv", sep=";")
            df.drop('Simulation Step', inplace=True, axis=1)
            print(df)
            
            aggregation_functions = {'Total': 'sum', 'occupation: [worker]': 'sum'}
            df_new = df.groupby(['Origin', "Destination"]).sum()

            print(df_new)
            df_new.to_csv(self.data_frames_path + "od_matrix_region_sum.csv")
               

        print("ACABO")