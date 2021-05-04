import sys
sys.path.append('../')

import unittest
import environment
import util
from population import *


def verify_block_validity(block):
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
        pass

    def tearDown(self):
        pass
    
    #### bucket tests
    ## add bucket
    def test_bucket_add_bucket(self):
        """Tests PropertyBucket.add_bucket"""

        # create aux bucket
        aux_bucket = PropertyBucket('bucket_1')
        aux_bucket.set_values_rand(('prop_1_1', 'prop_1_2', 'prop_1_3') , 60)

        # Create a same property aux bucket
        aux_bucket2 = PropertyBucket('bucket_1')
        aux_bucket2.set_values_rand(('prop_1_1', 'prop_1_2', 'prop_1_3') , 60)

        # Test adding same characteristic PropertyBuckets
        aux_bucket_size = aux_bucket.get_population_size()
        aux_bucket_size2 = aux_bucket2.get_population_size()
        aux_bucket.add_bucket(aux_bucket2)

        merge_size = aux_bucket.get_population_size()

        # assert if bucket was added correctly
        self.assertEqual(merge_size, aux_bucket_size + aux_bucket_size2,
                        'Add bucket not adding same property buckets correctly.')

        # Test adding different characteristic PropertyBuckets
        aux_bucket3 = PropertyBucket('bucket_2')
        aux_bucket3.set_values_rand(('prop_2_1', 'prop_2_2') , 60)

        aux_bucket.add_bucket(aux_bucket3)
        merge_size = aux_bucket.get_population_size()

        # assert whether bucket was skipped
        self.assertEqual(merge_size, aux_bucket_size + aux_bucket_size2,
                        'Add bucket adding different property buckets incorrectly.')

        
    ## extract
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
        # Create aux bucket
        aux_bucket = PropertyBucket('bucket_1')
        aux_bucket.set_values(('prop_1_1', 'prop_1_2', 'prop_1_3') , (60,60,60))

        #extract
        characteristic = aux_bucket.characteristic
        bucket_size = aux_bucket.get_population_size()
        extracted_bucket = aux_bucket.extract(100)
        smaller_bucket_size = aux_bucket.get_population_size()
        extracted_bucket_size = extracted_bucket.get_population_size()

        #compare
        self.assertEqual(bucket_size, smaller_bucket_size + extracted_bucket_size,
                        'Case 1 buckets do not add up.')
        self.assertEqual(100, extracted_bucket_size,
                        'Case 1 extracted bucket is not the correct size.')
        self.assertEqual(smaller_bucket_size, bucket_size - extracted_bucket_size,
                        'Case 1 original bucket is not the corrected suze.')

        # Case 2:
        # Create aux bucket
        aux_bucket = PropertyBucket('bucket_1')
        aux_bucket.set_values(('prop_1_1', 'prop_1_2', 'prop_1_3') , (60,60,60))

        #extract
        characteristic = aux_bucket.characteristic
        bucket_size = aux_bucket.get_population_size()
        extracted_bucket = aux_bucket.extract(180)
        smaller_bucket_size = aux_bucket.get_population_size()
        extracted_bucket_size = extracted_bucket.get_population_size()
        
        #compare
        self.assertEqual(bucket_size, smaller_bucket_size + extracted_bucket_size,
                        'Case 2 buckets do not add up.')
        self.assertEqual(bucket_size, extracted_bucket_size,
                        'Case 2 extracted bucket is not the total size.')
        self.assertEqual(smaller_bucket_size, 0,
                        'Case 2 original bucket is not the zero.')                

        # Case 3:
        # Create aux bucket
        aux_bucket = PropertyBucket('bucket_1')
        aux_bucket.set_values(('prop_1_1', 'prop_1_2', 'prop_1_3') , (60,60,60))

        #extract
        characteristic = aux_bucket.characteristic
        bucket_size = aux_bucket.get_population_size()
        extracted_bucket = aux_bucket.extract(300)
        smaller_bucket_size = aux_bucket.get_population_size()
        extracted_bucket_size = extracted_bucket.get_population_size()
        
        #compare
        self.assertEqual(bucket_size, smaller_bucket_size + extracted_bucket_size,
                        'Case 3 buckets do not add up.')
        self.assertEqual(bucket_size, extracted_bucket_size,
                        'Case 3 extracted bucket is not the total size.')
        self.assertEqual(smaller_bucket_size, 0,
                        'Case 3 original bucket is not the zero.')

    ## extract
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
        # Create aux bucket
        aux_bucket = PropertyBucket('bucket_1')
        aux_bucket.set_values(('prop_1_1', 'prop_1_2', 'prop_1_3') , (60,60,60))
        
        #extract
        bucket_size = aux_bucket.get_population_size(key='prop_1_1')
        extracted_bucket = aux_bucket.extract(30, key='prop_1_1')
        smaller_bucket_size = aux_bucket.get_population_size(key='prop_1_1')
        extracted_bucket_size = extracted_bucket.get_population_size(key='prop_1_1')

        #compare
        self.assertEqual(bucket_size, smaller_bucket_size + extracted_bucket_size,
                        'Case 1 buckets do not add up.')
        self.assertEqual(30, extracted_bucket_size,
                        'Case 1 extracted bucket is not the correct size.')
        self.assertEqual(smaller_bucket_size, bucket_size - extracted_bucket_size,
                        'Case 1 original bucket is not the corrected size.')

        # Case 2:
        # Create aux bucket
        aux_bucket = PropertyBucket('bucket_1')
        aux_bucket.set_values(('prop_1_1', 'prop_1_2', 'prop_1_3') , (60,60,60))

        #extract
        bucket_size = aux_bucket.get_population_size(key='prop_1_1')
        extracted_bucket = aux_bucket.extract(60, key='prop_1_1')
        smaller_bucket_size = aux_bucket.get_population_size(key='prop_1_1')
        extracted_bucket_size = extracted_bucket.get_population_size(key='prop_1_1')
        
        #compare
        self.assertEqual(bucket_size, smaller_bucket_size + extracted_bucket_size,
                        'Case 2 buckets do not add up.')
        self.assertEqual(bucket_size, extracted_bucket_size,
                        'Case 2 extracted bucket is not the total size.')
        self.assertEqual(smaller_bucket_size, 0,
                        'Case 2 original bucket is not the zero.')                

        # Case 3:
        # Create aux bucket
        aux_bucket = PropertyBucket('bucket_1')
        aux_bucket.set_values(('prop_1_1', 'prop_1_2', 'prop_1_3') , (60,60,60))

        #extract
        bucket_size = aux_bucket.get_population_size(key='prop_1_1')
        extracted_bucket = aux_bucket.extract(120, key='prop_1_1')
        smaller_bucket_size = aux_bucket.get_population_size(key='prop_1_1')
        extracted_bucket_size = extracted_bucket.get_population_size(key='prop_1_1')
        
        #compare
        self.assertEqual(bucket_size, smaller_bucket_size + extracted_bucket_size,
                        'Case 3 buckets do not add up.')
        self.assertEqual(bucket_size, extracted_bucket_size,
                        'Case 3 extracted bucket is not the total size.')
        self.assertEqual(smaller_bucket_size, 0,
                        'Case 3 original bucket is not the zero.')


    ## tests add block function
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

    # block tests
    suite.addTest(PopulationTests('test_block_add_block'))
    suite.addTest(PopulationTests('test_initialize_buckets_profile'))
    suite.addTest(PopulationTests('test_block_extract'))

    # blob tests
    suite.addTest(PopulationTests('test_blob_move_profile_without_template'))
    suite.addTest(PopulationTests('test_blob_move_profile_with_template'))
    suite.addTest(PopulationTests('test_blob_split_blob_without_profile_unbalanced_pop'))
    suite.addTest(PopulationTests('test_blob_split_blob_without_profile_balanced_pop'))
    suite.addTest(PopulationTests('test_blob_grab_pop'))
    suite.addTest(PopulationTests('test_blob_consume_blob'))

    # missing test_initialize_buckets_profile
    # missing test_blob_split_blob_with_profile

    # missing get_population_size tests

    return suite

if __name__ == "__main__":
    runner = unittest.TextTestRunner()
    runner.run(suite())
