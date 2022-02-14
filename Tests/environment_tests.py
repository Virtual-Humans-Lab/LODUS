from __future__ import annotations
import sys
sys.path.append('../')
sys.path.append('../Plugins')

import unittest
import environment
import population
from population_tests import verify_blobs_validity
from population_tests import verify_blob_validity
from util import *
from data_parse_util import *

from GatherPopulationNewPlugin import GatherPopulationNewPlugin
from ReturnPopulationPlugin import ReturnPopulationPlugin

def verify_node_validity(node:EnvNode)-> bool:
    """Checks whether all Blobs contained in a EnvNode are valid."""
    result = True
    for blob in node.contained_blobs:
        blob_result = verify_blob_validity(blob)
        if blob_result is False:
            print('\n\t\tBlob with id {0} is Invalid'.format(blob.blob_id))
        result = result and blob_result

    return result

def verify_region_validity(region:EnvRegion)-> bool:
    """Checks whether all EnvNodes contained in a EnvRegion are valid."""
    result = True
    for node in region.node_list:
        node_result = verify_node_validity(node)
        if node_result is False:
            print('\n\tNode with name {0} is Invalid'.format(node.name))
        result = result and node_result

    return result

def verify_graph_validity(graph:EnvironmentGraph) -> bool:
    """Checks whether all EnvRegions contained in a EnvironmentGraph are valid."""
    result = True
    for region in graph.region_list:
        region_result = verify_region_validity(region)
        if region_result is False:
            print('\nRegion with name {0} is Invalid, and id {1}'.format(region.name, region.id))
        result = result and verify_region_validity(region)
    
    return result

def verify_graph_validity_size(graph: EnvironmentGraph, desired_size: int, population_template = None):
    """Checks whether an EnvironmentGraph is valid and desired size."""
    valid = verify_graph_validity(graph)
    return valid and (desired_size == graph.get_population_size(population_template))

def verify_blob_contained_in_node(blob: Blob, node: EnvNode):
    """Checks whether a Blob is contained in a EnvNode."""
    return blob in node.contained_blobs

def verify_blobs_contained_in_node(blobs: list[Blob], node: EnvNode):
    """Checks whether an list of Blobs are contained in a EnvNode."""
    return all([b in node.contained_blobs for b in blobs])

def blobs_total_size(blobs: list[Blob], population_template = None):
    return sum([x.get_population_size(population_template) for x in blobs])

class EnvironmentTests(unittest.TestCase):

    def setUp(self):
        #Sets up the test environment
        environment_path = '../DataInput/Tests/environment_tests_dummy_input_A.json'
        self.envA = generate_EnvironmentGraph(environment_path)

        pA1 = GatherPopulationNewPlugin(self.envA)
        pA2 = ReturnPopulationPlugin(self.envA)

        self.envA.LoadPlugin(pA1)
        self.envA.LoadPlugin(pA2)
        
        environment_path = '../DataInput/Tests/environment_tests_dummy_input_B.json'
        self.envB = generate_EnvironmentGraph(environment_path)
        
        pB1 = GatherPopulationNewPlugin(self.envB)
        pB2 = ReturnPopulationPlugin(self.envB)

        self.envB.LoadPlugin(pB1)
        self.envB.LoadPlugin(pB2)

    def tearDown(self):
        #Resets the test environment
        pass

    ### EnvNode tests
    ## EnvNode.get_population_size - one Blob in EnvNode
    def test_node_get_population_size_one_blob(self):
        """Tests EnvNode.get_population_size

        Gets population sizes for a EnvNode using multiple PopTemplates. 
        
        Target EnvNode population description:
        "age": {"adults": 40, "elders": 20, "young": 15, "children": 25},
        "occupation": {"idle": 20, "student": 40, "worker": 40},
        "social_profile": {"low": 40, "mid": 35, "high": 25}
        
        Case 1: 
            action: Gets population sizes in multiple scenarios.
            result: Sizes are equal as pre-defined in the population description
        """
        # Case 1:
        node_sizes = []
        
        # Gets a target EnvNode with population 100
        target_node = self.envA.get_node_by_name("Petropolis", "home")
        node_sizes.append(target_node.get_population_size())
        
        # Gets the population size for multiple PopTemplates
        pop_template = PopTemplate() 
        pop_template.set_sampled_property('age', 'adults')
        node_sizes.append(target_node.get_population_size(pop_template))
        
        pop_template = PopTemplate() 
        pop_template.set_sampled_property('age', 'elders')
        node_sizes.append(target_node.get_population_size(pop_template))
        
        pop_template = PopTemplate() 
        pop_template.set_sampled_property('age', ['adults', 'elders'])
        node_sizes.append(target_node.get_population_size(pop_template))
        
        pop_template = PopTemplate() 
        pop_template.set_sampled_property('age', ['adults', 'elders'])
        pop_template.set_sampled_property('occupation', 'worker')
        node_sizes.append(target_node.get_population_size(pop_template))
        
        pop_template = PopTemplate() 
        pop_template.set_sampled_property('age', ['adults', 'elders'])
        pop_template.set_sampled_property('occupation', ['idle', 'worker'])
        node_sizes.append(target_node.get_population_size(pop_template))
        
        pop_template = PopTemplate() 
        pop_template.set_sampled_property('age', [])
        pop_template.set_sampled_property('occupation', [])
        node_sizes.append(target_node.get_population_size(pop_template))
        
        pop_template = PopTemplate() 
        pop_template.set_sampled_property('age', ['adults', 'elders'])
        pop_template.set_sampled_property('occupation', [])
        node_sizes.append(target_node.get_population_size(pop_template))
        
        pop_template = PopTemplate() 
        pop_template.set_sampled_property('age', ['adults', 'elders'])
        pop_template.set_sampled_property('occupation', [])
        pop_template.set_sampled_property('social_profile', 'mid')
        node_sizes.append(target_node.get_population_size(pop_template))
        
        pop_template = PopTemplate() 
        pop_template.set_sampled_property('age', 'elders')
        pop_template.set_sampled_property('occupation', [])
        pop_template.set_sampled_property('social_profile', 'mid')
        node_sizes.append(target_node.get_population_size(pop_template))
        
        # assert validity and correct sizes
        self.assertTrue(verify_node_validity(target_node),
        'Case 1: EnvNode is not valid.')
        self.assertTrue(verify_graph_validity_size(self.envA, 300),
        'Case 1: EnvironmentGraph changed in size.')
        self.assertEqual(node_sizes, [100, 40, 20, 60, 40, 60, 100, 60, 35, 20],
        f'Case 1: Population sizes different than expected {node_sizes}.')
        
    ## EnvNode.get_population_size - multiple Blobs in EnvNode
    def test_node_get_population_size_multiple_blobs(self):
        """Tests EnvNode.get_population_size

        Gets population sizes for a EnvNode using multiple PopTemplates. 
        
        Target EnvNode contains four Blobs with population 100 and permutations of:
        "traceable_A": {"default", "other_value"},
        "traceable_B": {0, 1}
        
        Target EnvNode population description for each Blob:
        "age": {"adults": 40, "elders": 20, "young": 15, "children": 25},
        "occupation": {"idle": 20, "student": 40, "worker": 40},
        "social_profile": {"low": 40, "mid": 35, "high": 25}
        
        Case 1: 
            action: Gets population sizes in multiple scenarios.
            result: Sizes are equal as pre-defined in the population description
        """
        # Case 1:
        node_sizes = []
        
        # Gets a target EnvNode with population 100
        target_node = self.envB.get_node_by_name("Petropolis", "home")
        node_sizes.append(target_node.get_population_size())
        
        # Gets the population size for multiple PopTemplates
        pop_template = PopTemplate() 
        pop_template.set_sampled_property('age', 'adults')
        node_sizes.append(target_node.get_population_size(pop_template))
        
        pop_template = PopTemplate() 
        pop_template.set_sampled_property('age', ['adults', 'elders'])
        pop_template.set_sampled_property('occupation', ['idle', 'worker'])
        node_sizes.append(target_node.get_population_size(pop_template))
        
        pop_template = PopTemplate() 
        pop_template.set_sampled_property('age', 'elders')
        pop_template.set_sampled_property('occupation', [])
        pop_template.set_sampled_property('social_profile', 'mid')
        node_sizes.append(target_node.get_population_size(pop_template))
        
        pop_template = PopTemplate() 
        pop_template.set_traceable_property('traceable_A', 'default')
        node_sizes.append(target_node.get_population_size(pop_template))
        
        pop_template = PopTemplate() 
        pop_template.set_traceable_property('traceable_A', 'default')
        pop_template.set_traceable_property('traceable_B', 0)
        node_sizes.append(target_node.get_population_size(pop_template))
        
        pop_template = PopTemplate() 
        pop_template.set_traceable_property('traceable_A', ['default', 'other_value'])
        pop_template.set_traceable_property('traceable_B', [0, 1])
        node_sizes.append(target_node.get_population_size(pop_template))
                
        pop_template = PopTemplate() 
        pop_template.set_traceable_property('traceable_A', 'default')
        pop_template.set_traceable_property('traceable_B', 0)
        pop_template.set_sampled_property('age', 'adults')
        node_sizes.append(target_node.get_population_size(pop_template))
        
        pop_template = PopTemplate() 
        pop_template.set_traceable_property('traceable_A', ['default', 'other_value'])
        pop_template.set_traceable_property('traceable_B', 0)
        pop_template.set_sampled_property('age', 'adults')
        node_sizes.append(target_node.get_population_size(pop_template))
        
        pop_template = PopTemplate() 
        pop_template.set_traceable_property('traceable_A', ['default', 'other_value'])
        pop_template.set_traceable_property('traceable_B', 0)
        pop_template.set_sampled_property('age', 'adults')
        pop_template.set_sampled_property('occupation', [])
        pop_template.set_sampled_property('social_profile', 'mid')
        node_sizes.append(target_node.get_population_size(pop_template))
        
        # assert validity and correct sizes
        self.assertTrue(verify_node_validity(target_node),
        'Case 1: EnvNode is not valid.')
        self.assertTrue(verify_graph_validity_size(self.envA, 300),
        'Case 1: EnvironmentGraph changed in size.')
        self.assertEqual(node_sizes, [400, 160, 240, 80, 200, 100, 400, 40, 80, 70],
        f'Case 1: Population sizes different than expected {node_sizes}.')
    
    ## EnvNode.grab_population - without template - one Blob in EnvNode
    def test_node_grab_population_no_template_one_blob(self):
        """Tests EnvNode.grab_population
        
        Requests population from EnvNodes. Each EnvNode has only one Blob
        
        Case 1: 
            action: Requests less population than available.
            result: Node is valid.
                    Blobs are valid.
                    Grabbed Blob is different than one in the node.
                    Total population size unchanged.
                    Blob size equals extracted quantity.     
                    
        Case 2: 
            action: Equal population as available.
            result: Node is valid.
                    Blobs is valid.
                    Node is empty.
                    Blob is the same as the one that was in the in the node.
                    Total population size unchanged.
                    Blob size equals extracted quantity.
                    
        Case 3: 
            action: More population than available.
            result: Node is valid.
                    Blobs is valid.
                    Node is empty.
                    Blob is the same as the one that was in the in the node.
                    Total population size unchanged.
                     
        """
        # Case 1:
        # Gets a target EnvNode with population 100
        target_node = self.envA.get_node_by_name("Petropolis", "home")
        source_blob = target_node.contained_blobs[0]
        node_original_size = target_node.get_population_size()
        source_original_size = source_blob.get_population_size()

        # Grabs 50 people from the target node - less than available
        grabbed_population = target_node.grab_population(50)
        node_final_size = target_node.get_population_size()
        source_final_size = source_blob.get_population_size()
        grabbed_population_size = blobs_total_size(grabbed_population)

        # assert validity and correct sizes
        self.assertTrue(verify_blobs_validity(grabbed_population),
        'Case 1: Grabbed population is not valid.')
        self.assertTrue(not verify_blobs_contained_in_node(grabbed_population, target_node),
        'Case 1: Grabbed population still in EnvNode.')
        self.assertTrue(verify_blob_contained_in_node(source_blob, target_node),
        'Case 1: Source Blob is not in EnvNode.')
        self.assertEqual(node_original_size, node_final_size + grabbed_population_size,
        'Case 1: Total population size changed.')
        self.assertEqual(source_original_size, source_final_size + grabbed_population_size,
        'Case 1: Source population size changed.')
        self.assertEqual(grabbed_population_size, 50,
        'Case 1: Grabbed population size is not equal to grabbed amount.')
        self.assertTrue(verify_graph_validity_size(self.envA, 300 - grabbed_population_size),
        'Case 1: EnvironmentGraph changed in size.')
        self.assertTrue(verify_node_validity(target_node),
        'Case 1: Grabbed pop still in node.')
        
        # Returns Blobs to target node for next Case
        target_node.add_blobs(grabbed_population)
        
        # Case 2:
        # Gets a target EnvNode with population 100
        target_node = self.envA.get_node_by_name("Partenon", "home")
        source_blob = target_node.contained_blobs[0]
        node_original_size = target_node.get_population_size()
        source_original_size = source_blob.get_population_size()

        # Grabs 100 people from the target node - equal as available
        grabbed_population = target_node.grab_population(100)
        node_final_size = target_node.get_population_size()
        source_final_size = source_blob.get_population_size()
        grabbed_population_size = blobs_total_size(grabbed_population)

        # assert validity and correct sizes
        self.assertTrue(verify_blobs_validity(grabbed_population),
        'Case 2: Grabbed population is not valid.')
        self.assertTrue(verify_node_validity(target_node),
        'Case 2: Grabbed population still in node.')
        self.assertTrue(len(target_node.contained_blobs) == 0,
        'Case 2: Node is not empty.')
        self.assertEqual(node_original_size, node_final_size + grabbed_population_size,
        'Case 2: Total population size changed.')
        self.assertEqual(grabbed_population_size, 100,
        'Case 2: Grabbed population size is not equal to grabbed amount.')
        self.assertEqual(source_blob, grabbed_population[0],
        'Case 2: Blob is not the same which was in the node.')
        self.assertTrue(not verify_blobs_contained_in_node(grabbed_population, target_node),
        'Case 2: Grabbed population still in EnvNode.')
        self.assertTrue(not verify_blob_contained_in_node(source_blob, target_node),
        'Case 2: Source Blob is not in EnvNode.')
        self.assertEqual(source_original_size, source_final_size,
        'Case 2: Source population size changed.')
        self.assertEqual(grabbed_population_size, source_final_size,
        'Case 2: Source population size changed.')
        self.assertEqual(grabbed_population_size, 100,
        'Case 2: Grabbed population size is not equal to grabbed amount.')
        self.assertTrue(verify_graph_validity_size(self.envA, 300 - grabbed_population_size),
        'Case 2: EnvironmentGraph changed in size.')
        
        # Returns Blobs to target node for next Case
        target_node.add_blobs(grabbed_population)
        
        # Case 3:
        # Gets a target EnvNode with population 100
        target_node = self.envA.get_node_by_name("Centro", "home")
        source_blob = target_node.contained_blobs[0]
        node_original_size = target_node.get_population_size()
        source_original_size = source_blob.get_population_size()

        # Grabs 200 people from the target node - more than available
        grabbed_population = target_node.grab_population(200)
        node_final_size = target_node.get_population_size()
        source_final_size = source_blob.get_population_size()
        grabbed_population_size = blobs_total_size(grabbed_population)

        # assert validity and correct sizes
        self.assertTrue(verify_blobs_validity(grabbed_population),
        'Case 3: Grabbed population is not valid.')
        self.assertTrue(verify_node_validity(target_node),
        'Case 3: Grabbed population still in node.')
        self.assertTrue(len(target_node.contained_blobs) == 0,
        'Case 3: Node is not empty.')
        self.assertEqual(node_original_size, node_final_size + grabbed_population_size,
        'Case 3: Total population size changed.')
        self.assertEqual(grabbed_population_size, 100,
        'Case 3: Grabbed population size is not equal to grabbed amount.')
        self.assertEqual(source_blob, grabbed_population[0],
        'Case 3: Blob is not the same which was in the node.')
        self.assertTrue(not verify_blobs_contained_in_node(grabbed_population, target_node),
        'Case 3: Grabbed population still in EnvNode.')
        self.assertTrue(not verify_blob_contained_in_node(source_blob, target_node),
        'Case 3: Source Blob is not in EnvNode.')
        self.assertEqual(source_original_size, source_final_size,
        'Case 3: Source population size changed.')
        self.assertEqual(grabbed_population_size, source_final_size,
        'Case 3: Source population size changed.')
        self.assertTrue(verify_graph_validity_size(self.envA, 300 - grabbed_population_size),
        'Case 3: EnvironmentGraph changed in size.')    
        
    ## EnvNode.grab_population - without template - three Blobs in EnvNode
    def test_node_grab_population_no_template_three_blobs(self):
        """Tests EnvNode.grab_population
        
        Clone two extra Blobs in a EnvNode. Then, grabs population from node

        Case 1: 
            action: Less population than available.
            result: Node is valid.
                    Blobs are valid.
                    Blobs in list are different than one in the node.
                    Total population size unchanged.    
                    
        Case 2: 
            action: Equal population as available.
            result: Node is valid.
                    Blobs are valid.
                    Node is empty.
                    3 Blobs are in list.
                    Total population size unchanged.
                    
        Case 3: 
            action: More population than available.
            result: Node is valid.
                    No population is removed.
                    3 Blobs are in list.
                    Total population size unchanged.
                    Returns an empty list.
        """

        # Case 1:
        # Gets a target EnvNode with population 100
        target_node = self.envA.get_node_by_name("Petropolis", "home")
        node_blobs = target_node.contained_blobs

        # Gets the first Blob in target node
        source_blob = node_blobs[0]

        # Copy two extra Blobs with same profile
        clone_blob_1 = source_blob.blob_factory.GenerateProfile(0, 100, source_blob.profiles)
        clone_blob_2 = source_blob.blob_factory.GenerateProfile(0, 100, source_blob.profiles)

        # Adds extra Blobs to target node
        target_node.add_blobs([clone_blob_1, clone_blob_2])

        # Grabs 150 people from the target node - less than available
        node_original_size = target_node.get_population_size()
        grabbed_population = target_node.grab_population(150)
        source_final_size = target_node.get_population_size()
        grabbed_population_size = blobs_total_size(grabbed_population)

        # assert validity and correct sizes
        self.assertTrue(verify_blobs_validity(grabbed_population),
        'Case 1: Grabbed population is not valid.')
        self.assertTrue(not verify_blobs_contained_in_node(grabbed_population, target_node),
        'Case 1: Grabbed pop still in node.')
        self.assertEqual(node_original_size, source_final_size + grabbed_population_size,
        'Case 1: Total population size changed.')
        self.assertEqual(grabbed_population_size, 150,
        'Case 1: Grabbed population size is not equal to grabbed amount.')
        self.assertTrue(len(target_node.contained_blobs) == 3,
        'Case 1: Target EnvNode has a different number of Blobs than intended.')
        self.assertTrue(verify_node_validity(target_node),
        'Case 1: Grabbed pop still in node.')
        self.assertTrue(verify_graph_validity_size(self.envA, 500 - grabbed_population_size),
        'Case 1: EnvironmentGraph changed in size.')
        
        # Returns Blobs to target node for next Case
        target_node.add_blobs(grabbed_population)
        
        # Case 2:
        # Gets a target EnvNode with population 100
        target_node = self.envA.get_node_by_name("Partenon", "home")
        node_blobs = target_node.contained_blobs

        # Gets the first Blob in target node
        source_blob = node_blobs[0]

        # Copy two extra Blobs with same profile
        clone_blob_1 = source_blob.blob_factory.GenerateProfile(0, 100, source_blob.profiles)
        clone_blob_2 = source_blob.blob_factory.GenerateProfile(0, 100, source_blob.profiles)
        
        # Adds extra Blobs to target node
        target_node.add_blobs([clone_blob_1, clone_blob_2])
        original_blobs = [source_blob, clone_blob_1, clone_blob_2]

        # Grabs 300 people from the target node - equal as available
        node_original_size = target_node.get_population_size()
        grabbed_population = target_node.grab_population(300)
        node_final_size = target_node.get_population_size()
        grabbed_population_size = blobs_total_size(grabbed_population)

        # assert validity and correct sizes
        self.assertTrue(verify_blobs_validity(grabbed_population),
        'Case 2: Grabbed population is not valid.')
        self.assertTrue(not verify_blobs_contained_in_node(grabbed_population, target_node),
        'Case 2: Grabbed pop still in node.')
        self.assertTrue(not verify_blobs_contained_in_node(original_blobs, target_node),
        'Case 2: Grabbed pop still in node.')
        self.assertEqual(node_original_size, node_final_size + grabbed_population_size,
        'Case 2: Total population size changed.')
        self.assertEqual(node_final_size, 0,
        'Case 2: Target EnvNode is not empty.')
        self.assertEqual(grabbed_population_size, 300,
        'Case 2: Grabbed population size is not equal to grabbed amount.')
        self.assertTrue(len(target_node.contained_blobs) == 0,
        'Case 2: Target EnvNode has a different number of Blobs than intended.')
        self.assertTrue(verify_node_validity(target_node),
        'Case 2: Grabbed pop still in node.')
        self.assertTrue(verify_graph_validity_size(self.envA, 700 - grabbed_population_size),
        'Case 2: EnvironmentGraph changed in size.')
        self.assertTrue(all([(x in grabbed_population) for x in original_blobs]),
        'Case 2: Blob is not the same which was in the node.')
        
        # Returns Blobs to target node for next Case
        target_node.add_blobs(grabbed_population)
        
        # Case 3:
        # Gets a target EnvNode with population 100
        target_node = self.envA.get_node_by_name("Centro", "home")
        node_blobs = target_node.contained_blobs
        
        # Gets the first Blob in target node
        source_blob = node_blobs[0]

        # Copy two extra Blobs with same profile
        clone_blob_1 = source_blob.blob_factory.GenerateProfile(0, 100, source_blob.profiles)
        clone_blob_2 = source_blob.blob_factory.GenerateProfile(0, 100, source_blob.profiles)

        # Adds extra Blobs to target node
        target_node.add_blobs([clone_blob_1, clone_blob_2])
        original_blobs = [source_blob, clone_blob_1, clone_blob_2]

        # Grabs 600 people from the target node - more than available
        node_original_size = target_node.get_population_size()
        grabbed_population = target_node.grab_population(600)
        node_final_size = target_node.get_population_size()
        grabbed_population_size = blobs_total_size(grabbed_population)
        
        # assert validity and correct sizes
        self.assertTrue(verify_blobs_validity(grabbed_population),
        'Case 3: Grabbed population is not valid.')
        self.assertTrue(not verify_blobs_contained_in_node(grabbed_population, target_node),
        'Case 3: Grabbed pop still in node.')
        self.assertTrue(not verify_blobs_contained_in_node(original_blobs, target_node),
        'Case 3: Grabbed pop still in node.')
        self.assertEqual(node_original_size, node_final_size + grabbed_population_size,
        'Case 3: Total population size changed.')
        self.assertEqual(node_final_size, 0,
        'Case 3: Target EnvNode is not empty.')
        self.assertEqual(grabbed_population_size, 300,
        'Case 3: Grabbed population size is not equal to grabbed amount.')
        self.assertTrue(len(target_node.contained_blobs) == 0,
        'Case 3: Target EnvNode has a different number of Blobs than intended.')
        self.assertTrue(verify_node_validity(target_node),
        'Case 3: Grabbed pop still in node.')
        self.assertTrue(verify_graph_validity_size(self.envA, 900 - grabbed_population_size),
        'Case 3: EnvironmentGraph changed in size.')
        self.assertTrue(all([(x in grabbed_population) for x in original_blobs]),
        'Case 3: Blob is not the same which was in the node.')
        
    ## EnvNode.grab_population - without template - unbalanced Blobs in Node 
    def test_node_grab_population_no_template_three_blobs_unbalanced(self):
        """Tests EnvNode.grab_population
        
        extra_blob_4 is invalid (None), by choice.

        Case 1: 
            action: Less population than available, one blob has population 0.
                    0 pop blob represents an unmatching population template blob.
                    One blob has less population.

            result: Node is valid.
                    Blobs are valid.
                    Blobs in list are different than one in the node.
                    Total population size unchanged.
                    
        Case 2: 
            action: Equal population as available, one blob has population 0.
                    0 pop blob represents an unmatching population template blob.
                    One blob has less population.
            result: Node is valid.
                    Blobs are valid.
                    Node is empty.
                    3 Blobs are in list.
                    Total population size unchanged.
                    
        Case 3: 
            action: More population than available, one blob has population 0.
                    0 pop blob represents an unmatching population template blob.
                    One blob has less population.
            result: Node is valid.
                    No population is removed.
                    3 Blobs are in list.
                    Total population size unchanged.
                    Returns an empty list.
        """
        
        # Case 1:
        # Gets a target EnvNode with population 100
        target_node = self.envA.get_node_by_name("Petropolis", "home")
        node_blobs = target_node.contained_blobs
        
        # Gets the first Blob in target node
        source_blob = node_blobs[0]

        # Copy four extra Blobs with same profile - clone_blob_4 should ne None
        extra_blob_1 = source_blob.blob_factory.GenerateProfile(0, 100, source_blob.profiles)
        extra_blob_2 = source_blob.blob_factory.Generate(0, 190)
        extra_blob_3 = source_blob.blob_factory.Generate(0, 10)
        extra_blob_4 = source_blob.blob_factory.Generate(0, 0)
        
        # Adds extra Blobs to target node
        target_node.add_blobs([extra_blob_1, extra_blob_2, extra_blob_3, extra_blob_4])
        
        # Grabs 200 people from the target node - less than available
        node_original_size = target_node.get_population_size()
        grabbed_population = target_node.grab_population(200)
        source_final_size = target_node.get_population_size()
        grabbed_population_size = blobs_total_size(grabbed_population)

        # Clean up node
        target_node.remove_blob(extra_blob_4)
        
        # assert validity and correct sizes
        self.assertTrue(verify_blobs_validity(grabbed_population),
        'Case 1: Grabbed population is not valid.')
        self.assertTrue(not verify_blobs_contained_in_node(grabbed_population, target_node),
        'Case 1: Grabbed pop still in node.')
        self.assertEqual(node_original_size, source_final_size + grabbed_population_size,
        'Case 1: Total population size changed.')
        self.assertEqual(grabbed_population_size, 200,
        'Case 1: Grabbed population size is not equal to grabbed amount.')
        self.assertTrue(len(target_node.contained_blobs) == 4,
        'Case 1: Target EnvNode has a different number of Blobs than intended.')
        self.assertTrue(verify_node_validity(target_node),
        'Case 1: Grabbed pop still in node.')
        self.assertEqual(extra_blob_4, None, 'Case 1: Cloned Blob should be None.')
        self.assertTrue(verify_graph_validity_size(self.envA, 600 - grabbed_population_size),
        'Case 1: EnvironmentGraph changed in size.')
        
        # Returns Blobs to target node for next Case
        target_node.add_blobs(grabbed_population)
        
        # Case 2:
        # Gets a target EnvNode with population 100
        target_node = self.envA.get_node_by_name("Partenon", "home")
        node_blobs = target_node.contained_blobs
        
        # Gets the first Blob in target node
        source_blob = node_blobs[0]

        # Copy four extra Blobs with same profile - clone_blob_4 should ne None
        extra_blob_1 = source_blob.blob_factory.GenerateProfile(0, 100, source_blob.profiles)
        extra_blob_2 = source_blob.blob_factory.Generate(0, 190)
        extra_blob_3 = source_blob.blob_factory.Generate(0, 10)
        extra_blob_4 = source_blob.blob_factory.Generate(0, 0)
        
        # Adds extra Blobs to target node
        target_node.add_blobs([extra_blob_1, extra_blob_2, extra_blob_3, extra_blob_4])
        original_blobs = [source_blob, extra_blob_1, extra_blob_2, extra_blob_3]
                       
        # Grabs 400 people from the target node - equal as available
        node_original_size = target_node.get_population_size()
        grabbed_population = target_node.grab_population(400)
        node_final_size = target_node.get_population_size()
        grabbed_population_size = blobs_total_size(grabbed_population)

        # Clean up node
        target_node.remove_blob(extra_blob_4)

        # assert validity and correct sizes
        self.assertTrue(verify_blobs_validity(grabbed_population),
        'Case 2: Grabbed population is not valid.')
        self.assertTrue(not verify_blobs_contained_in_node(grabbed_population, target_node),
        'Case 2: Grabbed pop still in node.')
        self.assertTrue(not verify_blobs_contained_in_node(original_blobs, target_node),
        'Case 2: Grabbed pop still in node.')
        self.assertEqual(node_original_size, node_final_size + grabbed_population_size,
        'Case 2: Total population size changed.')
        self.assertEqual(node_final_size, 0,
        'Case 2: Target EnvNode is not empty.')
        self.assertEqual(grabbed_population_size, 400,
        'Case 2: Grabbed population size is not equal to grabbed amount.')
        self.assertTrue(len(target_node.contained_blobs) == 0,
        'Case 2: Target EnvNode has a different number of Blobs than intended.')
        self.assertTrue(verify_node_validity(target_node),
        'Case 2: Grabbed pop still in node.')
        self.assertTrue(verify_graph_validity_size(self.envA, 900 - grabbed_population_size),
        'Case 2: EnvironmentGraph changed in size.')
        self.assertTrue(all([(x in grabbed_population) for x in original_blobs]),
        'Case 2: Blob is not the same which was in the node.')
        
        # Returns Blobs to target node for next Case
        target_node.add_blobs(grabbed_population)
        
        # Case 3:
        # Gets a target EnvNode with population 100
        target_node = self.envA.get_node_by_name("Centro", "home")
        node_blobs = target_node.contained_blobs
        
        # Gets the first Blob in target node
        source_blob = node_blobs[0]

        # Copy four extra Blobs with same profile - clone_blob_4 should ne None
        extra_blob_1 = source_blob.blob_factory.GenerateProfile(0, 100, source_blob.profiles)
        extra_blob_2 = source_blob.blob_factory.Generate(0, 190)
        extra_blob_3 = source_blob.blob_factory.Generate(0, 10)
        extra_blob_4 = source_blob.blob_factory.Generate(0, 0)
        
        # Adds extra Blobs to target node
        target_node.add_blobs([extra_blob_1, extra_blob_2, extra_blob_3, extra_blob_4])
        original_blobs = [source_blob, extra_blob_1, extra_blob_2, extra_blob_3]
                       
        # Grabs 600 people from the target node - more than available
        node_original_size = target_node.get_population_size()
        grabbed_population = target_node.grab_population(600)
        node_final_size = target_node.get_population_size()
        grabbed_population_size = blobs_total_size(grabbed_population)
        
        # Clean up node
        target_node.remove_blob(extra_blob_4)

        # assert validity and correct sizes
        self.assertTrue(verify_blobs_validity(grabbed_population),
        'Case 3: Grabbed population is not valid.')
        self.assertTrue(not verify_blobs_contained_in_node(grabbed_population, target_node),
        'Case 3: Grabbed pop still in node.')
        self.assertTrue(not verify_blobs_contained_in_node(original_blobs, target_node),
        'Case 3: Grabbed pop still in node.')
        self.assertEqual(node_original_size, node_final_size + grabbed_population_size,
        'Case 3: Total population size changed.')
        self.assertEqual(node_final_size, 0,
        'Case 3: Target EnvNode is not empty.')
        self.assertEqual(grabbed_population_size, 400,
        'Case 3: Grabbed population size is not equal to grabbed amount.')
        self.assertTrue(len(target_node.contained_blobs) == 0,
        'Case 3: Target EnvNode has a different number of Blobs than intended.')
        self.assertTrue(verify_node_validity(target_node),
        'Case 3: Grabbed pop still in node.')
        self.assertTrue(verify_graph_validity_size(self.envA, 1200 - grabbed_population_size),
        'Case 3: EnvironmentGraph changed in size.')
        self.assertTrue(all([(x in grabbed_population) for x in original_blobs]),
        'Case 3: Blob is not the same which was in the node.')

    ## EnvNode.grab_population - with template - one Blob in EnvNode
    def test_node_grab_population_with_template_one_blob(self):
        """Tests EnvNode.grab_population
        
        Grab population using a PopTemplate
        
        Case 1: 
            action: Requests less population than available.
            result: Node is valid.
                    Blobs are valid.
                    Grabbed Blob is different than one in the node.
                    Total population size unchanged.
                    Blob size equals extracted quantity.      
                    
        Case 2: 
            action: Equal population as available.
            result: Node is valid.
                    Blobs is valid.
                    Grabbed Blob is different than one in the node.
                    Total population size unchanged.
                    Blob size equals extracted quantity.
                    
        Case 3: 
            action: More population than available.
            result: Node is valid.
                    Blobs is valid.
                    Grabbed Blob is different than one in the node.
                    Total population size unchanged.
                    Blob size equals extracted quantity.
        """
        # Sets a PopTemplate
        pop_template = PopTemplate() 
        pop_template.set_sampled_property('age', ['adults', 'elders'])
        pop_template.set_sampled_property('occupation', ['idle', 'worker'])
                
        # Case 1:
        # Gets a target EnvNode with population 100
        target_node = self.envA.get_node_by_name("Petropolis", "home")
        source_blob = target_node.contained_blobs[0]
        node_original_size = target_node.get_population_size()
        source_original_size = source_blob.get_population_size()

        # Grabs 30 people from the target node - less than available
        grabbed_population = target_node.grab_population(30, pop_template)
        node_final_size = target_node.get_population_size()
        source_final_size = source_blob.get_population_size()
        grabbed_population_size = blobs_total_size(grabbed_population)

        # assert validity and correct sizes
        self.assertTrue(verify_blobs_validity(grabbed_population),
        'Case 1: Grabbed population is not valid.')
        self.assertTrue(not verify_blobs_contained_in_node(grabbed_population, target_node),
        'Case 1: Grabbed population still in EnvNode.')
        self.assertTrue(verify_blob_contained_in_node(source_blob, target_node),
        'Case 1: Source Blob is not in EnvNode.')
        self.assertEqual(node_original_size, node_final_size + grabbed_population_size,
        'Case 1: Total population size changed.')
        self.assertEqual(source_original_size, source_final_size + grabbed_population_size,
        'Case 1: Source population size changed.')
        self.assertEqual(grabbed_population_size, 30,
        'Case 1: Grabbed population size is not equal to grabbed amount.')
        self.assertTrue(verify_graph_validity_size(self.envA, 300 - grabbed_population_size),
        'Case 1: EnvironmentGraph changed in size.')
        self.assertTrue(verify_node_validity(target_node),
        'Case 1: Grabbed pop still in node.')
        
        # Returns Blobs to target node for next Case
        target_node.add_blobs(grabbed_population)
        
        # Case 2:
        # Gets a target EnvNode with population 100
        target_node = self.envA.get_node_by_name("Partenon", "home")
        source_blob = target_node.contained_blobs[0]
        node_original_size = target_node.get_population_size()
        source_original_size = source_blob.get_population_size()
        
        # Grabs 60 people from the target node - equal as available
        grabbed_population = target_node.grab_population(60, pop_template)
        node_final_size = target_node.get_population_size()
        source_final_size = source_blob.get_population_size()
        grabbed_population_size = blobs_total_size(grabbed_population)

        # assert validity and correct sizes
        self.assertTrue(verify_blobs_validity(grabbed_population),
        'Case 2: Grabbed population is not valid.')
        self.assertTrue(not verify_blobs_contained_in_node(grabbed_population, target_node),
        'Case 2: Grabbed population still in EnvNode.')
        self.assertTrue(verify_blob_contained_in_node(source_blob, target_node),
        'Case 2: Source Blob is not in EnvNode.')
        self.assertEqual(node_original_size, node_final_size + grabbed_population_size,
        'Case 2: Total population size changed.')
        self.assertEqual(source_original_size, source_final_size + grabbed_population_size,
        'Case 2: Source population size changed.')
        self.assertEqual(grabbed_population_size, 60,
        'Case 2: Grabbed population size is not equal to grabbed amount.')
        self.assertTrue(verify_graph_validity_size(self.envA, 300 - grabbed_population_size),
        'Case 2: EnvironmentGraph changed in size.')
        self.assertTrue(verify_node_validity(target_node),
        'Case 2: Grabbed pop still in node.')
        
        # Returns Blobs to target node for next Case
        target_node.add_blobs(grabbed_population)
        
        # Case 3:
        # Gets a target EnvNode with population 100
        target_node = self.envA.get_node_by_name("Centro", "home")
        source_blob = target_node.contained_blobs[0]
        node_original_size = target_node.get_population_size()
        source_original_size = source_blob.get_population_size()

        # Grabs 120 people from the target node - more than available
        grabbed_population = target_node.grab_population(120, pop_template)
        node_final_size = target_node.get_population_size()
        source_final_size = source_blob.get_population_size()
        grabbed_population_size = blobs_total_size(grabbed_population)

        # assert validity and correct sizes
        self.assertTrue(verify_blobs_validity(grabbed_population),
        'Case 3: Grabbed population is not valid.')
        self.assertTrue(not verify_blobs_contained_in_node(grabbed_population, target_node),
        'Case 3: Grabbed population still in EnvNode.')
        self.assertTrue(verify_blob_contained_in_node(source_blob, target_node),
        'Case 3: Source Blob is not in EnvNode.')
        self.assertEqual(node_original_size, node_final_size + grabbed_population_size,
        'Case 3: Total population size changed.')
        self.assertEqual(source_original_size, source_final_size + grabbed_population_size,
        'Case 3: Source population size changed.')
        self.assertEqual(grabbed_population_size, 60,
        'Case 3: Grabbed population size is not equal to grabbed amount.')
        self.assertTrue(verify_graph_validity_size(self.envA, 300 - grabbed_population_size),
        'Case 3: EnvironmentGraph changed in size.')
        self.assertTrue(verify_node_validity(target_node),
        'Case 3: Grabbed pop still in node.')
        
    ## EnvNode.grab_population - with template - three Blobs in EnvNode
    def test_node_grab_population_with_template_three_blobs(self):
        """Tests EnvNode.grab_population
        
        Clone two extra Blobs in a EnvNode. Then, grabs population from node

        Case 1: 
            action: Less population than available.
            result: Node is valid.
                    Blobs are valid.
                    Blobs in list are different than one in the node.
                    Total population size unchanged.    
                    
        Case 2: 
            action: Equal population as available.
            result: Node is valid.
                    Blobs are valid.
                    Node is not empty.
                    3 Blobs are in list.
                    Blobs in list are different than one in the node.
                    Total population size unchanged.
                    
        Case 3: 
            action: More population than available.
            result: Node is valid.
                    Blobs are valid.
                    Node is not empty.
                    3 Blobs are in list.
                    Blobs in list are different than one in the node.
                    Total population size unchanged.
        """
        # Sets a PopTemplate
        pop_template = PopTemplate() 
        pop_template.set_sampled_property('age', ['adults', 'elders'])
        pop_template.set_sampled_property('occupation', ['idle', 'worker'])

        # Case 1:
        # Gets a target EnvNode with population 100
        target_node = self.envA.get_node_by_name("Petropolis", "home")

        # Gets the first Blob in target node
        source_blob = target_node.contained_blobs[0]

        # Copy two extra Blobs with same profile
        clone_blob_1 = source_blob.blob_factory.GenerateProfile(0, 100, source_blob.profiles, source_blob.traceable_properties)
        clone_blob_2 = source_blob.blob_factory.GenerateProfile(0, 100, source_blob.profiles, source_blob.traceable_properties)
        
        # Adds extra Blobs to target node
        target_node.add_blobs([clone_blob_1, clone_blob_2])
        original_blobs = target_node.contained_blobs
        
        # Grabs 90 people from the target node - less than available
        node_original_size = target_node.get_population_size()
        grabbed_population = target_node.grab_population(90, pop_template)
        node_final_size = target_node.get_population_size()
        grabbed_population_size = blobs_total_size(grabbed_population)

        # assert validity and correct sizes
        self.assertTrue(verify_blobs_validity(grabbed_population),
        'Case 1: Grabbed population is not valid.')
        self.assertTrue(not verify_blobs_contained_in_node(grabbed_population, target_node),
        'Case 1: Grabbed pop still in node.')
        self.assertTrue(verify_blobs_contained_in_node(original_blobs, target_node),
        'Case 2: Grabbed pop still in node.')
        self.assertEqual(node_original_size, node_final_size + grabbed_population_size,
        'Case 1: Total population size changed.')
        self.assertEqual(grabbed_population_size, 90,
        'Case 1: Grabbed population size is not equal to grabbed amount.')
        self.assertTrue(len(target_node.contained_blobs) == 3,
        'Case 1: Target EnvNode has a different number of Blobs than intended.')
        self.assertTrue(verify_node_validity(target_node),
        'Case 1: Grabbed pop still in node.')
        self.assertTrue(verify_graph_validity_size(self.envA, 500 - grabbed_population_size),
        'Case 1: EnvironmentGraph changed in size.')
        
        # Returns Blobs to target node for next Case
        target_node.add_blobs(grabbed_population)
        
        # Case 2:
        # Gets a target EnvNode with population 100
        target_node = self.envA.get_node_by_name("Partenon", "home")
        node_blobs = target_node.contained_blobs

        # Gets the first Blob in target node
        source_blob = node_blobs[0]

        # Copy two extra Blobs with same profile
        clone_blob_1 = source_blob.blob_factory.GenerateProfile(0, 100, source_blob.profiles)
        clone_blob_2 = source_blob.blob_factory.GenerateProfile(0, 100, source_blob.profiles)
        
        # Adds extra Blobs to target node
        target_node.add_blobs([clone_blob_1, clone_blob_2])
        original_blobs = [source_blob, clone_blob_1, clone_blob_2]

        # Grabs 300 people from the target node - equal as available
        node_original_size = target_node.get_population_size()
        grabbed_population = target_node.grab_population(180, pop_template)
        node_final_size = target_node.get_population_size()
        grabbed_population_size = blobs_total_size(grabbed_population)

        # assert validity and correct sizes
        self.assertTrue(verify_blobs_validity(grabbed_population),
        'Case 2: Grabbed population is not valid.')
        self.assertTrue(not verify_blobs_contained_in_node(grabbed_population, target_node),
        'Case 2: Grabbed pop still in node.')
        self.assertTrue(verify_blobs_contained_in_node(original_blobs, target_node),
        'Case 2: Grabbed pop still in node.')
        self.assertEqual(node_original_size, node_final_size + grabbed_population_size,
        'Case 2: Total population size changed.')
        self.assertEqual(grabbed_population_size, 180,
        'Case 2: Grabbed population size is not equal to grabbed amount.')
        self.assertTrue(len(target_node.contained_blobs) == 3,
        'Case 2: Target EnvNode has a different number of Blobs than intended.')
        self.assertTrue(verify_node_validity(target_node),
        'Case 2: Grabbed pop still in node.')
        self.assertTrue(verify_graph_validity_size(self.envA, 700 - grabbed_population_size),
        'Case 2: EnvironmentGraph changed in size.')
        self.assertTrue(all([(x not in grabbed_population) for x in original_blobs]),
        'Case 2: Blob is the same which was in the node.')
        
        # Returns Blobs to target node for next Case
        target_node.add_blobs(grabbed_population)
        
        # Case 3:
        # Gets a target EnvNode with population 100
        target_node = self.envA.get_node_by_name("Centro", "home")
        node_blobs = target_node.contained_blobs
        
        # Gets the first Blob in target node
        source_blob = node_blobs[0]

        # Copy two extra Blobs with same profile
        clone_blob_1 = source_blob.blob_factory.GenerateProfile(0, 100, source_blob.profiles)
        clone_blob_2 = source_blob.blob_factory.GenerateProfile(0, 100, source_blob.profiles)

        # Adds extra Blobs to target node
        target_node.add_blobs([clone_blob_1, clone_blob_2])
        original_blobs = [source_blob, clone_blob_1, clone_blob_2]

        # Grabs 360 people from the target node - more than available
        node_original_size = target_node.get_population_size()
        grabbed_population = target_node.grab_population(360, pop_template)
        node_final_size = target_node.get_population_size()
        grabbed_population_size = blobs_total_size(grabbed_population)
        
        # assert validity and correct sizes
        self.assertTrue(verify_blobs_validity(grabbed_population),
        'Case 3: Grabbed population is not valid.')
        self.assertTrue(not verify_blobs_contained_in_node(grabbed_population, target_node),
        'Case 3: Grabbed pop still in node.')
        self.assertTrue(verify_blobs_contained_in_node(original_blobs, target_node),
        'Case 3: Grabbed pop still in node.')
        self.assertEqual(node_original_size, node_final_size + grabbed_population_size,
        'Case 3: Total population size changed.')
        self.assertEqual(grabbed_population_size, 180,
        'Case 3: Grabbed population size is not equal to grabbed amount.')
        self.assertTrue(len(target_node.contained_blobs) == 3,
        'Case 3: Target EnvNode has a different number of Blobs than intended.')
        self.assertTrue(verify_node_validity(target_node),
        'Case 3: Grabbed pop still in node.')
        self.assertTrue(verify_graph_validity_size(self.envA, 900 - grabbed_population_size),
        'Case 3: EnvironmentGraph changed in size.')
        self.assertTrue(all([(x not in grabbed_population) for x in original_blobs]),
        'Case 3: Blob is the same which was in the node.')
        
    ## EnvNode.grab_population - with template - unbalanced Blobs in Node 
    def test_node_grab_population_with_template_three_blobs_unbalanced(self):
        """Tests EnvNode.grab_population
        
        extra_blob_4 is invalid (None), by choice.

        Case 1: 
            action: Less population than available.
            result: Node is valid.
                    Blobs are valid.
                    Blobs in list are different than one in the node.
                    Total population size unchanged.    
                    
        Case 2: 
            action: Equal population as available.
            result: Node is valid.
                    Blobs are valid.
                    Node is not empty.
                    3 Blobs are in list.
                    Blobs in list are different than one in the node.
                    Total population size unchanged.
                    
        Case 3: 
            action: More population than available.
            result: Node is valid.
                    Blobs are valid.
                    Node is not empty.
                    3 Blobs are in list.
                    Blobs in list are different than one in the node.
                    Total population size unchanged.
        """
        # Sets a PopTemplate
        pop_template = PopTemplate() 
        pop_template.set_sampled_property('age', ['adults', 'elders'])
        pop_template.set_sampled_property('occupation', ['idle', 'worker'])
        
        # Case 1:
        # Gets a target EnvNode with population 100
        target_node = self.envA.get_node_by_name("Petropolis", "home")
        
        # Gets the first Blob in target node
        source_blob = target_node.contained_blobs[0]
        
        # Copy four extra Blobs with same profile - clone_blob_4 should ne None
        extra_blob_1 = source_blob.blob_factory.GenerateProfile(0, 100, source_blob.profiles)
        extra_blob_2 = source_blob.blob_factory.Generate(0, 190)
        extra_blob_3 = source_blob.blob_factory.Generate(0, 10)
        extra_blob_4 = source_blob.blob_factory.Generate(0, 0)
        
        # Adds extra Blobs to target node
        target_node.add_blobs([extra_blob_1, extra_blob_2, extra_blob_3, extra_blob_4])
        available_population = target_node.get_population_size(pop_template)
        
        # Grabs half the available people from the target node
        node_original_size = target_node.get_population_size()
        grabbed_population = target_node.grab_population(available_population//2, pop_template)
        source_final_size = target_node.get_population_size()
        grabbed_population_size = blobs_total_size(grabbed_population)

        # Clean up node
        target_node.remove_blob(extra_blob_4)
        
        # assert validity and correct sizes
        self.assertTrue(verify_blobs_validity(grabbed_population),
        'Case 1: Grabbed population is not valid.')
        self.assertTrue(not verify_blobs_contained_in_node(grabbed_population, target_node),
        'Case 1: Grabbed pop still in node.')
        self.assertEqual(node_original_size, source_final_size + grabbed_population_size,
        'Case 1: Total population size changed.')
        self.assertEqual(grabbed_population_size, available_population//2,
        'Case 1: Grabbed population size is not equal to grabbed amount.')
        self.assertTrue(len(target_node.contained_blobs) == 4,
        'Case 1: Target EnvNode has a different number of Blobs than intended.')
        self.assertTrue(verify_node_validity(target_node),
        'Case 1: Grabbed pop still in node.')
        self.assertEqual(extra_blob_4, None, 'Case 1: Cloned Blob should be None.')
        self.assertTrue(verify_graph_validity_size(self.envA, 600 - grabbed_population_size),
        'Case 1: EnvironmentGraph changed in size.')
        
        # Returns Blobs to target node for next Case
        target_node.add_blobs(grabbed_population)
        
        # Case 2:
        # Gets a target EnvNode with population 100
        target_node = self.envA.get_node_by_name("Partenon", "home")
        node_blobs = target_node.contained_blobs
        
        # Gets the first Blob in target node
        source_blob = node_blobs[0]

        # Copy four extra Blobs with same profile - clone_blob_4 should ne None
        extra_blob_1 = source_blob.blob_factory.GenerateProfile(0, 100, source_blob.profiles)
        extra_blob_2 = source_blob.blob_factory.Generate(0, 190)
        extra_blob_3 = source_blob.blob_factory.Generate(0, 10)
        extra_blob_4 = source_blob.blob_factory.Generate(0, 0)
        
        # Adds extra Blobs to target node
        target_node.add_blobs([extra_blob_1, extra_blob_2, extra_blob_3, extra_blob_4])
        original_blobs = [source_blob, extra_blob_1, extra_blob_2, extra_blob_3]
        available_population = target_node.get_population_size(pop_template)
                       
        # Grabs the available amount of people from the target node
        node_original_size = target_node.get_population_size()
        grabbed_population = target_node.grab_population(available_population, pop_template)
        node_final_size = target_node.get_population_size()
        grabbed_population_size = blobs_total_size(grabbed_population)

        # Clean up node
        target_node.remove_blob(extra_blob_4)

        # assert validity and correct sizes
        self.assertTrue(verify_blobs_validity(grabbed_population),
        'Case 2: Grabbed population is not valid.')
        self.assertTrue(not verify_blobs_contained_in_node(grabbed_population, target_node),
        'Case 2: Grabbed pop still in node.')
        self.assertEqual(node_original_size, node_final_size + grabbed_population_size,
        'Case 2: Total population size changed.')
        self.assertEqual(grabbed_population_size, available_population,
        'Case 2: Grabbed population size is not equal to grabbed amount.')
        self.assertTrue(len(target_node.contained_blobs) > 0,
        'Case 2: Target EnvNode has a different number of Blobs than intended.')
        self.assertTrue(verify_node_validity(target_node),
        'Case 2: Grabbed pop still in node.')
        self.assertTrue(verify_graph_validity_size(self.envA, 900 - grabbed_population_size),
        'Case 2: EnvironmentGraph changed in size.')
        self.assertTrue(all([(x not in grabbed_population) for x in original_blobs]),
        'Case 2: Blob is the same which was in the node.')
        
        # Returns Blobs to target node for next Case
        target_node.add_blobs(grabbed_population)
        
        # Case 3:
        # Gets a target EnvNode with population 100
        target_node = self.envA.get_node_by_name("Centro", "home")
        node_blobs = target_node.contained_blobs
        
        # Gets the first Blob in target node
        source_blob = node_blobs[0]

        # Copy four extra Blobs with same profile - clone_blob_4 should ne None
        extra_blob_1 = source_blob.blob_factory.GenerateProfile(0, 100, source_blob.profiles)
        extra_blob_2 = source_blob.blob_factory.Generate(0, 190)
        extra_blob_3 = source_blob.blob_factory.Generate(0, 10)
        extra_blob_4 = source_blob.blob_factory.Generate(0, 0)
        
        # Adds extra Blobs to target node
        target_node.add_blobs([extra_blob_1, extra_blob_2, extra_blob_3, extra_blob_4])
        original_blobs = [source_blob, extra_blob_1, extra_blob_2, extra_blob_3]
        available_population = target_node.get_population_size(pop_template)
                       
        # Grabs double than available population from the target node
        node_original_size = target_node.get_population_size()
        grabbed_population = target_node.grab_population(available_population * 2, pop_template)
        node_final_size = target_node.get_population_size()
        grabbed_population_size = blobs_total_size(grabbed_population)
        
        # Clean up node
        target_node.remove_blob(extra_blob_4)

        # assert validity and correct sizes
        self.assertTrue(verify_blobs_validity(grabbed_population),
        'Case 3: Grabbed population is not valid.')
        self.assertTrue(not verify_blobs_contained_in_node(grabbed_population, target_node),
        'Case 3: Grabbed pop still in node.')
        self.assertEqual(node_original_size, node_final_size + grabbed_population_size,
        'Case 3: Total population size changed.')
        self.assertEqual(grabbed_population_size, available_population,
        'Case 3: Grabbed population size is not equal to grabbed amount.')
        self.assertTrue(len(target_node.contained_blobs) > 0,
        'Case 3: Target EnvNode has a different number of Blobs than intended.')
        self.assertTrue(verify_node_validity(target_node),
        'Case 3: Grabbed pop still in node.')
        self.assertTrue(verify_graph_validity_size(self.envA, 1200 - grabbed_population_size),
        'Case 3: EnvironmentGraph changed in size.')
        self.assertTrue(all([(x not in grabbed_population) for x in original_blobs]),
        'Case 3: Blob is not the same which was in the node.')

    ## EnvNode.grab_population - with template - two grab operations with complementing templates
    def test_node_grab_population_with_complementing_templates(self):
        """Tests EnvNode.grab_population
        
        Grab population using a PopTemplate. Then, sets the template to request other property values and Grabs population again. 
        
        Case 1: 
            action: Requests population equal as available using a template.
            result: Node is valid.
                    Blobs are valid.
                    Grabbed Blob is different than one in the node.
                    Total population size unchanged.
                    Blob size equals extracted quantity.      
                    
        Case 2: 
            action: Equal population as available.
            result: Node is valid.
                    Node is empty.
                    Blobs are valid.
                    Blob is the same as the one that was in the in the node.
                    Total population size unchanged.
                    Blob size equals extracted quantity.
        """
        
        # Sets two complementing PopTemplates
        pop_template_A = PopTemplate() 
        pop_template_A.set_sampled_property('age', ['adults', 'elders'])
        pop_template_A.set_sampled_property('occupation', ['idle', 'worker'])
        pop_template_A.set_sampled_property('social_profile', ['mid', 'high'])
        
        pop_template_B = PopTemplate() 
        pop_template_B.set_sampled_property('age', ['young', 'children'])
        pop_template_B.set_sampled_property('occupation', 'student')
        pop_template_B.set_sampled_property('social_profile', 'low')
                
        # Case 1:
        # Gets a target EnvNode with population 100
        target_node = self.envA.get_node_by_name("Petropolis", "home")
        source_blob = target_node.contained_blobs[0]
        node_original_size = target_node.get_population_size()
        source_original_size = source_blob.get_population_size()

        # Grabs 60 people from the target node - equal as available
        grabbed_population_A = target_node.grab_population(60, pop_template_A)
        node_final_size = target_node.get_population_size()
        source_final_size = source_blob.get_population_size()
        grabbed_population_A_size = blobs_total_size(grabbed_population_A)

        # assert validity and correct sizes
        self.assertTrue(verify_blobs_validity(grabbed_population_A),
        'Case 1: Grabbed population is not valid.')
        self.assertTrue(not verify_blobs_contained_in_node(grabbed_population_A, target_node),
        'Case 1: Grabbed population still in EnvNode.')
        self.assertTrue(verify_blob_contained_in_node(source_blob, target_node),
        'Case 1: Source Blob is not in EnvNode.')
        self.assertEqual(node_original_size, node_final_size + grabbed_population_A_size,
        'Case 1: Total population size changed.')
        self.assertEqual(source_original_size, source_final_size + grabbed_population_A_size,
        'Case 1: Source population size changed.')
        self.assertEqual(grabbed_population_A_size, 60,
        'Case 1: Grabbed population size is not equal to grabbed amount.')
        self.assertTrue(verify_graph_validity_size(self.envA, 300 - grabbed_population_A_size),
        'Case 1: EnvironmentGraph changed in size.')
        self.assertTrue(verify_node_validity(target_node),
        'Case 1: Grabbed pop still in node.')
        
        # Case 2:
        # Gets a target EnvNode with the remaining population of 40
        target_node = self.envA.get_node_by_name("Petropolis", "home")
        source_blob = target_node.contained_blobs[0]
        node_original_size = target_node.get_population_size()
        source_original_size = source_blob.get_population_size()

        # Grabs 40 people from the target node - equal as available
        grabbed_population_B = target_node.grab_population(40, pop_template_B)
        node_final_size = target_node.get_population_size()
        source_final_size = source_blob.get_population_size()
        grabbed_population_B_size = blobs_total_size(grabbed_population_B)
        
        # assert validity and correct sizes
        self.assertTrue(verify_blobs_validity(grabbed_population_B),
        'Case 2: Grabbed population is not valid.')
        self.assertTrue(not verify_blobs_contained_in_node(grabbed_population_B, target_node),
        'Case 2: Grabbed population still in EnvNode.')
        self.assertTrue(not verify_blob_contained_in_node(source_blob, target_node),
        'Case 2: Source Blob is not in EnvNode.')
        self.assertEqual(node_original_size, node_final_size + grabbed_population_B_size,
        'Case 2: Total population size changed.')
        self.assertEqual(source_original_size, source_final_size,
        'Case 2: Source population size changed.')
        self.assertEqual(grabbed_population_B_size, 40,
        'Case 2: Grabbed population size is not equal to grabbed amount.')
        self.assertTrue(verify_graph_validity_size(self.envA, 300 - grabbed_population_A_size - grabbed_population_B_size),
        'Case 2: EnvironmentGraph changed in size.')
        self.assertTrue(verify_node_validity(target_node),
        'Case 2: Grabbed pop still in node.')
        self.assertTrue(len(target_node.contained_blobs) == 0,
        'Case 2: Node is not empty.')
        self.assertEqual(source_blob, grabbed_population_B[0],
        'Case 2: Blob is not the same which was in the node.')

    ## EnvNode.grab_population - with traceable properties in the template
    def test_node_grab_population_traceable_properties(self):
        """Tests EnvNode.grab_population
        
        Grab population using a traceable property with one value in the PopTemplate
        
        Case 1: 
            action: Requests less population than available.
            result: Node is valid.
                    Blobs are valid.
                    Grabbed Blob is different than one in the node.
                    Total population size unchanged.
                    Blob size equals extracted quantity.      
                    
        Case 2: 
            action: Equal population as available.
            result: Node is valid.
                    Blobs is valid.
                    Grabbed Blob is different than one in the node.
                    Total population size unchanged.
                    Blob size equals extracted quantity.
                    
        Case 3: 
            action: More population than available.
            result: Node is valid.
                    Blobs is valid.
                    Grabbed Blob is different than one in the node.
                    Total population size unchanged.
                    Blob size equals extracted quantity.
        """
        # Sets a PopTemplate
        pop_template = PopTemplate() 
        pop_template.set_traceable_property('traceable_A', 'default')
                
        # Case 1:
        # Gets a target EnvNode with population 400
        target_node = self.envB.get_node_by_name("Petropolis", "home")
        node_original_size = target_node.get_population_size()

        # Grabs 100 people from the target node - less than available
        grabbed_population = target_node.grab_population(100, pop_template)
        node_final_size = target_node.get_population_size()
        grabbed_population_size = blobs_total_size(grabbed_population)

        # assert validity and correct sizes
        self.assertTrue(verify_blobs_validity(grabbed_population),
        'Case 1: Grabbed population is not valid.')
        self.assertTrue(not verify_blobs_contained_in_node(grabbed_population, target_node),
        'Case 1: Grabbed population still in EnvNode.')
        self.assertEqual(node_original_size, node_final_size + grabbed_population_size,
        'Case 1: Total population size changed.')
        self.assertEqual(grabbed_population_size, 100,
        'Case 1: Grabbed population size is not equal to grabbed amount.')
        self.assertEqual(len(grabbed_population), 2,
        'Case 1: Grabbed Blob count different than expected.')
        self.assertEqual(len(target_node.contained_blobs), 4,
        'Case 1: Node Blob count different than expected.')
        self.assertTrue(verify_graph_validity_size(self.envB, 1200 - grabbed_population_size),
        'Case 1: EnvironmentGraph changed in size.')
        self.assertTrue(verify_node_validity(target_node),
        'Case 1: Grabbed pop still in node.')
                
        # Returns Blobs to target node for next Case
        target_node.add_blobs(grabbed_population)
        
        # Case 2:
        # Gets a target EnvNode with population 400
        target_node = self.envB.get_node_by_name("Partenon", "home")
        node_original_size = target_node.get_population_size()
        
        # Grabs 200 people from the target node - equal as available
        grabbed_population = target_node.grab_population(200, pop_template)
        node_final_size = target_node.get_population_size()
        grabbed_population_size = blobs_total_size(grabbed_population)

        # assert validity and correct sizes
        self.assertTrue(verify_blobs_validity(grabbed_population),
        'Case 2: Grabbed population is not valid.')
        self.assertTrue(not verify_blobs_contained_in_node(grabbed_population, target_node),
        'Case 2: Grabbed population still in EnvNode.')
        self.assertEqual(node_original_size, node_final_size + grabbed_population_size,
        'Case 2: Total population size changed.')
        self.assertEqual(grabbed_population_size, 200,
        'Case 2: Grabbed population size is not equal to grabbed amount.')
        self.assertEqual(len(grabbed_population), 2,
        'Case 1: Grabbed Blob count different than expected.')
        self.assertEqual(len(target_node.contained_blobs), 2,
        'Case 1: Node Blob count different than expected.')
        self.assertTrue(verify_graph_validity_size(self.envB, 1200 - grabbed_population_size),
        'Case 2: EnvironmentGraph changed in size.')
        self.assertTrue(verify_node_validity(target_node),
        'Case 2: Grabbed pop still in node.')
        
        # Returns Blobs to target node for next Case
        target_node.add_blobs(grabbed_population)
                
        # Case 3:
        # Gets a target EnvNode with population 400
        target_node = self.envB.get_node_by_name("Centro", "home")
        node_original_size = target_node.get_population_size()

        # Grabs 400 people from the target node - more than available
        grabbed_population = target_node.grab_population(400, pop_template)
        node_final_size = target_node.get_population_size()
        grabbed_population_size = blobs_total_size(grabbed_population)

        # assert validity and correct sizes
        self.assertTrue(verify_blobs_validity(grabbed_population),
        'Case 3: Grabbed population is not valid.')
        self.assertTrue(not verify_blobs_contained_in_node(grabbed_population, target_node),
        'Case 3: Grabbed population still in EnvNode.')
        self.assertEqual(node_original_size, node_final_size + grabbed_population_size,
        'Case 3: Total population size changed.')
        self.assertEqual(grabbed_population_size, 200,
        'Case 3: Grabbed population size is not equal to grabbed amount.')
        self.assertEqual(len(grabbed_population), 2,
        'Case 3: Grabbed Blob count different than expected.')
        self.assertEqual(len(target_node.contained_blobs), 2,
        'Case 3: Node Blob count different than expected.')
        self.assertTrue(verify_graph_validity_size(self.envB, 1200 - grabbed_population_size),
        'Case 3: EnvironmentGraph changed in size.')
        self.assertTrue(verify_node_validity(target_node),
        'Case 3: Grabbed pop still in node.')
        
    ## EnvNode.grab_population - with multiple values for a traceable property in the template
    def test_node_grab_population_traceable_properties_multiple_values(self):
        """Tests EnvNode.grab_population
        
        Grab population using a traceable property with all possible values in the PopTemplate
        
        Case 1: 
            action: Requests less population than available.
            result: Node is valid.
                    Blobs are valid.
                    Grabbed Blob is different than one in the node.
                    Total population size unchanged.
                    Blob size equals extracted quantity.      
                    
        Case 2: 
            action: Equal population as available.
            result: Node is valid.
                    Blobs is valid.
                    Grabbed Blob is different than one in the node.
                    Total population size unchanged.
                    Blob size equals extracted quantity.
                    
        Case 3: 
            action: More population than available.
            result: Node is valid.
                    Blobs is valid.
                    Grabbed Blob is different than one in the node.
                    Total population size unchanged.
                    Blob size equals extracted quantity.
        """
        # Sets a PopTemplate
        pop_template = PopTemplate() 
        pop_template.set_traceable_property('traceable_A', ['default', 'other_value'])
                
        # Case 1:
        # Gets a target EnvNode with population 400
        target_node = self.envB.get_node_by_name("Petropolis", "home")
        node_original_size = target_node.get_population_size()

        # Grabs 200 people from the target node - less than available
        grabbed_population = target_node.grab_population(200, pop_template)
        node_final_size = target_node.get_population_size()
        grabbed_population_size = blobs_total_size(grabbed_population)

        # assert validity and correct sizes
        self.assertTrue(verify_blobs_validity(grabbed_population),
        'Case 1: Grabbed population is not valid.')
        self.assertTrue(not verify_blobs_contained_in_node(grabbed_population, target_node),
        'Case 1: Grabbed population still in EnvNode.')
        self.assertEqual(node_original_size, node_final_size + grabbed_population_size,
        'Case 1: Total population size changed.')
        self.assertEqual(grabbed_population_size, 200,
        'Case 1: Grabbed population size is not equal to grabbed amount.')
        self.assertEqual(len(grabbed_population), 4,
        'Case 1: Grabbed Blob count different than expected.')
        self.assertEqual(len(target_node.contained_blobs), 4,
        'Case 1: Node Blob count different than expected.')
        self.assertTrue(verify_graph_validity_size(self.envB, 1200 - grabbed_population_size),
        'Case 1: EnvironmentGraph changed in size.')
        self.assertTrue(verify_node_validity(target_node),
        'Case 1: Grabbed pop still in node.')
                
        # Returns Blobs to target node for next Case
        target_node.add_blobs(grabbed_population)
        
        # Case 2:
        # Gets a target EnvNode with population 400
        target_node = self.envB.get_node_by_name("Partenon", "home")
        node_original_size = target_node.get_population_size()
        
        # Grabs 400 people from the target node - equal as available
        grabbed_population = target_node.grab_population(400, pop_template)
        node_final_size = target_node.get_population_size()
        grabbed_population_size = blobs_total_size(grabbed_population)

        # assert validity and correct sizes
        self.assertTrue(verify_blobs_validity(grabbed_population),
        'Case 2: Grabbed population is not valid.')
        self.assertTrue(not verify_blobs_contained_in_node(grabbed_population, target_node),
        'Case 2: Grabbed population still in EnvNode.')
        self.assertEqual(node_original_size, node_final_size + grabbed_population_size,
        'Case 2: Total population size changed.')
        self.assertEqual(grabbed_population_size, 400,
        'Case 2: Grabbed population size is not equal to grabbed amount.')
        self.assertEqual(len(grabbed_population), 4,
        'Case 1: Grabbed Blob count different than expected.')
        self.assertEqual(len(target_node.contained_blobs), 0,
        'Case 1: Node Blob count different than expected.')
        self.assertTrue(verify_graph_validity_size(self.envB, 1200 - grabbed_population_size),
        'Case 2: EnvironmentGraph changed in size.')
        self.assertTrue(verify_node_validity(target_node),
        'Case 2: Grabbed pop still in node.')
        
        # Returns Blobs to target node for next Case
        target_node.add_blobs(grabbed_population)
                
        # Case 3:
        # Gets a target EnvNode with population 400
        target_node = self.envB.get_node_by_name("Centro", "home")
        node_original_size = target_node.get_population_size()

        # Grabs 800 people from the target node - more than available
        grabbed_population = target_node.grab_population(800, pop_template)
        node_final_size = target_node.get_population_size()
        grabbed_population_size = blobs_total_size(grabbed_population)

        # assert validity and correct sizes
        self.assertTrue(verify_blobs_validity(grabbed_population),
        'Case 3: Grabbed population is not valid.')
        self.assertTrue(not verify_blobs_contained_in_node(grabbed_population, target_node),
        'Case 3: Grabbed population still in EnvNode.')
        self.assertEqual(node_original_size, node_final_size + grabbed_population_size,
        'Case 3: Total population size changed.')
        self.assertEqual(grabbed_population_size, 400,
        'Case 3: Grabbed population size is not equal to grabbed amount.')
        self.assertEqual(len(grabbed_population), 4,
        'Case 1: Grabbed Blob count different than expected.')
        self.assertEqual(len(target_node.contained_blobs), 0,
        'Case 1: Node Blob count different than expected.')
        self.assertTrue(verify_graph_validity_size(self.envB, 1200 - grabbed_population_size),
        'Case 3: EnvironmentGraph changed in size.')
        self.assertTrue(verify_node_validity(target_node),
        'Case 3: Grabbed pop still in node.')
        
    
    ## EnvNode.process_routine
    def test_node_process_routine(self):
        """Tests EnvNode.get_population_size

        Process routines for a EnvNode in the EnvironmentGraph.
        
        Case 1: 
            action: Get a list of TimeActions for each hour in the day.
            result: Routine Lengths are equal as expected.
                    EnvNodes are valid after processing the routine.
        
        Case : 
            action: Gets the available TimeActions for a set of EnvNodes
            result: Type and Values for a give TimeAction are equal as defined in the input file for the EnvironmentGraph
        """
        # Case 1:
        # Gets target EnvNodes with the EnrivonmentGraph
        target_node_A = self.envA.get_node_by_name("Petropolis", "home")
        target_node_B = self.envA.get_node_by_name("Petropolis", "school")
        target_node_C = self.envA.get_node_by_name("Petropolis", "work")
        
        # Gets a list of routines per hour
        hours = range(0, 24)
        routines_A = [target_node_A.process_routine(h) for h in hours]
        routines_B = [target_node_B.process_routine(h) for h in hours]
        routines_C = [target_node_C.process_routine(h) for h in hours]
        
        # Sets the expected count of routines per hour
        count_A, count_B, count_C = [0] * 24, [0] * 24, [0] * 24
        count_A[18] = 1
        count_B[7] = 2
        count_C[7] = 1
        
        # assert validity and correct sizes
        self.assertTrue(verify_node_validity(target_node_A),
        'Case 1: EnvNode is not valid.')
        self.assertTrue(verify_node_validity(target_node_B),
        'Case 1: EnvNode is not valid.')
        self.assertTrue(verify_node_validity(target_node_C),
        'Case 1: EnvNode is not valid.')
        self.assertEqual([len(routines_A[h]) for h in hours], count_A,
        'Case 1: Routine counts different than expected.')
        self.assertEqual([len(routines_B[h]) for h in hours], count_B,
        'Case 1: Routine counts different than expected.')
        self.assertEqual([len(routines_C[h]) for h in hours], count_C,
        'Case 1: Routine counts different than expected.')
        
        # Case 2:
        target_action_A = routines_A[18][0]
        target_action_B = routines_B[7][0]
        target_action_C = routines_B[7][1]
        target_action_D = routines_C[7][0]
        
        # assert correct values for TimeActions
        # TimeAction_A - "home" EnvNode
        self.assertTrue(target_action_A.type == "return_population_home",
        'Case 2: TimeAction type not as expected.')
        self.assertTrue(target_action_A.values['quantity'] == -1,
        'Case 2: TimeAction value not as expected.')
        self.assertTrue(target_action_A.values['region'] == "Petropolis",
        'Case 2: TimeAction value not as expected.')
        self.assertTrue(target_action_A.values['population_template'].is_empty(),
        'Case 2: TimeAction value not as expected.')
        # TimeAction_B and C - "school" EnvNode
        self.assertTrue(target_action_B.type == "gather_population",
        'Case 2: TimeAction type not as expected.')
        self.assertTrue(target_action_B.values['quantity'] == 5,
        'Case 2: TimeAction value not as expected.')
        self.assertTrue(target_action_B.values['node'] == "school",
        'Case 2: TimeAction value not as expected.')
        self.assertTrue(target_action_B.values['population_template'].pairs['age'] == 'young',
        'Case 2: TimeAction value not as expected.')
        self.assertTrue(target_action_B.values['population_template'].pairs['occupation'] == 'student',
        'Case 2: TimeAction value not as expected.')
        self.assertTrue(target_action_C.type == "gather_population",
        'Case 2: TimeAction type not as expected.')
        self.assertTrue(target_action_C.values['quantity'] == 5,
        'Case 2: TimeAction value not as expected.')
        self.assertTrue(target_action_C.values['node'] == "school",
        'Case 2: TimeAction value not as expected.')
        self.assertTrue(target_action_C.values['population_template'].pairs['age'] == 'children',
        'Case 2: TimeAction value not as expected.')
        self.assertTrue(target_action_C.values['population_template'].pairs['occupation'] == 'student',
        'Case 2: TimeAction value not as expected.')
        # TimeAction_D - "work" EnvNode
        self.assertTrue(target_action_D.type == "gather_population",
        'Case 2: TimeAction type not as expected.')
        self.assertTrue(target_action_D.values['quantity'] == 20,
        'Case 2: TimeAction value not as expected.')
        self.assertTrue(target_action_D.values['node'] == "work",
        'Case 2: TimeAction value not as expected.')
        self.assertTrue(target_action_D.values['population_template'].pairs['age'] == 'adults',
        'Case 2: TimeAction value not as expected.')
        self.assertTrue(target_action_D.values['population_template'].pairs['occupation'] == 'worker',
        'Case 2: TimeAction value not as expected.')
       
    
    #### EnvRegion Tests
    ## EnvRegion.get_population_size - one Blob in populated EnvNode
    def test_region_get_population_size_one_blob(self):
        """Tests EnvRegion.get_population_size

        Gets population sizes for a EnvRegion using multiple PopTemplates. 
        
        Target EnvRegion population description in the "home" EnvNode:
        "age": {"adults": 40, "elders": 20, "young": 15, "children": 25},
        "occupation": {"idle": 20, "student": 40, "worker": 40},
        "social_profile": {"low": 40, "mid": 35, "high": 25}
        
        Case 1: 
            action: Gets population sizes in multiple scenarios.
            result: Sizes are equal as pre-defined in the population description
        """
        # Case 1:
        region_sizes = []
        
        # Gets a target EnvNode with population 100
        target_region = self.envA.get_region_by_name("Petropolis")
        
        # Gets the population size for multiple PopTemplates
        ## ---------- Expected: 100
        pop_template = PopTemplate() 
        region_sizes.append(target_region.get_population_size())
        ## ---------- Expected: 40
        pop_template.set_sampled_property('age', 'adults')
        region_sizes.append(target_region.get_population_size(pop_template))
        ## ---------- Expected: 20
        pop_template.set_sampled_property('age', 'elders')
        region_sizes.append(target_region.get_population_size(pop_template))
        ## ---------- Expected: 60
        pop_template.set_sampled_property('age', ['adults', 'elders'])
        region_sizes.append(target_region.get_population_size(pop_template))
        ## ---------- Expected: 40
        pop_template.set_sampled_property('age', ['adults', 'elders'])
        pop_template.set_sampled_property('occupation', 'worker')
        region_sizes.append(target_region.get_population_size(pop_template))
        ## ---------- Expected: 60 
        pop_template.set_sampled_property('age', ['adults', 'elders'])
        pop_template.set_sampled_property('occupation', ['idle', 'worker'])
        region_sizes.append(target_region.get_population_size(pop_template))
        ## ---------- Expected: 100 
        pop_template.set_sampled_property('age', [])
        pop_template.set_sampled_property('occupation', [])
        region_sizes.append(target_region.get_population_size(pop_template))
        ## ---------- Expected: 60
        pop_template.set_sampled_property('age', ['adults', 'elders'])
        pop_template.set_sampled_property('occupation', [])
        region_sizes.append(target_region.get_population_size(pop_template))
        ## ---------- Expected: 35
        pop_template.set_sampled_property('age', ['adults', 'elders'])
        pop_template.set_sampled_property('occupation', [])
        pop_template.set_sampled_property('social_profile', 'mid')
        region_sizes.append(target_region.get_population_size(pop_template))
        ## ---------- Expected: 20
        pop_template.set_sampled_property('age', 'elders')
        pop_template.set_sampled_property('occupation', [])
        pop_template.set_sampled_property('social_profile', 'mid')
        region_sizes.append(target_region.get_population_size(pop_template))
        
        # assert validity and correct sizes
        self.assertTrue(verify_graph_validity(self.envA),
        'Case 1: EnvironmentGraph is not valid.')
        self.assertTrue(verify_graph_validity_size(self.envA, 300),
        'Case 1: EnvironmentGraph changed in size.')
        self.assertEqual(region_sizes, [100, 40, 20, 60, 40, 60, 100, 60, 35, 20],
        f'Case 1: Population sizes different than expected {region_sizes}.')
        
    ## EnvRegion.get_population_size - multiple Blobs in populated EnvNode
    def test_region_get_population_size_multiple_blobs(self):
        """Tests EnvRegion.get_population_size

        Gets population sizes for a EnvRegion using multiple PopTemplates. 
        
        Target EnvRegion contains four Blobs in the "home" EnvNode with population 100 and permutations of:
        "traceable_A": {"default", "other_value"},
        "traceable_B": {0, 1}
        
        Target EnvRegion population description for each Blob:
        "age": {"adults": 40, "elders": 20, "young": 15, "children": 25},
        "occupation": {"idle": 20, "student": 40, "worker": 40},
        "social_profile": {"low": 40, "mid": 35, "high": 25}
        
        Case 1: 
            action: Gets population sizes in multiple scenarios.
            result: Sizes are equal as pre-defined in the population description
        """
        # Case 1:
        regions_sizes = [] 
        
        # Gets a target EnvNode with population 100
        target_region = self.envB.get_region_by_name("Petropolis")
        # Gets the population size for multiple PopTemplates
        ## ---------- Expected: 400
        pop_template = PopTemplate()
        regions_sizes.append(target_region.get_population_size())
        ## ---------- Expected: 160
        pop_template.set_sampled_property('age', 'adults')
        regions_sizes.append(target_region.get_population_size(pop_template))
        ## ---------- Expected: 240
        pop_template.set_sampled_property('age', ['adults', 'elders'])
        pop_template.set_sampled_property('occupation', ['idle', 'worker'])
        regions_sizes.append(target_region.get_population_size(pop_template))
        ## ---------- Expected: 80
        pop_template.set_sampled_property('age', 'elders')
        pop_template.set_sampled_property('occupation', [])
        pop_template.set_sampled_property('social_profile', 'mid')
        regions_sizes.append(target_region.get_population_size(pop_template))
        ## ---------- Expected: 200
        pop_template = PopTemplate() 
        pop_template.set_traceable_property('traceable_A', 'default')
        regions_sizes.append(target_region.get_population_size(pop_template))
        ## ---------- Expected: 100
        pop_template.set_traceable_property('traceable_A', 'default')
        pop_template.set_traceable_property('traceable_B', 0)
        regions_sizes.append(target_region.get_population_size(pop_template))
        ## ---------- Expected: 400
        pop_template.set_traceable_property('traceable_A', ['default', 'other_value'])
        pop_template.set_traceable_property('traceable_B', [0, 1])
        regions_sizes.append(target_region.get_population_size(pop_template))
        ## ---------- Expected: 40      
        pop_template.set_traceable_property('traceable_A', 'default')
        pop_template.set_traceable_property('traceable_B', 0)
        pop_template.set_sampled_property('age', 'adults')
        regions_sizes.append(target_region.get_population_size(pop_template))
        ## ---------- Expected: 80
        pop_template.set_traceable_property('traceable_A', ['default', 'other_value'])
        pop_template.set_traceable_property('traceable_B', 0)
        pop_template.set_sampled_property('age', 'adults')
        regions_sizes.append(target_region.get_population_size(pop_template))
        ## ---------- Expected: 70
        pop_template.set_traceable_property('traceable_A', ['default', 'other_value'])
        pop_template.set_traceable_property('traceable_B', 0)
        pop_template.set_sampled_property('age', 'adults')
        pop_template.set_sampled_property('occupation', [])
        pop_template.set_sampled_property('social_profile', 'mid')
        regions_sizes.append(target_region.get_population_size(pop_template))
        
        # assert validity and correct sizes
        self.assertTrue(verify_graph_validity(self.envA),
        'Case 1: EnvironmentGraph is not valid.')
        self.assertTrue(verify_graph_validity_size(self.envA, 300),
        'Case 1: EnvironmentGraph changed in size.')
        self.assertEqual(regions_sizes, [400, 160, 240, 80, 200, 100, 400, 40, 80, 70],
        f'Case 1: Population sizes different than expected {regions_sizes}.')
    
    ## EnvRegion.generate_action_list
    def test_region_generate_action_list(self):
        """Tests EnvRegion.generate_action_list

        Process routines for a EnvNode in the EnvironmentGraph.
        
        Case 1: 
            action: Get a list of TimeActions for each hour in the day.
            result: Routine Lengths are equal as expected.
                    EnvironmentGraph is valid after processing the routine.
        
        Case : 
            action: Gets the available TimeActions for a set of EnvNodes
            result: Type and Values for a give TimeAction are equal as defined in the input file for the EnvironmentGraph
        """
        # Case 1:
        # Gets target EnvNodes with the EnrivonmentGraph
        target_region = self.envA.get_region_by_name("Petropolis")
        
        # Gets a list of routines per hour
        hours = range(0, 24)
        action_lists = [target_region.generate_action_list(h) for h in hours]
        
        # Sets the expected count of actions per hour
        expected_count = [0] * 24
        expected_count[7] = 3
        expected_count[18] = 1
        
        # assert validity and correct sizes
        self.assertTrue(verify_graph_validity(self.envA),
        'Case 1: EnvNode is not valid.')
        self.assertEqual([len(action_lists[h]) for h in hours], expected_count,
        'Case 1: Routine counts different than expected.')
        
        # Case 2:
        target_action_A = action_lists[18][0]
        target_action_B = action_lists[7][0]
        target_action_C = action_lists[7][1]
        target_action_D = action_lists[7][2]
        
        # assert correct values for TimeActions
        # TimeAction_A - "home" EnvNode
        self.assertTrue(target_action_A.type == "return_population_home",
        'Case 2: TimeAction type not as expected.')
        self.assertTrue(target_action_A.values['quantity'] == -1,
        'Case 2: TimeAction value not as expected.')
        self.assertTrue(target_action_A.values['region'] == "Petropolis",
        'Case 2: TimeAction value not as expected.')
        self.assertTrue(target_action_A.values['population_template'].is_empty(),
        'Case 2: TimeAction value not as expected.')
        # TimeAction_B and C - "school" EnvNode
        self.assertTrue(target_action_B.type == "gather_population",
        'Case 2: TimeAction type not as expected.')
        self.assertTrue(target_action_B.values['quantity'] == 5,
        'Case 2: TimeAction value not as expected.')
        self.assertTrue(target_action_B.values['node'] == "school",
        'Case 2: TimeAction value not as expected.')
        self.assertTrue(target_action_B.values['population_template'].pairs['age'] == 'young',
        'Case 2: TimeAction value not as expected.')
        self.assertTrue(target_action_B.values['population_template'].pairs['occupation'] == 'student',
        'Case 2: TimeAction value not as expected.')
        self.assertTrue(target_action_C.type == "gather_population",
        'Case 2: TimeAction type not as expected.')
        self.assertTrue(target_action_C.values['quantity'] == 5,
        'Case 2: TimeAction value not as expected.')
        self.assertTrue(target_action_C.values['node'] == "school",
        'Case 2: TimeAction value not as expected.')
        self.assertTrue(target_action_C.values['population_template'].pairs['age'] == 'children',
        'Case 2: TimeAction value not as expected.')
        self.assertTrue(target_action_C.values['population_template'].pairs['occupation'] == 'student',
        'Case 2: TimeAction value not as expected.')
        # TimeAction_D - "work" EnvNode
        self.assertTrue(target_action_D.type == "gather_population",
        'Case 2: TimeAction type not as expected.')
        self.assertTrue(target_action_D.values['quantity'] == 20,
        'Case 2: TimeAction value not as expected.')
        self.assertTrue(target_action_D.values['node'] == "work",
        'Case 2: TimeAction value not as expected.')
        self.assertTrue(target_action_D.values['population_template'].pairs['age'] == 'adults',
        'Case 2: TimeAction value not as expected.')
        self.assertTrue(target_action_D.values['population_template'].pairs['occupation'] == 'worker',
        'Case 2: TimeAction value not as expected.')
    
    
    #### EnvironmentGraph Tests
    ## EnvironmentGraph.process_routines
    def test_region_process_routines(self):
        """Tests EnvRegion.generate_action_list

        Process routines for a EnvNode in the EnvironmentGraph.
        
        Case 1: 
            action: Get a list of TimeActions for each hour in the day.
            result: Routine Lengths are equal as expected.
                    EnvironmentGraph is valid after processing the routine.
        
        Case : 
            action: Gets the available TimeActions for a set of EnvNodes
            result: Type and Values for a give TimeAction are equal as defined in the input file for the EnvironmentGraph
        """
        # Case 1:
        
        # Gets a list of routines per hour
        hours = range(0, 24)
        action_lists = [self.envA.process_routines(h) for h in hours]
        
        # Sets the expected count of actions per hour
        expected_count = [0] * 24
        expected_count[7] = 9
        expected_count[18] = 3
        
        # assert validity and correct sizes
        self.assertTrue(verify_graph_validity(self.envA),
        'Case 1: EnvNode is not valid.')
        self.assertEqual([len(action_lists[h]) for h in hours], expected_count,
        'Case 1: Routine counts different than expected.')
        
        # Case 2:
        target_action_A = action_lists[18][0]
        target_action_B = action_lists[7][0]
        target_action_C = action_lists[7][1]
        target_action_D = action_lists[7][2]
        
        # assert correct values for TimeActions
        # TimeAction_A - "home" EnvNode
        self.assertTrue(target_action_A.type == "return_population_home",
        'Case 2: TimeAction type not as expected.')
        self.assertTrue(target_action_A.values['quantity'] == -1,
        'Case 2: TimeAction value not as expected.')
        self.assertTrue(target_action_A.values['region'] == "Petropolis",
        'Case 2: TimeAction value not as expected.')
        self.assertTrue(target_action_A.values['population_template'].is_empty(),
        'Case 2: TimeAction value not as expected.')
        # TimeAction_B and C - "school" EnvNode
        self.assertTrue(target_action_B.type == "gather_population",
        'Case 2: TimeAction type not as expected.')
        self.assertTrue(target_action_B.values['quantity'] == 5,
        'Case 2: TimeAction value not as expected.')
        self.assertTrue(target_action_B.values['node'] == "school",
        'Case 2: TimeAction value not as expected.')
        self.assertTrue(target_action_B.values['population_template'].pairs['age'] == 'young',
        'Case 2: TimeAction value not as expected.')
        self.assertTrue(target_action_B.values['population_template'].pairs['occupation'] == 'student',
        'Case 2: TimeAction value not as expected.')
        self.assertTrue(target_action_C.type == "gather_population",
        'Case 2: TimeAction type not as expected.')
        self.assertTrue(target_action_C.values['quantity'] == 5,
        'Case 2: TimeAction value not as expected.')
        self.assertTrue(target_action_C.values['node'] == "school",
        'Case 2: TimeAction value not as expected.')
        self.assertTrue(target_action_C.values['population_template'].pairs['age'] == 'children',
        'Case 2: TimeAction value not as expected.')
        self.assertTrue(target_action_C.values['population_template'].pairs['occupation'] == 'student',
        'Case 2: TimeAction value not as expected.')
        # TimeAction_D - "work" EnvNode
        self.assertTrue(target_action_D.type == "gather_population",
        'Case 2: TimeAction type not as expected.')
        self.assertTrue(target_action_D.values['quantity'] == 20,
        'Case 2: TimeAction value not as expected.')
        self.assertTrue(target_action_D.values['node'] == "work",
        'Case 2: TimeAction value not as expected.')
        self.assertTrue(target_action_D.values['population_template'].pairs['age'] == 'adults',
        'Case 2: TimeAction value not as expected.')
        self.assertTrue(target_action_D.values['population_template'].pairs['occupation'] == 'worker',
        'Case 2: TimeAction value not as expected.')
    
    ## EnvironmentGraph.merge_node - Cloned Blobs
    def test_graph_merge_node(self):
        """Tests EnvironmentGraph.merge_node

        Case 1: 
            action: Merges blobs in graph.
            result: Graph contains only nodes containing unique mother_blob_id containiend_blob lists.
        """
        
        # Gets a target EnvNode with population 100
        target_node = self.envA.get_node_by_name("Petropolis", "home")
        node_blobs = target_node.contained_blobs
        
        # Gets the first Blob in target node
        source_blob = node_blobs[0]
        
        # Copy three extra Blobs with same profile - clone_blob_4 should ne None
        extra_blob_1 = source_blob.blob_factory.GenerateProfile(source_blob.mother_blob_id, 100, source_blob.profiles, source_blob.traceable_properties)
        extra_blob_2 = source_blob.blob_factory.Generate(source_blob.mother_blob_id, 190, source_blob.traceable_properties)
        extra_blob_3 = source_blob.blob_factory.Generate(source_blob.mother_blob_id, 10, source_blob.traceable_properties) 
                
        # Adds extra Blobs to target node
        target_node.add_blobs([extra_blob_1, extra_blob_2, extra_blob_3])
        
        # Gets sizes before merge
        node_original_size = target_node.get_population_size()
        graph_original_size = self.envA.get_population_size()
                
        # Merge Blobs in target node - no Blobs should change
        self.envA.merge_node(target_node)
        
        # Gets sizes and counts after merge
        node_final_size = target_node.get_population_size()
        graph_final_size = self.envA.get_population_size()
        target_node_blob_count = len(target_node.contained_blobs)
        blob_sizes = [b.get_population_size() for b in target_node.contained_blobs]
        
        # Gets a list of unique mother_blob_ids and checks for duplicates
        ids = set()
        result = True
        for blob in target_node.contained_blobs:
            if blob.mother_blob_id not in ids:
                ids.add(blob.mother_blob_id)
            else:
                result = False

        # assert validity and correct sizes
        self.assertTrue(verify_graph_validity(self.envA),
        'Case 1: Graph is not valid.')
        self.assertTrue(result,
        'Case 1: mother_blob_id repeated in node.contained_blobs.')
        self.assertEqual(graph_final_size, graph_original_size,
        'Case 1: Total population size changed.')
        self.assertEqual(node_final_size, node_original_size,
        'Case 1: Total population size in node changed.')
        self.assertEqual(blob_sizes, [400],
        'Case 1: Blob sizes are different than expected.')
        self.assertTrue(target_node_blob_count == 1,
        'Case 1: Node Blob count different than expected.')

    ## EnvironmentGraph.merge_node - Blobs with different traceable properties
    def test_graph_merge_node_with_traceable_properties(self):
        """Tests EnvironmentGraph.merge_node

        Merges Blobs with varying traceable properties in a EnvNode.

        Case 1: 
            action: Merges Blobs in a EnvNode.
            result: EnvNode contains the same Blobs as before the merge.
            
        Case 2: 
            action: Changes a traceable property for all Blobs. Then, merges Blobs in EnvNode.
            result: EnvNode now contains two merged Blobs (from four)
            
        Case 3: 
            action: Changes a traceable property for all Blobs. Then, merges Blobs in EnvNode.
            result: EnvNode now contains one merged Blob (from two)
        """
        
        # Case 1:
        # Gets a target EnvNode with population 400
        target_node = self.envB.get_node_by_name("Petropolis", "home")
        node_original_size = target_node.get_population_size()
        
        # Merge Blobs in target node - no Blobs should change
        self.envB.merge_node(target_node)
        
        # Gets sizes and counts after merge
        node_final_size = target_node.get_population_size()
        target_node_blob_count = len(target_node.contained_blobs)
        blob_sizes = [b.get_population_size() for b in target_node.contained_blobs]
        
        # assert validity and correct sizes
        self.assertTrue(verify_blobs_validity(target_node.contained_blobs),
        'Case 1: Grabbed population is not valid.')
        self.assertTrue(verify_blobs_contained_in_node(target_node.contained_blobs, target_node),
        'Case 1: Grabbed population still in EnvNode.')
        self.assertEqual(node_original_size, node_final_size,
        'Case 1: Total population size changed.')
        self.assertEqual(node_original_size, 400,
        'Case 1: Grabbed population size is not equal to grabbed amount.')
        self.assertEqual(blob_sizes, [100, 100, 100, 100],
        'Case 1: Blob sizes are different than expected.')
        self.assertTrue(verify_graph_validity_size(self.envB, 1200),
        'Case 1: EnvironmentGraph changed in size.')
        self.assertTrue(target_node_blob_count == 4,
        'Case 1: Node Blob count different than expected.')
        self.assertTrue(verify_node_validity(target_node),
        'Case 1: Grabbed pop still in node.')
        
        # Case 2:
        # Uses the same target node
        node_original_size = target_node.get_population_size()
        
        # Set a traceable property for all Blobs in node - two merges should occur
        for blob in target_node.contained_blobs:
            blob.traceable_properties['traceable_B'] = 0
        
        # Merge Blobs in target node - Blob0 should merge with Blob1, and Blob2 should merge with Blob3
        self.envB.merge_node(target_node)
        
        # Gets sizes and counts after merge
        node_final_size = target_node.get_population_size()
        target_node_blob_count = len(target_node.contained_blobs)
        blob_sizes = [b.get_population_size() for b in target_node.contained_blobs]
        
        # assert validity and correct sizes
        self.assertTrue(verify_blobs_validity(target_node.contained_blobs),
        'Case 2: Grabbed population is not valid.')
        self.assertTrue(verify_blobs_contained_in_node(target_node.contained_blobs, target_node),
        'Case 2: Grabbed population still in EnvNode.')
        self.assertEqual(node_original_size, node_final_size,
        'Case 2: Total population size changed.')
        self.assertEqual(node_original_size, 400,
        'Case 2: Grabbed population size is not equal to grabbed amount.')
        self.assertEqual(blob_sizes, [200, 200],
        'Case 2: Blob sizes are different than expected.')
        self.assertTrue(verify_graph_validity_size(self.envB, 1200),
        'Case 2: EnvironmentGraph changed in size.')
        self.assertTrue(target_node_blob_count == 2,
        'Case 2: Node Blob count different than expected.')
        self.assertTrue(verify_node_validity(target_node),
        'Case 2: Grabbed pop still in node.')
        
        # Case 3:
        # Uses the same target node
        node_original_size = target_node.get_population_size()
        
        # Set a traceable property for all Blobs in node - one merge should occur
        for blob in target_node.contained_blobs:
            blob.traceable_properties['traceable_A'] = 'default'
        
        # Merge Blobs in target node - Blob0 should merge with Blob1
        self.envB.merge_node(target_node)
        
        # Gets sizes and counts after merge
        node_final_size = target_node.get_population_size()
        target_node_blob_count = len(target_node.contained_blobs)
        blob_sizes = [b.get_population_size() for b in target_node.contained_blobs]
        
        # assert validity and correct sizes
        self.assertTrue(verify_blobs_validity(target_node.contained_blobs),
        'Case 3: Grabbed population is not valid.')
        self.assertTrue(verify_blobs_contained_in_node(target_node.contained_blobs, target_node),
        'Case 3: Grabbed population still in EnvNode.')
        self.assertEqual(node_original_size, node_final_size,
        'Case 3: Total population size changed.')
        self.assertEqual(node_original_size, 400,
        'Case 3: Grabbed population size is not equal to grabbed amount.')
        self.assertEqual(blob_sizes, [400],
        'Case 3: Blob sizes are different than expected.')
        self.assertTrue(verify_graph_validity_size(self.envB, 1200),
        'Case 3: EnvironmentGraph changed in size.')
        self.assertTrue(target_node_blob_count == 1,
        'Case 3: Node Blob count different than expected.')
        self.assertTrue(verify_node_validity(target_node),
        'Case 3: Grabbed pop still in node.')

    ## EnvironmentGraph.consume_time_action - move_population
    def test_graph_consume_time_action_move_population(self):
        """Tests EnvironmentGraph.move_population

        Assumes the move_population action is valid (the necessary population will be available).
        
        Case 1: 
            action: Operates one move_population action. Less population than available.
            result: Graph is valid.
                    Origin node contains quantity less population.
                    Target node has population increased by quantity.
    
        Case 2: 
            action: Operates one move_population action. Equal population as available.
            result: Graph is valid.
                    Origin node contains quantity less population.
                    Target node has population increased by quantity.
                    
        Case 3: 
            action: Operates one move_population action. More than available population.
            result: Graph is valid.
                    Origin node contains 0 population.
                    Target node has sum of populations.
                    
        Case 4: 
            action: Operates one move_population action. Quantity = -1. Represents move all population.
            result: Graph is valid.
                    Origin node contains 0 population.
                    Target node has sum of populations. 
                    
        Case 5: 
            action: Operates one move_population action. Quantity = 0. Operation should not occur.
            result: Graph is valid.
                    Populations remain the same.
        """
        # Gets a deepcopy of EnvironmentGraph_A do test multiple cases
        _envs = [copy.deepcopy(self.envA) for x in range(0,5)]
        
        # Sets a PopTemplate
        pop_template  = PopTemplate()
        
        # Case 1:
        # Gets the EnvNodes used in the operation
        node_origin = _envs[0].get_node_by_name('Petropolis', 'home')
        node_destination = _envs[0].get_node_by_name('Centro', 'work')
        
        # Gets sizes before operation
        graph_original_size = _envs[0].get_population_size()
        origin_node_original_size = node_origin.get_population_size()
        destination_node_original_size = node_destination.get_population_size()
        
        # Setup of move_population TimeAction - Requests half of original population
        values = {  'origin_region': node_origin.containing_region_name,
                    'origin_node': node_origin.name,
                    'destination_region': node_destination.containing_region_name,
                    'destination_node': node_destination.name,
                    'quantity': origin_node_original_size//2,
                    'population_template':pop_template}
        action = TimeAction('move_population', values)
        
        # Consumes the TimeAction
        _envs[0].consume_time_action(action, 0, 0)

        # Gets sizes after operation
        graph_final_size  = _envs[0].get_population_size()
        origin_node_final_size = node_origin.get_population_size()
        destination_node_final_size = node_destination.get_population_size()
        
        # assert validity and correct sizes
        self.assertTrue(verify_graph_validity(_envs[0]),
        'Case 1: Graph is not valid.')
        self.assertEqual(origin_node_final_size, origin_node_original_size - origin_node_original_size//2,
        'Case 1: Origin population did not decrease correctly.')
        self.assertEqual(origin_node_final_size, 50,
        'Case 1: Origin population did not decrease correctly.')
        self.assertEqual(destination_node_final_size, 50,
        'Case 1: Destination population did not increase correctly.')
        self.assertEqual(destination_node_original_size  + origin_node_original_size//2, destination_node_final_size,
        'Case 1: Destination population did not increase correctly.')
        self.assertEqual(len(node_origin.contained_blobs), 1,
        'Case 1: Origin EnvNode Blob count different than expected.')
        self.assertEqual(len(node_destination.contained_blobs), 1,
        'Case 1: Destination EnvNode Blob count different than expected.')
        self.assertEqual(graph_original_size, graph_final_size,
        'Case 1: Population size changed.')
        
        # Case 2:
        # Gets the EnvNodes used in the operation
        node_origin = _envs[1].get_node_by_name('Petropolis', 'home')
        node_destination = _envs[1].get_node_by_name('Centro', 'work')
        
        # Gets sizes before operation
        graph_original_size = _envs[1].get_population_size()
        origin_node_original_size = node_origin.get_population_size()
        destination_node_original_size = node_destination.get_population_size()
        
        # Setup of move_population TimeAction - Requests a amount equal as the original population
        values = {  'origin_region': node_origin.containing_region_name,
                    'origin_node': node_origin.name,
                    'destination_region': node_destination.containing_region_name,
                    'destination_node': node_destination.name,
                    'quantity': origin_node_original_size,
                    'population_template':pop_template}
        action = TimeAction('move_population', values)
        
        # Consumes the TimeAction
        _envs[1].consume_time_action(action, 0, 0)

        # Gets sizes after operation
        graph_final_size  = _envs[1].get_population_size()
        origin_node_final_size = node_origin.get_population_size()
        destination_node_final_size = node_destination.get_population_size()

        # assert validity and correct sizes
        self.assertTrue(verify_graph_validity(_envs[1]),
        'Case 2: Graph is not valid.')
        self.assertEqual(origin_node_final_size, origin_node_original_size - origin_node_original_size,
        'Case 2: Origin population did not decrease correctly.')
        self.assertEqual(origin_node_final_size, 0,
        'Case 2: Origin population did not decrease correctly.')
        self.assertEqual(destination_node_final_size, 100,
        'Case 2: Destination population did not increase correctly.')
        self.assertEqual(destination_node_original_size  + origin_node_original_size, destination_node_final_size,
        'Case 2: Destination population did not increase correctly.')
        self.assertEqual(len(node_origin.contained_blobs), 0,
        'Case 2: Origin EnvNode Blob count different than expected.')
        self.assertEqual(len(node_destination.contained_blobs), 1,
        'Case 2: Destination EnvNode Blob count different than expected.')
        self.assertEqual(graph_original_size, graph_final_size,
        'Case 2: Population size changed.')
        
        # Case 3:
        # Gets the EnvNodes used in the operation
        node_origin = _envs[2].get_node_by_name('Petropolis', 'home')
        node_destination = _envs[2].get_node_by_name('Centro', 'work')
        
        # Gets sizes before operation
        graph_original_size = _envs[2].get_population_size()
        origin_node_original_size = node_origin.get_population_size()
        destination_node_original_size = node_destination.get_population_size()
        
        # Setup of move_population TimeAction - Requests double the original population
        values = {  'origin_region': node_origin.containing_region_name,
                    'origin_node': node_origin.name,
                    'destination_region': node_destination.containing_region_name,
                    'destination_node': node_destination.name,
                    'quantity': origin_node_original_size * 2,
                    'population_template':pop_template}
        action = TimeAction('move_population', values)
        
        # Consumes the TimeAction
        _envs[2].consume_time_action(action, 0, 0)

        # Gets sizes after operation
        graph_final_size  = _envs[2].get_population_size()
        origin_node_final_size = node_origin.get_population_size()
        destination_node_final_size = node_destination.get_population_size()

        # assert validity and correct sizes
        self.assertTrue(verify_graph_validity(_envs[2]),
        'Case 3: Graph is not valid.')
        self.assertEqual(origin_node_final_size, origin_node_original_size - destination_node_final_size,
        'Case 3: Origin population did not decrease correctly.')
        self.assertEqual(origin_node_final_size, 0,
        'Case 3: Origin population did not decrease correctly.')
        self.assertEqual(destination_node_final_size, 100,
        'Case 3: Destination population did not increase correctly.')
        self.assertEqual(destination_node_original_size  + origin_node_original_size, destination_node_final_size,
        'Case 3: Destination population did not increase correctly.')
        self.assertEqual(len(node_origin.contained_blobs), 0,
        'Case 3: Origin EnvNode Blob count different than expected.')
        self.assertEqual(len(node_destination.contained_blobs), 1,
        'Case 3: Destination EnvNode Blob count different than expected.')
        self.assertEqual(graph_original_size, graph_final_size,
        'Case 3: Population size changed.')
                
        # Case 4:
        # Gets the EnvNodes used in the operation
        node_origin = _envs[3].get_node_by_name('Petropolis', 'home')
        node_destination = _envs[3].get_node_by_name('Centro', 'work')
        
        # Gets sizes before operation
        graph_original_size = _envs[3].get_population_size()
        origin_node_original_size = node_origin.get_population_size()
        destination_node_original_size = node_destination.get_population_size()
        
        # Setup of move_population TimeAction - Requests double the original population
        values = {  'origin_region': node_origin.containing_region_name,
                    'origin_node': node_origin.name,
                    'destination_region': node_destination.containing_region_name,
                    'destination_node': node_destination.name,
                    'quantity': -1,
                    'population_template':pop_template}
        action = TimeAction('move_population', values)
        
        # Consumes the TimeAction
        _envs[3].consume_time_action(action, 0, 0)

        # Gets sizes after operation
        graph_final_size  = _envs[3].get_population_size()
        origin_node_final_size = node_origin.get_population_size()
        destination_node_final_size = node_destination.get_population_size()
        
        # assert validity and correct sizes
        self.assertTrue(verify_graph_validity(_envs[3]),
        'Case 4: Graph is not valid.')
        self.assertEqual(origin_node_final_size, origin_node_original_size - destination_node_final_size,
        'Case 4: Origin population did not decrease correctly.')
        self.assertEqual(origin_node_final_size, 0,
        'Case 4: Origin population did not decrease correctly.')
        self.assertEqual(destination_node_final_size, 100,
        'Case 4: Destination population did not increase correctly.')
        self.assertEqual(destination_node_original_size  + origin_node_original_size, destination_node_final_size,
        'Case 4: Destination population did not increase correctly.')
        self.assertEqual(len(node_origin.contained_blobs), 0,
        'Case 4: Origin EnvNode Blob count different than expected.')
        self.assertEqual(len(node_destination.contained_blobs), 1,
        'Case 4: Destination EnvNode Blob count different than expected.')
        self.assertEqual(graph_original_size, graph_final_size,
        'Case 4: Population size changed.')
        
        # Case 5:
        # Gets the EnvNodes used in the operation
        node_origin = _envs[4].get_node_by_name('Petropolis', 'home')
        node_destination = _envs[4].get_node_by_name('Centro', 'work')
        
        # Gets sizes before operation
        graph_original_size = _envs[4].get_population_size()
        origin_node_original_size = node_origin.get_population_size()
        destination_node_original_size = node_destination.get_population_size()
        
        # Setup of move_population TimeAction - Requests double the original population
        values = {  'origin_region': node_origin.containing_region_name,
                    'origin_node': node_origin.name,
                    'destination_region': node_destination.containing_region_name,
                    'destination_node': node_destination.name,
                    'quantity': 0,
                    'population_template':pop_template}
        action = TimeAction('move_population', values)
        
        # Consumes the TimeAction
        _envs[4].consume_time_action(action, 0, 0)

        # Gets sizes after operation
        graph_final_size  = _envs[3].get_population_size()
        origin_node_final_size = node_origin.get_population_size()
        destination_node_final_size = node_destination.get_population_size()
        
        # assert validity and correct sizes
        self.assertTrue(verify_graph_validity(_envs[4]),
        'Case 5: Graph is not valid.')
        self.assertEqual(origin_node_final_size, origin_node_original_size,
        'Case 5: Origin population changed.')
        self.assertEqual(origin_node_final_size, 100,
        'Case 5: Origin population changed.')
        self.assertEqual(destination_node_final_size, 0,
        'Case 5: Destination population changed.')
        self.assertEqual(destination_node_final_size, destination_node_original_size ,
        'Case 5: Destination population changed.')
        self.assertEqual(len(node_origin.contained_blobs), 1,
        'Case 5: Origin EnvNode Blob count different than expected.')
        self.assertEqual(len(node_destination.contained_blobs), 0,
        'Case 5: Destination EnvNode Blob count different than expected.')
        self.assertEqual(graph_original_size, graph_final_size,
        'Case 5: Population size changed.')
        
    ## EnvironmentGraph.consume_time_action - move_population - with template
    def test_graph_consume_time_action_move_population_with_template(self):
        """Tests EnvironmentGraph.move_population

        Assumes the move_population action is valid (the necessary population will be available).
        Uses a PopTemplate in all actions.
        
        Case 1: 
            action: Operates one move_population action. Less population than available.
            result: Graph is valid.
                    Origin node contains less population.
                    Origin node contains available population of the requested PopTemplate.
                    Target node has population increased by quantity.
    
        Case 2: 
            action: Operates one move_population action. Equal population as available.
            result: Graph is valid.
                    Origin node contains less population.
                    Origin node doesn't contains available population of the requested PopTemplate.
                    Target node has population increased by quantity.
                    
        Case 3: 
            action: Operates one move_population action. More than available population.
            result: Graph is valid.
                    Origin node contains less population.
                    Origin node doesn't contains available population of the requested PopTemplate.
                    Target node has population increased by quantity.
                    
        Case 4: 
            action: Operates one move_population action. Quantity = -1. Represents move all population.
            result: Graph is valid.
                    Origin node contains less population.
                    Origin node doesn't contains available population of the requested PopTemplate.
                    Target node has population increased by quantity.
                    
        Case 5: 
            action: Operates one move_population action. Quantity = 0. Operation should not occur.
            result: Graph is valid.
                    Populations remain the same.
        """
        # Gets a deepcopy of EnvironmentGraph_A do test multiple cases
        _envs = [copy.deepcopy(self.envA) for x in range(0,5)]
        
        # Sets a PopTemplate
        pop_template  = PopTemplate()
        pop_template.set_sampled_property('age', ['adults', 'elders'])
        pop_template.set_sampled_property('occupation', ['idle', 'worker'])
        
        # Case 1:
        # Gets the EnvNodes used in the operation
        node_origin = _envs[0].get_node_by_name('Petropolis', 'home')
        node_destination = _envs[0].get_node_by_name('Centro', 'work')
        
        # Gets sizes before operation
        graph_original_size = _envs[0].get_population_size()
        origin_node_original_size = node_origin.get_population_size()
        original_available_population = node_origin.get_population_size(pop_template)
        destination_node_original_size = node_destination.get_population_size()
        
        # Setup of move_population TimeAction - Requests half of original population
        values = {  'origin_region': node_origin.containing_region_name,
                    'origin_node': node_origin.name,
                    'destination_region': node_destination.containing_region_name,
                    'destination_node': node_destination.name,
                    'quantity': original_available_population//2,
                    'population_template':pop_template}
        action = TimeAction('move_population', values)
        
        # Consumes the TimeAction
        _envs[0].consume_time_action(action, 0, 0)

        # Gets sizes after operation
        graph_final_size  = _envs[0].get_population_size()
        origin_node_final_size = node_origin.get_population_size()
        final_available_population = node_origin.get_population_size(pop_template)
        destination_node_final_size = node_destination.get_population_size()
        
        # assert validity and correct sizes
        self.assertTrue(verify_graph_validity(_envs[0]),
        'Case 1: Graph is not valid.')
        self.assertEqual(original_available_population, 60,
        'Case 1: Original available population different than expected.')
        self.assertEqual(final_available_population, 30,
        'Case 1: Final available population different than expected.')
        self.assertEqual(origin_node_final_size + original_available_population//2, origin_node_original_size,
        'Case 1: Origin population did not decrease correctly.')
        self.assertEqual(origin_node_final_size, 70,
        'Case 1: Origin population did not decrease correctly.')
        self.assertEqual(destination_node_final_size, 30,
        'Case 1: Destination population did not increase correctly.')
        self.assertEqual(destination_node_original_size  + original_available_population//2, destination_node_final_size,
        'Case 1: Destination population did not increase correctly.')
        self.assertEqual(len(node_origin.contained_blobs), 1,
        'Case 1: Origin EnvNode Blob count different than expected.')
        self.assertEqual(len(node_destination.contained_blobs), 1,
        'Case 1: Destination EnvNode Blob count different than expected.')
        self.assertEqual(graph_original_size, graph_final_size,
        'Case 1: Population size changed.')
        
        # Case 2:
        # Gets the EnvNodes used in the operation
        node_origin = _envs[1].get_node_by_name('Petropolis', 'home')
        node_destination = _envs[1].get_node_by_name('Centro', 'work')
        
        # Gets sizes before operation
        graph_original_size = _envs[1].get_population_size()
        origin_node_original_size = node_origin.get_population_size()
        original_available_population = node_origin.get_population_size(pop_template)
        destination_node_original_size = node_destination.get_population_size()
        
        # Setup of move_population TimeAction - Requests a amount equal as the original population
        values = {  'origin_region': node_origin.containing_region_name,
                    'origin_node': node_origin.name,
                    'destination_region': node_destination.containing_region_name,
                    'destination_node': node_destination.name,
                    'quantity': original_available_population,
                    'population_template':pop_template}
        action = TimeAction('move_population', values)
        
        # Consumes the TimeAction
        _envs[1].consume_time_action(action, 0, 0)

        # Gets sizes before operation
        graph_final_size  = _envs[1].get_population_size()
        origin_node_final_size = node_origin.get_population_size()
        final_available_population = node_origin.get_population_size(pop_template)
        destination_node_final_size = node_destination.get_population_size()

        # assert validity and correct sizes
        self.assertTrue(verify_graph_validity(_envs[1]),
        'Case 2: Graph is not valid.')
        self.assertEqual(original_available_population, 60,
        'Case 2: Original available population different than expected.')
        self.assertEqual(final_available_population, 0,
        'Case 2: Final available population different than expected.')
        self.assertEqual(origin_node_final_size, origin_node_original_size - original_available_population,
        'Case 2: Origin population did not decrease correctly.')
        self.assertEqual(origin_node_final_size, 40,
        'Case 2: Origin population did not decrease correctly.')
        self.assertEqual(destination_node_final_size, 60,
        'Case 2: Destination population did not increase correctly.')
        self.assertEqual(destination_node_final_size, original_available_population,
        'Case 2: Destination population did not increase correctly.')
        self.assertEqual(destination_node_original_size + original_available_population, destination_node_final_size,
        'Case 2: Destination population did not increase correctly.')
        self.assertEqual(len(node_origin.contained_blobs), 1,
        'Case 2: Origin EnvNode Blob count different than expected.')
        self.assertEqual(len(node_destination.contained_blobs), 1,
        'Case 2: Destination EnvNode Blob count different than expected.')
        self.assertEqual(graph_original_size, graph_final_size,
        'Case 2: Population size changed.')
        
        # Case 3:
        # Gets the EnvNodes used in the operation
        node_origin = _envs[2].get_node_by_name('Petropolis', 'home')
        node_destination = _envs[2].get_node_by_name('Centro', 'work')
        
        # Gets sizes before operation
        graph_original_size = _envs[2].get_population_size()
        origin_node_original_size = node_origin.get_population_size()
        original_available_population = node_origin.get_population_size(pop_template)
        destination_node_original_size = node_destination.get_population_size()
        
        # Setup of move_population TimeAction - Requests double the original population
        values = {  'origin_region': node_origin.containing_region_name,
                    'origin_node': node_origin.name,
                    'destination_region': node_destination.containing_region_name,
                    'destination_node': node_destination.name,
                    'quantity': original_available_population * 2,
                    'population_template':pop_template}
        action = TimeAction('move_population', values)
        
        # Consumes the TimeAction
        _envs[2].consume_time_action(action, 0, 0)

        # Gets sizes before operation
        graph_final_size  = _envs[2].get_population_size()
        origin_node_final_size = node_origin.get_population_size()
        final_available_population = node_origin.get_population_size(pop_template)
        destination_node_final_size = node_destination.get_population_size()

        # assert validity and correct sizes
        self.assertTrue(verify_graph_validity(_envs[2]),
        'Case 3: Graph is not valid.')
        self.assertEqual(original_available_population, 60,
        'Case 3: Original available population different than expected.')
        self.assertEqual(final_available_population, 0,
        'Case 3: Final available population different than expected.')
        self.assertEqual(origin_node_final_size, origin_node_original_size - original_available_population,
        'Case 3: Origin population did not decrease correctly.')
        self.assertEqual(origin_node_final_size, 40,
        'Case 3: Origin population did not decrease correctly.')
        self.assertEqual(destination_node_final_size, 60,
        'Case 3: Destination population did not increase correctly.')
        self.assertEqual(destination_node_final_size, original_available_population,
        'Case 3: Destination population did not increase correctly.')
        self.assertEqual(destination_node_original_size + original_available_population, destination_node_final_size,
        'Case 3: Destination population did not increase correctly.')
        self.assertEqual(len(node_origin.contained_blobs), 1,
        'Case 3: Origin EnvNode Blob count different than expected.')
        self.assertEqual(len(node_destination.contained_blobs), 1,
        'Case 3: Destination EnvNode Blob count different than expected.')
        self.assertEqual(graph_original_size, graph_final_size,
        'Case 3: Population size changed.')
                
        # Case 4:
        # Gets the EnvNodes used in the operation
        node_origin = _envs[3].get_node_by_name('Petropolis', 'home')
        node_destination = _envs[3].get_node_by_name('Centro', 'work')
        
        # Gets sizes before operation
        graph_original_size = _envs[3].get_population_size()
        origin_node_original_size = node_origin.get_population_size()
        original_available_population = node_origin.get_population_size(pop_template)
        destination_node_original_size = node_destination.get_population_size()
        
        # Setup of move_population TimeAction - Requests double the original population
        values = {  'origin_region': node_origin.containing_region_name,
                    'origin_node': node_origin.name,
                    'destination_region': node_destination.containing_region_name,
                    'destination_node': node_destination.name,
                    'quantity': -1,
                    'population_template':pop_template}
        action = TimeAction('move_population', values)
        
        # Consumes the TimeAction
        _envs[3].consume_time_action(action, 0, 0)

        # Gets sizes before operation
        graph_final_size  = _envs[3].get_population_size()
        origin_node_final_size = node_origin.get_population_size()
        final_available_population = node_origin.get_population_size(pop_template)
        destination_node_final_size = node_destination.get_population_size()
        
        # assert validity and correct sizes
        self.assertTrue(verify_graph_validity(_envs[3]),
        'Case 4: Graph is not valid.')
        self.assertEqual(original_available_population, 60,
        'Case 4: Original available population different than expected.')
        self.assertEqual(final_available_population, 0,
        'Case 4: Final available population different than expected.')
        self.assertEqual(origin_node_final_size, origin_node_original_size - original_available_population,
        'Case 4: Origin population did not decrease correctly.')
        self.assertEqual(origin_node_final_size, 40,
        'Case 4: Origin population did not decrease correctly.')
        self.assertEqual(destination_node_final_size, 60,
        'Case 4: Destination population did not increase correctly.')
        self.assertEqual(destination_node_final_size, original_available_population,
        'Case 4: Destination population did not increase correctly.')
        self.assertEqual(destination_node_original_size + original_available_population, destination_node_final_size,
        'Case 4: Destination population did not increase correctly.')
        self.assertEqual(len(node_origin.contained_blobs), 1,
        'Case 4: Origin EnvNode Blob count different than expected.')
        self.assertEqual(len(node_destination.contained_blobs), 1,
        'Case 4: Destination EnvNode Blob count different than expected.')
        self.assertEqual(graph_original_size, graph_final_size,
        'Case 4: Population size changed.')
        
        # Case 5:
        # Gets the EnvNodes used in the operation
        node_origin = _envs[4].get_node_by_name('Petropolis', 'home')
        node_destination = _envs[4].get_node_by_name('Centro', 'work')
        
        # Gets sizes before operation
        graph_original_size = _envs[4].get_population_size()
        origin_node_original_size = node_origin.get_population_size()
        original_available_population = node_origin.get_population_size(pop_template)
        destination_node_original_size = node_destination.get_population_size()
        
        # Setup of move_population TimeAction - Requests double the original population
        values = {  'origin_region': node_origin.containing_region_name,
                    'origin_node': node_origin.name,
                    'destination_region': node_destination.containing_region_name,
                    'destination_node': node_destination.name,
                    'quantity': 0,
                    'population_template':pop_template}
        action = TimeAction('move_population', values)
        
        # Consumes the TimeAction
        _envs[4].consume_time_action(action, 0, 0)

        # Gets sizes before operation
        graph_final_size  = _envs[3].get_population_size()
        origin_node_final_size = node_origin.get_population_size()
        final_available_population = node_origin.get_population_size(pop_template)
        destination_node_final_size = node_destination.get_population_size()
        
        # assert validity and correct sizes
        self.assertTrue(verify_graph_validity(_envs[4]),
        'Case 5: Graph is not valid.')
        self.assertEqual(origin_node_final_size, origin_node_original_size,
        'Case 5: Origin population changed.')
        self.assertEqual(origin_node_final_size, 100,
        'Case 5: Origin population changed.')
        self.assertEqual(destination_node_final_size, 0,
        'Case 5: Destination population changed.')
        self.assertEqual(destination_node_final_size, destination_node_original_size ,
        'Case 5: Destination population changed.')
        self.assertEqual(len(node_origin.contained_blobs), 1,
        'Case 5: Origin EnvNode Blob count different than expected.')
        self.assertEqual(len(node_destination.contained_blobs), 0,
        'Case 5: Destination EnvNode Blob count different than expected.')
        self.assertEqual(graph_original_size, graph_final_size,
        'Case 5: Population size changed.')
     
    ## EnvironmentGraph.consume_time_action - two move_population operations with complementing templates
    def test_graph_consume_time_action_move_population_with_complementing_templates(self):
        """Tests EnvironmentGraph.move_population

        Assumes the move_population action is valid (the necessary population will be available).
        Consumes a move_population TimeAction with a PopTemplate. Then, sets the template to request other property values and consumes a move_population population again. 
        
        Case 1: 
            action: Requests population equal as available using a template.
            result: Graph is valid.
                    Origin Node is not empty.
                    Total population size unchanged.    
                    Origin node contains less population.Origin node doesn't contains available population of the requested PopTemplate.
                    Target node has population increased by requested quantity.
                    
        Case 2: 
            action: Moves population equal as available (complementing template).
            result: Graph is valid.
                    Origin Node is empty.
                    Total population size unchanged.
                    Blob size equals extracted quantity.
                    Target node has population increased by requested quantity.
                    
        Case 3: 
            action: Merges the Destination Node after the two move_population operations
            result: Graph is valid.
                    Origin Node is empty
                    Destination Node contains 1 Blob
                    Destination Node contains the original population
        """
        # Sets two complementing PopTemplates
        pop_template_A = PopTemplate() 
        pop_template_A.set_sampled_property('age', ['adults', 'elders'])
        pop_template_A.set_sampled_property('occupation', ['idle', 'worker'])
        pop_template_A.set_sampled_property('social_profile', ['mid', 'high'])
        
        pop_template_B = PopTemplate() 
        pop_template_B.set_sampled_property('age', ['young', 'children'])
        pop_template_B.set_sampled_property('occupation', 'student')
        pop_template_B.set_sampled_property('social_profile', 'low')
        
        # Case 1:
        # Gets the EnvNodes used in the operation
        node_origin = self.envA.get_node_by_name('Petropolis', 'home')
        node_destination = self.envA.get_node_by_name('Centro', 'work')
        source_blob = node_origin.contained_blobs[0]
        
        # Gets sizes before operation
        graph_original_size = self.envA.get_population_size()
        origin_node_original_size = node_origin.get_population_size()
        original_available_population = node_origin.get_population_size(pop_template_A)
        destination_node_original_size = node_destination.get_population_size()
        
        # Setup of move_population TimeAction - Requests half of original population
        values = {  'origin_region': node_origin.containing_region_name,
                    'origin_node': node_origin.name,
                    'destination_region': node_destination.containing_region_name,
                    'destination_node': node_destination.name,
                    'quantity': original_available_population,
                    'population_template':pop_template_A}
        action = TimeAction('move_population', values)
        
        # Consumes the TimeAction
        self.envA.consume_time_action(action, 0, 0)

        # Gets sizes after operation
        graph_final_size  = self.envA.get_population_size()
        origin_node_final_size = node_origin.get_population_size()
        final_available_population = node_origin.get_population_size(pop_template_A)
        destination_node_final_size = node_destination.get_population_size()
        
        # assert validity and correct sizes
        self.assertTrue(verify_graph_validity(self.envA),
        'Case 1: Graph is not valid.')
        self.assertTrue(verify_blob_contained_in_node(source_blob, node_origin),
        'Case 1: Source Blob is not in EnvNode.')
        self.assertEqual(original_available_population, 60,
        'Case 1: Original available population different than expected.')
        self.assertEqual(final_available_population, 0,
        'Case 1: Final available population different than expected.')
        self.assertEqual(origin_node_final_size + original_available_population, origin_node_original_size,
        'Case 1: Origin population did not decrease correctly.')
        self.assertEqual(origin_node_final_size, 40,
        'Case 1: Origin population did not decrease correctly.')
        self.assertEqual(destination_node_final_size, 60,
        'Case 1: Destination population did not increase correctly.')
        self.assertEqual(destination_node_original_size  + original_available_population, destination_node_final_size,
        'Case 1: Destination population did not increase correctly.')
        self.assertEqual(len(node_origin.contained_blobs), 1,
        'Case 1: Origin EnvNode Blob count different than expected.')
        self.assertEqual(len(node_destination.contained_blobs), 1,
        'Case 1: Destination EnvNode Blob count different than expected.')
        self.assertEqual(graph_original_size, graph_final_size,
        'Case 1: Population size changed.')
        
        # Case 2:
        # Gets the EnvNodes used in the operation
        node_origin = self.envA.get_node_by_name('Petropolis', 'home')
        node_destination = self.envA.get_node_by_name('Centro', 'work')
        source_blob = node_origin.contained_blobs[0]
        
        # Gets sizes before operation
        graph_original_size = self.envA.get_population_size()
        origin_node_original_size = node_origin.get_population_size()
        original_available_population = node_origin.get_population_size(pop_template_B)
        destination_node_original_size = node_destination.get_population_size()
        
        # Setup of move_population TimeAction - Requests a amount equal as the original population
        values = {  'origin_region': node_origin.containing_region_name,
                    'origin_node': node_origin.name,
                    'destination_region': node_destination.containing_region_name,
                    'destination_node': node_destination.name,
                    'quantity': original_available_population,
                    'population_template':pop_template_B}
        action = TimeAction('move_population', values)
        
        # Consumes the TimeAction
        self.envA.consume_time_action(action, 0, 0)

        # Gets sizes before operation
        graph_final_size  = self.envA.get_population_size()
        origin_node_final_size = node_origin.get_population_size()
        final_available_population = node_origin.get_population_size(pop_template_B)
        destination_node_final_size = node_destination.get_population_size()

        # assert validity and correct sizes
        self.assertTrue(verify_graph_validity(self.envA),
        'Case 2: Graph is not valid.')
        self.assertTrue(not verify_blob_contained_in_node(source_blob, node_origin),
        'Case 2: Source Blob is in EnvNode.')
        self.assertEqual(original_available_population, 40,
        'Case 2: Original available population different than expected.')
        self.assertEqual(final_available_population, 0,
        'Case 2: Final available population different than expected.')
        self.assertEqual(origin_node_final_size, origin_node_original_size - original_available_population,
        'Case 2: Origin population did not decrease correctly.')
        self.assertEqual(origin_node_final_size, 0,
        'Case 2: Origin population did not decrease correctly.')
        self.assertEqual(destination_node_final_size, 100,
        'Case 2: Destination population did not increase correctly.')
        self.assertEqual(destination_node_original_size + original_available_population, destination_node_final_size,
        'Case 2: Destination population did not increase correctly.')
        self.assertEqual(len(node_origin.contained_blobs), 0,
        'Case 2: Origin EnvNode Blob count different than expected.')
        self.assertEqual(len(node_destination.contained_blobs), 2,
        'Case 2: Destination EnvNode Blob count different than expected.')
        self.assertEqual(graph_original_size, graph_final_size,
        'Case 2: Population size changed.')
        
        # Case 3:
        # Merge destionation node after two move_populations
        self.envA.merge_node(node_destination)
        destination_node_final_size = node_destination.get_population_size()
        
        # assert validity and correct sizes
        self.assertTrue(verify_graph_validity(self.envA),
        'Case 3: Graph is not valid.')
        self.assertEqual(len(node_destination.contained_blobs), 1,
        'Case 3: Destination EnvNode Blob count different than expected.')
        self.assertEqual(destination_node_final_size, 100,
        'Case 3: Destination population did not increase correctly.')
      
    ## EnvironmentGraph.consume_time_action - move_population with traceable properties in the template
    def test_graph_consume_time_action_move_population_traceable_properties(self):
        """Tests EnvironmentGraph.move_population

        Assumes the move_population action is valid (the necessary population will be available).
        Uses a PopTemplate with traceable properties in all actions.
        
        Case 1: 
            action: Operates one move_population action. Less population than available.
            result: Graph is valid.
                    Origin node contains less population.
                    Origin node contains available population of the requested PopTemplate.
                    Target node has population increased by quantity.
    
        Case 2: 
            action: Operates one move_population action. Equal population as available.
            result: Graph is valid.
                    Origin node contains less population.
                    Origin node doesn't contains available population of the requested PopTemplate.
                    Target node has population increased by quantity.
                    
        Case 3: 
            action: Operates one move_population action. More than available population.
            result: Graph is valid.
                    Origin node contains less population.
                    Origin node doesn't contains available population of the requested PopTemplate.
                    Target node has population increased by quantity.
                    
        Case 4: 
            action: Operates one move_population action. Quantity = -1. Represents move all population.
            result: Graph is valid.
                    Origin node contains less population.
                    Origin node doesn't contains available population of the requested PopTemplate.
                    Target node has population increased by quantity.
                    
        Case 5: 
            action: Operates one move_population action. Quantity = 0. Operation should not occur.
            result: Graph is valid.
                    Populations remain the same.
        """
        # Gets a deepcopy of EnvironmentGraph_B do test multiple cases
        _envs = [copy.deepcopy(self.envB) for x in range(0,5)]
        
        # Sets a PopTemplate
        pop_template = PopTemplate() 
        pop_template.set_traceable_property('traceable_A', 'default')
        
        # Gets the EnvNodes used in the operation
        node_origin = _envs[0].get_node_by_name('Petropolis', 'home')
        node_destination = _envs[0].get_node_by_name('Centro', 'work')
        
        # Gets sizes before operation
        graph_original_size = self.envA.get_population_size()
        origin_node_original_size = node_origin.get_population_size()
        original_available_population = node_origin.get_population_size(pop_template)
        destination_node_original_size = node_destination.get_population_size()
        
        # Setup of move_population TimeAction - Requests half of original population
        values = {  'origin_region': node_origin.containing_region_name,
                    'origin_node': node_origin.name,
                    'destination_region': node_destination.containing_region_name,
                    'destination_node': node_destination.name,
                    'quantity': original_available_population//2,
                    'population_template':pop_template}
        action = TimeAction('move_population', values)
        
        # Consumes the TimeAction
        _envs[0].consume_time_action(action, 0, 0)

        # Gets sizes after operation
        graph_final_size  = self.envA.get_population_size()
        origin_node_final_size = node_origin.get_population_size()
        final_available_population = node_origin.get_population_size(pop_template)
        destination_node_final_size = node_destination.get_population_size()

        # assert validity and correct sizes
        self.assertTrue(verify_graph_validity(_envs[0]),
        'Case 1: Graph is not valid.')
        self.assertEqual(original_available_population, 200,
        'Case 1: Original available population different than expected.')
        self.assertEqual(final_available_population, 100,
        'Case 1: Final available population different than expected.')
        self.assertEqual(origin_node_final_size + original_available_population//2, origin_node_original_size,
        'Case 1: Origin population did not decrease correctly.')
        self.assertEqual(origin_node_final_size, 300,
        'Case 1: Origin population did not decrease correctly.')
        self.assertEqual(destination_node_final_size, 100,
        'Case 1: Destination population did not increase correctly.')
        self.assertEqual(destination_node_original_size  + original_available_population//2, destination_node_final_size,
        'Case 1: Destination population did not increase correctly.')
        self.assertEqual(len(node_origin.contained_blobs), 4,
        'Case 1: Origin EnvNode Blob count different than expected.')
        self.assertEqual(len(node_destination.contained_blobs), 2,
        'Case 1: Destination EnvNode Blob count different than expected.')
        self.assertEqual(graph_original_size, graph_final_size,
        'Case 1: Population size changed.')
        
        # Case 2:
        # Gets the EnvNodes used in the operation
        node_origin = _envs[1].get_node_by_name('Petropolis', 'home')
        node_destination = _envs[1].get_node_by_name('Centro', 'work')
        
        # Gets sizes before operation
        graph_original_size = _envs[1].get_population_size()
        origin_node_original_size = node_origin.get_population_size()
        original_available_population = node_origin.get_population_size(pop_template)
        destination_node_original_size = node_destination.get_population_size()
        
        # Setup of move_population TimeAction - Requests a amount equal as the original population
        values = {  'origin_region': node_origin.containing_region_name,
                    'origin_node': node_origin.name,
                    'destination_region': node_destination.containing_region_name,
                    'destination_node': node_destination.name,
                    'quantity': original_available_population,
                    'population_template':pop_template}
        action = TimeAction('move_population', values)
        
        # Consumes the TimeAction
        _envs[1].consume_time_action(action, 0, 0)

        # Gets sizes before operation
        graph_final_size  = _envs[1].get_population_size()
        origin_node_final_size = node_origin.get_population_size()
        final_available_population = node_origin.get_population_size(pop_template)
        destination_node_final_size = node_destination.get_population_size()

        # assert validity and correct sizes
        self.assertTrue(verify_graph_validity(_envs[1]),
        'Case 2: Graph is not valid.')
        self.assertEqual(original_available_population, 200,
        'Case 2: Original available population different than expected.')
        self.assertEqual(final_available_population, 0,
        'Case 2: Final available population different than expected.')
        self.assertEqual(origin_node_final_size, origin_node_original_size - original_available_population,
        'Case 2: Origin population did not decrease correctly.')
        self.assertEqual(origin_node_final_size, 200,
        'Case 2: Origin population did not decrease correctly.')
        self.assertEqual(destination_node_final_size, 200,
        'Case 2: Destination population did not increase correctly.')
        self.assertEqual(destination_node_final_size, original_available_population,
        'Case 2: Destination population did not increase correctly.')
        self.assertEqual(destination_node_original_size + original_available_population, destination_node_final_size,
        'Case 2: Destination population did not increase correctly.')
        self.assertEqual(len(node_origin.contained_blobs), 2,
        'Case 2: Origin EnvNode Blob count different than expected.')
        self.assertEqual(len(node_destination.contained_blobs), 2,
        'Case 2: Destination EnvNode Blob count different than expected.')
        self.assertEqual(graph_original_size, graph_final_size,
        'Case 2: Population size changed.')
        
        # Case 3:
        # Gets the EnvNodes used in the operation
        node_origin = _envs[2].get_node_by_name('Petropolis', 'home')
        node_destination = _envs[2].get_node_by_name('Centro', 'work')
        
        # Gets sizes before operation
        graph_original_size = _envs[2].get_population_size()
        origin_node_original_size = node_origin.get_population_size()
        original_available_population = node_origin.get_population_size(pop_template)
        destination_node_original_size = node_destination.get_population_size()
        
        # Setup of move_population TimeAction - Requests double the original population
        values = {  'origin_region': node_origin.containing_region_name,
                    'origin_node': node_origin.name,
                    'destination_region': node_destination.containing_region_name,
                    'destination_node': node_destination.name,
                    'quantity': original_available_population * 2,
                    'population_template':pop_template}
        action = TimeAction('move_population', values)
        
        # Consumes the TimeAction
        _envs[2].consume_time_action(action, 0, 0)

        # Gets sizes before operation
        graph_final_size  = _envs[2].get_population_size()
        origin_node_final_size = node_origin.get_population_size()
        final_available_population = node_origin.get_population_size(pop_template)
        destination_node_final_size = node_destination.get_population_size()

        # assert validity and correct sizes
        self.assertTrue(verify_graph_validity(_envs[2]),
        'Case 3: Graph is not valid.')
        self.assertEqual(original_available_population, 200,
        'Case 3: Original available population different than expected.')
        self.assertEqual(final_available_population, 0,
        'Case 3: Final available population different than expected.')
        self.assertEqual(origin_node_final_size, origin_node_original_size - original_available_population,
        'Case 3: Origin population did not decrease correctly.')
        self.assertEqual(origin_node_final_size, 200,
        'Case 3: Origin population did not decrease correctly.')
        self.assertEqual(destination_node_final_size, 200,
        'Case 3: Destination population did not increase correctly.')
        self.assertEqual(destination_node_final_size, original_available_population,
        'Case 3: Destination population did not increase correctly.')
        self.assertEqual(destination_node_original_size + original_available_population, destination_node_final_size,
        'Case 3: Destination population did not increase correctly.')
        self.assertEqual(len(node_origin.contained_blobs), 2,
        'Case 3: Origin EnvNode Blob count different than expected.')
        self.assertEqual(len(node_destination.contained_blobs), 2,
        'Case 3: Destination EnvNode Blob count different than expected.')
        self.assertEqual(graph_original_size, graph_final_size,
        'Case 3: Population size changed.')
        
        # Case 4:
        # Gets the EnvNodes used in the operation
        node_origin = _envs[3].get_node_by_name('Petropolis', 'home')
        node_destination = _envs[3].get_node_by_name('Centro', 'work')
        
        # Gets sizes before operation
        graph_original_size = _envs[3].get_population_size()
        origin_node_original_size = node_origin.get_population_size()
        original_available_population = node_origin.get_population_size(pop_template)
        destination_node_original_size = node_destination.get_population_size()
        
        # Setup of move_population TimeAction - Requests double the original population
        values = {  'origin_region': node_origin.containing_region_name,
                    'origin_node': node_origin.name,
                    'destination_region': node_destination.containing_region_name,
                    'destination_node': node_destination.name,
                    'quantity': -1,
                    'population_template':pop_template}
        action = TimeAction('move_population', values)
        
        # Consumes the TimeAction
        _envs[3].consume_time_action(action, 0, 0)

        # Gets sizes before operation
        graph_final_size  = _envs[3].get_population_size()
        origin_node_final_size = node_origin.get_population_size()
        final_available_population = node_origin.get_population_size(pop_template)
        destination_node_final_size = node_destination.get_population_size()
        
        # assert validity and correct sizes
        self.assertTrue(verify_graph_validity(_envs[3]),
        'Case 4: Graph is not valid.')
        self.assertEqual(original_available_population, 200,
        'Case 4: Original available population different than expected.')
        self.assertEqual(final_available_population, 0,
        'Case 4: Final available population different than expected.')
        self.assertEqual(origin_node_final_size, origin_node_original_size - original_available_population,
        'Case 4: Origin population did not decrease correctly.')
        self.assertEqual(origin_node_final_size, 200,
        'Case 4: Origin population did not decrease correctly.')
        self.assertEqual(destination_node_final_size, 200,
        'Case 4: Destination population did not increase correctly.')
        self.assertEqual(destination_node_final_size, original_available_population,
        'Case 4: Destination population did not increase correctly.')
        self.assertEqual(destination_node_original_size + original_available_population, destination_node_final_size,
        'Case 4: Destination population did not increase correctly.')
        self.assertEqual(len(node_origin.contained_blobs), 2,
        'Case 4: Origin EnvNode Blob count different than expected.')
        self.assertEqual(len(node_destination.contained_blobs), 2,
        'Case 4: Destination EnvNode Blob count different than expected.')
        self.assertEqual(graph_original_size, graph_final_size,
        'Case 4: Population size changed.')
        
        # Case 5:
        # Gets the EnvNodes used in the operation
        node_origin = _envs[4].get_node_by_name('Petropolis', 'home')
        node_destination = _envs[4].get_node_by_name('Centro', 'work')
        
        # Gets sizes before operation
        graph_original_size = _envs[4].get_population_size()
        origin_node_original_size = node_origin.get_population_size()
        original_available_population = node_origin.get_population_size(pop_template)
        destination_node_original_size = node_destination.get_population_size()
        
        # Setup of move_population TimeAction - Requests double the original population
        values = {  'origin_region': node_origin.containing_region_name,
                    'origin_node': node_origin.name,
                    'destination_region': node_destination.containing_region_name,
                    'destination_node': node_destination.name,
                    'quantity': 0,
                    'population_template':pop_template}
        action = TimeAction('move_population', values)
        
        # Consumes the TimeAction
        _envs[4].consume_time_action(action, 0, 0)

        # Gets sizes before operation
        graph_final_size  = _envs[4].get_population_size()
        origin_node_final_size = node_origin.get_population_size()
        final_available_population = node_origin.get_population_size(pop_template)
        destination_node_final_size = node_destination.get_population_size()
        
        # assert validity and correct sizes
        self.assertTrue(verify_graph_validity(_envs[4]),
        'Case 5: Graph is not valid.')
        self.assertEqual(origin_node_final_size, origin_node_original_size,
        'Case 5: Origin population changed.')
        self.assertEqual(origin_node_final_size, 400,
        'Case 5: Origin population changed.')
        self.assertEqual(destination_node_final_size, 0,
        'Case 5: Destination population changed.')
        self.assertEqual(destination_node_final_size, destination_node_original_size ,
        'Case 5: Destination population changed.')
        self.assertEqual(len(node_origin.contained_blobs), 4,
        'Case 5: Origin EnvNode Blob count different than expected.')
        self.assertEqual(len(node_destination.contained_blobs), 0,
        'Case 5: Destination EnvNode Blob count different than expected.')
        self.assertEqual(graph_original_size, graph_final_size,
        'Case 5: Population size changed.')
         
    ## EnvNode.grab_population - with multiple values for a traceable property in the template
    def test_graph_consume_time_action_move_population_traceable_properties_multiple_values(self):
        """Tests EnvironmentGraph.move_population
        
        Assumes the move_population action is valid (the necessary population will be available).
        Uses a PopTemplate with multiple values of traceable properties in all actions.
        
        Case 1: 
            action: Operates one move_population action. Requests less population than available.
            result: Graph is valid.
                    Origin node contains less population.
                    Origin node contains available population of the requested PopTemplate.
                    Target node has population increased by quantity.      
                    
        Case 2: 
            action: Operates one move_population action. Equal population as available.
            result: Graph is valid.
                    Origin node contains less population.
                    Origin node doesn't contains available population of the requested PopTemplate.
                    Target node has population increased by quantity.
                    
        Case 3: 
            action: Operates one move_population action. More population than available.
            result: Graph is valid.
                    Origin node contains less population.
                    Origin node doesn't contains available population of the requested PopTemplate.
                    Target node has population increased by quantity.
                    
        Case 4: 
            action: Operates one move_population action. Quantity = -1. Represents move all population.
            result: Graph is valid.
                    Origin node contains less population.
                    Origin node doesn't contains available population of the requested PopTemplate.
                    Target node has population increased by quantity.
                    
        Case 5: 
            action: Operates one move_population action. Quantity = 0. Operation should not occur.
            result: Graph is valid.
                    Populations remain the same.
        """
        # Gets a deepcopy of EnvironmentGraph_A do test multiple cases
        _envs = [copy.deepcopy(self.envB) for x in range(0,5)]
        
        # Sets a PopTemplate
        pop_template = PopTemplate() 
        pop_template.set_traceable_property('traceable_A', ['default', 'other_value'])
                
        # Case 1:
        # Gets the EnvNodes used in the operation
        node_origin = _envs[0].get_node_by_name('Petropolis', 'home')
        node_destination = _envs[0].get_node_by_name('Centro', 'work')
        
        # Gets sizes before operation
        graph_original_size = _envs[0].get_population_size()
        origin_node_original_size = node_origin.get_population_size()
        original_available_population = node_origin.get_population_size(pop_template)
        destination_node_original_size = node_destination.get_population_size()
        
        # Setup of move_population TimeAction - Requests half of original population
        values = {  'origin_region': node_origin.containing_region_name,
                    'origin_node': node_origin.name,
                    'destination_region': node_destination.containing_region_name,
                    'destination_node': node_destination.name,
                    'quantity': original_available_population//2,
                    'population_template':pop_template}
        action = TimeAction('move_population', values)
        
        # Consumes the TimeAction
        _envs[0].consume_time_action(action, 0, 0)

        # Gets sizes after operation
        graph_final_size  = _envs[0].get_population_size()
        origin_node_final_size = node_origin.get_population_size()
        final_available_population = node_origin.get_population_size(pop_template)
        destination_node_final_size = node_destination.get_population_size()
        
        # assert validity and correct sizes
        self.assertTrue(verify_graph_validity(_envs[0]),
        'Case 1: Graph is not valid.')
        self.assertEqual(original_available_population, 400,
        'Case 1: Original available population different than expected.')
        self.assertEqual(final_available_population, 200,
        'Case 1: Final available population different than expected.')
        self.assertEqual(origin_node_final_size + original_available_population//2, origin_node_original_size,
        'Case 1: Origin population did not decrease correctly.')
        self.assertEqual(origin_node_final_size, 200,
        'Case 1: Origin population did not decrease correctly.')
        self.assertEqual(destination_node_final_size, 200,
        'Case 1: Destination population did not increase correctly.')
        self.assertEqual(destination_node_original_size  + original_available_population//2, destination_node_final_size,
        'Case 1: Destination population did not increase correctly.')
        self.assertEqual(len(node_origin.contained_blobs), 4,
        'Case 1: Origin EnvNode Blob count different than expected.')
        self.assertEqual(len(node_destination.contained_blobs), 4,
        'Case 1: Destination EnvNode Blob count different than expected.')
        self.assertEqual(graph_original_size, graph_final_size,
        'Case 1: Population size changed.')
        
        # Case 2:
        # Gets the EnvNodes used in the operation
        node_origin = _envs[1].get_node_by_name('Petropolis', 'home')
        node_destination = _envs[1].get_node_by_name('Centro', 'work')
        
        # Gets sizes before operation
        graph_original_size = _envs[1].get_population_size()
        origin_node_original_size = node_origin.get_population_size()
        original_available_population = node_origin.get_population_size(pop_template)
        destination_node_original_size = node_destination.get_population_size()
        
        # Setup of move_population TimeAction - Requests a amount equal as the original population
        values = {  'origin_region': node_origin.containing_region_name,
                    'origin_node': node_origin.name,
                    'destination_region': node_destination.containing_region_name,
                    'destination_node': node_destination.name,
                    'quantity': original_available_population,
                    'population_template':pop_template}
        action = TimeAction('move_population', values)
        
        # Consumes the TimeAction
        _envs[1].consume_time_action(action, 0, 0)

        # Gets sizes before operation
        graph_final_size  = _envs[1].get_population_size()
        origin_node_final_size = node_origin.get_population_size()
        final_available_population = node_origin.get_population_size(pop_template)
        destination_node_final_size = node_destination.get_population_size()

        # assert validity and correct sizes
        self.assertTrue(verify_graph_validity(_envs[1]),
        'Case 2: Graph is not valid.')
        self.assertEqual(original_available_population, 400,
        'Case 2: Original available population different than expected.')
        self.assertEqual(final_available_population, 0,
        'Case 2: Final available population different than expected.')
        self.assertEqual(origin_node_final_size, origin_node_original_size - original_available_population,
        'Case 2: Origin population did not decrease correctly.')
        self.assertEqual(origin_node_final_size, 0,
        'Case 2: Origin population did not decrease correctly.')
        self.assertEqual(destination_node_final_size, 400,
        'Case 2: Destination population did not increase correctly.')
        self.assertEqual(destination_node_final_size, original_available_population,
        'Case 2: Destination population did not increase correctly.')
        self.assertEqual(destination_node_original_size + original_available_population, destination_node_final_size,
        'Case 2: Destination population did not increase correctly.')
        self.assertEqual(len(node_origin.contained_blobs), 0,
        'Case 2: Origin EnvNode Blob count different than expected.')
        self.assertEqual(len(node_destination.contained_blobs), 4,
        'Case 2: Destination EnvNode Blob count different than expected.')
        self.assertEqual(graph_original_size, graph_final_size,
        'Case 2: Population size changed.')
        
        # Case 3:
        # Gets the EnvNodes used in the operation
        node_origin = _envs[2].get_node_by_name('Petropolis', 'home')
        node_destination = _envs[2].get_node_by_name('Centro', 'work')
        
        # Gets sizes before operation
        graph_original_size = _envs[2].get_population_size()
        origin_node_original_size = node_origin.get_population_size()
        original_available_population = node_origin.get_population_size(pop_template)
        destination_node_original_size = node_destination.get_population_size()
        
        # Setup of move_population TimeAction - Requests double the original population
        values = {  'origin_region': node_origin.containing_region_name,
                    'origin_node': node_origin.name,
                    'destination_region': node_destination.containing_region_name,
                    'destination_node': node_destination.name,
                    'quantity': original_available_population * 2,
                    'population_template':pop_template}
        action = TimeAction('move_population', values)
        
        # Consumes the TimeAction
        _envs[2].consume_time_action(action, 0, 0)

        # Gets sizes before operation
        graph_final_size  = _envs[2].get_population_size()
        origin_node_final_size = node_origin.get_population_size()
        final_available_population = node_origin.get_population_size(pop_template)
        destination_node_final_size = node_destination.get_population_size()

        # assert validity and correct sizes
        self.assertTrue(verify_graph_validity(_envs[2]),
        'Case 3: Graph is not valid.')
        self.assertEqual(original_available_population, 400,
        'Case 3: Original available population different than expected.')
        self.assertEqual(final_available_population, 0,
        'Case 3: Final available population different than expected.')
        self.assertEqual(origin_node_final_size, origin_node_original_size - original_available_population,
        'Case 3: Origin population did not decrease correctly.')
        self.assertEqual(origin_node_final_size, 0,
        'Case 3: Origin population did not decrease correctly.')
        self.assertEqual(destination_node_final_size, 400,
        'Case 3: Destination population did not increase correctly.')
        self.assertEqual(destination_node_final_size, original_available_population,
        'Case 3: Destination population did not increase correctly.')
        self.assertEqual(destination_node_original_size + original_available_population, destination_node_final_size,
        'Case 3: Destination population did not increase correctly.')
        self.assertEqual(len(node_origin.contained_blobs), 0,
        'Case 3: Origin EnvNode Blob count different than expected.')
        self.assertEqual(len(node_destination.contained_blobs), 4,
        'Case 3: Destination EnvNode Blob count different than expected.')
        self.assertEqual(graph_original_size, graph_final_size,
        'Case 3: Population size changed.')
                
        # Case 4:
        # Gets the EnvNodes used in the operation
        node_origin = _envs[3].get_node_by_name('Petropolis', 'home')
        node_destination = _envs[3].get_node_by_name('Centro', 'work')
        
        # Gets sizes before operation
        graph_original_size = _envs[3].get_population_size()
        origin_node_original_size = node_origin.get_population_size()
        original_available_population = node_origin.get_population_size(pop_template)
        destination_node_original_size = node_destination.get_population_size()
        
        # Setup of move_population TimeAction - Requests double the original population
        values = {  'origin_region': node_origin.containing_region_name,
                    'origin_node': node_origin.name,
                    'destination_region': node_destination.containing_region_name,
                    'destination_node': node_destination.name,
                    'quantity': -1,
                    'population_template':pop_template}
        action = TimeAction('move_population', values)
        
        # Consumes the TimeAction
        _envs[3].consume_time_action(action, 0, 0)

        # Gets sizes before operation
        graph_final_size  = _envs[3].get_population_size()
        origin_node_final_size = node_origin.get_population_size()
        final_available_population = node_origin.get_population_size(pop_template)
        destination_node_final_size = node_destination.get_population_size()
        
        # assert validity and correct sizes
        self.assertTrue(verify_graph_validity(_envs[3]),
        'Case 4: Graph is not valid.')
        self.assertEqual(original_available_population, 400,
        'Case 4: Original available population different than expected.')
        self.assertEqual(final_available_population, 0,
        'Case 4: Final available population different than expected.')
        self.assertEqual(origin_node_final_size, origin_node_original_size - original_available_population,
        'Case 4: Origin population did not decrease correctly.')
        self.assertEqual(origin_node_final_size, 0,
        'Case 4: Origin population did not decrease correctly.')
        self.assertEqual(destination_node_final_size, 400,
        'Case 4: Destination population did not increase correctly.')
        self.assertEqual(destination_node_final_size, original_available_population,
        'Case 4: Destination population did not increase correctly.')
        self.assertEqual(destination_node_original_size + original_available_population, destination_node_final_size,
        'Case 4: Destination population did not increase correctly.')
        self.assertEqual(len(node_origin.contained_blobs), 0,
        'Case 4: Origin EnvNode Blob count different than expected.')
        self.assertEqual(len(node_destination.contained_blobs), 4,
        'Case 4: Destination EnvNode Blob count different than expected.')
        self.assertEqual(graph_original_size, graph_final_size,
        'Case 4: Population size changed.')
        
        # Case 5:
        # Gets the EnvNodes used in the operation
        node_origin = _envs[4].get_node_by_name('Petropolis', 'home')
        node_destination = _envs[4].get_node_by_name('Centro', 'work')
        
        # Gets sizes before operation
        graph_original_size = _envs[4].get_population_size()
        origin_node_original_size = node_origin.get_population_size()
        original_available_population = node_origin.get_population_size(pop_template)
        destination_node_original_size = node_destination.get_population_size()
        
        # Setup of move_population TimeAction - Requests double the original population
        values = {  'origin_region': node_origin.containing_region_name,
                    'origin_node': node_origin.name,
                    'destination_region': node_destination.containing_region_name,
                    'destination_node': node_destination.name,
                    'quantity': 0,
                    'population_template':pop_template}
        action = TimeAction('move_population', values)
        
        # Consumes the TimeAction
        _envs[4].consume_time_action(action, 0, 0)

        # Gets sizes before operation
        graph_final_size  = _envs[4].get_population_size()
        origin_node_final_size = node_origin.get_population_size()
        final_available_population = node_origin.get_population_size(pop_template)
        destination_node_final_size = node_destination.get_population_size()
        
        # assert validity and correct sizes
        self.assertTrue(verify_graph_validity(_envs[4]),
        'Case 5: Graph is not valid.')
        self.assertEqual(origin_node_final_size, origin_node_original_size,
        'Case 5: Origin population changed.')
        self.assertEqual(origin_node_final_size, 400,
        'Case 5: Origin population changed.')
        self.assertEqual(destination_node_final_size, 0,
        'Case 5: Destination population changed.')
        self.assertEqual(destination_node_final_size, destination_node_original_size ,
        'Case 5: Destination population changed.')
        self.assertEqual(len(node_origin.contained_blobs), 4,
        'Case 5: Origin EnvNode Blob count different than expected.')
        self.assertEqual(len(node_destination.contained_blobs), 0,
        'Case 5: Destination EnvNode Blob count different than expected.')
        self.assertEqual(graph_original_size, graph_final_size,
        'Case 5: Population size changed.')
        

    def test_graph_converge_population(self):
        """Tests EnvironmentGraph.converge_population
        
        Case 1: 
            action: Operates one gather_population action.
            result: Generated action list contains move population actions totaling requested quantity.
                    EnvironmentGraph is valid.
                    Total population unchanged.
                    Target node contains 50 extra population, after generated action list is consumed.
                    

        """
        pop_template  = PopTemplate()

        values = {'destination_region': 'Petropolis', 'destination_node': 'work', 'quantity':50, 'population_template':pop_template}


        action = TimeAction('gather_population', values)
        old_graph_size = self.envA.get_population_size()
        
        target_node = self.envA.get_node_by_name("Petropolis", "work")
        old_node_size = target_node.get_population_size()
        self.envA.consume_time_action(action, 0, 0)
        new_graph_size  = self.envA.get_population_size()
        new_node_size = target_node.get_population_size()

        #print(str(self.env).replace('\'', '\"'))

        self.assertTrue(verify_graph_validity(self.envA),
        'Case 1: Graph is not valid.')
        self.assertEqual(old_graph_size, new_graph_size,
        'Case 1: Total population size changed.')
        self.assertEqual(old_node_size  + 50,
                        new_node_size,
        'Case 1: Node size did not increase by the correct amount.')

    def test_graph_return_population_home(self):
        """Tests EnvironmentGraph.return_population_home
    
        Case 1: 
            action: Operates one return_population_home action.
            result: Generated action list contains move population actions totaling requested quantity.
                    EnvironmentGraph is valid.
                    Total population unchanged.
                    Target node contains all population with the desired mother_blob_id.

        """
        ## individual test setup
        desired_region = self.envA.get_region_by_name("Petropolis")

        reg_aux_1 = self.envA.get_region_by_name('Centro')
        reg_aux_2 = self.envA.get_region_by_name('Partenon')

        node = desired_region.get_node_by_name("home")
        node_blobs = node.contained_blobs
        #gets the one blob
        blob_1 = node_blobs[0]

        #copy extra blobs with same profile
        clone_blob_2 = blob_1.blob_factory.GenerateProfile(desired_region.id, (100,0,0,0), blob_1.profiles)
        clone_blob_3 = blob_1.blob_factory.GenerateProfile(desired_region.id, (100,0,0,0), blob_1.profiles)
        clone_blob_4 = blob_1.blob_factory.GenerateProfile(desired_region.id+1, (100,0,0,0), blob_1.profiles)
        ## add blobs to other regions

        reg_aux_1.get_node_by_name('school').add_blob(clone_blob_2)
        reg_aux_2.get_node_by_name('work').add_blob(clone_blob_3)
        reg_aux_2.get_node_by_name('work').add_blob(clone_blob_4)


        # test function
        pop_template  = PopTemplate()
        pop_template.mother_blob_id = desired_region.id

        values = {'region': 'Petropolis', 'node':'home', 'quantity':-1, 'population_template':pop_template}
        action = TimeAction('return_population_home', values)
        
        old_graph_size = self.envA.get_population_size()

        old_node_size = node.get_population_size()

        self.envA.consume_time_action(action, 0, 0)

        new_graph_size  = self.envA.get_population_size()
        new_node_size = node.get_population_size()

        all_in_home = True
        region_id = self.envA.get_region_by_name('Petropolis').id

        for region in self.envA.region_list:
            if region.name == 'Petropolis':
                continue
            else:
                for node in region.node_list:
                    for blob in node.contained_blobs:
                        if blob.mother_blob_id == region_id:
                            all_in_home = False

        self.assertTrue(all_in_home,
        'Case 1: Population is not entirely home.')
        self.assertTrue(verify_graph_validity(self.envA),
        'Case 1: Graph is not valid.')
        self.assertEqual(old_graph_size, new_graph_size,
        'Case 1: Total population size changed.')
        self.assertEqual(old_node_size + 200,
                        new_node_size,
        'Case 1: Node size did not increase by the correct amount.')



    def test_graph_balance_list(self):
        """Tests EnvironmentGraph.balance_action_list

        Case 1: 
            action: Balances an unbalanced action list.
            result: Balanced action list.
                        A balanced list is a list of actions which are all
                        guaranteed to be viable sequentially.
        
        Case 2: 
            action: Balances a balanced action list.
            result: Balanced action list.
                    A balanced list is a list of actions which are all
                        guaranteed to be viable sequentially.
        """
        pass  

    def test_graph_simplify_list(self):
        """Tests EnvironmentGraph.simplify_action_list

        Case 1: 
            action: Simplifies a list containing 2 move_population, 2 return_population_home and 
                        2 converge_population actions.
            result: List is composed entirely of base actions.

        Case 2:
            action: Simplifies list containing 1 return_population_home.
            result: List is composed entirely of base actions.
                    List moves population to returning node.

        Case 3:
            action: Simplifies list containing 1 gather_population.
            result: List is composed entirely of base actions.
                    List gathers correct amount of population.
  
        """
        pass

    
def suite():  
    suite = unittest.TestSuite()
    
    # EnvNode tests
    # get_population_size
    suite.addTest(EnvironmentTests('test_node_get_population_size_one_blob'))
    suite.addTest(EnvironmentTests('test_node_get_population_size_multiple_blobs'))
    # grab_population
    suite.addTest(EnvironmentTests('test_node_grab_population_no_template_one_blob'))
    suite.addTest(EnvironmentTests('test_node_grab_population_no_template_three_blobs'))
    suite.addTest(EnvironmentTests('test_node_grab_population_no_template_three_blobs_unbalanced'))
    suite.addTest(EnvironmentTests('test_node_grab_population_with_template_one_blob'))
    suite.addTest(EnvironmentTests('test_node_grab_population_with_template_three_blobs'))
    suite.addTest(EnvironmentTests('test_node_grab_population_with_template_three_blobs_unbalanced'))
    suite.addTest(EnvironmentTests('test_node_grab_population_with_complementing_templates'))
    suite.addTest(EnvironmentTests('test_node_grab_population_traceable_properties'))
    suite.addTest(EnvironmentTests('test_node_grab_population_traceable_properties_multiple_values'))
    # process_routine
    suite.addTest(EnvironmentTests('test_node_process_routine'))
   
    # EnvRegion tests
    # get_population_size
    suite.addTest(EnvironmentTests('test_region_get_population_size_one_blob'))
    suite.addTest(EnvironmentTests('test_region_get_population_size_multiple_blobs'))
    # generate_action_list
    suite.addTest(EnvironmentTests('test_region_generate_action_list'))
   
    # EnvironmentGraph tests
    # process_routines
    suite.addTest(EnvironmentTests('test_region_process_routines'))
    # merge_node
    suite.addTest(EnvironmentTests('test_graph_merge_node'))
    suite.addTest(EnvironmentTests('test_graph_merge_node_with_traceable_properties'))
    # consume_time_action
        # move_population
    suite.addTest(EnvironmentTests('test_graph_consume_time_action_move_population'))
    suite.addTest(EnvironmentTests('test_graph_consume_time_action_move_population_with_template'))
    suite.addTest(EnvironmentTests('test_graph_consume_time_action_move_population_with_complementing_templates'))
    suite.addTest(EnvironmentTests('test_graph_consume_time_action_move_population_traceable_properties'))
    suite.addTest(EnvironmentTests('test_graph_consume_time_action_move_population_traceable_properties_multiple_values'))
    
    #     ## consume time action
    #         ## converge population
    # suite.addTest(EnvironmentTests('test_graph_converge_population')) 
    # ###         ## return population home
    # suite.addTest(EnvironmentTests('test_graph_return_population_home')) 
    

    #TODO not implemented yet
        ## balance action list
    #suite.addTest(EnvironmentTests('test_graph_balance_list'))
        ## simplify action list
    #suite.addTest(EnvironmentTests('test_graph_simplify_list'))
    #TODO END not implemented yet

    
    # missing test generate action list (mightnot be necessary)
    return suite       

if __name__ == "__main__":
    FixedRandom()
    runner = unittest.TextTestRunner()
    runner.run(suite())