from itertools import count
from types import NoneType
from VaccineLocalPlugin import VaccinePlugin
import environment
from population import PopTemplate
import copy
from random_inst import FixedRandom
import math
import numpy as np
import csv
from simulation_logger import SimulationLogger
import util
import json

class NewInfectionPlugin(environment.TimeActionPlugin):
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
    def __init__(self, env_graph: environment.EnvironmentGraph, config_file_path, day_duration: int):

        super().__init__()
        
        # Set the time/frame variables
        self.day_duration = day_duration
        self.hour = 0
        self.time = 0
        self.current_day = 0
        
        # JSON file containing the configuration of the Infection Plugin
        self.config = json.loads(open(config_file_path ,'r').read())
        self.vacc_plugin:VaccinePlugin = None
        
        # Data from config file
        self.default_beta = self.config["default_beta"]
        self.default_gamma = self.config["default_gamma"]
        self.infection_multiplier = self.config["infection_multiplier"]
        self.removal_multiplier = self.config["removal_multiplier"]
        self.beta = self.default_beta
        self.gamma = self.default_gamma
        self.home_density = 1
        self.bus_density = 1
        self.count = 0
        self.infected = 0
        self.susceptible = 0
        self.removed = 0
        
        #, default_beta = 0.25, default_gamma = 0.08
        # Sets the 'infect' action
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
                
                   
        
        print("final Pop", self.graph.get_population_size())
        
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
        print("initial infected:", self.total_infected)
        
    def update_time_step(self, hour, time):
        # Updates time step data
        self.hour = hour
        self.time = time
        self.day = (time // self.day_duration) 
        self.vacc_plugin = self.graph.get_first_plugin(VaccinePlugin)
        # if hour == 0:
        #     self.dS_remainder_per_node = {n: 0.0 for n in self.graph.node_dict}
        #     self.dI_remainder_per_node = {n: 0.0 for n in self.graph.node_dict}
        
        # Add custom beta/gamma here here
    

    def move_with_infection(self, values, hour, time):

        origin_region = values['origin_region']
        if isinstance(origin_region, str):
            origin_region = self.graph.get_region_by_name(origin_region)

        origin_node = values['origin_node']
        if isinstance(origin_node, str):
            origin_node = origin_region.get_node_by_name(origin_node)

        destination_region = values['destination_region']
        if isinstance(destination_region, str):
            destination_region = self.graph.get_region_by_name(destination_region)

        destination_node = values['destination_node']
        if isinstance(destination_node, str):
            destination_node = destination_region.get_node_by_name(destination_node)

        beta = self.beta
        if isinstance(beta, str):
            beta = float(beta)
        self.beta = beta

        gamma = self.gamma
        if isinstance(gamma, str):
            gamma = float(gamma)
        self.gamma = gamma

        pop_template = values['population_template']

        quantity = values['quantity']
        if quantity == -1:
            quantity = origin_node.get_population_size(pop_template)
        
        
        grabbed_population = origin_node.grab_population(quantity, pop_template)
        
        for grab_pop in grabbed_population:
            if grab_pop.spawning_node is None:
                grab_pop.spawning_node = origin_node.id
                grab_pop.frame_origin_node = origin_node.id
                
            self.infect_moving_pop(grab_pop, self.bus_density, time, pop_template)

        destination_node.add_blobs(grabbed_population)

    def infect_moving_pop(self, blob, density, time, pop_template):
        pop_template_susc = copy.deepcopy(pop_template)
        pop_template_susc.add_block('susceptible')

        pop_template_inf = copy.deepcopy(pop_template)
        pop_template_inf.add_block('infected')

        pop_template_rem = copy.deepcopy(pop_template)
        pop_template_rem.add_block('removed')

        old_susceptible = blob.get_population_size(pop_template_susc)
        old_infected = blob.get_population_size(pop_template_inf)
        old_removed = blob.get_population_size(pop_template_rem)

        total = old_susceptible + old_infected + old_removed

        # TODO fix for empty nodes
        if total == 0:
            return

        self.susceptible = old_susceptible
        self.infected = old_infected
        self.removed = old_removed
        
        self.count = total

        self.new_infected = self.solve_infection(density)

        new_susceptible = int(self.susceptible)
        new_infected = int(self.infected)
        new_removed = total - new_susceptible - new_infected
        new_total = new_susceptible + new_infected + new_removed

        if not new_total == total:
            print('ops!! -> InfectionPlugin.infect_moving_pop total does not match!')
            input("press any key!")

        ### DO Susceptible -> Infected
        delta_susceptible = old_susceptible - new_susceptible
        blob.move_profile(delta_susceptible, pop_template, 'susceptible', 'infected')
        
        if delta_susceptible > 0:
            self.total_infected += delta_susceptible

        ### DO Infected -> Removed
        removed_quantity = max(new_removed - old_removed, 0)
        
        blob.move_profile(removed_quantity, pop_template, 'infected', 'removed')
        
    def infect(self, values, hour, time):
        
        assert ('region' in values and isinstance(values['region'], str), "No 'region' value defined")
        assert ('node' in values and isinstance(values['node'], str), "No 'node' value defined")
        assert ('frames' in values or 'cycle_length' in values)
        
        if 'frames' in values: 
            infections_per_day = len(values['frames'])
        else:
            infections_per_day = self.day_duration // values['cycle_length']
            
        # Gets the target region and node
        region = self.graph.get_region_by_name(values['region'])
        node = region.get_node_by_name(values['node'])
        if node.get_population_size() == 0: return

        # Sets some PopTemplates
        pop_template:PopTemplate = values['population_template']
        pt_sus = copy.deepcopy(pop_template)
        pt_sus.set_traceable_property('sir_status','susceptible')
        pt_inf = copy.deepcopy(pop_template)
        pt_inf.set_traceable_property('sir_status','infected')
        pt_rem = copy.deepcopy(pop_template)
        pt_rem.set_traceable_property('sir_status','removed')

        # Gets population sizes before infection
        prev_counts = [node.get_population_size(pt_sus),
                       node.get_population_size(pt_inf),
                       node.get_population_size(pt_rem)]
        prev_total = sum(prev_counts)

        # Infection operation
        abc = self.solve_infection_remainder(prev_counts, 
                                             node, 
                                             values,
                                             self.beta / infections_per_day,
                                             self.gamma / infections_per_day)
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
        
        if self.vacc_plugin is not None:
            new_blobs = []
            if to_inf > 0:
                i_grabbed = node.grab_population(to_inf, pt_sus)
                for b in i_grabbed:
                    _eff = self.vacc_plugin.get_blob_vacc_efficiency(b)
                    _pop = round(b.get_population_size() * (1.0 - _eff))
                    new_blobs.append(b.change_blob_traceable_property('sir_status', 'infected', _pop))
            if to_rem > 0:
                node.change_blobs_traceable_property('sir_status', 'removed', to_rem, pt_inf)
            node.add_blobs(new_blobs)
            
        else:
            node.change_blobs_traceable_property('sir_status', 'removed', to_rem, pt_inf)
            node.change_blobs_traceable_property('sir_status', 'infected', to_inf, pt_sus)

    def infect_population(self, values, hour, time):
        print("infect population")
        infect_values = {}
        infect_values['beta'] = values['beta']
        infect_values['gamma'] = values['gamma']

        infect_values['population_template'] = values['population_template']
        for region in values['region_list']:
            if isinstance(region, str):
                region = self.graph.get_region_by_name(region)

            infect_values['region'] = region

            for node in region.node_list:
                if isinstance(node, str):
                    node = region.get_node_by_name(node)

                infect_values['node'] = node
                self.infect(infect_values, hour, time)

    def solve_infection_remainder(self, _counts: list[int], _node: environment.EnvNode, values: dict, _beta:float, _gamma:float):
        
        if 'density' in _node.characteristics: 
            _density = _node.get_characteristic('density')
        else:
            _density = 1.0
        
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
    
    def solve_infection(self, _counts):
        
        Count = sum(_counts)
        Susceptible, Infected, Removed = _counts
        dS = -self.beta * Susceptible * Infected / Count
        #dI = -dS - self.gamma * Infected
        dI = (self.beta * Susceptible * Infected / Count) - (self.gamma * Infected)
        dR = self.gamma * Infected
        
        newS = Susceptible + int(round(dS))
        newI = Infected + int(round(dI))
        newR = Count - newS - newI
        
        return [[dS,dI,dR],[newS,newI,newR]]

    #### Logging Functions
    def setup_logger(self,logger:SimulationLogger):        
        self.logger = logger 
        if not self.logger: return
        
        self.log_file_infec = open(logger.base_path + "sir_status.csv", 'w', encoding='utf8')
        _header = 'Frame;Hour;Day'
        #for lvl in range(self.vacc_levels):
        #    _header += ";Vacc" + str(lvl)
        #for lvl in range(self.vacc_levels):
        #    _header += ";dVacc" + str(lvl)
        self.log_file_infec.write(_header + '\n')
        #self.last_frame = [0] * self.vacc_levels
        
        logger.global_custom_templates['Susceptible'] = self.pt_sus
        logger.global_custom_templates['Infected'] = self.pt_inf
        logger.global_custom_templates['Removed'] = self.pt_rem
        logger.region_custom_templates['Susceptible'] = self.pt_sus
        logger.region_custom_templates['Infected'] = self.pt_inf
        logger.region_custom_templates['Removed'] = self.pt_rem
        logger.node_custom_templates['Susceptible'] = self.pt_sus
        logger.node_custom_templates['Infected'] = self.pt_inf
        logger.node_custom_templates['Removed'] = self.pt_rem
        
        logger.add_custom_line_plot('SIR Status - Global', 
                                    file = 'global.csv',
                                    x_label="Frame", y_label="Population",
                                    columns= ['Susceptible', 'Infected', 'Removed'])
        
    def log_data(self, **kwargs):
        assert 'graph' in kwargs and 'frame' in kwargs, "Invalid inputs for logging"

    def stop_logger(self, **kwargs):
        self.log_file_infec.close()


if __name__ == "__main__":
    infection_plugin = NewInfectionPlugin(None)