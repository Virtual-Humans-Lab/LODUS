from itertools import count
from types import NoneType
# from time_actions.vaccine_local_plugin import VaccinePlugin
import environment
from population import PopTemplate
import copy
from random_inst import FixedRandom
import math
import numpy as np
import csv
# from loggers.population_count_logger import PopulationCountLogger
import util
import json

class InfectionPlugin(environment.TimeActionPlugin):
    ''' 
    This Plugin tmplements the SIR (Susceptible, Infected, Removed) model. 

    Requirements:
        The following Property Blocks:
            susceptible
            infected
            removed

    infect2
        Infects a population throughout the EnvGraph (moves them from S to I).

        Params:
            region : region of the node
            node : node to set desire
            beta : beta for infection equations
            gamma : gamma value for infection equation
            sigma : sigma value for infection equation
            mu: mu value for infection equation
            nu: nu value for infection equation
            population_template :  susceptible population. Block types should be empty.
    
    '''

    def __init__(self, env_graph: environment.EnvironmentGraph):

        super().__init__()
        self.__header:str = "Infection Plugin:"
    
        self.graph = env_graph

        # Loads isolation data, if available
        self.infection_beta_data_action = self.graph.data_action_map.get("infection_beta", None)
        self.infection_gamma_data_action = self.graph.data_action_map.get("infection_gamma", None)
        # assert not self.infection_beta_data_action or not self.infection_gamma_data_action, "Infection data actions weren't defined. Check if the correct plugins were loaded"
            
        # Loads experiment configuration, if any
        self.config:dict = self.graph.experiment_config.get("infection_plugin", {})
        self.default_beta:float = self.config.get("default_beta", 0.25)
        self.default_gamma:float = self.config.get("default_gamma", 0.08)
        self.infection_multiplier = self.config.get("infection_multiplier", 1.0)
        self.removal_multiplier = self.config.get("removal_multiplier", 1.0)
        
        # self.home_density = 1
        # self.bus_density = 1
        self.count = 0
        self.susceptible = 0
        self.infected = 0
        self.removed = 0

        # Sets the 'infect' action
        self.graph = env_graph
        self.set_pair('infect', self.infect)
        self.graph.base_actions.add('infect')
        self.set_pair('infect_population', self.infect_population)
        self.graph.base_actions.add('infect_population')
        # if self.config["use_infect_move_pop"]:
        #     self.graph.remove_action('move_population')
        #     self.set_pair('move_population', self.move_with_infection)


        # Sets a traceable properties for all blobs in the simulation
        self.graph.add_blobs_traceable_property("sir_status", 'susceptible')

        print("original Pop", self.graph.get_population_size())
        
        # Sets infection and recovery remainders for each node
        self.dS_remainder_per_node = {n: 0.0 for n in self.graph.node_dict}
        self.dI_remainder_per_node = {n: 0.0 for n in self.graph.node_dict}
        
        # Sets a number of infected people in the start of the simulation
        _custom_inf_values = {t[0]:t[1] for t in self.config['custom_infection_values']}
        for _name, _node in self.graph.node_dict.items():
            if _name in _custom_inf_values:
                _quant = _custom_inf_values[_name]
            elif _node.containing_region_name in _custom_inf_values:
                _quant = _custom_inf_values[_node.containing_region_name]
            elif _node.name in _custom_inf_values:
                _quant = _custom_inf_values[_node.name]
            else:
                _quant = self.config["default_infection_value"]
            if isinstance(_quant,float): _quant = math.floor(_node.get_population_size() * _quant)
            _node.change_blobs_traceable_property('sir_status', 'infected', _quant)
                
         
        # Sets PopTemplates to be used later
        self.pt_sus = PopTemplate()
        self.pt_sus.set_traceable_property("sir_status", 'susceptible')
        self.pt_inf = PopTemplate()
        self.pt_inf.set_traceable_property("sir_status", 'infected')
        self.pt_rem = PopTemplate()
        self.pt_rem.set_traceable_property("sir_status", 'removed')
        pop_template_inf = PopTemplate()
        pop_template_inf.set_traceable_property('sir_status', 'infected')
        self.total_infected = self.graph.get_population_size(pop_template_inf)
        print(self.__header, "initial infected:", self.total_infected)


        print(f"{self.__header} Default Infection Data:", 
              f"\n\tBeta {self.default_beta}; Gamma {self.default_gamma}", 
              f"\n\tInfection Mult {self.infection_multiplier}; Removal Mult {self.removal_multiplier}")
       
    def update_time_step(self, cycle_step:int, simulation_step:int):
        # Updates time step data
        self.cycle_length = self.graph.routine_cycle_length
        self.cycle_step = cycle_step
        self.simulation_step = simulation_step
        self.cycle = (simulation_step // self.cycle_length) 
        # self.vacc_plugin = self.graph.get_first_plugin(VaccinePlugin)
        # if hour == 0:
        #     self.dS_remainder_per_node = {n: 0.0 for n in self.graph.node_dict}
        #     self.dI_remainder_per_node = {n: 0.0 for n in self.graph.node_dict}
        
        # Add custom beta/gamma here here

    def infect(self, pop_template, values:dict, cycle_step:int, sim_step:int):
        
        assert ('region' in values and isinstance(values['region'], str), "No 'region' value defined")
        assert ('node' in values and isinstance(values['node'], str), "No 'node' value defined")
        assert ('frames' in values or 'cycle_length' in values)
     

    def infect_population(self, pop_template, values:dict, cycle_step:int, sim_step:int):
        print("infect population")
        infect_values = {}
        infect_values['beta'] = values['beta']
        infect_values['gamma'] = values['gamma']

     