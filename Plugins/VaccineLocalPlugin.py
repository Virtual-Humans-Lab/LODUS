import environment
from population import Blob, PopTemplate
import copy
from random_inst import FixedRandom
import math
import csv
from simulation_logger import SimulationLogger
import util
import json

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

    def __init__(self, env_graph: environment.EnvironmentGraph, config_file_path, day_duration: int):
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
        
        # JSON file containing the configuration of the Vaccine Plugin
        self.config = json.loads(open(config_file_path ,'r').read())
        
        # Data from config file
        self.vacc_levels:int = self.config["number_of_vaccine_levels"]
        self.dosages:int = self.vacc_levels - 1
        self.dosage_offsets:list[int] = self.config["dosage_starting_day_offsets"]
        self.efficiency_per_level:list[int] = self.config["efficiency_per_level"]
        self.vacc_multiplier:float = self.config["number_of_vaccines_multiplier"]
        assert (self.vacc_levels == len(self.efficiency_per_level)), "\"vaccine_levels\" should be equal to length of \"efficiency_per_level\" in the configuration file."
        assert (self.dosages == len(self.dosage_offsets)), "\"vaccine_levels\" should be 1 higher than length of \"efficiency_per_level\" in the configuration file."
        print(f'\nVaccine plugin loaded. {self.dosages} dosages available ({self.vacc_levels} levels). Day duration is {day_duration}. Starting days offset is {self.dosage_offsets}.')
        
        # Set a list of vaccines available per day
        self.vaccine_data = list()
        with open(self.config["vaccinations_per_day_data"]) as csvfile:
            reader = csv.reader(csvfile)
            for row in reader:
                self.vaccine_data.append(int(int(row[0]) * self.vacc_multiplier))
        assert len(self.vaccine_data) > 0, "No vaccine data available"
        print(f'\nVaccine days available: {len(self.vaccine_data)}')
        
        # Set the 'vaccinate' action (calls a gather_population), and the 'change_vaccine_level' (which calls a return_to_previous) action
        self.graph = env_graph
        self.set_pair('vaccinate', self.vaccinate)
        self.set_pair('change_vaccine_level', self.change_vaccine_level)
        
        # Sets two traceable properties for all blobs in the simulation
        self.graph.add_blobs_traceable_property("vaccine_level", 0)
        self.graph.add_blobs_traceable_property("days_since_last_vaccine", 0)
        
        # Get the total population of the simulation, and sets a dict of population per region and vaccines to be dealt at each region at that day
        self.total_population = self.graph.get_population_size()
        self.pop_per_region = {k: r.get_population_size() for k,r in self.graph.region_dict.items()}
        self.vacc_per_region = {r: [0] * self.dosages for r in self.graph.region_dict}
        self.remainder_per_region = {r: [0.0] * self.dosages for r in self.graph.region_dict}
        
        # Lists for number of vaccines per dosage per day, and vaccines given in the previous day
        self.to_vaccinate_per_dose = [0] * self.dosages
        self.prev_vac = [0] * self.dosages
        

    def update_time_step(self, hour, time):
        # Updates time step data
        self.hour = hour
        self.time = time
        self.current_day = (time // self.day_duration) - self.dosage_offsets[0]
        self.day = (time // self.day_duration)
        
        # Increases the days_since_last_vaccine for all blobs
        if self.day > 0:
            self.graph.lambda_blobs_traceable_property("days_since_last_vaccine", lambda b,v:v+1 if b.traceable_properties["vaccine_level"] < self.dosages else 0)
        
        # Checks vaccines available for each dosage
        for dose_index,starting_day in enumerate(self.dosage_offsets):
            _dose_offset = self.day - starting_day
            
            # Vaccination not started for this dose_index or offset bigger than available data (i.e. used all day entries for that dose_index)
            if _dose_offset < 0 or _dose_offset > len(self.vaccine_data):
                self.to_vaccinate_per_dose[dose_index] = 0
            # Vaccine data available for this dose_index
            else:
                self.to_vaccinate_per_dose[dose_index] = self.vaccine_data[_dose_offset]
                
                # Sets the number of vaccines of dose_index to be dealt in each region
                weight_list = [pop/self.total_population for (pop) in self.pop_per_region.values()]
                int_weights = util.distribute_ints_from_weights(self.to_vaccinate_per_dose[dose_index], weight_list)
                for _idx, _name in enumerate(self.graph.region_dict):
                    self.vacc_per_region[_name][dose_index] = int_weights[_idx]
                    self.remainder_per_region[_name] = [0.0] * self.dosages
            
        if self.DEBUG_VACC_DATA:    
            print('------------------------')   
            print(f'Vaccine day {self.current_day}. Qnt to Vacc: {self.to_vaccinate_per_dose}. Prev Vacc: {self.prev_vac}\n')
        
        # Resets vaccines given in the previous day and their remainders
        self.prev_vac = [0] * self.dosages
        self.remainder_per_region = {r: [0.0] * self.dosages for r in self.graph.region_dict}
    
    def get_blob_vacc_efficiency(self, blob:Blob):
        return self.efficiency_per_level[blob.traceable_properties['vaccine_level']]    

    def vaccinate(self, values, hour, time):
        assert "node_id" in values, "node_id not defined in Vaccinate action."
        sub_list = []
        # For each vaccine_level (_dose_index)
        for _dose_index in range(self.dosages):
            
            # if there is no vaccines of _dose_index to be given this day
            if self.to_vaccinate_per_dose[_dose_index] == 0:
                continue
            target_node = self.graph.get_node_by_id(values['node_id'])
            target_region = self.graph.get_region_by_name(target_node.containing_region_name)
            
            _dose_offset = 0
            if _dose_index > 0:
                _dose_offset = self.dosage_offsets[_dose_index] - self.dosage_offsets[_dose_index - 1]
            
            # Calculates the number of people to be vaccinated in this node
            # based on a proportion of: region.pop/env.total_pop
            requests_per_day = len(values['frames'])
            to_vacc_float = float(self.vacc_per_region[target_region.name][_dose_index]/requests_per_day) + self.remainder_per_region[target_region.name][_dose_index]
            
            # Floors to int (round if last request of the day)
            to_vacc = math.floor(to_vacc_float)
            if hour == values['frames'][-1]:
                to_vacc = round(to_vacc_float)
            
            # prev_vac track requests during the day
            # remainder_per_region is used in the next request to balance totals
            self.prev_vac[_dose_index] += to_vacc
            self.remainder_per_region[target_region.name][_dose_index] = to_vacc_float % 1.0
                        
            if self.DEBUG_ALL_REGIONS == True or target_region.name in self.DEBUG_REGIONS:
                print(f'{target_region.name[:13]}: \t{target_region.get_population_size()} \tPharm pop: {target_node.get_population_size()}\tToVac: {to_vacc}')
            
            # Sets a gather_population TimeAction, moving the requested amount of people to be vaccinated
            new_action_values = {}
            new_action_type = 'gather_population'
            new_action_values['destination_region'] = target_region.name
            new_action_values['destination_node'] = target_node.name
            new_action_values['quantity'] = to_vacc
            new_action_values['different_node_name'] = "true"
            
            pop_template = PopTemplate()
            pop_template.set_traceable_property('vaccine_level', lambda n: n == _dose_index)
            pop_template.set_traceable_property('days_since_last_vaccine', lambda n: n >= _dose_offset)
            new_action_values['population_template'] = pop_template
            
            new_action = environment.TimeAction(_type = new_action_type, _values = new_action_values)
            self.graph.direct_action_invoke(new_action, hour, time)
            #self.graph.queue_next_frame_action(new_action)
            #sub_list.append(new_action)
            
            # Sets a change_vaccine_level to affect the target ndoe
            new_action_values = {}
            new_action_type = 'change_vaccine_level'
            new_action_values['node_id'] = target_node.id
            new_action_values['current_level'] = _dose_index
            new_action_values['min_dose_offset'] = _dose_offset
            new_action_values['quantity'] = to_vacc
            new_action = environment.TimeAction(_type = new_action_type, _values = new_action_values)
            #self.graph.queue_next_frame_action(new_action)
            #self.graph.direct_action_invoke(new_action, hour, time)
            sub_list.append(new_action)
        return sub_list
        
    def change_vaccine_level(self, values, hour, time):
        if isinstance(values['node_id'], int):
            target_node = self.graph.get_node_by_id(values['node_id'])
        else:
            print("origin_node not defined in change_vaccine_level action.")
            return
        
        # print(values)
        current_level = values['current_level']
        
        pt = PopTemplate()
        pt.set_traceable_property('vaccine_level', current_level + 1)
        
        sub_list = []
        
        blob_ids = []
        
        for n in target_node.contained_blobs:
            if n.traceable_properties['vaccine_level'] == current_level and n.traceable_properties["days_since_last_vaccine"] >= values["min_dose_offset"]:
                n.traceable_properties['vaccine_level'] = current_level + 1
                n.traceable_properties['days_since_last_vaccine'] = 0
                #print("blob id",n.blob_id)
                blob_ids.append(n.blob_id)
                
                new_action_type = 'return_to_previous'
                new_action_values = {}
                new_action_values['node_id'] = target_node.id
                new_action_values['blob_id'] = n.blob_id
                new_action_values['population_template'] = pt
                new_action = environment.TimeAction(_type = new_action_type, _values = new_action_values)
                #self.graph.direct_action_invoke(new_action,hour,time)
                #sub_list.append(new_action)
                #print(hour,self.graph.get_node_by_id(n.previous_node).name)  
        return sub_list

    #### Logging Functions
    def setup_logger(self,logger:SimulationLogger):        
        self.logger = logger 
        if not self.logger: return
        
        self.log_file_vacc = open(logger.base_path + "vaccine_level.csv", 'w', encoding='utf8')
        _header = 'Frame;Hour;Day'
        for lvl in range(self.vacc_levels):
            _header += ";Vacc" + str(lvl)
        for lvl in range(self.vacc_levels):
            _header += ";dVacc" + str(lvl)
        self.log_file_vacc.write(_header + '\n')
        self.last_frame = [0] * self.vacc_levels
        
        for lvl in range(self.vacc_levels):
            pop_template = PopTemplate()
            pop_template.set_traceable_property("vaccine_level", lvl)
            logger.global_custom_templates['VaccLvl_' + str(lvl)] = pop_template
            logger.region_custom_templates['VaccLvl_' + str(lvl)] = pop_template
            logger.node_custom_templates['VaccLvl_' + str(lvl)] = pop_template
        
        logger.add_custom_line_plot('Vaccination Levels - Global', 
                                    file = 'global.csv',
                                    x_label="Frame", y_label="Population",
                                    columns= ['VaccLvl_' + str(lvl) for lvl in range(self.vacc_levels)])
        logger.add_custom_line_plot('Vaccination Levels - Azenha and Bom Fim', 
                                    file = 'regions.csv',
                                    x_label="Frame", y_label="Population",
                                    columns= ['VaccLvl_' + str(lvl) for lvl in range(self.vacc_levels)],
                                    level="Region", filter=['Azenha', 'Bom Fim'])
        logger.add_custom_line_plot('Vaccination Levels - Per Region', 
                                    file = 'regions.csv',
                                    x_label="Frame", y_label="Population",
                                    columns= ['VaccLvl_' + str(lvl) for lvl in range(self.vacc_levels)],
                                    level="Region")
        logger.add_custom_line_plot('Vaccination Level 2 - Per Region', 
                                    file = 'regions.csv',
                                    x_label="Frame", y_label="Population",
                                    columns= ['VaccLvl_2'],
                                    level="Region")
        logger.add_custom_line_plot('Vaccination Levels - Pharmacy Nodes', 
                                    file = 'nodes.csv',
                                    x_label="Frame", y_label="Population",
                                    columns= ['VaccLvl_' + str(lvl) for lvl in range(self.vacc_levels)],
                                    level="Node", filter=['pharmacy'])
        logger.add_custom_line_plot('Total Population - Pharmacy Nodes', 
                                    file = 'nodes.csv',
                                    x_label="Frame", y_label="Population",
                                    columns= ['Total'],
                                    level="Node", filter=['pharmacy'])
        
    def log_data(self, **kwargs):
        assert 'graph' in kwargs and 'frame' in kwargs, "Invalid inputs for logging"
        
        # Gets data from logger
        _graph:environment.EnvironmentGraph = kwargs.get('graph')
        _frame:int = kwargs.get('frame')
        
        _current_frame_counts = [0] * self.vacc_levels
        _pop_template = PopTemplate()
        
        # Gets number of vaccinated ler level
        for lvl in range(self.vacc_levels):
            _pop_template.set_traceable_property('vaccine_level', lvl)
            for node in _graph.node_list:
                _current_frame_counts[lvl] += node.get_population_size(_pop_template)
        
        # Output string/row
        _row = f"{_frame};{_frame % self.day_duration};{_frame//self.day_duration}"
        for lvl in range(self.vacc_levels):
            _row += ";" + str(_current_frame_counts[lvl])
        for lvl in range(self.vacc_levels):
            _row += ";" + str(_current_frame_counts[lvl] - self.last_frame[lvl])
        _row+= "\n"
        
        self.last_frame = _current_frame_counts
        self.log_file_vacc.write(_row)
        
    def stop_logger(self, **kwargs):
        self.log_file_vacc.close()


    


if __name__ == "__main__":
    vaccine_plugin = VaccinePlugin(None)