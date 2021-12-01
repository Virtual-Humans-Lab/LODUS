import environment
from population import PopTemplate
import copy
from random_inst import FixedRandom
import math
import numpy as np

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
    def __init__(self, env_graph, use_infect_move_pop = False, day_length = 24, default_beta = 0.25, default_gamma = 0.08):

        super().__init__()

        self.env_graph = env_graph
        self.set_pair('infect', self.infect)
        self.env_graph.base_actions.add('infect')
        self.set_pair('infect_population', self.infect_population)
        self.env_graph.base_actions.add('infect_population')
        #self.set_pair('vaccinate', self.vaccinate)
        #self.env_graph.base_actions.add('vaccinate')

        if use_infect_move_pop:
            self.env_graph.remove_action('move_population')
            self.set_pair('move_population', self.move_with_infection)

        self.default_beta = default_beta
        self.default_gamma = default_gamma
        self.beta = self.default_beta
        self.gamma = self.default_gamma
        self.count = 0
        self.infected = 0
        self.susceptible = 0
        self.removed = 0
        #self.new_vaccinated = 0

        pop_template_inf = PopTemplate()
        pop_template_inf.add_block('infected')
        self.total_infected = self.env_graph.get_population_size(pop_template_inf)
        print("initial infected:", self.total_infected)
        self.env_graph.