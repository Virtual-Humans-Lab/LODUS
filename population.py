#import random
from __future__ import annotations
import copy
import sys
from types import NoneType
from util import *
from random_inst import FixedRandom
from events import Events

from typing import Any, Union, List, Dict, Optional

class CharacteristicsFactory():
    """
    A factory for generating population characteristics.

    This class allows for the addition of sampled and traceable characteristics,
    and provides methods to generate collections of sampled characteristics for a given population.

    Attributes:
        sampled_characteristics (dict[str, list[str]]): A dictionary to store sampled characteristics.
        traceable_characteristics (dict[str, Any]): A dictionary to store traceable characteristics.

    Methods:
        add_sampled_characteristic(name: str, categories: list[str]):
            Adds a sampled characteristic with the given name and categories.
        add_traceable_characteristic(name: str, value):
            Adds a traceable characteristic with the given name and value.
        generate_characteristic_collection(population: int) -> SampledCharacteristicCollection:
            Generates a characteristic collection for the given population.
        generate_characteristic_collection_empty() -> SampledCharacteristicCollection:
            Generates an empty characteristic collection.
        generate_characteristic_collection_with_profile(population: int, pop_profile: dict):
            Generates a characteristic collection for the given population with a profile.

    Use case:
        dummy = PopulationCharacteristicsTemplate()
        dummy.add_sampled_characteristic('age', ['child', 'adult', 'ancient'])
        dummy.add_sampled_characteristic('economic_profile', ['unemployed', 'worker'])
        dummy.add_sampled_characteristic('social_profile', ['low', 'mid', 'high'])
        dummy.add_sampled_characteristic('risk', ['low', 'mid', 'high'])
    """
    
    def __init__(self):
        self.sampled_characteristics: dict[str, list[str]] = {}
        self.traceable_characteristics: dict[str, Any] = {}

    def add_sampled_characteristic(self, name: str, categories: list[str]):
        self.sampled_characteristics[name] = list(dict.fromkeys(categories))
        
    def add_traceable_characteristic(self, name: str, value):
        self.traceable_characteristics[name] = value

    def _validate_population(self, population: int) -> bool:
        return bool(self.sampled_characteristics) and population > 0

    def _create_characteristic_collection(self, population: int) -> SampledCharacteristicCollection:
        characteristic_collection = SampledCharacteristicCollection(population, self)
        characteristic_collection.set_values_rand(self)
        return characteristic_collection
         
    def generate_characteristic_collection_rand(self, population: int) -> SampledCharacteristicCollection:
        if not self._validate_population(population):
            raise ValueError(f"Invalid population. Size must be greater than 0, is {population}. Characteristics should be valid, and are {bool(self.sampled_characteristics)}.")
        return self._create_characteristic_collection(population)
    
    def generate_characteristic_collection_empty(self) -> SampledCharacteristicCollection:
        if not self.sampled_characteristics:
            raise ValueError("No sampled characteristics defined before using generate.")
        return self._create_characteristic_collection(0) 
  
    def generate_characteristic_collection_with_profile(self, population: int, pop_profile: dict):
        if not self._validate_population(population):
            raise ValueError(f"Invalid population. Size must be greater than 0, is {population}. Characteristics should be valid, and are {bool(self.sampled_characteristics)}.")
        characteristic_collection = SampledCharacteristicCollection(population, self)
        characteristic_collection.set_values_profile(self, pop_profile)
        return characteristic_collection
    

class SampledCharacteristic():
    """A sampled characteristic models a single attribute of a population.
    
    It represents a distribution of possible values (or ranges, in the case of continuous properties) and their respective population quantities. 
    
    The characteristic is stored as a dictionary that maps each possible categoriy to the corresponding population count.

    For example:
        In a population of 100 people:
        {'child': 20, 'adult': 60, 'elder': 20}
        would be a mapping of the 'age' characteristic.

    The mapping is defined during modelling time.

    Attributes:
        name (str): The name of the represented characteristic.
        categories (dict): A dictionary mapping each characteristic categories to its population count.
    """

    def __init__(self, _characteristic: str):
        self.name: str = _characteristic
        self.categories: dict[str, int] = {}

    def get_population_size(self, key: Optional[Union[str, List[str], set]] = None) -> int:
        """
        Returns the population size in this SampledCharacteristic. 

        Args:
            key (Union[str, List[str], set], optional): A specific key or list/set of keys. 
                If None, returns the total population.

        Returns:
            int: Population size.
        """
        if not key: # select all
            return sum(self.categories.values())
        if isinstance(key, str): # select single value
            return self.categories[key]
        if isinstance(key, (list, set)): # select multiple values
            return sum([self.categories[k] for k in set(key)])
        raise ValueError(f"Invalid key type: {type(key)}")

    def set_values_rand(self, keys: list[str], population: int = 0) -> None:
        """
        Initializes random values for a set of values and population quantity.
        
        Args:
            keys (list[str]): A list of keys representing characteristic values.
            population (int, optional): The total population to be distributed among the keys. Defaults to 0.
        """
        # Initialize all keys with a population of 0
        self.categories = {k: 0 for k in keys}
        
        # Distribute the total population randomly among the keys
        values = distribute_randomly(total_sum=population, n_partitions=len(keys))
        
        # Update the values dictionary with the distributed population
        self.categories.update({k: values[index] for index, k in enumerate(keys)})

    def set_values(self, keys: list[str], populations: list[int]) -> None:
        """
        Assigns population counts to the given keys.

        Args:
            keys (list[str]): A list of keys representing characteristic values.
            populations (list[int]): A list of population counts corresponding to each key.

        Raises:
            ValueError: If the lengths of 'keys' and 'populations' do not match.
            ValueError: If 'keys' is empty.
            ValueError: If the total population (sum of 'populations') is zero or negative.
        """
        if not keys:
            raise ValueError("The 'keys' list must not be empty.")
        if len(keys) != len(populations):
            raise ValueError("The lengths of 'keys' and 'populations' must match.")
        if sum(populations) <= 0:
            raise ValueError("The total population (sum of 'populations') must be greater than zero.")

        # Create the mapping of keys to populations
        self.categories = dict(zip(keys, populations))

    def set_values_dict(self, data: Dict[str, int]) -> None:
        """
        Sets the values for the given keys with the corresponding population counts.
        
        Args:
            data (Dict[str, int]): A dictionary where keys are the keys and values are the population counts.
        """
        if not data:
            raise ValueError("The 'data' dictionary must not be empty.")
        if sum(data.values()) < 0:
            raise ValueError("The total population (sum of 'data' values) must be zero or greater.")
        self.categories = {key: population for key, population in data.items()}

    def merge_values(self, other: SampledCharacteristic) -> None:
        """Adds the values of another bucket to this one.
        
        If characteristics are not named equally, this method does not do anything.

        This function is not responsible for removing/destroying 'other' after the merge.
        """
        if self.name != other.name:
            return
        for key in self.categories:
            self.categories[key] = self.categories[key] + other.categories[key]

    def extract(self, quantity: int, selected_keys:Optional[Union[str, List[str], set]] = None) -> SampledCharacteristic:
        """Extracts a population quantity from this SampledCharacteristic and returns the extracted population in an auxiliary PropertyBucket.
    
        If key is set, quantity is removed exclusively from the key value.
        Otherwise, population is removed randomly.
        Extracted population is uniformly distributed according to the population size for each characteristic.

        If quantity for a given key is larger than available population,
        the entire population for that key is returned.

        Params:
            quantity: the population quantity to be removed from this bucket.
            selected_keys: The desired value(s) to be extracted. If None, extracts population randomly.
        
        Returns:
            An auxiliary SampledCharacteristic containing the extracted population, with same characteristic name and keys.
        """
        # Check if selected_keys is a valid type (str, list, set). None will pass this check
        if not isinstance(selected_keys, (str, list, set, NoneType)):
            raise TypeError(f"Selected keys {selected_keys} requested for a sampled characteristic are not a list {type(selected_keys)}. {self}")
        
        # if key is a set or a string, convert it to a list
        if isinstance(selected_keys, set):
            selected_keys = list(selected_keys)
        if isinstance(selected_keys, str):
            selected_keys = [selected_keys]

        
        aux_characteristic = SampledCharacteristic(self.name)

        values = []
        characteristic_keys = list(self.categories.keys())
        number_of_keys = len(characteristic_keys)

        quantity = min(quantity, self.get_population_size(selected_keys))
        
        if quantity == 0:
            aux_characteristic.set_values_dict({key: 0 for key in characteristic_keys})
            return aux_characteristic

        # If no specific keys are selected, sample randomly from the entire population
        if not selected_keys:
            sample_list = [i for i in range(number_of_keys) for _ in range(self.categories[characteristic_keys[i]])]
        # If specific keys are selected, sample only from those keys
        elif isinstance(selected_keys, list):
            sample_list = [i for i in range(number_of_keys) if characteristic_keys[i] in selected_keys for _ in range(self.categories[characteristic_keys[i]])]
             
        samples = FixedRandom.instance.sample(sample_list, quantity)
        values = [samples.count(i) for i in range(number_of_keys)]

        for i in range(number_of_keys):
            self.categories[characteristic_keys[i]] -= values[i]

        aux_characteristic.set_values_dict(dict(zip(characteristic_keys, values)))
        return aux_characteristic
    
    def __str__(self):
        return f"\"{self.name}\" : {self.categories}"

    def __repr__(self):
        s = '\"{0}\" : {1}'.format(self.name, self.categories)
        return s
        
class SampledCharacteristicCollection():
    """A collection of SampledCharacteristics, representing a population with multiple attributes at the same time.

    Attributes:
        population: initial population for the collection.
        template: BlockTemplate this collection uses.
        characteristics: The SampledCharacteristics this collection uses, mapped as characteristic_name -> SampledCharacteristic.
    """
    def __init__(self, _population: int, _factory: CharacteristicsFactory):
        self.population: int = _population
        self.factory: CharacteristicsFactory = _factory
        self.characteristics: dict[str,SampledCharacteristic] = {}
        
    def get_mapping_of_property_values(self):
        """Returns a list of lists containing property values for each characteristic."""
        return [list(v.categories.values()) for v in self.characteristics.values()]
    
    def is_valid(self) -> bool:
        """
        Check if the population characteristics are valid.

        Validation Criteria:
            - All population sizes must be consistent across characteristics.
            - No category value should be negative.
            - Population size should be non-negative.

        Returns:
            bool: True if the characteristics are valid, False otherwise.
        """
        population_sizes = {pop_size.get_population_size() for pop_size in self.characteristics.values()}
        
        # Ensure all categories have non-negative values
        if any(val < 0 for pop_size in self.characteristics.values() for val in pop_size.categories.values()):
            return False
        
        # Validate population size consistency
        return len(population_sizes) == 1 and next(iter(population_sizes)) >= 0

    def set_values_rand(self, characteristics_factory: CharacteristicsFactory):
        """Initializes SampledCharacteristics according to a CharacteristicsFactory."""
        self.factory = characteristics_factory
        for name, categories in characteristics_factory.sampled_characteristics.items():
            sampled_char = SampledCharacteristic(name)
            sampled_char.set_values_rand(categories, self.population)
            self.characteristics[name] = sampled_char

    def set_values_profile(self, factory: CharacteristicsFactory, profile: dict):
        """Initializes SampledCharacteristics according to a CharacteristicsFactory and population description.
        
        Profile is a dictionary with any number of bucket characteristics as keys, and
        each value is a dictionary (SampledCharacteristic name -> population quantity) pairs.

        If a characteristic is in the profile, the respective buckets are initialized
        according to:
            if characteristic is associated with a quantity, that quantity is used.
            if characteristic is not associated with a quantity, its initialized randomly.
        
        The generated collection respect the self.population value.
        """
        self.factory = factory

        for char_name, categories in self.factory.sampled_characteristics.items():
            caracteristic = SampledCharacteristic(char_name)
            if char_name in profile:
                self._initialize_profiled_characteristic(caracteristic, categories, profile[char_name])
            else:
                caracteristic.set_values_rand(categories, self.population)
            self.characteristics[char_name] = caracteristic
        
    def _initialize_profiled_characteristic(self, target:SampledCharacteristic, categories:list[str], char_profile:dict[str,int]):
        profile_categories = char_profile.keys()
        total_profiled_population = sum(char_profile.values())
        non_profiled_categories = list(set(categories) - set(profile_categories))

        self._validate_profile_keys(profile_categories, categories)

        cat_to_value = {k: 0 for k in categories}
        # If the total population of the profiled categories is larger than the total population, distribute the population according to the profile
        if total_profiled_population > self.population:
            weights = [char_profile[x] / total_profiled_population for x in profile_categories]
            int_distribution = distribute_ints_from_weights(self.population, weights)
            for index, value in enumerate(profile_categories):
                cat_to_value[value] = int_distribution[index]
        # If the total population of the profiled categories is smaller than the total population, distribute the population according to the profile and distribute the remaining population randomly
        else:
            for k in profile_categories:
                cat_to_value[k] = char_profile[k]
            self._distribute_remaining_population(cat_to_value, categories, non_profiled_categories, total_profiled_population)

        target.set_values_dict(cat_to_value)    
    
    def _validate_profile_keys(self, profile_keys, bucket_keys):
        for k in profile_keys:
            if k not in bucket_keys:
                sys.exit(f"Error: The key '{k}' defined in a population profile is not a possible value for this SampledCharacteristic. Available keys: {bucket_keys}.")

    def _distribute_remaining_population(self, cat_to_qnt: dict[str, int], categories : list[str], non_profiled_categories: list[str], total_profiled_population: int):
        remaining_population = self.population - total_profiled_population
        # If there are non-profiled categories, distribute the remaining population randomly among them
        if non_profiled_categories:
            for _ in range(remaining_population):
                rand_key = non_profiled_categories[FixedRandom.instance.randint(0, len(non_profiled_categories) - 1)]
                cat_to_qnt[rand_key] += 1
        # If all categories were profiled, distribute the remaining population randomly among them
        else:
            for _ in range(remaining_population):
                rand_key = categories[FixedRandom.instance.randint(0, len(categories) - 1)]
                cat_to_qnt[rand_key] += 1
             

    def merge_characteristic_collection(self, other: SampledCharacteristicCollection):
        """Adds the values of another SampledCharacteristicsCollection to this one."""
        for key in self.characteristics:
            self._merge_characteristic(other.characteristics[key])
            # self.characteristics[key].merge_values(other.characteristics[key])

    def _merge_characteristic(self, other: SampledCharacteristic):
        """Adds the values of other SampledCharacteristic to the appropriate local SampledCharacteristic.
        
        Population balance between characteristics is responsability of the caller.

        Does not guarantee block validity.
        """
        self.characteristics[other.name].merge_values(other)

    def get_population_size(self, population_template: Optional[PopulationTemplate] = None) -> int:
        """Gets the population size matching a PopTemplate, or the total population size if no template is provided."""
        # No template defined - returns entire population
        if population_template is None or not population_template.has_sampled_properties():
            return next(iter(self.characteristics.values())).get_population_size()
        
        min_population = sys.maxsize
        
        for key, template_value in population_template.sampled_characteristics.items():
            if key in self.characteristics:
                min_population = min(
                    min_population, self.characteristics[key].get_population_size(template_value)
                )

        return min_population

    def extract(self, quantity: int, population_template: Optional[PopulationTemplate] = None) -> Optional[SampledCharacteristicCollection]:
        """Extracts a population quantity from this SampledCharacteristicsCollection.
        
        For keys not in the PopulationTemplate, values and quantities are selected randomly.
        For keys in the PopulationTemplate, values respect those selections.

        If quantity is larger than avaiable population matching template, returns as much as possible.

        Returns:
            A SampledCharacteristicsCollection with the extracted population.
        
        """
        if not population_template:
            population_template = PopulationTemplate()

        quantity = min(quantity, self.get_population_size(population_template))
        if quantity <= 0:
            return None
        
        extracted_characteristics: dict[str, SampledCharacteristic] = {}
        for name in self.characteristics:
            if name in population_template.sampled_characteristics:
                extracted_characteristics[name] = self.characteristics[name].extract(
                    quantity, population_template.sampled_characteristics[name]
                )
            else:
                extracted_characteristics[name] = self.characteristics[name].extract(quantity)

        extracted_collection = self.factory.generate_characteristic_collection_empty()
        for name, sampled_char in extracted_characteristics.items():
            extracted_collection._merge_characteristic(sampled_char)

        return extracted_collection

    def __str__(self):
        return "{" + ", ".join(str(bucket) for bucket in self.characteristics.values()) + "}"

    def __repr__(self):
        return self.__str__()



class PopulationTemplate():
    """
    Represents a set of characteristics a population can have. 
    This is used to filter population operations (extract, merge, change traceable characteristics, etc).

    The filter sets a key for each possible blob property value. For selected properties, blob operations 
    operate only on the population matching the filter. For properties left open, blob operations select 
    population uniformly.

    Attributes:
        blob_id (int): A specific blob_id to match.
        mother_blob_id (int): A specific mother_blob_id to match.
        sampled_properties (dict): Filtered sampled property characteristics (key -> [values]).
        traceable_properties (dict): Filtered traceable property characteristics.
        empty (bool): Whether the template is empty (i.e., has no filters).

    """

    def __init__(self,  sampled_characteristics:dict[str,list[str]] = {}, traceable_characteristics:dict[str, Any]= {}):
        self.blob_id: int = None # type: ignore
        self.mother_blob_id: int = None # type: ignore
        self.sampled_characteristics: dict[str,list[str]] = {}
        self.traceable_characteristics: dict[str, Any] = {}
        self.empty: bool = True

        if sampled_characteristics:
            self.set_sampled_properties(sampled_characteristics)
        if traceable_characteristics:
            self.set_traceable_properties(traceable_characteristics)


    def set_mother_blob_id(self, value: int) -> None:
        """Set the mother_blob_id."""
        try:
            self.mother_blob_id = int(value)
        except ValueError:
            raise ValueError(f"Mother blob id must be a positive integer, is {type(value)}")

    def set_sampled_property(self, key: str, value: list[str]) -> None:
        """Set a single sampled property."""
        if not isinstance(key, str):
            raise ValueError(f"Key must be a string, is {type(key)}")
        if not isinstance(value, list):
            raise ValueError(f"Value must be a list, is {type(value)}")
        self.sampled_characteristics[key] = value
        self.empty = False

    def set_traceable_property(self, key: str, value: Any) -> None:
        """Set a single traceable property."""
        if not isinstance(key, str):
            raise ValueError(f"Key must be a string, is {type(key)}")
        self.traceable_characteristics[key] = value
        self.empty = False

    def set_sampled_properties(self, properties: dict[str,list[str]]) -> None:
        """Set multiple sampled properties."""
        for key, value in properties.items():
            self.set_sampled_property(key, value)

    def set_traceable_properties(self, properties: dict[str, Any]) -> None:
        """Set multiple traceable properties."""
        for key, value in properties.items():
            self.set_traceable_property(key, value)

    def is_empty(self) -> bool:
        """Check if the template is empty."""
        return self.empty and self.mother_blob_id is None

    def has_traceable_properties(self):
        return not self.empty and bool(self.traceable_characteristics)
    
    def has_sampled_properties(self):
        return not self.empty and bool(self.sampled_characteristics)

    def compare(self, other:PopulationTemplate) -> bool:
        return (self.blob_id == other.blob_id and
                self.mother_blob_id == other.mother_blob_id and
                self.sampled_characteristics.items() == other.sampled_characteristics.items() and
                self.traceable_characteristics.items() == other.traceable_characteristics.items())


    def __str__(self):
        blob_id = "\"\"" if self.blob_id is None else self.blob_id
        mother_blob_id = "\"\"" if self.mother_blob_id is None else self.mother_blob_id
        return '{{"blob_id" : {0}, "mother_blob_id" : {1}, "pairs"  : {2}, "traceable_prop"  : {3}}}'.format(
            blob_id, mother_blob_id, self.sampled_characteristics, self.traceable_characteristics)

   
    def __repr__(self):
        blob_id = "\"\"" if self.blob_id is None else self.blob_id
        mother_blob_id = "\"\"" if self.mother_blob_id is None else self.mother_blob_id
        return '{{"blob_id" : {0}, "mother_blob_id" : {1}, "pairs"  : {2}, "traceable_prop"  : {3}}}'.format(
            blob_id, mother_blob_id, self.sampled_characteristics, self.traceable_characteristics)
    
   

class BlobFactory():
    """
    A factory for creating Blob objects based on predefined characteristics templates.

    Attributes:
        characteristics_factory (CharacteristicsFactory): The factory that provides characteristic templates for blobs.
    """
    def __init__(self, factory: CharacteristicsFactory):
        self.characteristics_factory: CharacteristicsFactory = factory

    def _traceable_characteristics_override(self, traceable_prop_override: dict[str, Any]):
        if not isinstance(traceable_prop_override, dict):
            raise ValueError("Invalid traceable property override. Must be a dictionary.")
        traceable_characteristics = self.characteristics_factory.traceable_characteristics.copy()
        traceable_characteristics.update(traceable_prop_override)
        return traceable_characteristics

    def generate_blob_rand(self, mother_blob_id: int, node_of_origin: int, population: int, traceable_prop_override: dict[str, Any] = {}):
        if population <= 0:
            raise ValueError("Invalid population size.")

        collection = self.characteristics_factory.generate_characteristic_collection_rand(population)
        traceable = self._traceable_characteristics_override(traceable_prop_override)
        
        blob = Blob(mother_blob_id, node_of_origin, 0, self)
        blob.initialize_characteristics(collection, traceable)
        return blob

    def generate_blob_empty(self, mother_blob_id, node_of_origin, traceable_prop_override:dict = {}):
        collection = self.characteristics_factory.generate_characteristic_collection_empty()
        traceable = self._traceable_characteristics_override(traceable_prop_override)
        blob = Blob(mother_blob_id, node_of_origin, 0, self)
        blob.initialize_characteristics(collection, traceable)
        return blob

    def generate_blob_with_profile(self,mother_blob_id, node_of_origin, population, profile, traceable_prop_override:dict = {}):
        if population <= 0:
            raise ValueError("Invalid population size.")
        
        collection = self.characteristics_factory.generate_characteristic_collection_with_profile(population, profile)
        traceable = self._traceable_characteristics_override(traceable_prop_override)
        blob = Blob(mother_blob_id, node_of_origin, 0, self)
        blob.initialize_characteristics(collection, traceable)
        return blob

class Blob():
    """Blobs represent a part of a population.
    
    Blobs are described by histograms of distribution for each characteristic.
    
    Each histogram is guaranteed to total the entire population in the blob. That is,
    each 'person' in the blob has a value for each characteristic.

    The characteristic values are not tied to each individual person, however. Being just a 
    statistical descriptor of the modeled population.

    Blobs also have properties which is trackable over time, defined by treaceable properties.

    Blobs contain a mother_blob_id which describes their population's original blob id, as well as origin region.


    Attributes:
        blob_template: The BlobTemplate used to generate this blob.
        original_population: Original population size.
        blob_id: Unique blob identifier.
        mother_blob_id: Original blob identifier, also denotes region of origin.
        sampled_properties: The PropertyBlock for this blob. Each key denotes a sampled characteristic.
        spawning_node: The node were this blob was created.
        frame_origin_node: The node where this blob started the frame.
    """
    events = Events()
    
    def __init__(self, _mother_blob_id, _node_of_origin, _population, _blob_factory:BlobFactory):
        self.blob_factory:BlobFactory = _blob_factory
        self.profiles = None
        self.original_population = _population
        self.blob_id = IDGen('blobs').get_id()
        self.mother_blob_id = _mother_blob_id
        self.node_of_origin: int = _node_of_origin
        self._traceable_properties:dict = {}
        self.sampled_properties:SampledCharacteristicCollection = None
        self.frame_origin_node = None
        self.previous_node = _node_of_origin
        
    def initialize_characteristics(self, sampled_characteristics:SampledCharacteristicCollection, traceable_characteristics:dict):
        self.sampled_properties = sampled_characteristics
        self._traceable_properties = traceable_characteristics
              
    def initialize_blocks(self, block_template:CharacteristicsFactory, population):
        self.sampled_properties = block_template.generate_characteristic_collection_rand(population)
        self._traceable_properties = copy.deepcopy(block_template.traceable_characteristics)

    def initialize_blocks_empty(self, block_template:CharacteristicsFactory):
        self.sampled_properties = block_template.generate_characteristic_collection_empty()
        self._traceable_properties = copy.deepcopy(block_template.traceable_characteristics)

    def initialize_blocks_profile(self, block_template:CharacteristicsFactory, population, profiles):
        self.profiles = profiles
        self.sampled_properties = block_template.generate_characteristic_collection_with_profile(population, profiles)
        self._traceable_properties = copy.deepcopy(block_template.traceable_characteristics)
        
    def set_traceable_property(self, key, value):
        prev_val = None
        if prev_val in self._traceable_properties:
            prev_val = self._traceable_properties[key]
            
        if prev_val == value:
            return
        self._traceable_properties[key] = value
        Blob.events.on_traceable_property_changed(self, key, prev_val, value)

    def get_traceable_property(self, key):
        return self._traceable_properties[key]

    def get_traceable_properties(self):
        return self._traceable_properties
        
    # used for infection for example
    # def move_profile(self, quantity, pop_template, origin_block, target_block):
    #     """Moves population from one PropertyBlock to another.
        
    #     This handles situations like infection (or another characteristic) tracking.

    #     For example, moving 1 population from 'healthy' to 'infected' blocks models infection of one population,
    #     and stores the profile of characteristics of infected population. 

    #     Params:
    #         quantity: Population quantity to be moved.
    #         pop_template: The PopTemplate filter to be matched.
    #         origin_block: origin block key.
    #         target_block: target block key.
    #     """
    #     extracted = self.blocks[origin_block].extract(quantity, pop_template)
    #     self.blocks[target_block].add_block(extracted)
        
    def split_blob(self, quantity, pop_template: PopulationTemplate = None):
        """Separates a blob into another blob. This is filtered by both PopTemplate and PropertyBlocks.
        
        Params:
            quantity: Population quantity to be separated into a new Blob.
            pop_template: The PopTemplate filter to be matched.

        Returns:
            A new blob containing the extracted population
        """
        total_available_population = self.get_population_size(pop_template)
        current_quantity = min(total_available_population, quantity)
        if current_quantity == 0:
            return None

        new_blob = self.blob_factory.generate_blob_empty(self.mother_blob_id, self.node_of_origin)
        
        if pop_template is not None:
            if pop_template.mother_blob_id is not None and pop_template.mother_blob_id != self.mother_blob_id:
                return new_blob

        
        removed_block = self.sampled_properties.extract(current_quantity, pop_template)
        new_blob.sampled_properties = removed_block
        
        for k,v in self.get_traceable_properties().items():
            new_blob._traceable_properties[k] = v
        # new_blob.spawning_node = self.spawning_node
        # new_blob.previous_node = self.previous_node
        new_blob.frame_origin_node = self.frame_origin_node
        return new_blob
    
    def change_blob_traceable_property(self, key, value, quantity: int, template : PopulationTemplate = None) -> Blob:
        
        _blob = self.grab_population(quantity, template)
        if not isinstance(_blob, Blob):
            return
        _blob.set_traceable_property(key, value)
        
        if _blob is not self:
            _blob.previous_node = self.previous_node
            _blob.frame_origin_node = self.frame_origin_node
        return _blob
    
    def grab_population(self, quantity, population_template = None)->Blob:
        """Grabs a population from this Blob.
        
        Returns either a new Blob, or the own blob, if it matches the entire population.

        Params:
            quantity: The population quantity to be grabbed.
            population_template: the population template to be matched.

        Returns:
            This Blob, if the population_template matches the entire population.    
            Otherwise, returns a new Blob, with a matched population inside.
        """
        matching_template_total_population = self.get_population_size(population_template) ==  self.get_population_size()
        if quantity >= self.get_population_size(population_template) and matching_template_total_population:
            return self
        else:
            return self.split_blob(quantity, population_template)

    def get_population_size(self, population_template:PopulationTemplate = None)->int:
        """Gets the population size matching a PopTemplate.

        If population_template is None, gets total population size.
        """

        # No template defined - returns entire population
        if population_template is None:
            return self.sampled_properties.get_population_size()

        # A template was defined, but without any traceable or sampled properties - returns entire population
        if population_template.is_empty():
            return self.sampled_properties.get_population_size()
        
        # Template defined with a mother_blob_id different than this blob - returns 0
        if population_template is not None and population_template.mother_blob_id is not None:
            #print("testing mother blob", population_template.mother_blob_id , self.mother_blob_id)
            if population_template.mother_blob_id != self.mother_blob_id:
                #print("Different")
                return 0
        
        # Compares the traceable properties defined in the Template to the ones in the Blob
        # Returns the population available according to the sampled properties
        if self.compare_traceable_properties_to_template(population_template):
            return self.sampled_properties.get_population_size(population_template)

        # If the traceable properties do not match - returns 0
        return 0

    def compare_traceable_properties_to_template(self, population_template:PopulationTemplate):
        
        # If PopTemplate does not have traceable properties defined
        if not population_template.has_traceable_properties():
            return True
    
        # Compares traceable properties set in the PopTemplate
        # The PopTemplate may have fewer properties than the Blob
        for k,v in population_template.traceable_characteristics.items():
            if k not in self.get_traceable_properties().keys():
                sys.exit(f"The traceable property \"{k}\" was not defined in this Blob. Set a default value using the \"EnviromentGraph.add_blobs_traceable_property()\" function, or setting it in a BlockTemplate of a BlockFactory. {self.verbose_str()}")
            if callable(v):
                if not v(self.get_traceable_property(k)):
                    return False
            elif isinstance(v,(list,set)):
                if self.get_traceable_property(k) not in v:
                    return False
            elif self.get_traceable_property(k) != v:
                return False
            
        # All defined properties matched
        return True

    def compare_traceable_properties_to_other(self, other_blob: Blob, check_missing_keys = True):
        if check_missing_keys:
            for k in self.get_traceable_properties().keys():
                if k not in other_blob.get_traceable_properties().keys():
                    sys.exit(f"The traceable property \"{k}\" was not defined in other Blob. {other_blob.verbose_str()}")
            for k in other_blob.get_traceable_properties().keys():
                if k not in self.get_traceable_properties().keys():
                    sys.exit(f"The traceable property \"{k}\" was not defined in this Blob. {self.verbose_str()}")

        return self.get_traceable_properties() == other_blob.get_traceable_properties()

    # merges a child blob into a mother blob
    # Outside code is responsible for deleting consumed blob
    def consume_blob(self, blob: Blob):
        """Consumes the population of another blob.
        
        IMPORTANT: The exclusion of the consumed blob from the simulation is responsability of the caller of this function.

        Params:
            blob: Another blob to be consumed.
        """
        if not isinstance(blob, Blob):
            return
        if self.compare_traceable_properties_to_other(blob):
            self.sampled_properties.merge_characteristic_collection(blob.sampled_properties)
            
    def verbose_str(self):
        return "{0} {1} {2}".format(self, self.get_traceable_properties(), self.sampled_properties)

    def __str__(self):
        template_string = '{{\"id\" : {0}, \"mother_id\" : {1}, \"population\" :  {2}, \"previous_node\" : {3}, \"frame_origin_node\" : {4}}}'
        return template_string.format(self.blob_id, self.mother_blob_id, self.get_population_size(), self.previous_node, self.frame_origin_node)

    def __repr__(self):
        template_string = '{{\"id\" : {0}, \"mother_id\" : {1}, \"population\" :  {2}, \"previous_node\" : {3}, \"frame_origin_node\" : {4}}}'
        return template_string.format(self.blob_id, self.mother_blob_id, self.get_population_size(), self.previous_node, self.frame_origin_node)




# EXAMPLES 
if __name__ == "__main__":

    FixedRandom()

    dummyBlockTemplate = CharacteristicsFactory()
    dummyBlockTemplate.add_sampled_characteristic('age', ('child', 'adult', 'ancient'))
    dummyBlockTemplate.add_sampled_characteristic('economic_profile', ('unemployed', 'worker'))
    dummyBlockTemplate.add_sampled_characteristic('social_profile', ('low', 'mid', 'high'))
    #dummyBlockTemplate.add_bucket('risk', ('low', 'mid', 'high'))
    #dummyBlockTemplate.add_bucket('height', ('short', 'average', 'tall'))
    dummyBlockTemplate.add_traceable_characteristic('vaccine_level', 0)
    dummyBlockTemplate.add_traceable_characteristic('sir_state', 'susceptible')
    dummyBlobFactory = BlobFactory(dummyBlockTemplate)
        
    print("\nCREATING BLOB 1")
    dummyBlob = dummyBlobFactory.generate_blob_rand(0, 0, 400)
    print("Dummy1", dummyBlob.get_population_size(), dummyBlob, dummyBlob.get_traceable_properties(), dummyBlob.sampled_properties)
    print("************")
    
    print(dummyBlob.sampled_properties, type(dummyBlob.sampled_properties.characteristics['age']))
    print(dummyBlob.sampled_properties.characteristics['age'].name, type(dummyBlob.sampled_properties.characteristics['age'].name))
    print("\nSPLIT BLOB 1 INTO BLOB 2 - MATCHING TREACEABLE_PROP")
    # sets a population template
    dummyPopTemplate = PopulationTemplate()
    dummyPopTemplate.set_sampled_property('age', ['child', 'adult', 'ancient'])
    # dummyPopTemplate.set_property('economic_profile', 'worker')
    # dummyPopTemplate.set_property('risk', 'high')
    # dummyPopTemplate.set_traceable_property('vaccine_level', 0)
    print("DummyPopTemplate", dummyPopTemplate)
    print("------------")
    # dummyBlob2 = dummyBlob.split_blob(40, dummyPopTemplate)
    # print("Dummy1", dummyBlob.get_population_size(), dummyBlob, dummyBlob.traceable_properties, dummyBlob.sampled_properties)
    # print("------------")
    # print("Dummy2", dummyBlob2.get_population_size(), dummyBlob2, dummyBlob2.traceable_properties, dummyBlob2.sampled_properties)
    # print("************")
    
    
    print("\nSPLIT BLOB 1 INTO BLOB 3 - NOT MATCHING TREACEABLE_PROP")
    dummyPopTemplate.set_traceable_property('vaccine_level', 1)
    dummyBlob3 = dummyBlob.split_blob(20, dummyPopTemplate)
    print("DummyPopTemplate", dummyPopTemplate)
    print("------------")
    print("Dummy1", dummyBlob.get_population_size(), dummyBlob, dummyBlob.get_traceable_properties(), dummyBlob.sampled_properties)
    print("------------")
    # print("Dummy2", dummyBlob2.get_population_size(), dummyBlob2, dummyBlob2.traceable_properties, dummyBlob2.sampled_properties)
    # print("------------")
    print("Dummy3", dummyBlob3)
    print("************")

    # print("\nFACTORY BLOB 4 - NOT MATCHING TREACEABLE_PROP")
    # dummyBlobFactory.block_template.add_traceable_property('vaccine_level', 1)
    # dummyBlob4 = dummyBlobFactory.Generate(0, 100)
    # print("Dummy1", dummyBlob.get_population_size(), dummyBlob.verbose_str())
    # print("------------")
    # print("Dummy2", dummyBlob2.get_population_size(), dummyBlob2.verbose_str())
    # print("------------")
    # print("Dummy3", dummyBlob3.get_population_size(), dummyBlob3.verbose_str())
    # print("************")
    # print("Dummy4", dummyBlob4.get_population_size(), dummyBlob4.verbose_str())
    # print("************")
    
    print("\nBLOB 1 CONSUMING BLOB 3 - NOT A MATCH")
    dummyBlob.consume_blob(dummyBlob3)
    print("DummyPopTemplate", dummyPopTemplate)
    print("------------")
    print("Dummy1", dummyBlob.get_population_size(), dummyBlob.verbose_str())
    print("------------")
    print("Dummy3", dummyBlob3)
    print("************")