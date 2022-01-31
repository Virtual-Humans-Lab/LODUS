import math
import json
from environment import *
from population import *

def DummyEnv():
    return ''


def DummyPop(env_graph):
    pass


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

        pop_factory = BlobFactory(block_template)
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

               
                for key, characteristic in node_value.items():
                   
                    # Add characteristics to the EnvNode
                    if key == 'characteristics':
                        for a, b in characteristic.items():
                            node_template.add_characteristic(a, b)

                    elif key == 'population_groups':
                        for group in characteristic:
                            node_template.add_blob_description(group['size'],group['traceable_properties'],group['description'], pop_factory
                            )

                    # Add TimeActions to the EnvNode
                    elif key == 'time_actions':
                        # Each Node description contains a list of frames
                        for frame_list in characteristic:
                            # Each frame contains a list of TimeActions
                            for frame_key, actions_list in frame_list.items():
                                node_actions = []
                                # Each TimeAction description in the actions list
                                for _a in actions_list:
                                    action = TimeAction(_a['type'], _a['values'])
                                    node_actions.append(action)
                                node_template.add_routine_template(frame_key, node_actions)


            region_template.add_template_node(node_k, node_template)
            
            env.add_region(region_description['world_position'], region_template, region_description['name'])
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

