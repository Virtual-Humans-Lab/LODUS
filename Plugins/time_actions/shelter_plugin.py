from pathlib import Path
from pprint import pprint
import time
import environment
from population import Blob, PopTemplate
import copy
from random_inst import FixedRandom
import math
import csv
from loggers.population_count_logger import PopulationCountLogger
import util
import json
from difflib import get_close_matches

class ShelterPlugin(environment.TimeActionPlugin):

    __default_initial_affected_people = 100000

    def __init__(self, env_graph: environment.EnvironmentGraph):
        super().__init__()
        
        self.__header:str = "Shelter Plugin:"
        self.__path =  Path(__file__).parent.parent.parent / "data_input"
        self.graph = env_graph
        self.shelters:list[environment.EnvNode] = []

        # Set the time/frame variables
        self.cycle_step = 0
        self.sim_step = 0

        self.safe_template = PopTemplate(traceable_properties={"flooding_status": "safe"})
        self.in_danger_template = PopTemplate(traceable_properties={"flooding_status": "in_danger"})
        self.sheltered_template = PopTemplate(traceable_properties={"flooding_status": "sheltered"})

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
        
        _poi_count = len(self.graph.node_dict.keys())
        self.selected_initially_affected_population()
        self.shelter_data = self.load_initial_shelter_data()
        self.create_initial_shelters()
        # requested in time_step 0 self.request_initial_population_to_shelters()
        print(f"{self.__header} Total population in danger before initial movement = {self.graph.get_population_size(population_template=self.in_danger_template)}")
        print(f"POI count before = {_poi_count}, and after = {len(self.graph.node_dict.keys())}")
        print("\n\n\n")

    def request_initial_population_to_shelters(self):
        for _shelter in self.shelter_data:
            _node:environment.EnvNode = _shelter["node"] # type: ignore
            new_action_values = {}
            new_action_type = 'gather_population'
            new_action_values['region'] = _node.containing_region_name
            new_action_values['node'] = _node.name
            new_action_values['quantity'] = _shelter["shelteredPeople"]
            new_action_values['different_node_name'] = "true"
            # print(cycle_step, target_node.get_unique_name(), "Quant", to_vacc, self.prev_vac[_dose_index])
            pop_template = PopTemplate(traceable_properties={"flooding_status": "in_danger"})
            # pop_template.set_traceable_property('days_since_last_vaccine', lambda n: n >= _dose_offset)
            
            new_action = environment.TimeAction(action_type = new_action_type, 
                                                pop_template = pop_template,
                                                values = new_action_values)
            self.graph.direct_action_invoke(new_action, self.cycle_step, self.sim_step)

            for _blob in _node.contained_blobs:
                if _blob.get_traceable_property("flooding_status") == "in_danger":
                    _pop = _blob.get_population_size()
                    _changed_blob = _blob.change_blob_traceable_property("flooding_status", "sheltered", _pop)
                    if _blob != _changed_blob:
                        _node.add_blob(_changed_blob)

    def create_initial_shelters(self):
        region_names = self.graph.region_dict.keys()
        for _shelter in self.shelter_data:
            # pprint(_shelter)
            if _shelter["region"] not in region_names:
                 _shelter["region"] = get_close_matches(_shelter["region"], region_names)[0]

            node_template = environment.EnvNodeTemplate()
            node_template.long_lat = (float(_shelter["Latitude"]), float(_shelter["Longitude"]))
            node_template.add_characteristic("shelter", True)
            node_template.add_characteristic("capacity", _shelter["capacity"])
            poi_name = "shelter_" + _shelter["order"]
            _shelter["node"] = self.graph.add_node_to_region(region=self.graph.region_dict[_shelter["region"]],
                                                             node_template=node_template,
                                                             node_unique_name=poi_name)

    def selected_initially_affected_population(self):
        
        # Data from config file
        self.initially_aff_pop:int = self.config.get("initially_affected_people", ShelterPlugin.__default_initial_affected_people)
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

        # Use weights based on loaded data
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

        # Get the available slots in all shelters (including recently modified)
        _available_slots = [_s["capacity"] - _s["shelteredPeople"] for _s in initial_shelters]
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
        print([(_s["order"], _s["shelteredPeople"],_s["capacity"]) for _s in initial_shelters])
        #print(f"\tShelter occupancy = {_shelter_occupancy}")
        print(f"\tAvg shelter occupancy = {sum(_shelter_occupancy)/len(_shelter_occupancy)}")
        return initial_shelters

    def move_initial_population_to_shelters(self):
        pass

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


        
if __name__ == "__main__":
    shelter_plugin = ShelterPlugin(None)





