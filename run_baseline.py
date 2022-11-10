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
from InfectionVaccinePlugin import InfectionVaccinePlugin
from SocialIsolationPlugin import SocialIsolationPlugin
from GatherPopulationPlugin import GatherPopulationPlugin
from ReverseSocialIsolationPlugin import ReverseSocialIsolationPlugin
from ReturnPopulationPlugin import ReturnPopulationPlugin
from LevyWalkPlugin import LevyWalkPlugin

from Loggers.population_count_logger import PopulationCountLogger
from pathlib import Path

import time

arg_parser = argparse.ArgumentParser(description="Population Dynamics Simulation.")
arg_parser.add_argument('-mobility_mode', '--m', metavar="M", type=int, default = 0, help='Mobility operation. 0 is distance based gathering. 1 is table based gathering. 2 is table and distance based pushing.')
arg_parser.add_argument('-infection_mode', '--i', metavar='I', type=int, default = 0, help='The type of infection module to use. 0 ignores infection, otherwise infection is used.')
arg_parser.add_argument('--f', metavar="F", type=str, default = '', help='Simulation file.')
arg_parser.add_argument('--s', metavar="S", type=int, default = None, help='Simulation Seed.')
arg_parser.add_argument('--b', metavar="B", type=str, default = 'DataInput/beta_history/bh.csv', help='Estimated beta history file (.csv)')
arg_parser.add_argument('--v', metavar="V", type=str, default = 'DataInput/vaccine_data.csv', help='Number of vaccinated people each day (.csv)')
args = vars(arg_parser.parse_args())


FixedRandom()


'''
Data Loading stuff
'''

if 'f' in args:
    environment_path = args['f']
else:
    raise Exception('Environment path missing. Use "python run_baseline.py -f <environment_file>.json."')
env_graph = generate_EnvironmentGraph(environment_path)
social_table_path = 'DataInput\Isolation_01_Mar_2020_To_20_Jan_2021\PortoAlegre_Isolation_01Mar2020_20Jan2021_semicolon_avg_extended.csv'


'''
Parameters
'''
#how many steps each day has
days = 407
day_duration = 24
env_graph.routine_day_length = day_duration

## how many steps to run for, days * day_duration
simulation_steps = days * day_duration

'''
Data Loading stuff
'''
# This is to load real contagion data.

# Load (calibrated) beta history file
print('Beta history will be read from file: ', args['b'])

betaHistory = list()
dayHistory = list()
errorHistory = list()
gammaHistory = list()
try:
	betaHistoryReader = open(args['b'], "r")
	line = betaHistoryReader.readline()
	historyLines = betaHistoryReader.readlines()
	for line in historyLines:
		s = line.split(";")
		d = int(s[0])
		b = float(s[1])
		g = float(s[2])
		e = float(s[3])
		dayHistory.append(d)
		betaHistory.append(b)
		gammaHistory.append(g)
		errorHistory.append(e)
except Exception:
	print('Beta history file not found. Will now estimated beta from start.')

print(f'beta history size: {len(betaHistory)}')
# Load real vaccine data
print('Vaccination history will be read from file: ', args['v'])
inputVaccineData = open(args['v'], "r")
vaccine_data = list()
for v in inputVaccineData:
	vaccine_data.append(v)

print("Number of days in vaccine data:", len(vaccine_data))

'''
Load Plugins Examples
'''
###infection plugin
# infection mode 0 skips infection
if args['i'] != 0:
    inf_plugin = InfectionVaccinePlugin(env_graph, use_infect_move_pop=False, day_length = day_duration)
    inf_plugin.home_density, inf_plugin.bus_density, inf_plugin.home_density, inf_plugin.bus_density = 1, 1, 1.0, 1.0
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
    #Path(f'{basename}-i{str(args["i"])}-m{str(args["m"])}').mkdir(parents=True,
    #exist_ok=True)
    logger = PopulationCountLogger(f'{basename}-i{str(args["i"])}-m{str(args["m"])}', day_duration)
else:
    #Path(f'{basename}-m{str(args["m"])}').mkdir(parents=True, exist_ok=True)
    logger = PopulationCountLogger(f'{basename}-m{str(args["m"])}', day_duration)

logger.set_data_to_record('global')
logger.set_data_to_record('neighbourhood')

pop_temp = PopTemplate()
logger.pop_template = pop_temp

'''
Simulation
'''

t = time.time()

for i in range(simulation_steps):
    #print(i, end='\r')
    hour = i % day_duration
    day = int(i/day_duration)

    print(f'step:{i}\thour:{hour}\tday:{day}')

    # Get estimated beta and gamma for today:
    if hour == 0:
        inf_plugin.beta = betaHistory.pop(0)
        inf_plugin.gamma = gammaHistory.pop(0)

    # Routine/Repeating Global Action Invoke example
    # Updates Node Routines and Repeating Global Actions
    # These are defined in the input environment descriptor
    # print(f'{sum([region.get_population_size() for region in
    # env_graph.region_list])}\n\n') no one gets lost
    env_graph.update_time_step(hour, i)

    # records frame I data
    logger.log_simulation_step(env_graph, i)


print(time.time() - t)

'''
Logging
# '''

logger.close()