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
        pop_buckets = descrip['population_template']
        for k in pop_buckets:
            block_template.add_bucket(k, pop_buckets[k])
        block_keys = descrip['block_types']
        pop_factory = BlobFactory(block_keys, block_template)

        if 'repeating_global_actions' in descrip:
            repeating_global_actions = descrip['repeating_global_actions']

            for rga in repeating_global_actions:
                env.set_repeating_action(int(rga['cycle_length']), TimeAction(rga['type'], rga['values']))

        for region_description in descrip['regions']:
            region_template = EnvRegionTemplate()
            region_profile = region_description['population_description']
            for node_k, node_value in region_description['nodes'].items():
                node_template = EnvNodeTemplate()
                for key, characteristic in node_value.items():
                    
                    if key == 'characteristics':
                        for a, b in characteristic.items():
                            node_template.add_characteristic(a, b)
                    else:
                        actions = []
                        for a in characteristic:
                            
                            action = TimeAction(a['type'], a['values'])
                            actions.append(action)
                        node_template.add_routine_template(key, actions)
                region_template.add_template_node(node_k, node_template)

            #env.add_region(region_description['long_lat_position'],
            env.add_region(region_description['world_position'],
                           sum(region_description['population']), region_template, region_description['name'])
            env.region_list[-1].long_lat = region_description['long_lat_position']
            populate_EnvRegion(env.region_list[-1],
                               pop_factory,
                               region_description['population'], 
                               region_profile)
        env.set_spawning_nodes()
        return env


def populate_EnvRegion(region, blob_factory, populations, profiles):
    home_node = None
    for node in  region.node_list:
        if node.name == 'home':
            home_node = node
    pop_profiles = []

    for key in blob_factory.block_keys:
        if key in profiles:
            pop_profiles.append(profiles[key])
        else:
            pop_profiles.append(dict())

    blob = blob_factory.GenerateProfile(region.id, populations, pop_profiles)

    home_node.add_blob(blob)


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

