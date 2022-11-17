# LODUS core
import sys
sys.path.append('/../../')
from environment import EnvironmentGraph
from logger_plugin import LoggerPlugin

import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
pd.options.plotting.backend = "plotly"

from pathlib import Path
from enum import Enum

class BlobCountRecordKey(Enum):
    BLOB_COUNT_GLOBAL = 0
    BLOB_COUNT_REGION = 1
    BLOB_COUNT_NODE = 2

class BlobCountLogger(LoggerPlugin):
    
    def __init__(self, base_filename):

        # Sets paths and create folders
        self.base_path = 'output_logs/' + base_filename + '/'
        self.data_frames_path = self.base_path + "/data_frames/"
        
        # Which data is being recorded
        self.data_to_record:set[BlobCountRecordKey] = set()
               
        # Blob Count Logging
        self.blob_global_count = []
        self.blob_region_count = {}
        self.blob_node_count = {}

    def load_to_enviroment(self, env:EnvironmentGraph):
         # Attaches itself to the EnvGraph
        self.graph = env

        # Cycle length and Current SimulationStep
        self.cycle_lenght:int = self.graph.routine_cycle_length
        self.sim_step: int = 0 

        self.blob_global_count = []
        self.blob_region_count = {r:[] for r in self.graph.region_dict}
        self.blob_node_count = {n:[] for n in self.graph.node_dict}

    def start_logger(self):
        Path(self.base_path).mkdir(parents=True, exist_ok=True)
        Path(self.data_frames_path).mkdir(parents=True, exist_ok=True)

    def update_time_step(self, cycle_step, simulation_step):
        self.sim_step = simulation_step

    def log_simulation_step(self):
        if BlobCountRecordKey.BLOB_COUNT_GLOBAL in self.data_to_record:
            self.blob_global_count.append(self.graph.get_blob_count())
        if BlobCountRecordKey.BLOB_COUNT_REGION in self.data_to_record:
            for r,v in self.graph.region_dict.items():
                self.blob_region_count[r].append(v.get_blob_count())
        if BlobCountRecordKey.BLOB_COUNT_NODE in self.data_to_record:
            for n,v in self.graph.node_dict.items():
                self.blob_node_count[n].append(len(v.contained_blobs))


    def stop_logger(self):
        if BlobCountRecordKey.BLOB_COUNT_GLOBAL in self.data_to_record:
            df = pd.DataFrame({'Blob Count': self.blob_global_count})
            df = df.rename_axis('Simulation Frame')
            df.to_csv(self.data_frames_path + 'blob_count_global.csv', sep = ';', encoding="utf-8-sig")
        if BlobCountRecordKey.BLOB_COUNT_REGION in self.data_to_record:
            df = pd.DataFrame(self.blob_region_count)
            df = df.rename_axis('Simulation Frame').rename_axis('Region', axis=1)
            df.to_csv(self.data_frames_path + 'blob_count_region.csv', sep = ';', encoding="utf-8-sig")           
        if BlobCountRecordKey.BLOB_COUNT_NODE in self.data_to_record:
            df = pd.DataFrame(self.blob_node_count)
            df = df.rename_axis('Simulation Frame').rename_axis('Node', axis=1)
            df.to_csv(self.data_frames_path + 'blob_count_node.csv', sep = ';', encoding="utf-8-sig")

    def process_blob_count_line_plots(self):#, show_figures: bool, export_html: bool, export_figures: bool, layout_update=None):
        
        figures = []
        xaxes_upt = {"tickmode": "linear", "tick0": 0, "dtick": 24}
        
        if BlobCountRecordKey.BLOB_COUNT_GLOBAL in self.data_to_record:
            df = pd.DataFrame({'Blob Count': self.blob_global_count})
            df = df.rename_axis('Simulation Frame')
            df.to_csv(self.data_frames_path + 'blob_count_global.csv', sep = ';')
            fig = px.line(df, y="Blob Count", title="Blob Count - Global")
            fig.update_xaxes(xaxes_upt)
            figures.append(fig)
            
            df = pd.DataFrame({'Blob Count': self.blob_global_count})
            df = df.iloc[::24].reset_index(drop = True)
            df.index = range(1,len(df)+1)
            df.rename_axis('Simulation Day', inplace = True)
            fig = px.line(df, y="Blob Count", title="Blob Count - Global - Hour 0", markers=True)
            figures.append(fig)
            
            
        if BlobCountRecordKey.BLOB_COUNT_REGION in self.data_to_record:
            df = pd.DataFrame(self.blob_region_count)
            df = df.rename_axis('Simulation Frame').rename_axis('Region', axis=1)
            df.to_csv(self.data_frames_path + 'blob_count_region.csv', sep = ';')
            fig = px.line(df, labels={'value':'Blob Count'}, 
                                            title="Blob Count - Per Region")
            fig.update_xaxes(xaxes_upt)
            figures.append(fig)
            
            df = pd.DataFrame(self.blob_region_count)
            df = df.iloc[::24].reset_index(drop = True)
            df.index = range(1,len(df)+1)
            df = df.rename_axis('Simulation Day').rename_axis('Region', axis=1)
            fig = px.line(df, labels={'value':'Blob Count'}, 
                            title="Blob Count - Per Region - Hour 0", markers=True)
            figures.append(fig)
            
        if BlobCountRecordKey.BLOB_COUNT_NODE in self.data_to_record:
            df = pd.DataFrame(self.blob_node_count)
            df = df.rename_axis('Simulation Frame').rename_axis('Node', axis=1)
            df.to_csv(self.data_frames_path + 'blob_count_node.csv', sep = ';')
            fig = px.line(df, labels={'value':'Blob Count'}, 
                            title="Blob Count - Per Node")
            fig.update_xaxes(xaxes_upt)
            figures.append(fig)
            
            df = pd.DataFrame(self.blob_node_count)
            df = df.iloc[::24].reset_index(drop = True)
            df.index = range(1,len(df)+1)
            df = df.rename_axis('Simulation Day').rename_axis('Node', axis=1)
            fig = px.line(df, labels={'value':'Blob Count'}, 
                            title="Blob Count - Per Node - Hour 0", markers=True)
            figures.append(fig)
            
        # self.generate_figures(show_figures,export_figures, export_html, layout_update, figures)