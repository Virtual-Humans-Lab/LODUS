import sys
sys.path.append('../')

import environment
from population import PopTemplate

class ReturnToPreviousPlugin(environment.TimeActionPlugin):

    def __init__(self, env_graph: environment.EnvironmentGraph):
        super().__init__()

        self.graph = env_graph
        self.set_pair('return_to_previous', self.return_to_previous)

    def update_time_step(self, cycle_step, simulation_step):
        return #super().update_time_step(cycle_step, simulation_step)

    def return_to_previous(self, values, hour, time):
        
        #assert('node_id' in values or ('region' in values and 'node' in values), 
        #       "No node_id or region/node pair defined in Return To Previous TimeAction")
        pop_prev = self.graph.get_population_size()
        #print(values)
        
        # Identifies the target node
        if 'node_id' in values:
            node_id = values['node_id']
            from_node = self.graph.get_node_by_id(node_id)
        else:
            from_region = self.graph.get_region_by_name(values['region'])
            from_node = from_region.get_node_by_name(values['node'])
            node_id = from_node.id
        
        pop_template = PopTemplate()
        if 'population_template' in values:
            pop_template = values['population_template']
        
        if 'blob_id' in values: 
            blob_id = values['blob_id']
            target_blob = None
            for x in from_node.contained_blobs:
                if x.blob_id == blob_id:
                    target_blob = x
            to_node = self.graph.get_node_by_id(target_blob.previous_node)
            grabbed = target_blob.grab_population(target_blob.get_population_size(pop_template), pop_template)
            
            grabbed.previous_node = from_node.id
            grabbed.frame_origin_node = from_node.id
                        
            to_node.add_blob(grabbed)
            from_node.remove_blob(grabbed)
        else:
            pop_md1 = self.graph.get_population_size()
            
            grabbed = from_node.grab_population(values['quantity'], pop_template)
            grabbed_size = sum([g1.get_population_size() for g1 in grabbed])
            #print(grabbed_size)
            for g in grabbed:
                to_node = self.graph.get_node_by_id(g.previous_node)
                g.frame_origin_node = from_node.id
                to_node.add_blob(g)
                #from_node.remove_blob(g)
        #print("node", node_id, "blob", blob_id, "pop_template", pop_template)
            
        #from_node = self.graph.get_node_by_id(node_id)
        
        
        pop_aft = self.graph.get_population_size()
        if pop_prev != pop_aft:
            print ("WTF", pop_prev, pop_md1, pop_aft, grabbed_size, 
                   from_node.get_unique_name(),to_node.get_unique_name(),values,'\n')
                
        return []