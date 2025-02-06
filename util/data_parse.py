import json
from pathlib import Path
from core.environment import EnvironmentGraph, EnvRegionTemplate, EnvNodeTemplate
from core.population import BlobFactory, BlobTemplate, CharacteristicsFactory, PopulationTemplate
from core.routine import Action, GlobalAction
from core.simulator import LodusSimulation

def generate_lodus_simulation(input_path: str):
    """Generate a LodusSimulation object from the given input path"""
    env_graph = EnvironmentGraph()
    simulation = LodusSimulation(env_graph)

    experiment_path = Path(__file__).parent.parent / "experiments"
    data_path =  Path(__file__).parent.parent / "data_input"

    experiment_config = load_json(experiment_path / f"{input_path}.json")
    input_files = experiment_config["envgraph_inputs_files"]

    simulation.experiment_config = experiment_config

    env_json = load_json(data_path / input_files["environment_file"])
    pop_json = load_json(data_path / input_files["population_file"])
    rot_json = load_json(data_path / input_files["routine_file"])

    population_template = { "traceable_properties": pop_json["default_traceable_characteristics"],
                    "sampled_properties": pop_json["sampled_characteristics_categories"]}
    
    characteristics_factory = CharacteristicsFactory()
    # Default values for traceable properties
    if 'traceable_properties' in population_template:
        tp = population_template['traceable_properties']
        for k in tp:
            characteristics_factory.add_traceable_characteristic(k, tp[k])

    # Default values for sampled properties
    if 'sampled_properties' in population_template:
        sp = population_template['sampled_properties']
        for k in sp:
            characteristics_factory.add_sampled_characteristic(k, sp[k])

    blob_factory = BlobFactory(characteristics_factory)
    simulation.original_block_template = characteristics_factory

    for reg_dict in env_json['regions']:
        create_region(env_graph, reg_dict, pop_json, rot_json, blob_factory)

    env_graph.set_spawning_nodes()
    env_graph.set_original_populations()

    add_global_actions(simulation, rot_json)

    return simulation

def load_json(file_path):
    """Load a json file from the given path"""
    with open(file_path, 'r', encoding='utf8') as file:
        return json.load(file)

def create_region(env_graph: EnvironmentGraph, 
                  region_description: dict, 
                  population_json: dict, 
                  routines_json: dict, 
                  blob_factory: BlobFactory):
    """Create a region from the given description and add it to the environment graph"""
    region_name = region_description['name']
    region_position = region_description['lng_lat']
    region_template = EnvRegionTemplate(region_name, region_position)

    for poi_dict in region_description['points_of_interest']:
        node_template = create_node_template(poi_dict, region_name, population_json, routines_json)
        region_template.add_envnode_template(node_template)

    env_graph.add_region(region_template, blob_factory)

def create_node_template(node_description: dict, 
                         region_name:str, 
                         population_json: dict, 
                         routines_json: dict):
    """ Create a node template from the given description"""
    node_type = node_description["poi_type"]
    node_unique_name = node_description["unique_name"]
    node_template = EnvNodeTemplate(node_type, node_unique_name)
    node_template.long_lat = node_description["lng_lat"]

    if "characteristics" in node_description:
        for a, b in node_description["characteristics"].items():
            node_template.add_node_attributes(a, b)

    poi_unique_name = f"{region_name}//{node_unique_name}"
    add_initial_populations(node_template, poi_unique_name, population_json)
    add_routines(node_template, poi_unique_name, routines_json)

    return node_template

def add_initial_populations(node_template: EnvNodeTemplate, poi_unique_name: str, population_json):
    if poi_unique_name in population_json["initial_population"]:
        for ip in population_json["initial_population"][poi_unique_name]:
            blob_template = BlobTemplate(
                population=ip["total_population"],
                traceable_characteristics=ip['traceable_characteristics'],
                sampled_characteristics=ip['sampled_characteristics']
            )
            node_template.add_blob_template(blob_template)

def add_routines(node_template: EnvNodeTemplate, poi_unique_name: str, routine_json):
    if poi_unique_name in routine_json["routines"]:
        for rt in routine_json["routines"][poi_unique_name]:
            pt = PopulationTemplate(
                sampled_characteristics=rt["action"]['population_template']["sampled_characteristics"],
                traceable_characteristics=rt["action"]['population_template']["traceable_characteristics"]
            )
            action = Action(
                action_type=rt["action"]['type'],
                values=rt["action"]['values'],
                pop_template=pt
            )
            node_template.add_action_to_routine_template(rt["cycle_step"], action)

def add_global_actions(simulation: LodusSimulation, routines_json):
    if 'global_routine' in routines_json:
        for rga in routines_json['global_routine']:
            action_type = rga['action']['type']
            pt = PopulationTemplate(
                sampled_characteristics=rga["action"]['population_template']["sampled_characteristics"],
                traceable_characteristics=rga["action"]['population_template']["traceable_characteristics"]
            )
            values = rga['action']['values']
            cycle_step = rga['cycle_step'] if isinstance(rga['cycle_step'], list) else int(rga['cycle_step'])
            
            simulation.add_global_action(GlobalAction(
                action_type=action_type,
                population_template=pt,
                values=values,
                cycle_step_definition=cycle_step
            ))


def parse_routines(data:dict):
    _global_actions = []
    _actions = []
    # Global Routines
    for _ga in data.get('global_routine', {}):
        if 'cycle_length' in _ga:
            _global_actions.append((int(_ga['cycle_length']),Action(_ga['type'], _ga['values'])))
        elif 'frames' in _ga:
            _global_actions.append(_ga['frames'], Action(_ga['type'], _ga['values']))
            #env.set_repeating_action(_ga['frames'], TimeAction(_ga['type'], _ga['values']))
        elif 'cycle_step' in _ga:
            pt = PopulationTemplate(
                    sampled_characteristics=_ga["action"]['population_template']["sampled_characteristics"],
                    traceable_characteristics=_ga["action"]['population_template']["traceable_characteristics"])
            if isinstance(_ga['cycle_step'], list):
                _global_actions.append((_ga['cycle_step'], 
                                        Action(action_type=_ga['action']['type'], 
                                                    pop_template=pt,
                                                    values=_ga['action']['values'])))
            else:
                _global_actions.append((int(_ga['cycle_step']), 
                                        Action(action_type=_ga['action']['type'], 
                                                    pop_template=pt,
                                                    values=_ga['action']['values'])))
    # EnvNode Routines
    for _node in data.get('routines', []):
        for _a in data['routines'][_node]:
            pt = PopulationTemplate(
                    sampled_characteristics=_a["action"]['population_template']["sampled_characteristics"],
                    traceable_characteristics=_a["action"]['population_template']["traceable_characteristics"])
            action = Action(action_type=_a["action"]['type'], 
                                values=_a["action"]['values'], 
                                pop_template=pt) 
            _actions.append((_a["cycle_step"], action))

    return _global_actions, _actions


