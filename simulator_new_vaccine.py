#encoding: utf-8
import sys
sys.path.append('./Plugins/')

import argparse
import environment
from util import *
from data_parse_util import *
import population

from random_inst import FixedRandom

from GatherPopulationNewPlugin import GatherPopulationNewPlugin
from ReturnPopulationPlugin import ReturnPopulationPlugin
from ReturnToPrevious import ReturnToPreviousPlugin
from ReverseSocialIsolationPlugin import ReverseSocialIsolationPlugin
from VaccineLocalPlugin import VaccinePlugin
from ExamplePlugin import ExamplePlugin

from simulation_logger import SimulationLogger
from pathlib import Path

import time

arg_parser = argparse.ArgumentParser(description="Population Dynamics Simulation.")
arg_parser.add_argument('--f', metavar="F", type=str, default = '', help='Simulation file.')
arg_parser.add_argument('--r', metavar="R", type=float, default = 0, help='R')
arg_parser.add_argument('--n', metavar="N", type=str, default = None, help='Experiment Name.')
arg_parser.add_argument('--v', metavar="V", type=str, default = "DataInput/vaccine_data.csv", help='Number of vaccinated people each day (.csv)')
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
days = 5
day_duration = 24
env_graph.routine_day_length = day_duration

simulation_steps = days * day_duration

'''
Load Plugins Examples
'''
plug = ExamplePlugin(env_graph)
plug.example_parameter = 'bar'
env_graph.LoadPlugin(plug)

gather_pop = GatherPopulationNewPlugin(env_graph, isolation_rate = 0.0)
gather_pop.iso_mode = 'regular'
env_graph.LoadPlugin(gather_pop)

return_plugin = ReturnPopulationPlugin(env_graph)
env_graph.LoadPlugin(return_plugin)

return_to_prev = ReturnToPreviousPlugin(env_graph)
env_graph.LoadPlugin(return_to_prev)

#social_distance = ReverseSocialIsolationPlugin(env_graph, '', isolation_rate = float(args['r']))
#social_distance.day_cycle = day_duration
#social_distance.iso_mode = 'regular'
#env_graph.LoadPlugin(social_distance)

vaccine_plugin = VaccinePlugin(env_graph, args['v'], day_duration, 0, multiplier=1.0)
env_graph.LoadPlugin(vaccine_plugin)

'''
Logging
'''

logger = SimulationLogger(f'{args["n"]}', day_duration)

logger.set_to_record('global')
logger.set_to_record('neighbourhood')
#logger.set_to_record('neighbourhood_disserta')
#logger.set_to_record('metrics')
logger.set_to_record('nodes')
#logger.set_to_record('positions')

pop_temp = PopTemplate()
#pop_temp.set_property('age', 'adults')
logger.pop_template = pop_temp
# logger.foreign_only = True
# this option saves REALLY big files
# logger.set_to_record('graph')

'''
Simulation
'''

for i in range(simulation_steps):
    print(i, end='\r')

    if i % day_duration == 0:
        vaccine_plugin.update_time_step(i % day_duration, i)

    # Routine/Repeating Global Action Invoke example
    # Updates Node Routines and Repeating Global Actions
    # These are defined in the input environment descriptor
    env_graph.update_time_step(i % day_duration, i)

    logger.record_frame(env_graph, i)
    # Direct Action Invoke example
    # if i == 50:
    #     dummy_action = TimeAction('push_population', {'region':'example1', 'node':'example2', 'quantity':50})
    #     env_graph.direct_action_invoke(dummy_action)
    
    # Next frame queue action example
    # if i == 60:
    #     dummy_action = TimeAction('push_population', {'region':'example1', 'node':'example2', 'quantity':50})
    #     env_graph.queue_next_frame_action(dummy_action)
logger.close()