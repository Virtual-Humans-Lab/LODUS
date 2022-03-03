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
        
        # Data from config file
        self.default_beta = self.config["default_beta"]
        self.default_gamma = self.config["default_gamma"]
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
        #self.set_pair('vaccinate', self.vaccinate)
        #self.env_graph.base_actions.add('vaccinate')

        # Sets two traceable properties for all blobs in the simulation
        self.graph.add_blobs_traceable_property("sir_status", 'susceptible')
        
        _custom_region_values = {tuple[0]:tuple[1] for tuple in self.config['custom_infection_values']}
        _custom_nodes = self.config['custom_infection_node_types']
        
        print("original Pop", self.graph.get_population_size())
        
        # Sets a number of infected people in the beginning of the simulation
        for _name,_reg in self.graph.region_dict.items():
            # If the EnvRegion has a custom infection value defined
            if _name in _custom_region_values:
                _quant = _custom_region_values[_name]
                for _node_name, _node in _reg.node_dict.items():
                    # Only the selected node types or all nodes when not defined
                    if len(_custom_nodes) == 0 or _node_name in _custom_nodes:
                        if isinstance(_quant,float): _quant = math.floor(_node.get_population_size() * _quant)
                        _node.change_blobs_traceable_property('sir_status', 'infected', _quant)
                        #_node.change_blobs_traceable_property('sir_status', 'infected', _quant)   
                        
            # Else, EnvRegion will be infected by the default amount (if defined) in the selected node
            elif self.config["default_infection_value"] > 0:
                _node = _reg.node_dict[self.config['default_infection_node']]
                _quant = self.config["default_infection_value"]
                if isinstance(_quant,float): _quant = math.floor(_node.get_population_size() * _quant)
                _node.change_blobs_traceable_property('sir_status', 'infected', _quant)
            
        
        print("final Pop", self.graph.get_population_size())
        

        pop_template_inf = PopTemplate()
        pop_template_inf.set_traceable_property('sir_status', 'infected')
        self.total_infected = self.graph.get_population_size(pop_template_inf)
        print("initial infected:", self.total_infected)
        
        
    def lalalala(self, env_graph, use_infect_move_pop = False, day_length = 24, default_beta = 0.25, default_gamma = 0.08):
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
        self.graph = env_graph
        self.set_pair('infect', self.infect)
        self.graph.base_actions.add('infect')
        self.set_pair('infect_population', self.infect_population)
        self.graph.base_actions.add('infect_population')
        self.set_pair('vaccinate', self.vaccinate)
        self.graph.base_actions.add('vaccinate')
        
        if use_infect_move_pop:
            print ("HEEEERE")
            self.graph.remove_action('move_population')
            self.set_pair('move_population', self.move_with_infection)

        self.default_beta = default_beta
        self.default_gamma = default_gamma
        self.beta = self.default_beta
        self.gamma = self.default_gamma
        self.count = 0
        self.infected = 0
        self.susceptible = 0
        self.removed = 0
        self.new_vaccinated = 0

        pop_template_inf = PopTemplate()
        pop_template_inf.add_block('infected')
        self.total_infected = self.graph.get_population_size(pop_template_inf)
        print("initial infected:", self.total_infected)

        pop_template_vac = PopTemplate()
        pop_template_vac.add_block('vaccinated')
        self.vaccinated = self.graph.get_population_size(pop_template_vac)
        print("initial vaccinated:", self.vaccinated)
       
        self.day_length = day_length

        self.home_density = 1
        self.bus_density = 1

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
        
        region = values['region']
        if isinstance(region, str):
            region = self.graph.get_region_by_name(region)

        node = values['node']
        if isinstance(node, str):
            node = region.get_node_by_name(node)

        #print(f'infect in region:{region.name}\tnode:{node.name}\tbeta:{self.beta}-gamma:{self.gamma}')

        pop_template = values['population_template']

        pop_template_susc = copy.deepcopy(pop_template)
        pop_template_susc.add_block('susceptible')
        
        pop_template_inf = copy.deepcopy(pop_template)
        pop_template_inf.add_block('infected')
        
        pop_template_rem = copy.deepcopy(pop_template)
        pop_template_rem.add_block('removed')

        pop_template_vac = copy.deepcopy(pop_template)
        pop_template_vac.add_block('vaccinated')

        old_susceptible = node.get_population_size(pop_template_susc)
        old_infected = node.get_population_size(pop_template_inf)
        old_removed = node.get_population_size(pop_template_rem)
        old_vaccinated = node.get_population_size(pop_template_vac)
        
        total = old_susceptible + old_infected + old_removed + old_vaccinated

        beforeS = node.get_population_size(pop_template_susc)
        beforeI = node.get_population_size(pop_template_inf)
        beforeR = node.get_population_size(pop_template_rem)
        beforeV = node.get_population_size(pop_template_vac)
        beforeT = beforeS + beforeI + beforeR + beforeV

        # TODO fix for empty nodes
        if total == 0:
            return

        
        self.count = total
        self.susceptible = old_susceptible
        self.infected = old_infected
        self.removed = old_removed
        self.vaccinated = old_vaccinated


        density=1
        abc = self.solve_infection(density)
        if (abc > 0):
            print("There is " + str(abc) + " newly infected")
        #self.new_infected = self.solve_infection(density)

        new_susceptible = int(self.susceptible)
        new_infected = int(self.infected)
        new_removed = int(self.removed)
        new_vaccinated = int(self.vaccinated)
        
        new_total = new_susceptible + new_infected + new_removed + new_vaccinated

        if new_total != total:
            print (str(total) + " |n : " +str(new_total) + " | v: " + str(self.vaccinated))
            print(f'oldT = {total}\tnewT = {new_total}')
            print(f'oldS = {old_susceptible}\tnewS = {new_susceptible}')
            print(f'oldI = {old_infected}\tnewI = {new_infected}')
            print(f'oldR = {old_removed}\tnewR = {new_removed}')
            print(f'oldV = {old_vaccinated}\tnewV = {new_vaccinated}')
            raise("Error - population size changed during infection.")

        ### DO Susceptible -> Infected
        tickets = []

        # TODO Can be optimized, use random.choices with weighted stuff
        # selects population to be moved from the population blobs witouht replacemente, weighted by blob size
        for i in range(len(node.contained_blobs)):
            blob = node.contained_blobs[i]
            for j in range(blob.get_population_size(pop_template_susc)):
                tickets.append(i)

        delta_susceptible = old_susceptible - new_susceptible
        if delta_susceptible > 0:
            self.total_infected += delta_susceptible

        # TODO can be optimized
        for i in range(delta_susceptible):
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
            rand = FixedRandom.instance.randint(0, len(tickets)-1)
            ticket = tickets[rand]
            blob = node.contained_blobs[ticket]
            blob.move_profile(1, pop_template, 'infected', 'removed')
            tickets.remove(ticket)


    def vaccinate3(self, values, hour, time):

        nodes = []

        for region in values['region_list']:
            if isinstance(region, str):
                region = self.graph.get_region_by_name(region)

            for node in region.node_list:
                if isinstance(node, str):
                    node = region.get_node_by_name(node)

                nodes.append(node)

        #print ("Vaccinating: " + str(values['quantity']) + " people")
        # All nodes present in nodes list
        pop_template = values['population_template']

        pop_template_susc = copy.deepcopy(pop_template)
        pop_template_susc.add_block('susceptible')

        pop_template_inf = copy.deepcopy(pop_template)
        pop_template_inf.add_block('infected')

        pop_template_rem = copy.deepcopy(pop_template)
        pop_template_rem.add_block('removed')

        pop_template_vac = copy.deepcopy(pop_template)
        pop_template_vac.add_block('vaccinated')
        


        total_vaccinated_today = 0

        while total_vaccinated_today < values['quantity'] and len(nodes) > 0:
            # Select one random node
            node_index = FixedRandom.instance.randint(0, len(nodes)-1)
            node = nodes[node_index]
            #print ("Selected Region: " + node.containing_region_name + "\t | Node: " + node.name + "\t | Population: " + str(node.get_population_size()))
            old_susceptible = node.get_population_size(pop_template_susc)
            if old_susceptible == 0:    # No more susceptibles in this node.
                del nodes[node_index]   # Remove it from list
                continue
            
            old_infected = node.get_population_size(pop_template_inf)
            old_removed = node.get_population_size(pop_template_rem)
            old_vaccinated = node.get_population_size(pop_template_vac)

            total = old_susceptible + old_infected + old_removed + old_vaccinated

            beforeS = node.get_population_size(pop_template_susc)
            beforeI = node.get_population_size(pop_template_inf)
            beforeR = node.get_population_size(pop_template_rem)
            beforeV = node.get_population_size(pop_template_vac)
            beforeT = beforeS + beforeI + beforeR + beforeV

            # TODO fix for empty nodes
            if total == 0:
                print ("Shouldn't enter here")
                continue

            if beforeT == 0:
                print ("Shouldn't enter here")
                continue

            #print ("Selected Region: " + node.containing_region_name + "\t | Node: " + node.name + "\t | Population: " + 
            #    str(node.get_population_size()) + "\t | Infected: " + str(node.get_population_size(pop_template_vac)))
            self.count = total
            self.susceptible = old_susceptible
            self.infected = old_infected
            self.removed = old_removed
            self.vaccinated = old_vaccinated
            #self.new_vaccinated = self.solve_vaccinate_one()

            to_be_vaccinated = self.solve_vaccinate_one()
            #print ("There is :" + str(to_be_vaccinated) + " newly vaccinated")

            self.new_vaccinated = to_be_vaccinated

            if self.new_vaccinated != 1:
                input("Press key!")

            #if self.new_vaccinated > 0:
            #    self.vaccinated += to_be_vaccinated
            
            total_vaccinated_today = total_vaccinated_today + to_be_vaccinated

            new_susceptible = int(self.susceptible)
            new_infected = int(self.infected)
            new_removed = int(self.removed)
            new_vaccinated = int(self.vaccinated) #+ old_vaccinated

            new_total = new_susceptible + new_infected + new_removed + new_vaccinated

            if new_total != total:
                print("Erro!!")
                print(f'oldT = {total}\tnewT = {new_total}')
                print(f'oldS = {old_susceptible}\tnewS = {new_susceptible}')
                print(f'oldI = {old_infected}\tnewI = {new_infected}')
                print(f'oldR = {old_removed}\tnewR = {new_removed}')
                print(f'oldV = {old_vaccinated}\tnewV = {new_vaccinated}')
                input("Press any key!")

            ### DO Susceptible -> Removed
            tickets = []

            # TODO Can be optimized, use random.choices with weighted stuff
            # selects population to be moved from the population blobs witouht replacemente, weighted by blob size
            for i in range(len(node.contained_blobs)):
                blob = node.contained_blobs[i]
                for j in range(blob.get_population_size(pop_template_susc)):
                    tickets.append(i)

            # TODO can be optimized
            if len(tickets) > 0:
                rand = FixedRandom.instance.randint(0, len(tickets) - 1)

                ticket = tickets[rand]
                blob = node.contained_blobs[ticket]
                blob.move_profile(1, pop_template, 'susceptible', 'vaccinated')
                tickets.remove(ticket)

            afterS = node.get_population_size(pop_template_susc)
            afterI = node.get_population_size(pop_template_inf)
            afterR = node.get_population_size(pop_template_rem)
            afterV = node.get_population_size(pop_template_vac)
            afterT = afterS + afterI + afterR + afterV
            # print("-----------")
            # print(f'oldT = {beforeT}\tnewT = {afterT}')
            # print(f'oldS = {beforeS}\tnewS = {afterS}')
            # print(f'oldI = {beforeI}\tnewI = {afterI}')
            # print(f'oldR = {beforeR}\tnewR = {afterR}')
            # print(f'oldV = {beforeV}\tnewV = {afterV}')
            # input("WTF")
            if beforeT != afterT:
                input("WTF")

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

    def solve_infection(self, ratio):
        Count = self.count
        Susceptible = self.susceptible
        Infected = self.infected
        Removed = self.removed

        dS = - self.beta * Infected * Susceptible / Count
        dI = -dS - self.gamma * Infected
        dR = self.gamma * Infected
        #print("Before" + str(self.susceptible))
        self.susceptible = Susceptible + int(round(dS))
        #print("After" + str(self.susceptible))
        self.removed = Removed + math.floor(dR)
        self.infected = Count - self.susceptible - self.removed - self.vaccinated

        new_infected = -int(round(dS))
        return new_infected

    def solve_vaccine(self, nu):
        Susceptible = self.susceptible
        Vaccinated = self.vaccinated

        self.nu = nu
        dS = - self.nu * Susceptible
        delta = int(round(dS))

        self.susceptible = Susceptible + delta
        self.vaccinated = Vaccinated - delta

        new_vaccinated = -delta
        return new_vaccinated

    def solve_vaccinate_one(self):
        if(self.susceptible > 0):
            self.susceptible = self.susceptible - 1
            self.vaccinated = self.vaccinated + 1
            return 1
        else:
            return 0


if __name__ == "__main__":
    vaccine_plugin = NewInfectionPlugin(None)