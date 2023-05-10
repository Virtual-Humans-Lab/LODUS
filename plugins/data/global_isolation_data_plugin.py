import environment


class GlobalIsolationDataPlugin(environment.TimeActionPlugin):

    def __init__(self, env_graph: environment.EnvironmentGraph):
        super().__init__()
        self.graph = env_graph

        # Loads experiment configuration, if any
        self.config:dict = self.graph.experiment_config.get("global_isolation_data_plugin", {})
        
        self.global_isolation:float = self.config.get("global_isolation", 0.0)
        self.graph.data_action_map["isolation"] = self.get_isolation
        print("Global Isolation", self.global_isolation)
       
    def update_time_step(self, cycle_step, simulation_step):
        return
    
    def get_isolation(self, region, node):
        return self.global_isolation