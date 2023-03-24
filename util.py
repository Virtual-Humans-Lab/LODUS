from enum import Enum
import math
import json
import typing
import numpy
from geopy import distance
from pyproj import Proj
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


def weighted_int_distribution(available, quantity):
    total_population = sum(available)
    quantity = min(quantity, total_population)

    adjusted_quantities  = [0 for x in available]
    for x in range(len(available)):
        if available[x] == 0:
            adjusted_quantities[x] = 0
        else:
            adjusted_quantities[x] = quantity / (total_population / available[x])
    
    int_adjusted_quantities =  [int(x) for x in adjusted_quantities]

    reduced_quantities = [x - y for (x,y) in zip(available, int_adjusted_quantities)]
    sum_adjusted = sum(int_adjusted_quantities)

    if sum(int_adjusted_quantities) != quantity:
        remaining = quantity - sum_adjusted

        while remaining > 0:
            largest_x = 0
            largest_quant = 0
            for x in range(len(reduced_quantities)):
                if reduced_quantities[x] > largest_quant:
                    largest_x = x
                    largest_quant = reduced_quantities[x]
            
            int_adjusted_quantities[largest_x] += 1
            reduced_quantities[largest_x] -=1
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

def distribute_ints_from_weights(quantity, weight_list:list[float]):
    
    if quantity == 0:
        return numpy.zeros(len(weight_list), dtype=int)
    
    weights_sum = sum(weight_list)
    adjusted_weights = [w/weights_sum for w in weight_list]
    int_quantities = [math.floor(aw*quantity) for aw in adjusted_weights]
        
    if sum(int_quantities) == quantity:
        return int_quantities
    
    # adds remaining quantities 
    for x in range(quantity - sum(int_quantities)):    
        largest_index = 0;
        largest_value = 0.0;

        for i in range(len(adjusted_weights)):
            if adjusted_weights[i] > largest_value:
                largest_index = i;
                largest_value = adjusted_weights[i];
        #print(largest_index, len(int_quantities))
        int_quantities[largest_index] += 1;
        adjusted_weights[largest_index] -= 1.0/quantity;
    
    return int_quantities
    
def distribute_ints_from_weights_with_limit(quantity, weight_list:list[float], limits:list[int]):
    
    if quantity == 0:
        return numpy.zeros(len(weight_list), dtype=int)
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
        largest_index = 0;
        largest_value = -10000.0;

        for i in range(len(adjusted_weights)):
            if int_quantities[i] < limits[i] and adjusted_weights[i] > largest_value:
                largest_index = i;
                largest_value = adjusted_weights[i];
        #print(largest_index, len(int_quantities))
        int_quantities[largest_index] += 1;
        adjusted_weights[largest_index] -= 1.0/quantity;
    
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
 
# never reuses an id for a given attribute
class IDGen:
    stacks = {}
    
    def __init__(self, attribute, current_id = 0):
        self.attribute = attribute
        if attribute not in IDGen.stacks:
            IDGen.stacks[attribute] = current_id

    def get_id(self) -> int:
        current_id = IDGen.stacks[self.attribute]
        IDGen.stacks[self.attribute] += 1
        return current_id


