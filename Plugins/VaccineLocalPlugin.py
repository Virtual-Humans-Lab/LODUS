import environment
from population import PopTemplate
import copy
from random_inst import FixedRandom
import math
import csv
import util

class VaccinePlugin(environment.TimeActionPlugin):
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

    def __init__(self, env_graph: environment.EnvironmentGraph, vaccine_file_path, day_duration: int, start_offset: int = 0, multiplier: float = 1.0):
        super().__init__()
        
        self.DEBUG_VACC_DATA = True
        self.DEBUG_ALL_REGIONS = False
        self.DEBUG_REGIONS = []
        self.DEBUG_MOVE_PROFILE = False
        
        # Set the time/frame variables
        self.day_duration = day_duration
        self.hour = 0
        self.time = 0
        self.current_day = 0
        self.start_offset = start_offset
        print(f'Vaccine plugin loaded. Day duration is {day_duration}. Starting day offset is {start_offset}.')
        
        # Set the 'vaccinate' action (calls a gather_population), and the 'vaccine_move_profile' base action
        self.graph = env_graph
        #self.set_pair('vaccinate', self.vaccinate)
        self.set_pair('vaccinate2', self.vaccinate)
        self.set_pair('vaccine_move_profile', self.vaccine_move_profile)
        #self.graph.base_actions.add('vaccine_move_profile')
                
        # Get the total population of the simulation, and a dict of population per region
        self.total_population = self.graph.get_population_size()
        self.pop_per_region = {}
        self.vac_per_region = {}
        for r in self.graph.region_dict.keys():
            self.pop_per_region[r] = self.graph.region_dict[r].get_population_size()
            self.vac_per_region[r] = 0
                
        # Set a list of vaccines available per day
        self.vaccinations_per_day = 0
        self.remainder = 0.0
        self.prev_vac = 0
        self.vaccine_data = list()
        with open(vaccine_file_path) as csvfile:
            reader = csv.reader(csvfile)
            for row in reader:
                self.vaccine_data.append(int(int(row[0]) * multiplier))
        
        print(f'Vaccine days available: {len(self.vaccine_data)}')

    def update_time_step(self, hour, time):
        self.hour = hour
        self.time = time
        self.current_day = (time // self.day_duration) - self.start_offset
        if self.current_day >= 0:
            self.to_vaccinate = self.vaccine_data[self.current_day]
        else:
            self.to_vaccinate = 0
         
        if self.DEBUG_VACC_DATA:    
            print('------------------------')   
            print(f'Vaccine day {self.current_day}. Qnt to Vacc: {self.to_vaccinate}. Prev Vacc: {self.prev_vac}')
        
        weight_list = [pop/self.total_population for (pop) in self.pop_per_region.values()]
        int_weights = util.distribute_ints_from_weights(self.to_vaccinate, weight_list)
        self.vac_per_region = dict([(list(self.pop_per_region.keys())[i], int_weights[i]) for i in range(len(self.pop_per_region))])
        self.remainder_per_region = dict([(list(self.pop_per_region.keys())[i], 0.0) for i in range(len(self.pop_per_region))])
        self.prev_vac = 0
        self.remainder = 0.0


    def vaccinate2(self, values, hour, time):
        if values["node"] == "pharmacy":
            print(values["node_id"], hour, time)
            print(values)
        return []

    def vaccinate(self, values, hour, time):
        if self.to_vaccinate == 0:
            return []
        if "node_id" in values:
            target_node = self.graph.get_node_by_id(values['node_id'])
        else:
            print("node_id not defined in Vaccinate action.")
            return
        
        target_region = self.graph.get_region_by_name(target_node.containing_region_name)
        
        
        # if isinstance(values['origin_region'], str):
        #     target_region = self.graph.get_region_by_name(values['origin_region'])
        # else:
        #     print("origin_region not defined in Vaccinate action.")
        #     return
        
        # if isinstance(values['origin_node'], str):
        #     target_node = target_region.get_node_by_name(values['origin_node'])
        # else:
        #     print("origin_node not defined in Vaccinate action.")
        #     return
        
        # Calculates the number of people to be vaccinated in this node
        # based on a proportion of: region.pop/env.total_pop
        calls_per_day = len(values['frames'])
        to_vacc_float = float(self.vac_per_region[target_region.name]/calls_per_day) + self.remainder_per_region[target_region.name]
        self.remainder_per_region[target_region.name] = to_vacc_float % 1.0
        
        if self.DEBUG_ALL_REGIONS == True or target_region.name in self.DEBUG_REGIONS:
            print(f'remainder of {target_node.name}: {self.remainder_per_region[target_region.name]}')
        
        to_vacc = math.floor(to_vacc_float)
        if hour == list(values['frames'])[-1]:
            to_vacc = round(to_vacc_float)
        #print(to_vacc_float)
        #rg_proportion = self.pop_per_region[target_region.name]/self.total_population
        #vac_proportion = ((self.to_vaccinate*rg_proportion) + self.remainder)/calls_per_day
        #to_vacc = int(vac_proportion)
        #to_vacc = self.vac_per_region[target_region.name]
        #print (target_region.name, self.vac_per_region[target_region.name],self.remainder_per_region[target_region.name])
        # prev_vac track requests during the day
        # remainder is used in the next action to balance requests
        self.prev_vac += to_vacc
        
        if self.DEBUG_ALL_REGIONS == True or target_region.name in self.DEBUG_REGIONS:
            print(f'{target_region.name[:13]}: \t{target_region.get_population_size()} \tPharm pop: {target_node.get_population_size()}\tToVac: {to_vacc}')
            
        sub_list = []
        new_action_values = {}
        new_action_type = 'gather_population'
        new_action_values['destination_region'] = target_region.name
        new_action_values['destination_node'] = target_node.name
        new_action_values['quantity'] = to_vacc
        #new_action_values['only_locals'] = "true"
        new_action_values['different_node_name'] = "true"
        
        pop_template = PopTemplate()
        pop_template.add_block('susceptible')
        pop_template.add_block('infected')
        pop_template.add_block('removed')
        new_action_values['population_template'] = pop_template
        
        new_action = environment.TimeAction(_type = new_action_type, _values = new_action_values)
        self.graph.direct_action_invoke(new_action, hour, time)
        #self.graph.queue_next_frame_action(new_action)
        #sub_list.append(new_action)
        
        new_action_values = {}
        new_action_type = 'vaccine_move_profile'
        new_action_values['node_id'] = target_node.id
        new_action = environment.TimeAction(_type = new_action_type, _values = new_action_values)
        #self.graph.queue_next_frame_action(new_action)
        self.graph.direct_action_invoke(new_action, hour, time)
        #sub_list.append(new_action)
        return sub_list
        
    def vaccine_move_profile(self, values, hour, time):
        
        if isinstance(values['node_id'], int):
            target_node = self.graph.get_node_by_id(values['node_id'])
        else:
            print("origin_node not defined in vaccine_move_profile action.")
            return
        
        pt = PopTemplate()
        pt.add_block('vaccinated')
        prev_pop = target_node.get_population_size(pt)
        
        print("prev vacc: ", target_node.get_population_size(pt))
        # pt_i = PopTemplate()
        # pt_i.add_block('infected')
        # target_region = self.graph.get_region_by_name(target_node.containing_region_name)
        # print(f'{target_node.id} is {self.graph.get_node_by_id(target_node.id).containing_region_name}-{self.graph.get_node_by_id(target_node.id).name}')
        # if target_region.get_population_size(pt_i) > 0:
        #         print("-------",target_region.name,target_region.get_population_size(pt_i))
        
        sub_list = []
        
        
        #print("number of blobs", len(target_node.contained_blobs), [n.blob_id for n in target_node.contained_blobs])
        for n in target_node.contained_blobs:
            size = n.get_population_size()
            n.move_profile(size, PopTemplate(),'susceptible', 'vaccinated')
            n.move_profile(size, PopTemplate(),'infected', 'vaccinated')
            n.move_profile(size, PopTemplate(),'removed', 'vaccinated')
            
            new_action_type = 'return_to_previous'
            new_action_values = {}
            new_action_values['node_id'] = target_node.id
            new_action_values['blob_id'] = n.blob_id
            new_action_values['population_template'] = pt
            new_action = environment.TimeAction(_type = new_action_type, _values = new_action_values)
            #self.graph.direct_action_invoke(new_action,hour,time)
            #sub_list.append(new_action)
            #print(hour,self.graph.get_node_by_id(n.previous_node).name)
            
        if self.DEBUG_MOVE_PROFILE or target_node.containing_region_name in self.DEBUG_REGIONS:
            print(f'{(target_node.containing_region_name)[:12]:}   \t{target_node.get_population_size()}\t{prev_pop} -> {target_node.get_population_size(pt)}')
            
        #for x in sub_list:
        #    self.graph.direct_action_invoke(x,hour,time)  
        return sub_list

    def lalalala(self, env_graph, use_infect_move_pop = False, day_length = 24, default_beta = 0.25, default_gamma = 0.08):

        self.env_graph = env_graph
        self.set_pair('infect', self.infect)
        self.env_graph.base_actions.add('infect')
        self.set_pair('infect_population', self.infect_population)
        self.env_graph.base_actions.add('infect_population')
        self.set_pair('vaccinate', self.vaccinate)
        self.env_graph.base_actions.add('vaccinate')
        
        if use_infect_move_pop:
            print ("HEEEERE")
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
        self.new_vaccinated = 0

        pop_template_inf = PopTemplate()
        pop_template_inf.add_block('infected')
        self.total_infected = self.env_graph.get_population_size(pop_template_inf)
        print("initial infected:", self.total_infected)

        pop_template_vac = PopTemplate()
        pop_template_vac.add_block('vaccinated')
        self.vaccinated = self.env_graph.get_population_size(pop_template_vac)
        print("initial vaccinated:", self.vaccinated)
       
        self.day_length = day_length

        self.home_density = 1
        self.bus_density = 1

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
            region = self.env_graph.get_region_by_name(region)

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
                region = self.env_graph.get_region_by_name(region)

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
                region = self.env_graph.get_region_by_name(region)

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
    vaccine_plugin = VaccinePlugin(None)