#encoding: utf-8
#python .\simplest_simulator.py --f .\DataInput\NT_13_Routines.json
import sys
sys.path.append('./Plugins/')

import argparse
import environment
from util import *
from data_parse_util import *
import population

from random_inst import FixedRandom

from ExamplePlugin import ExamplePlugin

from AgentBasedPlugin import AgentBasedPlugin
#from InfectionPlugin import InfectionPlugin
from SocialIsolationPlugin import SocialIsolationPlugin
from GatherPopulationPlugin import GatherPopulationPlugin
from ReverseSocialIsolationPlugin import ReverseSocialIsolationPlugin
from ReturnPopulationHomePlugin import ReturnPopulationHomePlugin
from LevyWalkLegacyPlugin import LevyWalkLegacyPlugin


from pathlib import Path

import time

arg_parser = argparse.ArgumentParser(description="Population Dynamics Simulation.")
arg_parser.add_argument('--f', metavar="F", type=str, default = '', help='Simulation file.')
arg_parser.add_argument('--n', metavar="N", type=str, default = None, help='Experiment Name.')
arg_parser.add_argument('--l', metavar="L", type=float, default = 0, help='L.')
arg_parser.add_argument('--s', metavar="S", type=int, default = 0, help='S')
arg_parser.add_argument('--r', metavar="R", type=float, default = 0, help='R')

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

env_graph.LoadPlugin(plug)



walk = LevyWalkLegacyPlugin(env_graph)
walk.distribution_scale = int(args['s'])
walk.levy_probability = float(args['l'])
env_graph.LoadPlugin(walk)

social_distance = ReverseSocialIsolationPlugin(env_graph, '', isolation_rate = float(args['r']))
social_distance.day_cycle = day_duration
social_distance.iso_mode = 'regular'
env_graph.LoadPlugin(social_distance)


return_plugin = ReturnPopulationHomePlugin(env_graph)
env_graph.LoadPlugin(return_plugin)



'''
Logging
'''

logger = PopulationCountLogger(f'{args["n"]}', day_duration)

#logger.set_to_record('global')
#logger.set_to_record('neighbourhood')
logger.set_data_to_record('neighbourhood_disserta')
logger.set_data_to_record('metrics')
#logger.set_to_record('nodes')
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
    # print(i)
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
    logger.record_frame(env_graph, i)
