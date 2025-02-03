from enum import Enum
import math
from typing import List
import numpy as np
from geopy import distance
from pyproj import Geod


class DistanceType(Enum):
    LONG_LAT = 1
    METRES_GEOPY = 2
    METRES_PYPROJ = 3

def distance2D(p1, p2):
    d = (p1[0] - p2[0]) * (p1[0] - p2[0]) + (p1[1] - p2[1]) * (p1[1] - p2[1])
    return math.sqrt(d)

def geopy_distance_metre(p1, p2):
    return distance.distance(p1, p2).m

def pyproj_distance_metre(p1, p2):
    return Geod(ellps='WGS84').inv(p1[0], p1[1], p2[0],p2[1])[2]

def distribute_randomly(total_sum: int, n_partitions: int) -> List[int]:
    """
    Distribute a total sum into random values across a specified number of partitions.

    Args:
        total_sum (int): The total sum to be partitioned.
        n_partitions (int): The number of partitions.

    Returns:
        list[int]: A list of partitioned values summing up to `total_sum`.
    """
    if n_partitions <= 0:
        raise ValueError("Number of partitions must be greater than 0.")
    if n_partitions == 1:
        return [total_sum]
    if total_sum == 0:
        return [0] * n_partitions

    # Generate random values and sort them
    random_values = np.sort(np.random.randint(0, total_sum, size=n_partitions - 1)).tolist()

    # Add boundary values to define intervals
    boundaries = [0] + random_values + [total_sum]

    # Compute differences between consecutive boundaries to get partition values
    return [boundaries[i + 1] - boundaries[i] for i in range(len(boundaries) - 1)]

def weighted_int_distribution(available_items:list[int], quantity:int):
    """Distributes a given quantity among a list of available items based on their weights.
    Ensures that the distribution is as fair as possible given the constraints of integer values
    """
    total_population = sum(available_items)
    quantity = min(quantity, total_population)

    adjusted_quantities = [
            0 if available_items[x] == 0 else quantity / (total_population / available_items[x])
            for x in range(len(available_items))
    ]
    
    int_adjusted_quantities = [int(x) for x in adjusted_quantities]
    reduced_quantities = [x - y for x, y in zip(available_items, int_adjusted_quantities)]
    sum_adjusted = sum(int_adjusted_quantities)

    if sum_adjusted != quantity:
        remaining = quantity - sum_adjusted

        while remaining > 0:
            largest_x = max(range(len(reduced_quantities)), key=lambda x: reduced_quantities[x])
            int_adjusted_quantities[largest_x] += 1
            reduced_quantities[largest_x] -= 1
            remaining -= 1

    return int_adjusted_quantities


def weighted_distribution_with_weights(available, quantity, weight_list):
    total_population = sum(available)
    quantity = min(quantity, total_population)
    total_weight = sum(weight_list)

    normalized_population = [p / total_population for p in available]
    normalized_weights = [w / total_weight for w in weight_list]
    
    quantity_weight = [w * quantity for w in normalized_weights]
    
    weighted_available = [min(available[x], quantity_weight[x]) for x in range(len(available))]

def distribute_ints_from_weights(quantity: int, weight_list:list[int]):
    """Distributes a given quantity among a list of available items based on their weights."""
    if quantity == 0:
        return np.zeros(len(weight_list), dtype=int)

    weights_sum = sum(weight_list)
    adjusted_weights = [w / weights_sum for w in weight_list]
    int_quantities = [math.floor(aw * quantity) for aw in adjusted_weights]

    remaining = quantity - sum(int_quantities)
    if remaining == 0:
        return int_quantities

    for _ in range(remaining):
        largest_index = max(range(len(adjusted_weights)), key=lambda i: adjusted_weights[i])
        int_quantities[largest_index] += 1
        adjusted_weights[largest_index] -= 1.0 / quantity

    return int_quantities
    
def distribute_ints_from_weights_with_limit(quantity, weight_list:list[float], limits:list[int]):
    
    if quantity == 0:
        return np.zeros(len(weight_list), dtype=int)
    if quantity > sum(limits):
        print("QUANTITY REQUESTED IS BIGGER THAN LIMIT SUM")
        quantity = sum(limits)
    
    weights_sum = sum(weight_list)
    adjusted_weights = [w/weights_sum for w in weight_list]
    int_quantities = [math.floor(aw*quantity) for aw in adjusted_weights]
    int_quantities = [min(limits[i],int_quantities[i]) for i in range(len(int_quantities))] 
    
    if sum(int_quantities) == quantity:
        return int_quantities
    
    # adds remaining quantities 
    for x in range(quantity - sum(int_quantities)):    
        largest_index = 0
        largest_value = -10000.0

        for i in range(len(adjusted_weights)):
            if int_quantities[i] < limits[i] and adjusted_weights[i] > largest_value:
                largest_index = i
                largest_value = adjusted_weights[i]
        #print(largest_index, len(int_quantities))
        int_quantities[largest_index] += 1
        adjusted_weights[largest_index] -= 1.0/quantity
    
    return int_quantities


def weighted_int_distribution_with_weights(available, quantity, weight_list):
    total_population = sum(available)
    quantity = min(quantity, total_population)
    total_weight = sum(weight_list)

    #normalized_population = [p / total_population for p in available]
    normalized_weights = [w / total_weight for w in weight_list]
    
    quantity_weight = [int(w * quantity) for w in normalized_weights]
    
    weighted_available = [min(available[x], quantity_weight[x]) for x in range(len(available))]
    total_weighted_available = sum(weighted_available)
    
    if total_weighted_available > 0:
        weighted_available_ratio = [p / total_weighted_available for p in weighted_available]
        return [int(w * quantity) for w in weighted_available_ratio]

    #requests = [int(w * quantity) for w in weighted_available_ratio]

    #print("QUEANTUTAEIFDFISADRTE",sum(requests), requests)

    remaining_to_pick = quantity - sum(weighted_available)
    reduced_available = [x - y for (x,y) in zip(available, weighted_available)]
    
    if remaining_to_pick > 0:
        
        while remaining_to_pick > 0:
            largest_x = 0
            largest_quant = 0
            for x in range(len(reduced_available)):
                if reduced_available[x] > largest_quant:
                    largest_x = x
                    largest_quant = reduced_available[x]
            
            weighted_available[largest_x] += 1
            reduced_available[largest_x] -=1
            remaining_to_pick -= 1

    return weighted_available
