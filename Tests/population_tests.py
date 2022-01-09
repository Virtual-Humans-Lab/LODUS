import sys
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
    bucket_sizes  = set()
    for bucket in block.buckets.values():
        bucket_sizes.add(bucket.get_population_size())
    
    for bucket in block.buckets.values():
        for val in bucket.values.values():
            if val < 0:
                return False
    
    # there is only one value of bucket size
    return len(bucket_sizes) <= 1 and list(bucket_sizes)[0] >= 0

def verify_blob_validity(blob):
    """Verifies if all blocks of a blob have the same population for each of its buckets.
    
    A Blob is Valid if all of its PropertyBlocks are Valid,
        and its population size is greater or equal to 0.
    """
    results = []
    for char, block in blob.blocks.items():
        block_result = verify_block_validity(block)
        if block_result is False:
            print('\n\t\t\tBlock with chracteristic {0} is Invalid'.format(char))
        results.append(block_result)
    return all(results)


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
    def test_bucket_add_bucket(self):
        """Tests PropertyBucket.add_bucket"""

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
    def test_extract_bucket_without_key(self):
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
    def test_extract_bucket_with_key(self):
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
    def test_extract_bucket_with_key_list(self):
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
    def test_extract_bucket_with_key_set(self):
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

    #### PropertyBlock tests
    ## PropertyBlock.add_block
    def test_block_add_block(self):
        """ Tests PropertyBlock.add_block

            Final block size equals original block size plus added block size. 

            Case 1: 
                action : Add auxiliary block to target block.
                result : Target block should be valid.
                         Target block size equals original size plus added block size.

        """
        # get aux blocks
        block_template = BlockTemplate()
        block_template.add_bucket('bucket_1', ('prop_1_1', 'prop_1_2', 'prop_1_3'))
        block_template.add_bucket('bucket_2', ('prop_2_1', 'prop_2_2'))
        block_template.add_bucket('bucket_3', ('prop_3_1', 'prop_3_2', 'prop_3_3'))
        block_template.add_bucket('bucket_4', ('prop_4_1', 'prop_4_2'))

        target_block = block_template.Generate(300)
        add_block = block_template.Generate(50)

        # get size
        original_size = target_block.get_population_size()
        add_size = add_block.get_population_size()

        # add aux to block
        target_block.add_block(add_block)
        
        final_size = target_block.get_population_size()
        # compare size
        self.assertEqual(final_size, original_size + add_size,
                        'Target block size is not the sum of both blocks.')

        # verify block validity
        self.assertTrue(verify_block_validity(target_block),
                        'Target block is not valid.')

    ## initialize_buckets_profile
    def test_initialize_buckets_profile(self):
        # TODO
        pass

    ## remove
    def test_block_extract(self):
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
        # Get auxiliary blocks
        block_template = BlockTemplate()
        block_template.add_bucket('bucket_1', ('prop_1_1', 'prop_1_2', 'prop_1_3'))
        block_template.add_bucket('bucket_2', ('prop_2_1', 'prop_2_2'))
        block_template.add_bucket('bucket_3', ('prop_3_1', 'prop_3_2', 'prop_3_3'))
        block_template.add_bucket('bucket_4', ('prop_4_1', 'prop_4_2'))

        pop_profile = {'bucket_1' : {'prop_1_1' : 30, 'prop_1_2' : 50},
                       'bucket_2' : {'prop_2_1' : 50, 'prop_2_2' : 250}}

        # Get initial block sizes
        initial_block_size = 300
        
        # set up PopTemplate
        pop_template = PopTemplate()
        pop_template.set_property('bucket_1', 'prop_1_1')
        pop_template.set_property('bucket_2', 'prop_2_1')

        # Case 1
        target_block = block_template.GenerateProfile(initial_block_size, pop_profile)

        # block extract
        original_size = target_block.get_population_size()
        template_original_size = target_block.get_population_size(pop_template)
        extracted_block = target_block.extract(20, pop_template)
        extracted_block_size = extracted_block.get_population_size()
        final_size = target_block.get_population_size()
        template_final_size = target_block.get_population_size(pop_template)
        self.assertEqual(20, extracted_block_size,
                        'Case 1: Extracted block size is not the extracted quantity.')
        self.assertEqual(original_size, extracted_block_size + final_size ,
                        'Case 1: Block sizes do not add up.')
        self.assertEqual(20, extracted_block.get_population_size(pop_template),
                        'Case 1: Extracted block does not represent template.')
        self.assertEqual(template_original_size, template_final_size + extracted_block_size,
                        'Case 1: Target block does not represent population template change.')
        self.assertTrue(verify_block_validity(target_block),
                        'Case 1: Target block is not valid.')
        self.assertTrue(verify_block_validity(extracted_block),
                        'Case 1: Extracted block is not valid.')


        # Case 2
        target_block = block_template.GenerateProfile(initial_block_size, pop_profile)

        # block extract
        original_size = target_block.get_population_size()
        template_original_size = target_block.get_population_size(pop_template)
        extracted_block = target_block.extract(30, pop_template)
        extracted_block_size = extracted_block.get_population_size()
        final_size = target_block.get_population_size()
        template_final_size = target_block.get_population_size(pop_template)

        self.assertEqual(30, extracted_block_size,
                        'Case 2: Extracted block size is not the extracted quantity.')
        self.assertEqual(original_size, extracted_block_size + final_size ,
                        'Case 2: Block sizes do not add up.')
        self.assertEqual(30, extracted_block.get_population_size(pop_template),
                        'Case 2: Extracted block does not represent template.')
        self.assertEqual(template_original_size, template_final_size + extracted_block_size,
                        'Case 2: Target block does not represent population template change.')
        self.assertTrue(verify_block_validity(target_block),
                        'Case 2: Target block is not valid.')
        self.assertTrue(verify_block_validity(extracted_block),
                        'Case 2: Extracted block is not valid.')               

        # Case 3
        target_block = block_template.GenerateProfile(initial_block_size, pop_profile)

        # block extract
        original_size = target_block.get_population_size()
        mathcing_pop_size = target_block.get_population_size(pop_template)
        template_original_size = target_block.get_population_size(pop_template)
        extracted_block = target_block.extract(50, pop_template)
        extracted_block_size = extracted_block.get_population_size()
        final_size = target_block.get_population_size()
        template_final_size = target_block.get_population_size(pop_template)

        self.assertEqual(mathcing_pop_size, extracted_block_size,
                        'Case 3: Extracted block size is not the entire possible population.')
        self.assertEqual(original_size, extracted_block_size + final_size ,
                        'Case 3: Block sizes do not add up.')
        self.assertEqual(mathcing_pop_size, extracted_block.get_population_size(pop_template),
                        'Case 3: Extracted block does not represent template.')
        self.assertEqual(template_original_size, template_final_size + extracted_block_size,
                        'Case 3: Target block does not represent population template change.')
        self.assertTrue(verify_block_validity(target_block),
                        'Case 3: Target block is not valid.')
        self.assertTrue(verify_block_validity(extracted_block),
                        'Case 3: Extracted block is not valid.')   


    #### blob tests
    ## move pop
    def test_blob_move_profile_without_template(self):
        """Tests Blob.move_profile
        
        Blob blocks should remain valid after the operation.
        Population size should remain the same.

        Case 1: 
            action : Moves less population than avaiable from origin block to target block. 
            result : Target block should be valid.
                     Origin block should valid.
                     Old blob size and new blob size should be equal.
                     New target block size minus moved quantity equals old target block size.
                     Old origin block size minus moved quantity equals new origin block size.
        
        Case 2: 
            action : Moves population equal to avaiable from origin block to target block. 
            result : Target block should be valid.
                     Origin block should valid.
                     New target block size minus moved quantity equals old target block size.
                     Old origin block size minus moved quantity equals new origin block size.
        
        Case 3: 
            action : Moves more population than avaiable from origin block to target block. 
            result : Target block should be valid.
                     Origin block should valid.
                     New origin block size should be zero.
                     New target block size should be equal to old target block 
                        size plus old origin block size.
        """
        # Get an auxiliary blob factory.
        block_template = BlockTemplate()
        block_template.add_bucket('bucket_1', ('prop_1_1', 'prop_1_2', 'prop_1_3'))
        block_template.add_bucket('bucket_2', ('prop_2_1', 'prop_2_2'))
        block_template.add_bucket('bucket_3', ('prop_3_1', 'prop_3_2', 'prop_3_3'))
        block_template.add_bucket('bucket_4', ('prop_4_1', 'prop_4_2'))
        block_types = ('block_1', 'block_2')
        blob_factory = BlobFactory(block_types, block_template)
        pop_template = PopTemplate()

        # Case 1:
        blob = blob_factory.Generate(0, (100, 100))
        # get pop size
        old_blob_size = blob.get_population_size()
        old_origin_size = blob.blocks['block_1'].get_population_size()
        old_target_size = blob.blocks['block_2'].get_population_size()
        # move pop from block_1 to block_2
        blob.move_profile(50, pop_template, 'block_1', 'block_2')
        # compare pop size (should be the same)
        new_blob_size = blob.get_population_size()
        new_origin_size = blob.blocks['block_1'].get_population_size()
        new_target_size = blob.blocks['block_2'].get_population_size()
        # verify blob validity
        self.assertTrue(verify_blob_validity(blob),
        'Case 1: Blob is not valid.')
        self.assertEqual(old_blob_size, new_blob_size,
        'Case 1: Blob size changed.')
        self.assertEqual(50, new_target_size - old_target_size,
        'Case 1: Target block did not incremet correctly.')
        self.assertEqual(50, old_origin_size - new_origin_size,
        'Case 1: Origin block did not decrement correctly.')


        # Case 2:
        blob = blob_factory.Generate(0, (100, 100))

        # get pop size
        old_blob_size = blob.get_population_size()
        old_origin_size = blob.blocks['block_1'].get_population_size()
        old_target_size = blob.blocks['block_2'].get_population_size()
        # move pop from block_1 to block_2
        blob.move_profile(100, pop_template, 'block_1', 'block_2')
        # compare pop size (should be the same)
        new_blob_size = blob.get_population_size()
        new_origin_size = blob.blocks['block_1'].get_population_size()
        new_target_size = blob.blocks['block_2'].get_population_size()

        # verify blob validity
        self.assertTrue(verify_blob_validity(blob),
        'Case 2: Blob is not valid.')
        self.assertEqual(old_blob_size, new_blob_size,
        'Case 2: Blob size changed.')
        self.assertEqual(100, new_target_size - old_target_size,
        'Case 2: Target block did not incremet correctly.')
        self.assertEqual(100, old_origin_size - new_origin_size,
        'Case 2: Origin block did not decrement correctly.')
        self.assertEqual(0, new_origin_size,
        'Case 2: Origin block is not 0.')

        # Case 3:
        blob = blob_factory.Generate(0, (100, 100))
        # get pop size
        old_blob_size = blob.get_population_size()
        old_origin_size = blob.blocks['block_1'].get_population_size()
        old_target_size = blob.blocks['block_2'].get_population_size()
        # move pop from block_1 to block_2
        blob.move_profile(100, pop_template, 'block_1', 'block_2')
        # compare pop size (should be the same)
        new_blob_size = blob.get_population_size()
        new_origin_size = blob.blocks['block_1'].get_population_size()
        new_target_size = blob.blocks['block_2'].get_population_size()
        # verify blob validity
        self.assertTrue(verify_blob_validity(blob),
        'Case 3: Blob is not valid.')
        self.assertEqual(old_blob_size, new_blob_size,
        'Case 3: Blob size changed.')
        self.assertEqual(0, new_origin_size,
        'Case 3: Origin block is not 0.')
        self.assertEqual(new_target_size, old_origin_size + old_target_size,
        'Case 3: Target block size is not the correct value.')
    
    def test_blob_move_profile_with_template(self):
        """Tests Blob.move_profile
        
        Blob blocks should remain valid after the operation.
        Population size should remain the same.

        Case 1: 
            action : Moves less population than avaiable from origin block to target block. 
            result : Target block should be valid.
                     Origin block should valid.
                     Old blob size and new blob size should be equal.
                     New target block size minus moved quantity equals old target block size.
                     Old origin block size minus moved quantity equals new origin block size.
        
        Case 2: 
            action : Moves population equal to avaiable from origin block to target block. 
            result : Target block should be valid.
                     Origin block should valid.
                     New target block size minus moved quantity equals old target block size.
                     Old origin block size minus moved quantity equals new origin block size.
        
        Case 3: 
            action : Moves more population than avaiable from origin block to target block. 
            result : Target block should be valid.
                     Origin block should valid.
                     New origin block size should be zero.
                     New target block size should be equal to old target block 
                        size plus old origin block size.
        """
        # Get an auxiliary blob factory.
        block_template = BlockTemplate()
        block_template.add_bucket('bucket_1', ('prop_1_1', 'prop_1_2', 'prop_1_3'))
        block_template.add_bucket('bucket_2', ('prop_2_1', 'prop_2_2'))
        block_template.add_bucket('bucket_3', ('prop_3_1', 'prop_3_2', 'prop_3_3'))
        block_template.add_bucket('bucket_4', ('prop_4_1', 'prop_4_2'))
        block_types = ('block_1', 'block_2')
        blob_factory = BlobFactory(block_types, block_template)
        pop_template = PopTemplate()
        pop_template.set_property('bucket_1', 'prop_1_1')
        pop_template.set_property('bucket_2', 'prop_2_2')

        pop_profile_1 = {'bucket_1' : {'prop_1_1' : 50, 'prop_1_2' : 30},
                        'bucket_2' : {'prop_2_1' : 50, 'prop_2_2' : 50}}

        pop_profile_2 = {'bucket_1' : {'prop_1_1' : 30, 'prop_1_2' : 50},
                        'bucket_2' : {'prop_2_1' : 50, 'prop_2_2' : 50}}

        # Case 1:
        blob = blob_factory.GenerateProfile(0, (100, 100), (pop_profile_1, pop_profile_2))

        # get pop size
        old_blob_size = blob.get_population_size(pop_template)
        old_origin_size = blob.blocks['block_1'].get_population_size(pop_template)
        old_target_size = blob.blocks['block_2'].get_population_size(pop_template)
        # move pop from block_1 to block_2
        blob.move_profile(30, pop_template, 'block_1', 'block_2')
        # compare pop size (should be the same)
        new_blob_size = blob.get_population_size(pop_template)
        new_origin_size = blob.blocks['block_1'].get_population_size(pop_template)
        new_target_size = blob.blocks['block_2'].get_population_size(pop_template)
        # verify blob validity
        self.assertTrue(verify_blob_validity(blob),
        'Case 1: Blob is not valid.')
        self.assertEqual(old_blob_size, new_blob_size,
        'Case 1: Blob size changed.')
        self.assertEqual(30, new_target_size - old_target_size,
        'Case 1: Target block did not incremet correctly.')
        self.assertEqual(30, old_origin_size - new_origin_size,
        'Case 1: Origin block did not decrement correctly.')

        # Case 2:
        blob = blob_factory.GenerateProfile(0, (100, 100), (pop_profile_1, pop_profile_2))

        # get pop size
        old_blob_size = blob.get_population_size(pop_template)
        old_origin_size = blob.blocks['block_1'].get_population_size(pop_template)
        old_target_size = blob.blocks['block_2'].get_population_size(pop_template)
        # move pop from block_1 to block_2
        blob.move_profile(50, pop_template, 'block_1', 'block_2')
        # compare pop size (should be the same)
        new_blob_size = blob.get_population_size(pop_template)
        new_origin_size = blob.blocks['block_1'].get_population_size(pop_template)
        new_target_size = blob.blocks['block_2'].get_population_size(pop_template)
        # verify blob validity
        self.assertTrue(verify_blob_validity(blob),
        'Case 2: Blob is not valid.')
        self.assertEqual(old_blob_size, new_blob_size,
        'Case 2: Blob size changed.')
        self.assertEqual(50, new_target_size - old_target_size,
        'Case 2: Target block did not incremet correctly.')
        self.assertEqual(50, old_origin_size - new_origin_size,
        'Case 2: Origin block did not decrement correctly.')
        self.assertEqual(0, new_origin_size,
        'Case 2: Origin block is not 0.')

        # Case 3:
        blob = blob_factory.GenerateProfile(0, (100, 100), (pop_profile_1, pop_profile_2))

        # get pop size
        old_blob_size = blob.get_population_size(pop_template)
        old_origin_size = blob.blocks['block_1'].get_population_size(pop_template)
        old_target_size = blob.blocks['block_2'].get_population_size(pop_template)
        # move pop from block_1 to block_2
        blob.move_profile(80, pop_template, 'block_1', 'block_2')
        # compare pop size (should be the same)
        new_blob_size = blob.get_population_size(pop_template)
        new_origin_size = blob.blocks['block_1'].get_population_size(pop_template)
        new_target_size = blob.blocks['block_2'].get_population_size(pop_template)
        # verify blob validity
        self.assertTrue(verify_blob_validity(blob),
        'Case 3: Blob is not valid.')
        self.assertEqual(old_blob_size, new_blob_size,
        'Case 3: Blob size changed.')
        self.assertEqual(0, new_origin_size,
        'Case 3: Origin block is not 0.')
        self.assertEqual(new_target_size, old_origin_size + old_target_size,
        'Case 3: Target block size is not the correct value.')


    ## split blob
    def test_blob_split_blob_without_profile_unbalanced_pop(self):
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
        block_template.add_bucket('bucket_1', ('prop_1_1', 'prop_1_2', 'prop_1_3'))
        block_template.add_bucket('bucket_2', ('prop_2_1', 'prop_2_2'))
        block_template.add_bucket('bucket_3', ('prop_3_1', 'prop_3_2', 'prop_3_3'))
        block_template.add_bucket('bucket_4', ('prop_4_1', 'prop_4_2'))
        block_types = ('block_1', 'block_2')
        blob_factory = BlobFactory(block_types, block_template)
        pop_template = PopTemplate()

        # Case 1:
        blob_1 = blob_factory.Generate(0, (100, 0,))
        
        # get orginal size
        old_blob_1_size = blob_1.get_population_size()
        # split blob
        blob_2 = blob_1.split_blob(block_types, 50, pop_template)
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
        blob_1 = blob_factory.Generate(0, (100, 0))
        
        # get orginal size
        old_blob_1_size = blob_1.get_population_size()
        # split blob
        blob_2 = blob_1.split_blob(block_types, 100, pop_template)
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
        blob_1 = blob_factory.Generate(0, (100, 0))
        
        # get orginal size
        old_blob_1_size = blob_1.get_population_size()
        # split blob
        blob_2 = blob_1.split_blob(block_types, 300, pop_template)
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
    def test_blob_split_blob_without_profile_balanced_pop(self):
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
        block_template.add_bucket('bucket_1', ('prop_1_1', 'prop_1_2', 'prop_1_3'))
        block_template.add_bucket('bucket_2', ('prop_2_1', 'prop_2_2'))
        block_template.add_bucket('bucket_3', ('prop_3_1', 'prop_3_2', 'prop_3_3'))
        block_template.add_bucket('bucket_4', ('prop_4_1', 'prop_4_2'))
        block_types = ('block_1', 'block_2')
        blob_factory = BlobFactory(block_types, block_template)
        pop_template = PopTemplate()

        # Case 1:
        blob_1 = blob_factory.Generate(0, (100, 100))
        
        # get orginal size
        old_blob_1_size = blob_1.get_population_size()
        # split blob
        blob_2 = blob_1.split_blob(block_types, 50, pop_template)
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
        blob_1 = blob_factory.Generate(0, (100, 100))
        
        # get orginal size
        old_blob_1_size = blob_1.get_population_size()
        # split blob
        blob_2 = blob_1.split_blob(block_types, 200, pop_template)
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
        self.assertEqual(200, new_blob_2_size,
        'Case 2: Split blob quantity does not match blob 2 size.')
        self.assertEqual(0, new_blob_1_size,
        'Case 2: Blob 1 new size is not 0.')
        self.assertEqual(old_blob_1_size, new_blob_2_size,
        'Case 2: Blob 2 size is not equal to old blob 1 size.')

        # Case 3:
        blob_1 = blob_factory.Generate(0, (100, 100))
        
        # get orginal size
        old_blob_1_size = blob_1.get_population_size()
        # split blob
        blob_2 = blob_1.split_blob(block_types, 300, pop_template)
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
                
    ## grab population
    def test_blob_grab_pop(self):
        """Tests Blob.grab_population
        
        Blobs should remain valid after the operation.
        Sum of population sizes should remain the same.

        Case 1: 
            action : Grabs less population than available in the blob.
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
        
        # get blob factory
        block_template = BlockTemplate()
        block_template.add_bucket('bucket_1', ('prop_1_1', 'prop_1_2', 'prop_1_3'))
        block_template.add_bucket('bucket_2', ('prop_2_1', 'prop_2_2'))
        block_template.add_bucket('bucket_3', ('prop_3_1', 'prop_3_2', 'prop_3_3'))
        block_template.add_bucket('bucket_4', ('prop_4_1', 'prop_4_2'))
        block_types = ('block_1', 'block_2')
        blob_factory = BlobFactory(block_types, block_template)
        pop_template = PopTemplate()

        # Case 1:
        blob_1 = blob_factory.Generate(0, (100, 100))
        
        # get orginal size
        old_blob_1_size = blob_1.get_population_size()
        # split blob
        blob_2 = blob_1.grab_population(50)
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
        'Case 1: Grabbed quantity does not match blob 2 size.')
        self.assertTrue(blob_1.blob_id is not blob_2.blob_id,
        'Case 1: Blobs are the same.')

        # Case 2:
        blob_1 = blob_factory.Generate(0, (100, 100))
        
        # get orginal size
        old_blob_1_size = blob_1.get_population_size()
        # split blob
        blob_2 = blob_1.grab_population(200)
        # compare original size with blob + blob2 sizes
        new_blob_1_size = blob_1.get_population_size()
        new_blob_2_size = blob_2.get_population_size()
        # verify blob validity for blob and blob2
        self.assertTrue(verify_blob_validity(blob_1),
        'Case 2: Blob 1 is not valid.')
        self.assertTrue(verify_blob_validity(blob_2),
        'Case 2: Blob 2 is not valid.')
        self.assertEqual(200, new_blob_2_size,
        'Case 2: Grabbed quantity does not match blob 2 size.')
        self.assertEqual(new_blob_1_size, new_blob_2_size,
        'Case 2: Blob sizes are not the same.')
        self.assertTrue(blob_1.blob_id is blob_2.blob_id,
        'Case 2: Blobs are not the same.')

        # Case 3:
        blob_1 = blob_factory.Generate(0, (100, 100))
        
        # get orginal size
        old_blob_1_size = blob_1.get_population_size()
        # split blob
        blob_2 = blob_1.grab_population(300)
        # compare original size with blob + blob2 sizes
        new_blob_1_size = blob_1.get_population_size()
        new_blob_2_size = blob_2.get_population_size()
        # verify blob validity for blob and blob2
        self.assertTrue(verify_blob_validity(blob_1),
        'Case 3: Blob 1 is not valid.')
        self.assertTrue(verify_blob_validity(blob_2),
        'Case 3: Blob 2 is not valid.')
        self.assertEqual(new_blob_1_size, new_blob_2_size,
        'Case 3: Blob sizes are not the same.')
        self.assertTrue(blob_1.blob_id is blob_2.blob_id,
        'Case 3: Blobs are not the same.')

    ## consume blob
    def test_blob_consume_blob(self):
        """Tests Blob.consume_blob
        
        Blob should remain valid after the operation.
        
        Case 1: 
            action : A blob consumes an auxiliary blob
            result : All population of consumed blob should be in the consuming blob.
                     Consuming blob should be valid.
        """

        # get blob factory
        block_template = BlockTemplate()
        block_template.add_bucket('bucket_1', ('prop_1_1', 'prop_1_2', 'prop_1_3'))
        block_template.add_bucket('bucket_2', ('prop_2_1', 'prop_2_2'))
        block_template.add_bucket('bucket_3', ('prop_3_1', 'prop_3_2', 'prop_3_3'))
        block_template.add_bucket('bucket_4', ('prop_4_1', 'prop_4_2'))
        block_types = ('block_1', 'block_2')
        blob_factory = BlobFactory(block_types, block_template)
        pop_template = PopTemplate()

        # Case 1:
        blob_1 = blob_factory.Generate(0, (100, 100))
        blob_2 = blob_factory.Generate(0, (50, 50))
        
        old_blob_1_size = blob_1.get_population_size()
        old_blob_2_size = blob_2.get_population_size()

        blob_1.consume_blob(blob_2)

        new_blob_1_size = blob_1.get_population_size()
        new_blob_2_size = blob_2.get_population_size()

        self.assertTrue(verify_blob_validity(blob_1),
        'Case 2: Blob 1 is not valid.')
        self.assertEqual(new_blob_1_size, old_blob_1_size + old_blob_2_size ,
        'Case 3: New blob 1 size is not the total population.')


def suite():
    suite = unittest.TestSuite()

    # bucket tests
    suite.addTest(PopulationTests('test_bucket_add_bucket'))
    suite.addTest(PopulationTests('test_extract_bucket_without_key'))
    suite.addTest(PopulationTests('test_extract_bucket_with_key'))
    suite.addTest(PopulationTests('test_extract_bucket_with_key_list'))
    suite.addTest(PopulationTests('test_extract_bucket_with_key_set'))

    # block tests
    suite.addTest(PopulationTests('test_block_add_block'))
    suite.addTest(PopulationTests('test_initialize_buckets_profile'))
    suite.addTest(PopulationTests('test_block_extract'))

    # # blob tests
    # suite.addTest(PopulationTests('test_blob_move_profile_without_template'))
    # suite.addTest(PopulationTests('test_blob_move_profile_with_template'))
    # suite.addTest(PopulationTests('test_blob_split_blob_without_profile_unbalanced_pop'))
    # suite.addTest(PopulationTests('test_blob_split_blob_without_profile_balanced_pop'))
    # suite.addTest(PopulationTests('test_blob_grab_pop'))
    # suite.addTest(PopulationTests('test_blob_consume_blob'))

    # missing test_initialize_buckets_profile
    # missing test_blob_split_blob_with_profile

    # missing get_population_size tests

    return suite

if __name__ == "__main__":
    runner = unittest.TextTestRunner()
    runner.run(suite())
