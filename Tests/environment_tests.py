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
        #sets up the test environment
        environment_path = '../DataInput/Tests/environment_tests_dummy_input_3.json'
        self.env = generate_EnvironmentGraph(environment_path)

        p1 = GatherPopulationNewPlugin(self.env)
        p2 = ReturnPopulationPlugin(self.env)

        self.env.LoadPlugin(p1)
        self.env.LoadPlugin(p2)

    def tearDown(self):
        #resets the test environment
        pass

    ### EnvNode tests
    ## EnvNode.grab_population - without template 
    def test_node_grab_population_no_template_one_blob_case1(self):
        """Tests EnvNode.grab_population
        
        Case 1: 
            action: Requests less population than available.
            result: Node is valid.
                    Blobs are valid.
                    Grabbed Blob is different than one in the node.
                    Total population size unchanged.
                    Blob size equals extracted quantity.      
        """

        # Gets a target EnvNode with population 100
        target_node = self.env.get_node_by_name("Petropolis", "home")
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
        self.assertEqual(node_original_size,
                        node_final_size + grabbed_population_size,
        'Case 1: Total population size changed.')
        self.assertEqual(source_original_size,
                        source_final_size + grabbed_population_size,
        'Case 1: Source population size changed.')
        self.assertEqual(grabbed_population_size,
                        50,
        'Case 1: Grabbed population size is not equal to grabbed amount.')
        self.assertTrue(verify_graph_validity_size(self.env, 300 - grabbed_population_size),
        'Case 1: EnvironmentGraph changed in size.')
        self.assertTrue(verify_node_validity(target_node),
        'Case 1: Grabbed pop still in node.')

    def test_node_grab_population_no_template_one_blob_case2(self):
        """Tests EnvNode.grab_population

        Case 2: 
            action: Equal population as available.
            result: Node is valid.
                    Blobs is valid.
                    Node is empty.
                    Blob is the same as the one that was in the in the node.
                    Total population size unchanged.
                    Blob size equals extracted quantity.
        
        """

        # Gets a target EnvNode with population 100
        target_node = self.env.get_node_by_name("Petropolis", "home")
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
        self.assertTrue(verify_graph_validity_size(self.env, 300 - grabbed_population_size),
        'Case 2: EnvironmentGraph changed in size.')

        
    def test_node_grab_population_no_template_one_blob_case3(self):
        """Tests EnvNode.grab_population

        Case 3: 
            action: More population than available.
            result: Node is valid.
                    Blobs is valid.
                    Node is empty.
                    Blob is the same as the one that was in the in the node.
                    Total population size unchanged.
        
        """

        # Gets a target EnvNode with population 100
        target_node = self.env.get_node_by_name("Petropolis", "home")
        source_blob = target_node.contained_blobs[0]
        node_original_size = target_node.get_population_size()
        source_original_size = source_blob.get_population_size()

        # Grabs 200 people from the target node - more than available
        grabbed_population = target_node.grab_population(100)
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
        self.assertEqual(grabbed_population_size, 100,
        'Case 3: Grabbed population size is not equal to grabbed amount.')
        self.assertTrue(verify_graph_validity_size(self.env, 300 - grabbed_population_size),
        'Case 3: EnvironmentGraph changed in size.')


    def test_node_grab_population_no_template_three_blobs_case1(self):
        """Tests EnvNode.grab_population
        
        Clone two extra Blobs in a EnvNode. Then, grabs population from node

        Case 1: 
            action: Less population than available.
            result: Node is valid.
                    Blobs are valid.
                    Blobs in list are different than one in the node.
                    Total population size unchanged.    
        """

        # Gets a target EnvNode with population 100
        target_node = self.env.get_node_by_name("Petropolis", "home")
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
        self.assertTrue(verify_graph_validity_size(self.env, 500 - grabbed_population_size),
        'Case 1: EnvironmentGraph changed in size.')

    def test_node_grab_population_no_template_three_blobs_case2(self):
        """Tests EnvNode.grab_population

        Case 2: 
            action: Equal population as available.
            result: Node is valid.
                    Blobs are valid.
                    Node is empty.
                    3 Blobs are in list.
                    Total population size unchanged.
        
        """

         # Gets a target EnvNode with population 100
        target_node = self.env.get_node_by_name("Petropolis", "home")
        node_blobs = target_node.contained_blobs

        # Gets the first Blob in target node
        source_blob = node_blobs[0]

        # Copy two extra Blobs with same profile
        clone_blob_1 = source_blob.blob_factory.GenerateProfile(0, 100, source_blob.profiles)
        clone_blob_2 = source_blob.blob_factory.GenerateProfile(0, 100, source_blob.profiles)
        
        # Adds extra Blobs to target node
        target_node.add_blobs([clone_blob_1, clone_blob_2])

        original_blobs = [source_blob, clone_blob_1, clone_blob_2]

        # Grabs 150 people from the target node - less than available
        node_original_size = target_node.get_population_size()
        grabbed_population = target_node.grab_population(300)
        node_final_size = target_node.get_population_size()
        source_final_size = target_node.get_population_size()
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
        self.assertTrue(verify_graph_validity_size(self.env, 500 - grabbed_population_size),
        'Case 2: EnvironmentGraph changed in size.')
        self.assertTrue(all([(x in grabbed_population) for x in original_blobs]),
        'Case 2: Blob is not the same which was in the node.')


    def test_node_grab_population_no_template_three_blobs_case3(self):
        """Tests EnvNode.grab_population

        Case 3: 
            action: More population than available.
            result: Node is valid.
                    No population is removed.
                    3 Blobs are in list.
                    Total population size unchanged.
                    Returns an empty list.
        
        """
        node = self.env.get_region_by_name("Petropolis").get_node_by_name("home")
        node_blobs = node.contained_blobs
        pop_template = PopTemplate()
        old_blob = node_blobs[0]

        #gets the one blob
        blob_1 = node_blobs[0]

        #copy extra blobs with same profile
        clone_blob_2 = blob_1.blob_factory.GenerateProfile(0, (100,0,0,0), blob_1.profiles)
        clone_blob_3 = blob_1.blob_factory.GenerateProfile(0, (100,0,0,0), blob_1.profiles)

        og_blobs = [blob_1, clone_blob_2, clone_blob_3]

        # add extra blobs
        node.add_blobs([clone_blob_2, clone_blob_3])


        old_pop_size = node.get_population_size()
        pop = node.grab_population(600, pop_template)
        new_pop_size = node.get_population_size()
        blob_pop_size = blobs_total_size(pop)

        self.assertTrue(verify_blobs_validity(pop),
        'Case 3: Grabbed population is not valid.')
        self.assertTrue(verify_node_validity(node),
        'Case 3: Grabbed pop still in node.')
        self.assertTrue(len(node_blobs) == 0,
        'Case 3: Node is not empty.')
        self.assertEqual(old_pop_size,
                        new_pop_size + blob_pop_size,
        'Case 3: Total population size changed.')
        self.assertEqual(blob_pop_size,
                        300,
        'Case 3: Grabbed population size is not equal to grabbed amount.')
        self.assertTrue(all([(x in pop) for x in og_blobs]),
        'Case 3: Blob is not the same which was in the node.')
        
    def test_node_grab_population_no_template_three_blobs_unbalanced_case1(self):
        """Tests EnvNode.grab_population
        
        TODO clone_blob_4 is invalid, by choice.

        Case 1: 
            action: Less population than available, one blob has population 0.
                    0 pop blob represents an unmatching population template blob.
                    One blob has less population.

            result: Node is valid.
                    Blobs are valid.
                    Blobs in list are different than one in the node.
                    Total population size unchanged.
        """
        #gets the chosen region
        node = self.env.get_region_by_name("Petropolis").get_node_by_name("home")
        node_blobs = node.contained_blobs

        #gets the one blob
        blob_1 = node_blobs[0]

        #copy extra blobs with same profile
        clone_blob_2 = blob_1.blob_factory.GenerateProfile(0, (100,0,0,0), blob_1.profiles)
        clone_blob_3 = blob_1.blob_factory.Generate(0, (10,0,0,0))
        clone_blob_4 = blob_1.blob_factory.Generate(0, (0,0,0,0))

        # add extra blobs
        node.add_blobs([clone_blob_2, clone_blob_3, clone_blob_4])

        pop_template = PopTemplate()
        old_pop_size = node.get_population_size()
        pop = node.grab_population(150, pop_template)
        new_pop_size = node.get_population_size()
        blob_pop_size = blobs_total_size(pop)

        # clean up node.
        node.remove_blob(clone_blob_4)

        self.assertTrue(verify_blobs_validity(pop),
        'Case 1: Grabbed population is not valid.')
        self.assertTrue(not verify_blobs_contained_in_node(pop, node),
        'Case 1: Grabbed pop still in node.')
        self.assertEqual(old_pop_size,
                        new_pop_size + blob_pop_size,
        'Case 1: Total population size changed.')
        self.assertEqual(blob_pop_size,
                        150,
        'Case 1: Grabbed population size is not equal to grabbed amount.')
        self.assertTrue(verify_node_validity(node),
        'Case 1: Grabbed pop still in node.')

    def test_node_grab_population_no_template_three_blobs_unbalanced_case2(self):
        """Tests EnvNode.grab_population

        TODO clone_blob_4 is invalid, by choice.

        Case 2: 
            action: Equal population as available, one blob has population 0.
                    0 pop blob represents an unmatching population template blob.
                    One blob has less population.
            result: Node is valid.
                    Blobs are valid.
                    Node is empty.
                    3 Blobs are in list.
                    Total population size unchanged.
        
        """
        node = self.env.get_region_by_name("Petropolis").get_node_by_name("home")
        node_blobs = node.contained_blobs
        pop_template = PopTemplate()
        old_blob = node_blobs[0]

        #gets the one blob
        blob_1 = node_blobs[0]

        #copy extra blobs with same profile
        clone_blob_2 = blob_1.blob_factory.GenerateProfile(0, (100,0,0,0), blob_1.profiles)
        clone_blob_3 = blob_1.blob_factory.Generate(0, (10,0,0,0))
        clone_blob_4 = blob_1.blob_factory.Generate(0, (0,0,0,0))

        og_blobs = [blob_1, clone_blob_2, clone_blob_3]

        # add extra blobs
        node.add_blobs([clone_blob_2, clone_blob_3, clone_blob_4])


        old_pop_size = node.get_population_size()
        pop = node.grab_population(300, pop_template)
        new_pop_size = node.get_population_size()
        blob_pop_size = blobs_total_size(pop)

        # clean up node.
        node.remove_blob(clone_blob_4)

        self.assertTrue(verify_blobs_validity(pop),
        'Case 2: Grabbed population is not valid.')
        self.assertTrue(verify_node_validity(node),
        'Case 2: Grabbed pop still in node.')
        self.assertTrue(len(node_blobs) == 0,
        'Case 2: Node is not empty.')
        self.assertEqual(old_pop_size,
                        new_pop_size + blob_pop_size,
        'Case 2: Total population size changed.')
        self.assertEqual(blob_pop_size,
                        old_pop_size,
        'Case 2: Grabbed population size is not the original node side.')
        self.assertTrue(all([(x in pop) for x in og_blobs]),
        'Case 2: Blob is not the same which was in the node.')


    def test_node_grab_population_no_template_three_blobs_unbalanced_case3(self):
        """Tests EnvNode.grab_population

        TODO clone_blob_4 is invalid, by choice.

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
        node = self.env.get_region_by_name("Petropolis").get_node_by_name("home")
        node_blobs = node.contained_blobs
        pop_template = PopTemplate()
        old_blob = node_blobs[0]

        #gets the one blob
        blob_1 = node_blobs[0]

        #copy extra blobs with same profile
        clone_blob_2 = blob_1.blob_factory.GenerateProfile(0, (100,0,0,0), blob_1.profiles)
        clone_blob_3 = blob_1.blob_factory.Generate(0, (10,0,0,0))
        clone_blob_4 = blob_1.blob_factory.Generate(0, (0,0,0,0))

        og_blobs = [blob_1, clone_blob_2, clone_blob_3]

        # add extra blobs
        node.add_blobs([clone_blob_2, clone_blob_3, clone_blob_4])


        old_pop_size = node.get_population_size()
        pop = node.grab_population(600, pop_template)
        new_pop_size = node.get_population_size()
        blob_pop_size = blobs_total_size(pop)

        # clean up node.
        node.remove_blob(clone_blob_4)

        self.assertTrue(verify_blobs_validity(pop),
        'Case 3: Grabbed population is not valid.')
        self.assertTrue(verify_node_validity(node),
        'Case 3: Grabbed pop still in node.')
        self.assertTrue(len(node_blobs) == 0,
        'Case 3: Node is not empty.')
        self.assertEqual(old_pop_size,
                        new_pop_size + blob_pop_size,
        'Case 3: Total population size changed.')
        self.assertEqual(blob_pop_size,
                        210,
        'Case 3: Grabbed population size is not equal to grabbed amount.')
        self.assertTrue(all([(x in pop) for x in og_blobs]),
        'Case 3: Blob is not the same which was in the node.')

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
        old_graph_size = self.env.get_population_size()

        node = self.env.get_region_by_name('Petropolis').get_node_by_name('work')
        old_node_size = node.get_population_size()
        self.env.consume_time_action(action, 0, 0)
        new_graph_size  = self.env.get_population_size()
        new_node_size = node.get_population_size()

        #print(str(self.env).replace('\'', '\"'))

        self.assertTrue(verify_graph_validity(self.env),
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
        desired_region = self.env.get_region_by_name("Petropolis")

        reg_aux_1 = self.env.get_region_by_name('Centro')
        reg_aux_2 = self.env.get_region_by_name('Partenon')

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
        
        old_graph_size = self.env.get_population_size()

        old_node_size = node.get_population_size()

        self.env.consume_time_action(action, 0, 0)

        new_graph_size  = self.env.get_population_size()
        new_node_size = node.get_population_size()

        all_in_home = True
        region_id = self.env.get_region_by_name('Petropolis').id

        for region in self.env.region_list:
            if region.name == 'Petropolis':
                continue
            else:
                for node in region.node_list:
                    for blob in node.contained_blobs:
                        if blob.mother_blob_id == region_id:
                            all_in_home = False

        self.assertTrue(all_in_home,
        'Case 1: Population is not entirely home.')
        self.assertTrue(verify_graph_validity(self.env),
        'Case 1: Graph is not valid.')
        self.assertEqual(old_graph_size, new_graph_size,
        'Case 1: Total population size changed.')
        self.assertEqual(old_node_size + 200,
                        new_node_size,
        'Case 1: Node size did not increase by the correct amount.')


    def test_graph_move_population_case1(self):
        """Tests EnvironmentGraph.move_population

        Assumes the move_population action is valid (the necessary population will be available).
        
        Case 1: 
            action: Operates one move_population action. Less population than available.
            result: Graph is valid.
                    Origin node contains quantity less population.
                    Target node has population increased by quantity.
    
        """
        pop_template  = PopTemplate()

        values = {  'origin_region': 'Petropolis',
                    'origin_node': 'home',
                    'destination_region': 'Centro',
                    'destination_node': 'work',
                    'quantity':50,
                    'population_template':pop_template}

        action = TimeAction('move_population', values)
        old_graph_size = self.env.get_population_size()

        node_origin = self.env.get_region_by_name('Petropolis').get_node_by_name('home')
        node_destination = self.env.get_region_by_name('Centro').get_node_by_name('work')

        old_node_origin_size = node_origin.get_population_size()
        old_node_destination_size = node_destination.get_population_size()

        self.env.consume_time_action(action, 0, 0)

        new_graph_size  = self.env.get_population_size()

        new_node_origin_size = node_origin.get_population_size()
        new_node_destination_size = node_destination.get_population_size()

        self.assertTrue(verify_graph_validity(self.env),
        'Case 1: Graph is not valid.')
        self.assertEqual(new_node_origin_size, old_node_origin_size - 50,
        'Case 1: Origin population did not decrease correctly.')
        self.assertEqual(old_node_destination_size  + 50,
                        new_node_destination_size,
        'Case 1: Destination population did not increase correctly.')
        self.assertEqual(old_graph_size,
                        new_graph_size,
        'Case 1: Population size changed.')

    def test_graph_move_population_case2(self):
        """Tests EnvironmentGraph.move_population

        Case 2: 
            action: Operates one move_population action. Equal population as available.
            result: Graph is valid.
                    Origin node contains quantity less population.
                    Target node has population increased by quantity.        
        """
        pop_template  = PopTemplate()

        values = {  'origin_region': 'Petropolis',
                    'origin_node': 'home',
                    'destination_region': 'Centro',
                    'destination_node': 'work',
                    'quantity':100,
                    'population_template':pop_template}

        action = TimeAction('move_population', values)
        old_graph_size = self.env.get_population_size()

        node_origin = self.env.get_region_by_name('Petropolis').get_node_by_name('home')
        node_destination = self.env.get_region_by_name('Centro').get_node_by_name('work')

        old_node_origin_size = node_origin.get_population_size()
        old_node_destination_size = node_destination.get_population_size()

        self.env.consume_time_action(action, 0, 0)

        new_graph_size  = self.env.get_population_size()

        new_node_origin_size = node_origin.get_population_size()
        new_node_destination_size = node_destination.get_population_size()

        self.assertTrue(verify_graph_validity(self.env),
        'Case 2: Graph is not valid.')
        self.assertEqual(new_node_origin_size, 0 ,
        'Case 2: Origin population is not 0.')
        self.assertEqual(old_node_destination_size  + old_node_origin_size,
                        new_node_destination_size,
        'Case 2: Destination population did not increase correctly.')
        self.assertEqual(old_graph_size,
                        new_graph_size,
        'Case 2: Population size changed.')

    
    def test_graph_move_population_case3(self):
        """Tests EnvironmentGraph.move_population

        Assumes the move_population action is valid (the necessary population will be available).

        Case 3: 
            action: Operates one move_population action. More than available population.
            result: Graph is valid.
                    Origin node contains 0 population.
                    Target node has sum of populations.        
        """
        pop_template  = PopTemplate()

        values = {  'origin_region': 'Petropolis',
                    'origin_node': 'home',
                    'destination_region': 'Centro',
                    'destination_node': 'work',
                    'quantity':500,
                    'population_template':pop_template}

        action = TimeAction('move_population', values)
        old_graph_size = self.env.get_population_size()

        node_origin = self.env.get_region_by_name('Petropolis').get_node_by_name('home')
        node_destination = self.env.get_region_by_name('Centro').get_node_by_name('work')

        old_node_origin_size = node_origin.get_population_size()
        old_node_destination_size = node_destination.get_population_size()

        self.env.consume_time_action(action, 0, 0)

        new_graph_size  = self.env.get_population_size()

        new_node_origin_size = node_origin.get_population_size()
        new_node_destination_size = node_destination.get_population_size()

        self.assertTrue(verify_graph_validity(self.env),
        'Case 3: Graph is not valid.')
        self.assertEqual(new_node_origin_size, 0 ,
        'Case 3: Origin population is not 0.')
        self.assertEqual(old_node_destination_size  + old_node_origin_size,
                        new_node_destination_size,
        'Case 3: Destination population did not increase correctly.')
        self.assertEqual(old_graph_size,
                        new_graph_size,
        'Case 3: Population size changed.')

    def test_graph_move_population_case4(self):
        """Tests EnvironmentGraph.move_population

        Assumes the move_population action is valid (the necessary population will be available).

        Case 4: 
            action: Operates one move_population action. Quantity = -1. Represents move all population.
            result: Graph is valid.
                    Origin node contains 0 population.
                    Target node has sum of populations.        
        """
        pop_template  = PopTemplate()

        values = {  'origin_region': 'Petropolis',
                    'origin_node': 'home',
                    'destination_region': 'Centro',
                    'destination_node': 'work',
                    'quantity':-1,
                    'population_template':pop_template}

        action = TimeAction('move_population', values)
        old_graph_size = self.env.get_population_size()

        node_origin = self.env.get_region_by_name('Petropolis').get_node_by_name('home')
        node_destination = self.env.get_region_by_name('Centro').get_node_by_name('work')

        old_node_origin_size = node_origin.get_population_size()
        old_node_destination_size = node_destination.get_population_size()

        self.env.consume_time_action(action, 0, 0)

        new_graph_size  = self.env.get_population_size()

        new_node_origin_size = node_origin.get_population_size()
        new_node_destination_size = node_destination.get_population_size()

        self.assertTrue(verify_graph_validity(self.env),
        'Case 4: Graph is not valid.')
        self.assertEqual(new_node_origin_size, 0 ,
        'Case 4: Origin population is not 0.')
        self.assertEqual(old_node_destination_size  + old_node_origin_size,
                        new_node_destination_size,
        'Case 4: Destination population did not increase correctly.')
        self.assertEqual(old_graph_size,
                        new_graph_size,
        'Case 4: Population size changed.') 


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

    def test_graph_merge_blobs(self):
        """Tests EnvironmentGraph.merge_node

        Case 1: 
            action: Merges blobs in graph.
            result: Graph contains only nodes containing unique mother_blob_id containiend_blob lists.
        """
        node = self.env.get_region_by_name("Petropolis").get_node_by_name("home")
        node_blobs = node.contained_blobs
        pop_template = PopTemplate()
        old_blob = node_blobs[0]

        #gets the one blob
        blob_1 = node_blobs[0]

        #copy extra blobs with same profile
        clone_blob_2 = blob_1.blob_factory.GenerateProfile(blob_1.mother_blob_id, (100,0,0,0), blob_1.profiles)
        clone_blob_3 = blob_1.blob_factory.GenerateProfile(blob_1.mother_blob_id+1, (100,0,0,0), blob_1.profiles)
        clone_blob_4 = blob_1.blob_factory.GenerateProfile(blob_1.mother_blob_id+1, (100,0,0,0), blob_1.profiles)
        
        # add extra blobs
        node.add_blobs([clone_blob_2, clone_blob_3, clone_blob_4 ])


        old_graph_size = self.env.get_population_size()
        old_node_size = node.get_population_size()
        #
        # 
        # old_blobs_in_node = len(node.contained_blobs)

        self.env.merge_node(node)

        new_graph_size = self.env.get_population_size()
        new_node_size = node.get_population_size()
        
        #new_blobs_in_node = len(node.contained_blobs)
        #print(old_node_size, new_node_size)
        #print(old_blobs_in_node, new_blobs_in_node)
        
        ids = set()
        result = True
        for blob in node.contained_blobs:
            if blob.mother_blob_id not in ids:
                ids.add(blob.mother_blob_id)
            else:
                result = False

        self.assertTrue(verify_graph_validity(self.env),
        'Case 1: Graph is not valid.')
        self.assertTrue(result,
        'Case 1: mother_blob_id repeated in node.contained_blobs.')
        self.assertEqual(new_graph_size, old_graph_size,
        'Case 1: Total population size changed.')
        self.assertEqual(new_node_size, old_node_size,
        'Case 1: Total population size in node changed.')



def suite():  
    suite = unittest.TestSuite()
    #### Node tests
        ## grab population
    suite.addTest(EnvironmentTests('test_node_grab_population_no_template_one_blob_case1'))
    suite.addTest(EnvironmentTests('test_node_grab_population_no_template_one_blob_case2'))
    suite.addTest(EnvironmentTests('test_node_grab_population_no_template_one_blob_case3'))
    suite.addTest(EnvironmentTests('test_node_grab_population_no_template_three_blobs_case1'))
    suite.addTest(EnvironmentTests('test_node_grab_population_no_template_three_blobs_case2'))
    # suite.addTest(EnvironmentTests('test_node_grab_population_no_template_three_blobs_case3'))
    # suite.addTest(EnvironmentTests('test_node_grab_population_no_template_three_blobs_unbalanced_case1'))
    # suite.addTest(EnvironmentTests('test_node_grab_population_no_template_three_blobs_unbalanced_case2'))
    # suite.addTest(EnvironmentTests('test_node_grab_population_no_template_three_blobs_unbalanced_case3'))
        
    ## TODO NOT DONE YET
    # suite.addTest(EnvironmentTests('test_node_grab_population_template_one_blob_case1'))
    # suite.addTest(EnvironmentTests('test_node_grab_population_template_one_blob_case2'))
    # suite.addTest(EnvironmentTests('test_node_grab_population_template_one_blob_case3'))
    # suite.addTest(EnvironmentTests('test_node_grab_population_template_three_blobs_case1'))
    # suite.addTest(EnvironmentTests('test_node_grab_population_template_three_blobs_case2'))
    # suite.addTest(EnvironmentTests('test_node_grab_population_template_three_blobs_case3'))
    ## END TODO NOT DONE YET

    
    #### Region tests
    # #### Graph tests
    #     ## consume time action
    #         ## converge population
    # suite.addTest(EnvironmentTests('test_graph_converge_population')) 
    # ###         ## return population home
    # suite.addTest(EnvironmentTests('test_graph_return_population_home')) 
    # ###         ## move population
    # suite.addTest(EnvironmentTests('test_graph_move_population_case1')) 
    # suite.addTest(EnvironmentTests('test_graph_move_population_case2')) 
    # suite.addTest(EnvironmentTests('test_graph_move_population_case3'))
    # suite.addTest(EnvironmentTests('test_graph_move_population_case4'))

    #TODO not implemented yet
        ## balance action list
    #suite.addTest(EnvironmentTests('test_graph_balance_list'))
        ## simplify action list
    #suite.addTest(EnvironmentTests('test_graph_simplify_list'))
    #TODO END not implemented yet

        ## merge blobs
    # suite.addTest(EnvironmentTests('test_graph_merge_blobs'))

    # missing test generate action list (mightnot be necessary)
    return suite       

if __name__ == "__main__":
    FixedRandom()
    runner = unittest.TextTestRunner()
    runner.run(suite())