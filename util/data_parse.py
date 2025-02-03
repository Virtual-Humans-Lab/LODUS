import json
from pathlib import Path
from core.environment import *
from core.population import *
from core.routine import Action, GlobalAction
from core.simulator import LodusSimulation

def DummyEnv():
    return ''


def DummyPop(env_graph):
    pass

def generate_lodus_simulation(env_input: str):
    env_graph = EnvironmentGraph()
    simulation = LodusSimulation(env_graph)

    experiment_path = Path(__file__).parent.parent / "experiments"
    data_path =  Path(__file__).parent.parent / "data_input"

    experiment_config = load_json(experiment_path / f"{env_input}.json")
    input_files = experiment_config["envgraph_inputs_files"]

    simulation.experiment_config = experiment_config

    env_json = load_json(data_path / input_files["environment_file"])
    pop_json = load_json(data_path / input_files["population_file"])
    rot_json = load_json(data_path / input_files["routine_file"])

    population_template = { "traceable_properties": pop_json["default_traceable_characteristics"],
                    "sampled_properties": pop_json["sampled_characteristics_bins"]}
    
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
                  population_json, 
                  rot_json, 
                  blob_factory: BlobFactory):
    """Create a region from the given description and add it to the environment graph"""
    region_name = region_description['name']
    region_position = region_description['lng_lat']
    region_template = EnvRegionTemplate(region_name, region_position)

    for poi_dict in region_description['points_of_interest']:
        node_template = create_node_template(poi_dict, region_name, population_json, rot_json)
        region_template.add_envnode_template(node_template)

    env_graph.add_region(region_position, region_template, blob_factory)

def create_node_template(node_description: dict, 
                         region_name:str, 
                         population_json, 
                         routines_json):
    """ Create a node template from the given description"""
    node_name = node_description["name"]
    node_template = EnvNodeTemplate(node_name)
    node_template.long_lat = node_description["lng_lat"]

    if "characteristics" in node_description:
        for a, b in node_description["characteristics"].items():
            node_template.add_node_attributes(a, b)

    poi_unique_name = f"{region_name}//{node_name}"
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
            cycle_definiton = get_cycle_definition(rga)
            simulation.add_global_action(GlobalAction(
                action_type=action_type,
                population_template=pt,
                values=values,
                cycle_step_definition=cycle_definiton
            ))

def get_cycle_definition(rga):
    if 'cycle_length' in rga:
        return int(rga['cycle_length'])
    elif 'frames' in rga:
        return rga['frames']
    elif 'cycle_step' in rga and isinstance(rga['cycle_step'], list):
        return rga['cycle_step']
    else:
        return int(rga['cycle_step'])


def Generate_EnvironmentGraph(env_input: str) -> EnvironmentGraph:
    print("Generating EnvGraph with new parsing. Experiment Config File:", env_input)
    # if env_input == 'dummy':
    #     env = DummyEnv()
    #     populate_EnvironmentGraph('dummy', env)
    #     return env
    
    exp_path = Path(__file__).parent / "experiments"
    data_path =  Path(__file__).parent / "data_input"

    exp_config = json.load(open(exp_path / (env_input + ".json"), 'r', encoding='utf8'))
    input_files = exp_config["envgraph_inputs_files"]

    env_file = open(data_path / input_files["environment_file"],'r', encoding='utf8')
    pop_file = open(data_path / input_files["population_file"],'r', encoding='utf8')
    rot_file = open(data_path / input_files["routine_file"],'r', encoding='utf8')

    env_json = json.load(env_file)
    pop_json = json.load(pop_file)
    rot_json = json.load(rot_file)

    env = EnvironmentGraph()
    env.experiment_config = exp_config

    block_template = CharacteristicsFactory()
    pop_template = { "traceable_properties": pop_json["default_traceable_characteristics"],
                    "sampled_properties": pop_json["sampled_characteristics_bins"]}
    
    # Default values for traceable properties
    if 'traceable_properties' in pop_template:
        tp = pop_template['traceable_properties']
        for k in tp:
            block_template.add_traceable_characteristic(k, tp[k])

    # Default values for sampled properties
    if 'sampled_properties' in pop_template:
        sp = pop_template['sampled_properties']
        for k in sp:
            block_template.add_sampled_characteristic(k, sp[k])

    blob_factory = BlobFactory(block_template)
    env.original_block_template = block_template

    # Process repeating global actions
    if 'global_routine' in rot_json:
        repeating_global_actions = rot_json['global_routine']

        for rga in repeating_global_actions:
            pt = PopulationTemplate(sampled_characteristics=rga["action"]['population_template']["sampled_characteristics"],
                                        traceable_characteristics=rga["action"]['population_template']["traceable_characteristics"])
                
            if 'cycle_length' in rga:
                env.set_repeating_action(int(rga['cycle_length']), 
                                         Action(action_type=rga['action']['type'], 
                                                    pop_template=pt,
                                                    values=rga['action']['values']))
            elif 'frames' in rga:
                env.set_repeating_action(rga['frames'], Action(rga['type'], rga['values']))
            elif 'cycle_step' in rga:
                # pt = population.PopTemplate(
                #         sampled_properties=rga["action"]['population_template']["sampled_characteristics"],
                #         traceable_properties=rga["action"]['population_template']["traceable_characteristics"])
                if isinstance(rga['cycle_step'], list):
                    env.set_repeating_action(rga['cycle_step'], 
                                            Action(action_type=rga['action']['type'], 
                                                        pop_template=pt,
                                                        values=rga['action']['values']))
                else:
                    env.set_repeating_action(int(rga['cycle_step']), 
                                            Action(action_type=rga['action']['type'], 
                                                        pop_template=pt,
                                                        values=rga['action']['values']))


    # Creating Regions
    for reg_dict in env_json['regions']:
        region_name:str = reg_dict['name']
        region_position: list[float] = reg_dict['lng_lat']
        region_template = EnvRegionTemplate(region_name, region_position)

        # Creating each Point of Interest/Node
        for poi_dict in reg_dict['points_of_interest']:
            node_name = poi_dict["name"]
            node_template = EnvNodeTemplate(node_name)

            # Node Long-Lat position
            node_template.long_lat = poi_dict["lng_lat"]

            # Additional characteristics
            if "characteristics" in poi_dict:
                for a, b in poi_dict["characteristics"].items():
                    node_template.add_node_attributes(a, b)

            # Add initial populations:
            poi_unique_name = region_name + "//" + poi_dict["name"]
            
            if poi_unique_name in pop_json["initial_population"]:
                for ip in pop_json["initial_population"][poi_unique_name]:
                    blob_template = BlobTemplate(population=ip["total_population"],
                        traceable_characteristics=ip['traceable_characteristics'],
                        sampled_characteristics=ip['sampled_characteristics'])
                    node_template.add_blob_template(blob_template)

            # Add routines
            if poi_unique_name in rot_json["routines"]:
                for rt in rot_json["routines"][poi_unique_name]:
                    pt = PopulationTemplate(
                        sampled_characteristics=rt["action"]['population_template']["sampled_characteristics"],
                        traceable_characteristics=rt["action"]['population_template']["traceable_characteristics"])
                    action = Action(action_type=rt["action"]['type'], 
                                        values=rt["action"]['values'], 
                                        pop_template=pt)
                    node_template.add_action_to_routine_template(rt["cycle_step"], action)

            region_template.add_envnode_template(node_template)
        
        env.add_region(reg_dict['lng_lat'], region_template, blob_factory)
        env.region_list[-1].long_lat = reg_dict['lng_lat']
    env.set_spawning_nodes()
    env.set_original_populations()
    return env

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

def generate_EnvironmentGraph(env_input):

    if env_input == 'dummy':
        env = DummyEnv()
        populate_EnvironmentGraph('dummy', env)
        return env
    else:
        f = open(env_input,'r', encoding='utf8')
        s = f.read()

        descrip = json.loads(s)
        env = EnvironmentGraph()

        block_template = CharacteristicsFactory()
        pop_template = descrip['population_template']

        # Default values for traceable properties
        if 'traceable_properties' in pop_template:
            tp = pop_template['traceable_properties']
            for k in tp:
                block_template.add_traceable_characteristic(k, tp[k])

        # Default values for sampled properties
        if 'sampled_properties' in pop_template:
            sp = pop_template['sampled_properties']
            for k in sp:
                block_template.add_sampled_characteristic(k, sp[k])

        blob_factory = BlobFactory(block_template)
        env.original_block_template = block_template

        # Process repeating global actions
        if 'repeating_global_actions' in descrip:
            repeating_global_actions = descrip['repeating_global_actions']

            for rga in repeating_global_actions:
                if 'cycle_length' in rga:
                    env.set_repeating_action(int(rga['cycle_length']), Action(rga['type'], rga['values']))
                elif 'frames' in rga:
                    env.set_repeating_action(rga['frames'], Action(rga['type'], rga['values']))

        for region_description in descrip['regions']:
            region_template = EnvRegionTemplate()
            
            for node_k, node_value in region_description['nodes'].items():
                node_template = EnvNodeTemplate()
                node_template.long_lat = node_value["characteristics"]["long_lat_position"]
                for key, characteristic in node_value.items():
                    # Add characteristics to the EnvNode
                    if key == 'characteristics':
                        for a, b in characteristic.items():
                            node_template.add_characteristic(a, b)

                    elif key == 'population_groups':
                        for group in characteristic:
                            node_template.add_blob_template(group['size'],group['traceable_properties'],group['description'], blob_factory)

                    # Add TimeActions to the EnvNode
                    elif key == 'time_actions':
                        # Each frame contains a list of TimeActions
                        for frame_key, actions_list in characteristic.items():
                            node_actions = []
                            # Each TimeAction description in the actions list
                            for _a in actions_list:
                                pop_template = PopulationTemplate()
                                if 'population_template' in _a['values']:
                                    pop_template = PopulationTemplate(_a['values']['population_template'])
                                action = Action(action_type=_a['type'], 
                                                    pop_template=pop_template,
                                                    values=_a['values'])
                                node_actions.append(action)
                            node_template.add_actions_to_routine_template(frame_key, node_actions)

                region_template.add_envnode_template(node_k, node_template)
            
            env.add_region(region_description['long_lat_position'], region_template, region_description['name'])
            env.region_list[-1].long_lat = region_description['long_lat_position']

        env.set_spawning_nodes()
        return env


def populate_EnvRegion(region, blob_factory: BlobFactory, population, profiles):
    home_node: EnvNode = None
    for node in  region.node_list:
        if node.name == 'home':
            home_node = node
    blob = blob_factory.generate_blob_with_profile(region.id, population, profiles)
    home_node.add_blob(blob)

def populate_EnvNode(region: EnvRegionTemplate, node_template: EnvNodeTemplate, blob_factory: BlobFactory, population, profiles):
    blob = blob_factory.generate_blob_with_profile(region.id, population, profiles)
    node_template.blobs.append(blob)


def populate_EnvironmentGraph(pop_input, env_graph):
    if pop_input == 'dummy':
        DummyPop(env_graph)

    else:
        pass
        #process input population

def json_2_routine(input_json):
    pass

def json_2_blob(input_json):
    pass

def json_2_node(input_json):
    pass

def json_2_region(input_json):
    pass

