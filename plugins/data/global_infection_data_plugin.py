import environment


class GlobalInfectionDataPlugin(environment.TimeActionPlugin):

    def __init__(self, env_graph: environment.EnvironmentGraph):
        super().__init__()
        self.graph = env_graph

        # Loads experiment configuration, if any
        self.config:dict = self.graph.experiment_config.get("global_infection_data_plugin", {})
        
        self.global_beta:float = self.config.get("global_beta", 0.0)
        self.global_gamma:float = self.config.get("global_gamma", 0.0)
        self.graph.data_action_map["infection_beta"] = self.get_infection_beta
        self.graph.data_action_map["infection_gamma"] = self.get_infection_gamma
        
    def update_time_step(self, cycle_step, simulation_step):
        return
    
    def get_infection_beta(self, region, node):
        return self.global_beta
    
    def get_infection_gamma(self, region, node):
        return self.global_gamma