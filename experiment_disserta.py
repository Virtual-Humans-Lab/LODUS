#encoding: utf-8
import sys
sys.path.append('./Plugins/')

import argparse

import environment
from util import *
from data_parse_util import *
import population

from random_inst import FixedRandom

from AgentBasedPlugin import AgentBasedPlugin
from InfectionPlugin import InfectionPlugin
from SocialIsolationPlugin import SocialIsolationPlugin
from GatherPopulationPlugin import GatherPopulationPlugin
from ReverseSocialIsolationPlugin import ReverseSocialIsolationPlugin
from ReturnPopulationPlugin import ReturnPopulationPlugin
from LevyWalkPlugin import LevyWalkPlugin

from simulation_logger import SimulationLogger
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
# FixedRandom()


'''
Data Loading stuff
'''

if 'f' in args:
    environment_path = args['f']

env_graph = generate_EnvironmentGraph(environment_path)


'''
Parameters
'''
#how many steps each day has
days = 7
day_duration = 24
env_graph.routine_day_length = day_duration

## how many steps to run for, days * day_duration
simulation_steps = days * day_duration

'''
Load Plugins Examples
'''

walk = LevyWalkPlugin(env_graph)
walk.distribution_scale = int(args['s'])
walk.levy_probability = float(args['l'])
env_graph.LoadPlugin(walk)

social_distance = ReverseSocialIsolationPlugin(env_graph, '', isolation_rate = float(args['r']))
social_distance.day_cycle = day_duration
social_distance.iso_mode = 'regular'
env_graph.LoadPlugin(social_distance)


return_plugin = ReturnPopulationPlugin(env_graph)
env_graph.LoadPlugin(return_plugin)


'''
Logging
'''

logger = SimulationLogger(f'{args["n"]}', day_duration)

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

t = time.time()


# worker_temp = PopTemplate()
# worker_temp.set_property('occupation', 'worker') 
# worker_temp.mother_blob_id = env_graph.get_region_by_name("Centro").id

for i in range(simulation_steps):
    print(i, end='\r')

    # Routine/Repeating Global Action Invoke example
    # Updates Node Routines and Repeating Global Actions
    # These are defined in the input environment descriptor
    # print(f'{sum([region.get_population_size() for region in env_graph.region_list])}\n\n') no one gets lost
    env_graph.update_time_step(i % day_duration, i)

    # Direct Action Invoke example
    # if i == 50:
    #     dummy_action = TimeAction('push_population', {'region':'example1', 'node':'example2', 'quantity':50})
    #     env_graph.direct_action_invoke(dummy_action)
    
    # Next frame queue action example
    # if i == 60:
    #     dummy_action = TimeAction('push_population', {'region':'example1', 'node':'example2', 'quantity':50})
    #     env_graph.queue_next_frame_action(dummy_action)


    # records frame I data
    logger.record_frame(env_graph, i)


print(time.time() - t)

# with open("distances.txt", 'w') as f:
#     for k, v in walk.dist_dict.items():
#         f.write(f'{k}\n')
#         for i in v:
#             f.write(f'{i[0]}\n')


'''
Logging
# '''
# dist = walk.get_node_distance_matrix()
# mat = logger.complete_od_matrix(dist)
# mat = logger.divide_od_matrix_by_scalar(mat, 1.0)
# mat = logger.normalize_od_matrix(mat)

# with open("node_distances.txt", 'w', encoding='utf-8') as mat_file:
#     logger.write_od_matrix(mat, mat_file)

# dist = walk.get_region_distance_matrix()
# mat = logger.complete_od_matrix(dist)
# mat = logger.divide_od_matrix_by_scalar(mat, 1.0)
# mat = logger.normalize_od_matrix(mat)

# with open("region_distances.txt", 'w', encoding='utf-8') as mat_file:
#     logger.write_od_matrix(mat, mat_file)


logger.compute_composite_data(env_graph, simulation_steps)
logger.close()