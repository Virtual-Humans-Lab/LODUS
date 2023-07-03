#encoding: utf-8
import sys
sys.path.append('./plugins/')

import argparse
import time
from pathlib import Path

from loggers.blob_count_logger import BlobCountLogger, BlobCountRecordKey
from loggers.characteristic_change_logger import CharacteristicChangeLogger
from loggers.movement_displacement_logger import MovementDisplacementLogger
from loggers.od_matrix_logger import ODMatrixLogger, ODMovementRecordKey
from loggers.population_count_logger import (PopulationCountLogger,
                                             PopulationCountRecordKey)
from loggers.levy_walk_sample_logger import LevyWalkSampleLogger

from loggers.infection_sum_logger import InfectionSumLogger
from loggers.vaccine_level_logger import VaccineLevelLogger
from routines.off_cycle_routine_plugin import OffCycleRoutinePlugin
from time_actions.custom_time_action_plugin import CustomTimeActionPlugin
from time_actions.gather_population_plugin import GatherPopulationPlugin
from time_actions.infection_plugin import InfectionPlugin
from time_actions.levy_walk_plugin import LevyWalkPlugin
from time_actions.move_population_plugin import MovePopulationPlugin
from time_actions.new_infection_plugin import NewInfectionPlugin
from data.node_density_data_plugin import NodeDensityDataPlugin
from time_actions.return_population_home_plugin import ReturnPopulationHomePlugin
from time_actions.return_to_previous_plugin import ReturnToPreviousPlugin
from time_actions.reverse_social_isolation_plugin import \
    ReverseSocialIsolationPlugin
from time_actions.send_population_back_plugin import SendPopulationBackPlugin
from time_actions.vaccine_plugin import VaccinePlugin
from data.global_isolation_data_plugin import GlobalIsolationDataPlugin
from data.global_infection_data_plugin import GlobalInfectionDataPlugin

import environment
import population
from data_parse_util import *
from random_inst import FixedRandom
from util import *
import numpy as np

arg_parser = argparse.ArgumentParser(description="Population Dynamics Simulation.")
arg_parser.add_argument('--f', metavar="F", type=str, default = '', help='Simulation file.')
arg_parser.add_argument('--e', metavar="E", type=str, default = None, help='Experiment Configuration File.')
arg_parser.add_argument('--r', metavar="R", type=float, default = 0, help='R')
arg_parser.add_argument('--n', metavar="N", type=str, default = None, help='Experiment Name.')
arg_parser.add_argument('--c', metavar="C", type=str, default = ".\\DataInput\\CustomTimeActions.json", help='Custom Time Actions Configuration File (.json)')
arg_parser.add_argument('--d', metavar="D", type=str, default = ".\\DataInput\\NodeDensities.json", help='Node Densities Configuration File (.json)')
arg_parser.add_argument('--v', metavar="V", type=str, default = ".\\DataInput\\VaccinePluginSetup.json", help='Vaccine Plugin Configuration File (.json)')
arg_parser.add_argument('--i', metavar="I", type=str, default = ".\\DataInput\\SIRPluginSetup.json", help='SIR Plugin Configuration File (.json)')
args = vars(arg_parser.parse_args())

FixedRandom(seed=0, numpy_seed=0)

output_str = ""

'''
Data Loading
'''
data_input_file_path = args['f']
experiment_configuration_file = args['e']
if ".json" in args['f']: 
    raise Exception("please use the new format of inputs (experiment config)")
env_graph = Generate_EnvironmentGraph(experiment_configuration_file)
'''
Parameters
'''
# How many steps each cycle has. Ex: a day (cycle) with 24 hours (length)
cycles:int = 1
cycle_length:int = 24
env_graph.routine_cycle_length = cycle_length
simulation_steps = cycles * cycle_length

env_graph.experiment_name = args["n"] if args["n"] is not None else args["e"]
print("Creating experiment:", env_graph.experiment_name)
print("EnvNode Count", len(env_graph.node_list))

'''
Data Plugins
'''

isolation_data = None
if 'global_isolation_data_plugin' in env_graph.experiment_config:
    isolation_data = GlobalIsolationDataPlugin(env_graph)
    env_graph.load_time_action_plugin(isolation_data)

infection_data = None
if 'global_infection_data_plugin' in env_graph.experiment_config:
    isolation_data = GlobalInfectionDataPlugin(env_graph)
    env_graph.load_time_action_plugin(isolation_data)

node_density_data = None
if 'node_density_data_plugin' in env_graph.experiment_config:
    node_density_data = NodeDensityDataPlugin(env_graph)
    env_graph.load_time_action_plugin(node_density_data)
'''
TimeAction Plugins
'''

move_population_plugin = MovePopulationPlugin(env_graph)
env_graph.load_time_action_plugin(move_population_plugin)

gather_pop = None
if 'gather_population_plugin' in env_graph.experiment_config:
    gather_pop = GatherPopulationPlugin(env_graph)
    env_graph.load_time_action_plugin(gather_pop)

return_pop_home = None
if 'return_population_home_plugin' in env_graph.experiment_config:
    return_pop_home = ReturnPopulationHomePlugin(env_graph)
    env_graph.load_time_action_plugin(return_pop_home)

send_pop_back = None
if 'send_population_back_plugin' in env_graph.experiment_config:
    send_pop_back = SendPopulationBackPlugin(env_graph)
    env_graph.load_time_action_plugin(send_pop_back)

return_to_previous = None
if 'return_to_previous' in env_graph.experiment_config:
    return_to_previous = ReturnToPreviousPlugin(env_graph)
    env_graph.load_time_action_plugin(return_to_previous)

levy_walk = None
if 'levy_walk_plugin' in env_graph.experiment_config:
    levy_walk = LevyWalkPlugin(env_graph)
    env_graph.load_time_action_plugin(levy_walk)

vaccine = None
if 'vaccine_plugin' in env_graph.experiment_config:
    vaccine = VaccinePlugin(env_graph)
    env_graph.load_time_action_plugin(vaccine)

infection = None
if 'infection_plugin' in env_graph.experiment_config:
    infection = InfectionPlugin(env_graph)
    env_graph.load_time_action_plugin(infection)
    

'''
Routine Plugins
'''
if 'off_cycle_routine_plugin' in env_graph.experiment_config:
    off_cycle_rourtine_plugin = OffCycleRoutinePlugin(env_graph)
    env_graph.LoadRoutinePlugin(off_cycle_rourtine_plugin)

'''
Logging
'''

pop_count_logger = PopulationCountLogger(f'{env_graph.experiment_name}', env_graph, cycle_length)
pop_count_logger.data_to_record = {PopulationCountRecordKey.POPULATION_COUNT_GLOBAL,
                                    PopulationCountRecordKey.POPULATION_COUNT_REGION}#,
                                    #PopulationCountRecordKey.POPULATION_COUNT_NODE}

if infection:
    pop_count_logger.global_custom_templates["Susceptible"] = PopTemplate(traceable_properties={"sir_status": "susceptible"})
    pop_count_logger.global_custom_templates["Infected"] = PopTemplate(traceable_properties={"sir_status": "infected"})
    pop_count_logger.global_custom_templates["Removed"] = PopTemplate(traceable_properties={"sir_status": "removed"})

    # pop_count_logger.region_custom_templates["Susceptible"] = PopTemplate(traceable_properties={"sir_status": "susceptible"})
    # pop_count_logger.region_custom_templates["Infected"] = PopTemplate(traceable_properties={"sir_status": "infected"})
    # pop_count_logger.region_custom_templates["Removed"] = PopTemplate(traceable_properties={"sir_status": "removed"})

    # pop_count_logger.node_custom_templates["Students"] = PopTemplate(sampled_properties={"occupation": "student"})
    # pop_count_logger.node_custom_templates["Workers"] = PopTemplate(sampled_properties={"occupation": "worker"})
    # pop_count_logger.node_custom_templates["Susceptible"] = PopTemplate(traceable_properties={"sir_status": "susceptible"})
    # pop_count_logger.node_custom_templates["Infected"] = PopTemplate(traceable_properties={"sir_status": "infected"})
    # pop_count_logger.node_custom_templates["Removed"] = PopTemplate(traceable_properties={"sir_status": "removed"})

if vaccine:
    pop_count_logger.global_custom_templates["VaccineLevel:0"] = PopTemplate(traceable_properties={"vaccine_level": 0})
    pop_count_logger.global_custom_templates["VaccineLevel:1"] = PopTemplate(traceable_properties={"vaccine_level": 1})
    pop_count_logger.global_custom_templates["VaccineLevel:2"] = PopTemplate(traceable_properties={"vaccine_level": 2})
    pop_count_logger.global_custom_templates["VaccineLevel:3"] = PopTemplate(traceable_properties={"vaccine_level": 3})

    # pop_count_logger.region_custom_templates["VaccineLevel:0"] = PopTemplate(traceable_properties={"vaccine_level": 0})
    # pop_count_logger.region_custom_templates["VaccineLevel:1"] = PopTemplate(traceable_properties={"vaccine_level": 1})
    # pop_count_logger.region_custom_templates["VaccineLevel:2"] = PopTemplate(traceable_properties={"vaccine_level": 2})
    # pop_count_logger.region_custom_templates["VaccineLevel:3"] = PopTemplate(traceable_properties={"vaccine_level": 3})
#logger.set_to_record('neighbourhood_disserta')
#logger.set_to_record('metrics')
#logger.set_to_record('positions')

blob_count_logger = BlobCountLogger(f'{env_graph.experiment_name}')
blob_count_logger.data_to_record = {BlobCountRecordKey.BLOB_COUNT_GLOBAL,
                                    BlobCountRecordKey.BLOB_COUNT_REGION,
                                    BlobCountRecordKey.BLOB_COUNT_NODE}


pop_temp = PopTemplate()
#pop_temp.set_property('age', 'adults')
pop_count_logger.pop_template = pop_temp
# logger.foreign_only = True
# this option saves REALLY big files
# logger.set_to_record('graph')
# logger.set_pluggin_to_record(infection_plugin)
# logger.set_pluggin_to_record(vaccine_plugin)

# pop_count_logger.add_custom_line_plot('Total Population - Hospital Nodes', 
#                                     file = 'nodes.csv',
#                                     x_label="Frame", y_label="Population",
#                                     columns= ['Total'],
#                                     level="Node", filter=['hospital'])

# pop_count_logger.add_custom_line_plot('Total Population - School Nodes', 
#                                     file = 'nodes.csv',
#                                     x_label="Frame", y_label="Population",
#                                     columns= ['Total'],
#                                     level="Node", filter=['school'])

# pop_count_logger.add_custom_line_plot('Total Population - Work Nodes', 
#                                     file = 'nodes.csv',
#                                     x_label="Frame", y_label="Population",
#                                     columns= ['Total'],
#                                     level="Node", filter=['work'])

# pop_count_logger.add_custom_line_plot('Total Population - Stadium Nodes', 
#                                     file = 'nodes.csv',
#                                     x_label="Frame", y_label="Population",
#                                     columns= ['Total'],
#                                     level="Node", filter=['stadium'])

# CharacteristicChange logger
traceable_logger = CharacteristicChangeLogger(f'{env_graph.experiment_name}')

# OD-Matrix logger
od_logger = ODMatrixLogger(f'{env_graph.experiment_name}')
od_logger.data_to_record = {ODMovementRecordKey.REGION_TO_REGION}
# od_logger.data_to_record = [ODMovementRecordKey.REGION_TO_REGION,
#                             ODMovementRecordKey.NODE_TO_NODE]

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

# Movement Displacement Logger
displacement_logger = MovementDisplacementLogger(f'{env_graph.experiment_name}')

# Levy Sample Logger
levy_sample_logger = None
if levy_walk is not None:
    levy_sample_logger = LevyWalkSampleLogger(f'{env_graph.experiment_name}')

infection_sum_logger = None
if infection is not None:
    infection_sum_logger = InfectionSumLogger(f'{env_graph.experiment_name}')
# Vaccine Logger
#vacc_logger = VaccineLevelLogger(f'{args["n"]}', env_graph, day_duration)

output_str += "Population per Age:\n"
output_str += "Children:" + str(env_graph.get_population_size(PopTemplate(sampled_properties={"age": "children"}))) + "\n"
output_str += "Youngs:" + str(env_graph.get_population_size(PopTemplate(sampled_properties={"age": "youngs"}))) + "\n"
output_str += "Adults:" + str(env_graph.get_population_size(PopTemplate(sampled_properties={"age": "adults"}))) + "\n"
output_str += "Elders:" + str(env_graph.get_population_size(PopTemplate(sampled_properties={"age": "elders"}))) + "\n"
output_str += "Population per Occupation:\n"
output_str += "Worker:" + str(env_graph.get_population_size(PopTemplate(sampled_properties={"occupation": "worker"}))) + "\n"
output_str += "Student:" + str(env_graph.get_population_size(PopTemplate(sampled_properties={"occupation": "student"}))) + "\n"
output_str += "Other:" + str(env_graph.get_population_size(PopTemplate(sampled_properties={"occupation": "other"}))) + "\n"
print(output_str)
'''
Simulation
'''

env_graph.LoadLoggerPlugin(pop_count_logger)
# env_graph.LoadLoggerPlugin(od_logger)
env_graph.LoadLoggerPlugin(blob_count_logger)
# # env_graph.LoadLoggerPlugin(traceable_logger)
# # env_graph.LoadLoggerPlugin(vacc_logger)
env_graph.LoadLoggerPlugin(displacement_logger)
if levy_sample_logger is not None: env_graph.LoadLoggerPlugin(levy_sample_logger)
if infection_sum_logger is not None: env_graph.LoadLoggerPlugin(infection_sum_logger)
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


#print("TimeAction Plugins execution times")
if levy_walk is not None: output_str += levy_walk.print_execution_time_data()
if infection is not None: output_str += infection.print_execution_time_data()
if vaccine is not None: output_str += vaccine.print_execution_time_data()
if gather_pop is not None: output_str += gather_pop.print_execution_time_data()
if return_pop_home is not None: output_str += return_pop_home.print_execution_time_data()
if send_pop_back is not None: output_str += send_pop_back.print_execution_time_data()
if return_to_previous is not None: output_str += return_to_previous.print_execution_time_data()
if move_population_plugin is not None: output_str += move_population_plugin.print_execution_time_data()

output_str += "Total Simulation Time: " + str(end_time - start_time) + "\n"
output_str += "Average Cycle Time: " + str((end_time - start_time)/cycles) + "\n"
output_str += "Loaded TimeAction Keys: " + str(env_graph.time_action_map.keys()) + "\n"

print("Total Simulation time")
print(end_time - start_time)
print("Average Cycle time")
print((end_time - start_time)/cycles)

print("Loaded TimeAction Keys: ", env_graph.time_action_map.keys())
print("writing Output File")
text_file = open(f"output_logs/{env_graph.experiment_name}/output.txt", "w")
text_file.write(output_str)
text_file.close()
exit(0)