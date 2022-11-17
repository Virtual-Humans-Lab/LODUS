# LODUS core
import sys
sys.path.append('/../../')
from environment import EnvironmentGraph, EnvNode, EnvRegion
from VaccineLocalPlugin import VaccinePlugin
#import VaccineLocalPlugin
#from VaccineLocalPlugin import VaccinePlugin 
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

class LoggerODRecordKey(Enum):
    REGION_TO_REGION = 0,
    NODE_TO_NODE = 0

class VaccineLevelLogger(LoggerPlugin):
    def __init__(self, base_filename:str, graph:EnvironmentGraph, cycle_length: int=24) -> None:
        # Attaches itself to the EnvGraph
        self.graph: EnvironmentGraph = graph
        if not graph.has_plugin(VaccinePlugin):
            exit("No VaccinePlugin found in the EnviromentGraph")
        self.vacc_plugin:VaccinePlugin = graph.get_first_plugin(VaccinePlugin)
        self.DEBUG_VACC_DATA = True
        self.DEBUG_ALL_REGIONS = False
        self.DEBUG_REGIONS = []
        self.DEBUG_MOVE_PROFILE = False
        
        # Set the time/frame variables
        self.day_duration = cycle_length
        self.hour = 0
        self.time = 0
        self.current_day = 0
              
        # Get the total population of the simulation, and sets a dict of population per region and vaccines to be dealt at each region at that day
        self.total_population = self.graph.get_population_size()
        self.pop_per_region = {k: r.get_population_size() for k,r in self.graph.region_dict.items()}
        #self.vacc_per_region = {r: [0] * self.dosages for r in self.graph.region_dict}
        #self.remainder_per_region = {r: [0.0] * self.dosages for r in self.graph.region_dict}
        
        # Lists for number of vaccines per dosage per day, and vaccines given in the previous day
        #self.to_vaccinate_per_dose = [0] * self.dosages
        #self.prev_vac = [0] * self.dosages

        
        self.base_path = 'output_logs/' + base_filename + '/'
        self.data_frames_path = self.base_path + "/data_frames/"

        self.vacc_levels:int = self.vacc_plugin.vacc_levels
        self.profiles_to_record:list[PopTemplate] = []


    #### Logging Functions
    def start_logger(self):    
        
        Path(self.base_path).mkdir(parents=True, exist_ok=True)
        Path(self.data_frames_path).mkdir(parents=True, exist_ok=True)

        
        self.log_file_vacc = open(self.base_path + "vaccine_level.csv", 'w', encoding='utf8')
        _header = 'Frame;Hour;Day'
        for lvl in range(self.vacc_levels):
            _header += ";Vacc" + str(lvl)
        for lvl in range(self.vacc_levels):
            _header += ";dVacc" + str(lvl)
        self.log_file_vacc.write(_header + '\n')
        self.last_frame = [0] * self.vacc_levels
        
        for lvl in range(self.vacc_levels):
            pop_template = PopTemplate()
            pop_template.set_traceable_property("vaccine_level", lvl)
            logger.global_custom_templates['VaccLvl_' + str(lvl)] = pop_template
            logger.region_custom_templates['VaccLvl_' + str(lvl)] = pop_template
            logger.node_custom_templates['VaccLvl_' + str(lvl)] = pop_template
        
        logger.add_custom_line_plot('Vaccination Levels - Global', 
                                    file = 'global.csv',
                                    x_label="Frame", y_label="Population",
                                    columns= ['VaccLvl_' + str(lvl) for lvl in range(self.vacc_levels)])
        logger.add_custom_line_plot('Vaccination Levels - Azenha and Bom Fim', 
                                    file = 'regions.csv',
                                    x_label="Frame", y_label="Population",
                                    columns= ['VaccLvl_' + str(lvl) for lvl in range(self.vacc_levels)],
                                    level="Region", filter=['Azenha', 'Bom Fim'])
        logger.add_custom_line_plot('Vaccination Levels - Per Region', 
                                    file = 'regions.csv',
                                    x_label="Frame", y_label="Population",
                                    columns= ['VaccLvl_' + str(lvl) for lvl in range(self.vacc_levels)],
                                    level="Region")
        logger.add_custom_line_plot('Vaccination Level 2 - Per Region', 
                                    file = 'regions.csv',
                                    x_label="Frame", y_label="Population",
                                    columns= ['VaccLvl_2'],
                                    level="Region")
        logger.add_custom_line_plot('Vaccination Levels - Pharmacy Nodes', 
                                    file = 'nodes.csv',
                                    x_label="Frame", y_label="Population",
                                    columns= ['VaccLvl_' + str(lvl) for lvl in range(self.vacc_levels)],
                                    level="Node", filter=['pharmacy'])
        logger.add_custom_line_plot('Total Population - Pharmacy Nodes', 
                                    file = 'nodes.csv',
                                    x_label="Frame", y_label="Population",
                                    columns= ['Total'],
                                    level="Node", filter=['pharmacy'])
        
    def log_simulation_step(self):
        return

    def log_data(self, **kwargs):
        assert 'graph' in kwargs and 'frame' in kwargs, "Invalid inputs for logging"
        
        # Gets data from logger
        _graph:environment.EnvironmentGraph = kwargs.get('graph')
        _frame:int = kwargs.get('frame')
        
        _current_frame_counts = [0] * self.vacc_levels
        _pop_template = PopTemplate()
        
        # Gets number of vaccinated ler level
        for lvl in range(self.vacc_levels):
            _pop_template.set_traceable_property('vaccine_level', lvl)
            for node in _graph.node_list:
                _current_frame_counts[lvl] += node.get_population_size(_pop_template)
        
        # Output string/row
        _row = f"{_frame};{_frame % self.day_duration};{_frame//self.day_duration}"
        for lvl in range(self.vacc_levels):
            _row += ";" + str(_current_frame_counts[lvl])
        for lvl in range(self.vacc_levels):
            _row += ";" + str(_current_frame_counts[lvl] - self.last_frame[lvl])
        _row+= "\n"
        
        self.last_frame = _current_frame_counts
        self.log_file_vacc.write(_row)
        
    def stop_logger(self, **kwargs):
        self.log_file_vacc.close()
