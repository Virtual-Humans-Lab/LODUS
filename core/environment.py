from __future__ import annotations
from dataclasses import dataclass, field
import json
from pprint import pprint
import time
from typing import Any, Optional
from core.plugin import RoutinePlugin, ActionPlugin
import logger_plugin
import copy
from core.population import Blob, BlobFactory, BlobTemplate, PopulationTemplate, SampledCharacteristicCollection
from core.routine import Routine, Action, RoutineFactory, RoutineTemplate
import util
from util import DistanceType as DistType
from events import Events
from random_inst import FixedRandom

DEBUG_OPERATION_OUTPUT =  False

class EnvEdge():
    """"Class representing a graph edge. 
        
    Currently not implemented. In the future this should represent different types of transportation or cost of movement between regions.
    """

    def __init__(self):
        self.edge_type = ''


@dataclass
class EnvNodeDistances():
    """Class representing distances between a node and all other nodes."""
    node_name: str = ''
    distance_to_others:dict[str, float] = field(default_factory = lambda: ({}))

    def get_distance_tuples(self):
        return sorted(self.distance_to_others.items(), key=lambda item: item[1])
        


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

    def __init__(self, node_type: str, name:str = ''):
        """Initializes an EnvNode."""
        self.node_type = node_type
        self.id = util.IDGen('nodes').get_id()
        self.type_id = util.IDGen(f'node_{node_type}').get_id()
        self.name = node_type

        self.containing_region_name:str = ''
        self.long_lat:list[float] = [0.0, 0.0]
        self.attributes: dict[str, Any] = {}

        self.contained_blobs:list[Blob] = [] 
        self.routine: Routine = None # type: ignore
        self.original_node_population:SampledCharacteristicCollection = None # type: ignore

    def get_unique_name(self):
        return f"{self.containing_region_name}//{self.node_type}{self.type_id}"
    
    def add_attribute(self, key: str, value: Any) -> None:
        self.attributes[key] = value

    def get_attribute(self, key: str) -> Any:
        return self.attributes[key]
    
    def set_long_lat_position(self, longitude: float, latitude: float) -> None:
        """Sets the physical position of this node."""
        if not isinstance(longitude, (int, float)) or not isinstance(latitude, (int, float)):
            raise ValueError(f"longitude and latitude must be of type int or float, are {type(longitude)} and {type(latitude)}")
        self.long_lat = [longitude, latitude]

    def process_routine(self, cycle_step) -> list[Action]:
        """Returns the list of Actions for the given cycle_step."""
        return self.routine.process_routine(cycle_step)

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
        int_adjusted_quantities = util.distribute_ints_from_weights(quantity, available_quantities)
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
        f"Unique Name: {self.get_unique_name()}\n"
        f"Name: {self.name}\n"
        f"ID: {self.id}\n"
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
    def __init__(self, node_type: str, node_name: Optional[str] = None):
        self.node_type: str = node_type
        self.node_name: str = node_name if node_name else node_type
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

        env_node = EnvNode(node_template.node_type)
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

        # for template in node_template.blob_templates:
        #     blob = blob_factory.generate_blob_with_profile(
        #         target_region.id, 
        #         env_node.id, 
        #         template.population, 
        #         template.sampled_characteristics, 
        #         template.traceable_characteristics
        #     )
        #     env_node.add_blob(blob)
        
        return env_node


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
        self.id = util.IDGen("regions").get_id()
        self.long_lat: list[float] = long_lat
        self.node_list: list[EnvNode] = []
        self.node_dict: dict[str, EnvNode] = {}

    def add_node(self, node: EnvNode):
        node.containing_region_name = self.name
        self.node_list.append(node)
        self.node_dict[node.get_unique_name()] = node

    def get_first_node_with_name(self, name: str) -> EnvNode | None:
        """Gets an EnvNode by name."""
        return next((node for node in self.node_list if node.name == name), None)

    def get_node_by_unique_name(self, unique_name: str) -> EnvNode:
        """Gets an EnvNode by name."""
        if unique_name not in self.node_dict:
            raise ValueError(f"Node {unique_name} not found in region {self.name}")
        return self.node_dict[unique_name]

    def get_population_size(self, population_template: Optional[PopulationTemplate] = None) -> int:
        """Gets the total population size contained in this EnvRegion."""
        return sum(node.get_population_size(population_template) for node in self.node_list)

    def get_blob_count(self) -> int:
        """Gets the total number of Blobs contained in this EnvRegion."""
        return sum(len(node.contained_blobs) for node in self.node_list)

    def generate_action_list(self, hour: int) -> list:
        """Generates a list of Actions for each EnvNode in this EnvRegion."""
        return [action for node in self.node_list for action in node.process_routine(hour)]
   
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

    def __init__(self, template:EnvRegionTemplate, default_blob_factory: BlobFactory):
        self.envregion_template = template
        self.default_blob_factory = default_blob_factory
    
    def generate_envregion(self):
        """Generates an EnvRegion based on the template."""
        region = EnvRegion(self.envregion_template.region_name, long_lat=self.envregion_template.long_lat)

        for envnode_template in self.envregion_template.envnode_templates:
            factory = EnvNodeFactory()
            node = factory.generate_envnode(envnode_template, self.default_blob_factory, region)
            
            region.add_node(node)
        
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



    Default available action types are:


        move_population
            Moves population from one node to another. TODO Assumes a valid operation.
                Params:
                    origin_region: origin region.
                    origin_node: origin node.
                    destination_region: destination region.
                    destination_node: destination node.
                    quantity: population size to be moved.
                    population_template: PopTemplate to be matched by the operation.

        return_population_home
            Moves each population native to a region back.
                Params:
                    region: region calling people home
                    node: node calling people home
                    quantity: quantity of people to come home, currently not implemented TODO
                    population_template: PopTemplate of population to return



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

        self.routine_cycle_length:int = 24
        self.time_action_map:dict[str, callable] = { }
        self.base_actions = set()
        self.data_action_map:dict[str, callable] = { }
        # self.time_action_map:dict[str, callable] = { 'move_population' : self.move_population }
        # self.base_actions = {'move_population'}
        
        self.loaded_plugins: list[ActionPlugin] = []
        self.loaded_logger_plugins: list[logger_plugin.LoggerPlugin] = []
        self.loaded_routine_plugins: list[RoutinePlugin] = []
        self.global_actions = set()

        # repeating actions are a tuple of (cycle_length or frame_list, time_action)
        self.repeating_global_actions = []

        # Logging data
        self.original_population_template = None
        self.original_block_template: population.CharacteristicsFactory = None
        self.original_repeating_actions = None

        # Queued actions
        self.next_frame_queue = []
        # Queued actions priority 'first' or 'last'
        self.queued_action_priority = 'first'

        self.experiment_name = "test"
        self.experiment_config = {}

        # Distances:
        # self.node_distances:dict[str,list[tuple[float,str]]] = {}
        self.default_distance_type: util.DistanceType = DistType.METRES_PYPROJ
        self.node_distances:dict[util.DistanceType, dict[str, EnvNodeDistances]] = {t:{} for t in util.DistanceType}

        #self.od_matrix_logger:od_matrix_logger.ODMatrixLogger = None
        self.movement_logger_dict = {}
        self.characteristic_change_logger = {}
        
        # Events test
        Blob.events.on_traceable_property_changed += self.log_traceable_change
      

    def get_node_by_name(self, region_name, node_name):
        return self.region_dict[region_name].get_node_by_unique_name(node_name)

    def get_node_by_id(self, _id) -> EnvNode:
        return self.node_id_dict[_id]

    def get_region_by_name(self, name) -> EnvRegion:
        return self.region_dict[name]

    def get_region_by_id(self, _id) -> EnvRegion:
        return self.region_id_dict[_id]
    
    # Node Distance Functions
    def calculate_all_distances(self):
        ''' Auxiliary function to calculate all node distances'''
        for node in self.node_list:
            self.get_node_distances(node)

    def get_node_distances(self, 
                          target_node:EnvNode, 
                          dist_type:DistType = DistType.LONG_LAT) -> EnvNodeDistances:
        '''Gets distances between a target node and all other nodes'''
        unique_name = target_node.get_unique_name()

        # Checks if the distance was calculated previously
        if unique_name in self.node_distances[dist_type]:
            return self.node_distances[dist_type][unique_name]
        
        node_dist = EnvNodeDistances(unique_name)
        node_pos = target_node.long_lat
        for other in self.node_list:
            if unique_name == other.get_unique_name():
                continue
            node_dist.distance_to_others[other.get_unique_name()] = self.__get_distance(node_pos, other.long_lat, dist_type)

        self.node_distances[dist_type][unique_name] = node_dist
        return self.node_distances[dist_type][unique_name]

    def __get_distance(self, p1, p2, dist_type:DistType = DistType.LONG_LAT):
        '''Gets distances based on selected distance type'''
        if dist_type == DistType.LONG_LAT:
            return util.distance2D(p1, p2)
        elif dist_type == DistType.METRES_GEOPY:
            return util.geopy_distance_metre(p1, p2)
        elif dist_type == DistType.METRES_PYPROJ:
            return util.pyproj_distance_metre(p1, p2)
        else:
            raise Exception("Distance Type is invalid")

    # Action Invoke Modes
    def process_routines(self, hour):
        action_list = []
        for region in self.region_list:
            action_list += region.generate_action_list(hour)
        return action_list

    def direct_action_invoke(self, action, hour, time):
        self.consume_time_action(action, hour, time)

    def queue_next_frame_action(self, action):
        self.next_frame_queue.append(action)

    def process_queued_actions(self):
        action_list = []
        action_list += self.next_frame_queue
        self.next_frame_queue.clear()
        return action_list

    def process_repeating_global_actions(self, global_action_list, hour):
        action_list = []
        # do repeating actions
        for rga in global_action_list:
            if (type(rga[0]) is int and hour % rga[0] == 0) or (type(rga[0]) is list and hour in rga[0]):
                for region in self.region_list:
                    for node in region.node_list:
                        if 'node_name' in rga[1].values and node.node_type != rga[1].values['node_name']:
                            continue
                        if 'node_type' in rga[1].values and node.node_type not in rga[1].values['node_type']:
                            continue
                        
                        action = copy.deepcopy(rga[1])
                        if type(rga[0]) is list:
                            action.values['frames'] = rga[0]
                        else:
                            action.values['cycle_length'] = rga[0]
                        action.values['region'] = region.name
                        action.values['node'] = node.node_type
                        action.values['node_id'] = node.id
                        action_list += [action]
        return action_list

    # END Action Invoke Modes

    def get_population_size(self, population_template = None):
        """Gets the total population size contained in this EnvironmentGraph.
        
        Gets the sum of each node's get_population_size.
        If a population_template is defined, gets the population size of the 
        population which matches that template.

        Args:
            population_template: A PopTemplate to be matched by this operation.

        Returns:
            The sum of each node's get_population_size, matching the population_template.
        """
        size = 0
        for node in self.node_list:
            size += node.get_population_size(population_template)
        return size
    
    def get_blob_count(self)->int:
        """Gets the total number of Blobs contained in this EnvironmentGraph."""
        return sum([rg.get_blob_count() for rg in self.region_list])

    def update_time_step(self, cycle_step, simulation_step):
        """Updates a time step for a given time.
        Updates Routines and Repeating Global Actions.

        Applies every TimeAction which matches time argument.
        """
        for _llp in self.loaded_logger_plugins:
            _llp.update_time_step(cycle_step, simulation_step)
        for _lp in self.loaded_plugins:
            _lp.update_time_step(cycle_step, simulation_step)

        actions = self.generate_action_list(cycle_step, simulation_step)
        simplified_actions   = self.simplify_action_list(actions, cycle_step, simulation_step)
        #balanced_actions     = self.balance_action_list(simplified_actions)

        #for action in balanced_actions:
        #     self.consume_time_action(action, hour, time)

        for action in simplified_actions:
            self.consume_time_action(action, cycle_step, simulation_step)

        #merge all nodes coming from the same origin
        for node in self.node_list:
            self.merge_node(node)

        # set frame origin nodes for all blobs
        self.set_frame_origin_nodes()


    def generate_action_list(self, cycle_step, simulation_step):
        """Generates the TimeAction list for every EnvRegion, for a given time slot and the Repeating Global Actions for this hour."""
        action_list = []

        # Actions queued as first
        if self.queued_action_priority == 'first':
            action_list += self.process_queued_actions()
        
        # Default Repeating Global Actions + Routine Plugins Start Global Actions
        for rp in self.loaded_routine_plugins:
            action_list.extend(self.process_repeating_global_actions(rp.start_of_step_global_actions, cycle_step))
        action_list += self.process_repeating_global_actions(self.repeating_global_actions, cycle_step)

        # Routine Plugins Start Actions
        for rp in self.loaded_routine_plugins:
            action_list.extend(rp.process_start_of_step_actions(cycle_step=cycle_step, simulation_step=simulation_step))

        # Default Routines
        action_list += self.process_routines(cycle_step)

        # Routine Plugins End Actions
        for rp in self.loaded_routine_plugins:
            action_list.extend(rp.process_end_of_step_actions(cycle_step=cycle_step, simulation_step=simulation_step))

        # Routine Plugins End Global Actions
        for rp in self.loaded_routine_plugins:
            action_list.extend(self.process_repeating_global_actions(rp.end_of_step_global_actions, cycle_step))

        # Actions queued as last
        if self.queued_action_priority == 'last':
            action_list += self.process_queued_actions()

        return action_list

    def consume_time_action(self, time_action:Action, hour, time):
        """Applies the graph operations (moving population, etc) of a given TimeAction.
        Args:
            time_action: A TimeAction to be processed.
        """
        
        action_type = time_action.action_type
        pop_template = time_action.pop_template
        values = time_action.values

        if action_type in self.base_actions:
            self.time_action_map[action_type](pop_template,values, hour, time)
        else:
            simplified_action = self.time_action_map[action_type](pop_template, values, hour, time)
            for action in simplified_action:
                #print('\n\naction ', action, '\n\n')
                self.consume_time_action(action, hour, time)


    def balance_action_list(self, action_list):
        ## corrects the quantities of agents flow to and from each region
        ## TODO not implemented yet
        ##print('EnvironmentGraph.balance_action_list not implemented yet')
        # TODO probably wrong because of templates
        totals = {}
        # accumulate totals
        for action in action_list:
            og_node = action['origin_node']
            pop_temp = action['population_template']
            node_pop = og_node.get_population_size(pop_temp)
            quantity = action['quantity']
            interpreted_quantity = max(-1, min(quantity, node_pop))
            totals[og_node] += interpreted_quantity
        # correct quantities     
        for action in action_list:
            og_node = action['origin_node']
            node_pop = og_node.get_population_size(pop_temp)
            quantity = action['quantity']

            action['quantity']  = int((quantity / totals[og_node]) * min(node_pop,  totals[og_node]))

        return action_list

    def apply_action_list(self, action_list):
        for action in action_list:
            self.time_action_map[action.type](action.values)

    def simplify_action_list(self, action_list:list[Action], hour, time):
        #simp_list = []

        while not all([x.action_type in self.base_actions for x in action_list]):
            i  = action_list.pop(0)
            if i.action_type not in self.base_actions:
                if i.action_type not in self.time_action_map:
                    exit(f"ERROR: TimeAction type {i.action_type} cannot be consumed. Please check if correct plugins are loaded.")
                sub_list = self.time_action_map[i.action_type](i.pop_template, i.values, hour, time)
                action_list += sub_list
            else:
                action_list += [i]

        # i = 0
        # while i != len(action_list):
        #     item  = action_list[i]
        #     if item.type not in self.base_actions:
        #         sub_list = self.time_action_map[item.type](item.values, hour, time)
        #         action_list.remove(item)
        #         action_list += sub_list
        #     else:
        #         i+=1

        #print(f'All stuff is true in this bagaça at time {time} with len {len(action_list)} = {all([x.type in self.base_actions for x in action_list])}\n')
        #print(f'Centro total movement = {sum([i.values["quantity"] if i.values["origin_region"] == "Centro"  else 0 for i in action_list ])}')

        return action_list

    def add_region(self, _position, _template: EnvRegionTemplate, blob_factory: BlobFactory):
        factory = EnvRegionFactory(_template, blob_factory)
        new_region = factory.generate_envregion()
        new_region.population = new_region.get_population_size()
        self.edge_table.append(['' for x in range(len(self.region_list))])

        for node in new_region.node_list:
            node.containing_region_name = new_region.name
            self.node_list.append(node)
            self.node_dict[node.get_unique_name()] = node
            self.node_id_dict[node.id] = node

        self.region_dict[_template.region_name] = new_region        
        self.region_list.append(new_region)
        self.region_id_dict[new_region.id] = new_region

    # def add_node_to_region(self, region:EnvRegion, node_template:EnvNodeTemplate, node_unique_name:str) -> EnvNode: 
    #     factory = EnvNodeFactory(node_template)
    #     node = factory.generate_envnode(region,node_unique_name)
    #     region.add_node(node)
    #     self.node_list.append(node)
    #     self.node_dict[node.get_unique_name()] = node
    #     self.node_id_dict[node.id] = node
    #     return node


    def add_edge(self, region1, region2, _type):
        self.edge_table[region1][region2] = _type
    
    def set_global_action(self, action_type):
        self.global_actions.add(action_type)

    def set_repeating_action(self, cycle_length: int, action):
        self.repeating_global_actions.append((int(cycle_length), action))

    def set_repeating_action(self, frames: list[int], action):
        self.repeating_global_actions.append((frames, action))

    def remove_action(self, action_type):
        self.time_action_map.pop(action_type)

    def add_function(self, action_type, function, is_base):
        self.time_action_map[action_type] = function
        if is_base:
            self.base_actions.add(action_type)

    def load_time_action_plugin(self, plugin:ActionPlugin):
        self.loaded_plugins.append(plugin)
        for k, v in plugin.get_action_type_to_function().items():
            self.time_action_map[k] = v
                
    def has_plugin(self, _type:type) -> bool:
        return any(isinstance(x, _type) for x in self.loaded_plugins)
            
    def get_plugins(self, _type:type) -> list:
        return [p for p in self.loaded_plugins if isinstance(p,_type)]
    
    def get_first_plugin(self, _type:type):
        for p in self.loaded_plugins:
            if isinstance(p,_type): return p
        return None

    def LoadRoutinePlugin(self, plugin:RoutinePlugin):
        self.loaded_routine_plugins.append(plugin)

    ## ----------- Logging Functions ----------- ##

    def LoadLoggerPlugin(self, plugin:LoggerPlugin):
        plugin.load_to_enviroment(self)
        self.loaded_logger_plugins.append(plugin)

    def has_logger_plugin(self, _type:type) -> bool:
        return any(isinstance(x, _type) for x in self.loaded_logger_plugins)
            
    def get_logger_plugins(self, _type:type) -> list:
        return [p for p in self.loaded_logger_plugins if isinstance(p,_type)]
    
    def get_first_logger_plugin(self, _type:type):
        for p in self.loaded_logger_plugins:
            if isinstance(p,_type): return p
        return None 
    
    def start_logging(self):  
        for l in self.loaded_logger_plugins:
            l.start_logger()
    
    def log_simulation_step(self):    
        for l in self.loaded_logger_plugins:
            l.log_simulation_step()
    
    def stop_logging(self):    
        for l in self.loaded_logger_plugins:
            print("Stopping Logger:", l.__class__)
            l.stop_logger()


    def log_blob_movement(self, origin_node:EnvNode, destination_node:EnvNode, blobs:list[Blob]):
        for k,v in self.movement_logger_dict.items():
            v(origin_node, destination_node, blobs)
            #self.od_matrix_logger.log_od_movement(origin_node, destination_node, blobs)

    def log_traceable_change(self, blob:Blob, key, prev_val, new_val):
        for k,v in self.characteristic_change_logger.items():
            v(blob, key, prev_val, new_val)

    # -----------------------------------

    def merge_blobs(self):
        """Merges every blob with a compatible mother_blob_id in a given EnvNode."""
        for node in self.node_list:
            i = 0
            blob_list  = node.contained_blobs
        
            while i < len(blob_list):
                current_blob =  blob_list[i]

                for j in range(i+1, len(blob_list[i+1:])):   
                    other_blob = blob_list[j]
                    node.remove_blob(other_blob)
                    #if current_blob.mother_blob_id == other_blob.mother_blob_id:
                    #    current_blob.consume_blob(other_blob)
                    if current_blob.node_of_origin == other_blob.node_of_origin:
                        current_blob.merge_blob(other_blob)

                i+=1
                
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

    

    def merge_node(self, node: EnvNode):
        i = 0
        blob_list  = node.contained_blobs
    
        while i < len(blob_list):
            current_blob: Blob =  blob_list[i]

            j = i+1
            while j < len(blob_list):   
                other_blob: Blob = blob_list[j]
                
                if current_blob.mother_blob_id == other_blob.mother_blob_id and current_blob.compare_traceable_characteristics_to_other(other_blob):
                    current_blob.merge_blob(other_blob)
                    node.remove_blob(other_blob)
                else:
                    j+=1
            i+=1

    ## time action functions
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

    def set_frame_origin_nodes(self):
        for node in self.node_list:
            for blob in node.contained_blobs:
                blob.frame_origin_node = node.id

    ## END time action functions

    def __str__(self):
        return "{\"graph\":" + str(self.region_list) + "}"
    
    def __repr__(self):
        return "{\"graph\":" + str(self.region_list) + "}"
