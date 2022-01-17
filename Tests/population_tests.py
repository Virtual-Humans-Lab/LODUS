import sys

from numpy import character
sys.path.append('../')
sys.path.append('../../')
from population import *
import environment
import unittest
import util


def verify_block_validity(block:PropertyBlock):
    """Verifies if every bucket in a block has the same population size.
    
        A Valid PropertyBlock has the same PropertyBucket.get_population_size
        for each characteristic,
        and its population size is greater or equal to 0.
        Every bucket contains only 0 or greater values.
    """
    bucket_sizes = set()
    for bucket in block.buckets.values():
        bucket_sizes.add(bucket.get_population_size())
    
    for bucket in block.buckets.values():
        for val in bucket.values.values():
            if val < 0:
                return False
    
    # there is only one value of bucket size
    return len(bucket_sizes) <= 1 and list(bucket_sizes)[0] >= 0

def verify_blob_validity(blob: Blob):
    """Verifies if all sampled properties of a blob have the same population for each of its buckets.
    
    A Blob is Valid if all of its PropertyBlock is Valid.
    """
    return verify_block_validity(blob.sampled_properties)


def verify_blobs_validity(blobs):
    """Verifies if all blobs in a list of blobs are Valid."""
    results = []
    for blob in blobs:
        results.append(verify_blob_validity(blob))
    return all(results)

class PopulationTests(unittest.TestCase):

    def setUp(self):
        FixedRandom()
        pass

    def tearDown(self):
        pass
    
    #### PropertyBucket tests
    ## PropertyBucket.add_bucket
    def test_property_bucket_add_bucket(self):
        """Tests PropertyBucket.add_bucket

        Case 1: 
            action : Creates 2 PropertyBuckets with the same characteristic. Add the second to the first one.
            result : Bucket1 should contain the sum of both populations.
                     
        Case 2: 
            action : Creates a thrid PropertyBucket with a different characteristic. Add the third to the first one.
            result : Operation does nothing and populations remain the same.
        """

        # Case 1:
        # Create a PropertyBucket with the 'characteristic_A', 3 different values, and population = 60 with random distribution
        aux_bucket1 = PropertyBucket('characteristic_A')
        aux_bucket1.set_values_rand(('char_A_value_1', 'char_A_value_2', 'char_A_value_3') , 60)

        # Create another PropertyBucket with the same characteristic and values, but population = 30
        aux_bucket2 = PropertyBucket('characteristic_A')
        aux_bucket2.set_values_rand(('char_A_value_1', 'char_A_value_2', 'char_A_value_3') , 30)

        # Test adding PropertyBuckets with the same characteristic 
        aux_bucket_size1 = aux_bucket1.get_population_size()
        aux_bucket_size2 = aux_bucket2.get_population_size()
        aux_bucket1.add_bucket(aux_bucket2)

        # Should be the sum of population_size in both aux buckets
        merge_size_test_1 = aux_bucket1.get_population_size()

        # assert if bucket was added correctly
        self.assertEqual(merge_size_test_1, aux_bucket_size1 + aux_bucket_size2,
                        'Add bucket not adding same property buckets correctly.')

        # Case 2:
        # Create a PropertyBucket with different characteristic and values
        # The values("ids/keys/str"), their quantity, and the population are irrelevant in this test due to the characteristic being different
        aux_bucket3 = PropertyBucket('characteristic_B')
        aux_bucket3.set_values_rand(('char_B_value_1', 'char_B_value_2') , 60)

        # Test adding PropertyBuckets with a different characteristic 
        aux_bucket1.add_bucket(aux_bucket3)

        # Should be the same value as 'merge_size_test_1'
        merge_size_test_2 = aux_bucket1.get_population_size()

        # assert whether bucket was skipped
        self.assertEqual(merge_size_test_2, aux_bucket_size1 + aux_bucket_size2,
                        'Add bucket adding different property buckets incorrectly.')
        
    ## PropertyBucket.extract - without key
    def test_property_bucket_extract_without_key(self):
        """ Tests PropertyBucket.extract

            Original size of bucket equals final size of bucket + extrected bucket size. 

            Case 1: 
                action : Extract less population than available
                result : Extracted bucket contains requested population quantity.
                         Original bucket has original population minus requested population.

            Case 2: 
                action : Extract Equal population as available.
                result : Extracted bucket contains requested population quantity.
                         Original bucket contains zero population.

            Case 3:
                action : Extract more population than available.
                result : Extracted bucket contains original bucket population.
                         Original bucket contains zero population.
        """

        # Case 1:
        # Create a PropertyBucket with 3 different values, each with 60 people (180 total)
        aux_bucket = PropertyBucket('characteristic_A')
        aux_bucket.set_values(('value_1', 'value_2', 'value_3') , (60,60,60))

        # Extracting 100 people
        original_bucket_size = aux_bucket.get_population_size()
        extracted_bucket = aux_bucket.extract(100)
        smaller_bucket_size = aux_bucket.get_population_size()
        extracted_bucket_size = extracted_bucket.get_population_size()

        # Comparing bucket sizes
        self.assertEqual(original_bucket_size, smaller_bucket_size + extracted_bucket_size,
                        'Case 1 buckets do not add up.')
        self.assertEqual(100, extracted_bucket_size,
                        'Case 1 extracted bucket is not the correct size.')
        self.assertEqual(smaller_bucket_size, original_bucket_size - extracted_bucket_size,
                        'Case 1 original bucket is not the corrected size.')

        # Case 2:
        # Create a PropertyBucket with 3 different values, each with 60 people (180 total)
        aux_bucket = PropertyBucket('characteristic_A')
        aux_bucket.set_values(('value_1', 'value_2', 'value_3') , (60,60,60))

        # Extracting 180 people - the exact amount available (could use the original_bucket_size)
        original_bucket_size = aux_bucket.get_population_size()
        extracted_bucket = aux_bucket.extract(180)
        smaller_bucket_size = aux_bucket.get_population_size()
        extracted_bucket_size = extracted_bucket.get_population_size()
        
        # Comparing bucket sizes
        self.assertEqual(original_bucket_size, smaller_bucket_size + extracted_bucket_size,
                        'Case 2 buckets do not add up.')
        self.assertEqual(original_bucket_size, extracted_bucket_size,
                        'Case 2 extracted bucket is not the total size.')
        self.assertEqual(smaller_bucket_size, 0,
                        'Case 2 original bucket is not the zero.')                

        # Case 3:
        # Create a PropertyBucket with 3 different values, each with 60 people (180 total)
        aux_bucket = PropertyBucket('characteristic_A')
        aux_bucket.set_values(('value_1', 'value_2', 'value_3') , (60,60,60))

        # Extracting 300 people - more than available
        original_bucket_size = aux_bucket.get_population_size()
        extracted_bucket = aux_bucket.extract(300)
        smaller_bucket_size = aux_bucket.get_population_size()
        extracted_bucket_size = extracted_bucket.get_population_size()
        
        # Comparing bucket sizes
        self.assertEqual(original_bucket_size, smaller_bucket_size + extracted_bucket_size,
                        'Case 3 buckets do not add up.')
        self.assertEqual(original_bucket_size, extracted_bucket_size,
                        'Case 3 extracted bucket is not the total size.')
        self.assertEqual(smaller_bucket_size, 0,
                        'Case 3 original bucket is not the zero.')

    ## PropertyBucket.extract - with key
    def test_property_bucket_extract_with_key(self):
        """ Tests PropertyBucket.extract

            Original size of bucket equals final size of bucket + extrected bucket size. 

            Case 1: 
                action : Extract less population than available matching key
                result : Extracted bucket contains requested population quantity.
                         Original bucket has original population minus requested population.

            Case 2: 
                action : Extract Equal population as available matching key.
                result : Extracted bucket contains requested population quantity.
                         Original bucket contains zero population.

            Case 3:
                action : Extract more population than available matching key. 
                result : Extracted bucket contains original bucket population.
                         Original bucket contains zero population.
        """

        # Case 1:
        # Create a PropertyBucket with 3 different values, each with 60 people (180 total)
        aux_bucket = PropertyBucket('characteristic_A')
        aux_bucket.set_values(('value_1', 'value_2', 'value_3') , (60,60,60))
        
        # Extracting 30 people from 'value_1'
        original_bucket_size = aux_bucket.get_population_size()
        original_value_count = aux_bucket.get_population_size(key='value_1')
        extracted_bucket = aux_bucket.extract(30, key='value_1')
        smaller_bucket_size = aux_bucket.get_population_size()
        smaller_value_count = aux_bucket.get_population_size(key='value_1')
        extracted_bucket_size = extracted_bucket.get_population_size()
        extracted_value_count = extracted_bucket.get_population_size(key='value_1')

        # Comparing bucket sizes
        self.assertEqual(original_bucket_size, smaller_bucket_size + extracted_bucket_size,
                        'Case 1 buckets do not add up.')
        self.assertEqual(30, extracted_bucket_size,
                        'Case 1 extracted bucket is not the correct size.')
        self.assertEqual(smaller_bucket_size, original_bucket_size - extracted_bucket_size,
                        'Case 1 original bucket is not the correct size.')
        
        # Comparing count of 'value_1'
        self.assertEqual(original_value_count, smaller_value_count + extracted_value_count,
                        'Case 1 property values do not add up.')
        self.assertEqual(30,  extracted_value_count,
                        'Case 1 extracted property is not the correct size.')
        self.assertEqual(smaller_value_count, original_value_count - extracted_value_count,
                        'Case 1 original property count is not the correct size.')
        # Case 2:
        # Create a PropertyBucket with 3 different values, each with 60 people (180 total)
        aux_bucket = PropertyBucket('characteristic_A')
        aux_bucket.set_values(('value_1', 'value_2', 'value_3') , (60,60,60))

        # Extracting 60 people from 'value_1' - the exact amount available
        original_bucket_size = aux_bucket.get_population_size()
        original_value_count = aux_bucket.get_population_size(key='value_1')
        extracted_bucket = aux_bucket.extract(60, key='value_1')
        smaller_bucket_size = aux_bucket.get_population_size()
        smaller_value_count = aux_bucket.get_population_size(key='value_1')
        extracted_bucket_size = extracted_bucket.get_population_size()
        extracted_value_count = extracted_bucket.get_population_size(key='value_1')
        
        # Comparing bucket sizes
        self.assertEqual(original_bucket_size, smaller_bucket_size + extracted_bucket_size,
                        'Case 2 buckets do not add up.')
        self.assertEqual(120, smaller_bucket_size,
                        'Case 2 original bucket is not the correct size.')  
        self.assertEqual(smaller_bucket_size, original_bucket_size - extracted_bucket_size,
                        'Case 2  original bucket is not the correct size.')

        # Comparing count of 'value_1'
        self.assertEqual(original_value_count, smaller_value_count + extracted_value_count,
                        'Case 2 property values do not add up.')
        self.assertEqual(60,  extracted_value_count,
                        'Case 2 extracted property is not the correct size.')
        self.assertEqual(smaller_value_count, original_value_count - extracted_value_count,
                        'Case 2 original property count is not the correct size.')

        # Case 3:
        # Create a PropertyBucket with 3 different values, each with 60 people (180 total)
        aux_bucket = PropertyBucket('characteristic_A')
        aux_bucket.set_values(('value_1', 'value_2', 'value_3') , (60,60,60))

        # Extracting 120 people from 'value_1' - more than available
        original_bucket_size = aux_bucket.get_population_size()
        original_value_count = aux_bucket.get_population_size(key='value_1')
        extracted_bucket = aux_bucket.extract(120, key='value_1')
        smaller_bucket_size = aux_bucket.get_population_size()
        smaller_value_count = aux_bucket.get_population_size(key='value_1')
        extracted_bucket_size = extracted_bucket.get_population_size()
        extracted_value_count = extracted_bucket.get_population_size(key='value_1')

        # Comparing bucket sizes
        self.assertEqual(original_bucket_size, smaller_bucket_size + extracted_bucket_size,
                        'Case 3 buckets do not add up.')
        self.assertEqual(120, smaller_bucket_size,
                        'Case 3 original bucket is not the correct size.')  
        self.assertEqual(smaller_bucket_size, original_bucket_size - extracted_bucket_size,
                        'Case 3  original bucket is not the correct size.')

        # Comparing count of 'value_1'
        self.assertEqual(original_value_count, smaller_value_count + extracted_value_count,
                        'Case 3 property values do not add up.')
        self.assertEqual(60,  extracted_value_count,
                        'Case 3 extracted property is not the correct size.')
        self.assertEqual(smaller_value_count, original_value_count - extracted_value_count,
                        'Case 3 original property count is not the correct size.')

    ## PropertyBucket.extract - with key list
    def test_property_bucket_extract_with_key_list(self):
        """ Tests PropertyBucket.extract

            Original size of bucket equals final size of bucket + extrected bucket size.

            Case 1: 
                action : Extract less population than available matching keys (as list)
                result : Extracted bucket contains requested population quantity.
                         Original bucket has original population minus requested population.

            Case 2: 
                action : Extract Equal population as available matching keys (as list).
                result : Extracted bucket contains requested population quantity.
                         Original bucket has original population minus requested population.
                         Original bucket contains zero population in the requested keys.

            Case 3:
                action : Extract more population than available matching keys (as list). 
                result : Extracted bucket contains original bucket population.
                         Original bucket has original population minus requested population.
                         Original bucket contains zero population in the requested keys.
        """
        # Tests different combinations of keys as lists
        test_keys_scenarios = [[],['value_1'], ['value_2'], ['value_3'], ['value_1', 'value_2'], ['value_1', 'value_3'], ['value_2', 'value_3'], ['value_1', 'value_2', 'value_3']]

        # Also tests combinations with repeated key entries. Multiple entries do not change behavior
        test_keys_scenarios.extend([['value_1', 'value_1'], ['value_1', 'value_1', 'value_2'], ['value_1', 'value_1', 'value_2', 'value_3'], ['value_1', 'value_1', 'value_2', 'value_1', 'value_3']])

        total_population = 180

        for key_list in test_keys_scenarios:

            # available population for this combination of keys (60 for each key)
            available_population = len(set(key_list)) * 60 
            
            # Case 1:
            # Create a PropertyBucket with 3 different values, each with 60 people (180 total)
            aux_bucket = PropertyBucket('characteristic_A')
            aux_bucket.set_values(('value_1', 'value_2', 'value_3') , (60,60,60))
            
            # Extracting half of the available population (30 for each key)
            original_bucket_size = aux_bucket.get_population_size()
            original_value_count = aux_bucket.get_population_size(key_list)
            extracted_bucket = aux_bucket.extract(available_population//2, key_list)
            smaller_bucket_size = aux_bucket.get_population_size()
            smaller_value_count = aux_bucket.get_population_size(key_list)
            extracted_bucket_size = extracted_bucket.get_population_size()
            extracted_value_count = extracted_bucket.get_population_size(key_list)

            # Comparing bucket sizes
            self.assertEqual(original_bucket_size, smaller_bucket_size + extracted_bucket_size,
                            'Case 1 buckets do not add up.')
            self.assertEqual(available_population//2, extracted_bucket_size,
                            'Case 1 extracted bucket is not the correct size.')
            self.assertEqual(smaller_bucket_size, original_bucket_size - extracted_bucket_size,
                            'Case 1 original bucket is not the correct size.')
            
            # Comparing count of values in key_list
            self.assertEqual(original_value_count, smaller_value_count + extracted_value_count,
                            'Case 1 property values do not add up.')
            self.assertEqual(available_population//2,  extracted_value_count,
                            'Case 1 extracted property is not the correct size.')
            self.assertEqual(smaller_value_count, original_value_count - extracted_value_count,
                            'Case 1 original property count is not the correct size.')
            
            # Case 2:
            # Create a PropertyBucket with 3 different values, each with 60 people (180 total)
            aux_bucket = PropertyBucket('characteristic_A')
            aux_bucket.set_values(('value_1', 'value_2', 'value_3') , (60,60,60))

            # Extracting the total available population (60 for each key)
            original_bucket_size = aux_bucket.get_population_size()
            original_value_count = aux_bucket.get_population_size(key_list)
            extracted_bucket = aux_bucket.extract(available_population, key_list)
            smaller_bucket_size = aux_bucket.get_population_size()
            smaller_value_count = aux_bucket.get_population_size(key_list)
            extracted_bucket_size = extracted_bucket.get_population_size()
            extracted_value_count = extracted_bucket.get_population_size(key_list)
            
            # Comparing bucket sizes
            self.assertEqual(original_bucket_size, smaller_bucket_size + extracted_bucket_size,
                            'Case 2 buckets do not add up.')
            self.assertEqual(total_population - available_population, smaller_bucket_size,
                            'Case 2 original bucket is not the correct size.')  
            self.assertEqual(smaller_bucket_size, original_bucket_size - extracted_bucket_size,
                            'Case 2  original bucket is not the correct size.')

            # Comparing count of values in key_list
            self.assertEqual(original_value_count, smaller_value_count + extracted_value_count,
                            'Case 2 property values do not add up.')
            self.assertEqual(available_population,  extracted_value_count,
                            'Case 2 extracted property is not the correct size.')
            self.assertEqual(smaller_value_count, original_value_count - extracted_value_count,
                            'Case 2 original property count is not the correct size.')

            # Case 3:
            # Create a PropertyBucket with 3 different values, each with 60 people (180 total)
            aux_bucket = PropertyBucket('characteristic_A')
            aux_bucket.set_values(('value_1', 'value_2', 'value_3') , (60,60,60))

            # Extracting more than the total available population (120 for each key)
            original_bucket_size = aux_bucket.get_population_size()
            original_value_count = aux_bucket.get_population_size(key_list)
            extracted_bucket = aux_bucket.extract(int(available_population*2), key_list)
            smaller_bucket_size = aux_bucket.get_population_size()
            smaller_value_count = aux_bucket.get_population_size(key_list)
            extracted_bucket_size = extracted_bucket.get_population_size()
            extracted_value_count = extracted_bucket.get_population_size(key_list)

            # Comparing bucket sizes
            self.assertEqual(original_bucket_size, smaller_bucket_size + extracted_bucket_size,
                            'Case 3 buckets do not add up.')
            self.assertEqual(total_population - available_population, smaller_bucket_size,
                            'Case 3 original bucket is not the correct size.')  
            self.assertEqual(smaller_bucket_size, original_bucket_size - extracted_bucket_size,
                            'Case 3  original bucket is not the correct size.')

            # Comparing count of values in key_list
            self.assertEqual(original_value_count, smaller_value_count + extracted_value_count,
                            'Case 3 property values do not add up.')
            self.assertEqual(available_population,  extracted_value_count,
                            'Case 3 extracted property is not the correct size.')
            self.assertEqual(smaller_value_count, original_value_count - extracted_value_count,
                            'Case 3 original property count is not the correct size.')

    ## PropertyBucket.extract - with key set
    def test_property_bucket_extract_with_key_set(self):
        """ Tests PropertyBucket.extract

            Original size of bucket equals final size of bucket + extrected bucket size.

            Case 1: 
                action : Extract less population than available matching keys (as set)
                result : Extracted bucket contains requested population quantity.
                         Original bucket has original population minus requested population.

            Case 2: 
                action : Extract Equal population as available matching keys (as set).
                result : Extracted bucket contains requested population quantity.
                         Original bucket has original population minus requested population.
                         Original bucket contains zero population in the requested keys.

            Case 3:
                action : Extract more population than available matching keys (as set). 
                result : Extracted bucket contains original bucket population.
                         Original bucket has original population minus requested population.
                         Original bucket contains zero population in the requested keys.
        """
        # Tests different combinations of keys as sets
        test_keys_scenarios = [(set()),{'value_1'}, {'value_2'}, {'value_3'}, {'value_1', 'value_2'}, {'value_1', 'value_3'}, {'value_2', 'value_3'}, {'value_1', 'value_2', 'value_3'}]

        total_population = 180

        for key_list in test_keys_scenarios:

            # available population for this combination of keys (60 for each key)
            available_population = len(key_list) * 60 
            
            # Case 1:
            # Create a PropertyBucket with 3 different values, each with 60 people (180 total)
            aux_bucket = PropertyBucket('characteristic_A')
            aux_bucket.set_values(('value_1', 'value_2', 'value_3') , (60,60,60))
            
            # Extracting half of the available population (30 for each key)
            original_bucket_size = aux_bucket.get_population_size()
            original_value_count = aux_bucket.get_population_size(key_list)
            extracted_bucket = aux_bucket.extract(available_population//2, key_list)
            smaller_bucket_size = aux_bucket.get_population_size()
            smaller_value_count = aux_bucket.get_population_size(key_list)
            extracted_bucket_size = extracted_bucket.get_population_size()
            extracted_value_count = extracted_bucket.get_population_size(key_list)

            # Comparing bucket sizes
            self.assertEqual(original_bucket_size, smaller_bucket_size + extracted_bucket_size,
                            'Case 1 buckets do not add up.')
            self.assertEqual(available_population//2, extracted_bucket_size,
                            'Case 1 extracted bucket is not the correct size.')
            self.assertEqual(smaller_bucket_size, original_bucket_size - extracted_bucket_size,
                            'Case 1 original bucket is not the correct size.')
            
            # Comparing count of values in key_list
            self.assertEqual(original_value_count, smaller_value_count + extracted_value_count,
                            'Case 1 property values do not add up.')
            self.assertEqual(available_population//2,  extracted_value_count,
                            'Case 1 extracted property is not the correct size.')
            self.assertEqual(smaller_value_count, original_value_count - extracted_value_count,
                            'Case 1 original property count is not the correct size.')
            
            # Case 2:
            # Create a PropertyBucket with 3 different values, each with 60 people (180 total)
            aux_bucket = PropertyBucket('characteristic_A')
            aux_bucket.set_values(('value_1', 'value_2', 'value_3') , (60,60,60))

            # Extracting the total available population (60 for each key)
            original_bucket_size = aux_bucket.get_population_size()
            original_value_count = aux_bucket.get_population_size(key_list)
            extracted_bucket = aux_bucket.extract(available_population, key_list)
            smaller_bucket_size = aux_bucket.get_population_size()
            smaller_value_count = aux_bucket.get_population_size(key_list)
            extracted_bucket_size = extracted_bucket.get_population_size()
            extracted_value_count = extracted_bucket.get_population_size(key_list)
            
            # Comparing bucket sizes
            self.assertEqual(original_bucket_size, smaller_bucket_size + extracted_bucket_size,
                            'Case 2 buckets do not add up.')
            self.assertEqual(total_population - available_population, smaller_bucket_size,
                            'Case 2 original bucket is not the correct size.')  
            self.assertEqual(smaller_bucket_size, original_bucket_size - extracted_bucket_size,
                            'Case 2  original bucket is not the correct size.')

            # Comparing count of values in key_list
            self.assertEqual(original_value_count, smaller_value_count + extracted_value_count,
                            'Case 2 property values do not add up.')
            self.assertEqual(available_population,  extracted_value_count,
                            'Case 2 extracted property is not the correct size.')
            self.assertEqual(smaller_value_count, original_value_count - extracted_value_count,
                            'Case 2 original property count is not the correct size.')

            # Case 3:
            # Create a PropertyBucket with 3 different values, each with 60 people (180 total)
            aux_bucket = PropertyBucket('characteristic_A')
            aux_bucket.set_values(('value_1', 'value_2', 'value_3') , (60,60,60))

            # Extracting more than the total available population (120 for each key)
            original_bucket_size = aux_bucket.get_population_size()
            original_value_count = aux_bucket.get_population_size(key_list)
            extracted_bucket = aux_bucket.extract(int(available_population*2), key_list)
            smaller_bucket_size = aux_bucket.get_population_size()
            smaller_value_count = aux_bucket.get_population_size(key_list)
            extracted_bucket_size = extracted_bucket.get_population_size()
            extracted_value_count = extracted_bucket.get_population_size(key_list)

            # Comparing bucket sizes
            self.assertEqual(original_bucket_size, smaller_bucket_size + extracted_bucket_size,
                            'Case 3 buckets do not add up.')
            self.assertEqual(total_population - available_population, smaller_bucket_size,
                            'Case 3 original bucket is not the correct size.')  
            self.assertEqual(smaller_bucket_size, original_bucket_size - extracted_bucket_size,
                            'Case 3  original bucket is not the correct size.')

            # Comparing count of values in key_list
            self.assertEqual(original_value_count, smaller_value_count + extracted_value_count,
                            'Case 3 property values do not add up.')
            self.assertEqual(available_population,  extracted_value_count,
                            'Case 3 extracted property is not the correct size.')
            self.assertEqual(smaller_value_count, original_value_count - extracted_value_count,
                            'Case 3 original property count is not the correct size.')

    ### BlockTemplate tests
    ## BlockTemplate.Generate
    def test_block_template_generate(self):
        """ Tests BlockTemplate.Generate

            Generate returns a valid PropertyBlock with the defined population quantity

            Case 1: 
                action : Create a PropertyBlock from a BlockTemplate
                result : PropertyBlock should be valid.
                
            Case 2: 
                action : Change the previous template and create another PropertyBlock
                result : New PropertyBlock should be valid.
                         The first PropertyBlock should not be affected by the changes in the template.
                         
            Case 3: 
                action : Creates a third PropertyBlock from a BlockTemplate with population 0
                result : PropertyBlock should be None.

        """
        
        # Create a BlockTemplate with 3 characteristics
        block_template = BlockTemplate()
        block_template.add_bucket('characteristic_A', ('value_A1', 'value_A2', 'value_A3'))
        block_template.add_bucket('characteristic_B', ('value_B1', 'value_B2',))
        block_template.add_bucket('characteristic_C', ('value_C1', 'value_C2', 'value_C3'))

        # Case 1:
        # Create a PropertyBlock using the BlockTemplate
        block1 = block_template.Generate(300)
        block1_size = block1.get_population_size()
        
        # Compare size, PropertyBuckets count and verify block validity
        self.assertEqual(block1_size, 300,
                        'Case 1 Target block size is not the correct amount.')
        self.assertEqual(len(block1.buckets.keys()), 3,
                        'Case 1 Target block bucket count is not the correct amount.')
        self.assertTrue(verify_block_validity(block1),
                        'Case 1 Target block is not valid.')
                       
        # Case 2:
        # Adds a new bucket to the BlockTemplate and creates a new PropertyBlock
        block_template.add_bucket('characteristic_D', ('value_D1', 'value_D2'))
        block2 = block_template.Generate(50)
        block2_size = block2.get_population_size()
        
        # Compare size, PropertyBuckets count and verify block validity
        self.assertEqual(block2_size, 50,
                        'Case 2 Target block population size is not the correct amount.')
        self.assertEqual(len(block2.buckets.keys()), 4,
                        'Case 2 Target block bucket count is not the correct amount.')
        self.assertEqual(len(block1.buckets.keys()), 3,
                        'Case 2 Previous block was affected by pop_template changes')
        self.assertTrue(verify_block_validity(block2),
                        'Case 2 Target block is not valid.')
        
        # Case 3:
        # Creates a PropertyBlock with 0 population - Should be None
        block3 = block_template.Generate(0)

        # Verify block validity
        self.assertEqual(block3, None, 'Case 3 Target block should be None.')
    
    ## BlockTemplate.GenerateEmpty    
    def test_block_template_generate_empty(self):
        """ Tests BlockTemplate.GenerateEmpty

            Generate returns a valid PropertyBlock with population 0

            Case 1: 
                action : Create a PropertyBlock from a BlockTemplate using GenerateEmpty
                result : PropertyBlock should be valid.
        """
        
        # Create a BlockTemplate with 3 characteristics
        block_template = BlockTemplate()
        block_template.add_bucket('characteristic_A', ('value_A1', 'value_A2', 'value_A3'))
        block_template.add_bucket('characteristic_B', ('value_B1', 'value_B2',))
        block_template.add_bucket('characteristic_C', ('value_C1', 'value_C2', 'value_C3'))

        # Case 1:
        # Create a PropertyBlock using the BlockTemplate
        block1 = block_template.GenerateEmpty()
        block1_size = block1.get_population_size()
        
        # Compare size, PropertyBuckets count and verify block validity
        self.assertEqual(block1_size, 0,
                        'Case 1 Target block size is not the correct amount.')
        self.assertEqual(len(block1.buckets.keys()), 3,
                        'Case 1 Target block bucket count is not the correct amount.')
        self.assertTrue(verify_block_validity(block1),
                        'Case 1 Target block is not valid.')
        
    ## BlockTemplate.GenerateProfile
    def test_block_template_generate_profile(self):
        """ Tests BlockTemplate.GenerateProfile

            GenerateProfile returns a valid PropertyBlock with the defined population quantity and characteristic->[values]

            Case 1: 
                action : Create a PropertyBlock from a BlockTemplate using a Profile.
                         The population requested is equal the highest sum defined in a single 
                         characteristic.
                result : PropertyBlock should be valid.
                         Characteristics with fewer defined people should be randomly dsitributed.
                
            Case 2: 
                action : Create a PropertyBlock from a BlockTemplate using a Profile.
                         The population requested is double than the highest sum defined in a single 
                         characteristic.
                result : New PropertyBlock should be valid.
                         Remainind population should be randomly distributed.
                         
            Case 3: 
                action : Create a PropertyBlock from a BlockTemplate using a Profile.
                         The population requested is half than the highest sum defined in a single            
                         characteristic.
                result : Population should be properly distributed according to proportion requested.
                
            Case 4: 
                action : Create a PropertyBlock from a BlockTemplate using a Profile.
                         The population requested is 0.
                result : PropertyBlock should be None


        """
        
        # Create a BlockTemplate with 6 characteristics
        block_template = BlockTemplate()
        block_template.add_bucket('characteristic_A', ('value_A1', 'value_A2', 'value_A3'))
        block_template.add_bucket('characteristic_B', ('value_B1', 'value_B2', 'value_B3'))
        block_template.add_bucket('characteristic_C', ('value_C1', 'value_C2', 'value_C3'))
        block_template.add_bucket('characteristic_D', ('value_D1', 'value_D2', 'value_D3'))
        block_template.add_bucket('characteristic_E', ('value_E1', 'value_E2'))
        block_template.add_bucket('characteristic_F', ('value_F1', 'value_F2'))
        
        # Case 1:
        # Creates a pop_profile dict with the following goals per characteristic:
        # A: Total population distributed through all values
        # B: Total population distributed in a two or more values, but not all - others sould be 0
        # C: Total population distributed in a single value - others sould be 0
        # D: Partial population in a single value - remaining population distributed in other values
        # E: Empty dict - should be randomly distributed
        # F: Not in profile - should be randomly distributed
        pop_profile = {'characteristic_A' : {'value_A1' : 30, 'value_A2' : 50, 'value_A3': 20},
                        'characteristic_B' : {'value_B1' : 40, 'value_B2': 60},
                        'characteristic_C' : {'value_C1' : 100},
                        'characteristic_D' : {'value_D1' : 30},
                        'characteristic_E' : {}}
        
        # Create a PropertyBlock using the template. 100 is the highest sum defined in a single characteristic (A, B and C) 
        block1 = block_template.GenerateProfile(100, pop_profile)
        block1_size = block1.get_population_size()
        values = block1.get_mapping_of_property_values()
        
        # Compare size, PropertyBuckets count and verify block validity
        self.assertTrue(verify_block_validity(block1),
                        'Case 1 Target block is not valid.')
        self.assertEqual(block1_size, 100,
                        'Case 1 Target block size is not the correct amount.')
        self.assertEqual(len(block1.buckets.keys()), 6,
                        'Case 1 Target block bucket count is not the correct amount.')
        
        # Verify that the population was properly distributed when all values are defined and equal the requested amount
        self.assertTrue(values[0] == [30,50,20], 'Case 1 Propery value is not the expected amount')
        self.assertTrue(values[1] == [40,60,0], 'Case 1 Propery value is not the expected amount')
        self.assertTrue(values[2] == [100,0,0], 'Case 1 Propery value is not the expected amount')
        
        # Verify that a value is as defined when the sum of all values is less than the requested amount
        self.assertTrue(values[3][0] == 30, 'Case 1 Propery value is not the expected amount')
        
        # Case 2:
        # Requested population is higher than the max defined value, the following behaviours should occur:
        # A: Population distributed through all values - minimum values of (30, 50, 20)
        # B: Remaining population distributed in the undefined values - equal to (40, 60, 100)
        # C: Remaining population distributed in the undefined values - ranges of (100, 0-100, 0-100)
        # D: Remaining population distributed in the undefined values - ranges of (30, 0-170, 0-170)
        # E: Empty dict - should be randomly distributed
        # F: Not in profile - should be randomly distributed
        pop_profile = {'characteristic_A' : {'value_A1' : 30, 'value_A2' : 50, 'value_A3': 20},
                        'characteristic_B' : {'value_B1' : 40, 'value_B2': 60},
                        'characteristic_C' : {'value_C1' : 100},
                        'characteristic_D' : {'value_D1' : 30},
                        'characteristic_E' : {}}
        
        # Create a PropertyBlock using the template. 200 is the more than the highest sum defined in a single characteristic (A, B and C)
        block2 = block_template.GenerateProfile(200, pop_profile)
        block2_size = block2.get_population_size()
        values = block2.get_mapping_of_property_values()
        
        # Compare size, PropertyBuckets count and verify block validity
        self.assertTrue(verify_block_validity(block2),
                        'Case 2 Target block is not valid.')
        self.assertEqual(block2_size, 200,
                        'Case 2 Target block size is not the corrected amount.')
        self.assertEqual(len(block2.buckets.keys()), 6,
                        'Case 2 Target block bucket count is not the correct amount.')
        
        # Verify that the population was properly distributed when all values are defined
        self.assertTrue(values[0][0] >= 30, 'Case 2 Propery value is not the expected amount')
        self.assertTrue(values[0][1] >= 50, 'Case 2 Propery value is not the expected amount')
        self.assertTrue(values[0][2] >= 20, 'Case 2 Propery value is not the expected amount')
        
        # Verify that defined values remained the same when there is a undefined value
        self.assertTrue(values[1] == [40,60,100], 'Case 2 Propery value is not the expected amount')
        self.assertTrue(values[2][0] == 100, 'Case 2 Propery value is not the expected amount')
        self.assertTrue(values[3][0] == 30, 'Case 2 Propery value is not the expected amount')
        
        # Verify that undefined values are the expected amount after distribution
        self.assertTrue(values[2][1] >= 0 and values[2][1] <= 100, 
                        'Case 2 Propery value is not the expected amount')
        self.assertTrue(values[2][2] >= 0 and values[2][2] <= 100,
                        'Case 2 Propery value is not the expected amount')
        self.assertTrue(values[3][1] >= 0 and values[3][1] <= 170,
                        'Case 2 Propery value is not the expected amount')
        self.assertTrue(values[3][2] >= 0 and values[3][2] <= 170,
                        'Case 2 Propery value is not the expected amount')
        
        
        # Case 3:
        # Requested population is fewer than the max defined value, the following behaviours should occur:
        # A: Population distributed through all values - maximum values of (20, 20, 20)
        # B: Defined values reduced to fit requested amount - ranges of (0-20, 0-20, 0)
        # C: Defined values reduced to fit requested amount - equals to (20, 0, 0)
        # D: Defined values reduced to fit requested amount - equals of (30, 0-170, 0-170)
        # E: Empty dict - should be randomly distributed
        # F: Not in profile - should be randomly distributed
        pop_profile = {'characteristic_A' : {'value_A1' : 30, 'value_A2' : 50, 'value_A3': 20},
                        'characteristic_B' : {'value_B1' : 40, 'value_B2': 60},
                        'characteristic_C' : {'value_C1' : 100},
                        'characteristic_D' : {'value_D1' : 30},
                        'characteristic_E' : {}}
        
        # Create a PropertyBlock using the template. 20 is the lower then the minimum defined in a single characteristic (D)
        block3 = block_template.GenerateProfile(20, pop_profile)
        block3_size = block3.get_population_size()
        values = block3.get_mapping_of_property_values()
        
        # Compare size, PropertyBuckets count and verify block validity
        self.assertTrue(verify_block_validity(block3),
                        'Case 3 Target block is not valid.')
        self.assertEqual(block3_size, 20,
                        'Case 3 Target block size is not the corrected amount.')
        self.assertEqual(len(block3.buckets.keys()), 6,
                        'Case 3 Target block bucket count is not the correct amount.')
        
        # Verify that the population was properly distributed when all values are defined
        self.assertTrue(values[0][0] <= 20, 'Case 3 Propery value is not the expected amount')
        self.assertTrue(values[0][1] <= 20, 'Case 3 Propery value is not the expected amount')
        self.assertTrue(values[0][2] <= 20, 'Case 3 Propery value is not the expected amount')
        self.assertTrue(values[1][0] <= 20, 'Case 3 Propery value is not the expected amount')
        self.assertTrue(values[1][1] <= 20, 'Case 3 Propery value is not the expected amount')
        
        # Verify that defined values remained the same when there is a undefined value
        self.assertTrue(values[1][2] == 0, 'Case 3 Propery value is not the expected amount')
        self.assertTrue(values[2] == [20,0,0], 'Case 3 Propery value is not the expected amount')
        self.assertTrue(values[3] == [20,0,0], 'Case 3 Propery value is not the expected amount')
        
        
        # Case 4:
        # Requested 0 population:
        block4 = block_template.GenerateProfile(0, pop_profile)

        # Verify block validity
        self.assertEqual(block4, None, 'Case 4 Target block should be None.')
     
    ## BlockTemplate.Generate - without buckets    
    def test_block_template_without_buckets(self):
        """ Tests BlockTemplate Generate functions without defining buckets

            All Generate functions return a invalid PropertyBlock (None)

            Case 1: 
                action : Create a PropertyBlock from a BlockTemplate with 0 buckets using Generate
                result : PropertyBlock should be None.
                
            Case 2: 
                action : Create a PropertyBlock from a BlockTemplate with 0 buckets using GenerateEmpty
                result : PropertyBlock should be None.
                
            Case 3: 
                action : Create a PropertyBlock from a BlockTemplate with 0 buckets using GenerateProfile
                result : PropertyBlock should be None.
                
        """
        
        # Create a BlockTemplate with 0 characteristics
        block_template = BlockTemplate()

        # Case 1:
        # Create a PropertyBlock using BlockTemplate.Generate
        block1 = block_template.Generate(100)
        self.assertEqual(block1, None, 'Case 1 Target block should be None.')
        
        # Case 2:
        # Create a PropertyBlock using BlockTemplate.Generate
        block2 = block_template.GenerateEmpty()
        self.assertEqual(block2, None, 'Case 2 Target block should be None.')
        
        # Case 3:
        # Create a PropertyBlock using BlockTemplate.Generate
        pop_profile = {}
        block3 = block_template.GenerateProfile(100, pop_profile)
        self.assertEqual(block3, None, 'Case 3 Target block should be None.')
          
    
    ### PropertyBlock tests   
    ## PropertyBlock.add_block
    def test_property_block_add_block(self):
        """ Tests PropertyBlock.add_block

            Final block size equals original block size plus added block size. 

            Case 1: 
                action : Add auxiliary block to target block.
                result : Target block should be valid.
                         Target block size equals original size plus added block size.

        """
        # Create a BlockTemplate with 4 characteristics
        block_template = BlockTemplate()
        block_template.add_bucket('characteristic_A', ('value_A1', 'value_A2', 'value_A3'))
        block_template.add_bucket('characteristic_B', ('value_B1', 'value_B2',))
        block_template.add_bucket('characteristic_C', ('value_C1', 'value_C2', 'value_C3'))
        block_template.add_bucket('characteristic_D', ('value_D1', 'value_D2'))

        # Create two PropertyBlocks using the same template
        target_block = block_template.Generate(300)
        add_block = block_template.Generate(50)

        # Get PropertyBlocks sizes
        original_size = target_block.get_population_size()
        add_size = add_block.get_population_size()

        # Add aux block to the target block
        target_block.add_block(add_block)
        
        final_size = target_block.get_population_size()
        
        # Compare size
        self.assertEqual(final_size, original_size + add_size,
                        'Target block size is not the sum of both blocks.')

        # Verify block validity
        self.assertTrue(verify_block_validity(target_block),
                        'Target block is not valid.')

    ## PropertyBlock.extract - without key
    def test_property_block_extract_without_key(self):
        """Tests PropertyBlock.extract without using keys in a PopTemplate
        
        Final block size equals original block size plus added block size. 

        Case 1: 
            action : Extracts less population from target block than available matching template. 
            result : Target block should be valid.
                     Extracted block should valid.
                     Target block size plus Extracted block size should 
                        equal to previous target block size.
                     Extracted block should have population size matching template 
                        equal to requested quantity.
                     Target block final size according to template is original size - extracted block size.
        
        Case 2: 
            action : Extracts equal population from target block as available matching template. 
            result : Target block should be valid.
                     Extracted block should valid.
                     Target block size plus Extracted block size should 
                        equal to previous target block size.
                     Extracted block should have population size matching template 
                        equal to original size.
                     Target block population size is zero.
        
        Case 3: 
            action : Extracts more population from target block than available matching template. 
            result : Target block should be valid.
                     Extracted block should valid.
                     Target block size plus Extracted block size should 
                        equal to previous target block size.
                     Extracted block should have population size matching template 
                        equal to original size.
        
        """
        
        # Create a BlockTemplate with 3 characteristics
        block_template = BlockTemplate()
        block_template.add_bucket('characteristic_A', ('value_A1', 'value_A2', 'value_A3'))
        block_template.add_bucket('characteristic_B', ('value_B1', 'value_B2',))
        block_template.add_bucket('characteristic_C', ('value_C1', 'value_C2', 'value_C3'))
        
        pop_profile = {'characteristic_A' : {'value_A1' : 30, 'value_A2' : 50},
                       'characteristic_B' : {'value_B1' : 50, 'value_B2' : 250}}
        
        # Set initial block size
        initial_block_size = 300
        
        # Creates a PopTemplate
        pop_template = PopTemplate()

        # Case 1
        target_block = block_template.GenerateProfile(initial_block_size, pop_profile)
        
        # Gets original sizes
        target_block_original_size = target_block.get_population_size()
        available_original_size = target_block.get_population_size(pop_template)
        
        # Extracts less people than available
        extracted_block = target_block.extract(20, pop_template)
        
        # Gets final sizes
        extracted_block_size = extracted_block.get_population_size()
        target_block_final_size = target_block.get_population_size()
        available_final_size = target_block.get_population_size(pop_template)
        
        self.assertEqual(20, extracted_block_size,
                        'Case 1: Extracted block size is not the extracted quantity.')
        self.assertEqual(target_block_original_size, extracted_block_size + target_block_final_size ,
                        'Case 1: Block sizes do not add up.')
        self.assertEqual(20, extracted_block.get_population_size(pop_template),
                        'Case 1: Extracted block does not represent template.')
        self.assertEqual(available_original_size, available_final_size + extracted_block_size,
                        'Case 1: Target block does not represent population template change.')
        self.assertTrue(verify_block_validity(target_block),
                        'Case 1: Target block is not valid.')
        self.assertTrue(verify_block_validity(extracted_block),
                        'Case 1: Extracted block is not valid.')


        # Case 2
        target_block = block_template.GenerateProfile(initial_block_size, pop_profile)

        # Gets original sizes
        target_block_original_size = target_block.get_population_size()
        matching_pop_size = target_block.get_population_size(pop_template)
        available_original_size = target_block.get_population_size(pop_template)
        
        # Extracts equal people to available
        extracted_block = target_block.extract(matching_pop_size, pop_template)
        
        # Gets final sizes
        extracted_block_size = extracted_block.get_population_size()
        target_block_final_size = target_block.get_population_size()
        available_final_size = target_block.get_population_size(pop_template)

        self.assertEqual(matching_pop_size, extracted_block_size,
                        'Case 2: Extracted block size is not the extracted quantity.')
        self.assertEqual(target_block_original_size, extracted_block_size + target_block_final_size ,
                        'Case 2: Block sizes do not add up.')
        self.assertEqual(matching_pop_size, extracted_block.get_population_size(pop_template),
                        'Case 2: Extracted block does not represent template.')
        self.assertEqual(available_original_size, available_final_size + extracted_block_size,
                        'Case 2: Target block does not represent population template change.')
        self.assertTrue(verify_block_validity(target_block),
                        'Case 2: Target block is not valid.')
        self.assertTrue(verify_block_validity(extracted_block),
                        'Case 2: Extracted block is not valid.')               

        # Case 3
        target_block = block_template.GenerateProfile(initial_block_size, pop_profile)

        # Gets original sizes
        target_block_original_size = target_block.get_population_size()
        matching_pop_size = target_block.get_population_size(pop_template)
        available_original_size = target_block.get_population_size(pop_template)
        
        # Extracts more people than available
        extracted_block = target_block.extract(matching_pop_size + 20, pop_template)
        
        # Gets final sizes
        extracted_block_size = extracted_block.get_population_size()
        target_block_final_size = target_block.get_population_size()
        available_final_size = target_block.get_population_size(pop_template)

        self.assertEqual(matching_pop_size, extracted_block_size,
                        'Case 3: Extracted block size is not the entire possible population.')
        self.assertEqual(target_block_original_size, extracted_block_size + target_block_final_size ,
                        'Case 3: Block sizes do not add up.')
        self.assertEqual(matching_pop_size, extracted_block.get_population_size(pop_template),
                        'Case 3: Extracted block does not represent template.')
        self.assertEqual(available_original_size, available_final_size + extracted_block_size,
                        'Case 3: Target block does not represent population template change.')
        self.assertTrue(verify_block_validity(target_block),
                        'Case 3: Target block is not valid.')
        self.assertTrue(verify_block_validity(extracted_block),
                        'Case 3: Extracted block is not valid.') 

    ## PropertyBlock.extract - with key
    def test_property_block_extract_with_key(self):
        """Tests PropertyBlock.extract
        
        Final block size equals original block size plus added block size. 

        Case 1: 
            action : Extracts less population from target block than available matching template. 
            result : Target block should be valid.
                     Extracted block should valid.
                     Target block size plus Extracted block size should 
                        equal to previous target block size.
                     Extracted block should have population size matching template 
                        equal to requested quantity.
                     Target block final size according to template is original size - extracted block size.
        
        Case 2: 
            action : Extracts equal population from target block as available matching template. 
            result : Target block should be valid.
                     Extracted block should valid.
                     Target block size plus Extracted block size should 
                        equal to previous target block size.
                     Extracted block should have population size matching template 
                        equal to original size.
                     Target block population size is zero.
        
        Case 3: 
            action : Extracts more population from target block than available matching template. 
            result : Target block should be valid.
                     Extracted block should valid.
                     Target block size plus Extracted block size should 
                        equal to previous target block size.
                     Extracted block should have population size matching template 
                        equal to original size.
        
        """
        
        # Create a BlockTemplate with 3 characteristics
        block_template = BlockTemplate()
        block_template.add_bucket('characteristic_A', ('value_A1', 'value_A2', 'value_A3'))
        block_template.add_bucket('characteristic_B', ('value_B1', 'value_B2',))
        block_template.add_bucket('characteristic_C', ('value_C1', 'value_C2', 'value_C3'))
        
        pop_profile = {'characteristic_A' : {'value_A1' : 30, 'value_A2' : 50},
                       'characteristic_B' : {'value_B1' : 50, 'value_B2' : 250}}
        
        # Set initial block size
        initial_block_size = 300
        
        # Creates a PopTemplate
        pop_template = PopTemplate()
        pop_template.set_sampled_property('characteristic_A', 'value_A1')
        pop_template.set_sampled_property('characteristic_B', 'value_B1')

        # Case 1
        target_block = block_template.GenerateProfile(initial_block_size, pop_profile)
        
        # Gets original sizes
        target_block_original_size = target_block.get_population_size()
        available_original_size = target_block.get_population_size(pop_template)
        
        # Extracts less people than available
        extracted_block = target_block.extract(20, pop_template)
        
        # Gets final sizes
        extracted_block_size = extracted_block.get_population_size()
        target_block_final_size = target_block.get_population_size()
        available_final_size = target_block.get_population_size(pop_template)
        
        self.assertEqual(20, extracted_block_size,
                        'Case 1: Extracted block size is not the extracted quantity.')
        self.assertEqual(target_block_original_size, extracted_block_size + target_block_final_size ,
                        'Case 1: Block sizes do not add up.')
        self.assertEqual(available_final_size, available_original_size - 20,
                        'Case 1: Available final size is not correct.')
        self.assertEqual(20, extracted_block.get_population_size(pop_template),
                        'Case 1: Extracted block does not represent template.')
        self.assertEqual(available_original_size, available_final_size + extracted_block_size,
                        'Case 1: Target block does not represent population template change.')
        self.assertTrue(verify_block_validity(target_block),
                        'Case 1: Target block is not valid.')
        self.assertTrue(verify_block_validity(extracted_block),
                        'Case 1: Extracted block is not valid.')


        # Case 2
        target_block = block_template.GenerateProfile(initial_block_size, pop_profile)

        # Gets original sizes
        target_block_original_size = target_block.get_population_size()
        matching_pop_size = target_block.get_population_size(pop_template)
        available_original_size = target_block.get_population_size(pop_template)
        
        # Extracts equal people to available
        extracted_block = target_block.extract(matching_pop_size, pop_template)
        
        # Gets final sizes
        extracted_block_size = extracted_block.get_population_size()
        target_block_final_size = target_block.get_population_size()
        available_final_size = target_block.get_population_size(pop_template)

        self.assertEqual(matching_pop_size, extracted_block_size,
                        'Case 2: Extracted block size is not the extracted quantity.')
        self.assertEqual(target_block_original_size, extracted_block_size + target_block_final_size ,
                        'Case 2: Block sizes do not add up.')
        self.assertEqual(available_final_size, 0,
                        'Case 2: Available final size is not 0.')
        self.assertEqual(matching_pop_size, extracted_block.get_population_size(pop_template),
                        'Case 2: Extracted block does not represent template.')
        self.assertEqual(available_original_size, available_final_size + extracted_block_size,
                        'Case 2: Target block does not represent population template change.')
        self.assertTrue(verify_block_validity(target_block),
                        'Case 2: Target block is not valid.')
        self.assertTrue(verify_block_validity(extracted_block),
                        'Case 2: Extracted block is not valid.')               

        # Case 3
        target_block = block_template.GenerateProfile(initial_block_size, pop_profile)

        # Gets original sizes
        target_block_original_size = target_block.get_population_size()
        matching_pop_size = target_block.get_population_size(pop_template)
        available_original_size = target_block.get_population_size(pop_template)
        
        # Extracts more people than available
        extracted_block = target_block.extract(matching_pop_size + 20, pop_template)
        
        # Gets final sizes
        extracted_block_size = extracted_block.get_population_size()
        target_block_final_size = target_block.get_population_size()
        available_final_size = target_block.get_population_size(pop_template)

        self.assertEqual(matching_pop_size, extracted_block_size,
                        'Case 3: Extracted block size is not the entire possible population.')
        self.assertEqual(target_block_original_size, extracted_block_size + target_block_final_size ,
                        'Case 3: Block sizes do not add up.')
        self.assertEqual(available_final_size, 0,
                        'Case 3: Available final size is not 0.')
        self.assertEqual(matching_pop_size, extracted_block.get_population_size(pop_template),
                        'Case 3: Extracted block does not represent template.')
        self.assertEqual(available_original_size, available_final_size + extracted_block_size,
                        'Case 3: Target block does not represent population template change.')
        self.assertTrue(verify_block_validity(target_block),
                        'Case 3: Target block is not valid.')
        self.assertTrue(verify_block_validity(extracted_block),
                        'Case 3: Extracted block is not valid.')   
        
    ## PropertyBlock.extract - with key list
    def test_property_block_extract_with_key_list(self):
        """Tests PropertyBlock.extract using key list in PopTemplate
        
        Final block size equals original block size plus added block size. 

        Case 1: 
            action : Extracts less population from target block than available matching template. 
            result : Target block should be valid.
                     Extracted block should valid.
                     Target block size plus Extracted block size should 
                        equal to previous target block size.
                     Extracted block should have population size matching template 
                        equal to requested quantity.
                     Target block final size according to template is original size - extracted block size.
        
        Case 2: 
            action : Extracts equal population from target block as available matching template. 
            result : Target block should be valid.
                     Extracted block should valid.
                     Target block size plus Extracted block size should 
                        equal to previous target block size.
                     Extracted block should have population size matching template 
                        equal to original size.
                     Target block population size is zero.
        
        Case 3: 
            action : Extracts more population from target block than available matching template. 
            result : Target block should be valid.
                     Extracted block should valid.
                     Target block size plus Extracted block size should 
                        equal to previous target block size.
                     Extracted block should have population size matching template 
                        equal to original size.
        
        """
        
        # Create a BlockTemplate with 3 characteristics
        block_template = BlockTemplate()
        block_template.add_bucket('characteristic_A', ('value_A1', 'value_A2', 'value_A3'))
        block_template.add_bucket('characteristic_B', ('value_B1', 'value_B2',))
        block_template.add_bucket('characteristic_C', ('value_C1', 'value_C2', 'value_C3'))
        
        pop_profile = {'characteristic_A' : {'value_A1' : 30, 'value_A2' : 50},
                       'characteristic_B' : {'value_B1' : 50, 'value_B2' : 250}}
        
        # Set initial block size
        initial_block_size = 300
        
        # Creates a PopTemplate
        pop_template = PopTemplate()
        pop_template.set_sampled_property('characteristic_A', ['value_A1', 'value_A2'])
        pop_template.set_sampled_property('characteristic_B', ['value_B1', 'value_B2'])
        pop_template.set_sampled_property('characteristic_C', [])


        # Case 1
        target_block = block_template.GenerateProfile(initial_block_size, pop_profile)
        
        # Gets original sizes
        target_block_original_size = target_block.get_population_size()
        available_original_size = target_block.get_population_size(pop_template)
        
        # Extracts less people than available
        extracted_block = target_block.extract(20, pop_template)
        
        # Gets final sizes
        extracted_block_size = extracted_block.get_population_size()
        target_block_final_size = target_block.get_population_size()
        available_final_size = target_block.get_population_size(pop_template)
        
        self.assertEqual(20, extracted_block_size,
                        'Case 1: Extracted block size is not the extracted quantity.')
        self.assertEqual(target_block_original_size, extracted_block_size + target_block_final_size ,
                        'Case 1: Block sizes do not add up.')
        self.assertEqual(available_final_size, available_original_size - 20,
                        'Case 1: Available final size is not correct.')
        self.assertEqual(20, extracted_block.get_population_size(pop_template),
                        'Case 1: Extracted block does not represent template.')
        self.assertEqual(available_original_size, available_final_size + extracted_block_size,
                        'Case 1: Target block does not represent population template change.')
        self.assertTrue(verify_block_validity(target_block),
                        'Case 1: Target block is not valid.')
        self.assertTrue(verify_block_validity(extracted_block),
                        'Case 1: Extracted block is not valid.')


        # Case 2
        target_block = block_template.GenerateProfile(initial_block_size, pop_profile)

        # Gets original sizes
        target_block_original_size = target_block.get_population_size()
        matching_pop_size = target_block.get_population_size(pop_template)
        available_original_size = target_block.get_population_size(pop_template)
        
        # Extracts equal people to available
        extracted_block = target_block.extract(matching_pop_size, pop_template)
        
        # Gets final sizes
        extracted_block_size = extracted_block.get_population_size()
        target_block_final_size = target_block.get_population_size()
        available_final_size = target_block.get_population_size(pop_template)

        self.assertEqual(matching_pop_size, extracted_block_size,
                        'Case 2: Extracted block size is not the extracted quantity.')
        self.assertEqual(target_block_original_size, extracted_block_size + target_block_final_size ,
                        'Case 2: Block sizes do not add up.')
        self.assertEqual(available_final_size, 0,
                        'Case 2: Available final size is not 0.')
        self.assertEqual(matching_pop_size, extracted_block.get_population_size(pop_template),
                        'Case 2: Extracted block does not represent template.')
        self.assertEqual(available_original_size, available_final_size + extracted_block_size,
                        'Case 2: Target block does not represent population template change.')
        self.assertTrue(verify_block_validity(target_block),
                        'Case 2: Target block is not valid.')
        self.assertTrue(verify_block_validity(extracted_block),
                        'Case 2: Extracted block is not valid.')               

        # Case 3
        target_block = block_template.GenerateProfile(initial_block_size, pop_profile)

        # Gets original sizes
        target_block_original_size = target_block.get_population_size()
        matching_pop_size = target_block.get_population_size(pop_template)
        available_original_size = target_block.get_population_size(pop_template)
        
        # Extracts more people than available
        extracted_block = target_block.extract(matching_pop_size + 20, pop_template)
        
        # Gets final sizes
        extracted_block_size = extracted_block.get_population_size()
        target_block_final_size = target_block.get_population_size()
        available_final_size = target_block.get_population_size(pop_template)

        self.assertEqual(matching_pop_size, extracted_block_size,
                        'Case 3: Extracted block size is not the entire possible population.')
        self.assertEqual(target_block_original_size, extracted_block_size + target_block_final_size ,
                        'Case 3: Block sizes do not add up.')
        self.assertEqual(available_final_size, 0,
                        'Case 3: Available final size is not 0.')
        self.assertEqual(matching_pop_size, extracted_block.get_population_size(pop_template),
                        'Case 3: Extracted block does not represent template.')
        self.assertEqual(available_original_size, available_final_size + extracted_block_size,
                        'Case 3: Target block does not represent population template change.')
        self.assertTrue(verify_block_validity(target_block),
                        'Case 3: Target block is not valid.')
        self.assertTrue(verify_block_validity(extracted_block),
                        'Case 3: Extracted block is not valid.')   

    ## PropertyBlock.extract - with key set
    def test_property_block_extract_with_key_set(self):
        """Tests PropertyBlock.extract using key sets in PopTemplate
        
        Final block size equals original block size plus added block size. 

        Case 1: 
            action : Extracts less population from target block than available matching template. 
            result : Target block should be valid.
                     Extracted block should valid.
                     Target block size plus Extracted block size should 
                        equal to previous target block size.
                     Extracted block should have population size matching template 
                        equal to requested quantity.
                     Target block final size according to template is original size - extracted block size.
        
        Case 2: 
            action : Extracts equal population from target block as available matching template. 
            result : Target block should be valid.
                     Extracted block should valid.
                     Target block size plus Extracted block size should 
                        equal to previous target block size.
                     Extracted block should have population size matching template 
                        equal to original size.
                     Target block population size is zero.
        
        Case 3: 
            action : Extracts more population from target block than available matching template. 
            result : Target block should be valid.
                     Extracted block should valid.
                     Target block size plus Extracted block size should 
                        equal to previous target block size.
                     Extracted block should have population size matching template 
                        equal to original size.
        
        """
        
        # Create a BlockTemplate with 3 characteristics
        block_template = BlockTemplate()
        block_template.add_bucket('characteristic_A', ('value_A1', 'value_A2', 'value_A3'))
        block_template.add_bucket('characteristic_B', ('value_B1', 'value_B2',))
        block_template.add_bucket('characteristic_C', ('value_C1', 'value_C2', 'value_C3'))
        
        pop_profile = {'characteristic_A' : {'value_A1' : 30, 'value_A2' : 50},
                       'characteristic_B' : {'value_B1' : 50, 'value_B2' : 250}}
        
        # Set initial block size
        initial_block_size = 300
        
        # Creates a PopTemplate
        pop_template = PopTemplate()
        pop_template.set_sampled_property('characteristic_A', {'value_A1', 'value_A2'})
        pop_template.set_sampled_property('characteristic_B', {'value_B1', 'value_B2'})
        pop_template.set_sampled_property('characteristic_C', set())

        # Case 1
        target_block = block_template.GenerateProfile(initial_block_size, pop_profile)
        
        # Gets original sizes
        target_block_original_size = target_block.get_population_size()
        available_original_size = target_block.get_population_size(pop_template)
        
        # Extracts less people than available
        extracted_block = target_block.extract(20, pop_template)
        
        # Gets final sizes
        extracted_block_size = extracted_block.get_population_size()
        target_block_final_size = target_block.get_population_size()
        available_final_size = target_block.get_population_size(pop_template)
        
        self.assertEqual(20, extracted_block_size,
                        'Case 1: Extracted block size is not the extracted quantity.')
        self.assertEqual(target_block_original_size, extracted_block_size + target_block_final_size ,
                        'Case 1: Block sizes do not add up.')
        self.assertEqual(available_final_size, available_original_size - 20,
                        'Case 1: Available final size is not correct.')
        self.assertEqual(20, extracted_block.get_population_size(pop_template),
                        'Case 1: Extracted block does not represent template.')
        self.assertEqual(available_original_size, available_final_size + extracted_block_size,
                        'Case 1: Target block does not represent population template change.')
        self.assertTrue(verify_block_validity(target_block),
                        'Case 1: Target block is not valid.')
        self.assertTrue(verify_block_validity(extracted_block),
                        'Case 1: Extracted block is not valid.')


        # Case 2
        target_block = block_template.GenerateProfile(initial_block_size, pop_profile)

        # Gets original sizes
        target_block_original_size = target_block.get_population_size()
        matching_pop_size = target_block.get_population_size(pop_template)
        available_original_size = target_block.get_population_size(pop_template)
        
        # Extracts equal people to available
        extracted_block = target_block.extract(matching_pop_size, pop_template)
        
        # Gets final sizes
        extracted_block_size = extracted_block.get_population_size()
        target_block_final_size = target_block.get_population_size()
        available_final_size = target_block.get_population_size(pop_template)

        self.assertEqual(matching_pop_size, extracted_block_size,
                        'Case 2: Extracted block size is not the extracted quantity.')
        self.assertEqual(target_block_original_size, extracted_block_size + target_block_final_size ,
                        'Case 2: Block sizes do not add up.')
        self.assertEqual(available_final_size, 0,
                        'Case 2: Available final size is not 0.')
        self.assertEqual(matching_pop_size, extracted_block.get_population_size(pop_template),
                        'Case 2: Extracted block does not represent template.')
        self.assertEqual(available_original_size, available_final_size + extracted_block_size,
                        'Case 2: Target block does not represent population template change.')
        self.assertTrue(verify_block_validity(target_block),
                        'Case 2: Target block is not valid.')
        self.assertTrue(verify_block_validity(extracted_block),
                        'Case 2: Extracted block is not valid.')               

        # Case 3
        target_block = block_template.GenerateProfile(initial_block_size, pop_profile)

        # Gets original sizes
        target_block_original_size = target_block.get_population_size()
        matching_pop_size = target_block.get_population_size(pop_template)
        available_original_size = target_block.get_population_size(pop_template)
        
        # Extracts more people than available
        extracted_block = target_block.extract(matching_pop_size + 20, pop_template)
        
        # Gets final sizes
        extracted_block_size = extracted_block.get_population_size()
        target_block_final_size = target_block.get_population_size()
        available_final_size = target_block.get_population_size(pop_template)

        self.assertEqual(matching_pop_size, extracted_block_size,
                        'Case 3: Extracted block size is not the entire possible population.')
        self.assertEqual(target_block_original_size, extracted_block_size + target_block_final_size ,
                        'Case 3: Block sizes do not add up.')
        self.assertEqual(available_final_size, 0,
                        'Case 3: Available final size is not 0.')
        self.assertEqual(matching_pop_size, extracted_block.get_population_size(pop_template),
                        'Case 3: Extracted block does not represent template.')
        self.assertEqual(available_original_size, available_final_size + extracted_block_size,
                        'Case 3: Target block does not represent population template change.')
        self.assertTrue(verify_block_validity(target_block),
                        'Case 3: Target block is not valid.')
        self.assertTrue(verify_block_validity(extracted_block),
                        'Case 3: Extracted block is not valid.')  
        
    ### BlobFactory tests  
    ## BlobFactory.Generate
    def test_blob_factory_generate(self):
        """ Tests BlobFactory.Generate

            Generate returns a valid Blob with the defined population quantity and profile based on a BlockTemplate

            Case 1: 
                action : Create a Blob from a BlobFactory with 3 sampled properties(buckets/characteristics) and 1 traceable property
                result : Blob should be valid, with 3 sampled properties and 1 traceable property
                
            Case 2: 
                action : Adds a new sampled property to the BlobFactory and creates a new Blob
                result : New Blob should be valid, with 4 sampled properties and 1 traceable property
                         The first Blob should not be affected by the changes in the template.
                         
            Case 3: 
                action : Adds a new traceable property to the BlobFactory and creates a new Blob
                result : New Blob should be valid, with 4 sampled properties and 2 traceable property
                         The first Blob should not be affected by the changes in the template.
                         
            Case 2: 
                action : Adds a new sampled and a new traceable property to the BlobFactory and creates a new Blob
                result : New Blob should be valid, with 5 sampled properties and 2 traceable property
                         The first Blob should not be affected by the changes in the template.
                         
            Case 5: 
                action : Creates a new Blob from a BlobFactory with population 0
                result : Blob should be None.

        """
        
        # Create a BlockTemplate with 3 characteristics
        block_template = BlockTemplate()
        block_template.add_bucket('characteristic_A', ('value_A1', 'value_A2', 'value_A3'))
        block_template.add_bucket('characteristic_B', ('value_B1', 'value_B2',))
        block_template.add_bucket('characteristic_C', ('value_C1', 'value_C2', 'value_C3'))
        block_template.add_traceable_property('traceable_A', 0)
        blob_factory = BlobFactory(block_template)
        
        # Case 1:
        # Create a Blob using the BlobFactory
        blob1 = blob_factory.Generate(0, 300)
        blob1_size = blob1.get_population_size()
            
        # Compare size, sampled properties count and verify block validity
        self.assertEqual(blob1_size, 300,
                        'Case 1 Target Blob size is not the correct amount.')
        self.assertEqual(len(blob1.sampled_properties.buckets.keys()), 3,
                        'Case 1 Target Blob sampled properties count is not the correct amount.')
        self.assertEqual(len(blob1.traceable_properties.keys()), 1,
                        'Case 1 Target Blob traceable properties count is not the correct amount.')
        self.assertTrue(verify_blob_validity(blob1),
                        'Case 1 Target Blob is not valid.')
                       
        # Case 2:
        # Adds a new sampled property/bucket to the BlobFactory.BlockTemplate and creates a new Blob
        blob_factory.block_template.add_bucket('characteristic_D', ('value_D1', 'value_D2'))
        blob2 = blob_factory.Generate(0, 50)
        blob2_size = blob2.get_population_size()
        
        # Compare size, sampled properties count and verify block validity
        self.assertEqual(blob2_size, 50,
                        'Case 2 Target Blob size is not the correct amount.')
        self.assertEqual(len(blob2.sampled_properties.buckets.keys()), 4,
                        'Case 2 Target Blob sampled properties count is not the correct amount.')
        self.assertEqual(len(blob2.traceable_properties.keys()), 1,
                        'Case 2 Target Blob traceable properties count is not the correct amount.')
        self.assertEqual(len(blob1.sampled_properties.buckets.keys()), 3,
                        'Case 2 Original Blob sampled properties count is not the correct amount.')
        self.assertEqual(len(blob1.traceable_properties.keys()), 1,
                        'Case 2 Original Blob traceable properties count is not the correct amount.')
        self.assertTrue(verify_blob_validity(blob2),
                        'Case 2 Target Blob is not valid.')
        
        # Case 3:
        # Adds a new traceable property to the BlobFactory.BlockTemplate and creates a new Blob
        blob_factory.block_template.add_traceable_property('traceable_B', 'abc')
        blob3 = blob_factory.Generate(0, 20)
        blob3_size = blob3.get_population_size()
        
        # Compare size, sampled properties count and verify block validity
        self.assertEqual(blob3_size, 20,
                        'Case 3 Target Blob size is not the correct amount.')
        self.assertEqual(len(blob3.sampled_properties.buckets.keys()), 4,
                        'Case 3 Target Blob sampled properties count is not the correct amount.')
        self.assertEqual(len(blob3.traceable_properties.keys()), 2,
                        'Case 3 Target Blob traceable properties count is not the correct amount.')
        self.assertEqual(len(blob1.sampled_properties.buckets.keys()), 3,
                        'Case 3 Original Blob sampled properties count is not the correct amount.')
        self.assertEqual(len(blob1.traceable_properties.keys()), 1,
                        'Case 3 Original Blob traceable properties count is not the correct amount.')
        self.assertTrue(verify_blob_validity(blob3),
                        'Case 3 Target Blob is not valid.')
        
        # Case 4:
        # Adds a new sampled property/bucket and a traceable property directly to the BlockTemplate and creates a new Blob
        block_template.add_bucket('characteristic_E', ('value_E1', 'value_E2'))
        block_template.add_traceable_property('traceable_c', { 0, 1, 2})
        blob4 = blob_factory.Generate(0, 500)
        blob4_size = blob4.get_population_size()
        
        # Compare size, sampled properties count and verify block validity
        self.assertEqual(blob4_size, 500,
                        'Case 4 Target Blob size is not the correct amount.')
        self.assertEqual(len(blob4.sampled_properties.buckets.keys()), 5,
                        'Case 4 Target Blob sampled properties count is not the correct amount.')
        self.assertEqual(len(blob4.traceable_properties.keys()), 3,
                        'Case 4 Target Blob traceable properties count is not the correct amount.')
        self.assertEqual(len(blob1.sampled_properties.buckets.keys()), 3,
                        'Case 4 Original Blob sampled properties count is not the correct amount.')
        self.assertEqual(len(blob1.traceable_properties.keys()), 1,
                        'Case 4 Original Blob traceable properties count is not the correct amount.')
        self.assertTrue(verify_blob_validity(blob4),
                        'Case 4 Target Blob is not valid.')
        
        # Case 5:
        # Creates a Blob with 0 population - Should be None
        blob5 = blob_factory.Generate(0, 0)

        # Verify Blob validity
        self.assertEqual(blob5, None, 'Case 5 Target Blob should be None.')

     ## BlobFactory.GenerateEmpty    
    def test_blob_factory_generate_empty(self):
        """ Tests BlobFactory.GenerateEmpty

            Generate returns a valid Blob with population 0

            Case 1: 
                action : Create a Blob from a BlobFactory using GenerateEmpty
                result : Blob should be valid.
        """
        
        # Create a BlockTemplate with 3 characteristics
        block_template = BlockTemplate()
        block_template.add_bucket('characteristic_A', ('value_A1', 'value_A2', 'value_A3'))
        block_template.add_bucket('characteristic_B', ('value_B1', 'value_B2',))
        block_template.add_bucket('characteristic_C', ('value_C1', 'value_C2', 'value_C3'))
        blob_factory = BlobFactory(block_template)

        # Case 1:
        # Create a PropertyBlock using the BlockTemplate
        blob_1 = blob_factory.GenerateEmpty(0)
        blob_1_size = blob_1.get_population_size()
        
        # Compare size, PropertyBuckets count and verify block validity
        self.assertEqual(blob_1_size, 0,
                        'Case 1 Target Blob size is not the correct amount.')
        self.assertEqual(len(blob_1.sampled_properties.buckets.keys()), 3,
                        'Case 1 Target Blob sampled properties count is not the correct amount.')
        self.assertTrue(verify_blob_validity(blob_1),
                        'Case 1 Target Blob is not valid.')
    
    ## BlobFactory.GenerateProfile
    def test_blob_factory_generate_profile(self):
        """ Tests BlobFactory.GenerateProfile

            GenerateProfile returns a valid Blob with the defined population quantity and, traceable and sampled properties

            Case 1: 
                action : Create a Blob from a BlobFactory using a Profile.
                         The population requested is equal the highest sum defined in a single 
                         characteristic.
                result : Blob should be valid.
                         Characteristics with fewer defined people should be randomly dsitributed.
                
            Case 2: 
                action : Create a Blob from a BlobFactory using a Profile.
                         The population requested is double than the highest sum defined in a single 
                         characteristic.
                result : New Blob should be valid.
                         Remainind population should be randomly distributed.
                         
            Case 3: 
                action : Create a Blob from a BlobFactory using a Profile.
                         The population requested is half than the highest sum defined in a single            
                         characteristic.
                result : Blob should be properly distributed according to proportion requested.
                
            Case 4: 
                action : Create a Blob from a BlobFactory using a Profile.
                         The population requested is 0.
                result : Blob should be None


        """
        
        # Create a BlockTemplate with 6 characteristics
        block_template = BlockTemplate()
        block_template.add_bucket('characteristic_A', ('value_A1', 'value_A2', 'value_A3'))
        block_template.add_bucket('characteristic_B', ('value_B1', 'value_B2', 'value_B3'))
        block_template.add_bucket('characteristic_C', ('value_C1', 'value_C2', 'value_C3'))
        block_template.add_bucket('characteristic_D', ('value_D1', 'value_D2', 'value_D3'))
        block_template.add_bucket('characteristic_E', ('value_E1', 'value_E2'))
        block_template.add_bucket('characteristic_F', ('value_F1', 'value_F2'))
        block_template.add_traceable_property('traceable_A', 0)
        blob_factory = BlobFactory(block_template)
        
        # Case 1:
        # Creates a pop_profile dict with the following goals per characteristic:
        # A: Total population distributed through all values
        # B: Total population distributed in a two or more values, but not all - others sould be 0
        # C: Total population distributed in a single value - others sould be 0
        # D: Partial population in a single value - remaining population distributed in other values
        # E: Empty dict - should be randomly distributed
        # F: Not in profile - should be randomly distributed
        pop_profile = {'characteristic_A' : {'value_A1' : 30, 'value_A2' : 50, 'value_A3': 20},
                        'characteristic_B' : {'value_B1' : 40, 'value_B2': 60},
                        'characteristic_C' : {'value_C1' : 100},
                        'characteristic_D' : {'value_D1' : 30},
                        'characteristic_E' : {}}
        
        # Case 1:
        # Create a Blob using the BlobFactory. 100 is the highest sum defined in a single characteristic (A, B and C) 
        blob1 = blob_factory.GenerateProfile(0, 100, pop_profile)
        blob1_size = blob1.get_population_size()
        values = blob1.sampled_properties.get_mapping_of_property_values()
        
        # Compare size, PropertyBuckets count and verify block validity
        self.assertTrue(verify_blob_validity(blob1),
                        'Case 1 Target Blob is not valid.')
        self.assertEqual(blob1_size, 100,
                        'Case 1 Target Blob size is not the correct amount.')
        self.assertEqual(len(blob1.sampled_properties.buckets.keys()), 6,
                        'Case 1 Target Blob sampled properties count is not the correct amount.')
        self.assertEqual(len(blob1.traceable_properties.keys()), 1,
                        'Case 1 Target Blob traceable properties count is not the correct amount.')
        
        # Verify that the population was properly distributed when all values are defined and equal the requested amount
        self.assertTrue(values[0] == [30,50,20], 'Case 1 Sampled property value is not the expected amount')
        self.assertTrue(values[1] == [40,60,0], 'Case 1 Sampled property value is not the expected amount')
        self.assertTrue(values[2] == [100,0,0], 'Case 1 Sampled property value is not the expected amount')
        
        # Verify that a value is as defined when the sum of all values is less than the requested amount
        self.assertTrue(values[3][0] == 30, 'Case 1 Sampled property value is not the expected amount')
        
        # Case 2:
        # Requested population is higher than the max defined value, the following behaviours should occur:
        # A: Population distributed through all values - minimum values of (30, 50, 20)
        # B: Remaining population distributed in the undefined values - equal to (40, 60, 100)
        # C: Remaining population distributed in the undefined values - ranges of (100, 0-100, 0-100)
        # D: Remaining population distributed in the undefined values - ranges of (30, 0-170, 0-170)
        # E: Empty dict - should be randomly distributed
        # F: Not in profile - should be randomly distributed
        pop_profile = {'characteristic_A' : {'value_A1' : 30, 'value_A2' : 50, 'value_A3': 20},
                        'characteristic_B' : {'value_B1' : 40, 'value_B2': 60},
                        'characteristic_C' : {'value_C1' : 100},
                        'characteristic_D' : {'value_D1' : 30},
                        'characteristic_E' : {}}
        
        # Create a Blob using the template. 200 is the more than the highest sum defined in a single characteristic (A, B and C)
        blob2 = blob_factory.GenerateProfile(0, 200, pop_profile)
        blob2_size = blob2.get_population_size()
        values = blob2.sampled_properties.get_mapping_of_property_values()
        
        # Compare size, PropertyBuckets count and verify block validity
        self.assertTrue(verify_blob_validity(blob2),
                        'Case 2 Target Blob is not valid.')
        self.assertEqual(blob2_size, 200,
                        'Case 2 Target Blob size is not the corrected amount.')
        self.assertEqual(len(blob2.sampled_properties.buckets.keys()), 6,
                        'Case 1 Target Blob sampled properties count is not the correct amount.')
        self.assertEqual(len(blob2.traceable_properties.keys()), 1,
                        'Case 1 Target Blob traceable properties count is not the correct amount.')
        
        # Verify that the population was properly distributed when all values are defined
        self.assertTrue(values[0][0] >= 30, 'Case 2 Sampled property value is not the expected amount')
        self.assertTrue(values[0][1] >= 50, 'Case 2 Sampled property value is not the expected amount')
        self.assertTrue(values[0][2] >= 20, 'Case 2 Sampled property value is not the expected amount')
        
        # Verify that defined values remained the same when there is a undefined value
        self.assertTrue(values[1] == [40,60,100], 'Case 2 Sampled property value is not the expected amount')
        self.assertTrue(values[2][0] == 100, 'Case 2 Sampled property value is not the expected amount')
        self.assertTrue(values[3][0] == 30, 'Case 2 Sampled property value is not the expected amount')
        
        # Verify that undefined values are the expected amount after distribution
        self.assertTrue(values[2][1] >= 0 and values[2][1] <= 100, 
                        'Case 2 Sampled property value is not the expected amount')
        self.assertTrue(values[2][2] >= 0 and values[2][2] <= 100,
                        'Case 2 Sampled property value is not the expected amount')
        self.assertTrue(values[3][1] >= 0 and values[3][1] <= 170,
                        'Case 2 Sampled property value is not the expected amount')
        self.assertTrue(values[3][2] >= 0 and values[3][2] <= 170,
                        'Case 2 Sampled property value is not the expected amount')
        
        
        # Case 3:
        # Requested population is fewer than the max defined value, the following behaviours should occur:
        # A: Population distributed through all values - maximum values of (20, 20, 20)
        # B: Defined values reduced to fit requested amount - ranges of (0-20, 0-20, 0)
        # C: Defined values reduced to fit requested amount - equals to (20, 0, 0)
        # D: Defined values reduced to fit requested amount - equals of (30, 0-170, 0-170)
        # E: Empty dict - should be randomly distributed
        # F: Not in profile - should be randomly distributed
        pop_profile = {'characteristic_A' : {'value_A1' : 30, 'value_A2' : 50, 'value_A3': 20},
                        'characteristic_B' : {'value_B1' : 40, 'value_B2': 60},
                        'characteristic_C' : {'value_C1' : 100},
                        'characteristic_D' : {'value_D1' : 30},
                        'characteristic_E' : {}}
        
        # Create a PropertyBlock using the template. 20 is the lower then the minimum defined in a single characteristic (D)
        blob3 = blob_factory.GenerateProfile(0, 20, pop_profile)
        blob3_size = blob3.get_population_size()
        values = blob3.sampled_properties.get_mapping_of_property_values()
        
        # Compare size, PropertyBuckets count and verify block validity
        self.assertTrue(verify_blob_validity(blob3),
                        'Case 3 Target Blob is not valid.')
        self.assertEqual(blob3_size, 20,
                        'Case 3 Target Blob size is not the corrected amount.')
        self.assertEqual(len(blob3.sampled_properties.buckets.keys()), 6,
                        'Case 3 Target Blob sampled properties count is not the correct amount.')
        self.assertEqual(len(blob3.traceable_properties.keys()), 1,
                        'Case 3 Target Blob traceable properties count is not the correct amount.')
        
        # Verify that the population was properly distributed when all values are defined
        self.assertTrue(values[0][0] <= 20, 'Case 3 Sampled property value is not the expected amount')
        self.assertTrue(values[0][1] <= 20, 'Case 3 Sampled property value is not the expected amount')
        self.assertTrue(values[0][2] <= 20, 'Case 3 Sampled property value is not the expected amount')
        self.assertTrue(values[1][0] <= 20, 'Case 3 Sampled property value is not the expected amount')
        self.assertTrue(values[1][1] <= 20, 'Case 3 Sampled property value is not the expected amount')
        
        # Verify that defined values remained the same when there is a undefined value
        self.assertTrue(values[1][2] == 0, 'Case 3 Sampled property value is not the expected amount')
        self.assertTrue(values[2] == [20,0,0], 'Case 3 Sampled property value is not the expected amount')
        self.assertTrue(values[3] == [20,0,0], 'Case 3 Sampled property value is not the expected amount')
        
        
        # Case 4:
        # Requested 0 population:
        blob4 = blob_factory.GenerateProfile(0, 0, pop_profile)

        # Verify block validity
        self.assertEqual(blob4, None, 'Case 4 Blob should be None.')
    
    
    def test_block_template_add_traceable_property(self):
        """ Tests BlockTemplate.Generate

            Generate returns a valid PropertyBlock with the defined population quantity

            Case 1: 
                action : Create a PropertyBlock from a BlockTemplate
                result : PropertyBlock should be valid.
                
            Case 2: 
                action : Change the previous template and create another PropertyBlock
                result : New PropertyBlock should be valid.
                         The first PropertyBlock should not be affected by the changes in the template.
                         
            Case 3: 
                action : Creates a third PropertyBlock from a BlockTemplate with population 0
                result : PropertyBlock should be None.

        """
        
        # Create a BlockTemplate with 3 characteristics
        block_template = BlockTemplate()
        block_template.add_bucket('characteristic_A', ('value_A1', 'value_A2', 'value_A3'))
        block_template.add_bucket('characteristic_B', ('value_B1', 'value_B2',))
        block_template.add_bucket('characteristic_C', ('value_C1', 'value_C2', 'value_C3'))
        block_template.add_traceable_property('traceable_A', 0)
        block_template.add_traceable_property('sir_state', 'susceptible')
        
        # Case 1:
        # Create a PropertyBlock using the BlockTemplate
        block1 = block_template.Generate(300)
        block1_size = block1.get_population_size()
        
        # Compare size, PropertyBuckets count and verify block validity
        self.assertEqual(block1_size, 300,
                        'Case 1 Target block size is not the correct amount.')
        self.assertEqual(len(block1.buckets.keys()), 3,
                        'Case 1 Target block bucket count is not the correct amount.')
        self.assertTrue(verify_block_validity(block1),
                        'Case 1 Target block is not valid.')
                       
        # Case 2:
        # Adds a new bucket to the BlockTemplate and creates a new PropertyBlock
        block_template.add_bucket('characteristic_D', ('value_D1', 'value_D2'))
        block2 = block_template.Generate(50)
        block2_size = block2.get_population_size()
        
        # Compare size, PropertyBuckets count and verify block validity
        self.assertEqual(block2_size, 50,
                        'Case 2 Target block population size is not the correct amount.')
        self.assertEqual(len(block2.buckets.keys()), 4,
                        'Case 2 Target block bucket count is not the correct amount.')
        self.assertEqual(len(block1.buckets.keys()), 3,
                        'Case 2 Previous block was affected by pop_template changes')
        self.assertTrue(verify_block_validity(block2),
                        'Case 2 Target block is not valid.')
        
        # Case 3:
        # Creates a PropertyBlock with 0 population - Should be None
        block3 = block_template.Generate(0)

        # Verify block validity
        self.assertEqual(block3, None, 'Case 3 Target block should be None.')
    
    ### Blob tests
    ## Blob.consume_blob
    def test_blob_consume_blob(self):
        """Tests Blob.consume_blob
        
        A Blob can consume another when their traceable properties match. Blobs should remain valid after the operation.
        
        Case 1: 
            action : A blob consumes an auxiliary blob with the same traceable properties
            result : All population of consumed blob should be in the consuming blob.
                     Both blobs should be valid.
                     
        Case 2: 
            action : A blob consumes an auxiliary blob with different traceable properties
            result : Operation does nothing and populations remain the same.
                     Both blobs should be valid.
        """

        # Set blob factory
        block_template = BlockTemplate()
        block_template.add_bucket('characteristic_A', ('value_A1', 'value_A2', 'value_A3'))
        block_template.add_bucket('characteristic_B', ('value_B1', 'value_B2',))
        block_template.add_bucket('characteristic_C', ('value_C1', 'value_C2', 'value_C3'))
        block_template.add_traceable_property('traceable_A', 0)
        blob_factory = BlobFactory(block_template)

        # Case 1:
        # Creates 2 Blobs with the same traceable properties
        blob_1 = blob_factory.Generate(0, 100)
        blob_2 = blob_factory.Generate(0, 50)
        
        # Get original Blob sizes
        blob_1_original_size = blob_1.get_population_size()
        blob_2_original_size = blob_2.get_population_size()

        # Blob 1 try to consume Blob 2 - it should succeed
        blob_1.consume_blob(blob_2)

        # Get final Blob sizes
        blob_1_final_size = blob_1.get_population_size()
        blob_2_final_size = blob_2.get_population_size()

        # assets that Blobs are valid and the consume_blob succeeded
        self.assertTrue(verify_blob_validity(blob_1), 'Case 1 Blob 1 is not valid.')
        self.assertTrue(verify_blob_validity(blob_2), 'Case 1 Blob 2 is not valid.')
        self.assertTrue(blob_1.compare_traceable_properties_to_other(blob_2), 
                        'Case 1 Traceable Properties do not match')
        self.assertEqual(blob_1_final_size, blob_1_original_size + blob_2_original_size, 
                         'Case 1 Blob 1 final size is not the total population.')
        self.assertEqual(blob_2_original_size, blob_2_final_size, 
                         'Case 1 Blob 2 final size was altered.')
        
        # Case 2:
        # Creates 2 Blobs with differente traceable properties
        blob_1 = blob_factory.Generate(0, 100)
        block_template.add_traceable_property('traceable_A', 1)
        blob_2 = blob_factory.Generate(0, 50)
        
        # Get original Blob sizes
        blob_1_original_size = blob_1.get_population_size()
        blob_2_original_size = blob_2.get_population_size()

        # Blob 1 try to consume Blob 2 - it should fail
        blob_1.consume_blob(blob_2)

        # Get final Blob sizes
        blob_1_final_size = blob_1.get_population_size()
        blob_2_final_size = blob_2.get_population_size()

        # assets that Blobs are valid and the consume_blob failed
        self.assertTrue(verify_blob_validity(blob_1), 'Case 2 Blob 1 is not valid.')
        self.assertTrue(verify_blob_validity(blob_2), 'Case 2 Blob 2 is not valid.')
        self.assertTrue(not blob_1.compare_traceable_properties_to_other(blob_2), 
                        'Case 2 Traceable Properties match when they should not')
        self.assertEqual(blob_1_final_size, blob_1_original_size, 
                         'Case 2 Blob 1 final size was altered.')
        self.assertEqual(blob_2_original_size, blob_2_final_size, 
                         'Case 2 Blob 2 final was altered.')
   
    ## Blob.split_blob - unbalanced population in profile 
    def test_blob_split_blob_unbalanced_population(self):
        """Tests Blob.split_blob
        
        Blobs should remain valid after the operation.
        Sum of population sizes should remain the same.

        Case 1: 
            action : Splits less population than avaiable from origin blob. 
            result : Both blobs should be valid.
                     Sum of blob sizes is equal to original blob size.
                     Split blob size equal to split quantity.
        
        Case 2: 
            action : Splits equal population as avaiable from origin blob.  
            result : Both blobs should be valid.
                     Sum of blob sizes is equal to original blob size.
                     Split blob size equal to origin blob size.
                     Split blob size equal to split blob quantity.
                     New origin blob size should be 0.

        Case 3: 
            action : Splits more population than avaiable from origin blob. 
            result : Both blobs should be valid.
                     Sum of blob sizes is equal to original blob size.
                     Split blob size equal to origin blob size.
                     Origin blob size should be 0.
        """
        # get blob factory
        block_template = BlockTemplate()
        block_template.add_bucket('characteristic_A', ('value_A1', 'value_A2', 'value_A3'))
        block_template.add_bucket('characteristic_B', ('value_B1', 'value_B2', 'value_B3'))
        blob_factory = BlobFactory(block_template)

        pop_profile = {'characteristic_A' : {'value_A1' : 100}}

        # Case 1:
        blob_1 = blob_factory.GenerateProfile(0, 100, pop_profile)
        
        # get orginal size
        old_blob_1_size = blob_1.get_population_size()
        # split blob
        blob_2 = blob_1.split_blob(50)
        # compare original size with blob + blob2 sizes
        new_blob_1_size = blob_1.get_population_size()
        new_blob_2_size = blob_2.get_population_size()

        # verify blob validity for blob and blob2
        self.assertTrue(verify_blob_validity(blob_1),
        'Case 1: Blob 1 is not valid.')
        self.assertTrue(verify_blob_validity(blob_2),
        'Case 1: Blob 2 is not valid.')
        self.assertEqual(old_blob_1_size, new_blob_1_size + new_blob_2_size,
        'Case 1: Old blob 1 size is not the sum of new blob 1 size and blob 2 size.')
        self.assertEqual(50, new_blob_2_size,
        'Case 1: Split blob quantity does not match blob 2 size.')

        # Case 2:
        blob_1 = blob_factory.GenerateProfile(0, 100, pop_profile)
        
        # get orginal size
        old_blob_1_size = blob_1.get_population_size()
        # split blob
        blob_2 = blob_1.split_blob(100)
        # compare original size with blob + blob2 sizes
        new_blob_1_size = blob_1.get_population_size()
        new_blob_2_size = blob_2.get_population_size()
        # verify blob validity for blob and blob2


        self.assertTrue(verify_blob_validity(blob_1),
        'Case 2: Blob 1 is not valid.')
        self.assertTrue(verify_blob_validity(blob_2),
        'Case 2: Blob 2 is not valid.')
        self.assertEqual(old_blob_1_size, new_blob_1_size + new_blob_2_size,
        'Case 2: Old blob 1 size is not the sum of new blob 1 size and blob 2 size.')
        self.assertEqual(100, new_blob_2_size,
        'Case 2: Split blob quantity does not match blob 2 size.')
        self.assertEqual(0, new_blob_1_size,
        'Case 2: Blob 1 new size is not 0.')
        self.assertEqual(old_blob_1_size, new_blob_2_size,
        'Case 2: Blob 2 size is not equal to old blob 1 size.')

        # Case 3:
        blob_1 = blob_factory.GenerateProfile(0, 100, pop_profile)
        
        # get orginal size
        old_blob_1_size = blob_1.get_population_size()
        # split blob
        blob_2 = blob_1.split_blob(300)
        # compare original size with blob + blob2 sizes
        new_blob_1_size = blob_1.get_population_size()
        new_blob_2_size = blob_2.get_population_size()
        # verify blob validity for blob and blob2
        self.assertTrue(verify_blob_validity(blob_1),
        'Case 3: Blob 1 is not valid.')
        self.assertTrue(verify_blob_validity(blob_2),
        'Case 3: Blob 2 is not valid.')
        self.assertEqual(old_blob_1_size, new_blob_1_size + new_blob_2_size,
        'Case 3: Old blob 1 size is not the sum of new blob 1 size and blob 2 size.')
        self.assertEqual(0, new_blob_1_size,
        'Case 3: Blob 1 new size is not 0.')
        self.assertEqual(old_blob_1_size, new_blob_2_size,
        'Case 3: Blob 2 size is not equal to old blob 1 size.')


    ## split blob
    def test_blob_split_blob_balanced_population(self):
        """Tests Blob.split_blob
        
        Blobs should remain valid after the operation.
        Sum of population sizes should remain the same.

        Case 1: 
            action : Splits less population than avaiable from origin blob. 
            result : Both blobs should be valid.
                     Sum of blob sizes is equal to original blob size.
                     Split blob size equal to split quantity.
        
        Case 2: 
            action : Splits equal population as avaiable from origin blob.  
            result : Both blobs should be valid.
                     Sum of blob sizes is equal to original blob size.
                     Split blob size equal to origin blob size.
                     Split blob size equal to split blob quantity.
                     New origin blob size should be 0.

                     
        Case 3: 
            action : Splits more population than avaiable from origin blob. 
            result : Both blobs should be valid.
                     Sum of blob sizes is equal to original blob size.
                     Split blob size equal to origin blob size.
                     Origin blob size should be 0.
        """
        # get blob factory
        block_template = BlockTemplate()
        block_template.add_bucket('characteristic_A', ('value_A1', 'value_A2', 'value_A3'))
        block_template.add_bucket('characteristic_B', ('value_B1', 'value_B2', 'value_B3'))
        blob_factory = BlobFactory(block_template)

        pop_profile = {'characteristic_A' : {'value_A1' : 100, 'value_A2' : 100}}
        blob_factory = BlobFactory(block_template)
        pop_template = PopTemplate()

        # Case 1:
        blob_1 = blob_factory.GenerateProfile(0, 100, pop_profile)
        
        # get orginal size
        old_blob_1_size = blob_1.get_population_size()
        # split blob
        blob_2 = blob_1.split_blob(50, pop_template)
        # compare original size with blob + blob2 sizes
        new_blob_1_size = blob_1.get_population_size()
        new_blob_2_size = blob_2.get_population_size()

        # verify blob validity for blob and blob2
        self.assertTrue(verify_blob_validity(blob_1),
        'Case 1: Blob 1 is not valid.')
        self.assertTrue(verify_blob_validity(blob_2),
        'Case 1: Blob 2 is not valid.')
        self.assertEqual(old_blob_1_size, new_blob_1_size + new_blob_2_size,
        'Case 1: Old blob 1 size is not the sum of new blob 1 size and blob 2 size.')
        self.assertEqual(50, new_blob_2_size,
        'Case 1: Split blob quantity does not match blob 2 size.')

        # Case 2:
        blob_1 = blob_factory.GenerateProfile(0, 100, pop_profile)
        
        # get orginal size
        old_blob_1_size = blob_1.get_population_size()
        # split blob
        blob_2 = blob_1.split_blob(200, pop_template)
        # compare original size with blob + blob2 sizes
        new_blob_1_size = blob_1.get_population_size()
        new_blob_2_size = blob_2.get_population_size()
        # verify blob validity for blob and blob2


        self.assertTrue(verify_blob_validity(blob_1),
        'Case 2: Blob 1 is not valid.')
        self.assertTrue(verify_blob_validity(blob_2),
        'Case 2: Blob 2 is not valid.')
        self.assertEqual(old_blob_1_size, new_blob_1_size + new_blob_2_size,
        'Case 2: Old blob 1 size is not the sum of new blob 1 size and blob 2 size.')
        self.assertEqual(100, new_blob_2_size,
        'Case 2: Split blob quantity does not match blob 2 size.')
        self.assertEqual(0, new_blob_1_size,
        'Case 2: Blob 1 new size is not 0.')
        self.assertEqual(old_blob_1_size, new_blob_2_size,
        'Case 2: Blob 2 size is not equal to old blob 1 size.')

        # Case 3:
        blob_1 = blob_factory.GenerateProfile(0, 100, pop_profile)
        
        # get orginal size
        old_blob_1_size = blob_1.get_population_size()
        # split blob
        blob_2 = blob_1.split_blob(300, pop_template)
        # compare original size with blob + blob2 sizes
        new_blob_1_size = blob_1.get_population_size()
        new_blob_2_size = blob_2.get_population_size()
        # verify blob validity for blob and blob2
        self.assertTrue(verify_blob_validity(blob_1),
        'Case 3: Blob 1 is not valid.')
        self.assertTrue(verify_blob_validity(blob_2),
        'Case 3: Blob 2 is not valid.')
        self.assertEqual(old_blob_1_size, new_blob_1_size + new_blob_2_size,
        'Case 3: Old blob 1 size is not the sum of new blob 1 size and blob 2 size.')
        self.assertEqual(0, new_blob_1_size,
        'Case 3: Blob 1 new size is not 0.')
        self.assertEqual(old_blob_1_size, new_blob_2_size,
        'Case 3: Blob 2 size is not equal to old blob 1 size.')
                
    ## Blob.grab_population - without template
    def test_blob_grab_population_without_template(self):
        """Tests Blob.grab_population
        
        Blobs should remain valid after the operation.
        Sum of population sizes should remain the same.

        Case 1: 
            action : Grabs less population than available in the target blob.
            result : Both blobs should be valid.
                     Sum of blob sizes is equal to original blob size.
                     Grabbed blob size equal to grab quantity.
                     Grabbed blob and original blob are not the same blob.
        
        Case 2: 
            action : Grabs as much population as available in the blob.
            result : Both blobs should be valid.
                     Split blob size equal to origin blob size.
                     Split blob size equal to grab population quantity.
                     Both blobs are the same.
                     
        Case 3: 
            action : Grabs more population than available than available.
            result : Both blobs should be valid.
                     Split blob size equal to origin blob size.
                     Both blobs are the same.
                     
        """
        
        # Set a BlobFactory
        block_template = BlockTemplate()
        block_template.add_bucket('characteristic_A', ('value_A1', 'value_A2', 'value_A3'))
        block_template.add_bucket('characteristic_B', ('value_B1', 'value_B2',))
        block_template.add_bucket('characteristic_C', ('value_C1', 'value_C2', 'value_C3'))
        block_template.add_traceable_property('traceable_A', 0)
        blob_factory = BlobFactory(block_template)

        # Case 1:
        # Create a Blob using the BlobFactory
        blob_1 = blob_factory.Generate(0, 200)
        blob_1_original_size = blob_1.get_population_size()
        
        # Grab population from Blob1
        blob_2 = blob_1.grab_population(50)

        # Get final Blob sizes
        blob_1_final_size = blob_1.get_population_size()
        blob_2_final_size = blob_2.get_population_size()

        # Verify Blob validity and sizes
        self.assertTrue(verify_blob_validity(blob_1),
        'Case 1: Blob 1 is not valid.')
        self.assertTrue(verify_blob_validity(blob_2),
        'Case 1: Blob 2 is not valid.')
        self.assertEqual(blob_1_original_size, blob_1_final_size + blob_2_final_size,
        'Case 1: Old blob 1 size is not the sum of new blob 1 size and blob 2 size.')
        self.assertEqual(50, blob_2_final_size,
        'Case 1: Grabbed quantity does not match blob 2 size.')
        self.assertTrue(blob_1.blob_id is not blob_2.blob_id,
        'Case 1: Blobs are the same.')

        # Case 2:
        # Create a Blob using the BlobFactory
        blob_1 = blob_factory.Generate(0, 200)
        blob_1_original_size = blob_1.get_population_size()
        
        # Grab population from Blob1
        blob_2 = blob_1.grab_population(200)

        # Get final Blob sizes
        blob_1_final_size = blob_1.get_population_size()
        blob_2_final_size = blob_2.get_population_size()

        # Verify Blob validity and sizes
        self.assertTrue(verify_blob_validity(blob_1),
        'Case 2: Blob 1 is not valid.')
        self.assertTrue(verify_blob_validity(blob_2),
        'Case 2: Blob 2 is not valid.')
        self.assertEqual(200, blob_2_final_size,
        'Case 2: Grabbed quantity does not match blob 2 size.')
        self.assertEqual(blob_1_final_size, blob_2_final_size,
        'Case 2: Blob sizes are not the same.')
        self.assertTrue(blob_1.blob_id is blob_2.blob_id,
        'Case 2: Blobs are not the same.')

        # Case 3:
        # Create a Blob using the BlobFactory
        blob_1 = blob_factory.Generate(0, 200)
        blob_1_original_size = blob_1.get_population_size()
        
        # Grab population from Blob1
        blob_2 = blob_1.grab_population(300)

        # Get final Blob sizes
        blob_1_final_size = blob_1.get_population_size()
        blob_2_final_size = blob_2.get_population_size()

        # Verify Blob validity and sizes
        self.assertTrue(verify_blob_validity(blob_1),
        'Case 3: Blob 1 is not valid.')
        self.assertTrue(verify_blob_validity(blob_2),
        'Case 3: Blob 2 is not valid.')
        self.assertEqual(blob_1_final_size, blob_2_final_size,
        'Case 3: Blob sizes are not the same.')
        self.assertTrue(blob_1.blob_id is blob_2.blob_id,
        'Case 3: Blobs are not the same.')
    
    ## Blob.grab_population - with template
    def test_blob_grab_population_with_template(self):
        """Tests Blob.grab_population
        
        Blobs should remain valid after the operation.
        Uses a PopTemplate to filter available population.
        Sum of population sizes should remain the same.

        Case 1: 
            action : Grabs less population than available in the target blob.
            result : Both blobs should be valid.
                     Sum of blob sizes is equal to original blob size.
                     Grabbed blob size equal to grab quantity.
                     Grabbed blob and original blob are not the same blob.
        
        Case 2: 
            action : Grabs as much population as available in the blob.
            result : Both blobs should be valid.
                     Split blob size equal to origin blob size.
                     Split blob size equal to grab population quantity.
                     Both blobs are the same.
                     
        Case 3: 
            action : Grabs more population than available than available.
            result : Both blobs should be valid.
                     Split blob size equal to origin blob size.
                     Both blobs are the same.
                     
         Case 4: 
            action : Tries to grab population with an unmatching template.
            result :  Original Blob should be valid. Second Blob should be None.

        """
        
        # Set a BlobFactory
        block_template = BlockTemplate()
        block_template.add_bucket('characteristic_A', ('value_A1', 'value_A2', 'value_A3'))
        block_template.add_bucket('characteristic_B', ('value_B1', 'value_B2',))
        block_template.add_bucket('characteristic_C', ('value_C1', 'value_C2', 'value_C3'))
        block_template.add_traceable_property('traceable_A', 0)
        blob_factory = BlobFactory(block_template)

        #Set a PopTemplate
        pop_template = PopTemplate()
        pop_template.set_sampled_property('characteristic_A', ['value_A1', 'value_A2'])
        pop_template.set_traceable_property('traceable_A', {0, 1})

        # Case 1:
        # Create a Blob using the BlobFactory
        blob_1 = blob_factory.Generate(0, 200)
        blob_1_available_size = blob_1.get_population_size(pop_template)
        blob_1_original_size = blob_1.get_population_size()
        
        # Grab population from Blob1
        blob_2 = blob_1.grab_population(blob_1_available_size // 2, pop_template)

        # Get final Blob sizes
        blob_1_final_size = blob_1.get_population_size()
        blob_1_final_available_size = blob_1.get_population_size(pop_template)
        blob_2_final_size = blob_2.get_population_size()

        # Verify Blob validity and sizes
        self.assertTrue(verify_blob_validity(blob_1),
        'Case 1: Blob 1 is not valid.')
        self.assertTrue(verify_blob_validity(blob_2),
        'Case 1: Blob 2 is not valid.')
        self.assertTrue(blob_1.compare_traceable_properties_to_template(pop_template), 'Case 1: Blob does not match with Template')
        self.assertTrue(blob_2.compare_traceable_properties_to_template(pop_template), 'Case 1: Blob does not match with Template')
        self.assertEqual(blob_1_original_size, blob_1_final_size + blob_2_final_size,
        'Case 1: Old blob 1 size is not the sum of new blob 1 size and blob 2 size.')
        self.assertEqual(blob_1_available_size//2, blob_2_final_size,
        'Case 1: Grabbed quantity does not match blob 2 size.')
        self.assertEqual(blob_1_available_size, blob_1_final_available_size + blob_2_final_size, 'Case 1: Final available populations does not match')
        self.assertTrue(blob_1.blob_id is not blob_2.blob_id,
        'Case 1: Blobs are the same.')

        # Case 2:
        # Create a Blob using the BlobFactory
        blob_1 = blob_factory.Generate(0, 200)
        blob_1_available_size = blob_1.get_population_size(pop_template)
        blob_1_original_size = blob_1.get_population_size()
        
        # Grab population from Blob1
        blob_2 = blob_1.grab_population(blob_1_available_size, pop_template)

        # Get final Blob sizes
        blob_1_final_size = blob_1.get_population_size()
        blob_1_final_available_size = blob_1.get_population_size(pop_template)
        blob_2_final_size = blob_2.get_population_size()

        # Verify Blob validity and sizes
        self.assertTrue(verify_blob_validity(blob_1),
        'Case 2: Blob 1 is not valid.')
        self.assertTrue(verify_blob_validity(blob_2),
        'Case 2: Blob 2 is not valid.')
        self.assertTrue(blob_1.compare_traceable_properties_to_template(pop_template), 'Case 2: Blob does not match with Template')
        self.assertTrue(blob_2.compare_traceable_properties_to_template(pop_template), 'Case 2: Blob does not match with Template')
        self.assertEqual(blob_1_available_size, blob_2_final_size,
        'Case 2: Grabbed quantity does not match blob 2 size.')
        self.assertEqual(blob_1_final_size, blob_1_original_size - blob_1_available_size,
        'Case 2: Blob sizes are not the same.')
        self.assertTrue(blob_1.blob_id is not blob_2.blob_id,
        'Case 2: Blobs are the same.')

        # Case 3:
        # Create a Blob using the BlobFactory
        blob_1 = blob_factory.Generate(0, 200)
        blob_1_available_size = blob_1.get_population_size(pop_template)
        blob_1_original_size = blob_1.get_population_size()
        
        # Grab population from Blob1
        blob_2 = blob_1.grab_population(blob_1_available_size * 2, pop_template)

        # Get final Blob sizes
        blob_1_final_size = blob_1.get_population_size()
        blob_1_final_available_size = blob_1.get_population_size(pop_template)
        blob_2_final_size = blob_2.get_population_size()


        # Verify Blob validity and sizes
        self.assertTrue(verify_blob_validity(blob_1),
        'Case 3: Blob 1 is not valid.')
        self.assertTrue(verify_blob_validity(blob_2),
        'Case 3: Blob 2 is not valid.')
        self.assertTrue(blob_1.compare_traceable_properties_to_template(pop_template), 'Case 3: Blob does not match with Template')
        self.assertTrue(blob_2.compare_traceable_properties_to_template(pop_template), 'Case 3: Blob does not match with Template')
        self.assertEqual(blob_1_available_size, blob_2_final_size,
        'Case 3: Grabbed quantity does not match blob 2 size.')
        self.assertEqual(blob_1_final_size, blob_1_original_size - blob_1_available_size,
        'Case 3: Blob sizes are not the same.')
        self.assertTrue(blob_1.blob_id is not blob_2.blob_id,
        'Case 3: Blobs are the same.')
        
        # Case 4:
        # Create a Blob using the BlobFactory
        blob_1 = blob_factory.Generate(0, 200)
        blob_1_available_size = blob_1.get_population_size(pop_template)
        blob_1_original_size = blob_1.get_population_size()

        # Change the PopTemplate and tries to grab population from Blob1
        pop_template.set_traceable_property('traceable_A', 2)

        blob_2 = blob_1.grab_population(blob_1_available_size * 2, pop_template)

        # Get final Blob sizes
        blob_1_final_size = blob_1.get_population_size()
        blob_1_final_available_size = blob_1.get_population_size(pop_template)

        # Verify Blob validity and sizes
        self.assertTrue(verify_blob_validity(blob_1), 'Case 4: Blob 1 is not valid.')
        self.assertTrue(blob_2 == None, 'Case 4: Blob 2 is not None.')
        self.assertTrue(not blob_1.compare_traceable_properties_to_template(pop_template), 'Case 4: Blob matches with Template')
        self.assertEqual(0, blob_1_final_available_size,
        'Case 4: There is population available after changing the template.')
        self.assertEqual(blob_1_final_size, blob_1_original_size,
        'Case 4: Blob 1 size changed.')



def suite():
    suite = unittest.TestSuite()

    # PropertyBucket tests
    suite.addTest(PopulationTests('test_property_bucket_add_bucket'))
    suite.addTest(PopulationTests('test_property_bucket_extract_without_key'))
    suite.addTest(PopulationTests('test_property_bucket_extract_with_key'))
    suite.addTest(PopulationTests('test_property_bucket_extract_with_key_list'))
    suite.addTest(PopulationTests('test_property_bucket_extract_with_key_set'))

    # BlockTemplate tests
    suite.addTest(PopulationTests('test_block_template_generate'))
    suite.addTest(PopulationTests('test_block_template_generate_empty'))
    suite.addTest(PopulationTests('test_block_template_generate_profile'))
    suite.addTest(PopulationTests('test_block_template_without_buckets'))
    
    # PropertyBlock tests
    suite.addTest(PopulationTests('test_property_block_add_block'))
    suite.addTest(PopulationTests('test_property_block_extract_without_key'))
    suite.addTest(PopulationTests('test_property_block_extract_with_key'))
    suite.addTest(PopulationTests('test_property_block_extract_with_key_list'))
    suite.addTest(PopulationTests('test_property_block_extract_with_key_set'))
     
    # BlobFactory tests 
    suite.addTest(PopulationTests('test_blob_factory_generate'))
    suite.addTest(PopulationTests('test_blob_factory_generate_empty'))
    suite.addTest(PopulationTests('test_blob_factory_generate_profile'))
    suite.addTest(PopulationTests('test_block_template_generate_empty'))
    
    # Blob tests
    suite.addTest(PopulationTests('test_blob_consume_blob'))
    suite.addTest(PopulationTests('test_blob_split_blob_unbalanced_population'))
    suite.addTest(PopulationTests('test_blob_split_blob_balanced_population'))
    suite.addTest(PopulationTests('test_blob_grab_population_without_template'))
    suite.addTest(PopulationTests('test_blob_grab_population_with_template'))
    
    # missing test_blob_split_blob_with_profile

    # missing get_population_size tests

    return suite

if __name__ == "__main__":
    runner = unittest.TextTestRunner()
    runner.run(suite())
