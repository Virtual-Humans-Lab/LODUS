'''
Execution
python simulator_hospital.py --f .\DataInput\HOSPITAL_TESTE.json --n hosp_example
'''

#encoding: utf-8
import sys

from population import PopTemplate
sys.path.append('./Plugins/')

import argparse
from data_parse_util import generate_EnvironmentGraph
from random_inst import FixedRandom

from GatherPopulationNewPlugin import GatherPopulationNewPlugin
from HospitalPlugin import HospitalPlugin
from ReturnPopulationPlugin import ReturnPopulationPlugin

from simulation_logger import LoggerDefaultRecordKey, SimulationLogger


arg_parser = argparse.ArgumentParser(description="Population Dynamics Simulation.")
arg_parser.add_argument('--f', metavar="F", type=str, default = '', help='Simulation file.')
arg_parser.add_argument('--r', metavar="R", type=float, default = 0, help='R')
arg_parser.add_argument('--n', metavar="N", type=str, default = None, help='Experiment Name.')
arg_parser.add_argument('--h', metavar="H", type=str, default = ".\DataInput\\region_month_2022.csv", help='Sick Per Region Example.')
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
day_duration = 12
env_graph.routine_day_length = day_duration

simulation_steps = days * day_duration

'''
Load Plugins
'''
gather_pop = GatherPopulationNewPlugin(env_graph, isolation_rate = 0.0)
gather_pop.iso_mode = 'regular'
env_graph.LoadPlugin(gather_pop)

return_plugin = ReturnPopulationPlugin(env_graph)
env_graph.LoadPlugin(return_plugin)

hospitalPlugin = HospitalPlugin(env_graph, args['h'], simulation_steps, day_duration)
env_graph.LoadPlugin(hospitalPlugin)


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


pt_not_patient = PopTemplate()
pt_not_patient.set_traceable_property("patient_id", 0)
pt_patient = PopTemplate()
pt_patient.set_traceable_property("patient_id", lambda x: x != 0)
logger.node_custom_templates['Not Patients'] = pt_not_patient
logger.node_custom_templates['Patients'] = pt_patient

logger.add_custom_line_plot('Total Patient Population - Hospital Nodes', 
                                file = 'nodes.csv',
                                x_label="Frame", y_label="Population",
                                columns= ['Patients'],
                                level="Node", filter=['hospital'])

'''
Simulation
'''
logger.start_logging()

for i in range(simulation_steps):
    # print(i, end='\r')

    env_graph.update_time_step(i % day_duration, i)

    logger.record_frame(env_graph, i)

logger.stop_logging(show_figures=False, export_figures=False, export_html=True)