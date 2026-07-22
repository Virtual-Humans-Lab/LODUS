from __future__ import annotations
from dataclasses import dataclass, field
import json
from pprint import pprint
import time
from typing import Any, Callable, Optional
from core.plugin import RoutinePlugin, ActionPlugin
import copy
from core.population import Blob, BlobFactory, BlobTemplate, CharacteristicsFactory, PopulationTemplate, SampledCharacteristicCollection
from core.routine import Routine, Action, RoutineFactory, RoutineTemplate
import util
from util.math import DistanceType as DistType, distance2D, distribute_ints_from_weights, geopy_distance_metre, pyproj_distance_metre
from util.random_instance import FixedRandom
from util.id_gen import IDGen
from events import Events

DEBUG_OPERATION_OUTPUT =  False

class EnvEdge():
    """"Class representing a graph edge. 
        
    Currently not implemented. In the future this should represent different types of transportation or cost of movement between regions.
    """

    def __init__(self):
        self.edge_type = ''

class EnvNode():
    """A point of interest in an Environment Graph. 
    
    Represents a physical location or abstracted space of the environment. 
    For example, a market (or all the markets) in a neighborhood.
    
    Depending on abstraction level, an EnvNode can represent:
        A school (finer level);
        Residential blocks of a neighborhood;
        A neighborhood;
        A city;
        A state;
        A country (coarser level);

    Ideally, this class should be constructed with the EnvNodeFactory class.

    Attributes:
        name: The name of the node.
        contained_blobs: A list of the blobs currently occupying this space.
        routine: The current time action Routine this region is implementing.
    """

    def __init__(self, node_type: str, node_unique_name:str):
        """Initializes an EnvNode."""
        self.node_type = node_type
        self.id = IDGen('nodes').get_id()
        self.type_id = IDGen(f'node_{node_type}').get_id()
        self.unique_name = node_unique_name

        self.containing_region_name:str = ''
        self.long_lat:list[float] = [0.0, 0.0]
        self.attributes: dict[str, Any] = {}
        self.enabled: bool = True

        
        self.contained_blobs:list[Blob] = []
        self.routine: Routine = None # type: ignore
        self.original_node_population:SampledCharacteristicCollection = None # type: ignore

    def get_complete_name(self):
        return f"{self.containing_region_name}//{self.unique_name}"
    
    def add_attribute(self, key: str, value: Any) -> None:
        self.attributes[key] = value

    def get_attribute(self, key: str) -> Any:
        return self.attributes[key]

    def set_enabled(self, enabled: bool) -> None:
        if not isinstance(enabled, bool):
            raise ValueError(f"enabled must be of type bool, is {type(enabled)}")
        self.enabled = enabled

    def enable(self) -> None:
        self.enabled = True

    def disable(self) -> None:
        self.enabled = False

    def is_enabled(self) -> bool:
        return self.enabled
    
    def set_long_lat_position(self, longitude: float, latitude: float) -> None:
        """Sets the physical position of this node."""
        if not isinstance(longitude, (int, float)) or not isinstance(latitude, (int, float)):
            raise ValueError(f"longitude and latitude must be of type int or float, are {type(longitude)} and {type(latitude)}")
        self.long_lat = [longitude, latitude]

    def process_routine(self, cycle_step) -> list[Action]:
        """Returns the list of Actions for the given cycle_step."""
        return self.routine.process_routine(cycle_step)

    def add_blob(self, blob: Blob):
        """Adds a blob to this EnvNode."""
        if not isinstance(blob, Blob):
            raise ValueError(f"blob must be of type Blob, is {type(blob)}")
        if blob in self.contained_blobs:
            raise ValueError("BLOB ALREADY HERE")
        self.contained_blobs.append(blob)

    def add_blobs(self, blobs: list[Blob]):
        """Adds a list of blobs to this EnvNode."""
        for blob in blobs:
            self.add_blob(blob)

    def remove_blob(self, blob: Blob):
        """Removes a blob from this EnvNode."""
        if not isinstance(blob, Blob):
            raise ValueError(f"blob must be of type Blob, is {type(blob)}")
        try:
            self.contained_blobs.remove(blob)
        except ValueError:
            pass
            
    def remove_blobs(self, blobs: list[Blob]):
        """Removes a list of blobs from this EnvNode."""
        for blob in blobs:
            self.remove_blob(blob)

    def merge_blobs_in_node(self):
        """Merges all blobs in this EnvNode that have the same mother_blob_id and traceable characteristics."""
        blob_list = self.contained_blobs
        i = 0

        while i < len(blob_list):
            current_blob: Blob = blob_list[i]
            j = i + 1

            while j < len(blob_list):
                other_blob: Blob = blob_list[j]

                if (current_blob.mother_blob_id == other_blob.mother_blob_id and
                        current_blob.compare_traceable_characteristics_to_other(other_blob)):
                    current_blob.merge_blob(other_blob)
                    self.remove_blob(other_blob)
                else:
                    j += 1
            i += 1

    def get_population_size(self, population_template: Optional[PopulationTemplate] = None):
        """Gets the total population size contained in this EnvNode."""
        return sum(blob.get_population_size(population_template) for blob in self.contained_blobs)

    def grab_population(self, quantity: int, template : Optional[PopulationTemplate] = None) -> list[Blob]:
        """Gets and removes a population matching a template from this EnvNode.
        The population removed is returned as a list of blobs.

        If quantity is larger than the current population size matching the tamplate,
        this method returns the largest possible population.

        Grabbed blobs are removed from this EnvNode.
        """
        total_available_population = self.get_population_size(template)

        if total_available_population == 0 or quantity <= 0:
            return []

        quantity = min(quantity, total_available_population)

        available_quantities = [blob.get_population_size(template) for blob in self.contained_blobs]
        int_adjusted_quantities = distribute_ints_from_weights(quantity, available_quantities)
        # int_adjusted_quantities = util.weighted_int_distribution(available_quantities, quantity)
        new_blobs:list[Blob] = [
            blob.grab_population(int_adjusted_quantities[x], template)
            for x, blob in enumerate(self.contained_blobs)
            if int_adjusted_quantities[x] > 0
        ] # type: ignore
        self.remove_blobs(new_blobs)
        return new_blobs

    def change_multiple_blobs_traceable_property(self, 
                                                 traceable_property_key:str, 
                                                 new_value: Any, 
                                                 desired_quantity:int, 
                                                 population_template:Optional[PopulationTemplate] = None) -> list[Blob]:
        """Grabs a quantity of population and changes their traceable properties. 
        May affect multiple blobs. Newly created blobs are added to this EnvNode.
        """
        grabbed_blobs = self.grab_population(desired_quantity, population_template)
        self.add_blobs(grabbed_blobs)

        for blob in grabbed_blobs:
            self._set_blob_traceable_properties(blob, traceable_property_key, new_value)

        return grabbed_blobs

    def change_single_blob_traceable_property(self, 
                                              blob:Blob, 
                                              traceable_property_key:str, 
                                              new_value: Any, 
                                              desired_quantity:int, 
                                              population_template:Optional[PopulationTemplate] = None) -> Blob:
        """Changes a traceable property of a single blob contained in this EnvNode.
        May split a blob during grab_population. Newly created blob is added to this EnvNode.
        """
        if desired_quantity == 0:
            return None

        if blob not in self.contained_blobs:
            raise ValueError(f"Blob is not in the contained blobs of node {blob.verbose_str()} {self}")

        grabbed_blob = blob.grab_population(desired_quantity, population_template)

        if grabbed_blob is None:
            return None
        if blob is not grabbed_blob:
            self.add_blob(grabbed_blob)

        self._set_blob_traceable_properties(grabbed_blob, traceable_property_key, new_value, blob)
        return grabbed_blob

    def _set_blob_traceable_properties(self, blob: Blob, key: str, value: Any, origin_blob: Optional[Blob] = None):
        """Internal function to set a traceable property of a contained blob."""
        blob.set_traceable_characteristic(key, value)
        blob.previous_node = self.id if origin_blob is None else origin_blob.previous_node
        blob.frame_origin_node = self.id if origin_blob is None else origin_blob.frame_origin_node

    def __str__(self):
        return (
        f"Type: {self.node_type}\n"
        f"Unique Name: {self.get_complete_name()}\n"
        f"Name: {self.unique_name}\n"
        f"ID: {self.id}\n"
        f"Enabled: {self.enabled}\n"
        f"Routine: {self.routine}\n"
        f"Characteristics: {self.attributes}\n"
        f"Blobs: {self.contained_blobs}\n"
    )                                                                

    def __repr__(self):
        return self.__str__()

class EnvNodeTemplate:
    """Describes an EnvNode generation template.
    
    EnvNodeFactory objects can generate EnvNodes based on this template.
    """
    def __init__(self, node_type: str, node_unique_name: str):
        self.node_type: str = node_type
        self.node_unique_name: str = node_unique_name
        self.node_attributes: dict[str, Any] = {}
        self.routine_template: RoutineTemplate = RoutineTemplate()
        self.blob_templates: list[BlobTemplate] = []
        self.long_lat: list[float] = [0.0, 0.0]

    def add_node_attributes(self, key: str, value: Any) -> None:
        """Adds an attribute to the node."""
        self.node_attributes[key] = value

    def add_action_to_routine_template(self, cycle_stop: int, action: Action) -> None:
        self.routine_template.add_action_to_template(cycle_stop, action)

    def add_actions_to_routine_template(self, cycle_stop: int, actions: list[Action]) -> None:
        for action in actions:
            self.routine_template.add_action_to_template(cycle_stop, action)

    def add_blob_template(self, blob_template: BlobTemplate) -> None:
        self.blob_templates.append(blob_template)

    def set_long_lat_position(self, longitude: float, latitude: float) -> None:
        """Sets the physical position of this node."""
        if not isinstance(longitude, (int, float)) or not isinstance(latitude, (int, float)):
            raise ValueError(f"longitude and latitude must be of type int or float, are {type(longitude)} and {type(latitude)}")
        self.long_lat = [longitude, latitude]

class EnvNodeFactory():
    """A factory to generate EnvNodes with a particular EnvNodeTemplate.
    
    Generates both an EnvNode and the respective Routine for the node.
    """
    def __init__(self):
        self.default_routine_factory = RoutineFactory()

    def generate_envnode(self,
                         node_template: EnvNodeTemplate,
                         blob_factory: BlobFactory,
                         target_region: EnvRegion, 
                         routine_factory: Optional[RoutineFactory] = None) -> EnvNode:
        """Generates an EnvNode based on a NodeTemplate and Blob Factory."""
        routine_factory = routine_factory or self.default_routine_factory

        env_node = EnvNode(node_template.node_type, node_template.node_unique_name)
        env_node.set_long_lat_position(node_template.long_lat[0], node_template.long_lat[1])
        env_node.routine = routine_factory.generate_routine(node_template.routine_template)
        env_node.attributes.update(node_template.node_attributes)
    
        for template in node_template.blob_templates:
            blob = blob_factory.generate_blob_from_template(
                target_region.id,
                env_node.id,
                template
            )
            env_node.add_blob(blob)

        return env_node

@dataclass
class EnvNodeDistances():
    """Class representing distances between a node and all other nodes."""
    node_name: str = ''
    distance_to_others:dict[str, float] = field(default_factory = lambda: ({}))

    def get_sorted_distance_to_others(self):
        return sorted(self.distance_to_others.items(), key=lambda item: item[1])


class EnvRegion():
    """"Represents a particular region in the simulation.
    A region is an abstraction for a set of points of interest and their initial populations.
    It is assumed its initial population returns frequently.

    EnvRegions are a possible abstraction for an aggregation of points-of-interest.

    Depending on abstraction level, an EnvRegion can represent:
        A neighborhood containing blocks, markets, schools;
        A city containing neighborhoods or discretized regions;
        A state containing cities and towns;
        A country containing states;

    Ideally, an EnvRegion is constructed using an EnvRegionFactory.
    """

    def __init__(self, region_name: str, long_lat: list[float]):
        """Initializes an EnvRegion"""
        self.name: str = region_name
        self.id = IDGen("regions").get_id()
        self.long_lat: list[float] = long_lat
        self.node_list: list[EnvNode] = []
        self.node_dict: dict[str, EnvNode] = {}

    def set_long_lat_position(self, longitude: float, latitude: float) -> None:
        """Sets the physical position of this region."""
        if not isinstance(longitude, (int, float)) or not isinstance(latitude, (int, float)):
            raise ValueError(f"longitude and latitude must be of type int or float, are {type(longitude)} and {type(latitude)}")
        self.long_lat = [longitude, latitude]

    def add_envnode(self, node: EnvNode):
        """Adds an EnvNode to this EnvRegion."""
        if not isinstance(node, EnvNode):
            raise ValueError(f"node must be of type EnvNode, is {type(node)}")
        node.containing_region_name = self.name
        self.node_list.append(node)
        self.node_dict[node.get_complete_name()] = node

    def get_first_node_with_name(self, name: str) -> EnvNode | None:
        """Gets an EnvNode by name."""
        return next((node for node in self.node_list if node.unique_name == name), None)

    def get_node_by_unique_name(self, unique_name: str) -> EnvNode:
        """Gets an EnvNode by name."""
        if unique_name not in self.node_dict:
            raise ValueError(f"Node {unique_name} not found in region {self.name}")
        return self.node_dict[unique_name]
    
    def get_nodes_by_type(self, node_type: str) -> list[EnvNode]:
        """Gets a list of EnvNodes by type."""
        return [node for node in self.node_list if node.node_type == node_type]

    def get_population_size(self, population_template: Optional[PopulationTemplate] = None) -> int:
        """Gets the total population size contained in this EnvRegion."""
        return sum(node.get_population_size(population_template) for node in self.node_list)

    def get_blob_count(self) -> int:
        """Gets the total number of Blobs contained in this EnvRegion."""
        return sum(len(node.contained_blobs) for node in self.node_list)

    def generate_action_list(self, cycle_step: int) -> list:
        """Generates a list of Actions for each EnvNode in this EnvRegion."""
        return [action for node in self.node_list for action in node.process_routine(cycle_step)]
   
    def grab_population(self, quantity: int, pop_template: PopulationTemplate) -> list:
        """Gets and removes a population matching a template from this EnvRegion.
        
        The population removed is returned as a list of blobs.

        If quantity is larger than the current population size matching the template,
        this method returns the largest possible population.

        Population is extracted evenly from EnvNodes.
        """
        raise NotImplementedError

    def __str__(self) -> str:
        return '{{"id" : {0}, "name" : "{1}",  "position" : {2}, "nodes" : {3}}}'.format(
            self.id, self.name, self.long_lat, self.node_list
        )

    def __repr__(self) -> str:
        return self.__str__()

class EnvRegionTemplate():
    """Describes a template for generating EnvRegions"""

    def __init__(self, region_name: str, long_lat: list[float]):
        self.region_name:str = region_name
        self.long_lat:list[float] = long_lat
        self.envnode_templates:list[EnvNodeTemplate] = []

    def add_envnode_template(self, node_template:EnvNodeTemplate):
        """Adds an EnvNodeTemplate to the region template."""
        if not isinstance(node_template, EnvNodeTemplate):
            raise ValueError("node_template must be of type EnvNodeTemplate")
        self.envnode_templates.append(node_template)
    
class EnvRegionFactory():
    """Generates EnvRegions based on a specific EnvRegionTemplate."""

    def __init__(self):
        pass
    
    def generate_envregion(self, envregion_template:EnvRegionTemplate, default_blob_factory: BlobFactory) -> EnvRegion:
        """Generates an EnvRegion based on the template."""

        region = EnvRegion(envregion_template.region_name, long_lat=envregion_template.long_lat)

        for envnode_template in envregion_template.envnode_templates:
            factory = EnvNodeFactory()
            node = factory.generate_envnode(envnode_template, default_blob_factory, region)
            
            region.add_envnode(node)
        
        return region


class EnvironmentGraph():
    """Models the top level of the Crowd Dynamics simulator. Additionally, handles TimeAction and Routine logic.
    
    The top level abstraction represents a group of EnvRegions. This can be used to model a city, country, etc.

    The TimeAction and Routine logic is handled by the EnvironmentGraph, since TimeActions are abstractions for 
    command-pattern graph operations.

    TimeActions are defined in the EnvironmentGraph as either being base actions or not. 
    Base actions translate directly into graph operations, moving population, for example.
    Composite actions are to be decomposed into any number of base actions, depending on that it needs to achieve.
    For example, a composite action could return every blob with mother_blob_id = 1 to its native EnvRegion, this
    action translates into several move_poplation TimeActions.


    Each time step update follows the following flow:
        The EnvironmentGraph gathers the TimeActions for each EnvNode.
        The EnvironmentGraph simpifies the TimeAction list into base actions.
        The EnvironmentGraph balances the TimeAction list into base actions, this operation is also responsible for guaranteeing all time actions are valid currently.
        Finally, each TimeAction is applied.

        The same algorithm is applied for repeating_actions.
        For each repeating action, the EnvironmentGraph check
        timestep % cycle_length == 0
        and processes that time action for each EnvNode.
        The EnvGraph calls the repeating_action with the desired values, setting region and node for each node in the EnvGraph.


    Attributes:
        region_list: List of contained EnvRegions.
        node_list: List of contained EnvNodes.
        edge_table: Relationship between neighboring EnVRegions. Currently, unused.
        time_action_map: Maps each TimeAction type to the relevant graph operation function. This should be extensible in a future version.
        base_actions: A set containing each base action the EnvironmentGraph supports.  This should be extensible in a future version.   
        self.global_actions : placeholder
        self.repeating_global_actions : A list of pairs [cycle_length, time_action]. Each repeating action is repeated every cycle_length steps.
    """

    def __init__(self):
        self.region_list: list[EnvRegion] = []
        self.region_dict: dict[str,EnvRegion] = {}
        self.region_id_dict = {}

        self.node_list: list[EnvNode] = []
        self.node_id_dict = {}
        self.node_dict: dict[str,EnvNode]= {}

        self.edge_table = [[]]

        self.data_action_map:dict[str, Callable] = { }

        # Distances:
        # self.node_distances:dict[str,list[tuple[float,str]]] = {}
        self.default_distance_type: DistType = DistType.METRES_PYPROJ
        self.node_distances:dict[DistType, dict[str, EnvNodeDistances]] = {t:{} for t in DistType}

        #self.od_matrix_logger:od_matrix_logger.ODMatrixLogger = None
        self.movement_logger_dict = {}
        self.characteristic_change_logger = {}
        
        # Events test
        Blob.events.on_traceable_property_changed += self.log_traceable_change
      
    def get_region_by_name(self, region_name: str) -> EnvRegion:
        if region_name not in self.region_dict:
            raise ValueError(f"Region {region_name} not found in region_dict")
        return self.region_dict[region_name]

    def get_region_by_id(self, region_id: int) -> EnvRegion:
        if region_id not in self.region_id_dict:
            raise ValueError(f"Region {region_id} not found in region_id_dict")
        return self.region_id_dict[region_id]

    def get_node_by_unique_name(self, region_name: str, node_unique_name: str):
        if region_name not in self.region_dict:
            raise ValueError(f"Region {region_name} not found in region_dict")
        return self.region_dict[region_name].get_node_by_unique_name(node_unique_name)
    
    def get_first_node_with_name(self, region_name: str, node_name: str):
        if region_name not in self.region_dict:
            raise ValueError(f"Region {region_name} not found in region_dict")
        return self.region_dict[region_name].get_first_node_with_name(node_name)
    
    def get_nodes_by_type(self, node_type: str) -> list[EnvNode]:
        """Gets a list of EnvNodes by type."""
        return [node for node in self.node_list if node.node_type == node_type]

    def change_node_enabled_state(self, node_complete_name: str, enabled: bool, cascade_reenable: bool = False) -> dict:
        """Change enabled state for a single node given by its complete name (`RegionName//UniqueName`).

        - Uses `node_dependency` plugin (if present) for validations and cascading.
        - Only the node matching `node_complete_name` is targeted directly; cascades
          (disables) may affect multiple nodes per dependency rules.

        Returns a summary dict with keys: `enabled`, `disabled`, and `blocked`.
        """
        # Find the exact node by complete name
        targets = [n for n in self.node_list if n.get_complete_name() == node_complete_name]
        if not targets:
            raise ValueError(f"Node with complete name '{node_complete_name}' not found in graph")
        if len(targets) > 1:
            raise ValueError(f"Multiple nodes with complete name '{node_complete_name}' found in graph")
        
        node = targets[0]
        dep_action = self.data_action_map.get("node_dependency")
        summary = {"enabled": [], "disabled": [], "blocked": {}}

        # Helper: unique name portion used by the dependency plugin
        unique_name = node.unique_name

        if enabled:
            # Build current enabled set (by complete_name)
            current_enabled = {n.get_complete_name() for n in self.node_list if n.is_enabled()}

            # If plugin exists, validate prerequisites first
            if dep_action:
                can_enable = dep_action("can_node_be_enabled", node.get_complete_name(), current_enabled)
                if not can_enable:
                    missing = [p for p in dep_action("get_transitive_dependency_nodes", node.get_complete_name()) if p not in current_enabled]
                    summary["blocked"][node.get_complete_name()] = missing
                    return summary

            # Enable target node
            node.enable()
            summary["enabled"].append(node.get_complete_name())
            current_enabled.add(node.get_complete_name())

            # Optionally cascade re-enable: try to re-enable dependents that are now satisfiable
            if dep_action and cascade_reenable:
                dependents = dep_action("get_transitive_dependent_nodes", node.get_complete_name())
                for dep in dependents:
                    for n in self.node_list:
                        if n.get_complete_name() == dep and not n.is_enabled():
                            if dep_action("can_node_be_enabled", n.get_complete_name(), current_enabled):
                                n.enable()
                                summary["enabled"].append(n.get_complete_name())
                                current_enabled.add(n.get_complete_name())

        else:
            # Disable target node
            if node.is_enabled():
                node.disable()
                summary["disabled"].append(node.get_complete_name())

            # If plugin exists, disable all transitive dependents
            if dep_action:
                dependents = dep_action("get_transitive_dependent_nodes", node.get_complete_name())
                for dep_name in dependents:
                    for n in self.node_list:
                        if n.get_complete_name() == dep_name and n.is_enabled():
                            n.disable()
                            summary["disabled"].append(n.get_complete_name())

        return summary

    def get_node_by_id(self, _id) -> EnvNode:
        return self.node_id_dict[_id]
    
    def get_population_size(self, population_template: Optional[PopulationTemplate] = None):
        """Gets the total population size contained in this EnvironmentGraph."""
        return sum(region.get_population_size(population_template) for region in self.region_list)
    
    def get_blob_count(self)->int:
        """Gets the total number of Blobs contained in this EnvironmentGraph."""
        return sum([region.get_blob_count() for region in self.region_list])



    # Node Distance Functions
    def calculate_all_distances(self):
        ''' Auxiliary function to calculate all node distances'''
        for node in self.node_list:
            self.get_node_distances(node)

    def get_node_distances(self, 
                          target_node:EnvNode, 
                          dist_type:DistType = DistType.LONG_LAT) -> EnvNodeDistances:
        '''Gets distances between a target node and all other nodes'''
        unique_name = target_node.get_complete_name()

        # Checks if the distance was calculated previously
        if unique_name in self.node_distances[dist_type]:
            return self.node_distances[dist_type][unique_name]
        
        node_dist = EnvNodeDistances(unique_name)
        node_pos = target_node.long_lat
        for other in self.node_list:
            if unique_name == other.get_complete_name():
                continue
            node_dist.distance_to_others[other.get_complete_name()] = self.__get_distance(node_pos, other.long_lat, dist_type)

        self.node_distances[dist_type][unique_name] = node_dist
        return self.node_distances[dist_type][unique_name]

    def __get_distance(self, p1, p2, dist_type:DistType = DistType.LONG_LAT):
        '''Gets distances based on selected distance type'''
        if dist_type == DistType.LONG_LAT:
            return distance2D(p1, p2)
        elif dist_type == DistType.METRES_GEOPY:
            return geopy_distance_metre(p1, p2)
        elif dist_type == DistType.METRES_PYPROJ:
            return pyproj_distance_metre(p1, p2)
        else:
            raise Exception("Distance Type is invalid")

    def add_region(self, region_template: EnvRegionTemplate, blob_factory: BlobFactory):
        """Adds a region to the EnvironmentGraph."""
        factory = EnvRegionFactory()
        new_region = factory.generate_envregion(region_template, blob_factory)
        self.edge_table.append(['' for x in range(len(self.region_list))])

        for node in new_region.node_list:
            node.containing_region_name = new_region.name
            self.node_list.append(node)
            if node.get_complete_name() in self.node_dict:
                raise ValueError(f"Node {node.get_complete_name()} already exists in the graph")
            self.node_dict[node.get_complete_name()] = node
            if node.id in self.node_id_dict:
                raise ValueError(f"Node {node.id} already exists in the graph")
            self.node_id_dict[node.id] = node

        self.region_dict[region_template.region_name] = new_region        
        self.region_list.append(new_region)
        self.region_id_dict[new_region.id] = new_region

    def add_edge(self, region1, region2, _type):
        self.edge_table[region1][region2] = _type
                
    def log_blob_movement(self, origin_node:EnvNode, destination_node:EnvNode, blobs:list[Blob]):
        for k,v in self.movement_logger_dict.items():
            v(origin_node, destination_node, blobs)
            #self.od_matrix_logger.log_od_movement(origin_node, destination_node, blobs)

    def log_traceable_change(self, blob:Blob, key, prev_val, new_val):
        for k,v in self.characteristic_change_logger.items():
            v(blob, key, prev_val, new_val)

    # -----------------------------------
    def add_blobs_traceable_property(self, key, value):
        for node in self.node_list:
            for blob in node.contained_blobs:
                blob.set_traceable_characteristic(key, value)
                
    # def lambda_blobs_traceable_property(self, key, lambda_funtion):
    #     for node in self.node_list:
    #         for blob in node.contained_blobs:
    #             blob.traceable_properties[key] = lambda_funtion(blob.traceable_properties[key])
                #print("days", blob.traceable_properties[key])
                
    def lambda_blobs_traceable_property(self, key, lambda_funtion):
        for node in self.node_list:
            for blob in node.contained_blobs:
                blob.set_traceable_characteristic(key, lambda_funtion(blob, blob.get_traceable_characteristic(key)))

    def merge_blobs_in_all_envnodes(self):
        """Merges all blobs in all EnvNodes that have the same mother_blob_id and traceable characteristics."""
        for node in self.node_list:
            node.merge_blobs_in_node()

    def set_original_populations(self):
        for node in self.node_list:
            for blob in node.contained_blobs:
                prop_block = blob.sampled_characteristics.copy()
                if node.original_node_population == None:
                    node.original_node_population = prop_block
                else:
                    node.original_node_population.merge_characteristic_collection(prop_block)

    def set_spawning_nodes(self):
        for node in self.node_list:
            for blob in node.contained_blobs:
                if blob.node_of_origin is None:
                    print("WTF SPAWN")
                    blob.spawning_node = node.id

    def set_frame_origin_of_all_blobs(self):
        for node in self.node_list:
            for blob in node.contained_blobs:
                blob.frame_origin_node = node.id

    def update_time_step(self, cycle_step, simulation_step):
        raise NotImplementedError("update_time_step was moved to the Simulation class. Please, create a simulator")
    
    def print_overview(self, show_nodes_with_population: bool = False):
        print(f"EnvironmentGraph with {len(self.region_list)} regions and {len(self.node_list)} nodes.")
        print(f"-- Population Count: {self.get_population_size()}")
        print(f"-- Blob Count: {self.get_blob_count()}")
        if show_nodes_with_population:
            print(f"-- Nodes with Population: {[node.get_complete_name() for node in self.node_list if node.get_population_size() > 0]}")

    def __str__(self):
        return "{\"graph\":" + str(self.region_list) + "}"
    
    def __repr__(self):
        return "{\"graph\":" + str(self.region_list) + "}"

FLOODED_ATTRIBUTES = {
    "is_flooded": bool
}
