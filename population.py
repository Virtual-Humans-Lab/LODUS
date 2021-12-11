#import random
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
        self.buckets = {}

    def add_bucket(self, property, values):
        self.buckets[property] = values

    def Generate(self, population):
        block = PropertyBlock(population)
        block.initialize_buckets(self)
        return block

    def GenerateProfile(self, population, pop_profile):
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

    def __init__(self, _characteristic):
        self.characteristic = _characteristic
        self.values = {}

    def get_population_size(self, key = None):
        """Returns the population size in this bucket. If key is not None, returns the population size of the matching value.
        
        Args:
            key: A possible value for the values map.

        Returns:
            Total population size if key is not set. Otherwise, returns the matching population quantity.
        """
        if key is None:
            return sum(self.values.values())
        else:
            return self.values[key]

    # bruteforcey
    def set_values_rand(self, keys, population = 0):
        """Initializes random values for a set of values and population quantity."""
        qtd_keys = len(keys)

        for key in keys:
            self.values[key] = 0

        for i in range(population):
            #self.values[keys[random.randint(0, qtd_keys-1)]] += 1
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
        aux_bucket = PropertyBucket(self.characteristic)
        values = []
        keys = list(self.values.keys())
        qtd_keys = len(keys)

        if quantity > self.get_population_size(key):
            quantity = self.get_population_size(key)
            
        if key is not None:
            for k in keys:
                if k == key:
                    values.append(quantity)
                else:
                    values.append(0)
        else:
            values = [0 for i in range(qtd_keys)]

            sample_list = []
            values = [0 for i in range(qtd_keys)]
            for i  in range(qtd_keys):
                sample_list.extend([i] * self.values[keys[i]])
            #samples = random.sample(sample_list, quantity)
            samples = FixedRandom.instance.sample(sample_list, quantity)
            for i  in range(qtd_keys):
                values[i] = samples.count(i)
            
            # TODO make this uniformly distributed according to population size
            # i = 0
            # while i < quantity:
            #     index = random.randint(0, qtd_keys-1)
            #     if values[index] < self.values[keys[index]]:
            #         values[index] += 1
            #         i+=1

        for i in range(qtd_keys):
            self.values[keys[i]] -= values[i]

        aux_bucket.set_values(keys, values)

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
        self.population = _population
        self.template = None
        self.buckets = {}
    
    def initialize_buckets(self, block_template):
        """Initializes buckets according to a BlockTemplate."""
        self.template = block_template
        template_buckets = self.template.buckets

        for key in template_buckets:
            bucket = PropertyBucket(key)
            bucket.set_values_rand(template_buckets[key], self.population)
            self.buckets[key] = bucket

    def initialize_buckets_profile(self, block_template, profile):
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

                values = {}

                for k in bucket_keys:
                    values[k] = 0

                for k in profile_keys:
                    values[k] = profile[key][k]

                non_profiled_keys = list(set(bucket_keys) - set(profile_keys))

                for i in range(self.population - total_profiled_population):
                    #rand_key = non_profiled_keys[random.randint(0, len(non_profiled_keys)-1)]
                    rand_key = non_profiled_keys[FixedRandom.instance.randint(0, len(non_profiled_keys)-1)]

                    values[rand_key] += 1


                bucket.set_values(list(values.keys()), list(values.values()))
                self.buckets[key] = bucket

    def add_block(self, block):
        """Adds the values of another PropertyBlock to this one."""
        for k in self.buckets.keys():
            self.buckets[k].add_bucket(block.buckets[k])

    def add_bucket(self, bucket):
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

        min_value = float("inf")

        template_keys = population_template.pairs.keys()

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

        buckets = {}
        for key in self.buckets.keys():
            if key in template_keys:
                bucket_prop = population_template.pairs[key]
                buckets[key] = self.buckets[key].extract(quantity, bucket_prop)
            else:
                buckets[key] = self.buckets[key].extract(quantity)

        aux = self.template.Generate(0)
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
        self.blocks = set()
        self.pairs = {}
        self.empty = True

        if string_values is not None:
            for k,v in string_values.items():
                self.set_property(k, v)


    def add_block(self, block):
        self.blocks.add(block)

    def set_property(self, key, value):
        self.pairs[key] = value
        self.empty = False

    def set_properties(self, pairs):
        for (key, value) in pairs:
            self.set_property(key, value)

    def is_empty(self):
        return self.empty

    def compare(self, other):
        if self.blob_id != other.blob_id:
            return False
        if self.mother_blob_id != other.mother_blob_id:
            return False
        if len(self.blocks.difference(other.blocks)) != 0:
            return False
        if self.pairs.items() != other.pairs.items():
            return False

        return True

    def __str__(self):
        blob_id = "\"\"" if self.blob_id is None else self.blob_id
        mother_blob_id = "\"\"" if self.mother_blob_id is None else self.mother_blob_id
        return '{{\"blob_id\" : {0}, \"mother_blob_id\" : {1}, \" pairs\"  : {2}}}'.format(blob_id,
                                                                                             mother_blob_id,
                                                                                             self.pairs)

    def __repr__(self):
        blob_id = "\"\"" if self.blob_id is None else self.blob_id
        mother_blob_id = "\"\"" if self.mother_blob_id is None else self.mother_blob_id
        return '{{\"blob_id\" : {0}, \"mother_blob_id\" : {1}, \" pairs\"  : {2}}}'.format(blob_id,
                                                                                             mother_blob_id,
                                                                                             self.pairs)



class BlobFactory():
    """A Blob factory. Used to create Blobs according to a pre-defined template.

    Use case:
        template = BlockTemplate()
        template.add_bucket('age', ('child', 'adult', 'ancient'))
        template.add_bucket('economic_profile', ('unemployed', 'worker'))
        template.add_bucket('social_profile', ('low', 'mid', 'high'))
        template.add_bucket('risk', ('low', 'mid', 'high'))
    
        types_of_blocks = ('healthy', 'infected', 'cured', 'dead')

        blobFactory = BlobFactory(types_of_blocks, template)

        blob = blobFactory.Generate(0, (100,100,100,100))
        blob2 = blobFactory.Generate(1, (100,0,0,0))


    Attributes:
        block_keys: A tuple of characteristic keys for blocks. Order matters.
        block_template: The BlockTemplate used by this factory.
    """
    def __init__(self, block_keys, block_template):
        self.block_keys = block_keys
        self.block_template = block_template
    
    def Generate(self, _mother_blob_id, _populations):
        """Generates a new Blob based on a pre-defined template.
        
        Params:
            _mother_blob_id: A mother_blob_id. ID uniqueness is responsability of the caller.
            _populations: A collection of ordered population quantities for block each block in block_keys.

        Returns:
            A new Blob with a block for each key in block_keys, each matching the template in block_template.
        """
        blob = Blob(_mother_blob_id, sum(_populations), self)
        blob.initialize_blocks(self.block_keys, self.block_template, _populations)
        return blob

    def GenerateProfile(self,_mother_blob_id, _populations, _profiles):
        """Generates a new Blob based on a pre-defined template, population quantities
            and population profile.

        Example of profile:
            pop_profile_1 = {\'bucket_1\' : {\'prop_1_1\' : 30, \'prop_1_2\' : 50},
                            \'bucket_2\' : {\'prop_2_1\' : 50, \'prop_2_2\' : 50}}
            defines values for two characteristics in bucket_1 and two characteristics in bucket_2
        
        Pre-Condition:
            Each population decripiton dictionary either maps the entire population of that block,
            or has at least one non-described PropertyBucket property to receive the remained population.

        Params:
            _mother_blob_id: A mother_blob_id. ID uniqueness is responsability of the caller.
            _populations: A collection of ordered population quantities for block each block in block_keys.
            _profiles : A collection containing an ordered population profile description dictionaries.

        Returns:
            A new Blob with a block for each key in block_keys, each matching the template in block_template.
            The new blob contains the desired number of people for profiled blocks.
        """
        blob = Blob(_mother_blob_id, sum(_populations), self)
        blob.initialize_blocks_profile(self.block_keys, self.block_template, _populations, _profiles)
        return blob

# tem blocks com dados de agentes com uma caracteristica similar
# block para saudaveis, block para infectados, block para mortos, block para 
class Blob():
    """Blobs represent a part of a population.
    
    Blobs are described by histograms of distribution for each characteristic.
    
    Each histogram is guaranteed to total the entire population in the blob. That is,
    each 'person' in the blob has a value for each characteristic.

    The characteristic values are not tied to each individual person, however. Being just a 
    statistical descriptor of the modeled population.

    Blobs also have a property which is trackable over time, defined by blocks of properties.


    Moving 1 population from the 'healthy' to the 'infected' block, tracks the kind of population who gets infected.
    For example, the histograms for 'healthy' and 'infected' are distributed with different rations given a simulation.


    Blobs contain a mother_blob_id which describes their population's original blob id, as well as origin region.


    Attributes:
        blob_template: The BlobTemplate used to generate this blob.
        original_population: Original population size.
        blob_id: Unique blob identifier.
        mother_blob_id: Original blob identifier, also denotes region of origin.
        blocks: The PropertyBlocks for this block. Each key denotes a trackable characteristic.
        spawning_node: The node were this blob was created.
        frame_origin_node: The node where this blob started the frame.
    """
    
    def __init__(self, _mother_blob_id, _population, _blob_factory):
        self.blob_factory = _blob_factory
        self.profiles = None
        self.original_population = _population
        self.blob_id = IDGen('blobs').get_id()
        self.mother_blob_id = _mother_blob_id
        self.blocks = {}
        self.spawning_node = None
        self.frame_origin_node = None
        self.previous_node = None

    def initialize_blocks(self, block_keys, block_template, populations):
        for i in range(len(block_keys)):
            self.blocks[block_keys[i]] = block_template.Generate(populations[i])

    def initialize_blocks_profile(self, block_keys, block_template, populations, profiles):
        self.profiles = profiles
        for i in range(len(block_keys)):
            self.blocks[block_keys[i]] = block_template.GenerateProfile(populations[i], profiles[i])
        

    # used for infection for example
    def move_profile(self, quantity, pop_template, origin_block, target_block):
        """Moves population from one PropertyBlock to another.
        
        This handles situations like infection (or another characteristic) tracking.

        For example, moving 1 population from 'healthy' to 'infected' blocks models infection of one population,
        and stores the profile of characteristics of infected population. 

        Params:
            quantity: Population quantity to be moved.
            pop_template: The PopTemplate filter to be matched.
            origin_block: origin block key.
            origin_block: target block key.
        """
        extracted = self.blocks[origin_block].extract(quantity, pop_template)
        self.blocks[target_block].add_block(extracted)
        
    def split_blob(self, block_keys, quantity, pop_template = None):
        """Separates a blob into another blob. This is filtered by both PopTemplate and PropertyBlocks.
        
        Params:
            quantity: Population quantity to be separated into a new Blob.
            pop_template: The PopTemplate filter to be matched.
            block_keys: the PropertyBlock keys to be used in the split.

        Returns:
            A new blob containing the extracted population
        """
        new_blob = self.blob_factory.Generate(self.mother_blob_id, (0,0,0,0))
        current_quantity = quantity

        if pop_template is not None and pop_template.mother_blob_id is not None:
            if pop_template.mother_blob_id != self.mother_blob_id:
                return new_blob

        len_block_keys = len(block_keys)
        quantities = [0 for x in range(len_block_keys)]

        # gets the available population size per block
        available_quantities = [self.blocks[block_keys[x]].get_population_size(pop_template) for x in range(len_block_keys)]
        total_available_population = sum(available_quantities)
        current_quantity = min(total_available_population, current_quantity)

        # update in python 3.9
        # samples = random.sample([x for x in block_keys], current_quantity, counts = available_quantities)

        sample_list = []

        for i  in range(len_block_keys):
            sample_list.extend([i] * available_quantities[i])

        #samples = random.sample(sample_list, current_quantity)
        samples = FixedRandom.instance.sample(sample_list, current_quantity)
        
        for i  in range(len_block_keys):
            quantities[i] = samples.count(i)

        for i in range(len_block_keys):
            k = list(block_keys)[i]
            removed_block = self.blocks[k].extract(quantities[i], pop_template)
            new_blob.blocks[k].add_block(removed_block)

        return new_blob
    
    ## TODO Correct for block keys
    def grab_population(self, quantity, population_template = None):
        """Grabs a population from this Blob.
        
        Returns either a new Blob, or the own blob, if it matches the entire population.

        TODO Currently ignores PropertyBlock selection.
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
            return self.split_blob(list(self.blocks.keys()), quantity, population_template)

    # TODO correct for blocks keys
    def get_population_size(self, population_template = None):
        """Gets the population size matching a PopTemplate.

        If population_template is None, gets total population size.
        """
        
        min_value = float("inf")

        if population_template is not None and population_template.mother_blob_id is not None:
            if population_template.mother_blob_id != self.mother_blob_id:
                return 0

        if population_template is None:
            pop = 0
            for block in self.blocks.values():
                pop += block.get_population_size()
            return pop

        if population_template.is_empty():
            pop = 0
            block_keys = []
            if len(population_template.blocks) == 0:
                block_keys = list(self.blocks.keys())
            else:
                block_keys = list(population_template.blocks)

            for block_key in block_keys:
                pop += self.blocks[block_key].get_population_size()
            return pop

        template_keys = population_template.pairs.keys()

        block_keys = []
        if len(population_template.blocks) == 0:
            block_keys = list(self.blocks.keys())
        else:
            block_keys = list(population_template.blocks)

        min_total_val = 0
        for key, val in population_template.pairs.items():
            min_block_val = 0

            for block_key in block_keys:
                min_block_val += self.blocks[block_key].get_population_size(population_template)

            min_value = min(min_value, min_block_val)

        return min_value

    # merges a child blob into a mother blob
    # Outside code is responsible for deleting consumed blob
    def consume_blob(self, blob):
        """Consumes the population of another blob.
        
        IMPORTANT: The exclusion of the consumed blob from the simulation is responsability of the caller of this function.

        Params:
            blob: Another blob to be consumed.
        """
        for block_key in self.blocks.keys():
            self.blocks[block_key].add_block(blob.blocks[block_key])

    def __str__(self):
        template_string = '{{\"id\" : {0}, \"mother_id\" : {1}, \"population\" :  {2}, \"origin_node\" : {3}, \"frame_origin_node\" : {4}, \"blocks\" : {5}}}'
        return template_string.format(self.blob_id, self.mother_blob_id, self.get_population_size(), self.spawning_node, self.frame_origin_node, str(self.blocks))

    def __repr__(self):
        template_string = '{{\"id\" : {0}, \"mother_id\" : {1}, \"population\" :  {2}, \"origin_node\" : {3}, \"frame_origin_node\" : {4}, \"blocks\" : {5}}}'
        return template_string.format(self.blob_id, self.mother_blob_id, self.get_population_size(), self.spawning_node, self.frame_origin_node, str(self.blocks))




# EXAMPLES 
if __name__ == "__main__":

    output_list = []


    dummyBlockTemplate = BlockTemplate()
    dummyBlockTemplate.add_bucket('age', ('child', 'adult', 'ancient'))
    dummyBlockTemplate.add_bucket('economic_profile', ('unemployed', 'worker'))
    dummyBlockTemplate.add_bucket('social_profile', ('low', 'mid', 'high'))
    dummyBlockTemplate.add_bucket('risk', ('low', 'mid', 'high'))
    dummyBlockTemplate.add_bucket('height', ('short', 'average', 'tall'))

    types_of_blocks = ('healthy', 'infected', 'cured', 'dead')

    dummyBlobFactory = BlobFactory(types_of_blocks, dummyBlockTemplate)

    # creates a blob of 400 healthy individuals with random age, economic profile and social profile
    # with mother id 0
    dummyBlob = dummyBlobFactory.Generate(0, (100,100,100,100))

    # sets a population template
    dummyPopTemplate = PopTemplate()
    dummyPopTemplate.set_property('age', 'ancient')
    dummyPopTemplate.set_property('economic_profile', 'worker')
    dummyPopTemplate.set_property('risk', 'high')

    output_list.append(str(dummyBlob).replace('\'', '\"'))

    # infects 10 people of that template
    dummyBlob.move_profile(10, dummyPopTemplate, 'healthy', 'infected')

    output_list.append(str(dummyBlob).replace('\'', '\"'))

    # selects some works to go work
    healthy_old_workers_blob = dummyBlob.split_blob(('healthy', 'cured'), 40, dummyPopTemplate)

    output_list.append(str(dummyBlob).replace('\'', '\"'))

    healthy_old_workers_blob2 = dummyBlob.split_blob(('healthy', 'cured'), 20, dummyPopTemplate)

    output_list.append(str(dummyBlob).replace('\'', '\"'))

    # merges blobs again
    dummyBlob.consume_blob(healthy_old_workers_blob2)
    # delete healthy_old_workers_blob2 from the simulation


    output_list.append(str(dummyBlob).replace('\'', '\"'))
    output_list.append(str(healthy_old_workers_blob).replace('\'', '\"'))
    output_list.append(str(healthy_old_workers_blob2).replace('\'', '\"'))

    print(output_list)