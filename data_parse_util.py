import math
import json
from pathlib import Path
from environment import *
from population import *

def DummyEnv():
    return ''


def DummyPop(env_graph):
    pass


def Generate_EnvironmentGraph(env_input):
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

    block_template = BlockTemplate()
    pop_template = { "traceable_properties": pop_json["default_traceable_characteristics"],
                    "sampled_properties": pop_json["sampled_characteristics_bins"]}
    
    # Default values for traceable properties
    if 'traceable_properties' in pop_template:
        tp = pop_template['traceable_properties']
        for k in tp:
            block_template.add_traceable_property(k, tp[k])

    # Default values for sampled properties
    if 'sampled_properties' in pop_template:
        sp = pop_template['sampled_properties']
        for k in sp:
            block_template.add_bucket(k, sp[k])

    blob_factory = BlobFactory(block_template)
    env.original_block_template = block_template

    # Process repeating global actions
    if 'global_routine' in rot_json:
        repeating_global_actions = rot_json['global_routine']

        for rga in repeating_global_actions:
            if 'cycle_length' in rga:
                env.set_repeating_action(int(rga['cycle_length']), TimeAction(rga['type'], rga['values']))
            elif 'frames' in rga:
                env.set_repeating_action(rga['frames'], TimeAction(rga['type'], rga['values']))
            elif 'cycle_step' in rga:
                pt = population.PopTemplate(
                        sampled_properties=rga["action"]['population_template']["sampled_characteristics"],
                        traceable_properties=rga["action"]['population_template']["traceable_characteristics"])
                if isinstance(rga['cycle_step'], list):
                    env.set_repeating_action(rga['cycle_step'], 
                                            TimeAction(action_type=rga['action']['type'], 
                                                        pop_template=pt,
                                                        values=rga['action']['values']))
                else:
                    env.set_repeating_action(int(rga['cycle_step']), 
                                            TimeAction(action_type=rga['action']['type'], 
                                                        pop_template=pt,
                                                        values=rga['action']['values']))


    # Creating Regions
    for reg_dict in env_json['regions']:
        region_template = EnvRegionTemplate()

        # Creating each Point of Interest/Node
        for poi_dict in reg_dict['points_of_interest']:
            node_template = EnvNodeTemplate()

            # Node Long-Lat position
            node_template.long_lat = poi_dict["lng_lat"]

            # Additional characteristics
            if "characteristics" in poi_dict:
                for a, b in poi_dict["characteristics"].items():
                    node_template.add_characteristic(a, b)

            # Add initial populations:
            poi_unique_name = reg_dict["name"] + "//" + poi_dict["name"]
            
            if poi_unique_name in pop_json["initial_population"]:
                for ip in pop_json["initial_population"][poi_unique_name]:
                    node_template.add_blob_description(
                        population=ip["total_population"],
                        traceable_properties=ip['traceable_characteristics'],
                        description=ip['sampled_characteristics'], 
                        blob_factory=blob_factory)

            # Add routines
            if poi_unique_name in rot_json["routines"]:
                for rt in rot_json["routines"][poi_unique_name]:
                    pt = population.PopTemplate(
                        sampled_properties=rt["action"]['population_template']["sampled_characteristics"],
                        traceable_properties=rt["action"]['population_template']["traceable_characteristics"])
                    action = TimeAction(action_type=rt["action"]['type'], 
                                        values=rt["action"]['values'], 
                                        pop_template=pt)
                    node_template.add_action_to_template(rt["cycle_step"], action)

            region_template.add_template_node(poi_dict["name"], node_template)
        
        env.add_region(reg_dict['lng_lat'], region_template, reg_dict['name'])
        env.region_list[-1].long_lat = reg_dict['lng_lat']
    env.set_spawning_nodes()
    return env

def parse_routines(data:dict):
     
    _global_actions = []
    _actions = []
    # Global Routines
    for _ga in data.get('global_routine', {}):
        if 'cycle_length' in _ga:
            _global_actions.append((int(_ga['cycle_length']),TimeAction(_ga['type'], _ga['values'])))
        elif 'frames' in _ga:
            _global_actions.append(_ga['frames'], TimeAction(_ga['type'], _ga['values']))
            #env.set_repeating_action(_ga['frames'], TimeAction(_ga['type'], _ga['values']))
        elif 'cycle_step' in _ga:
            pt = population.PopTemplate(
                    sampled_properties=_ga["action"]['population_template']["sampled_characteristics"],
                    traceable_properties=_ga["action"]['population_template']["traceable_characteristics"])
            if isinstance(_ga['cycle_step'], list):
                _global_actions.append((_ga['cycle_step'], 
                                        TimeAction(action_type=_ga['action']['type'], 
                                                    pop_template=pt,
                                                    values=_ga['action']['values'])))
            else:
                _global_actions.append((int(_ga['cycle_step']), 
                                        TimeAction(action_type=_ga['action']['type'], 
                                                    pop_template=pt,
                                                    values=_ga['action']['values'])))
    # EnvNode Routines
    for _node in data.get('routines', []):
        for _a in data['routines'][_node]:
            pt = population.PopTemplate(
                    sampled_properties=_a["action"]['population_template']["sampled_characteristics"],
                    traceable_properties=_a["action"]['population_template']["traceable_characteristics"])
            action = TimeAction(action_type=_a["action"]['type'], 
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

        block_template = BlockTemplate()
        pop_template = descrip['population_template']

        # Default values for traceable properties
        if 'traceable_properties' in pop_template:
            tp = pop_template['traceable_properties']
            for k in tp:
                block_template.add_traceable_property(k, tp[k])

        # Default values for sampled properties
        if 'sampled_properties' in pop_template:
            sp = pop_template['sampled_properties']
            for k in sp:
                block_template.add_bucket(k, sp[k])

        blob_factory = BlobFactory(block_template)
        env.original_block_template = block_template

        # Process repeating global actions
        if 'repeating_global_actions' in descrip:
            repeating_global_actions = descrip['repeating_global_actions']

            for rga in repeating_global_actions:
                if 'cycle_length' in rga:
                    env.set_repeating_action(int(rga['cycle_length']), TimeAction(rga['type'], rga['values']))
                elif 'frames' in rga:
                    env.set_repeating_action(rga['frames'], TimeAction(rga['type'], rga['values']))

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
                            node_template.add_blob_description(group['size'],group['traceable_properties'],group['description'], blob_factory)

                    # Add TimeActions to the EnvNode
                    elif key == 'time_actions':
                        # Each frame contains a list of TimeActions
                        for frame_key, actions_list in characteristic.items():
                            node_actions = []
                            # Each TimeAction description in the actions list
                            for _a in actions_list:
                                pop_template = PopTemplate()
                                if 'population_template' in _a['values']:
                                    pop_template = PopTemplate(_a['values']['population_template'])
                                action = TimeAction(action_type=_a['type'], 
                                                    pop_template=pop_template,
                                                    values=_a['values'])
                                node_actions.append(action)
                            node_template.add_routine_template(frame_key, node_actions)

                region_template.add_template_node(node_k, node_template)
            
            env.add_region(region_description['long_lat_position'], region_template, region_description['name'])
            env.region_list[-1].long_lat = region_description['long_lat_position']

        env.set_spawning_nodes()
        return env


def populate_EnvRegion(region, blob_factory: BlobFactory, population, profiles):
    home_node: EnvNode = None
    for node in  region.node_list:
        if node.name == 'home':
            home_node = node
    blob = blob_factory.GenerateProfile(region.id, population, profiles)
    home_node.add_blob(blob)

def populate_EnvNode(region: EnvRegionTemplate, node_template: EnvNodeTemplate, blob_factory: BlobFactory, population, profiles):
    blob = blob_factory.GenerateProfile(region.id, population, profiles)
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

