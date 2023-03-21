import sys
sys.path.append('../')
sys.path.append('../EpidemicContagionPython/EpidemicContagionPython/')
import math
#import random
from random_inst import FixedRandom

from  EpidemicPopulation import EpidemicPopulation



def probabilistic_rounding(n):
    fractional = math.fmod(n, 1)
    whole = int(math.floor(n))

    #r = random.random()
    r = FixedRandom.instance.random()

    if r < fractional:
        whole += 1

    return whole


infection_solver = EpidemicPopulation(Count = 0, Infected = 0)

table = open('infection_debug.csv', 'w', encoding='utf-8')
table.write('Frame;ID;S;I;R;aS;aI;aR;nS;nI;nR\n')


cycle_length = 1
loops = cycle_length * 200
density = 1

do_round = True

susceptible = 190489 - 50
infected = 50
removed = 0

total = susceptible + infected + removed



infection_solver.Count = susceptible + infected + removed


for loop in range(loops):
    
    old_susceptible = infection_solver.Susceptible 
    old_infected = infection_solver.Infected
    old_removed = infection_solver.Removed

    infection_solver.Susceptible = susceptible 
    infection_solver.Infected = infected
    infection_solver.Removed = removed

    infection_solver.InfectWithDensityAndDay(density, loop // cycle_length)

    susceptible = infection_solver.Susceptible 
    infected = infection_solver.Infected
    removed = infection_solver.Removed

    if do_round:
        new_total = -1
        while total != new_total:
            susceptible = probabilistic_rounding(infection_solver.Susceptible)
            infected = probabilistic_rounding(infection_solver.Infected)
            removed = probabilistic_rounding(infection_solver.Removed)

            new_total = susceptible + infected + removed

    infection_solver.Susceptible = susceptible 
    infection_solver.Infected = infected
    infection_solver.Removed = removed
    
    s = f'{loop};Centro\\home;{old_susceptible};{old_infected};{old_removed};{infection_solver.Susceptible};{infection_solver.Infected};{infection_solver.Removed};{susceptible};{infected};{removed}\n'
    table.write(s)


table.close()