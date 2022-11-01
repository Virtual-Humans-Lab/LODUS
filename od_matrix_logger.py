from time import sleep
import environment
from population import Blob, PopTemplate
import os 
import util
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd

import numpy as np
import pandas as pd
pd.options.plotting.backend = "plotly"
from pathlib import Path

import copy
from enum import Enum


class LoggerODRecordKey(Enum):
    REGION_TO_REGION = 0

class ODMatrixLogger():

    def __init__(self, graph:environment.EnvironmentGraph, time_cycle=24) -> None:
        self.graph = graph
        graph.od_matrix_logger = self
        self.time_cycle = time_cycle
        self.data_to_record:set[LoggerODRecordKey] = set()


    def log_od_movement(self, origin_node:environment.EnvNode, destination_node:environment.EnvNode, blobs:list[Blob]):
        
        print(f"Test: from {origin_node.get_unique_name()} to {destination_node.get_unique_name()}")