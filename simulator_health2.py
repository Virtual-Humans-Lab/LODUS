#encoding: utf-8
import sys
sys.path.append('./Plugins/')

import argparse
from util import *
from data_parse_util import *

from random_inst import FixedRandom

from GatherPopulationNewPlugin import GatherPopulationNewPlugin
from ReturnPopulationPlugin import ReturnPopulationPlugin
from ReturnToPrevious import ReturnToPreviousPlugin
from HealthExamplePlugin import HealthExamplePlugin

from simulation_logger import LoggerDefaultRecordKey, SimulationLogger

arg_parser = argparse.ArgumentParser(description="Population Dynamics Simulation.")
arg_parser.add_argument('--f', metavar="F", type=str, default = '', help='Simulation file.')
arg_parser.add_argument('--r', metavar="R", type=float, default = 0, help='R')
arg_parser.add_argument('--n', metavar="N", type=str, default = None, help='Experiment Name.')
arg_parser.add_argument('--h', metavar="H", type=str, default = ".\DataInput\SickPerRegion2.csv", help='Sick Per Region Example.')
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
day_duration = 10
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

health = HealthExamplePlugin(env_graph, args['h'], day_duration)
env_graph.LoadPlugin(health)

# exit()

'''
Logging
'''

logger = SimulationLogger(f'{args["n"]}', env_graph, day_duration)

logger.set_default_data_to_record(LoggerDefaultRecordKey.BLOB_COUNT_GLOBAL)
logger.set_default_data_to_record(LoggerDefaultRecordKey.BLOB_COUNT_REGION)
logger.set_default_data_to_record(LoggerDefaultRecordKey.BLOB_COUNT_NODE)
logger.set_default_data_to_record(LoggerDefaultRecordKey.ENV_GLOBAL_POPULATION)
logger.set_default_data_to_record(LoggerDefaultRecordKey.ENV_REGION_POPULATION)
logger.set_default_data_to_record(LoggerDefaultRecordKey.ENV_NODE_POPULATION)

pop_temp = PopTemplate()
logger.pop_template = pop_temp

'''
Simulation
'''
logger.start_logging()
# exit()
for i in range(simulation_steps):
    print(i, end='\r')
        
    #infection_plugin.update_time_step(i % day_duration, i)

    #if i % day_duration == 0:
    #    vaccine_plugin.update_time_step(i % day_duration, i)

    # Routine/Repeating Global Action Invoke example
    # Updates Node Routines and Repeating Global Actions
    # These are defined in the input environment descriptor
    health.update_time_step(i % day_duration, i)

    env_graph.update_time_step(i % day_duration, i)
    
    #print(env_graph.get_blob_count())
    #print(env_graph.get_population_size())
    
    #if len(env_graph.region_dict["Azenha"].get_node_by_name("pharmacy").contained_blobs) > 0:
    #    print(env_graph.region_dict["Azenha"].get_node_by_name("pharmacy").contained_blobs[0].traceable_properties)
    
    logger.record_frame(env_graph, i)
    # Direct Action Invoke example
    # if i == 50:
    #     dummy_action = TimeAction('push_population', {'region':'example1', 'node':'example2', 'quantity':50})
    #     env_graph.direct_action_invoke(dummy_action)
    
    # Next frame queue action example
    # if i == 60:
    #     dummy_action = TimeAction('push_population', {'region':'example1', 'node':'example2', 'quantity':50})
    #     env_graph.queue_next_frame_action(dummy_action)

#logger.compute_composite_data(env_graph, simulation_steps)

logger.stop_logging(show_figures=False, export_figures=False, export_html=True)