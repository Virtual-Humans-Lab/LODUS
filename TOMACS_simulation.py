#encoding: utf-8
import sys

sys.path.append('./Plugins/')
from Loggers.characteristic_change_logger import CharacteristicChangeLogger
from Loggers.od_matrix_logger import ODMovementRecordKey, ODMatrixLogger
from Loggers.vaccine_level_logger import VaccineLevelLogger
from Loggers.population_count_logger import PopulationCountRecordKey, PopulationCountLogger
from Loggers.blob_count_logger import BlobCountLogger, BlobCountRecordKey

import argparse
import environment
from util import *
from data_parse_util import *
import population

from random_inst import FixedRandom

from MovePopulationPlugin import MovePopulationPlugin
from GatherPopulationPlugin import GatherPopulationPlugin
from ReturnPopulationHomePlugin import ReturnPopulationHomePlugin
from SendPopulationBackPlugin import SendPopulationBackPlugin
from ReturnToPrevious import ReturnToPreviousPlugin
from LevyWalkPlugin import LevyWalkPlugin
from ReverseSocialIsolationPlugin import ReverseSocialIsolationPlugin
from VaccineLocalPlugin import VaccinePlugin
from NewInfectionPlugin import NewInfectionPlugin
from NodeDensityPlugin import NodeDensityPlugin
from CustomTimeActionPlugin import CustomTimeActionPlugin

from pathlib import Path

import time

arg_parser = argparse.ArgumentParser(description="Population Dynamics Simulation.")
arg_parser.add_argument('--f', metavar="F", type=str, default = '', help='Simulation file.')
arg_parser.add_argument('--e', metavar="E", type=str, default = None, help='Experiment Configuration File.')
arg_parser.add_argument('--r', metavar="R", type=float, default = 0, help='R')
arg_parser.add_argument('--n', metavar="N", type=str, default = None, help='Experiment Name.')
arg_parser.add_argument('--c', metavar="C", type=str, default = ".\DataInput\CustomTimeActions.json", help='Custom Time Actions Configuration File (.json)')
arg_parser.add_argument('--d', metavar="D", type=str, default = ".\DataInput\\NodeDensities.json", help='Node Densities Configuration File (.json)')
arg_parser.add_argument('--v', metavar="V", type=str, default = ".\DataInput\VaccinePluginSetup.json", help='Vaccine Plugin Configuration File (.json)')
arg_parser.add_argument('--i', metavar="I", type=str, default = ".\DataInput\SIRPluginSetup.json", help='SIR Plugin Configuration File (.json)')
args = vars(arg_parser.parse_args())

FixedRandom()
'''
Data Loading
'''
data_input_file_path = args['f']
experiment_configuration_file = args['e']
if ".json" in args['f']: 
    env_graph = generate_EnvironmentGraph(data_input_file_path)
else:
    env_graph = Generate_EnvironmentGraph(experiment_configuration_file)
'''
Parameters
'''
# How many steps each cycle has. Ex: a day (cycle) with 24 hours (length)
cycles = 1
cycle_length = 24
env_graph.routine_cycle_length = cycle_length
simulation_steps = cycles * cycle_length
env_graph.experiment_name = args["n"]

print("node count", len(env_graph.node_list))
'''
Load Plugins Examples
'''

move_population_plugin = MovePopulationPlugin(env_graph)
env_graph.LoadPlugin(move_population_plugin)

gather_pop = GatherPopulationPlugin(env_graph, isolation_rate = 0.0)
gather_pop.iso_mode = 'regular'
env_graph.LoadPlugin(gather_pop)

return_pop_home_plugin = ReturnPopulationHomePlugin(env_graph)
env_graph.LoadPlugin(return_pop_home_plugin)

send_pop_back_plugin = SendPopulationBackPlugin(env_graph)
env_graph.LoadPlugin(send_pop_back_plugin)

return_to_prev = ReturnToPreviousPlugin(env_graph)
env_graph.LoadPlugin(return_to_prev)

levy_walk = None
if 'levy_walk_plugin' in env_graph.experiment_config:
    levy_walk = LevyWalkPlugin(env_graph)
    env_graph.LoadPlugin(levy_walk)

#social_distance = ReverseSocialIsolationPlugin(env_graph, '', isolation_rate = float(args['r']))
#social_distance.day_cycle = day_duration
#social_distance.iso_mode = 'regular'
#env_graph.LoadPlugin(social_distance)


density_plugin = NodeDensityPlugin(env_graph, args['d'])
env_graph.LoadPlugin(density_plugin)

#custom_action_plugin = CustomTimeActionPlugin(env_graph, args['c'])
#env_graph.LoadPlugin(custom_action_plugin)

#vaccine_plugin = VaccinePlugin(env_graph, args['v'], cycle_length)
#env_graph.LoadPlugin(vaccine_plugin)

#infection_plugin = NewInfectionPlugin(env_graph, args['i'], cycle_length)
#env_graph.LoadPlugin(infection_plugin)

'''
Logging
'''

pop_count_logger = PopulationCountLogger(f'{args["n"]}', env_graph, cycle_length)
pop_count_logger.data_to_record = [PopulationCountRecordKey.POPULATION_COUNT_GLOBAL,
                                    PopulationCountRecordKey.POPULATION_COUNT_REGION,
                                    PopulationCountRecordKey.POPULATION_COUNT_NODE]
#logger.set_to_record('neighbourhood_disserta')
#logger.set_to_record('metrics')
#logger.set_to_record('positions')

blob_count_logger = BlobCountLogger(f'{args["n"]}')
blob_count_logger.data_to_record = [BlobCountRecordKey.BLOB_COUNT_GLOBAL,
                                    BlobCountRecordKey.BLOB_COUNT_REGION,
                                    BlobCountRecordKey.BLOB_COUNT_NODE]


pop_temp = PopTemplate()
#pop_temp.set_property('age', 'adults')
pop_count_logger.pop_template = pop_temp
# logger.foreign_only = True
# this option saves REALLY big files
# logger.set_to_record('graph')
# logger.set_pluggin_to_record(infection_plugin)
# logger.set_pluggin_to_record(vaccine_plugin)

# CharacteristicChange logger
traceable_logger = CharacteristicChangeLogger(f'{args["n"]}')

# OD-Matrix logger
od_logger = ODMatrixLogger(f'{args["n"]}')
od_logger.data_to_record = [ODMovementRecordKey.REGION_TO_REGION,
                            ODMovementRecordKey.NODE_TO_NODE]

# Age tracking
od_logger.region_custom_templates["age: [children]"] = PopTemplate(sampled_properties={"age": "children"})
#od_logger.region_custom_templates["age: [youngs]"] = PopTemplate(sampled_properties={"age": "youngs"})
od_logger.region_custom_templates["age: [adults]"] = PopTemplate(sampled_properties={"age": "adults"})
od_logger.region_custom_templates["age: [elders]"] = PopTemplate(sampled_properties={"age": "elders"})

# Occupation tracking
#od_logger.region_custom_templates["occupation: [other]"] = PopTemplate(sampled_properties={"occupation": "other"})
od_logger.region_custom_templates["occupation: [student]"] = PopTemplate(sampled_properties={"occupation": "student"})
od_logger.region_custom_templates["occupation: [worker]"] = PopTemplate(sampled_properties={"occupation": "worker"})
od_logger.node_custom_templates["occupation: [worker]"] = PopTemplate(sampled_properties={"occupation": "worker"})
#----------------------------

# Vaccine Logger
#vacc_logger = VaccineLevelLogger(f'{args["n"]}', env_graph, day_duration)

'''
Simulation
'''

env_graph.LoadLoggerPlugin(pop_count_logger)
env_graph.LoadLoggerPlugin(od_logger)
env_graph.LoadLoggerPlugin(blob_count_logger)
#env_graph.LoadLoggerPlugin(traceable_logger)
#env_graph.LoadLoggerPlugin(vacc_logger)
#print("Loaded TimeAction Plugins: " + str([type(tap) for tap in env_graph.loaded_logger_plugins]))
#print("Loaded Logger Plugins: " + str([type(lp) for lp in env_graph.loaded_logger_plugins]))
env_graph.start_logging()

start_time = time.perf_counter()
for i in range(simulation_steps):
    print(i, end='\r')
        
    #infection_plugin.update_time_step(i % day_duration, i)

    #if i % day_duration == 0:
    #    vaccine_plugin.update_time_step(i % day_duration, i)

    # Routine/Repeating Global Action Invoke example

    # Updates Node Routines and Repeating Global Actions
    # These are defined in the input environment descriptor
    env_graph.update_time_step(i % cycle_length, i)

    # Log current simulation step
    env_graph.log_simulation_step()
    
    #if len(env_graph.region_dict["Azenha"].get_node_by_name("pharmacy").contained_blobs) > 0:
    #    print(env_graph.region_dict["Azenha"].get_node_by_name("pharmacy").contained_blobs[0].traceable_properties)
    

#logger.compute_composite_data(env_graph, simulation_steps)

#logger.stop_logging(show_figures=False, export_figures=False, export_html=True)
# od_logger.stop_logging()

end_time = time.perf_counter()
env_graph.stop_logging()


#print("Gather population execution times")
#print(gather_pop.execution_times)
if levy_walk is not None: levy_walk.print_execution_time_data()
gather_pop.print_execution_time_data()
return_pop_home_plugin.print_execution_time_data()
send_pop_back_plugin.print_execution_time_data()
return_to_prev.print_execution_time_data()
move_population_plugin.print_execution_time_data()

print("Total Simulation time")
print(end_time - start_time)
print("Average Cycle time")
print((end_time - start_time)/cycles)

print(env_graph.time_action_map.keys())

#test_file = open("demofile2.txt", "a")
#test_file.write(str(env_graph.time_action_map['move_population']))
#test_file.close()
#test_file = open("demofile21.txt", "a")
#test_file.write(str(env_graph.time_action_map['gather_population']))
#test_file.close()