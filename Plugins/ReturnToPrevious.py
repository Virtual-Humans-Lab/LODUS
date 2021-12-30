import sys
sys.path.append('../')

import environment
from population import PopTemplate

class ReturnToPreviousPlugin(environment.TimeActionPlugin):

    def __init__(self, env_graph: environment.EnvironmentGraph):
        super().__init__()

        self.graph = env_graph
        self.set_pair('return_to_previous', self.return_to_previous)

    def return_to_previous(self, values, hour, time):
        
        node_id = values['node_id']
        blob_id = values['blob_id']
        pop_template = values["population_template"]
        #print("node", node_id, "blob", blob_id, "pop_template", pop_template)
            
        from_node = self.graph.get_node_by_id(node_id)
        target_blob = None
        for x in from_node.contained_blobs:
            if x.blob_id == blob_id:
                target_blob = x
        
        to_node = self.graph.get_node_by_id(target_blob.previous_node)
        grabbed = target_blob.grab_population(target_blob.get_population_size(pop_template), pop_template)
        
        grabbed.previous_node = from_node.id
        if grabbed.spawning_node is None:
            grabbed.spawning_node = from_node.id
            grabbed.frame_origin_node = from_node.id
                       
        to_node.add_blob(grabbed)
        from_node.remove_blob(grabbed)
                
        return []