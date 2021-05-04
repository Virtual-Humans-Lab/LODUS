import math
import json

def distance2D(p1, p2):
    d = (p1[0] - p2[0]) * (p1[0] - p2[0]) + (p1[1] - p2[1]) * (p1[1] - p2[1])
    return math.sqrt(d)


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



def weighted_int_distribution_with_weights(available, quantity, weight_list):
    total_population = sum(available)
    quantity = min(quantity, total_population)
    total_weight = sum(weight_list)

    #normalized_population = [p / total_population for p in available]
    normalized_weights = [w / total_weight for w in weight_list]
    
    quantity_weight = [int(w * quantity) for w in normalized_weights]
    
    weighted_available = [min(available[x], quantity_weight[x]) for x in range(len(available))]

    total_weighted_available = sum(weighted_available)
    weighted_available_ratio = [p / total_weighted_available for p in weighted_available]

    requests = [int(w * quantity) for w in weighted_available_ratio]

    #print("QUEANTUTAEIFDFISADRTE",sum(requests), requests)

    return requests
    # remaining_to_pick = quantity - sum(weighted_available)
    # reduced_available = [x - y for (x,y) in zip(available, weighted_available)]
    
    # if remaining_to_pick > 0:
        
    #     while remaining_to_pick > 0:
    #         largest_x = 0
    #         largest_quant = 0
    #         for x in range(len(reduced_available)):
    #             if reduced_available[x] > largest_quant:
    #                 largest_x = x
    #                 largest_quant = reduced_available[x]
            
    #         weighted_available[largest_x] += 1
    #         reduced_available[largest_x] -=1
    #         remaining_to_pick -= 1

    # return weighted_available
 
# never reuses an id for a given attribute
class IDGen:
    stacks = {}
    
    def __init__(self, attribute, current_id = 0):
        self.attribute = attribute
        if attribute not in IDGen.stacks:
            IDGen.stacks[attribute] = current_id

    def get_id(self):
        current_id = IDGen.stacks[self.attribute]
        IDGen.stacks[self.attribute] += 1
        return current_id


