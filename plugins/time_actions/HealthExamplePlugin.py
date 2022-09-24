from itertools import count
from types import NoneType
from VaccineLocalPlugin import VaccinePlugin
import environment
from population import PopTemplate
import copy
from random_inst import FixedRandom
import math
import numpy as np
import csv
from simulation_logger import SimulationLogger
import util
import json

class HealthExamplePlugin(environment.TimeActionPlugin):
    '''
    This Plugin implements ..... 

    '''

    def __init__(self, env_graph: environment.EnvironmentGraph, config_file_path, day_duration: int):

        super().__init__()
        
        # Set the time/frame variables
        self.day_duration = day_duration
        self.hour = 0
        self.time = 0
        self.current_day = 0

        #, default_beta = 0.25, default_gamma = 0.08
        # Sets the 'infect' action
        self.graph = env_graph

        self.set_pair('health_call', self.healthy_call_example)
        #self.graph.base_actions.add('health_call')

        # Sets a traceable properties for all blobs in the simulation
        self.graph.add_blobs_traceable_property("health_status", 'total')
        
        print("original Pop", self.graph.get_population_size())
        
        # Sets a number of infected people in the start of the simulation
        # for _name, _node in self.graph.node_dict.items():
        #     #print(_node.get_unique_name() + str(_node.get_population_size()))
        #     if _node.get_unique_name() == "Azenha//home":
        #         print("Azenha Antes")
        #         for _b in _node.contained_blobs:
        #             print(_b.verbose_str())   

        # JSON file containing the configuration of the Infection Plugin
        with open(config_file_path, newline='', encoding='utf-8') as csvfile:
            healty_count = csv.reader(csvfile, delimiter=',', quotechar='|')
            next(healty_count)
            for row in healty_count:
                _target_node = self.graph.get_region_by_name(row[0]).get_node_by_name("home")
                _target_node.change_blobs_traceable_property('health_status', 'attendance', int(row[1]))

        # for _name, _node in self.graph.node_dict.items():
        #     #print(_node.get_unique_name() + str(_node.get_population_size()))
        #     if _node.get_unique_name() == "Azenha//home":
        #         print("Azenha Depois")
        #         for _b in _node.contained_blobs:
        #             print(_b.verbose_str())       
 
        print("final Pop", self.graph.get_population_size())
        
        # Sets PopTemplates to be used later
        self.pt_healthy = PopTemplate()
        self.pt_healthy.set_traceable_property("health_status", 'total')
        self.pt_sick = PopTemplate()
        self.pt_sick.set_traceable_property("health_status", 'attendance')
    
        print("initially total:", self.graph.get_population_size(self.pt_healthy))
        print("initially attendance:", self.graph.get_population_size(self.pt_sick))


    def update_time_step(self, hour, time):
        # Updates time step data
        self.hour = hour
        self.time = time
        self.day = (time // self.day_duration) 
        print(self.time, self.hour, self.day)


    def healthy_call_example(self, values, hour, time):
        
        assert ('region' in values and isinstance(values['region'], str), "No 'region' value defined")
        assert ('node' in values and isinstance(values['node'], str), "No 'node' value defined")
        #assert ('frames' in values or 'cycle_length' in values)
        

        #print("TimeAction de um Plugin", hour, time, values)
        # Gets the target region and node
        region = self.graph.get_region_by_name(values['region'])
        node = region.get_node_by_name(values['node'])

        print(node.get_unique_name(), "sick population:", node.get_population_size(self.pt_sick))
        #if node.get_population_size() == 0: return

        
        new_action_values = {}
        new_action_type = 'gather_population'
        new_action_values['region'] = region.name
        new_action_values['node'] = node.name
        new_action_values['quantity'] = 10
        new_action_values['different_node_name'] = "true"
        
        pop_template = PopTemplate()
        pop_template.set_traceable_property('health_status', "sick")
        new_action_values['population_template'] = pop_template
        
        new_action = environment.TimeAction(_type = new_action_type, _values = new_action_values)
        #self.graph.direct_action_invoke(new_action, hour, time)

        return [new_action]