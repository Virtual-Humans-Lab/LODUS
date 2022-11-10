#encoding: utf-8
import sys
sys.path.append('./Plugins/')

import argparse

import environment
from util import *
from data_parse_util import *
import population

from AgentBasedPlugin import AgentBasedPlugin
from InfectionPlugin import InfectionPlugin
from SocialIsolationPlugin import SocialIsolationPlugin
from ReverseSocialIsolationPlugin import ReverseSocialIsolationPlugin
from GatherPopulationPlugin import GatherPopulationPlugin

from Loggers.population_count_logger import PopulationCountLogger


arg_parser = argparse.ArgumentParser(description="Population Dynamics Simulation.")
arg_parser.add_argument('-infection_mode', '--i', metavar='I', type=int, default = 0, help='The type of infection module to use. 0 is rate based, 1 is day based.')
arg_parser.add_argument('-isolation_mode', '--s', metavar="S", type=int, default = 0, help='Social isolation. Reduces movement according to a table. 0 is no social isolation. 1 is table based social isolation.')
arg_parser.add_argument('--f', metavar="F", type=str, default = '', help='Simulation file.')
args=  vars(arg_parser.parse_args())

print(args)

'''
Parameters
'''

## how many steps to run for, days * day_duration
simulation_steps = 30 * 24

simulation_hours =  [7,8,18,19]

#how many steps each day has
day_duration = 24

'''
Data Loading stuff
'''
# environment_path = 'DataInput\\ProofSixNeighborhoods.json'
# environment_path = 'DataInput\\ProofSixNeighborhoods2.json'
environment_path = 'DataInput\\ProofSixNeighborhoods3.json'
# environment_path = 'DataInput\\dummy_input_4.json'

if 'f' in args:
    environment_path = args['f']

env_graph = generate_EnvironmentGraph(environment_path)
social_table_path = 'DataInput/PortoAlegreOutput_semicolon_avg.csv'

'''
Load Plugins
'''
# env_graph.LoadPlugin(AgentBasedPlugin(env_graph))

###infection plugin
# inf_plugin = InfectionPlugin(env_graph, infect_mode=args['i'] , use_infect_move_pop=False)
# inf_plugin.day_length = day_duration
# inf_plugin.home_density = 1
# inf_plugin.bus_density = 1
# inf_plugin.home_density = 1.0
# inf_plugin.bus_density = 1.0
# env_graph.LoadPlugin(inf_plugin)

if args['s'] == 0:
    gather_pop = GatherPopulationPlugin(env_graph, isolation_rate = 0.8)
    gather_pop.iso_mode = 'quantity_correction'
    env_graph.LoadPlugin(gather_pop)
elif args['s'] == 1:
    social_distance = SocialIsolationPlugin(env_graph, social_table_path)
    social_distance.day_cycle = day_duration
    social_distance.iso_mode = 'quantity_correction'
    env_graph.LoadPlugin(social_distance)
elif args['s'] == 2:
    social_distance = ReverseSocialIsolationPlugin(env_graph, social_table_path, isolation_rate = 0.2)
    social_distance.day_cycle = day_duration
    social_distance.iso_mode = 'random_nudge'
    #social_distance.iso_mode = 2
    env_graph.LoadPlugin(social_distance)

'''
Logging
'''
basename = environment_path.split('\\')[-1].split('.')[0]

logger = PopulationCountLogger(f'{basename}-infection_data-i{str(args["i"])}-s{str(args["s"])}-fixed_20', day_duration)

logger.set_data_to_record('global')
logger.set_data_to_record('neighbourhood')
#logger.set_to_record('graph')

'''
Simulation
'''

for i in range(28):

    for hour in simulation_hours:
        print(hour + i * (24 * 7), end='\r')

        env_graph.update_time_step(hour, hour + i * (24 * 7))
        
        logger.log_simulation_step(env_graph, hour + i * (24 * 7))


'''
Logging
'''

logger.close()