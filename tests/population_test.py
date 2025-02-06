from typing import List, Set
from util.random_instance import FixedRandom

import pytest
from core.population import Blob, BlobFactory, BlobTemplate, CharacteristicsFactory, PopulationTemplate, SampledCharacteristic, SampledCharacteristicCollection

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

    def test_get_population_size_invalid_key_type(self, default_char_a: SampledCharacteristic):
        """
        Test get_population_size with an invalid key.
        """
        try:
            default_char_a.get_population_size(123) # type: ignore
        except ValueError as e:
            assert str(e) == "Invalid key type: <class 'int'>", "Exception message should match for invalid key type."

    def test_get_population_size_invalid_key_value(self, default_char_a: SampledCharacteristic):
        """
        Test get_population_size with an invalid key.
        """
        try:
            default_char_a.get_population_size('value_4') # type: ignore
        except ValueError as e:
            assert str(e) == f"Key 'value_4' not found in {default_char_a.name}.", "Exception message should match for invalid key value."

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


class TestSampledCharacteristicsCollection():

    @pytest.fixture
    def default_factory(self) -> CharacteristicsFactory:
        template = CharacteristicsFactory()
        template.add_sampled_characteristic('age', ['child', 'adult', 'ancient'])
        template.add_sampled_characteristic('economic_profile', ['unemployed', 'worker'])
        return template

    @pytest.fixture
    def default_collection(self, default_factory: CharacteristicsFactory) -> SampledCharacteristicCollection:
        collection = default_factory.generate_characteristic_collection_rand(100)
        return collection
    
    @pytest.fixture
    def default_profile(self) -> dict:
        profile = {
            'age': {'child': 30, 'adult': 50, 'ancient': 20} , 
            'economic_profile': {'unemployed': 30, 'worker': 70}
        }
        return profile

    @pytest.fixture
    def default_pop_template_single_key(self) -> PopulationTemplate:
        pop_template = PopulationTemplate()
        pop_template.set_sampled_property('age', ['adult'])
        pop_template.set_sampled_property('economic_profile', ['worker'])
        return pop_template

    @pytest.fixture
    def default_pop_template_key_list(self) -> PopulationTemplate:
        pop_template = PopulationTemplate()
        pop_template.set_sampled_property('age', ['adult', 'ancient'])	
        pop_template.set_sampled_property('economic_profile', ['unemployed', 'worker'])
        pop_template.set_sampled_property('empty_characteritic', [])
        return pop_template

    @pytest.fixture
    def default_collection_with_profile(self, default_factory: CharacteristicsFactory, default_profile:dict) -> SampledCharacteristicCollection:
        collection = default_factory.generate_characteristic_collection_with_profile(100, default_profile)
        return collection

    def test_get_mapping_of_property_values(self, default_collection: SampledCharacteristicCollection):
        mapping = default_collection.get_mapping_of_property_values()
        assert len(mapping) == len(default_collection.characteristics), "Mapping length should match number of characteristics."
        assert all(isinstance(values, list) for values in mapping), "Each mapping entry should be a list of values."

    def test_is_valid(self, default_collection: SampledCharacteristicCollection):
        assert default_collection.is_valid() == True, "Collection should be valid."
        default_collection.characteristics['age'].categories['child'] = -10
        assert default_collection.is_valid() == False, "Collection should be invalid due to negative category value."

    def test_set_values_rand(self, default_factory: CharacteristicsFactory):
        collection = default_factory.generate_characteristic_collection_rand(100)
        assert collection.factory == default_factory, "CharacteristicsFactory should be set correctly."
        assert 'age' in collection.characteristics, "Characteristic 'age' should be initialized."
        assert 'economic_profile' in collection.characteristics, "Characteristic 'economic_profile' should be initialized."
        assert collection.characteristics['age'].get_population_size() == 100, "Population for 'age' should be 100."
        assert collection.characteristics['economic_profile'].get_population_size() == 100, "Population for 'economic_profile' should be 100."
        assert collection.is_valid() == True, "Collection should be valid."
        assert collection.get_population_size() == 100, "Population should be set correctly."

    def test_set_values_profile(self, default_factory: CharacteristicsFactory):
        profile = {'age': {'child': 30, 'adult': 50}}
        collection = default_factory.generate_characteristic_collection_with_profile(100, profile)
        assert collection.factory == default_factory, "CharacteristicsFactory should be set correctly."
        assert 'age' in collection.characteristics, "Characteristic 'age' should be initialized."
        assert 'economic_profile' in collection.characteristics, "Characteristic 'economic_profile' should be initialized."
        assert collection.characteristics['age'].categories == {'child': 30, 'adult': 50, 'ancient': 20}, "Profiled values should be set correctly."
        assert collection.is_valid() == True, "Collection should be valid."
        assert collection.get_population_size() == 100, "Population should be set correctly."

    def test_merge_characteristic_collection(self, default_collection: SampledCharacteristicCollection, default_factory: CharacteristicsFactory):
        other_collection = default_factory.generate_characteristic_collection_rand(50)
        initial_population = default_collection.get_population_size()
        other_population = other_collection.get_population_size()
        default_collection.merge_characteristic_collection(other_collection)
        assert default_collection.get_population_size() == initial_population + other_population, "Merged population size should be correct."
        assert default_collection.is_valid() == True, "Merged collection should be valid."
        assert default_collection.characteristics['age'].get_population_size() == 150, "Merged 'age' population should be correct."
        assert default_collection.characteristics['economic_profile'].get_population_size() == 150, "Merged 'economic_profile' population should be correct."
        assert other_collection.get_population_size() == 50, "Other collection should maintain the same population. Removal of the other collection is responsability of the caller."

    def test_extract_without_template_single_key_less_population_than_available(self, default_collection: SampledCharacteristicCollection):
        extracted_collection = default_collection.extract(50)
        assert extracted_collection
        assert extracted_collection.get_population_size() == 50, "Extracted population should be 50."
        assert default_collection.get_population_size() == 50, "Remaining population should be 50."
        assert extracted_collection.is_valid() == True, "Extracted collection should be valid."
        assert default_collection.is_valid() == True, "Remaining collection should be valid."

    def test_extract_without_template_equal_population_as_available(self, default_collection: SampledCharacteristicCollection):
        extracted_collection = default_collection.extract(100)
        assert extracted_collection
        assert extracted_collection.get_population_size() == 100, "Extracted population should be 100."
        assert default_collection.get_population_size() == 0, "Remaining population should be 0. Removal of the other collection is responsability of the caller."
        assert extracted_collection.is_valid() == True, "Extracted collection should be valid."
        assert default_collection.is_valid() == True, "Remaining collection should be valid."
    
    def test_extract_without_template_more_population_than_available(self, default_collection: SampledCharacteristicCollection):
        extracted_collection = default_collection.extract(300)
        assert extracted_collection
        assert extracted_collection.get_population_size() == 100, "Extracted population should be 100."
        assert default_collection.get_population_size() == 0, "Remaining population should be 0. Removal of the other collection is responsability of the caller."
        assert extracted_collection.is_valid() == True, "Extracted collection should be valid."
        assert default_collection.is_valid() == True, "Remaining collection should be valid."

    def test_extract_with_template_single_key_less_population_than_available(self, default_collection_with_profile: SampledCharacteristicCollection, default_pop_template_single_key: PopulationTemplate):
        extracted_collection = default_collection_with_profile.extract(30, default_pop_template_single_key)
        assert extracted_collection
        assert extracted_collection.get_population_size() == 30, "Extracted population should be 30."
        assert default_collection_with_profile.get_population_size() == 70, "Remaining population should be \0."
        assert extracted_collection.is_valid() == True, "Extracted collection should be valid."
        assert default_collection_with_profile.is_valid() == True, "Remaining collection should be valid."
        assert extracted_collection.characteristics['age'].get_population_size() == 30, "Extracted 'age' population should be 30."
        assert extracted_collection.characteristics['economic_profile'].get_population_size() == 30, "Extracted 'economic_profile' population should be 30."
        assert default_collection_with_profile.characteristics['age'].categories['adult'] == 20, "Remaining 'age' population should be 20."
        assert extracted_collection.characteristics['age'].categories['adult'] == 30, "Extracted 'age' population should be 30."

    def test_extract_with_template_single_key_equal_population_as_available(self, default_collection_with_profile: SampledCharacteristicCollection, default_pop_template_single_key: PopulationTemplate):
        extracted_collection = default_collection_with_profile.extract(50, default_pop_template_single_key)
        assert extracted_collection
        assert extracted_collection.get_population_size() == 50, "Extracted population should be 50."
        assert default_collection_with_profile.get_population_size() == 50, "Remaining population should be 50."
        assert extracted_collection.is_valid() == True, "Extracted collection should be valid."
        assert default_collection_with_profile.is_valid() == True, "Remaining collection should be valid."
        assert extracted_collection.characteristics['age'].get_population_size() == 50, "Extracted 'age' population should be 30."
        assert extracted_collection.characteristics['economic_profile'].get_population_size() == 50, "Extracted 'economic_profile' population should be 30."
        assert default_collection_with_profile.characteristics['age'].categories['adult'] == 0, "Remaining 'age' population should be 20."
        assert default_collection_with_profile.characteristics['economic_profile'].categories['worker'] == 20, "Remaining 'economic_profile' population should be 20."
        assert extracted_collection.characteristics['age'].categories['adult'] == 50, "Extracted 'age' population should be 50."
        assert extracted_collection.characteristics['economic_profile'].categories['worker'] == 50, "Extracted 'economic_profile' population should be 50."

    def test_extract_with_template_single_key_more_population_than_available(self, default_collection_with_profile: SampledCharacteristicCollection, default_pop_template_single_key: PopulationTemplate):
        extracted_collection = default_collection_with_profile.extract(500, default_pop_template_single_key)
        assert extracted_collection
        assert extracted_collection.get_population_size() == 50, "Extracted population should be 50."
        assert default_collection_with_profile.get_population_size() == 50, "Remaining population should be 50."
        assert extracted_collection.is_valid() == True, "Extracted collection should be valid."
        assert default_collection_with_profile.is_valid() == True, "Remaining collection should be valid."
        assert extracted_collection.characteristics['age'].get_population_size() == 50, "Extracted 'age' population should be 30."
        assert extracted_collection.characteristics['economic_profile'].get_population_size() == 50, "Extracted 'economic_profile' population should be 30."
        assert default_collection_with_profile.characteristics['age'].categories['adult'] == 0, "Remaining 'age' population should be 20."
        assert default_collection_with_profile.characteristics['economic_profile'].categories['worker'] == 20, "Remaining 'economic_profile' population should be 20."
        assert extracted_collection.characteristics['age'].categories['adult'] == 50, "Extracted 'age' population should be 50."
        assert extracted_collection.characteristics['economic_profile'].categories['worker'] == 50, "Extracted 'economic_profile' population should be 50."

    def test_extract_with_template_key_list_less_population_than_available(self, default_collection_with_profile: SampledCharacteristicCollection, default_pop_template_key_list: PopulationTemplate):
        extracted_collection = default_collection_with_profile.extract(30, default_pop_template_key_list)
        assert extracted_collection
        assert extracted_collection.get_population_size() == 30, "Extracted population should be 30."
        assert default_collection_with_profile.get_population_size() == 70, "Remaining population should be 70."
        assert extracted_collection.is_valid() == True, "Extracted collection should be valid."
        assert default_collection_with_profile.is_valid() == True, "Remaining collection should be valid."
        assert extracted_collection.characteristics['age'].get_population_size() == 30, "Extracted 'age' population should be 30."
        assert extracted_collection.characteristics['economic_profile'].get_population_size() == 30, "Extracted 'economic_profile' population should be 30."
        assert extracted_collection.characteristics['age'].categories['adult'] + extracted_collection.characteristics['age'].categories['ancient'] == 30, "Extracted 'age' population should be 30."
        assert extracted_collection.characteristics['age'].categories['child'] == 0, "Extracted 'age' population should be 0."
        assert default_collection_with_profile.characteristics['age'].categories['adult'] + default_collection_with_profile.characteristics['age'].categories['ancient'] == 40, "Remaining 'age' population should be 40."
        assert default_collection_with_profile.characteristics['age'].categories['child'] == 30, "Remaining 'age' population should be 30."

    def test_extract_with_template_key_list_equal_population_as_available(self, default_collection_with_profile: SampledCharacteristicCollection, default_pop_template_key_list: PopulationTemplate):
        extracted_collection = default_collection_with_profile.extract(70, default_pop_template_key_list)
        assert extracted_collection
        assert extracted_collection.get_population_size() == 70, "Extracted population should be 70."
        assert default_collection_with_profile.get_population_size() == 30, "Remaining population should be 30."
        assert extracted_collection.is_valid() == True, "Extracted collection should be valid."
        assert default_collection_with_profile.is_valid() == True, "Remaining collection should be valid."
        assert extracted_collection.characteristics['age'].get_population_size() == 70, "Extracted 'age' population should be 70."
        assert extracted_collection.characteristics['economic_profile'].get_population_size() == 70, "Extracted 'economic_profile' population should be 70."
        assert extracted_collection.characteristics['age'].categories['adult'] + extracted_collection.characteristics['age'].categories['ancient'] == 70, "Extracted 'age' population should be 70."
        assert extracted_collection.characteristics['age'].categories['child'] == 0, "Extracted 'age' population should be 0."
        assert default_collection_with_profile.characteristics['age'].categories['adult'] + default_collection_with_profile.characteristics['age'].categories['ancient'] == 0, "Remaining 'age' population should be 0."
        assert default_collection_with_profile.characteristics['age'].categories['child'] == 30, "Remaining 'age' population should be 30."

    def test_extract_with_template_key_list_more_population_than_available(self, default_collection_with_profile: SampledCharacteristicCollection, default_pop_template_key_list: PopulationTemplate):
        extracted_collection = default_collection_with_profile.extract(300, default_pop_template_key_list)
        assert extracted_collection
        assert extracted_collection.get_population_size() == 70, "Extracted population should be 70."
        assert default_collection_with_profile.get_population_size() == 30, "Remaining population should be 30."
        assert extracted_collection.is_valid() == True, "Extracted collection should be valid."
        assert default_collection_with_profile.is_valid() == True, "Remaining collection should be valid."
        assert extracted_collection.characteristics['age'].get_population_size() == 70, "Extracted 'age' population should be 70."
        assert extracted_collection.characteristics['economic_profile'].get_population_size() == 70, "Extracted 'economic_profile' population should be 70."
        assert extracted_collection.characteristics['age'].categories['adult'] + extracted_collection.characteristics['age'].categories['ancient'] == 70, "Extracted 'age' population should be 70."
        assert extracted_collection.characteristics['age'].categories['child'] == 0, "Extracted 'age' population should be 0."
        assert default_collection_with_profile.characteristics['age'].categories['adult'] + default_collection_with_profile.characteristics['age'].categories['ancient'] == 0, "Remaining 'age' population should be 0."
        assert default_collection_with_profile.characteristics['age'].categories['child'] == 30, "Remaining 'age' population should be 30."

class TestPopTemplate:

    @pytest.fixture
    def default_template(self) -> PopulationTemplate:
        """Fixture to provide a default PopTemplate instance."""
        return PopulationTemplate()
    
    def test_default_initialization(self, default_template: PopulationTemplate):
        assert default_template.blob_id is None, "Blob ID should be None."
        assert default_template.mother_blob_id is None, "Mother Blob ID should be None."
        assert default_template.sampled_characteristics == {}, "Sampled characteristics should be an empty dictionary."
        assert default_template.traceable_characteristics == {}, "Traceable characteristics should be an empty dictionary."
        assert default_template.empty is True, "Template should be empty."

    def test_initialization_with_characteristics(self):
        sampled = {'age': ['child', 'adult']}
        traceable = {'location': 'city'}
        template = PopulationTemplate(sampled, traceable)
        assert template.sampled_characteristics == sampled, "Sampled characteristics should be set correctly."
        assert template.traceable_characteristics == traceable, "Traceable characteristics should be set correctly."
        assert template.empty is False, "Template should not be empty."

    def test_set_mother_blob_id_valid(self, default_template: PopulationTemplate):
        default_template.set_mother_blob_id(123)
        assert default_template.mother_blob_id == 123, "Mother Blob ID should be set correctly."

    def test_set_mother_blob_id_invalid(self, default_template: PopulationTemplate):
        with pytest.raises(ValueError, match=f"Mother blob id must be a positive integer, is {type('invalid')}"):
            default_template.set_mother_blob_id("invalid") # type: ignore

    def test_set_sampled_property_valid(self, default_template: PopulationTemplate):
        default_template.set_sampled_property('age', ['child', 'adult'])
        assert default_template.sampled_characteristics == {'age': ['child', 'adult']}
        assert default_template.empty is False

    def test_set_sampled_property_invalid_key(self, default_template: PopulationTemplate):
        with pytest.raises(ValueError):
            default_template.set_sampled_property(123, ['child', 'adult']) # type: ignore

    def test_set_sampled_property_invalid_value(self, default_template: PopulationTemplate):
        with pytest.raises(ValueError):
            default_template.set_sampled_property('age', 'invalid') # type: ignore

    def test_set_traceable_property_valid(self, default_template: PopulationTemplate):
        default_template.set_traceable_property('location', 'city')
        assert default_template.traceable_characteristics == {'location': 'city'}
        assert default_template.empty is False

    def test_set_traceable_property_invalid_key(self, default_template: PopulationTemplate):
        with pytest.raises(ValueError):
            default_template.set_traceable_property(123, 'city') # type: ignore

    def test_set_sampled_properties(self, default_template: PopulationTemplate):
        properties = {'age': ['child', 'adult'], 'gender': ['male', 'female']}
        default_template.set_sampled_properties(properties)
        assert default_template.sampled_characteristics == properties
        assert default_template.empty is False

    def test_set_traceable_properties(self, default_template: PopulationTemplate):
        properties = {'location': 'city', 'status': 'active'}
        default_template.set_traceable_properties(properties)
        assert default_template.traceable_characteristics == properties
        assert default_template.empty is False

    def test_is_empty(self, default_template: PopulationTemplate):
        assert default_template.is_empty() is True
        default_template.set_sampled_property('age', ['child'])
        assert default_template.is_empty() is False

    def test_has_traceable_properties(self, default_template: PopulationTemplate):
        assert default_template.has_traceable_characteristics() is False
        default_template.set_traceable_property('location', 'city')
        assert default_template.has_traceable_characteristics() is True

    def test_has_sampled_properties(self, default_template: PopulationTemplate):
        assert default_template.has_sampled_characteristics() is False
        default_template.set_sampled_property('age', ['child'])
        assert default_template.has_sampled_characteristics() is True

    def test_compare(self):
        template1 = PopulationTemplate({'age': ['child']}, {'location': 'city'})
        template2 = PopulationTemplate({'age': ['child']}, {'location': 'city'})
        template3 = PopulationTemplate({'age': ['adult']}, {'location': 'village'})
        assert template1.compare(template2) is True, "Templates with the same characteristics should be equal."
        assert template1.compare(template3) is False, "Templates with different characteristics should not be equal."
        assert template2.compare(template3) is False, "Templates with different characteristics should not be equal."

    def test_str(self):
        template = PopulationTemplate({'age': ['child']}, {'location': 'city'})
        expected_str = '{"blob_id" : "", "mother_blob_id" : "", "pairs"  : {\'age\': [\'child\']}, "traceable_prop"  : {\'location\': \'city\'}}'
        assert str(template) == expected_str, "String representation should match expected."

    def test_repr(self):
        template = PopulationTemplate({'age': ['child']}, {'location': 'city'})
        expected_repr = '{"blob_id" : "", "mother_blob_id" : "", "pairs"  : {\'age\': [\'child\']}, "traceable_prop"  : {\'location\': \'city\'}}'
        assert repr(template) == expected_repr, "Repr representation should match expected."

class TestCharacteristicsFactory():

    @pytest.fixture
    def default_characteristic_template(self) -> CharacteristicsFactory:
        char_template = CharacteristicsFactory()
        char_template.add_sampled_characteristic('age', ['child', 'adult', 'ancient'])
        return char_template

    def test_initialization(self):
        """Test that the template initializes with empty characteristics."""
        template = CharacteristicsFactory()
        assert template.sampled_characteristics == {}, "Sampled characteristics should be initialized as an empty dictionary."
        assert template.traceable_characteristics == {}, "Traceable characteristics should be initialized as an empty dictionary."

    def test_add_sampled_characteristic(self):
        """Test adding sampled characteristics and removing duplicates."""
        template = CharacteristicsFactory()
        template.add_sampled_characteristic('age', ['child', 'adult', 'ancient', 'adult'])
        assert template.sampled_characteristics == {'age': ['child', 'adult', 'ancient']}, "Sampled characteristics should be added and duplicates removed."

    def test_add_traceable_characteristic(self):
        """Test adding traceable characteristics."""
        template = CharacteristicsFactory()
        template.add_traceable_characteristic('vaccine_level', 0)
        assert template.traceable_characteristics == {'vaccine_level': 0}, "Traceable characteristics should be added correctly."

    def test_validate_population(self, default_characteristic_template: CharacteristicsFactory):
        """Test population validation based on characteristics and population size."""
        assert default_characteristic_template._validate_population(100) == True, "Population should be valid when characteristics are defined and population is greater than 0."
        assert default_characteristic_template._validate_population(0) == False, "Population should be invalid when population is 0."
        template = CharacteristicsFactory()
        assert template._validate_population(100) == False, "Population should be invalid when no characteristics are defined."

    def test_create_characteristic_collection(self, default_characteristic_template: CharacteristicsFactory):
        """Test creating a characteristic collection with a valid population."""
        generated_collection = default_characteristic_template._create_characteristic_collection(100)
        assert isinstance(generated_collection, SampledCharacteristicCollection), "Should create a SampledCharacteristicCollection instance."
        assert generated_collection.population == 100, "Population should be set correctly in the collection."
        assert generated_collection.is_valid() == True, "Generated SampledCharacteristicCollection should be valid."

    def test_generate_characteristic_collection_rand_valid_population(self, default_characteristic_template: CharacteristicsFactory):
        """Test generating a characteristic collection with a valid population."""
        generated_collection = default_characteristic_template.generate_characteristic_collection_rand(100)
        assert isinstance(generated_collection, SampledCharacteristicCollection), "Should generate a SampledCharacteristicCollection instance."
        assert generated_collection.population == 100, "Population should be set correctly in the collection."

    def test_generate_characteristic_collection_rand_invalid_population(self, default_characteristic_template: CharacteristicsFactory):
        """Test generating a characteristic collection with an invalid population."""
        with pytest.raises(ValueError):
            default_characteristic_template.generate_characteristic_collection_rand(0)
        empty_template = CharacteristicsFactory()
        with pytest.raises(ValueError):
            empty_template.generate_characteristic_collection_rand(100)

    def test_generate_characteristic_collection_empty_valid(self, default_characteristic_template: CharacteristicsFactory):
        """Test generating an empty characteristic collection with valid characteristics."""
        generated_collection = default_characteristic_template.generate_characteristic_collection_empty()
        assert isinstance(generated_collection, SampledCharacteristicCollection), "Should generate an empty SampledCharacteristicCollection instance."
        assert generated_collection.population == 0, "Population should be set to 0 in the collection."
        template = CharacteristicsFactory()
        with pytest.raises(ValueError, match="No sampled characteristics defined."):
            template.generate_characteristic_collection_empty()

    def test_generate_characteristic_collection_empty_invalid(self):
        """Test generating an empty characteristic collection with no characteristics defined."""
        template = CharacteristicsFactory()
        with pytest.raises(ValueError, match="No sampled characteristics defined."):
            template.generate_characteristic_collection_empty()

    def test_generate_characteristic_collection_with_profile_valid(self, default_characteristic_template: CharacteristicsFactory):
        """Test generating a characteristic collection with a valid profile."""
        profile = {'age': {'child': 30, 'adult': 50}}
        generated_collection = default_characteristic_template.generate_characteristic_collection_with_profile(100, profile)
        assert isinstance(generated_collection, SampledCharacteristicCollection), "Should generate a SampledCharacteristicCollection instance with profile."
        assert generated_collection.population == 100, "Population should be set correctly in the collection."

    def test_generate_characteristic_collection_with_profile_invalid(self, default_characteristic_template: CharacteristicsFactory):
        """Test generating a characteristic collection with an invalid profile."""
        profile = {'age': {'child': 30, 'adult': 50}}
        with pytest.raises(ValueError):
            default_characteristic_template.generate_characteristic_collection_with_profile(0, profile)

class TestBlob:

    @pytest.fixture
    def blob_factory(self) -> BlobFactory:
        characteristics_factory = CharacteristicsFactory()
        characteristics_factory.add_sampled_characteristic('age', ['child', 'adult', 'ancient'])
        characteristics_factory.add_sampled_characteristic('economic_profile', ['unemployed', 'worker'])
        characteristics_factory.add_traceable_characteristic('vaccine_level', 0)
        characteristics_factory.add_traceable_characteristic('sir_state', 'susceptible')
        return BlobFactory(characteristics_factory)

    @pytest.fixture
    def default_blob(self, blob_factory: BlobFactory) -> Blob:
        return blob_factory.generate_blob_rand(0, 0, 100)

    def test_set_traceable_characteristic(self, default_blob: Blob):
        default_blob.set_traceable_characteristic('vaccine_level', 1)
        assert default_blob.get_traceable_characteristic('vaccine_level') == 1

    def test_get_traceable_characteristic(self, default_blob: Blob):
        assert default_blob.get_traceable_characteristic('vaccine_level') == 0

    def test_get_traceable_characteristics(self, default_blob: Blob):
        assert default_blob.get_traceable_characteristics() == {'vaccine_level': 0, 'sir_state': 'susceptible'}

    def test_get_population_size_no_template(self, default_blob: Blob):
        assert default_blob.get_population_size() == 100

    def test_get_population_size_with_template_matching_all_sampled_characteristics(self, default_blob: Blob):
        template = PopulationTemplate(sampled_characteristics={'age': ['child', 'adult', 'ancient']})
        assert default_blob.get_population_size(template) == 100

    def test_get_population_size_with_template_matching_separated_sampled_characteristics(self, default_blob: Blob):
        template1 = PopulationTemplate(sampled_characteristics={'age': ['child']})
        template2 = PopulationTemplate(sampled_characteristics={'age': ['adult']})
        template3 = PopulationTemplate(sampled_characteristics={'age': ['ancient']})
        population1 = default_blob.get_population_size(template1)
        population2 = default_blob.get_population_size(template2)
        population3 = default_blob.get_population_size(template3)
        assert population1 >= 0 <= 100
        assert population2 >= 0 <= 100
        assert population3 >= 0 <= 100
        assert population1 + population2 + population3 == 100

    def test_get_population_size_with_template_matching_traceable_characteristics(self, default_blob: Blob):
        template = PopulationTemplate(traceable_characteristics={'vaccine_level': 0})
        assert default_blob.get_population_size(template) == 100

    def test_get_population_size_with_template_not_matching_traceable_characteristics(self, default_blob: Blob):
        template = PopulationTemplate(traceable_characteristics={'vaccine_level': 1})
        assert default_blob.get_population_size(template) == 0

    def test_compare_traceable_characteristics_no_traceable(self, default_blob: Blob):
        template = PopulationTemplate()
        assert default_blob._compare_traceable_characteristics_to_population_template(template)

    def test_compare_traceable_characteristics_to_population_template_matching(self, default_blob: Blob):
        template = PopulationTemplate(traceable_characteristics={'vaccine_level': 0})
        assert default_blob._compare_traceable_characteristics_to_population_template(template) is True

    def test_compare_traceable_characteristics_to_population_template_non_matching(self, default_blob: Blob):
        template = PopulationTemplate(traceable_characteristics={'vaccine_level': 1})
        assert default_blob._compare_traceable_characteristics_to_population_template(template) is False

    def test_merge_blob_matching_traceable(self, default_blob: Blob, blob_factory: BlobFactory):
        other_blob = blob_factory.generate_blob_rand(0, 0, 50)
        default_blob.merge_blob(other_blob)
        assert default_blob.get_population_size() == 150, "Merged blob should have a population size of 150."
        assert other_blob.get_population_size() == 50, "Merged blob should not be modified."
        assert default_blob.sampled_characteristics.is_valid() == True, "Merged blob should have valid sampled characteristics."
        assert other_blob.sampled_characteristics.is_valid() == True, "Other blob should be valid."

    def test_merge_blob_non_matching_traceable(self, default_blob: Blob, blob_factory: BlobFactory):
        other_blob = blob_factory.generate_blob_rand(0, 0, 50)
        other_blob.set_traceable_characteristic('vaccine_level', 1)
        default_blob.merge_blob(other_blob)
        assert default_blob.get_population_size() == 100, "Merged blob should have a population size of 100."
        assert other_blob.get_population_size() == 50, "Other blob should not be modified."
        assert default_blob.sampled_characteristics.is_valid() == True, "Merged blob should have valid sampled characteristics."
        assert other_blob.sampled_characteristics.is_valid() == True, "Other blob should be valid."

    def test_split_blob_no_template(self, default_blob: Blob):
        new_blob = default_blob._split_blob(50)
        assert new_blob
        assert new_blob.sampled_characteristics.is_valid() == True
        assert new_blob.get_population_size() == 50
        assert default_blob.get_population_size() == 50
        assert default_blob.sampled_characteristics.is_valid() == True, "Original blob should have valid sampled characteristics."
        assert new_blob.sampled_characteristics.is_valid() == True, "New blob should be valid."

    def test_split_blob_matching_template(self, default_blob: Blob):
        template = PopulationTemplate({'age': ['child', 'adult', 'ancient']})
        new_blob = default_blob._split_blob(50, template)
        assert new_blob
        assert new_blob.sampled_characteristics.is_valid() == True
        assert new_blob.get_population_size() == 50
        assert default_blob.get_population_size() == 50
        assert default_blob.sampled_characteristics.is_valid() == True, "Original blob should have valid sampled characteristics."
        assert new_blob.sampled_characteristics.is_valid() == True, "New blob should be valid."

    def test_split_blob_non_matching_template(self, default_blob: Blob):
        template = PopulationTemplate({'age': ['nonexistent']})
        try:
           default_blob._split_blob(50, template)
        except ValueError as e:
            assert str(e) == f"Key '['nonexistent']' not found in age.", "Exception message should match for invalid key value."

    def test_split_and_change_blob_traceable_characteristic(self, default_blob: Blob):
        new_blob = default_blob.split_and_change_blob_traceable_characteristic('vaccine_level', 1, 50)
        assert new_blob
        assert new_blob.get_traceable_characteristic('vaccine_level') == 1
        assert new_blob.get_population_size() == 50
        assert default_blob.get_population_size() == 50
        assert default_blob.sampled_characteristics.is_valid() == True, "Original blob should have valid sampled characteristics."
        assert new_blob.sampled_characteristics.is_valid() == True, "New blob should be valid."

    def test_grab_population_no_template_less_population_than_available(self, default_blob: Blob):
        new_blob = default_blob.grab_population(50)
        assert new_blob
        assert new_blob.get_population_size() == 50
        assert default_blob.get_population_size() == 50
        assert default_blob.sampled_characteristics.is_valid() == True, "Original blob should have valid sampled characteristics."
        assert new_blob.sampled_characteristics.is_valid() == True, "New blob should be valid."

    def test_grab_population_no_template_equal_population_as_available(self, default_blob: Blob):
        new_blob = default_blob.grab_population(100)
        assert new_blob 
        assert default_blob == new_blob
        assert default_blob.__dict__ == new_blob.__dict__, "Original and new blob should be the same."
        assert default_blob.get_population_size() == 100
        assert default_blob.sampled_characteristics.is_valid() == True, "Both blobs should be valid."

    def test_grab_population_no_template_more_population_than_available(self, default_blob: Blob):
        new_blob = default_blob.grab_population(200)
        assert new_blob 
        assert default_blob == new_blob
        assert default_blob.__dict__ == new_blob.__dict__, "Original and new blob should be the same."
        assert default_blob.get_population_size() == 100
        assert default_blob.sampled_characteristics.is_valid() == True, "Both blobs should be valid."

    def test_grab_population_matching_template(self, default_blob: Blob):
        template = PopulationTemplate({'age': ['child', 'adult', 'ancient']})
        new_blob = default_blob.grab_population(50, template)
        assert new_blob
        assert new_blob.get_population_size() == 50
        assert default_blob.get_population_size() == 50
        assert default_blob.sampled_characteristics.is_valid() == True, "Original blob should have valid sampled characteristics."
        assert new_blob.sampled_characteristics.is_valid() == True, "New blob should be valid."

    def test_grab_population_not_matching_sampled_characteristic(self, default_blob: Blob):
        template = PopulationTemplate({'age': ['nonexistent']})
        try:
           default_blob.grab_population(50, template)
        except ValueError as e:
            assert str(e) == f"Key '['nonexistent']' not found in age.", "Exception message should match for invalid key value."

    def test_grab_population_not_matching_traceable_characteristic(self, default_blob: Blob):
        template = PopulationTemplate(traceable_characteristics={'vaccine_level': 1})
        new_blob = default_blob.grab_population(50, template)
        assert new_blob is None
        assert default_blob.get_population_size() == 100
        assert default_blob.sampled_characteristics.is_valid() == True, "Original blob should have valid sampled characteristics."

    def test_grab_population_unbalanced_less_population_than_available(self, blob_factory: BlobFactory):
        profile = {'age': {'child': 100}}
        population_template = PopulationTemplate({'age': ['child']})
        blob1 = blob_factory.generate_blob_with_profile(0, 0, 100, profile)
        blob2 = blob1.grab_population(50)
        assert blob2
        assert blob1.get_population_size() == 50
        assert blob2.get_population_size() == 50
        assert blob1.sampled_characteristics.is_valid() == True, "Original blob should have valid sampled characteristics."
        assert blob2.sampled_characteristics.is_valid() == True, "New blob should be valid."
        assert blob1.get_population_size(population_template) == 50, "Original blob should have 50 children."
        assert blob2.get_population_size(population_template) == 50, "New blob should have 50 children."

    def test_grab_population_unbalanced_equal_population_as_available(self, blob_factory: BlobFactory):
        profile = {'age': {'child': 100}}
        population_template = PopulationTemplate({'age': ['child']})
        blob1 = blob_factory.generate_blob_with_profile(0, 0, 100, profile)
        blob2 = blob1.grab_population(100)
        assert blob2
        assert blob1 == blob2
        assert blob1.__dict__ == blob2.__dict__, "Original and new blob should be the same."
        assert blob1.get_population_size() == 100
        assert blob1.sampled_characteristics.is_valid() == True, "Both blobs should be valid."
        assert blob1.get_population_size(population_template) == 100, "Both blobs should have 100 children."

    def test_grab_population_unbalanced_more_population_than_available(self, blob_factory: BlobFactory):
        profile = {'age': {'child': 100}}
        population_template = PopulationTemplate({'age': ['child']})
        blob1 = blob_factory.generate_blob_with_profile(0, 0, 100, profile)
        blob2 = blob1.grab_population(200)
        assert blob2
        assert blob1 == blob2
        assert blob1.__dict__ == blob2.__dict__, "Original and new blob should be the same."
        assert blob1.get_population_size() == 100
        assert blob1.sampled_characteristics.is_valid() == True, "Both blobs should be valid."
        assert blob1.get_population_size(population_template) == 100, "Both blobs should have 100 children."

    def test_grab_population_balanced_less_population_than_available(self, blob_factory: BlobFactory):
        profile = {'age': {'child': 50, 'adult': 50}}
        population_template = PopulationTemplate({'age': ['child', 'adult']})
        blob1 = blob_factory.generate_blob_with_profile(0, 0, 100, profile)
        blob2 = blob1.grab_population(50)
        assert blob2
        assert blob1.get_population_size() == 50
        assert blob2.get_population_size() == 50
        assert blob1.sampled_characteristics.is_valid() == True, "Original blob should have valid sampled characteristics."
        assert blob2.sampled_characteristics.is_valid() == True, "New blob should be valid."
        assert blob1.get_population_size(population_template) == 50, "Original blob should have 50 children and adults."
        assert blob2.get_population_size(population_template) == 50, "New blob should have 50 children and adults."

    def test_grab_population_balanced_equal_population_as_available(self, blob_factory: BlobFactory):
        profile = {'age': {'child': 50, 'adult': 50}}
        population_template = PopulationTemplate({'age': ['child', 'adult']})
        blob1 = blob_factory.generate_blob_with_profile(0, 0, 100, profile)
        blob2 = blob1.grab_population(100)
        assert blob2
        assert blob1 == blob2
        assert blob1.__dict__ == blob2.__dict__, "Original and new blob should be the same."
        assert blob1.get_population_size() == 100
        assert blob1.sampled_characteristics.is_valid() == True, "Both blobs should be valid."
        assert blob1.get_population_size(population_template) == 100, "Both blobs should have 100 children and adults."

    def test_grab_population_balanced_more_population_than_available(self, blob_factory: BlobFactory):
        profile = {'age': {'child': 50, 'adult': 50}}
        population_template = PopulationTemplate({'age': ['child', 'adult']})
        blob1 = blob_factory.generate_blob_with_profile(0, 0, 100, profile)
        blob2 = blob1.grab_population(100)
        assert blob2
        assert blob1 == blob2
        assert blob1.__dict__ == blob2.__dict__, "Original and new blob should be the same."
        assert blob1.get_population_size() == 100
        assert blob1.sampled_characteristics.is_valid() == True, "Both blobs should be valid."
        assert blob1.get_population_size(population_template) == 100, "Both blobs should have 100 children and adults."


class TestBlobTemplate:

    def test_initialization(self):
        population = 100
        traceable_characteristics = {'vaccine_level': 1, 'sir_state': 'susceptible'}
        sampled_characteristics = {
            'age': {'child': 20, 'adult': 60, 'elder': 20},
            'economic_profile': {'unemployed': 10, 'worker': 90}
        }
        blob_template = BlobTemplate(population, traceable_characteristics, sampled_characteristics)

        assert blob_template.population == population, "Population should be initialized correctly."
        assert blob_template.traceable_characteristics == traceable_characteristics, "Traceable characteristics should be initialized correctly."
        assert blob_template.sampled_characteristics == sampled_characteristics, "Sampled characteristics should be initialized correctly."

    def test_empty_traceable_characteristics(self):
        population = 100
        traceable_characteristics = {}
        sampled_characteristics = {
            'age': {'child': 20, 'adult': 60, 'elder': 20},
            'economic_profile': {'unemployed': 10, 'worker': 90}
        }
        blob_template = BlobTemplate(population, traceable_characteristics, sampled_characteristics)

        assert blob_template.population == population, "Population should be initialized correctly."
        assert blob_template.traceable_characteristics == traceable_characteristics, "Traceable characteristics should be initialized correctly."
        assert blob_template.sampled_characteristics == sampled_characteristics, "Sampled characteristics should be initialized correctly."

    def test_empty_sampled_characteristics(self):
        population = 100
        traceable_characteristics = {'vaccine_level': 1, 'sir_state': 'susceptible'}
        sampled_characteristics = {}
        blob_template = BlobTemplate(population, traceable_characteristics, sampled_characteristics)

        assert blob_template.population == population, "Population should be initialized correctly."
        assert blob_template.traceable_characteristics == traceable_characteristics, "Traceable characteristics should be initialized correctly."
        assert blob_template.sampled_characteristics == sampled_characteristics, "Sampled characteristics should be initialized correctly."

    def test_empty_characteristics(self):
        population = 100
        traceable_characteristics = {}
        sampled_characteristics = {}
        blob_template = BlobTemplate(population, traceable_characteristics, sampled_characteristics)

        assert blob_template.population == population, "Population should be initialized correctly."
        assert blob_template.traceable_characteristics == traceable_characteristics, "Traceable characteristics should be initialized correctly."
        assert blob_template.sampled_characteristics == sampled_characteristics, "Sampled characteristics should be initialized correctly."
        
class TestBlobFactory:

    @pytest.fixture
    def characteristics_factory(self) -> CharacteristicsFactory:
        factory = CharacteristicsFactory()
        factory.add_sampled_characteristic('age', ['child', 'adult', 'ancient'])
        factory.add_sampled_characteristic('economic_profile', ['unemployed', 'worker'])
        factory.add_traceable_characteristic('vaccine_level', 0)
        factory.add_traceable_characteristic('sir_state', 'susceptible')
        return factory

    @pytest.fixture
    def blob_factory(self, characteristics_factory: CharacteristicsFactory) -> BlobFactory:
        return BlobFactory(characteristics_factory)
    
    @pytest.fixture
    def blob_template(self):
        return BlobTemplate(
            population=100,
            traceable_characteristics={'vaccine_level': 1, 'sir_state': 'infected'},
            sampled_characteristics={
                'age': {'child': 30, 'adult': 50, 'ancient': 20},
                'economic_profile': {'unemployed': 40, 'worker': 60}
            }
        )
    
    def test_traceable_characteristics_override_replace(self, blob_factory: BlobFactory):
        override = {'vaccine_level': 1, 'sir_state': 'infected'}
        traceable = blob_factory._traceable_characteristics_override(override)
        assert traceable['vaccine_level'] == 1, "Traceable property 'vaccine_level' should be overridden to 1."
        assert traceable['sir_state'] == 'infected', "Traceable property 'sir_state' should be overridden to 'infected'."
        assert len(traceable) == 2, "Only the overridden properties should be present."

    def test_traceable_characteristics_override_add(self, blob_factory: BlobFactory):
        override = {'favorite_color': 'blue'}
        traceable = blob_factory._traceable_characteristics_override(override)
        assert traceable['vaccine_level'] == 0, "Traceable property 'vaccine_level' should be overridden to 0."
        assert traceable['sir_state'] == 'susceptible', "Traceable property 'sir_state' should be overridden to 'susceptible'."
        assert traceable['favorite_color'] == 'blue', "Traceable property 'favorite_color' should be added."
        assert len(traceable) == 3, "Only the overridden properties should be present."

    def test_traceable_characteristics_override_replace_and_add(self, blob_factory: BlobFactory):
        override = {'vaccine_level': 2, 'sir_state': 'removed', 'favorite_color': 'red'}
        traceable = blob_factory._traceable_characteristics_override(override)
        assert traceable['vaccine_level'] == 2, "Traceable property 'vaccine_level' should be overridden to 2."
        assert traceable['sir_state'] == 'removed', "Traceable property 'sir_state' should be overridden to 'removed'."
        assert traceable['favorite_color'] == 'red', "Traceable property 'favorite_color' should be added."
        assert len(traceable) == 3, "Only the overridden properties should be present."

    def test_generate_blob_rand(self, blob_factory: BlobFactory):
        blob = blob_factory.generate_blob_rand(1, 1, 100)
        assert blob.get_population_size() == 100, "Blob population size should be 100."
        assert blob.get_traceable_characteristic('vaccine_level') == 0, "Traceable property 'vaccine_level' should be 0."
        assert blob.get_traceable_characteristic('sir_state') == 'susceptible', "Traceable property 'sir_state' should be 'susceptible'."
        assert blob.mother_blob_id == 1, "Mother blob ID should be set correctly."
        assert blob.node_of_origin == 1, "Node of origin should be set correctly."

    def test_generate_blob_rand_invalid_population(self, blob_factory: BlobFactory):
        with pytest.raises(ValueError, match="Invalid population size."):
            blob_factory.generate_blob_rand(1, 1, 0)

    def test_generate_blob_rand_factory_change(self, blob_factory: BlobFactory):
        blob1 = blob_factory.generate_blob_rand(1, 1, 100)
        assert blob1.sampled_characteristics.is_valid() == True, "Blob should have valid sampled characteristics."
        assert blob1.get_population_size() == 100, "Blob population size should be 100."
        assert len(blob1.sampled_characteristics.characteristics) == 2, "Blob should have 2 sampled characteristics."
        assert len(blob1.traceable_characteristics) == 2, "Blob should have 2 traceable characteristics."
        blob_factory.characteristics_factory.add_sampled_characteristic('favorite_color', ['red', 'blue'])
        blob2 = blob_factory.generate_blob_rand(1, 1, 200)
        assert blob2.get_population_size() == 200, "Blob population size should be 200."
        assert len(blob2.sampled_characteristics.characteristics) == 3, "Blob should have 3 sampled characteristics."
        assert len(blob2.traceable_characteristics) == 2, "Blob should have 2 traceable characteristics."
        assert len(blob1.sampled_characteristics.characteristics) == 2, "Blob should have 2 sampled characteristics."
        blob_factory.characteristics_factory.add_traceable_characteristic('mode_of_transport', 'walking')
        blob3 = blob_factory.generate_blob_rand(1, 1, 300)
        assert blob3.get_population_size() == 300, "Blob population size should be 300."
        assert len(blob3.sampled_characteristics.characteristics) == 3, "Blob should have 3 sampled characteristics."
        assert len(blob3.traceable_characteristics) == 3, "Blob should have 3 traceable characteristics."
        assert len(blob1.traceable_characteristics) == 2, "Blob should have 2 traceable characteristics."
        assert len(blob2.traceable_characteristics) == 2, "Blob should have 2 traceable characteristics."
        blob_factory.characteristics_factory.add_sampled_characteristic('income', ['low', 'medium', 'high'])
        blob_factory.characteristics_factory.add_traceable_characteristic('favorite_food', 'pizza')
        blob4 = blob_factory.generate_blob_rand(1, 1, 400)
        assert blob4.get_population_size() == 400, "Blob population size should be 400."
        assert len(blob4.sampled_characteristics.characteristics) == 4, "Blob should have 4 sampled characteristics."
        assert len(blob4.traceable_characteristics) == 4, "Blob should have 4 traceable characteristics."
        assert len(blob1.sampled_characteristics.characteristics) == 2, "Blob should have 2 sampled characteristics."
        assert len(blob1.traceable_characteristics) == 2, "Blob should have 2 traceable characteristics."
        assert len(blob2.sampled_characteristics.characteristics) == 3, "Blob should have 3 sampled characteristics."
        assert len(blob2.traceable_characteristics) == 2, "Blob should have 2 traceable characteristics."
        assert len(blob3.sampled_characteristics.characteristics) == 3, "Blob should have 3 sampled characteristics."
        assert len(blob3.traceable_characteristics) == 3, "Blob should have 3 traceable characteristics."
        with pytest.raises(ValueError, match="Invalid population size."):
            blob_factory.generate_blob_rand(1, 1, 0)

    def test_generate_blob_empty(self, blob_factory: BlobFactory):
        blob = blob_factory.generate_blob_empty(1, 1)
        assert blob.get_population_size() == 0, "Blob population size should be 0."
        assert blob.get_traceable_characteristic('vaccine_level') == 0, "Traceable property 'vaccine_level' should be 0."
        assert blob.get_traceable_characteristic('sir_state') == 'susceptible', "Traceable property 'sir_state' should be 'susceptible'."
        assert blob.mother_blob_id == 1, "Mother blob ID should be set correctly."
        assert blob.node_of_origin == 1, "Node of origin should be set correctly."

    def test_generate_blob_empty_factory_change(self, blob_factory: BlobFactory):
        blob1 = blob_factory.generate_blob_empty(1, 1)
        assert blob1.sampled_characteristics.is_valid() == True, "Blob should have valid sampled characteristics."
        assert len(blob1.sampled_characteristics.characteristics) == 2, "Blob should have 2 sampled characteristics."
        assert len(blob1.traceable_characteristics) == 2, "Blob should have 2 traceable characteristics."
        blob_factory.characteristics_factory.add_sampled_characteristic('favorite_color', ['red', 'blue'])
        blob2 = blob_factory.generate_blob_empty(1, 1)
        assert len(blob2.sampled_characteristics.characteristics) == 3, "Blob should have 3 sampled characteristics."
        assert len(blob2.traceable_characteristics) == 2, "Blob should have 2 traceable characteristics."
        assert len(blob1.sampled_characteristics.characteristics) == 2, "Blob should have 2 sampled characteristics."
        blob_factory.characteristics_factory.add_traceable_characteristic('mode_of_transport', 'walking')
        blob3 = blob_factory.generate_blob_empty(1, 1)
        assert len(blob3.sampled_characteristics.characteristics) == 3, "Blob should have 3 sampled characteristics."
        assert len(blob3.traceable_characteristics) == 3, "Blob should have 3 traceable characteristics."
        assert len(blob1.traceable_characteristics) == 2, "Blob should have 2 traceable characteristics."
        assert len(blob2.traceable_characteristics) == 2, "Blob should have 2 traceable characteristics."
        blob_factory.characteristics_factory.add_sampled_characteristic('income', ['low', 'medium', 'high'])
        blob_factory.characteristics_factory.add_traceable_characteristic('favorite_food', 'pizza')
        blob4 = blob_factory.generate_blob_empty(1, 1)
        assert len(blob4.sampled_characteristics.characteristics) == 4, "Blob should have 4 sampled characteristics."
        assert len(blob4.traceable_characteristics) == 4, "Blob should have 4 traceable characteristics."
        assert len(blob1.sampled_characteristics.characteristics) == 2, "Blob should have 2 sampled characteristics."
        assert len(blob1.traceable_characteristics) == 2, "Blob should have 2 traceable characteristics."
        assert len(blob2.sampled_characteristics.characteristics) == 3, "Blob should have 3 sampled characteristics."
        assert len(blob2.traceable_characteristics) == 2, "Blob should have 2 traceable characteristics."
        assert len(blob3.sampled_characteristics.characteristics) == 3, "Blob should have 3 sampled characteristics."
        assert len(blob3.traceable_characteristics) == 3, "Blob should have 3 traceable characteristics."
 

    def test_generate_blob_with_profile_complete(self, blob_factory: BlobFactory):
        profile = {
            'age': {'child': 30, 'adult': 50, 'ancient': 20},
            'economic_profile': {'unemployed': 30, 'worker': 70}
        }
        blob = blob_factory.generate_blob_with_profile(1, 1, 100, profile)
        assert blob.get_population_size() == 100, "Blob population size should be 100."
        assert blob.get_traceable_characteristic('vaccine_level') == 0, "Traceable property 'vaccine_level' should be 0."
        assert blob.get_traceable_characteristic('sir_state') == 'susceptible', "Traceable property 'sir_state' should be 'susceptible'."
        assert blob.mother_blob_id == 1, "Mother blob ID should be set correctly."
        assert blob.node_of_origin == 1, "Node of origin should be set correctly."
        assert blob.sampled_characteristics.characteristics['age'].categories == {'child': 30, 'adult': 50, 'ancient': 20}, "Profiled 'age' categories should be set correctly."
        assert blob.sampled_characteristics.characteristics['economic_profile'].categories == {'unemployed': 30, 'worker': 70}, "Profiled 'economic_profile' categories should be set correctly."

    def test_generate_blob_with_profile_incomplete(self, blob_factory: BlobFactory):
        profile = {
            'age': {'child': 30, 'adult': 50},
            'economic_profile': {'unemployed': 30}
        }
        blob = blob_factory.generate_blob_with_profile(1, 1, 100, profile)
        assert blob.get_population_size() == 100, "Blob population size should be 100."
        assert blob.get_traceable_characteristic('vaccine_level') == 0, "Traceable property 'vaccine_level' should be 0."
        assert blob.get_traceable_characteristic('sir_state') == 'susceptible', "Traceable property 'sir_state' should be 'susceptible'."
        assert blob.mother_blob_id == 1, "Mother blob ID should be set correctly."
        assert blob.node_of_origin == 1, "Node of origin should be set correctly."
        assert blob.sampled_characteristics.characteristics['age'].categories == {'child': 30, 'adult': 50, 'ancient': 20}, "Profiled 'age' categories should be set correctly."
        assert blob.sampled_characteristics.characteristics['economic_profile'].categories == {'unemployed': 30, 'worker': 70}, "Profiled 'economic_profile' categories should be set correctly."

    def test_generate_blob_with_profile_overprofiled(self, blob_factory: BlobFactory):
        profile = {
            'age': {'child': 80, 'adult': 100, 'ancient': 70},
            'economic_profile': {'unemployed': 130, 'worker': 170}
        }
        blob = blob_factory.generate_blob_with_profile(1, 1, 100, profile)
        assert blob.get_population_size() == 100, "Blob population size should be 100."
        assert blob.get_traceable_characteristic('vaccine_level') == 0, "Traceable property 'vaccine_level' should be 0."
        assert blob.get_traceable_characteristic('sir_state') == 'susceptible', "Traceable property 'sir_state' should be 'susceptible'."
        assert blob.mother_blob_id == 1, "Mother blob ID should be set correctly."
        assert blob.node_of_origin == 1, "Node of origin should be set correctly."

    def test_generate_blob_with_profile_invalid_population(self, blob_factory: BlobFactory):
        profile = {
            'age': {'child': 30, 'adult': 50, 'ancient': 20},
            'economic_profile': {'unemployed': 30, 'worker': 70}
        }
        with pytest.raises(ValueError, match="Invalid population size."):
            blob_factory.generate_blob_with_profile(1, 1, 0, profile)

    def test_generate_blob_with_profile_factory_change(self, blob_factory: BlobFactory):
        profile = {
            'age': {'child': 80, 'adult': 100, 'ancient': 70},
            'economic_profile': {'unemployed': 130, 'worker': 170}
        }
        blob1 = blob_factory.generate_blob_with_profile(1, 1, 100, profile)
        assert blob1.sampled_characteristics.is_valid() == True, "Blob should have valid sampled characteristics."
        assert blob1.get_population_size() == 100, "Blob population size should be 100."
        assert len(blob1.sampled_characteristics.characteristics) == 2, "Blob should have 2 sampled characteristics."
        assert len(blob1.traceable_characteristics) == 2, "Blob should have 2 traceable characteristics."
        blob_factory.characteristics_factory.add_sampled_characteristic('favorite_color', ['red', 'blue'])
        blob2 = blob_factory.generate_blob_with_profile(1, 1, 200, profile)
        assert blob2.get_population_size() == 200, "Blob population size should be 200."
        assert len(blob2.sampled_characteristics.characteristics) == 3, "Blob should have 3 sampled characteristics."
        assert len(blob2.traceable_characteristics) == 2, "Blob should have 2 traceable characteristics."
        assert len(blob1.sampled_characteristics.characteristics) == 2, "Blob should have 2 sampled characteristics."
        blob_factory.characteristics_factory.add_traceable_characteristic('mode_of_transport', 'walking')
        blob3 = blob_factory.generate_blob_with_profile(1, 1, 300, profile)
        assert blob3.get_population_size() == 300, "Blob population size should be 300."
        assert len(blob3.sampled_characteristics.characteristics) == 3, "Blob should have 3 sampled characteristics."
        assert len(blob3.traceable_characteristics) == 3, "Blob should have 3 traceable characteristics."
        assert len(blob1.traceable_characteristics) == 2, "Blob should have 2 traceable characteristics."
        assert len(blob2.traceable_characteristics) == 2, "Blob should have 2 traceable characteristics."
        blob_factory.characteristics_factory.add_sampled_characteristic('income', ['low', 'medium', 'high'])
        blob_factory.characteristics_factory.add_traceable_characteristic('favorite_food', 'pizza')
        blob4 = blob_factory.generate_blob_with_profile(1, 1, 400, profile)
        assert blob4.get_population_size() == 400, "Blob population size should be 400."
        assert len(blob4.sampled_characteristics.characteristics) == 4, "Blob should have 4 sampled characteristics."
        assert len(blob4.traceable_characteristics) == 4, "Blob should have 4 traceable characteristics."
        assert len(blob1.sampled_characteristics.characteristics) == 2, "Blob should have 2 sampled characteristics."
        assert len(blob1.traceable_characteristics) == 2, "Blob should have 2 traceable characteristics."
        assert len(blob2.sampled_characteristics.characteristics) == 3, "Blob should have 3 sampled characteristics."
        assert len(blob2.traceable_characteristics) == 2, "Blob should have 2 traceable characteristics."
        assert len(blob3.sampled_characteristics.characteristics) == 3, "Blob should have 3 sampled characteristics."
        assert len(blob3.traceable_characteristics) == 3, "Blob should have 3 traceable characteristics."
        with pytest.raises(ValueError, match="Invalid population size."):
            blob_factory.generate_blob_with_profile(1, 1, 0, profile)

    def test_generate_blob_from_template_valid(self, blob_factory: BlobFactory, blob_template: BlobTemplate):
        blob = blob_factory.generate_blob_from_template(1, 1, blob_template)
        assert blob.get_population_size() == 100
        assert blob.get_traceable_characteristic('vaccine_level') == 1
        assert blob.get_traceable_characteristic('sir_state') == 'infected'
        assert blob.sampled_characteristics.characteristics['age'].categories == {'child': 30, 'adult': 50, 'ancient': 20}
        assert blob.sampled_characteristics.characteristics['economic_profile'].categories == {'unemployed': 40, 'worker': 60}

    def test_generate_blob_from_template_invalid_population(self, blob_factory: BlobFactory, blob_template: BlobTemplate):
        blob_template.population = -1
        with pytest.raises(ValueError, match="Invalid population size."):
            blob_factory.generate_blob_from_template(1, 1, blob_template)

    def test_generate_blob_from_template_characteristics_initialization(self, blob_factory: BlobFactory, blob_template: BlobTemplate):
        blob = blob_factory.generate_blob_from_template(1, 1, blob_template)
        assert blob.sampled_characteristics.characteristics['age'].get_population_size() == 100
        assert blob.sampled_characteristics.characteristics['economic_profile'].get_population_size() == 100