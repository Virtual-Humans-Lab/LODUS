import sys
sys.path.append('../')

import environment 
from population import PopTemplate

class ExamplePlugin(environment.TimeActionPlugin):

    def __init__(self, env_graph):
        super().__init__()

        self.graph = env_graph
        self.set_pair('example_action', self.example_action)

        self.example_parameter = 'foo'

    def example_action(self, values, hour, time):
        region = values['region']
        if isinstance(region, str):
            region = self.graph.get_region_by_name(region)

        node = values['node']
        if isinstance(node, str):
            node = region.get_node_by_name(node)

        pop_template = values['population_template']

        new_action_values = {}
        new_action_type = 'move_population'
        new_action_values['origin_region'] = region.name
        new_action_values['origin_node'] = node.name
        new_action_values['destination_region'] = region.name
        new_action_values['destination_node'] = 'home'
        
        new_action_values['quantity'] = 100
        new_action_values['population_template'] = pop_template

        action = environment.TimeAction(_type = new_action_type, _values = new_action_values)

        return [action]
        