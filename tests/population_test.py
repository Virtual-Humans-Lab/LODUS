import sys

from random_inst import FixedRandom

from numpy import character
import pytest
from population import SampledCharacteristic
import environment, util

@pytest.fixture(scope="session", autouse=True)
def start_fixedrandom():
    """Initialize FixedRandom to ensure deterministic behavior in tests."""
    FixedRandom()  # Ensure FixedRandom is defined or imported properly.

def test_property_bucket_add_bucket():
    """
    Test PropertyBucket.add_bucket functionality.

    Case 1: Add a bucket with the same characteristic.
        Expected: Combined population of both buckets.
    Case 2: Add a bucket with a different characteristic.
        Expected: No changes to the original bucket population.

    Tests PropertyBucket.add_bucket

    Case 1: 
        action : Creates 2 PropertyBuckets with the same characteristic. Add the second to the first one.
        result : Bucket1 should contain the sum of both populations.
                    
    Case 2: 
        action : Creates a third PropertyBucket with a different characteristic. Add the third to the first one.
        result : Operation does nothing and populations remain the same.
    """

    # Case 1:
    # Create a PropertyBucket with the 'characteristic_A', 3 different values, and population = 60 with random distribution
    aux_bucket1 = SampledCharacteristic('characteristic_A')
    aux_bucket1.set_values_rand(('char_A_value_1', 'char_A_value_2', 'char_A_value_3') , 60)

    # Create another PropertyBucket with the same characteristic and values, but population = 30
    aux_bucket2 = SampledCharacteristic('characteristic_A')
    aux_bucket2.set_values_rand(('char_A_value_1', 'char_A_value_2', 'char_A_value_3') , 30)

    # Test adding PropertyBuckets with the same characteristic 
    aux_bucket_size1 = aux_bucket1.get_population_size()
    aux_bucket_size2 = aux_bucket2.get_population_size()
    aux_bucket1.merge_values(aux_bucket2)

    # Should be the sum of population_size in both aux buckets
    merge_size_test_1 = aux_bucket1.get_population_size()

    # assert if bucket was added correctly
    assert merge_size_test_1 == (aux_bucket_size1 + aux_bucket_size2), 'Add bucket not adding same property buckets correctly.'

    # Case 2:
    # Create a PropertyBucket with different characteristic and values
    # The values("ids/keys/str"), their quantity, and the population are irrelevant in this test due to the characteristic being different
    aux_bucket3 = SampledCharacteristic('characteristic_B')
    aux_bucket3.set_values_rand(('char_B_value_1', 'char_B_value_2') , 60)

    # Test adding PropertyBuckets with a different characteristic 
    aux_bucket1.merge_values(aux_bucket3)

    # Should be the same value as 'merge_size_test_1'
    merge_size_test_2 = aux_bucket1.get_population_size()

    # assert whether bucket was skipped
    assert merge_size_test_2 == (aux_bucket_size1 + aux_bucket_size2), 'Add bucket adding different property buckets incorrectly.'