from __future__ import annotations
from dataclasses import dataclass, field
from pprint import pprint
import time
import logger_plugin
import population
#import Plugins.Loggers.od_matrix_logger as od_matrix_logger
import copy
import util
from util import DistanceType as DistType
from events import Events
from random_inst import FixedRandom

DEBUG_OPERATION_OUTPUT =  False

#access streetways between blocks
class EnvEdge():
    """"Class representing a graph edge. 
        
    Currently not implemented. In the future this should represent different types of transportation.
    """

    def __init__(self):
        self.edge_type = ''
        

#point-of-interest
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
        characteristics: The environment characteristics this node has. 
    """

    def __init__(self):
        """"Inits EnvNode with an empty template."""
        self.name = ''
        self.contained_blobs:list[population.Blob] = [] 
        self.routine: Routine = None
        self.characteristics = {}
        self.long_lat:tuple[float, float] = [0.0, 0.0]
        self.id = util.IDGen('nodes').get_id()
        self.containing_region_name = None
        self.original_node_population:population.PropertyBlock = None

    def get_characteristic(self, key):
        return self.characteristics[key]
    
    def add_characteristic(self, key, value):
        self.characteristics[key] = value

    def process_routine(self, hour) -> list[TimeAction]:
        """Generates and returns the TimeAction list of the routine for a certain time.
        
        Args:
            time: The time slot to be processed.

        Returns:
            A list containing all TimeAction this EnvNode requires for the corresponding time.
        """
        return self.routine.process_routine(hour)

    def remove_blob(self, blob: population.Blob):
        if isinstance(blob, population.Blob) and blob in self.contained_blobs:
            self.contained_blobs.remove(blob)
            
    def remove_blobs(self, blobs: list[population.Blob]):
        for blob in blobs:
            self.remove_blob(blob)

    def add_blob(self, blob: population.Blob):
        if isinstance(blob, population.Blob):
            assert blob not in self.contained_blobs, "BLOB ALREADY HERE"
            self.contained_blobs.append(blob)

    def add_blobs(self, blobs: list[population.Blob]):
        for blob in blobs:
            self.add_blob(blob)

    def get_population_size(self, population_template = None):
        """Gets the total population size contained in this EnvNode.
        
        Gets the sum of each blob's get_population_size.
        If a population_template is defined, gets the population size of the 
        population which matches that template.

        Args:
            population_template: A PopTemplate to be matched by this operation.

        Returns:
            The sum of each contained_blob's get_population_size, matching the population_template.
        """
        count = 0
        for blob in self.contained_blobs:
            count += blob.get_population_size(population_template)
        return count

    def grab_population(self, quantity: int, template : population.PopTemplate = None) -> list[population.Blob]:
        """Gets and removes a population matching a template from this EnvNode.
        
        The population removed is returned as a list of blobs, each with a unique mother_blob_id.

        If quantity is larger than the current population size matching the tamplate,
        this method returns the largest possible population.

        Args:
            quantity: The desired population size to be grabbed from this EnvNode.
            template: The PopTemplate to be matched.,

        Returns:
            If there are enough population, a list containing the grabbed population. This list might have more than one Blob.
                In such case, each blob is guaranteed to be from different mother_blob_id.
            If there are not enough population, returns the available amount.
        """
        total_available_population = self.get_population_size(template)

        if total_available_population == 0:
            return []

        quantity = min(quantity, total_available_population)
        
        if quantity <= 0:
            return []
        
        new_blobs = []

        available_quantities = [blob.get_population_size(template) for blob in self.contained_blobs]
        int_adjusted_quantities = util.weighted_int_distribution(available_quantities, quantity)
        
        for x in range(len(self.contained_blobs)):
            # quantity * ratio of this blobs contribution to the total
            if int_adjusted_quantities[x] == 0:
                continue
            blob = self.contained_blobs[x]
            
            adjusted_quantity = int_adjusted_quantities[x]
            grabbed_blob = blob.grab_population(adjusted_quantity, template)
            new_blobs.append(grabbed_blob)

        self.remove_blobs(new_blobs)
        return new_blobs

    def change_blobs_traceable_property(self, key, value, quantity:int, template:population.PopTemplate = None):
        _grabbed = self.grab_population(quantity, template)
        self.add_blobs(_grabbed)

        for _blob in _grabbed:
            _blob.set_traceable_property(key, value)
            _blob.previous_node = self.id
            
            #if _blob.spawning_node is None:
            #    _blob.spawning_node = self.id
            _blob.frame_origin_node = self.id

    def change_blob_traceable_property(self, blob:population.Blob, key, value, quantity:int, template:population.PopTemplate = None) -> population.Blob:
        
        if quantity == 0:
            return

        assert blob in self.contained_blobs, "Blob is not in the contained blobs of node" + blob.verbose_str() + str(self)
                    
        _grabbed = blob.grab_population(quantity, template)

        if _grabbed is None:
            return
        if blob is not _grabbed:
            self.add_blob(_grabbed)
        
        _grabbed.set_traceable_property(key, value)
        _grabbed.previous_node = blob.previous_node
        #if _blob.spawning_node is None:
        #    _blob.spawning_node = self.id
        _grabbed.frame_origin_node = blob.frame_origin_node
        return _grabbed
        
    
    def get_unique_name(self):
        return f"{self.containing_region_name}//{self.name}"

    def __str__(self):
        return '{{\"name\" : \"{0}\", \"id\" : \"{1}\", \"routine\"  : {2}, \"characteristics\"  : {3}, \"blobs\"  : {4}}}'.format(
                                                                                self.name,
                                                                                self.id,
                                                                                self.routine,
                                                                                self.characteristics,
                                                                                self.contained_blobs)

    def __repr__(self):
        return '{{\"name\" : \"{0}\", \"id\" : \"{1}\", \"routine\"  : {2}, \"characteristics\"  : {3}, \"blobs\"  : {4}}}'.format(
                                                                                self.name,
                                                                                self.id,
                                                                                self.routine,
                                                                                self.characteristics,
                                                                                self.contained_blobs)

class EnvNodeTemplate():    
    """Describes an EnvNode generation template.
    
    EnvNodeFactory objects can generate EnvNodes based on templates.
        
    TODO Use case.
    """

    def __init__(self):
        self.characteristics = {}
        self.routine_template = {}
        self.blob_descriptions = []
        self.long_lat:tuple[float, float]

    def add_characteristic(self, key, value):
        self.characteristics[key] = value

    def add_routine_template(self, hour, actions):
        """Adds a TimeAction to the designated time slot."""
        self.routine_template[str(hour)] = actions

    def add_action_to_template(self, hour, action):
        """Adds a TimeAction to the designated time slot."""
        if str(hour) not in self.routine_template:
            self.routine_template[str(hour)] = []
        self.routine_template[str(hour)].append(action)

    def add_long_lat_position(self, longitude:float, latitude:float):
        self.long_lat = [longitude,latitude]

    def add_blob_description(self, population, traceable_properties, description, blob_factory):
        self.blob_descriptions.append((population, traceable_properties, description, blob_factory))


class EnvNodeFactory():
    """A factory to generate EnvNodes with a particular template.
    
    Generates both an EnvNode and the respective Routine.
    
    """
    def __init__(self, _node_template: EnvNodeTemplate):
        self.template:EnvNodeTemplate = _node_template

    def GenerateRoutine(self, routine_template)->Routine:
        routine = Routine()
        for k, v in routine_template.items():
            routine.add_time_action(v, k)
        
        return routine

    def Generate(self, region:EnvRegion, _name)->EnvNode:
        node  = EnvNode()
        node.name = _name
        node.long_lat = self.template.long_lat
        node.routine = self.GenerateRoutine(self.template.routine_template)
        for k in self.template.characteristics.keys():
            node.characteristics[k] = self.template.characteristics[k]

        for (pop,trace,desc,factory) in self.template.blob_descriptions:
            blob: population.Blob = factory.GenerateProfile(region.id, node.id, pop, desc, trace)
            node.add_blob(blob)
            
        return node


# envregion
class EnvRegion():
    """"Represents a particular region of simulation.
    
    A region is an abstraction for a set of points of interest and initial population.
    It is assumed its initial population returns frequently.

    EnvRegions are a possible abstraction for an aggregation of points-of-interest.

    Depending on abstraction level, an EnvRegion can represent:
        A neighborhood containing blocks, markets, schools;
        A city containing neighborhoods or discretized regions;
        A state containing cities and towns;
        A country containing states;

    Ideally, an EnvRegion is constructed using an EnvRegionFactory.

    Attributes:
        id: A unique integer region identifier.
        position: The physical location of this region.
        population: The total population size in this region.
        node_list: Contained EnvNodes in this region.
        neighbours: Currently unused. The relation between this region and each other region.

    """

    def __init__(self, _position = (0.0, 0.0), _long_lat = (0.0, 0.0), population = 0, _id = None):
        """Initializes an empty EnvRegion"""
        self.name:str = ''
        self.id: int = _id
        if _id is None:
            self.id = util.IDGen("regions").get_id()
        self.position:tuple[float, float] = _position
        self.long_lat:tuple[float, float] = _long_lat
        self.population:int = population
        self.node_list:list[EnvNode] = []
        self.node_dict:dict[str, EnvNode] = {}
        self.neighbours = [[]]

    def add_node(self, _node: EnvNode):
        self.node_list.append(_node)
        self.node_dict[_node.name] = _node
        _node.containing_region_name = self.name

    def get_population_size(self, template = None):
        """Gets the total population size contained in this EnvRegion.
        
        Gets the sum of each EnvNode's get_population_size.
        If a population_template is defined, gets the population size of the 
        population which matches that template.

        Args:
            population_template: A PopTemplate to be matched by this operation.

        Returns:
            The sum of each EnvNode in node_list's get_population_size, matching the population_template.
        """
        count = 0
        for node in self.node_list:
            count += node.get_population_size(template)

        return count
    
    def get_blob_count(self)->int:
        """Gets the total number of Blobs contained in this EnvRegion."""
        return sum([len(nd.contained_blobs) for nd in self.node_list])

    def generate_action_list(self, hour: int):
        """Gets the TimeAction list for each EnvNode in this EnvRegion for this time slot.
        
        Generate a TimeAction list which contais  each TimeAction for EnvNodes in this EnvRegion. 

        Args:
            time: The requested time slot.

        Returns:
            The concatenated TimeAction list.
        """
        action_list = []
        for node in self.node_list:
            action_list += node.process_routine(hour)

        return action_list

    def get_node_by_name(self, name) -> EnvNode:
        return self.node_dict[name]

    ## Not sure if its needed TODO
    ## maybe we only should do population grabs per node
    def grab_population(self, quantity, pop_template):
        """Gets and removes a population matching a template from this EnvRegion.
        
        The population removed is returned as a list of blobs, each with a unique mother_blob_id.

        If quantity is larger than the current population size matching the tamplate,
        this method returns the largest possible population.

        Population is extracted evenly from EnvNodes.

        TODO NOT IMPLEMENTED YET.

        Args:
            quantity: The desired population size to be grabbed from this EnvRegion.
            template: The PopTemplate to be matched.,

        Returns:
            A list containing the grabbed population. This list might have more than one Blob.
            In such case, each blob is guaranteed to be from different mother_blob_id.
        """
        print("EnvRegion.grab_population not implemented yet")
        pass

    def __str__(self):
        return '{{\"id\" : {0}, \"name\" : \"{1}\",  \"position\" : {2}, \"nodes\" : {3}}}'.format(
                                                            self.id,
                                                            self.name,
                                                            self.position,
                                                            self.node_list
        )
    
    def __repr__(self):
        return '{{\"id\" : {0}, \"name\" : \"{1}\",  \"position\" : {2}, \"nodes\" : {3}}}'.format(
                                                            self.id,
                                                            self.name,
                                                            self.position,
                                                            self.node_list
        )

class EnvRegionTemplate():
    """Describes a template for generating EnvRegions"""

    def __init__(self):
        self.template:list[tuple[str,EnvNodeTemplate]] = []

    def add_template_node(self, node_name:str, _node_template:EnvNodeTemplate):
        self.template.append((node_name, _node_template))
    

class EnvRegionFactory():
    """Generates EnvRegions based on a specific EnvRegionTemplate."""

    def __init__(self, _template:EnvRegionTemplate):
        self.region_template = _template
    
    def Generate(self, _position:tuple[float,float]):
        region = EnvRegion(_position)

        for c in self.region_template.template:
            node_name, node_template = c
            factory = EnvNodeFactory(node_template)
            node = factory.Generate(region,node_name)
            
            region.add_node(node)
        
        return region

@dataclass
class EnvNodeDistances():
    node_name: str = ''
    distance_to_others:dict[str, float] = field(default_factory = lambda: ({}))

    def get_distance_tuples(self):
        return sorted(self.distance_to_others.items(), key=lambda item: item[1])
    
    #distance_to_others:list[tuple[float,str]] = field(default_factory=lambda: [])

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
        
        self.loaded_plugins: list[TimeActionPlugin] = []
        self.loaded_logger_plugins: list[logger_plugin.LoggerPlugin] = []
        self.loaded_routine_plugins: list[RoutinePlugin] = []
        self.global_actions = set()

        # repeating actions are a tuple of (cycle_length or frame_list, time_action)
        self.repeating_global_actions = []

        # Logging data
        self.original_population_template = None
        self.original_block_template: population.BlockTemplate = None
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
        population.Blob.events.on_traceable_property_changed += self.log_traceable_change
      

    def get_node_by_name(self, region_name, node_name):
        return self.region_dict[region_name].get_node_by_name(node_name)

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
                        if 'node_name' in rga[1].values and node.name != rga[1].values['node_name']:
                            continue
                        if 'node_type' in rga[1].values and node.name not in rga[1].values['node_type']:
                            continue
                        
                        action = copy.deepcopy(rga[1])
                        if type(rga[0]) is list:
                            action.values['frames'] = rga[0]
                        else:
                            action.values['cycle_length'] = rga[0]
                        action.values['region'] = region.name
                        action.values['node'] = node.name
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

    def consume_time_action(self, time_action:TimeAction, hour, time):
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

    def simplify_action_list(self, action_list:list[TimeAction], hour, time):
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

    def add_region(self, _position, _template: EnvRegionTemplate, name):
        factory = EnvRegionFactory(_template)
        new_region = factory.Generate(_position)
        new_region.name = name
        new_region.population = new_region.get_population_size()
        self.edge_table.append(['' for x in range(len(self.region_list))])

        for node in new_region.node_list:
            node.containing_region_name = new_region.name
            self.node_list.append(node)
            self.node_dict[node.get_unique_name()] = node
            self.node_id_dict[node.id] = node

        self.region_dict[name] = new_region        
        self.region_list.append(new_region)
        self.region_id_dict[new_region.id] = new_region

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

    def load_time_action_plugin(self, plugin:TimeActionPlugin):
        self.loaded_plugins.append(plugin)
        for k, v in plugin.get_pairs().items():
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


    def log_blob_movement(self, origin_node:EnvNode, destination_node:EnvNode, blobs:list[population.Blob]):
        for k,v in self.movement_logger_dict.items():
            v(origin_node, destination_node, blobs)
            #self.od_matrix_logger.log_od_movement(origin_node, destination_node, blobs)

    def log_traceable_change(self, blob:population.Blob, key, prev_val, new_val):
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
                        current_blob.consume_blob(other_blob)

                i+=1
                
    def add_blobs_traceable_property(self, key, value):
        for node in self.node_list:
            for blob in node.contained_blobs:
                blob.set_traceable_property(key, value)
                
    # def lambda_blobs_traceable_property(self, key, lambda_funtion):
    #     for node in self.node_list:
    #         for blob in node.contained_blobs:
    #             blob.traceable_properties[key] = lambda_funtion(blob.traceable_properties[key])
                #print("days", blob.traceable_properties[key])
                
    def lambda_blobs_traceable_property(self, key, lambda_funtion):
        for node in self.node_list:
            for blob in node.contained_blobs:
                blob.set_traceable_property(key, lambda_funtion(blob, blob.get_traceable_property(key)))

    

    def merge_node(self, node: EnvNode):
        i = 0
        blob_list  = node.contained_blobs
    
        while i < len(blob_list):
            current_blob: population.Blob =  blob_list[i]

            j = i+1
            while j < len(blob_list):   
                other_blob: population.Blob = blob_list[j]
                
                if current_blob.mother_blob_id == other_blob.mother_blob_id and current_blob.compare_traceable_properties_to_other(other_blob):
                    current_blob.consume_blob(other_blob)
                    node.remove_blob(other_blob)
                else:
                    j+=1
            i+=1

    ## time action functions
    def set_original_populations(self):
        for node in self.node_list:
            for blob in node.contained_blobs:
                prop_block = population.PropertyBlock(_population = blob.get_population_size())
                prop_block.initialize_buckets_profile(blob.blob_factory.block_template, blob.profiles)
                if node.original_node_population == None:
                    node.original_node_population = prop_block
                else:
                    node.original_node_population.add_block(prop_block)

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

# Defines a time action command
class TimeAction():
    """Describes a command-like TimeAction.
    
    TimeActions should be modelled and described in a contract for the simulator.
    Type and expectd values should be respected.

    TimeActions are either base actiors or composite actions.

    Each TimeAction is to be associated either:
        With a graph operator, for base actions; or
        A base TimeAction decomposition, for composite actions.
    """
    def __init__(self, action_type:str, pop_template:population.PopTemplate, values:dict):
        if type(pop_template) != population.PopTemplate:
            print("FUCK")

        self.action_type:str = action_type
        self.pop_template:population.PopTemplate = pop_template
        self.values:dict = values
        if "population_template" in self.values:
            self.values.pop("population_template")
        #    if isinstance(self.values["population_template"], dict):
        #        print("Adapting op template", self.values["population_template"])
        #        self.pop_template = population.PopTemplate(self.values["population_template"])
        #        self.values.pop("population_template")
                #self.values["population_template"] = population.PopTemplate(self.values["population_template"])



    def __str__(self):
        return '{{\"type\" : \"{0}\", \"pop_template\" : \"{1}\", \"values\"  : {2}}}'.format(self.action_type,
                                                                                        self.pop_template,
                                                                                        self.values)

    def __repr__(self):
        return '{{\"type\" : \"{0}\", \"pop_template\" : \"{1}\", \"values\"  : {2}}}'.format(self.action_type,
                                                                                        self.pop_template,
                                                                                        self.values)




class TimeActionPlugin():
    """Describes a set of action types and action function pairs.
    This class is used to extend the functionality of the simulator with additional TimeActions.
    
    Added functions should be 
    (string, dict) -> [TimeAction]

    the dict is a dictionary of values to be read from the input json.

    This parameters passed in the dictionary are defined by the plugin contracts.

    """ 
    def __init__(self):
        self.type_action_pairs = {}
        
        # Perfomance
        self.execution_times = []

    def add_execution_time(self, time):
        self.execution_times.append(time)

    def print_execution_time_data(self):
        print("\n",self.__class__.__name__,"Execution Time Data")
        print("---Number of executions:", len(self.execution_times))
        print("---Total execution time:", sum(self.execution_times))
        if len(self.execution_times) > 0:
            print("---Average execution time:", sum(self.execution_times)/len(self.execution_times))

    def set_pair(self, action_type, action_function):
        self.type_action_pairs[action_type] = action_function

    def get_pairs(self):
        return self.type_action_pairs
    
    def setup_logger(self,logger):    
        raise NotImplementedError("SubClass should implement the \"setup_logger\" method")

    def update_time_step(self, cycle_step, simulation_step):
        raise NotImplementedError("SubClass should implement the \"update_time_step\"  method" + str(type(self)))
    
    def log_data(self,logger):    
        raise NotImplementedError("SubClass should implement the \"log_data\"  method")
    
    def stop_logger(self,logger):    
        raise NotImplementedError("SubClass should implement the \"stop_logger\"  method")
    
    def unload_plugin(self):
        pass

class RoutinePlugin():
    """
    """
    def __init__(self) -> None:
        self.start_of_step_global_actions = []
        self.start_of_step_actions = []
        self.end_of_step_global_actions = []
        self.end_of_step_actions = []

    def process_start_of_step_actions(self, cycle_step, simulation_step):
        raise NotImplementedError("SubClass should implement the \"process_start_of_step_actions\"  method" + str(type(self)))
    
    def process_end_of_step_actions(self, cycle_step, simulation_step):
        raise NotImplementedError("SubClass should implement the \"process_end_of_step_actions\"  method" + str(type(self)))

    def update_time_step(self, cycle_step, simulation_step):
        raise NotImplementedError("SubClass should implement the \"update_time_step\"  method" + str(type(self)))
    

class Routine():
    """Describes a mapping of time slot -> TimeAction.

    This mapping should describe the routine an EnvNode follows during the simulation period, cyclically.
    The period of Routine repetition is part of simulation modelling.
    
    Each time slot matches to one specific TimeAction, describing the requested operation for any given time slot.

    TODO Make so time_actions maps time_slot -> [actions] instead of time_slot -> action
    """
    def __init__(self):
        # map of time ->  time_action
        self.time_actions = {}
        self.label = None

    def add_time_action(self, time_action, hour):
        # if time not in self.time_actions:
        #     self.time_actions[time] = []
        # self.time_actions[time].append(time_action)
        self.time_actions[str(hour)] = time_action

    def process_routine(self, hour) -> list[TimeAction]:
        if str(hour) in self.time_actions:
            return self.time_actions[str(hour)]
        else:
            return []

    def __str__(self):
        return '{{\"name\" : \"{0}\", \"actions\"  : {1}}}'.format(
                                                                                self.label,
                                                                                self.time_actions
                                                                                )

    def __repr__(self):
        return '{{\"name\" : \"{0}\", \"actions\"  : {1}}}'.format(
                                                                                self.label,
                                                                                self.time_actions
                                                                                )


