import sys
sys.path.append('../')
sys.path.append('../EpidemicContagionPython/EpidemicContagionPython/')

import environment
from population import PopTemplate
from  EpidemicPopulation import EpidemicPopulation
import copy
#import random
from random_inst import FixedRandom
import math
import numpy as np

def probabilistic_rounding(n):
    fractional = math.fmod(n, 1)
    whole = int(math.floor(n))

    #r = random.random()
    r = FixedRandom.instance.random()

    if r < fractional:
        whole += 1

    return whole

class InfectionPlugin(environment.TimeActionPlugin):
    '''
    Adds TimeActions to model infection behavior.
            Requires specific Property Blocks:
                susceptible
                infected
                removed

            infect
                infects population in a node.
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

    def __init__(self, env_graph, infect_mode = 0, use_infect_move_population = False, default_beta = 0.25, default_gamma = 0.08):
        super().__init__()

        self.env_graph = env_graph
        self.infection_solver = EpidemicPopulation(Count = 0, Infected = 0)
        self.set_pair('infect', self.infect)
        self.env_graph.base_actions.add('infect')

        if use_infect_move_population:
            self.env_graph.remove_action('move_population')
            self.set_pair('move_population', self.move_with_infection)

        self.default_beta = default_beta
        self.default_gamma =  default_gamma

        # 0 : density and rate infect
        # 1 : density day infect
        # 2 : density specific day infect
        self.infect_mode = infect_mode
        self.day_length = 24

        self.home_density = 0.021
        self.bus_density = 0.18

    def move_with_infection(self, values, hour, time):

        origin_region = values['origin_region']
        if isinstance(origin_region, str):
            origin_region = self.env_graph.get_region_by_name(origin_region)

        origin_node = values['origin_node']
        if isinstance(origin_node, str):
            origin_node = origin_region.get_node_by_name(origin_node)

        destination_region = values['destination_region']
        if isinstance(destination_region, str):
            destination_region = self.env_graph.get_region_by_name(destination_region)

        destination_node = values['destination_node']
        if isinstance(destination_node, str):
            destination_node = destination_region.get_node_by_name(destination_node)

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


        self.infection_solver.Count = total


        # TODO fix for empty nodes
        if total == 0:
            return

        self.infection_solver.Susceptible = old_susceptible
        self.infection_solver.Infected = old_infected
        self.infection_solver.Removed = old_removed

        if self.infect_mode == 0 :
            self.infection_solver.InfectWithDensityAndRate(density, self.default_beta, self.default_gamma)
        elif self.infect_mode == 1:
            self.infection_solver.InfectWithDensityAndDay(density, time // self.day_length)
        elif self.infect_mode == 2:
            self.infection_solver.InfectWithDensityAndDay(density, 25)

        new_susceptible = probabilistic_rounding(self.infection_solver.Susceptible)
        new_removed = probabilistic_rounding(self.infection_solver.Removed)
        new_infected = probabilistic_rounding(self.infection_solver.Infected)

        new_total = new_susceptible + new_infected + new_removed

        # TODO fix the janky fix
        # TODO redo selection until it works right....  change this 
        while total != new_total:
            new_susceptible = probabilistic_rounding(self.infection_solver.Susceptible)
            new_removed = probabilistic_rounding(self.infection_solver.Removed)
            new_infected = probabilistic_rounding(self.infection_solver.Infected)

            new_total = new_susceptible + new_infected + new_removed


        ### DO Susceptible -> Infected
        # TODO Can be optimized, use random.choices with weighted stuff
        # selects population to be moved from the population blobs witouht replacemente, weighted by blob size

        delta_susceptible = old_susceptible - new_susceptible


        # TODO can be optimized
        blob.move_profile(delta_susceptible, pop_template, 'susceptible', 'infected')

        ### DO Infected -> Removed

        removed_quantity = max(new_removed - old_removed, 0)

        blob.move_profile(removed_quantity, pop_template, 'infected', 'removed')


    def infect(self, values, hour, time):
        region = values['region']
        if isinstance(region, str):
            region = self.env_graph.get_region_by_name(region)

        node = values['node']
        if isinstance(node, str):
            node = region.get_node_by_name(node)

        beta = float(values['beta'])
        gamma = float(values['gamma'])
        #sigma = float(values['sigma'])
        mu = float(values['mu'])
        nu = float(values['nu'])
        pop_template = values['population_template']
    
        
        pop_template_susc = copy.deepcopy(pop_template)
        pop_template_susc.add_block('susceptible')

        pop_template_inf = copy.deepcopy(pop_template)
        pop_template_inf.add_block('infected')

        pop_template_rem = copy.deepcopy(pop_template)
        pop_template_rem.add_block('removed')

        old_susceptible = node.get_population_size(pop_template_susc)
        old_infected = node.get_population_size(pop_template_inf)
        old_removed = node.get_population_size(pop_template_rem)



        total = old_susceptible + old_infected + old_removed

        self.infection_solver.Count = total


        # TODO fix for empty nodes
        if total == 0:
            return

        self.infection_solver.Susceptible = old_susceptible
        self.infection_solver.Infected = old_infected
        self.infection_solver.Removed = old_removed

        if self.infect_mode == 1 :
            self.infection_solver.InfectWithDensityAndRate(self.home_density, beta, gamma)
        elif self.infect_mode == 2:
            self.infection_solver.InfectWithDensityAndDay(self.home_density, time // self.day_length)
        elif self.infect_mode == 3:
            self.infection_solver.InfectWithDensityAndDay(self.home_density, 25)
        #print(self.infection_solver.Susceptible, self.infection_solver.Removed, self.infection_solver.Infected)


        new_susceptible = probabilistic_rounding(self.infection_solver.Susceptible)
        new_removed = probabilistic_rounding(self.infection_solver.Removed)
        new_infected = probabilistic_rounding(self.infection_solver.Infected)

        new_total = new_susceptible + new_infected + new_removed

        # TODO fix the janky fix
        # TODO redo selection until it works right....  change this 
        while total != new_total:
            new_susceptible = probabilistic_rounding(self.infection_solver.Susceptible)
            new_removed = probabilistic_rounding(self.infection_solver.Removed)
            new_infected = probabilistic_rounding(self.infection_solver.Infected)

            new_total = new_susceptible + new_infected + new_removed

        #print(region.name, node.name, beta, '\n' , "\told_susc", old_susceptible, "old_inf", old_infected, "old_rem", old_removed,
        #                                    "\n\tnew_susc", new_susceptible, "new_inf", new_infected, "new_rem", new_removed, total == new_total)


        ### DO Susceptible -> Infected
        tickets = []

        # TODO Can be optimized, use random.choices with weighted stuff
        # selects population to be moved from the population blobs witouht replacemente, weighted by blob size
        for i in range(len(node.contained_blobs)):
            blob = node.contained_blobs[i]
            for j in range(blob.get_population_size(pop_template_susc)):
                tickets.append(i)

        delta_susceptible = old_susceptible - new_susceptible

        # TODO can be optimized
        for i in range(delta_susceptible):
            #rand = random.randint(0, len(tickets)-1)
            rand = FixedRandom.instance.randint(0, len(tickets)-1)
            ticket = tickets[rand]
            blob = node.contained_blobs[ticket]
            blob.move_profile(1, pop_template, 'susceptible', 'infected')
            tickets.remove(ticket)

        ### DO Infected -> Removed
        tickets = []

        # TODO Can be optimized
        for i in range(len(node.contained_blobs)):
            blob = node.contained_blobs[i]
            for j in range(blob.get_population_size(pop_template_inf)):
                tickets.append(i)

        removed_quantity = max(new_removed - old_removed, 0)

        # TODO can be optimized
        for i in range(removed_quantity):
            #rand = random.randint(0, len(tickets)-1)
            rand = FixedRandom.instance.randint(0, len(tickets)-1)
            ticket = tickets[rand]
            blob = node.contained_blobs[ticket]
            blob.move_profile(1, pop_template, 'infected', 'removed')
            tickets.remove(ticket)



if __name__ == "__main__":
    infection_plugin = InfectionPlugin(None)