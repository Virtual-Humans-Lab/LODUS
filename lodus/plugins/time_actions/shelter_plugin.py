from pathlib import Path
from pprint import pprint
import time
import environment
from population import Blob, PopulationTemplate
import copy
from random_inst import FixedRandom
import math
import csv
from loggers.population_count_logger import PopulationCountLogger
from . import util
import json
from difflib import get_close_matches

class ShelterPlugin(environment.TimeActionPlugin):

    def __init__(self, env_graph: environment.EnvironmentGraph):
        super().__init__()
        
        self.__header:str = "Shelter Plugin:"
        self.__path =  Path(__file__).parent.parent.parent / "data_input"
        self.graph = env_graph
        self.random = FixedRandom.instance
        self.shelters:list[environment.EnvNode] = []

        # Set the time/frame variables
        self.cycle_step = 0
        self.sim_step = 0

        self.safe_template = PopulationTemplate(traceable_characteristics={"flooding_status": "safe"})
        self.in_danger_template = PopulationTemplate(traceable_characteristics={"flooding_status": "in_danger"})
        self.sheltered_template = PopulationTemplate(traceable_characteristics={"flooding_status": "sheltered"})
        self.last_reallocation = -1
         # Loads experiment configuration, if any
        self.config:dict = self.graph.experiment_config.get("shelter_plugin", {})

        # Loads a config file, if defined
        if "configuration_file" in self.config:
            _content = open(self.__path / self.config["configuration_file"], 'r', encoding='utf8')
            _json = json.load(_content)
            # Override values
            for key, value in self.config.items():
                _json[key] = value
            self.config = _json
      
       
        # Sets traceable properties for all blobs in the simulation
        self.graph.add_blobs_traceable_property("flooding_status", "safe")
        
        self.set_pair('move_to_shelters', self.move_to_shelters)
        self.set_pair('shelter_population', self.shelter_population)
        self.set_pair('reallocate_shelter_waitlist', self.reallocate_shelter_waitlist)
        self.graph.base_actions.add('move_to_shelters')
        self.graph.base_actions.add('shelter_population')
        self.graph.base_actions.add('reallocate_shelter_waitlist')

        _poi_count = len(self.graph.node_dict.keys())
        self.selected_initially_affected_population()
        self.shelter_data = self.load_initial_shelter_data()
        self.create_initial_shelters()
        # requested in time_step 0 self.request_initial_population_to_shelters()
        print(f"{self.__header} Total population in danger before initial movement = {self.graph.get_population_size(population_template=self.in_danger_template)}")
        print(f"\tTotal population sheltered before initial movement = {self.graph.get_population_size(population_template=self.sheltered_template)}")

        print(f"POI count before = {_poi_count}, and after = {len(self.graph.node_dict.keys())}")
        print("\n\n\n")

    def reallocate_shelter_waitlist(self, pop_template, values:dict, cycle_step:int, sim_step:int):
        start_time = time.perf_counter()
        assert "node_id" in values, "node_id not defined in Vaccinate action."
        if self.last_reallocation >= cycle_step:
            return
        
        self.last_reallocation = cycle_step
        _total_cap = sum([node.get_attribute("capacity") for node in self.shelters])
        _total_sheltered = sum([node.get_population_size(self.sheltered_template) for node in self.shelters])
        _to_move = _total_cap - _total_sheltered
        _av_target_shelters = [_sh for _sh in self.shelters if 
                               _sh.get_attribute("capacity") > _sh.get_population_size(self.sheltered_template)]
        _av_origin_shelters = {_sh: _sh.get_population_size(self.in_danger_template) for _sh in self.shelters}
        _av_origin_shelters = {k: v for k, v in _av_origin_shelters.items() if v > 0}
        _total_in_danger = sum(_av_origin_shelters.values())
        print(f"cap {_total_cap}, sheltered {_total_sheltered}, to move " +
              f"{_to_move}, in danger {_total_in_danger}, available shelters {len(_av_target_shelters)}")
        
        for i in range(_to_move):
            acting_node = self.random.choice(list(_av_origin_shelters.keys()))
            acting_region = self.graph.get_region_by_name(acting_node.containing_region_name)
            
            target_node = self.random.choice(_av_target_shelters)
            target_region = self.graph.get_region_by_name(target_node.containing_region_name)
            # print(f"from {acting_node.get_unique_name()} to {target_node.get_unique_name()}")
            

            new_action_type = 'move_population'
            new_action_values = {'origin_region': acting_region.name,
                                 'origin_node': acting_node.name,
                                 'destination_region': target_region.name,
                                 'destination_node': target_node.name,
                                 'quantity': 1}
            template = copy.deepcopy(self.in_danger_template)
            #temp.mother_blob_id = acting_region.id

            new_action = environment.TimeAction(action_type = new_action_type, 
                                                pop_template = template,
                                                values = new_action_values)
            self.graph.direct_action_invoke(new_action, self.cycle_step, self.sim_step)

            _av_origin_shelters[acting_node] = _av_origin_shelters[acting_node] - 1
            if _av_origin_shelters[acting_node] == 0:
                # print("removing", acting_node.get_unique_name())
                _av_origin_shelters.pop(acting_node, None)
            if target_node.get_population_size() >= target_node.get_attribute("capacity"):
                # print("removing 2",target_node.get_unique_name())
                _av_target_shelters.remove(target_node)
        # print("WTF")
        
        self.add_execution_time(time.perf_counter() - start_time)

    def shelter_population(self, pop_template, values:dict, cycle_step:int, sim_step:int):
        start_time = time.perf_counter()
        assert "node_id" in values, "node_id not defined in Vaccinate action."
        target_node = self.graph.get_node_by_id(values['node_id'])
        # target_region = self.graph.get_region_by_name(target_node.containing_region_name)
        # if target_region not in self.affected_regions: return
        if "shelter" not in target_node.name: return

        _capacity = target_node.get_attribute("capacity")
        _sheltered = target_node.get_population_size(self.sheltered_template)
        _to_shelter = _capacity - _sheltered
        
        # print(target_node.get_unique_name(), _capacity, _sheltered, "asdas")
        if _to_shelter <= 0:
            return
        
        # print("Sheltering pop at", target_node.get_unique_name(), _to_shelter)

        _blobs = target_node.grab_population(_to_shelter, self.in_danger_template)
        for _b in _blobs:
            _b.set_traceable_characteristic("flooding_status", "sheltered")
            if _b not in  target_node.contained_blobs:
                target_node.add_blob(_b)


        self.add_execution_time(time.perf_counter() - start_time)

    def move_to_shelters(self, pop_template, values:dict, cycle_step:int, sim_step:int):
        start_time = time.perf_counter()
        assert "node_id" in values, "node_id not defined in Vaccinate action."
        target_node = self.graph.get_node_by_id(values['node_id'])
        target_region = self.graph.get_region_by_name(target_node.containing_region_name)
        if target_region not in self.affected_regions: return
        if target_node.name != "home": return
        
        _mode = values['mode']
        _percentage = values["population_percentage_to_move"]
        if _mode == 0: # initial affected pop
            _to_move = math.ceil(self.pop_aff_areas[target_region.name] * _percentage)
        elif _mode == 1: # current affected pop
            _to_move = math.ceil(target_node.get_population_size(self.in_danger_template) * _percentage)

        # print(f"To move {_to_move} from {target_node.get_unique_name()}")

        
        new_action_values = {}
        new_action_type = 'levy_walk_direct'
        new_action_values['region'] = target_region.name
        new_action_values['node'] = target_node.name
        new_action_values['quantity'] = _to_move
        new_action_values['target_node_type'] = ["shelter"]
        new_action_values['population_group_size'] = 1
        new_action_values['movement_probability'] = 1.00
        # new_action_values['use_buckets'] = False
        new_action_values['use_original_population'] = False
        new_action_values['target_node_type_contains'] = True
        new_action_values['different_node_name'] = True
        # new_action_values['percentage_per_search'] = 1.00
        pop_template = PopulationTemplate(traceable_characteristics={"flooding_status": "in_danger"})
        new_action = environment.TimeAction(action_type = new_action_type, 
                                                pop_template = pop_template,
                                                values = new_action_values)
        self.graph.direct_action_invoke(new_action, self.cycle_step, self.sim_step)
        self.add_execution_time(time.perf_counter() - start_time)
        # print("ALEGRIA")
        # exit()

    def request_initial_population_to_shelters(self):
        for _shelter in self.shelter_data:
            if _shelter["shelteredPeople"] == 0: continue
            _node:environment.EnvNode = _shelter["node"] # type: ignore
            new_action_values = {}
            new_action_type = 'gather_population'
            new_action_values['region'] = _node.containing_region_name
            new_action_values['node'] = _node.name
            new_action_values['quantity'] = _shelter["shelteredPeople"]
            new_action_values['different_node_name'] = "true"
            new_action_values['percentage_per_search'] = 1.00
            # print(cycle_step, target_node.get_unique_name(), "Quant", to_vacc, self.prev_vac[_dose_index])
            pop_template = PopulationTemplate(traceable_characteristics={"flooding_status": "in_danger"})
            # pop_template.set_traceable_property('days_since_last_vaccine', lambda n: n >= _dose_offset)
            
            new_action = environment.TimeAction(action_type = new_action_type, 
                                                pop_template = pop_template,
                                                values = new_action_values)
            # pprint(new_action_values)
            self.graph.direct_action_invoke(new_action, self.cycle_step, self.sim_step)

            for _blob in _node.contained_blobs:
                if _blob.get_traceable_characteristic("flooding_status") == "in_danger":
                    _pop = _blob.get_population_size()
                    _changed_blob = _blob.split_and_change_blob_traceable_characteristic("flooding_status", "sheltered", _pop)
                    if _blob != _changed_blob:
                        _node.add_blob(_changed_blob)

    def create_initial_shelters(self):
        region_names = self.graph.region_dict.keys()
        for _shelter in self.shelter_data:
            # pprint(_shelter)
            if _shelter["region"] not in region_names:
                 _shelter["region"] = get_close_matches(_shelter["region"], region_names)[0]

            node_template = environment.EnvNodeTemplate()
            node_template.long_lat = (float(_shelter["Longitude"]), float(_shelter["Latitude"]))
            node_template.add_characteristic("shelter", True)
            node_template.add_characteristic("capacity", _shelter["capacity"])
            poi_name = "shelter_" + _shelter["id"]
            _shelter["node"] = self.graph.add_node_to_region(region=self.graph.region_dict[_shelter["region"]],
                                                             node_template=node_template,
                                                             node_unique_name=poi_name)
            self.shelters.append(_shelter["node"])

    def selected_initially_affected_population(self):
        
        # Data from config file
        self.initially_aff_pop:int = self.config.get("initially_affected_people", 0)
        self.affected_regions:list[environment.EnvRegion] = []
        self.affected_area_mode:int = self.config["affected_areas"].get("mode", 0)
        
        self.total_population = self.graph.get_population_size()
        self.pop_aff_areas:dict[str, int] = {}
        self.total_pop_aff_areas = 0
        
        # In mode 0, selectes the population based on the entire affected regions
        if self.affected_area_mode == 0:
            with open(self.__path /self.config["affected_areas"]["affected_regions_file"], 'r', encoding='utf8') as csvfile:
                reader = csv.DictReader(csvfile)
                self.affected_regions = [self.graph.region_dict[row["RegionName"]] for row in reader if row["Affected"] == "TRUE"]
            # print(len(self.affected_regions), [r.name for r in self.affected_regions])

            self.pop_aff_areas = {r.name: r.get_population_size(template=self.safe_template) for r in self.affected_regions}
            self.total_pop_aff_areas = sum(self.pop_aff_areas.values())

        elif self.affected_area_mode == 1:
            region_names = self.graph.region_dict.keys()
            with open(self.__path /self.config["affected_areas"]["affected_census_sectors_file"], 'r', encoding='utf8') as csvfile:
                reader = csv.DictReader(csvfile)
                self.sector_data = [row for row in reader]
            
            self.affected_regions = []   
            self.pop_aff_areas = {} #{r.name: r.get_population_size(template=self.safe_template) for r in self.affected_regions}
            
            for _sect in self.sector_data:
                # print(_sect["Bairro"])
                _sect["Bairro"] = get_close_matches(str.lower(_sect["Bairro"]), region_names, cutoff=0.5)[0]
                _sect["Total de pessoas"] = int(_sect["Total de pessoas"])
                _sect["Inundação"] = str.lower(_sect["Inundação"]) == "true"
                
                if _sect["Inundação"]:
                    _reg = self.graph.region_dict[_sect["Bairro"]]
                    if _reg not in self.affected_regions: 
                        self.affected_regions.append(_reg)
                        self.pop_aff_areas[_reg.name] = 0
                    self.pop_aff_areas[_reg.name] += _sect["Total de pessoas"]
            self.total_pop_aff_areas = sum(self.pop_aff_areas.values())
            # print(len(self.affected_regions), [r.name for r in self.affected_regions])
            print(len(self.affected_regions), "Affected population per Region:", self.pop_aff_areas)
            print("Total affected Sectors:",len([0 for _sect in self.sector_data if _sect["Inundação"]]))
            # exit()
        # Use weights based on loaded data
        if self.initially_aff_pop == 0: self.initially_aff_pop = self.total_pop_aff_areas
        weight_list = [pop/self.total_pop_aff_areas for (pop) in self.pop_aff_areas.values()]
        int_weights = util.distribute_ints_from_weights(self.initially_aff_pop, weight_list)
        # print(int_weights)
        # print("sum", sum(int_weights), self.initially_aff_pop)

        for idx, _region in enumerate(self.affected_regions):
            # print(idx, _region.name)
            _region.node_dict["home"].change_blobs_traceable_property(key="flooding_status", 
                                                                    value="in_danger", 
                                                                    quantity=int_weights[idx])
            # for _b in _region.node_dict["home"].contained_blobs:
            #     print(_b.verbose_str())

        # print(f"\tAffected population per region: {self.pop_aff_areas}")
        print(f"\tTotal population of initially affected regions: {self.total_pop_aff_areas}")
        _ratio_affected = self.initially_aff_pop / self.total_pop_aff_areas
        print(f"\t% of affected people vs available population in affected regions = {_ratio_affected}")

    def load_initial_shelter_data(self):
        if "shelter_data" not in self.config: 
            print(f"{self.__header} no shelter data file defined.")
            return []

        print(f"{self.__header} loading shelter data from {self.config["shelter_data"]}")
        # Load shelter data
        initial_shelters = []
        with open(self.__path /self.config["shelter_data"], 'r', encoding='utf8') as csvfile:
            reader = csv.DictReader(csvfile)
            initial_shelters = [row for row in reader]
        
        # Filter and preprocess data (only shelters marked with "Sim" and without "EVACUADO")
        initial_shelters = [_s for _s in initial_shelters if _s["abrigo"] == "Sim" and "EVACUADO" not in _s["name"]]
        
        # Defines shelteredPeople and capacity as its value or 0 if not defined, then max capacity
        for _shelter in initial_shelters:
            _shelter["shelteredPeople"]:int = int(float(_shelter["shelteredPeople"])) if _shelter["shelteredPeople"] else 0
            _shelter["capacity"] = int(float(_shelter["capacity"])) if _shelter["capacity"] else 0
            _shelter["capacity"] = max( _shelter["capacity"], _shelter["shelteredPeople"])
        
        # Gets current capacity and sheltered people
        _capacity = sum([_s["capacity"] for _s in initial_shelters]) # type: ignore
        _sheltered = sum([_s["shelteredPeople"] for _s in initial_shelters]) # type: ignore
        print(f"\tTotal Shelters = {len(initial_shelters)} \tCapacity = {_capacity} \t Sheltered = {_sheltered}")

        # Selects shelters with 0 capacity, and adjusts it based on missing total capacity
        undefined_shelters = [_s for _s in initial_shelters if _s["capacity"] == 0]
        _missing_capacity = self.config.get("initial_shelter_capacity", 0) - _capacity
        _missing_sheltered = self.config.get("initially_sheltered_people", 0) - _sheltered
        print(f"\tUndefined shelters = {len(undefined_shelters)}" + 
              f"\tMissing Capacity = {_missing_capacity} \tMissing Sheltered = {_missing_sheltered}")
        if _missing_capacity > 0:
            weight_list = [1.0 for _s in undefined_shelters]
            int_weights = util.distribute_ints_from_weights(_missing_capacity, weight_list)
            # print("Weights for missing capacity", int_weights, "Sum", sum(int_weights))
            for idx, _shelter in enumerate(undefined_shelters):
                _shelter["capacity"] = int_weights[idx]
        else:
            print("Excess capacity")
            initial_shelters = [_shelter for _shelter in initial_shelters if _shelter not in undefined_shelters]

        # Get the available slots in all shelters (including recently modified)
        _available_slots = [_s["capacity"] - _s["shelteredPeople"] for _s in initial_shelters] # type: ignore
        _total_available_slots = sum(_available_slots)

        if _missing_sheltered > 0:
            weight_list = [_slots/_total_available_slots for _slots in _available_slots]
            int_weights = util.distribute_ints_from_weights(_missing_sheltered, weight_list)
            # print("Weights for missing sheltered people", int_weights, "Sum", sum(int_weights))
            for idx, _shelter in enumerate(initial_shelters):
                _shelter["shelteredPeople"] = _shelter["shelteredPeople"] + int_weights[idx]

         # Gets current capacity and sheltered people
        _capacity = sum([_s["capacity"] for _s in initial_shelters]) # type: ignore
        _sheltered = sum([_s["shelteredPeople"] for _s in initial_shelters]) # type: ignore
        _shelter_occupancy = [_s["shelteredPeople"]/_s["capacity"] for _s in initial_shelters] # type: ignore
        print(f"\tAfter changes \tCapacity = {_capacity} \t Sheltered = {_sheltered}")
        # print([(_s["id"], _s["shelteredPeople"],_s["capacity"]) for _s in initial_shelters])
        # print(f"\tShelter occupancy = {_shelter_occupancy}")
        print(f"\tAvg shelter occupancy = {sum(_shelter_occupancy)/len(_shelter_occupancy)}")
        return initial_shelters

    def update_time_step(self, cycle_step:int, simulation_step:int):
        # Updates time step data
        self.cycle_length = self.graph.routine_cycle_length
        self.cycle_step = cycle_step
        self.sim_step = simulation_step
        self.cycle = (simulation_step // self.cycle_length)
        
        if simulation_step == 0: 
            self.request_initial_population_to_shelters()
            print(f"{self.__header} Total population in danger after initial movement = {self.graph.get_population_size(population_template=self.in_danger_template)}")
            print(f"{self.__header} Total population sheltered after initial movement = {self.graph.get_population_size(population_template=self.sheltered_template)}")
        if cycle_step == 9:
            print(f"{self.__header} Total population in danger at {simulation_step} = {self.graph.get_population_size(population_template=self.in_danger_template)}")
            print(f"{self.__header} Total population sheltered at {simulation_step} = {self.graph.get_population_size(population_template=self.sheltered_template)}")
            print(f"{self.__header} Total population in line at {simulation_step} = {sum([node.get_population_size(self.in_danger_template) for node in self.shelters])}")
            

        
if __name__ == "__main__":
    shelter_plugin = ShelterPlugin(None)





