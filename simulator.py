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

from Loggers.population_count_logger import PopulationCountLogger
from pathlib import Path

import time

arg_parser = argparse.ArgumentParser(description="Population Dynamics Simulation.")
arg_parser.add_argument('-infection_mode', '--i', metavar='I', type=int, default = 0, help='The type of infection module to use. 0 is rate based, 1 is day based.')
arg_parser.add_argument('-mobility_mode', '--m', metavar="M", type=int, default = 0, help='Mobility operation. 0 is distance based gathering. 1 is table based gathering. 2 is table and distance based pushing.')
arg_parser.add_argument('--f', metavar="F", type=str, default = '', help='Simulation file.')
arg_parser.add_argument('--s', metavar="S", type=int, default = None, help='Simulation Seed.')
args = vars(arg_parser.parse_args())


# FixedRandom(args['s'])
FixedRandom()


'''
Data Loading stuff
'''
# environment_path = 'DataInput\\ProofSixNeighborhoods.json'
# environment_path = 'DataInput\\ProofSixNeighborhoods2.json'
environment_path = 'DataInput\\ProofSixNeighborhoods3.json'
# environment_path = 'DataInput\\dummy_input_4.json'

if 'f' in args:
    environment_path = args['f']

print(f'Loading environment graph: {environment_path}')
env_graph = generate_EnvironmentGraph(environment_path)
social_table_path = 'DataInput/PortoAlegreOutput_semicolon_avg-name_fix.csv'


'''
Parameters
'''
#how many steps each day has
days = 7
day_duration = 24
env_graph.routine_cycle_length = day_duration

## how many steps to run for, days * day_duration
simulation_steps = days * day_duration

'''
Load Plugins Examples
'''
###infection plugin
# infection mode 0 skips infection
if args['i'] != 0:
    inf_plugin = InfectionPlugin(env_graph, infect_mode=args['i'] , use_infect_move_pop=False)
    inf_plugin.day_length = day_duration
    inf_plugin.home_density, inf_plugin.bus_density, inf_plugin.home_density, inf_plugin.bus_density  = 1, 1, 1.0, 1.0
    env_graph.LoadPlugin(inf_plugin)


if args['m'] == 0:
    gather_pop = GatherPopulationPlugin(env_graph, isolation_rate = 0.8)
    gather_pop.iso_mode = 'quantity_correction'
    env_graph.LoadPlugin(gather_pop)
elif args['m'] == 1:
    social_distance = SocialIsolationPlugin(env_graph, social_table_path)
    social_distance.day_cycle = day_duration
    social_distance.iso_mode = 'quantity_correction'
    env_graph.LoadPlugin(social_distance)
elif args['m'] == 2:
    social_distance = ReverseSocialIsolationPlugin(env_graph, social_table_path, isolation_rate = 0.2)
    social_distance.day_cycle = day_duration
    social_distance.iso_mode = 'regular'
    env_graph.LoadPlugin(social_distance)
elif args['m'] == 3:
    walk = LevyWalkPlugin(env_graph)
    walk.distribution_scale = 100
    walk.distribution_location = 0
    walk.mobility_scale = 100
    env_graph.LoadPlugin(walk)
elif args['m'] == 4:
    walk = LevyWalkPlugin(env_graph)
    walk.distribution_scale = 50
    walk.distribution_location = 0
    walk.mobility_scale = 10
    walk.levy_probability = 0.2
    env_graph.LoadPlugin(walk)

    social_distance = ReverseSocialIsolationPlugin(env_graph, '', isolation_rate = 0.3)
    social_distance.day_cycle = day_duration
    social_distance.iso_mode = 'regular'
    env_graph.LoadPlugin(social_distance)


return_plugin = ReturnPopulationPlugin(env_graph)
env_graph.LoadPlugin(return_plugin)


'''
Logging
'''
basename = environment_path.split('\\')[-1].split('.')[0]

if args['i'] != 0:
    #Path(f'{basename}-i{str(args["i"])}-m{str(args["m"])}').mkdir(parents=True, exist_ok=True)
    logger = PopulationCountLogger(f'{basename}-i{str(args["i"])}-m{str(args["m"])}', day_duration)
else:
    #Path(f'{basename}-m{str(args["m"])}').mkdir(parents=True, exist_ok=True)
    logger = PopulationCountLogger(f'{basename}-m{str(args["m"])}', day_duration)

logger.set_data_to_record('global')
logger.set_data_to_record('neighbourhood')
logger.set_data_to_record('neighbourhood_disserta')
logger.set_data_to_record('metrics')
logger.set_data_to_record('nodes')
logger.set_data_to_record('positions')

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


worker_temp = PopTemplate()
worker_temp.set_sampled_property('occupation', 'worker') 
worker_temp.mother_blob_id = env_graph.get_region_by_name("Centro").id
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
    logger.log_simulation_step(env_graph, i)


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