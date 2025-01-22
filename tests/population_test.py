from typing import List, Set
from random_inst import FixedRandom

import pytest
from population import SampledCharacteristic

@pytest.fixture(scope="session", autouse=True)
def start_fixedrandom():
    """Initialize FixedRandom to ensure deterministic behavior in tests."""
    FixedRandom()  # Ensure FixedRandom is defined or imported properly.


class TestSampledCharacteristic():

     # Tests different combinations of keys as lists
    # Also tests combinations with repeated key entries. Multiple entries should not change behavior
    keys_as_list_scenarios = [
        [],
        ['value_1'], ['value_2'], ['value_3'], 
        ['value_1', 'value_2'], ['value_1', 'value_3'], ['value_2', 'value_3'], 
        ['value_1', 'value_2', 'value_3'],
        ['value_1', 'value_1'], 
        ['value_1', 'value_1', 'value_2'], 
        ['value_1', 'value_1', 'value_2', 'value_3'], 
        ['value_1', 'value_1', 'value_2', 'value_1', 'value_3']
        ]
    # Tests different combinations of keys as sets
    keys_as_set_scenarios = [
        (set()),
        {'value_1'}, {'value_2'}, {'value_3'}, 
        {'value_1', 'value_2'}, {'value_1', 'value_3'}, {'value_2', 'value_3'}, 
        {'value_1', 'value_2', 'value_3'}
        ]


    @pytest.fixture
    def default_char_a(self) -> SampledCharacteristic:
        characteristic = SampledCharacteristic('characteristic_A')
        characteristic.set_values_dict({'value_1': 30, 'value_2': 50, 'value_3': 20})
        return characteristic

    @pytest.fixture
    def default_char_b(self) -> SampledCharacteristic:
        characteristic = SampledCharacteristic('characteristic_B')
        characteristic.set_values_dict({'value_1': 60, 'value_2': 60, 'value_3': 60})
        return characteristic

    def test_get_population_size_no_key(self, default_char_a: SampledCharacteristic):
        """
        Test get_population_size with no key provided.
        """
        total_population = default_char_a.get_population_size()
        assert total_population == 100, "Total population size should be 100."

    def test_get_population_size_single_key(self, default_char_a: SampledCharacteristic):
        """
        Test get_population_size with a single key.
        """
        population_value_1 = default_char_a.get_population_size('value_1')
        assert population_value_1 == 30, "Population size for 'value_1' should be 30."

    def test_get_population_size_multiple_keys(self, default_char_a: SampledCharacteristic):
        """
        Test get_population_size with multiple keys.
        """
        population_values = default_char_a.get_population_size(['value_1', 'value_3'])
        assert population_values == 50, "Population size for 'value_1' and 'value_3' should be 50."

    def test_get_population_size_invalid_key(self, default_char_a: SampledCharacteristic):
        """
        Test get_population_size with an invalid key.
        """
        try:
            default_char_a.get_population_size(123) # type: ignore
        except ValueError as e:
            assert str(e) == "Invalid key type: <class 'int'>", "Exception message should match for invalid key type."

    def test_get_population_size_set_key(self, default_char_a: SampledCharacteristic):
        """
        Test get_population_size with a set of keys.
        """
        population_values = default_char_a.get_population_size({'value_1', 'value_2'})
        assert population_values == 80, "Population size for 'value_1' and 'value_2' should be 80."

    def test_set_values_rand(self):
        """
        Test SampledCharacteristic.set_values_rand functionality.

        Case 1: Population is distributed correctly among keys.
        Case 2: Population is zero.
        Case 3: Only one key.
        """
        # Case 1: Population is distributed correctly among keys
        characteristic = SampledCharacteristic('characteristic_A')
        characteristic.set_values_rand(['value_1', 'value_2', 'value_3'], 100)
        total_population = characteristic.get_population_size()
        assert total_population == 100, "Population was not distributed correctly among keys."
        assert all(value >= 0 for value in characteristic.categories.values()), "Population values should be non-negative."

        # Case 2: Population is zero
        characteristic.set_values_rand(['value_1', 'value_2', 'value_3'], 0)
        total_population = characteristic.get_population_size()
        assert total_population == 0, "Population should be zero when initialized with zero."
        assert all(value == 0 for value in characteristic.categories.values()), "All population values should be zero."

        # Case 3: Only one key
        characteristic.set_values_rand(['value_1'], 50)
        total_population = characteristic.get_population_size()
        assert total_population == 50, "Population was not distributed correctly for a single key."
        assert characteristic.get_population_size('value_1') == 50, "Population for the single key should be equal to the total population."

    def test_set_values_valid_input(self):
        """
        Test SampledCharacteristic.set_values with valid input.
        """
        characteristic = SampledCharacteristic('characteristic_A')
        keys = ['value_1', 'value_2', 'value_3']
        populations = [30, 50, 20]
        characteristic.set_values(keys, populations)
        assert characteristic.categories == {'value_1': 30, 'value_2': 50, 'value_3': 20}, \
            "The categories should match the input keys and populations."

    def test_set_values_empty_keys(self):
        """
        Test SampledCharacteristic.set_values with empty keys list.
        """
        characteristic = SampledCharacteristic('characteristic_A')
        keys = []
        populations = [30, 50, 20]
        try:
            characteristic.set_values(keys, populations)
        except ValueError as e:
            assert str(e) == "The 'keys' list must not be empty.", "Exception message should match for empty keys list."

    def test_set_values_mismatched_lengths(self):
        """
        Test SampledCharacteristic.set_values with mismatched lengths of keys and populations.
        """
        characteristic = SampledCharacteristic('characteristic_A')
        keys = ['value_1', 'value_2']
        populations = [30, 50, 20]
        try:
            characteristic.set_values(keys, populations)
        except ValueError as e:
            assert str(e) == "The lengths of 'keys' and 'populations' must match.", "Exception message should match for mismatched lengths."

    def test_set_values_zero_total_population(self):
        """
        Test SampledCharacteristic.set_values with total population zero.
        """
        characteristic = SampledCharacteristic('characteristic_A')
        keys = ['value_1', 'value_2', 'value_3']
        populations = [0, 0, 0]
        try:
            characteristic.set_values(keys, populations)
        except ValueError as e:
            assert str(e) == "The total population (sum of 'populations') must be greater than zero.", \
                "Exception message should match for zero total population."

    def test_set_values_negative_total_population(self):
        """
        Test SampledCharacteristic.set_values with negative total population.
        """
        characteristic = SampledCharacteristic('characteristic_A')
        keys = ['value_1', 'value_2', 'value_3']
        populations = [-15, 5, 5]
        try:
            characteristic.set_values(keys, populations)
        except ValueError as e:
            assert str(e) == "The total population (sum of 'populations') must be greater than zero.", \
                "Exception message should match for negative total population."

    def test_set_values_dict_valid_input(self):
        """
        Test SampledCharacteristic.set_values_dict with valid input.
        """
        characteristic = SampledCharacteristic('characteristic_A')
        data = {'value_1': 30, 'value_2': 50, 'value_3': 20}
        characteristic.set_values_dict(data)
        assert characteristic.categories == data, "The categories should match the input data."

    def test_set_values_dict_empty_data(self):
        """
        Test SampledCharacteristic.set_values_dict with empty data dictionary.
        """
        characteristic = SampledCharacteristic('characteristic_A')
        data = {}
        try:
            characteristic.set_values_dict(data)
        except ValueError as e:
            assert str(e) == "The 'data' dictionary must not be empty.", "Exception message should match for empty data dictionary."

    def test_set_values_dict_zero_total_population(self):
        """
        Test set_values_dict with total population zero.
        """
        characteristic = SampledCharacteristic('characteristic_A')
        data = {'value_1': 0, 'value_2': 0, 'value_3': 0}
        try:
            characteristic.set_values_dict(data)
        except ValueError as e:
            assert str(e) == "The total population (sum of 'data' values) must be greater than zero.", \
                "Exception message should match for zero total population."

    def test_set_values_dict_negative_total_population(self):
        """
        Test set_values_dict with negative total population.
        """
        characteristic = SampledCharacteristic('characteristic_A')
        data = {'value_1': -15, 'value_2': 5, 'value_3': 5}
        try:
            characteristic.set_values_dict(data)
        except ValueError as e:
            assert str(e) == "The total population (sum of 'data' values) must be zero or greater.", \
                "Exception message should match for negative total population."
            

    def test_merge_values_same_name(self):
        """
        Test SampledCharacteristic.merge_values functionality for characteristics with the same name.
        """
        aux_char1 = SampledCharacteristic('characteristic_A')
        aux_char1.set_values_rand(['char_A_value_1', 'char_A_value_2', 'char_A_value_3'], 60)

        aux_char2 = SampledCharacteristic('characteristic_A')
        aux_char2.set_values_rand(['char_A_value_1', 'char_A_value_2', 'char_A_value_3'], 30)

        initial_population1 = aux_char1.get_population_size()
        initial_population2 = aux_char2.get_population_size()

        aux_char1.merge_values(aux_char2)

        # Assert that populations were combined correctly
        assert aux_char1.get_population_size() == initial_population1 + initial_population2, \
            "Failed to merge characteristics with the same name correctly."

    def test_merge_values_different_names(self):
        """
        Test SampledCharacteristic.merge_values functionality for characteristics with different names.
        """
        aux_char1 = SampledCharacteristic('characteristic_A')
        aux_char1.set_values_rand(['char_A_value_1', 'char_A_value_2', 'char_A_value_3'], 60)

        aux_char2 = SampledCharacteristic('characteristic_B')
        aux_char2.set_values_rand(['char_B_value_1', 'char_B_value_2'], 60)

        initial_population1 = aux_char1.get_population_size()

        aux_char1.merge_values(aux_char2)

        # Assert that the merge was skipped and population remains unchanged
        assert aux_char1.get_population_size() == initial_population1, \
            "Incorrectly merged characteristics with different names."

    def test_extract_specific_key(self, default_char_a: SampledCharacteristic):
        """
        Test extract with a specific key provided.
        """
        extracted = default_char_a.extract(20, 'value_1')
        assert extracted.get_population_size() == 20, "Extracted population should be 20."
        assert extracted.categories['value_1'] == 20, "Extracted population for 'value_1' should be 20."
        assert default_char_a.get_population_size() == 80, "Remaining population should be 80."
        assert default_char_a.categories['value_1'] == 10, "Remaining population for 'value_1' should be 10."

    def test_extract_multiple_keys(self, default_char_a: SampledCharacteristic):
        """
        Test extract with multiple keys provided.
        """
        extracted = default_char_a.extract(40, ['value_1', 'value_2'])
        assert extracted.get_population_size() == 40, "Extracted population should be 40."
        assert extracted.categories['value_1'] + extracted.categories['value_2'] == 40, "Extracted population for 'value_1' and 'value_2' should be 40."
        assert default_char_a.get_population_size() == 60, "Remaining population should be 60."

    def test_extract_zero_quantity(self, default_char_a: SampledCharacteristic):
        """
        Test extract with zero quantity.
        """
        extracted = default_char_a.extract(0)
        assert extracted.get_population_size() == 0, "Extracted population should be 0."
        assert default_char_a.get_population_size() == 100, "Remaining population should be 100."

    def test_extract_quantity_exceeds_population(self, default_char_a: SampledCharacteristic):
        """
        Test extract with quantity exceeding total population.
        """
        extracted = default_char_a.extract(150)
        assert extracted.get_population_size() == 100, "Extracted population should be 100."
        assert default_char_a.get_population_size() == 0, "Remaining population should be 0."

    def test_extract_invalid_key_type(self, default_char_a: SampledCharacteristic):
        """
        Test extract with an invalid key type.
        """
        
        try:
            default_char_a.extract(10, 123)  # type: ignore
        except TypeError as e:
            assert str(e) == f"Selected keys {123} requested for a sampled characteristic are not a list {type(123)}. {default_char_a}", \
                "Exception message should match for invalid key type."
            
    def test_extract_without_key_less_population_than_available(self, default_char_b: SampledCharacteristic):
        """Test SampledCharacteristic.extract with no key when extracting less population than available."""

        # Extracting 100 people
        original_population_size = default_char_b.get_population_size()
        extracted_characteristic = default_char_b.extract(100)
        smaller_population_size = default_char_b.get_population_size()
        extracted_population_size = extracted_characteristic.get_population_size()

        # Comparing characteristics sizes
        assert original_population_size == (smaller_population_size + extracted_population_size), \
                         'Populations do not add up.'
        assert 100 == extracted_population_size, 'Extracted population is not the correct size.'
        assert smaller_population_size == (original_population_size - extracted_population_size), \
                         'Original population is not the correct size.'

    def test_extract_without_key_equal_population_as_available(self, default_char_b: SampledCharacteristic):
        """Test SampledCharacteristic.extract with no key when extracting exactly the population available."""

        # Extracting 180 people - the exact amount available
        original_population_size = default_char_b.get_population_size()
        extracted_characteristic = default_char_b.extract(180)
        smaller_population_size = default_char_b.get_population_size()
        extracted_population_size = extracted_characteristic.get_population_size()

        # Comparing characteristics sizes
        assert original_population_size == (smaller_population_size + extracted_population_size), \
                         'Populations do not add up.'
        assert original_population_size == extracted_population_size, 'Extracted population is not the total size.'
        assert smaller_population_size == 0, 'Original population is not zero.'

    def test_extract_without_key_more_population_than_available(self, default_char_b: SampledCharacteristic):
        """Test SampledCharacteristic.extract with no key when extracting more population than available."""

        # Extracting 300 people - more than available
        original_population_size = default_char_b.get_population_size()
        extracted_characteristic = default_char_b.extract(300)
        smaller_population_size = default_char_b.get_population_size()
        extracted_population_size = extracted_characteristic.get_population_size()

        # Comparing characteristic sizes
        assert original_population_size == (smaller_population_size + extracted_population_size), \
                         'Populations do not add up.'
        assert original_population_size == extracted_population_size, 'Extracted population is not the total size.'
        assert smaller_population_size == 0, 'Original population is not zero.'

    def test_extract_single_key_less_population_than_available(self, default_char_b: SampledCharacteristic):
        """Test SampledCharacteristic.extract when extracting less population than available for a specific str key."""

        original_population_size = default_char_b.get_population_size()
        original_category_count = default_char_b.get_population_size(key='value_1')
        extracted_characteristic = default_char_b.extract(30, selected_keys='value_1')
        smaller_population_size = default_char_b.get_population_size()
        smaller_category_count = default_char_b.get_population_size(key='value_1')
        extracted_population_size = extracted_characteristic.get_population_size()
        extracted_category_count = extracted_characteristic.get_population_size(key='value_1')

        # Comparing population sizes
        assert original_population_size == smaller_population_size + extracted_population_size, 'Populations do not add up.'
        assert extracted_population_size == 30, 'Extracted population is not the correct size.'
        assert smaller_population_size == original_population_size - extracted_population_size, 'Original population is not the correct size.'

        # Comparing count of 'value_1'
        assert original_category_count == smaller_category_count + extracted_category_count, 'Characteristic values do not add up.'
        assert extracted_category_count == 30, 'Extracted population is not the correct size.'
        assert smaller_category_count == original_category_count - extracted_category_count, 'Original category count is not the correct size.'

    def test_extract_single_key_equal_population_as_available(self, default_char_b: SampledCharacteristic):
        """Test SampledCharacteristic.extract when extracting exactly the population available for a specific key."""
        original_population_size = default_char_b.get_population_size()
        original_category_count = default_char_b.get_population_size(key='value_1')
        extracted_characteristic = default_char_b.extract(60, selected_keys='value_1')
        smaller_population_size = default_char_b.get_population_size()
        smaller_category_count = default_char_b.get_population_size(key='value_1')
        extracted_population_size = extracted_characteristic.get_population_size()
        extracted_category_count = extracted_characteristic.get_population_size(key='value_1')

        # Comparing population sizes
        assert original_population_size == smaller_population_size + extracted_population_size, 'Populations do not add up.'
        assert smaller_population_size == 120, 'Original population is not the correct size.'
        assert smaller_population_size == original_population_size - extracted_population_size, 'Original characteristic is not the correct size.'

        # Comparing count of 'value_1'
        assert original_category_count == smaller_category_count + extracted_category_count, 'Characteristic values do not add up.'
        assert extracted_category_count == 60, 'Extracted population is not the correct size.'
        assert smaller_category_count == original_category_count - extracted_category_count, 'Original category count is not the correct size.'

    def test_extract_single_key_more_population_than_available(self, default_char_b: SampledCharacteristic):
        """Test SampledCharacteristic.extract when extracting more population than available for a specific key."""

        original_population_size = default_char_b.get_population_size()
        original_category_count = default_char_b.get_population_size(key='value_1')
        extracted_characteristic = default_char_b.extract(120, selected_keys='value_1')
        smaller_population_size = default_char_b.get_population_size()
        smaller_category_count = default_char_b.get_population_size(key='value_1')
        extracted_population_size = extracted_characteristic.get_population_size()
        extracted_category_count = extracted_characteristic.get_population_size(key='value_1')

        # Comparing population sizes
        assert original_population_size == smaller_population_size + extracted_population_size, 'Populations do not add up.'
        assert smaller_population_size == 120, 'Original population is not the correct size.'
        assert smaller_population_size == original_population_size - extracted_population_size, 'Original characteristic is not the correct size.'

        # Comparing count of 'value_1'
        assert original_category_count == smaller_category_count + extracted_category_count, 'Characteristic values do not add up.'
        assert extracted_category_count == 60, 'Extracted population is not the correct size.'
        assert smaller_category_count == original_category_count - extracted_category_count, 'Original category count is not the correct size.'

    @pytest.mark.parametrize("keys_list", keys_as_list_scenarios)
    def test_extract_key_list_less_population_than_available(self, default_char_b: SampledCharacteristic, keys_list:List[str]):
        """Test SampledCharacteristic.extract when extracting less population than available matching keys (as list)"""
        available_population = len(set(keys_list)) * 60

        original_population_size = default_char_b.get_population_size()
        original_category_count = default_char_b.get_population_size(keys_list)
        extracted_characteristic = default_char_b.extract(available_population // 2, keys_list)
        smaller_population_size = default_char_b.get_population_size()
        smaller_category_count = default_char_b.get_population_size(keys_list)
        extracted_population_size = extracted_characteristic.get_population_size()
        extracted_category_count = extracted_characteristic.get_population_size(keys_list)

        # Comparing population sizes
        assert original_population_size == smaller_population_size + extracted_population_size, 'Populations do not add up.'
        assert available_population // 2 == extracted_population_size, 'Original population is not the correct size.'
        assert smaller_population_size == original_population_size - extracted_population_size, 'Original characteristic is not the correct size.'

        # Comparing expected count based on keys_list
        assert original_category_count == smaller_category_count + extracted_category_count, 'Characteristic values do not add up.'
        assert available_population // 2 == extracted_category_count, 'Extracted population is not the correct size.'
        assert smaller_category_count == original_category_count - extracted_category_count, 'Original category count is not the correct size.'

    @pytest.mark.parametrize("keys_list", keys_as_list_scenarios)
    def test_extract_key_list_equal_population_as_available(self, default_char_b: SampledCharacteristic, keys_list:List[str]):
        """Test SampledCharacteristic.extract when extracting equal population as available matching keys (as list)"""
        available_population = len(set(keys_list)) * 60

        original_population_size = default_char_b.get_population_size()
        original_category_count = default_char_b.get_population_size(keys_list)
        extracted_characteristic = default_char_b.extract(available_population, keys_list)
        smaller_population_size = default_char_b.get_population_size()
        smaller_category_count = default_char_b.get_population_size(keys_list)
        extracted_population_size = extracted_characteristic.get_population_size()
        extracted_category_count = extracted_characteristic.get_population_size(keys_list)

        # Comparing population sizes
        assert original_population_size == smaller_population_size + extracted_population_size, 'Populations do not add up.'
        assert smaller_population_size == 180 - available_population, 'Original population is not the correct size.'
        assert smaller_population_size == original_population_size - extracted_population_size, 'Original characteristic is not the correct size.'

        # Comparing expected count based on keys_list
        assert original_category_count == smaller_category_count + extracted_category_count, 'Characteristic values do not add up.'
        assert available_population == extracted_category_count, 'Extracted population is not the correct size.'
        assert smaller_category_count == original_category_count - extracted_category_count, 'Original category count is not the correct size.'

    @pytest.mark.parametrize("keys_list", keys_as_list_scenarios)
    def test_extract_key_list_more_population_than_available(self, default_char_b: SampledCharacteristic, keys_list:List[str]):
        """Test SampledCharacteristic.extract when extracting more population than available matching keys (as list)"""	
        available_population = len(set(keys_list)) * 60

        original_population_size = default_char_b.get_population_size()
        original_category_count = default_char_b.get_population_size(keys_list)
        extracted_characteristic = default_char_b.extract(available_population * 2, keys_list)
        smaller_population_size = default_char_b.get_population_size()
        smaller_category_count = default_char_b.get_population_size(keys_list)
        extracted_population_size = extracted_characteristic.get_population_size()
        extracted_category_count = extracted_characteristic.get_population_size(keys_list)

        # Comparing population sizes
        assert original_population_size == smaller_population_size + extracted_population_size, 'Populations do not add up.'
        assert smaller_population_size == 180 - available_population, 'Original population is not the correct size.'
        assert smaller_population_size == original_population_size - extracted_population_size, 'Original characteristic is not the correct size.'

        # Comparing expected count based on keys_list
        assert original_category_count == smaller_category_count + extracted_category_count, 'Characteristic values do not add up.'
        assert available_population == extracted_category_count, 'Extracted population is not the correct size.'
        assert smaller_category_count == original_category_count - extracted_category_count, 'Original category count is not the correct size.'

    @pytest.mark.parametrize("keys_set", keys_as_set_scenarios)
    def test_extract_key_set_less_population_than_available(self, default_char_b: SampledCharacteristic, keys_set:Set[str]):
        """Test SampledCharacteristic.extract when extracting less population than available matching keys (as set)"""
        available_population = len(set(keys_set)) * 60

        original_population_size = default_char_b.get_population_size()
        original_category_count = default_char_b.get_population_size(keys_set)
        extracted_characteristic = default_char_b.extract(available_population // 2, keys_set)
        smaller_population_size = default_char_b.get_population_size()
        smaller_category_count = default_char_b.get_population_size(keys_set)
        extracted_population_size = extracted_characteristic.get_population_size()
        extracted_category_count = extracted_characteristic.get_population_size(keys_set)

        # Comparing population sizes
        assert original_population_size == smaller_population_size + extracted_population_size, 'Populations do not add up.'
        assert available_population // 2 == extracted_population_size, 'Original population is not the correct size.'
        assert smaller_population_size == original_population_size - extracted_population_size, 'Original characteristic is not the correct size.'

        # Comparing expected count based on keys_set
        assert original_category_count == smaller_category_count + extracted_category_count, 'Characteristic values do not add up.'
        assert available_population // 2 == extracted_category_count, 'Extracted population is not the correct size.'
        assert smaller_category_count == original_category_count - extracted_category_count, 'Original category count is not the correct size.'

    @pytest.mark.parametrize("keys_set", keys_as_set_scenarios)
    def test_extract_key_set_equal_population_as_available(self, default_char_b: SampledCharacteristic, keys_set:Set[str]):
        """Test SampledCharacteristic.extract when extracting equal population as available matching keys (as set)"""
        available_population = len(set(keys_set)) * 60

        original_population_size = default_char_b.get_population_size()
        original_category_count = default_char_b.get_population_size(keys_set)
        extracted_characteristic = default_char_b.extract(available_population, keys_set)
        smaller_population_size = default_char_b.get_population_size()
        smaller_category_count = default_char_b.get_population_size(keys_set)
        extracted_population_size = extracted_characteristic.get_population_size()
        extracted_category_count = extracted_characteristic.get_population_size(keys_set)

        # Comparing population sizes
        assert original_population_size == smaller_population_size + extracted_population_size, 'Populations do not add up.'
        assert smaller_population_size == 180 - available_population, 'Original population is not the correct size.'
        assert smaller_population_size == original_population_size - extracted_population_size, 'Original characteristic is not the correct size.'

        # Comparing expected count based on keys_set
        assert original_category_count == smaller_category_count + extracted_category_count, 'Characteristic values do not add up.'
        assert available_population == extracted_category_count, 'Extracted population is not the correct size.'
        assert smaller_category_count == original_category_count - extracted_category_count, 'Original category count is not the correct size.'

    @pytest.mark.parametrize("keys_set", keys_as_set_scenarios)
    def test_extract_key_set_more_population_than_available(self, default_char_b: SampledCharacteristic, keys_set:Set[str]):
        """Test SampledCharacteristic.extract when extracting more population than available matching keys (as awr)"""	
        available_population = len(set(keys_set)) * 60

        original_population_size = default_char_b.get_population_size()
        original_category_count = default_char_b.get_population_size(keys_set)
        extracted_characteristic = default_char_b.extract(available_population * 2, keys_set)
        smaller_population_size = default_char_b.get_population_size()
        smaller_category_count = default_char_b.get_population_size(keys_set)
        extracted_population_size = extracted_characteristic.get_population_size()
        extracted_category_count = extracted_characteristic.get_population_size(keys_set)

        # Comparing population sizes
        assert original_population_size == smaller_population_size + extracted_population_size, 'Populations do not add up.'
        assert smaller_population_size == 180 - available_population, 'Original population is not the correct size.'
        assert smaller_population_size == original_population_size - extracted_population_size, 'Original characteristic is not the correct size.'

        # Comparing expected count based on keys_set
        assert original_category_count == smaller_category_count + extracted_category_count, 'Characteristic values do not add up.'
        assert available_population == extracted_category_count, 'Extracted population is not the correct size.'
        assert smaller_category_count == original_category_count - extracted_category_count, 'Original category count is not the correct size.'