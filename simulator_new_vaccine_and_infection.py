#encoding: utf-8
import sys

from od_matrix_logger import LoggerODRecordKey, ODMatrixLogger
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
from NewInfectionPlugin import NewInfectionPlugin
from NodeDensityPlugin import NodeDensityPlugin
from CustomTimeActionPlugin import CustomTimeActionPlugin

from simulation_logger import LoggerDefaultRecordKey, SimulationLogger
from pathlib import Path

import time

arg_parser = argparse.ArgumentParser(description="Population Dynamics Simulation.")
arg_parser.add_argument('--f', metavar="F", type=str, default = '', help='Simulation file.')
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
env_graph = generate_EnvironmentGraph(data_input_file_path)

'''
Parameters
'''
#how many steps each day has
days = 1
day_duration = 24
env_graph.routine_day_length = day_duration

simulation_steps = days * day_duration





'''
Load Plugins Examples
'''

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


density_plugin = NodeDensityPlugin(env_graph, args['d'])
env_graph.LoadPlugin(density_plugin)

#custom_action_plugin = CustomTimeActionPlugin(env_graph, args['c'])
#env_graph.LoadPlugin(custom_action_plugin)

#vaccine_plugin = VaccinePlugin(env_graph, args['v'], day_duration)
#env_graph.LoadPlugin(vaccine_plugin)

#infection_plugin = NewInfectionPlugin(env_graph, args['i'], day_duration)
#env_graph.LoadPlugin(infection_plugin)

'''
Logging
'''

logger = SimulationLogger(f'{args["n"]}', env_graph, day_duration)

logger.set_data_list_to_record([LoggerDefaultRecordKey.BLOB_COUNT_GLOBAL,
    LoggerDefaultRecordKey.BLOB_COUNT_REGION,
    LoggerDefaultRecordKey.BLOB_COUNT_NODE,
    LoggerDefaultRecordKey.ENV_GLOBAL_POPULATION,
    LoggerDefaultRecordKey.ENV_REGION_POPULATION,
    LoggerDefaultRecordKey.ENV_NODE_POPULATION])
#logger.set_to_record('neighbourhood_disserta')
#logger.set_to_record('metrics')
#logger.set_to_record('positions')



pop_temp = PopTemplate()
#pop_temp.set_property('age', 'adults')
logger.pop_template = pop_temp
# logger.foreign_only = True
# this option saves REALLY big files
# logger.set_to_record('graph')
# logger.set_pluggin_to_record(infection_plugin)
# logger.set_pluggin_to_record(vaccine_plugin)

# OD-Matrix logger
od_logger = ODMatrixLogger(f'{args["n"]}', env_graph, day_duration)
od_logger.data_to_record.add(LoggerODRecordKey.REGION_TO_REGION)
od_logger.data_to_record.add(LoggerODRecordKey.NODE_TO_NODE)

# Age tracking
od_logger.region_custom_templates["age: [children]"] = PopTemplate(sampled_properties={"age": "children"})
od_logger.region_custom_templates["age: [young]"] = PopTemplate(sampled_properties={"age": "young"})
od_logger.region_custom_templates["age: [adults]"] = PopTemplate(sampled_properties={"age": "adults"})
od_logger.region_custom_templates["age: [elders]"] = PopTemplate(sampled_properties={"age": "elders"})

# Occupation tracking
od_logger.region_custom_templates["occupation: [idle]"] = PopTemplate(sampled_properties={"occupation": "idle"})
od_logger.region_custom_templates["occupation: [student]"] = PopTemplate(sampled_properties={"occupation": "student"})
od_logger.region_custom_templates["occupation: [worker]"] = PopTemplate(sampled_properties={"occupation": "worker"})
#----------------------------

'''
Simulation
'''
#logger.start_logging()

env_graph.LoadLoggerPlugin(od_logger)
print(env_graph.loaded_logger_plugins)
env_graph.start_logging()

for i in range(simulation_steps):
    print(i, end='\r')
        
    #infection_plugin.update_time_step(i % day_duration, i)

    #if i % day_duration == 0:
    #    vaccine_plugin.update_time_step(i % day_duration, i)

    # Routine/Repeating Global Action Invoke example
    # Updates Node Routines and Repeating Global Actions
    # These are defined in the input environment descriptor
    # od_logger.update_time_step(i % day_duration, i)
    env_graph.update_time_step(i % day_duration, i)
    env_graph.log_simulation_step()
    #print(env_graph.get_blob_count())
    #print(env_graph.get_population_size())
    
    #if len(env_graph.region_dict["Azenha"].get_node_by_name("pharmacy").contained_blobs) > 0:
    #    print(env_graph.region_dict["Azenha"].get_node_by_name("pharmacy").contained_blobs[0].traceable_properties)
    
    #logger.record_frame(env_graph, i)
    # Direct Action Invoke example
    # if i == 50:
    #     dummy_action = TimeAction('push_population', {'region':'example1', 'node':'example2', 'quantity':50})
    #     env_graph.direct_action_invoke(dummy_action)
    
    # Next frame queue action example
    # if i == 60:
    #     dummy_action = TimeAction('push_population', {'region':'example1', 'node':'example2', 'quantity':50})
    #     env_graph.queue_next_frame_action(dummy_action)

#logger.compute_composite_data(env_graph, simulation_steps)

#logger.stop_logging(show_figures=False, export_figures=False, export_html=True)
# od_logger.stop_logging()
env_graph.stop_logging()