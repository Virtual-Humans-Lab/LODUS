#encoding: utf-8
import sys

sys.path.append('./plugins/')
import argparse
import json
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from loggers.blob_count_logger import BlobCountLogger, BlobCountRecordKey
from loggers.characteristic_change_logger import CharacteristicChangeLogger
from loggers.movement_displacement_logger import MovementDisplacementLogger
from loggers.enumeration_area_od_matrix_logger import EnumerationAreaODMatrixLogger
from loggers.od_matrix_logger import ODMatrixLogger, ODMovementRecordKey
from loggers.envnode_state_logger import EnvNodeStateLogger
from loggers.population_count_logger import (PopulationCountLogger,
                                             PopulationCountRecordKey)
from loggers.levy_walk_sample_logger import LevyWalkSampleLogger

from loggers.infection_sum_logger import InfectionSumLogger
from loggers.vaccine_level_logger import VaccineLevelLogger
from loggers.dialysis_logger import DialysisLogger
from loggers.inpatient_care_logger import InpatientCareLogger

from routines.off_cycle_routine_plugin import OffCycleRoutinePlugin
from time_actions.custom_time_action_plugin import CustomTimeActionPlugin
from time_actions.gather_population_plugin import GatherPopulationPlugin
from time_actions.infection_plugin import InfectionPlugin
from time_actions.levy_walk_plugin import LevyWalkPlugin
from time_actions.move_population_plugin import MovePopulationPlugin
from time_actions.new_infection_plugin import NewInfectionPlugin
from data.node_density_data_plugin import NodeDensityDataPlugin
from data.node_dependency_data_plugin import NodeDependencyDataPlugin
from data.water_level_data_plugin import WaterLevelDataPlugin
from time_actions.return_population_home_plugin import ReturnPopulationHomePlugin
from time_actions.return_to_previous_plugin import ReturnToPreviousPlugin
from time_actions.reverse_social_isolation_plugin import \
    ReverseSocialIsolationPlugin
from time_actions.send_population_back_plugin import SendPopulationBackPlugin
from time_actions.vaccine_plugin import VaccinePlugin
from time_actions.dialysis_plugin import DialysisPlugin
from time_actions.inpatient_care_plugin import InpatientCarePlugin

from time_actions.change_enabled_state_plugin import ChangeEnabledStatePlugin
from data.global_isolation_data_plugin import GlobalIsolationDataPlugin
from data.global_infection_data_plugin import GlobalInfectionDataPlugin
from data.custom_dependency_data_plugin import CustomDependencyDataPlugin

import core.environment
from core.population import PopulationTemplate
from util.random_instance import FixedRandom
from util.data_parse import generate_lodus_simulation, load_experiment_config
from util.resource_usage import get_peak_memory_kib
import numpy as np

arg_parser = argparse.ArgumentParser(description="Population Dynamics Simulation.")
arg_parser.add_argument('--f', metavar="F", type=str, default = '', help='Simulation file.')
arg_parser.add_argument('--e', metavar="E", type=str, default = None, help='Experiment Configuration File.')
arg_parser.add_argument('--r', metavar="R", type=float, default = 0, help='R')
arg_parser.add_argument('--n', metavar="N", type=str, default = None, help='Experiment Name.')
arg_parser.add_argument('--c', metavar="C", type=str, default = "./data_input/CustomTimeActions.json", help='Custom Time Actions Configuration File (.json)')
arg_parser.add_argument('--d', metavar="D", type=str, default = "./data_input/NodeDensities.json", help='Node Densities Configuration File (.json)')
arg_parser.add_argument('--v', metavar="V", type=str, default = "./data_input/VaccinePluginSetup.json", help='Vaccine Plugin Configuration File (.json)')
arg_parser.add_argument('--i', metavar="I", type=str, default = "./data_input/SIRPluginSetup.json", help='SIR Plugin Configuration File (.json)')
arg_parser.add_argument('--seed', type=int, default=None, help='Random seed. Overrides simulation_parameters.random_seed.')
arg_parser.add_argument('--no-dialysis-png', action='store_true', help='Generate dialysis HTML outputs without PNG export.')
arg_parser.add_argument('--no-inpatient-care-png', action='store_true', help='Generate inpatient care HTML outputs without PNG export.')
arg_parser.add_argument('--no-inpatient-care-plots', action='store_true', help='Skip inpatient care HTML and PNG plot generation.')
args = vars(arg_parser.parse_args())

configured_seed = None
if args["e"] is not None:
    seed_config = load_experiment_config(args["e"])
    configured_seed = seed_config.get("simulation_parameters", {}).get(
        "random_seed",
        seed_config.get("random_seed"),
    )
simulation_seed = (
    args["seed"]
    if args["seed"] is not None
    else int(configured_seed or 0)
)
FixedRandom(
    random_seed=simulation_seed,
    numpy_seed=simulation_seed,
)

output_str = ""

'''
Data Loading
'''
data_input_file_path = args['f']
experiment_configuration_file = args['e']
if ".json" in args['f']: 
    raise Exception("please use the new format of inputs (experiment config)")
lodus_simulation = generate_lodus_simulation(experiment_configuration_file)
lodus_simulation.experiment_config.setdefault(
    "simulation_parameters", {}
)["random_seed"] = simulation_seed
env_graph = lodus_simulation.env_graph
'''
Parameters
'''
# How many steps each cycle has. Ex: a day (cycle) with 24 hours (length)
cycles = lodus_simulation.time_status.total_cycles
cycle_length = lodus_simulation.time_status.cycle_length

lodus_simulation.experiment_name = args["n"] if args["n"] is not None else args["e"]
lodus_simulation.env_graph.print_overview()
print("----------------------")

#print([reg.name for reg in env_graph.region_dict.values()])
#print([node.get_complete_name() for node in env_graph.node_list])


'''
Data Plugins
'''

isolation_data = None
if 'global_isolation_data_plugin' in lodus_simulation.experiment_config:
    isolation_data = GlobalIsolationDataPlugin(env_graph)
    env_graph.load_time_action_plugin(isolation_data)

infection_data = None
if 'global_infection_data_plugin' in lodus_simulation.experiment_config:
    isolation_data = GlobalInfectionDataPlugin(env_graph)
    env_graph.load_time_action_plugin(isolation_data)

node_density_data = None
if 'node_density_data_plugin' in lodus_simulation.experiment_config:
    node_density_data = NodeDensityDataPlugin(env_graph)
    env_graph.load_time_action_plugin(node_density_data)

node_dependency_data = None
if 'node_dependency_data_plugin' in lodus_simulation.experiment_config:
    node_dependency_data = NodeDependencyDataPlugin()
    lodus_simulation.load_plugin(node_dependency_data)
    #env_graph.load_time_action_plugin(node_dependency_data)

water_level_data = None
if 'water_level_data_plugin' in lodus_simulation.experiment_config:
    water_level_data = WaterLevelDataPlugin(env_graph)
    lodus_simulation.load_plugin(water_level_data)

custom_dependency_data = None
if 'custom_dependency_data_plugin' in lodus_simulation.experiment_config:
    custom_dependency_data = CustomDependencyDataPlugin()
    lodus_simulation.load_plugin(custom_dependency_data)
'''
TimeAction Plugins
'''

move_population_plugin = MovePopulationPlugin()
lodus_simulation.load_plugin(move_population_plugin)

gather_pop = None
if 'gather_population_plugin' in lodus_simulation.experiment_config:
    gather_pop = GatherPopulationPlugin()
    lodus_simulation.load_plugin(gather_pop)

return_pop_home = None
if 'return_population_home_plugin' in lodus_simulation.experiment_config:
    return_pop_home = ReturnPopulationHomePlugin(env_graph)
    env_graph.load_time_action_plugin(return_pop_home)

send_pop_back = None
if 'send_population_back_plugin' in lodus_simulation.experiment_config:
    send_pop_back = SendPopulationBackPlugin()
    lodus_simulation.load_plugin(send_pop_back)

return_to_previous = None
if 'return_to_previous' in lodus_simulation.experiment_config:
    return_to_previous = ReturnToPreviousPlugin()
    lodus_simulation.load_plugin(return_to_previous)

levy_walk = None
if 'levy_walk_plugin' in lodus_simulation.experiment_config:
    levy_walk = LevyWalkPlugin()
    lodus_simulation.load_plugin(levy_walk)

vaccine = None
if 'vaccine_plugin' in lodus_simulation.experiment_config:
    vaccine = VaccinePlugin()
    lodus_simulation.load_plugin(vaccine)

infection = None
if 'infection_plugin' in lodus_simulation.experiment_config:
    infection = InfectionPlugin()
    lodus_simulation.load_plugin(infection)

change_enabled_state = None
if 'change_enabled_state_plugin' in lodus_simulation.experiment_config:
    change_enabled_state = ChangeEnabledStatePlugin()
    lodus_simulation.load_plugin(change_enabled_state)

dialysis = None
if 'dialysis_plugin' in lodus_simulation.experiment_config:
    dialysis = DialysisPlugin()
    lodus_simulation.load_plugin(dialysis)

inpatient_care = None
if 'inpatient_care_plugin' in lodus_simulation.experiment_config:
    inpatient_care = InpatientCarePlugin()
    lodus_simulation.load_plugin(inpatient_care)



'''
Routine Plugins
'''
off_cycle_routine = None
if 'off_cycle_routine_plugin' in lodus_simulation.experiment_config:
    off_cycle_routine = OffCycleRoutinePlugin()
    lodus_simulation.load_plugin(off_cycle_routine)

'''
Logging
'''

pop_count_logger = PopulationCountLogger()
pop_count_logger.data_to_record = {PopulationCountRecordKey.POPULATION_COUNT_GLOBAL,
                                    PopulationCountRecordKey.POPULATION_COUNT_REGION}#,
                                    #PopulationCountRecordKey.POPULATION_COUNT_NODE}

if infection:
    pop_count_logger.global_custom_templates["Susceptible"] = PopulationTemplate(traceable_characteristics={"sir_status": "susceptible"})
    pop_count_logger.global_custom_templates["Infected"] = PopulationTemplate(traceable_characteristics={"sir_status": "infected"})
    pop_count_logger.global_custom_templates["Removed"] = PopulationTemplate(traceable_characteristics={"sir_status": "removed"})

    # pop_count_logger.region_custom_templates["Susceptible"] = PopTemplate(traceable_properties={"sir_status": "susceptible"})
    # pop_count_logger.region_custom_templates["Infected"] = PopTemplate(traceable_properties={"sir_status": "infected"})
    # pop_count_logger.region_custom_templates["Removed"] = PopTemplate(traceable_properties={"sir_status": "removed"})

    # pop_count_logger.node_custom_templates["Students"] = PopTemplate(sampled_properties={"occupation": "student"})
    # pop_count_logger.node_custom_templates["Workers"] = PopTemplate(sampled_properties={"occupation": "worker"})
    # pop_count_logger.node_custom_templates["Susceptible"] = PopTemplate(traceable_properties={"sir_status": "susceptible"})
    # pop_count_logger.node_custom_templates["Infected"] = PopTemplate(traceable_properties={"sir_status": "infected"})
    # pop_count_logger.node_custom_templates["Removed"] = PopTemplate(traceable_properties={"sir_status": "removed"})

if vaccine:
    pop_count_logger.global_custom_templates["VaccineLevel:0"] = PopulationTemplate(traceable_characteristics={"vaccine_level": 0})
    pop_count_logger.global_custom_templates["VaccineLevel:1"] = PopulationTemplate(traceable_characteristics={"vaccine_level": 1})
    pop_count_logger.global_custom_templates["VaccineLevel:2"] = PopulationTemplate(traceable_characteristics={"vaccine_level": 2})
    pop_count_logger.global_custom_templates["VaccineLevel:3"] = PopulationTemplate(traceable_characteristics={"vaccine_level": 3})

    # pop_count_logger.region_custom_templates["VaccineLevel:0"] = PopTemplate(traceable_properties={"vaccine_level": 0})
    # pop_count_logger.region_custom_templates["VaccineLevel:1"] = PopTemplate(traceable_properties={"vaccine_level": 1})
    # pop_count_logger.region_custom_templates["VaccineLevel:2"] = PopTemplate(traceable_properties={"vaccine_level": 2})
    # pop_count_logger.region_custom_templates["VaccineLevel:3"] = PopTemplate(traceable_properties={"vaccine_level": 3})
#logger.set_to_record('neighbourhood_study')
#logger.set_to_record('metrics')
#logger.set_to_record('positions')

dialysis_logger = None
if dialysis:
    dialysis_logger = DialysisLogger(
        export_png=not args["no_dialysis_png"]
    )

inpatient_care_logger = None
if inpatient_care:
    inpatient_care_logger = InpatientCareLogger(
        export_png=not args["no_inpatient_care_png"],
        generate_plots=not args["no_inpatient_care_plots"],
    )

blob_count_logger = BlobCountLogger()
blob_count_logger.data_to_record = {BlobCountRecordKey.BLOB_COUNT_GLOBAL,
                                    BlobCountRecordKey.BLOB_COUNT_REGION,
                                    BlobCountRecordKey.BLOB_COUNT_NODE}


pop_temp = core.population.PopulationTemplate()
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
traceable_logger = CharacteristicChangeLogger()

# OD-Matrix logger
od_logger = ODMatrixLogger()
od_logger.data_to_record = {ODMovementRecordKey.REGION_TO_REGION}
# od_logger.data_to_record = [ODMovementRecordKey.REGION_TO_REGION,
#                             ODMovementRecordKey.NODE_TO_NODE]

# Age tracking
od_logger.region_custom_templates["age: [children]"] = PopulationTemplate(sampled_characteristics={"age": ["children"]})
od_logger.region_custom_templates["age: [youngs]"] = PopulationTemplate(sampled_characteristics={"age": ["youngs"]})
od_logger.region_custom_templates["age: [adults]"] = PopulationTemplate(sampled_characteristics={"age": ["adults"]})
od_logger.region_custom_templates["age: [elders]"] = PopulationTemplate(sampled_characteristics={"age": ["elders"]})

# Occupation tracking
#od_logger.region_custom_templates["occupation: [other]"] = PopulationTemplate(sampled_characteristics={"occupation": ["other"]})
od_logger.region_custom_templates["occupation: [student]"] = PopulationTemplate(sampled_characteristics={"occupation": ["student"]})
od_logger.region_custom_templates["occupation: [worker]"] = PopulationTemplate(sampled_characteristics={"occupation": ["worker"]})
od_logger.region_custom_templates["occupation: [other]"] = PopulationTemplate(sampled_characteristics={"occupation": ["other"]})
#od_logger.node_custom_templates["occupation: [worker]"] = PopulationTemplate(sampled_characteristics={"occupation": ["worker"]})
#----------------------------

# EnumerationArea OD-Matrix logger
enum_area_logger = EnumerationAreaODMatrixLogger()

# Age tracking
enum_area_logger.custom_templates["age: [children]"] = PopulationTemplate(sampled_characteristics={"age": ["children"]})
enum_area_logger.custom_templates["age: [youngs]"] = PopulationTemplate(sampled_characteristics={"age": ["youngs"]})
enum_area_logger.custom_templates["age: [adults]"] = PopulationTemplate(sampled_characteristics={"age": ["adults"]})
enum_area_logger.custom_templates["age: [elders]"] = PopulationTemplate(sampled_characteristics={"age": ["elders"]})

# Occupation tracking
enum_area_logger.custom_templates["occupation: [student]"] = PopulationTemplate(sampled_characteristics={"occupation": ["student"]})
enum_area_logger.custom_templates["occupation: [worker]"] = PopulationTemplate(sampled_characteristics={"occupation": ["worker"]})
enum_area_logger.custom_templates["occupation: [other]"] = PopulationTemplate(sampled_characteristics={"occupation": ["other"]})

# Movement Displacement Logger
displacement_logger = MovementDisplacementLogger()

# EnvNode Enabled/Disabled Snapshot Logger
envnode_state_logger = EnvNodeStateLogger()

# Levy Sample Logger
levy_sample_logger = None
if levy_walk is not None:
    levy_sample_logger = LevyWalkSampleLogger()

infection_sum_logger = None
if infection is not None:
    infection_sum_logger = InfectionSumLogger(f'{env_graph.experiment_name}')
# Vaccine Logger
#vacc_logger = VaccineLevelLogger(f'{args["n"]}', env_graph, day_duration)

output_str += "Population per Age:\n"
output_str += "Children:" + str(env_graph.get_population_size(PopulationTemplate(sampled_characteristics={"age": ["children"]}))) + "\n"
output_str += "Youngs:" + str(env_graph.get_population_size(PopulationTemplate(sampled_characteristics={"age": ["youngs"]}))) + "\n"
output_str += "Adults:" + str(env_graph.get_population_size(PopulationTemplate(sampled_characteristics={"age": ["adults"]}))) + "\n"
output_str += "Elders:" + str(env_graph.get_population_size(PopulationTemplate(sampled_characteristics={"age": ["elders"]}))) + "\n"
output_str += "Population per Occupation:\n"
output_str += "Worker:" + str(env_graph.get_population_size(PopulationTemplate(sampled_characteristics={"occupation": ["worker"]}))) + "\n"
output_str += "Student:" + str(env_graph.get_population_size(PopulationTemplate(sampled_characteristics={"occupation": ["student"]}))) + "\n"
output_str += "Other:" + str(env_graph.get_population_size(PopulationTemplate(sampled_characteristics={"occupation": ["other"]}))) + "\n"
print(output_str)
'''
Simulation
'''

lodus_simulation.load_plugin(pop_count_logger)
lodus_simulation.load_plugin(od_logger)
lodus_simulation.load_plugin(enum_area_logger)
lodus_simulation.load_plugin(blob_count_logger)
# # env_graph.LoadLoggerPlugin(traceable_logger)
# # env_graph.LoadLoggerPlugin(vacc_logger)
lodus_simulation.load_plugin(displacement_logger)
lodus_simulation.load_plugin(envnode_state_logger)
if dialysis_logger is not None:
    lodus_simulation.load_plugin(dialysis_logger)
if inpatient_care_logger is not None:
    lodus_simulation.load_plugin(inpatient_care_logger)
# if levy_sample_logger is not None: lodus_simulation.load_plugin(levy_sample_logger)
if infection_sum_logger is not None: lodus_simulation.load_plugin(infection_sum_logger)
#print("Loaded TimeAction Plugins: " + str([type(tap) for tap in env_graph.loaded_logger_plugins]))
#print("Loaded Logger Plugins: " + str([type(lp) for lp in env_graph.loaded_logger_plugins]))

lodus_simulation.setup_logging()

start_time = time.perf_counter()
started_at = datetime.now(timezone.utc)
#for i in range(simulation_steps):

print("Water sources: ", [node.get_complete_name() for node in lodus_simulation.env_graph.get_nodes_by_type("water_source")])
print("Dialysis clinics: ", [node.get_complete_name() for node in lodus_simulation.env_graph.get_nodes_by_type("dialysis_clinic")])

while not lodus_simulation.time_status.is_final_step:
    

    #infection_plugin.update_time_step(lodus_simulation.time_status.simulation_step % day_duration, lodus_simulation.time_status.simulation_step)

    #if i % day_duration == 0:
    #    vaccine_plugin.update_time_step(i % day_duration, i)

    # Routine/Repeating Global Action Invoke example

    # Updates Node Routines and Repeating Global Actions
    # These are defined in the input environment descriptor
    #env_graph.update_time_step(i % cycle_length, i)

    lodus_simulation.update_time_step()

    i = lodus_simulation.time_status.simulation_step
    # print(i, end='\r')

    # print number of disabled nodes at the end of each simulation step
    disabled_nodes = [node for node in env_graph.node_list if not node.enabled]
    print(f"\nEnd of Step {i}: {len(disabled_nodes)} disabled nodes")

    # Log current simulation step
    lodus_simulation.log_simulation_step()
    
    #if len(env_graph.region_dict["Azenha"].get_node_by_name("pharmacy").contained_blobs) > 0:
    #    print(env_graph.region_dict["Azenha"].get_node_by_name("pharmacy").contained_blobs[0].traceable_properties)
    

#logger.compute_composite_data(env_graph, simulation_steps)

#logger.stop_logging(show_figures=False, export_figures=False, export_html=True)
# od_logger.stop_logging()

end_time = time.perf_counter()
finished_at = datetime.now(timezone.utc)
lodus_simulation.stop_logging()


#print("TimeAction Plugins execution times")python .\TOMACS_simulation.py --e BaselineRefactored
if levy_walk is not None: output_str += levy_walk.print_execution_time_data()
if infection is not None: output_str += infection.print_execution_time_data()
if vaccine is not None: output_str += vaccine.print_execution_time_data()
if gather_pop is not None: output_str += gather_pop.print_execution_time_data()
if return_pop_home is not None: output_str += return_pop_home.print_execution_time_data()
if send_pop_back is not None: output_str += send_pop_back.print_execution_time_data()
if return_to_previous is not None: output_str += return_to_previous.print_execution_time_data()
if move_population_plugin is not None: output_str += move_population_plugin.print_execution_time_data()
if change_enabled_state is not None: output_str += change_enabled_state.print_execution_time_data()
if dialysis is not None: output_str += dialysis.print_execution_time_data()
if inpatient_care is not None: output_str += inpatient_care.print_execution_time_data()

output_str += "Total Simulation Time: " + str(end_time - start_time) + "\n"
output_str += "Average Cycle Time: " + str((end_time - start_time)/cycles) + "\n"
output_str += "Loaded TimeAction Keys: " + str(lodus_simulation.routine_controller.action_type_to_function.keys()) + "\n"

print("Total Simulation time")
print(end_time - start_time)
print("Average Cycle time")
print((end_time - start_time)/cycles)

print("Loaded TimeAction Keys: ", lodus_simulation.routine_controller.action_type_to_function.keys())
print("writing Output File")
output_path = Path("output_logs") / lodus_simulation.experiment_name
output_path.mkdir(parents=True, exist_ok=True)
(output_path / "output.txt").write_text(output_str, encoding="utf8")
try:
    commit_sha = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=Path(__file__).parent,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
except (OSError, subprocess.CalledProcessError):
    commit_sha = None
metadata = {
    "status": "complete",
    "experiment": args["e"],
    "run_name": lodus_simulation.experiment_name,
    "seed": simulation_seed,
    "numpy_seed": simulation_seed,
    "started_at_utc": started_at.isoformat(),
    "finished_at_utc": finished_at.isoformat(),
    "runtime_seconds": end_time - start_time,
    "peak_memory_kib": get_peak_memory_kib(),
    "commit_sha": commit_sha,
    "environment_files": lodus_simulation.experiment_config.get(
        "envgraph_inputs_files", {}
    ),
    "simulation_parameters": {
        "total_cycles": cycles,
        "cycle_length": cycle_length,
    },
    "resolved_config": lodus_simulation.experiment_config,
}
(output_path / "run_metadata.json").write_text(
    json.dumps(metadata, indent=2, ensure_ascii=False),
    encoding="utf8",
)
exit(0)

# source .venv/bin/activate
# python sector_simulation.py --e EnumerationArea13

# python.exe visualize_envnode_states.py --experiment-name YOUR_EXPERIMENT_NAME --output-html output_logs/YOUR_EXPERIMENT_NAME/envnode_state_visualization.html
# python.exe visualize_envnode_states.py --state-log output_logs/YOUR_EXPERIMENT_NAME/data_frames/envnode_state.csv
# python misc_scripts/visualize_envnode_states.py --experiment-name EnumerationArea13 --output-html output_logs/EnumerationArea13/envnode_state_visualization.html
