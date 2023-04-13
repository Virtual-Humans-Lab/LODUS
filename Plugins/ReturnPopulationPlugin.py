import copy
import sys
from types import new_class
sys.path.append('../')

import environment 
from population import PopTemplate

class ReturnPopulationPlugin(environment.TimeActionPlugin):

    def __init__(self, env_graph: environment.EnvironmentGraph):
        '''gather_population
            Pushes population to nearby nodes into a requesting node.
                Params:
                    region: destination region.
                    node: destination node.
                    quantity: population size requested.
                    population_template: PopTemplate to be matched by the operation.

                    isolation_rate: the quantity to reduce movements by. simulates social isolation.
                    to_total_ratio_correction: corrects the ratio for gather_population operations, so that operations are based on the entire 
                        population of the node. a value between 0 and 1. However many % the original operation leaves in the node.
                    locals_only: forces gathering to only pull from native populations for each node.
                
                iso_mode: Can be:
                    'regular'
                        changes movement quantities following an isolation table.
                    'quantity_correction'
                        same as 'regular' but
                        corrects to assume the operation requested x% of the population, but wanted the entire population.
                    'random_nudge' 
                        fixed isolation rate with a random nudge to the isolation rate
        '''
        super().__init__()

        self.graph = env_graph
        self.set_pair('return_population_home', self.return_population_home)
        self.set_pair('send_population_back', self.send_population_back)


        ## returns everyone home
    def return_population_home(self, values, hour, time):
        # print(values)
        target_region = values['region']
        if isinstance(target_region, str):
            target_region = self.graph.get_region_by_name(target_region)

        node = values['node']
        if isinstance(node, str):
            node = target_region.get_node_by_name(node)
        
        pop_template = PopTemplate()
        if 'population_template' in values:
            pop_template = values['population_template']

        sub_list = []
        
        for region in self.graph.region_list:
            for origin_node in region.node_list:
                if node.id != origin_node.id:
                    new_action_values = {}
                    new_action_type = 'move_population'
                    
                    new_action_values['origin_region'] = region.name

                    # TODO placeholder 
                    new_action_values['origin_node'] = origin_node.name
                    new_action_values['destination_region'] = target_region.name

                    # TODO placeholder 
                    new_action_values['destination_node'] = node.name
                    
                    new_action_values['quantity'] = -1
                    pop_template.mother_blob_id = target_region.id
                    new_action_values['population_template'] = pop_template

                    new_action = environment.TimeAction(_type = new_action_type, _values = new_action_values)
                    self.graph.consume_time_action(new_action, hour, time)
                    # sub_list.append(new_action)
                    
        return sub_list
    
    def send_population_back(self, values, hour, time):
        #print(values)
        assert 'region' in values, "region is not defined in Gather Population TimeAction"
        assert 'node' in values, "node is not defined in Gather Population TimeAction"
        
        current_region = self.graph.get_region_by_name(values['region'])
        current_node = current_region.get_node_by_name(values['node'])
        
        

        sub_list = []
        for b in current_node.contained_blobs:
            pop_template = PopTemplate()
            if 'population_template' in values:
                pop_template = values['population_template']
            
            new_action_values = {}
            new_action_type = 'move_population'
            
            new_action_values['origin_region'] = current_region.name
            new_action_values['origin_node'] = current_node.name
            
            node_of_origin = self.graph.get_node_by_id(b.node_of_origin)
            region_of_origin = self.graph.get_region_by_name(node_of_origin.containing_region_name)
            # print(b.mother_blob_id, b.node_of_origin)
            # print(self.graph.get_node_by_id(b.node_of_origin).get_unique_name())
            # print(self.graph.get_region_by_id(b.mother_blob_id).name)
            
            new_action_values['destination_region'] = region_of_origin.name
            new_action_values['destination_node'] = node_of_origin.name
            
            new_action_values['quantity'] = values['quantity']
            pop_template.set_mother_blob_id(region_of_origin.id)
            new_action_values['population_template'] = pop_template
            #print(new_action_values)
            new_action = environment.TimeAction(_type = new_action_type, _values = new_action_values)
            sub_list.append(new_action)
        

        return sub_list