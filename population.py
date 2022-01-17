#import random
from __future__ import annotations
import copy
import sys
from util import *
from random_inst import FixedRandom

class BlockTemplate():
    """Defines a template for a population PropertyBlock
    
    Use case:
        dummy = BlockTemplate()
        dummy.add_bucket('age', ('child', 'adult', 'ancient'))
        dummy.add_bucket('economic_profile', ('unemployed', 'worker'))
        dummy.add_bucket('social_profile', ('low', 'mid', 'high'))
        dummy.add_bucket('risk', ('low', 'mid', 'high'))
    
    """
    
    def __init__(self):
        self.buckets:dict = {}
        self.default_traceable_properties:dict = {}

    def add_bucket(self, property: str, values: list):
        self.buckets[property] = values
        
    def add_traceable_property(self, key: str, value):
        self.default_traceable_properties[key] = value

    def Generate(self, population: int):
        if not bool(self.buckets):
            return None
        if population <= 0:
            return None
        block = PropertyBlock(population)
        block.initialize_buckets(self)
        return block
    
    def GenerateEmpty(self):
        if not bool(self.buckets):
            return None
        block = PropertyBlock(0)
        block.initialize_buckets(self)
        return block

    def GenerateProfile(self, population: int, pop_profile: dict):
        if not bool(self.buckets):
            return None
        if population <= 0:
            return None
        block = PropertyBlock(population)
        block.initialize_buckets_profile(self, pop_profile)
        return block
    

class PropertyBucket():
    """"A property bucket models a single characteristic of a population.
    
        A characteristic is a histogram of population for each possible value (or range in case of continuous properties) of that characteristic.
        The bucket stores a map of value -> population quantity for each possible value.

        Each key for the stored dictionary represents a possible value for the tracked characteristic.


        For example:
            In  a population of 100 people:
            {'child' : 20, 'adult':60, 'elder':20}
            would be a mapping of the 'age' characteristic.

        The mapping is defined during modelling time.

        Attributes:
            characteristic: The represented characteristic
            values: The mapping for characteristic-value to population quantity
    """

    def __init__(self, _characteristic: str):
        self.characteristic:str = _characteristic
        self.values: dict[str,int] = {}

    def get_population_size(self, key:str = None):
        """Returns the population size in this bucket. If key is not None, returns the population size of the matching value.
        
        Args:
            key: A possible value for the values map.

        Returns:
            Total population size if key is not set. Otherwise, returns the matching population quantity.
        """
        if key is None:
            return sum(self.values.values())
        if isinstance(key, str):
            return self.values[key]
        if isinstance(key, list):
            if len(key) == 0: return sum(self.values.values())
            else: return sum([self.values[k] for k in set(key)])
        if isinstance(key, set):
            if len(key) == 0: return sum(self.values.values())
            else: return sum([self.values[k] for k in key])
        # if isinstance(key, list):
        #     return sum([self.values[k] for k in set(key)])
        # if isinstance(key, set):
        #     return sum([self.values[k] for k in key])
    
    # bruteforcey
    def set_values_rand(self, keys, population = 0):
        """Initializes random values for a set of values and population quantity."""
        qtd_keys = len(keys)

        for key in keys:
            self.values[key] = 0

        for i in range(population):
            self.values[keys[FixedRandom.instance.randint(0, qtd_keys-1)]] += 1

    def set_values(self, keys, populations):
        for i in range(len(keys)):
            self.values[keys[i]] = populations[i]

    def add_bucket(self, bucket):
        """Adds the values of another bucket to this one.
        
        If characteristics are not equal, this method does not do anything.
        """
        if self.characteristic == bucket.characteristic:
            for k in set(self.values):
                self.values[k] = self.values[k] + bucket.values[k]

    def extract(self, quantity, key = None):
        """Extracts a population quantity from this bucket and returns the extracted population in an auxiliary PropertyBucket.
        
        If key is set, quantity is removed exclusively from the key value.
        Otherwise, population is removed randomly.
        Extracted peopulation is uniformly distributed according to the population size for each characteristic.

        
        If quantity for a given key is larger than available population,
        the entire population for that key is returned.

        Params:
            quantity: the population quantity to be removed from this bucket.
            key: The desired value to be extracted. If None, extracts population randomly.
        
        Returns:
            An auxiliary PropertyBucket containing the extracted population, with same characteristic and keys.
        """
        # if key is a set, convert it to a list
        if isinstance(key, set):
            key = list(key)
        # if key is a list with only one entry, convert it to a string
        if isinstance(key, list) and len(key) == 1:
            key = key[0]
        # if key is a list with only no entry, set it to None
        if isinstance(key, list) and len(key) == 0:
            key = None

        aux_bucket = PropertyBucket(self.characteristic)
        values = []
        bucket_keys = list(self.values.keys())
        qtd_keys = len(bucket_keys)

        if quantity > self.get_population_size(key):
            quantity = self.get_population_size(key)
        
        if quantity == 0:
            values = [0 for i in range(qtd_keys)]
            aux_bucket.set_values(bucket_keys, values)
            return aux_bucket

        if key is None:
            sample_list = []
            values = [0 for i in range(qtd_keys)]
            for i  in range(qtd_keys):
                sample_list.extend([i] * self.values[bucket_keys[i]])
            samples = FixedRandom.instance.sample(sample_list, quantity)
            for i  in range(qtd_keys):
                values[i] = samples.count(i)
        # key is not None
        else:
            if isinstance(key, str):
                for k in bucket_keys:
                    if k == key:
                        values.append(quantity)
                    else:
                        values.append(0)
            elif isinstance(key, list):
                # TODO test the ratio_to_int distribution in Util.py
                values = [0 for i in range(qtd_keys)]
                sample_list = []
                for i in range(qtd_keys):
                    if bucket_keys[i] in key:
                        sample_list.extend([i] * self.values[bucket_keys[i]])
                samples = FixedRandom.instance.sample(sample_list, quantity)
                for i  in range(qtd_keys):
                    values[i] = samples.count(i)
            else:
                sys.exit("Key \"{key}\" requested for a property bucket is not a str nor a list. {self}")

        for i in range(qtd_keys):
            self.values[bucket_keys[i]] -= values[i]

        aux_bucket.set_values(bucket_keys, values)
        return aux_bucket

    def __str__(self):
        s = '\"{0}\" : {1}'.format(self.characteristic, self.values)
        return s

    def __repr__(self):
        s = '\"{0}\" : {1}'.format(self.characteristic, self.values)
        return s
        

# describes a block of blob parameters
class PropertyBlock():
    """A block of characteristics, represents a population with a traceable property.
    
    Maps a traceable property, for example, history of infectious disease, to a set of PropertyBuckets.
    This traceable characteristic, however, is external to a PropertyBlock.

    Attributes:
        population: initial population for the block
        template: BlockTemplate this block uses
        buckets: the PropertyBuckets this block uses. Mapped as block characteristic -> PropertyBucket

    """
    def __init__(self, _population):
        self.population: int = _population
        self.template: BlockTemplate = None
        self.buckets: dict[str,PropertyBucket] = {}
        
    def get_mapping_of_property_values(self):
        return [ list(v.values.values()) for v in self.buckets.values()]
    
    def initialize_buckets(self, block_template):
        """Initializes buckets according to a BlockTemplate."""
        self.template = block_template
        template_buckets = self.template.buckets

        for key in template_buckets:
            bucket = PropertyBucket(key)
            bucket.set_values_rand(template_buckets[key], self.population)
            self.buckets[key] = bucket

    def initialize_buckets_profile(self, block_template: BlockTemplate, profile: dict):
        """Initializes buckets according to a BlockTemplate and population description.
        
        Profile is a dictionary with any number of bucket characteristics as keys, and
        each value is a dictionary (property -> population quantity) pairs.

        If a characteristic is in the profile, the respective buckets are initialized
        according to:
            if property is associated with a quantity, that quantity is used.
            if property is not associated with a quantity, its initialized randomly.
        
        The generated buckets respect the self.population value.

        Use case:
            block_temp = BlockTemplate()
            block_temp.add_bucket('bucket_1', ('prop_1_1', 'prop_1_2', 'prop_1_3'))
            block_temp.add_bucket('bucket_2', ('prop_2_1', 'prop_2_2'))
            block_temp.add_bucket('bucket_3', ('prop_3_1', 'prop_3_2', 'prop_3_3'))
            block_temp.add_bucket('bucket_4', ('prop_4_1', 'prop_4_2'))

            pop_profile = {'bucket_1' : {'prop_1_1' : 30, 'prop_1_2' : 50},
                           'bucket_3' : {'prop_3_1' : 30}}

            block = block_template.initialize_buckets_profile(block_template, pop_profile)


        TODO review this.        
        """
        self.template = block_template
        template_buckets = self.template.buckets
                
        for key in template_buckets:
            if key not in profile:
                bucket = PropertyBucket(key)
                bucket.set_values_rand(template_buckets[key], self.population)
                self.buckets[key] = bucket
            else:
                bucket = PropertyBucket(key)
                bucket_keys = block_template.buckets[key]
                profile_values = profile[key].values()
                profile_keys = profile[key].keys()
                total_profiled_population = sum(profile_values)
                non_profiled_keys = list(set(bucket_keys) - set(profile_keys))
                
                
                for k in profile_keys:
                    if k not in bucket_keys:
                        sys.exit(f"Error occured in PropertyBlock.initialize_buckets_profile(): The key \'{k}\' defined in a population profile is not a possible value for this PropertyBucket. Available keys: {bucket_keys}. Verify the BlockTemplate and its buckets before trying to assign population values do a PropertyBlock")
                
                
                values = {}
                for k in bucket_keys:
                    values[k] = 0
                        
                if total_profiled_population > self.population:
                    weights = [profile[key][x]/total_profiled_population for x in profile_keys]
                    int_distribution = distribute_ints_from_weights(self.population,weights)
                    for index, value in enumerate(profile_keys):
                        values[value] = int_distribution[index]
                else:
                    for k in profile_keys:
                        values[k] = profile[key][k]
                    
                    if len(non_profiled_keys) == 0:
                        for i in range(self.population - total_profiled_population):
                            rand_key = bucket_keys[FixedRandom.instance.randint(0, len(bucket_keys)-1)]

                            values[rand_key] += 1
                    else:
                        for i in range(self.population - total_profiled_population):
                            rand_key = non_profiled_keys[FixedRandom.instance.randint(0, len(non_profiled_keys)-1)]
                            values[rand_key] += 1

                bucket.set_values(list(values.keys()), list(values.values()))
                self.buckets[key] = bucket
             

    def add_block(self, block):
        """Adds the values of another PropertyBlock to this one."""
        for k in self.buckets.keys():
            self.buckets[k].add_bucket(block.buckets[k])

    def add_bucket(self, bucket: PropertyBucket):
        """Adds the values a PropertyBucket to the appropriate local PropertyBucket.
        
        Population balance between buckets is responsability of the caller.

        Does not guarantee block validity.
        """
        self.buckets[bucket.characteristic].add_bucket(bucket)

    def get_population_size(self, population_template = None):
        """Gets the population size matching a PopTemplate.
        
        If population_template is None, gets total population size.
        """
        if population_template is None or population_template.is_empty():
            ## inefficient? change to be less janky
            a_bucket = list(self.buckets.values())[0]
            return a_bucket.get_population_size()
        
        if not bool(population_template.pairs.keys()):
            a_bucket = list(self.buckets.values())[0]
            return a_bucket.get_population_size()
        
        min_value = sys.maxsize
        template_keys = population_template.pairs.keys()
        
        #print(population_template, template_keys)
        for key in self.buckets.keys():
            if key in template_keys:
                val = population_template.pairs[key]

                min_value = min(min_value, self.buckets[key].get_population_size(val))

        return min_value


    # generates an auxiliary propertyblock
    def extract(self, quantity, population_template):
        """Extracts a quantity of population from this PropertyBlock.
        
        
        For keys not in the PopulationTemplate, values and quantities are selected randomly.
        For keys in the PopulationTemplate, values respect those selections.

        If quantity is larger than avaiable population matching template, returns as much as possible.


        Returns:
            A PropertyBlock with the extracted population.
        
        """
        if population_template is None:
            population_template = PopTemplate()

        template_keys = population_template.pairs.keys()
        # corrects for a bucket limiting the quantity
        min_val = quantity
        for k, v in population_template.pairs.items():
            bucket_size = self.buckets[k].get_population_size(v)
            min_val = min(min_val, bucket_size)
        quantity = min_val
        
        if quantity <= 0:
            return None
        
        buckets = {}
        for key in self.buckets.keys():
            if key in template_keys:
                bucket_prop = population_template.pairs[key]
                buckets[key] = self.buckets[key].extract(quantity, bucket_prop)
            else:
                buckets[key] = self.buckets[key].extract(quantity)

        aux = self.template.GenerateEmpty()
        for k in buckets.keys():
            aux.add_bucket(buckets[k])

        return aux

    def __str__(self):
        s = '{'
        for k in self.buckets.keys():
            s += '{0},'.format(self.buckets[k])
        return s[:-1] + '}'

    def __repr__(self):
        s = '{'
        for k in self.buckets.keys():
            s += '{0},'.format(self.buckets[k])
        return s[:-1]+ '}'



class PopTemplate():
    """Represents a set of characteristics a population can have. This is used to filter population operations.
    
    This filter sets a key for each possible blob property value. For selected properties, Blob operations operate only of the population matching the filter.

    For properties left open, blob operations select population uniformly.

    TODO FIX DICT INSTANTIATION FOR POP TEMPLATES

    Attributes:
        blob_id: a specific blob_id to match. TODO Currently not implemented.
        mother_blob_id: a specific mother_blob_id to match. TODO Currently not implemented.
        pairs: A dict of the the filtered property characteristics. TODO change to property_key -> [values] Currently property_key -> value
        blocks: The filtered property characteristics.
    """

    def __init__(self,  string_values= None):
        self.blob_id = None
        self.mother_blob_id = None
        self.traceable_properties:dict = {}
        self.pairs = {}
        self.empty = True

        if string_values is not None:
            for k,v in string_values.items():
                self.set_sampled_property(k, v)

    def set_sampled_property(self, key, value):
        self.pairs[key] = value
        self.empty = False
        
    def set_traceable_property(self, key, value):
        self.traceable_properties[key] = value
        self.empty = False

    def set_sampled_properties(self, pairs):
        for (key, value) in pairs:
            self.set_sampled_property(key, value)

    def is_empty(self):
        return self.empty

    def has_traceable_properties(self):
        if self.empty:
            return False
        if self.traceable_properties is None:
            return False
        if not bool(self.traceable_properties):
            return False
        return True

    def compare(self, other):
        if self.blob_id != other.blob_id:
            return False
        if self.mother_blob_id != other.mother_blob_id:
            return False
        if self.pairs.items() != other.pairs.items():
            return False
        if self.traceable_properties.items() != other.traceable_properties.items():
            return False

        return True

    def __str__(self):
        blob_id = "\"\"" if self.blob_id is None else self.blob_id
        mother_blob_id = "\"\"" if self.mother_blob_id is None else self.mother_blob_id
        return '{{\"blob_id\" : {0}, \"mother_blob_id\" : {1}, \"pairs\"  : {2}, \"traceable prop\"  : {3}}}'.format(blob_id,
                                                                                             mother_blob_id,
                                                                                             self.pairs, self.traceable_properties)

    def __repr__(self):
        blob_id = "\"\"" if self.blob_id is None else self.blob_id
        mother_blob_id = "\"\"" if self.mother_blob_id is None else self.mother_blob_id
        return '{{\"blob_id\" : {0}, \"mother_blob_id\" : {1}, \"pairs\"  : {2}, \"traceable prop\"  : {3}}}'.format(blob_id,
                                                                                             mother_blob_id,
                                                                                             self.pairs, self.traceable_properties)



class BlobFactory():
    """A Blob factory. Used to create Blobs according to a pre-defined template.

    Use case:
        template = BlockTemplate()
        template.add_bucket('age', ('child', 'adult', 'ancient'))
        template.add_bucket('economic_profile', ('unemployed', 'worker'))
        template.add_bucket('social_profile', ('low', 'mid', 'high'))
        template.add_bucket('risk', ('low', 'mid', 'high'))
    
        blobFactory = BlobFactory(template)

        blob = blobFactory.Generate(0, 100)
        blob2 = blobFactory.Generate(1, 350)


    Attributes:
        block_template: The BlockTemplate used by this factory.
    """
    def __init__(self, block_template:BlockTemplate):
        self.block_template:BlockTemplate = block_template
    
    def Generate(self, _mother_blob_id, _population):
        """Generates a new Blob based on a pre-defined template.
        
        Params:
            _mother_blob_id: A mother_blob_id. ID uniqueness is responsability of the caller.
            _population: The population quantity for each sampled property/characteristic of the BlockTemplate.

        Returns:
            A new Blob with characteristics matching the template in block_template.
        """
        if not bool(self.block_template.buckets):
            return None
        if _population <= 0:
            return None
        blob = Blob(_mother_blob_id, _population, self)
        blob.initialize_blocks(self.block_template, _population)
        return blob

    def GenerateEmpty(self, _mother_blob_id):
        """Generates a new empty Blob based on a pre-defined template.
        
        Params:
            _mother_blob_id: A mother_blob_id. ID uniqueness is responsability of the caller.

        Returns:
            A new Blob with characteristics matching the template in block_template and population 0.
        """
        if not bool(self.block_template.buckets):
            return None
        blob = Blob(_mother_blob_id, 0, self)
        blob.initialize_blocks_empty(self.block_template, 0)
        return blob

    def GenerateProfile(self,_mother_blob_id, _population, _profile):
        """Generates a new Blob based on a pre-defined template, population quantity and population profile.

        Example of profile:
            pop_profile_1 = {\'characteristic_A\' : {\'value_A1\' : 30, \'value_A2\' : 50},
                            \'characteristic_B\' : {\'value_B1\' : 50, \'value_B2\' : 50}}
            defines two characteristics with two distinct values

        Params:
            _mother_blob_id: A mother_blob_id. ID uniqueness is responsability of the caller.
            _populations: A collection of ordered population quantities for block each block in block_keys.
            _profile : A collection containing an ordered population profile description dictionaries.

        Returns:
            A new Blob with characteristics matching the template in block_template.
            The new blob contains the desired number of people for profiled characteristics.
        """
        if not bool(self.block_template.buckets):
            return None
        if _population <= 0:
            return None
        blob = Blob(_mother_blob_id, _population, self)
        blob.initialize_blocks_profile(self.block_template, _population, _profile)
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
    
    def __init__(self, _mother_blob_id, _population, _blob_factory:BlobFactory):
        self.blob_factory:BlobFactory = _blob_factory
        self.profiles = None
        self.original_population = _population
        self.blob_id = IDGen('blobs').get_id()
        self.mother_blob_id = _mother_blob_id
        self.traceable_properties:dict = {}
        self.sampled_properties:PropertyBlock = None
        self.spawning_node = None
        self.frame_origin_node = None
        self.previous_node = None

    def initialize_blocks(self, block_template:BlockTemplate, population):
        self.sampled_properties = block_template.Generate(population)
        self.traceable_properties = copy.deepcopy(block_template.default_traceable_properties)

    def initialize_blocks_empty(self, block_template:BlockTemplate, population):
        self.sampled_properties = block_template.GenerateEmpty()
        self.traceable_properties = copy.deepcopy(block_template.default_traceable_properties)

    def initialize_blocks_profile(self, block_template:BlockTemplate, population, profiles):
        self.profiles = profiles
        self.sampled_properties = block_template.GenerateProfile(population, profiles)
        self.traceable_properties = copy.deepcopy(block_template.default_traceable_properties)
        

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
        
    def split_blob(self, quantity, pop_template: PopTemplate = None):
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

        new_blob = self.blob_factory.GenerateEmpty(self.mother_blob_id)
        
        if pop_template is not None:
            if pop_template.mother_blob_id is not None and pop_template.mother_blob_id != self.mother_blob_id:
                return new_blob

        
        removed_block = self.sampled_properties.extract(current_quantity, pop_template)
        new_blob.sampled_properties = removed_block
        return new_blob
    
    def grab_population(self, quantity, population_template = None):
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

    def get_population_size(self, population_template:PopTemplate = None):
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
            if population_template.mother_blob_id != self.mother_blob_id:
                return 0
        
        # Compares the traceable properties defined in the Template to the ones in the Blob
        # Returns the population available according to the sampled properties
        if self.compare_traceable_properties_to_template(population_template):
            return self.sampled_properties.get_population_size(population_template)

        # If the traceable properties do not match - returns 0
        return 0

    def compare_traceable_properties_to_template(self, population_template:PopTemplate):
        
        # If PopTemplate does not have traceable properties defined
        if not population_template.has_traceable_properties():
            return True

        # Compares traceable properties set in the PopTemplate
        # The PopTemplate may have fewer properties than the Blob
        for k,v in population_template.traceable_properties.items():
            if k not in self.traceable_properties.keys():
                sys.exit(f"The traceable property \"{k}\" was not defined in this Blob. Set a default value using the \"EnviromentGraph.add_blobs_traceable_property()\" function, or setting it in a BlockTemplate of a BlockFactory. {self.verbose_str()}")
            if isinstance(v,(list,set)):
                return self.traceable_properties[k] in v
            if self.traceable_properties[k] != v:
                return False

        # All defined properties matched
        return True

    def compare_traceable_properties_to_other(self, other_blob, check_missing_keys = True):
        if check_missing_keys:
            for k in self.traceable_properties.keys():
                if k not in other_blob.traceable_properties.keys():
                    sys.exit(f"The traceable property \"{k}\" was not defined in other Blob. {other_blob.verbose_str()}")
            for k in other_blob.traceable_properties.keys():
                if k not in self.traceable_properties.keys():
                    sys.exit(f"The traceable property \"{k}\" was not defined in this Blob. {self.verbose_str()}")

        return self.traceable_properties == other_blob.traceable_properties

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
            self.sampled_properties.add_block(blob.sampled_properties)

    def verbose_str(self):
        return "{0} {1} {2}".format(self, self.traceable_properties, self.sampled_properties)

    def __str__(self):
        template_string = '{{\"id\" : {0}, \"mother_id\" : {1}, \"population\" :  {2}, \"origin_node\" : {3}, \"frame_origin_node\" : {4}}}'
        return template_string.format(self.blob_id, self.mother_blob_id, self.get_population_size(), self.spawning_node, self.frame_origin_node)

    def __repr__(self):
        template_string = '{{\"id\" : {0}, \"mother_id\" : {1}, \"population\" :  {2}, \"origin_node\" : {3}, \"frame_origin_node\" : {4}}}'
        return template_string.format(self.blob_id, self.mother_blob_id, self.get_population_size(), self.spawning_node, self.frame_origin_node)




# EXAMPLES 
if __name__ == "__main__":

    FixedRandom()

    dummyBlockTemplate = BlockTemplate()
    dummyBlockTemplate.add_bucket('age', ('child', 'adult', 'ancient'))
    dummyBlockTemplate.add_bucket('economic_profile', ('unemployed', 'worker'))
    dummyBlockTemplate.add_bucket('social_profile', ('low', 'mid', 'high'))
    #dummyBlockTemplate.add_bucket('risk', ('low', 'mid', 'high'))
    #dummyBlockTemplate.add_bucket('height', ('short', 'average', 'tall'))
    dummyBlockTemplate.add_traceable_property('vaccine_level', 0)
    dummyBlockTemplate.add_traceable_property('sir_state', 'susceptible')
    dummyBlobFactory = BlobFactory(dummyBlockTemplate)
        
    print("\nCREATING BLOB 1")
    dummyBlob = dummyBlobFactory.Generate(0, 400)
    print("Dummy1", dummyBlob.get_population_size(), dummyBlob, dummyBlob.traceable_properties, dummyBlob.sampled_properties)
    print("************")
    
    print(dummyBlob.sampled_properties, type(dummyBlob.sampled_properties.buckets['age']))
    print(dummyBlob.sampled_properties.buckets['age'].characteristic, type(dummyBlob.sampled_properties.buckets['age'].characteristic))
    print("\nSPLIT BLOB 1 INTO BLOB 2 - MATCHING TREACEABLE_PROP")
    # sets a population template
    dummyPopTemplate = PopTemplate()
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
    print("Dummy1", dummyBlob.get_population_size(), dummyBlob, dummyBlob.traceable_properties, dummyBlob.sampled_properties)
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
    # print("Dummy2", dummyBlob2.get_population_size(), dummyBlob2.verbose_str())
    # print("------------")
    print("Dummy3", dummyBlob3)
    print("************")
    # print("Dummy4", dummyBlob4.get_population_size(), dummyBlob4.verbose_str())
    # print("************")
    
    # print("\nCONSUMING BLOB 2 - IS A MATCH - SHOULD DELETE BLOB 2 AFTER")
    # dummyBlob.consume_blob(dummyBlob2)
    # print("DummyPopTemplate", dummyPopTemplate)
    # print("------------")
    # print("Dummy1", dummyBlob.get_population_size(), dummyBlob.verbose_str())
    # print("------------")
    # print("Dummy2", dummyBlob2.get_population_size(), dummyBlob2.verbose_str())
    # print("------------")
    # print("Dummy3", dummyBlob3.get_population_size(), dummyBlob3.verbose_str())
    # print("************")
    # print("Dummy4", dummyBlob4.get_population_size(), dummyBlob4.verbose_str())
    # print("************")

    # print("\nBLOB 1 CONSUMING BLOB 4 AFTER CHANGE - IS A MATCH")
    # dummyBlob4.traceable_properties['vaccine_level'] = 0
    # dummyBlob.consume_blob(dummyBlob4)
    # print("DummyPopTemplate", dummyPopTemplate)
    # print("------------")
    # print("Dummy1", dummyBlob.get_population_size(), dummyBlob.verbose_str())
    # print("------------")
    # print("Dummy2", dummyBlob2.get_population_size(), dummyBlob2.verbose_str())
    # print("------------")
    # print("Dummy3", dummyBlob3.get_population_size(), dummyBlob3.verbose_str())
    # print("************")
    # print("Dummy4", dummyBlob4.get_population_size(), dummyBlob4.verbose_str())
    # print("************")