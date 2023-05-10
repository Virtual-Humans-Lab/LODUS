#encoding: utf-8
import sys
sys.path.append('./Plugins/')

import argparse
import environment
from util import *
from data_parse_util import *
import population

from random_inst import FixedRandom

from ExamplePlugin import ExamplePlugin

from pathlib import Path

import time

arg_parser = argparse.ArgumentParser(description="Population Dynamics Simulation.")
arg_parser.add_argument('--f', metavar="F", type=str, default = '', help='Simulation file.')
args = vars(arg_parser.parse_args())

FixedRandom()
'''
Data Loading
'''
data_input_file_path = args['f']
env_graph = generate_EnvironmentGraph(data_input_file_path)

'''
Parameters
'''
#how many steps each day has
days = 3
day_duration = 24
env_graph.routine_cycle_length = day_duration

simulation_steps = days * day_duration

'''
Load Plugins Examples
'''
plug = ExamplePlugin(env_graph)
plug.example_parameter = 'bar'

env_graph.load_time_action_plugin(plug)

'''
Simulation
'''

for i in range(simulation_steps):
    print(i, end='\r')

    # Routine/Repeating Global Action Invoke example
    # Updates Node Routines and Repeating Global Actions
    # These are defined in the input environment descriptor
    env_graph.update_time_step(i % day_duration, i)

    # Direct Action Invoke example
    # if i == 50:
    #     dummy_action = TimeAction('push_population', {'region':'example1', 'node':'example2', 'quantity':50})
    #     env_graph.direct_action_invoke(dummy_action)
    
    # Next frame queue action example
    # if i == 60:
    #     dummy_action = TimeAction('push_population', {'region':'example1', 'node':'example2', 'quantity':50})
    #     env_graph.queue_next_frame_action(dummy_action)
