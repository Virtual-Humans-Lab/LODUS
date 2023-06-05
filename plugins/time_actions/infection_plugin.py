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
        self.vaccine_efficiency_data_action = self.graph.data_action_map.get("vaccine_efficiency", None)
        # assert not self.infection_beta_data_action or not self.infection_gamma_data_action, "Infection data actions weren't defined. Check if the correct plugins were loaded"
            
        # Loads experiment configuration, if any
        self.config:dict = self.graph.experiment_config.get("infection_plugin", {})
        self.default_beta:float = self.config.get("default_beta", 0.25)
        self.default_gamma:float = self.config.get("default_gamma", 0.08)
        self.infection_multiplier = self.config.get("infection_multiplier", 1.0)
        self.removal_multiplier = self.config.get("removal_multiplier", 1.0)

        _initial_infected_template_dict = self.config.get("initial_infected_template", {
                                                            "traceable_characteristics": {},
                                                            "sampled_characteristics": {}})
        self.initial_infected_template = PopTemplate(sampled_properties = _initial_infected_template_dict["sampled_characteristics"],
                                                     traceable_properties= _initial_infected_template_dict["traceable_characteristics"])
        self.initial_infected_default = self.config.get("initial_infected_default", 100)
        self.inicial_infected_custom = self.config.get("custom_initial_infected", [])

        # Loads density data, if available
        self.node_density_data_action = self.graph.data_action_map.get("node_density", None)


        # self.home_density = 1
        # self.bus_density = 1
        self.count = 0
        self.susceptible = 0
        self.infected = 0
        self.removed = 0

        # Sets the 'infect' actions
        self.graph = env_graph
        self.set_pair('infect', self.infect)
        self.graph.base_actions.add('infect')
        self.set_pair('infect_population', self.infect_population)
        self.graph.base_actions.add('infect_population')
        if self.config["use_infect_move_pop"]:
            self.graph.remove_action('move_population')
            self.set_pair('move_population', self.move_with_infection)


        # Sets a traceable properties for all blobs in the simulation
        self.graph.add_blobs_traceable_property("sir_status", 'susceptible')

        print("original Pop", self.graph.get_population_size())
        
        # Sets infection and recovery remainders for each node
        self.dS_remainder_per_node = {n: 0.0 for n in self.graph.node_dict}
        self.dI_remainder_per_node = {n: 0.0 for n in self.graph.node_dict}
        
        # Sets a number of infected people in the start of the simulation
        _custom_inf_values = {t[0]:t[1] for t in self.config.get('initial_infected_custom', ())}
        for _name, _node in self.graph.node_dict.items():
            if _name in _custom_inf_values: # unique_name in list
                _quant = _custom_inf_values[_name]
            elif _node.containing_region_name in _custom_inf_values: # region name in list
                _quant = _custom_inf_values[_node.containing_region_name]
            elif _node.name in _custom_inf_values: # noty type in list
                _quant = _custom_inf_values[_node.name]
            else: # default
                _quant = self.initial_infected_default
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

        # self.sum_susceptible = self.graph.s
        self.sum_infected = self.graph.get_population_size(self.pt_inf)
        # self.sum_removed = self.graph.get_population_size(self.pt_rem)

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
        
        assert 'region' in values and isinstance(values['region'], str), "No 'region' value defined"
        assert 'node' in values and isinstance(values['node'], str), "No 'node' value defined"
        assert 'frames' in values or 'cycle_length' in values, "No 'frames' or 'cycle_length value defined"
     
        if 'frames' in values: 
            infections_per_day = len(values['frames'])
        else:
            infections_per_day = self.cycle_length // values['cycle_length']

        # Gets the target region and node
        acting_region = self.graph.get_region_by_name(values['region'])
        acting_node = acting_region.get_node_by_name(values['node'])
        if acting_node.get_population_size() == 0: return

        # Load beta and gamma from data actions (if available)
        if self.infection_beta_data_action:
            _beta = self.infection_beta_data_action(acting_region, acting_node)
        else:
            _beta = self.default_beta
        if self.infection_gamma_data_action:
            _gamma = self.infection_gamma_data_action(acting_region, acting_node)
        else:
            _gamma = self.default_gamma
        # Loads optional action parameters, otherwise, use default values
        _beta = values.get("infection_beta", _beta)
        _gamma = values.get("infection_gamma", _gamma)

        # Sets some PopTemplates for this operation
        pt_sus:PopTemplate = copy.deepcopy(pop_template)
        pt_sus.set_traceable_property('sir_status','susceptible')
        pt_inf:PopTemplate = copy.deepcopy(pop_template)
        pt_inf.set_traceable_property('sir_status','infected')
        pt_rem:PopTemplate = copy.deepcopy(pop_template)
        pt_rem.set_traceable_property('sir_status','removed')

        # Gets population sizes before infection
        prev_counts = [acting_node.get_population_size(pt_sus),
                       acting_node.get_population_size(pt_inf),
                       acting_node.get_population_size(pt_rem)]
        prev_total = sum(prev_counts)

        # print(cycle_step, "infections per day", infections_per_day, values)
        # exit()

        # Infection operation
        # print("beta", _beta, "gamma", _gamma)
        abc = self.solve_infection_remainder(_counts = prev_counts,
                                             _region = acting_region, 
                                             _node = acting_node, 
                                             _beta =_beta / infections_per_day,
                                             _gamma = _gamma / infections_per_day)
        #abc = self.solve_infection(prev_counts)
            
        # if node.get_unique_name() == 'Azenha//home':
        #    print(abc)
        new_counts = abc[1]
        new_total = sum(new_counts)

        if new_total != prev_total:
            raise("Error - population size changed during infection.")
        
        # Populations to be changed
        to_inf = abs(new_counts[0] - prev_counts[0])
        to_rem = new_counts[2] - prev_counts[2]
        
        if to_inf <= 0 and to_rem <= 0:
            return
        
        if self.vaccine_efficiency_data_action is not None:
            if to_rem > 0:
                acting_node.change_blobs_traceable_property('sir_status', 'removed', to_rem, pt_inf)
            if to_inf > 0:
                i_grabbed = acting_node.grab_population(to_inf, pt_sus)
                acting_node.add_blobs(i_grabbed)
                for b in i_grabbed:
                    _eff = self.vaccine_efficiency_data_action(b)
                    _quant_after_eff = round(b.get_population_size() * (1.0 - _eff))
                    acting_node.change_blob_traceable_property(b, 'sir_status', 'infected', _quant_after_eff)
                    self.sum_infected += _quant_after_eff
                      
        else:
            acting_node.change_blobs_traceable_property('sir_status', 'removed', to_rem, pt_inf)
            acting_node.change_blobs_traceable_property('sir_status', 'infected', to_inf, pt_sus)
            self.sum_infected += to_inf



    def infect_population(self, pop_template, values:dict, cycle_step:int, sim_step:int):
        print("infect population")
        infect_values = {}
        infect_values['beta'] = values['beta']
        infect_values['gamma'] = values['gamma']

    def solve_infection_remainder(self, 
                                  _counts: list[int], 
                                  _region: environment.EnvRegion,
                                  _node: environment.EnvNode, 
                                  _beta:float, 
                                  _gamma:float):
        
        if self.node_density_data_action:
            _density = self.node_density_data_action(_region, _node)
        else:
            _density = 1.0
        print(_density, _node.get_unique_name())
        _node_name = _node.get_unique_name()
        _total = sum(_counts)
        _sus, _inf, _rem = _counts
        
        # Shared equations
        _sus_to_inf = _beta * _sus * _inf * self.infection_multiplier * _density / _total
        _inf_to_rem = _gamma * _inf * self.removal_multiplier
        
        # Calculates deltas based on SIR model - with multipliers
        dS = -_sus_to_inf
        dI = _sus_to_inf - _inf_to_rem
        dR = _inf_to_rem
        # print(_node_name, _counts,_beta,_gamma,dI,dR)
        
        # Adds remainders of previous operations in EnvNode
        dS = dS + self.dS_remainder_per_node[_node_name]
        dI = dI + self.dI_remainder_per_node[_node_name]
                
        # Gets integers from deltas
        dS_int, dI_int = math.ceil(dS), math.floor(dI)
        dR_int = - dS_int - dI_int 
        assert (dS_int + dI_int + dR_int) == 0, "Infection deltas sum not matching"
        
        # Sets remainders for future operations
        self.dS_remainder_per_node[_node_name] = dS % -1.0
        self.dI_remainder_per_node[_node_name] = dI % 1.0
        
        # New totals
        newS = _sus + dS_int
        newI = _inf + dI_int
        newR = _total - newS - newI
        return ([dS_int, dI_int, dR_int],[newS, newI, newR])
    
     