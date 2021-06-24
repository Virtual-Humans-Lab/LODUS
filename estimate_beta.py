#encoding: utf-8
# python .\estimate_beta.py --i 1 --m 2 --f .\DataInput\Vaccine_Infection_Centro_3cpd.json --b none
import sys
sys.path.append('./Plugins/')

import argparse

import environment
from util import *
from data_parse_util import *
import population

from random_inst import FixedRandom

from AgentBasedPlugin import AgentBasedPlugin
from InfectionVaccinePlugin import InfectionVaccinePlugin
from SocialIsolationPlugin import SocialIsolationPlugin
from GatherPopulationPlugin import GatherPopulationPlugin
from ReverseSocialIsolationPlugin import ReverseSocialIsolationPlugin
from ReturnPopulationPlugin import ReturnPopulationPlugin
from LevyWalkPlugin import LevyWalkPlugin

from simulation_logger import SimulationLogger
from pathlib import Path
import datetime
import time
import pickle


def EstimateBetaForToday(_step, _beta_search):
	print("Entering beta search loop...")
	snapName = f'snap_estimate_beta.pickle'
	with open(snapName, "wb") as output_file:
		print("Generating snapshot of simulation.", snapName)
		pickle.dump(env_graph, output_file)


	bestGamma = 1 / 14
	bestBeta = 0
	maxBeta = 1.0
	minBeta = 0.0
	oldMinBeta = -1.0
	oldMidBeta = -1.0
	oldMaxBeta = -1.0
	minError = sys.float_info.max
	oldMinBetaError = sys.float_info.max
	oldMidBetaError = sys.float_info.max
	oldMaxBetaError = sys.float_info.max

	for x in range(_beta_search):
		print("x:", x)
		midBeta = (maxBeta + minBeta) / 2

		print("minBeta: ", minBeta)
		print("midBeta: ", midBeta)
		print("maxBeta: ", maxBeta)

		if(minBeta == oldMinBeta):
			sqrMinError = oldMinBetaError
		elif(minBeta == oldMidBeta):
			sqrMinError = oldMidBetaError
		else:
			[sqrMinError, minScalarError] = ComputeErrorForToday(_step, minBeta, bestGamma, snapName)

		oldMinBeta = minBeta
		oldMinBetaError = sqrMinError
		print(f'sqrMinError: {sqrMinError}\tminScalarError: {minScalarError}')

		if(sqrMinError == 0):
			minError = sqrMinError
			scalarError = minScalarError
			bestBeta = minBeta
			break

		if(maxBeta == oldMaxBeta):
			sqrMaxError = oldMaxBetaError
		elif(maxBeta == oldMidBeta):
			sqrMaxError = oldMidBetaError
		else:
			[sqrMaxError, maxScalarError] = ComputeErrorForToday(_step, maxBeta, bestGamma, snapName)

		oldMaxBeta = maxBeta
		oldMaxBetaError = sqrMaxError
		print(f'sqrMaxError: {sqrMaxError}\tmaxScalarError: {maxScalarError}')

		if(sqrMaxError == 0):
			minError = sqrMaxError
			scalarError = maxScalarError
			bestBeta = maxBeta
			break

		[sqrMidError, midScalarError] = ComputeErrorForToday(_step, midBeta, bestGamma, snapName)

		oldMidBeta = midBeta
		oldMidBetaError = sqrMidError
		print("sqrMidError: ", sqrMidError)
		print(f'sqrMidError: {sqrMidError}\tmidScalarError: {midScalarError}')

		if(sqrMidError == 0):
			minError = sqrMidError
			scalarError = midScalarError
			bestBeta = midBeta
			break

		if(minError > sqrMinError):
			minError = sqrMinError
			scalarError = minScalarError
			bestBeta = minBeta
			print("(minBeta) bestBeta = ", bestBeta)

		if(minError > sqrMidError):
			minError = sqrMidError
			scalarError = midScalarError
			bestBeta = midBeta
			print("(midBeta) bestBeta = ", bestBeta)
			
		if(minError > sqrMaxError):
			minError = sqrMaxError
			scalarError = maxScalarError
			bestBeta = maxBeta
			print("(maxBeta) bestBeta = ", bestBeta)

		if(sqrMinError >= sqrMidError) and (sqrMinError >= sqrMaxError):
			minBeta = midBeta
		if(sqrMaxError >= sqrMidError) and (sqrMaxError >= sqrMinError):
			maxBeta = midBeta
		if(maxBeta == minBeta):
			print("maxBeta and minBeta are the same!")
			print("bestBeta:", bestBeta)
			break
	
	print(" ... finish!")
	inf_plugin.beta = bestBeta
	inf_plugin.gamma = bestGamma
	print("Best beta:", bestBeta, end='\t')
	print("Best gamma:", bestGamma)
	print("Error:", scalarError)
	return scalarError


def ComputeErrorForToday(_step, _beta, _gamma, _snap):
	#_test_env = copy.deepcopy(env_graph)
	with open(_snap, "rb") as input_file:
		print("Reading simulation snapshot...", _snap)
		_test_env = pickle.load(input_file)

	auxRandom = copy.deepcopy(FixedRandom.instance)

	# Set testBeta
	test_inf = InfectionVaccinePlugin(_test_env, use_infect_move_pop=True, day_length = day_duration)
	test_inf.total_infected = inf_plugin.total_infected
	test_inf.vaccinated = env_graph.get_population_size(pop_template_vac)
	test_inf.gamma = _gamma
	test_inf.beta = _beta
	_test_env.LoadPlugin(test_inf)

	susceptible = _test_env.get_population_size(pop_template_suc)
	print("(before)Susceptible: %d" % susceptible)
	infected = inf_plugin.total_infected
	print("(before)Infected: %d - expI[%d]: %d" % (infected, day, expectedI[day]))
	removed = _test_env.get_population_size(pop_template_rem)
	print("(before)Removed: %d" % removed)
	vaccinated = _test_env.get_population_size(pop_template_vac)
	print("(before)Vaccinated: %d" % vaccinated)

	print(f'Compute error for beta ({_beta}) and gamma ({_gamma})')
	print(f'Simulate {day_duration} time steps...', end=' ')
	for event in range(day_duration):
		_test_env.update_time_step(event, _step + event)
	print("Done!")

	susceptible = _test_env.get_population_size(pop_template_suc)
	print("(after)Susceptible: %d" % susceptible)
	infected = test_inf.total_infected
	print("(after)Infected: %d - expI[%d]: %d" % (infected, day, expectedI[day]))
	removed = _test_env.get_population_size(pop_template_rem)
	print("(after)Removed: %d" % removed)
	vaccinated = _test_env.get_population_size(pop_template_vac)
	print("(after)Vaccinated: %d" % vaccinated)

	error = infected - expectedI[day]
	_sqrError = error * error
	FixedRandom.instance = copy.deepcopy(auxRandom)
	return [_sqrError, error]


arg_parser = argparse.ArgumentParser(description="Population Dynamics Simulation.")
arg_parser.add_argument('-mobility_mode', '--m', metavar="M", type=int, default = 0, help='Mobility operation. 0 is distance based gathering. 1 is table based gathering. 2 is table and distance based pushing.')
arg_parser.add_argument('-infection_mode', '--i', metavar='I', type=int, default = 0, help='The type of infection module to use. 0 ignores infection, otherwise infection is used.')
arg_parser.add_argument('--f', metavar="F", type=str, default = '', help='Simulation file.')
arg_parser.add_argument('--s', metavar="S", type=int, default = None, help='Simulation Seed.')
arg_parser.add_argument('--b', metavar="B", type=str, default = 'DataInput/beta_history/bh.csv', help='Estimated beta history input file (.csv)')
arg_parser.add_argument('--o', metavar="O", type=str, default = 'output_logs/beta_history/bh_output.csv', help='Estimated beta history output file (.csv)')
arg_parser.add_argument('--v', metavar="V", type=str, default = 'DataInput/vaccine_data.csv', help='Number of vaccinated people each day (.csv)')
arg_parser.add_argument('--r', metavar="R", type=str, default = 'DataInput/infection_input.csv', help='Number of infected people each day (.csv)')
args = vars(arg_parser.parse_args())


FixedRandom()


'''
Data Loading stuff
'''

if 'f' in args:
    environment_path = args['f']
else:
    raise Exception('Environment path missing. Use "python run_baseline.py -f <environment_file>.json."')

env_graph = generate_EnvironmentGraph(environment_path)
social_table_path = 'DataInput\Isolation_01_Mar_2020_To_20_Jan_2021\PortoAlegre_Isolation_01Mar2020_20Jan2021_semicolon_avg_extended.csv'

# This is to load real contagion data.

# Load (calibrated) beta history file
print('Beta history will be read from file: ', args['b'])

betaHistory = list()
dayHistory = list()
errorHistory = list()
gammaHistory = list()
try:
	betaHistoryReader = open(args['b'], "r")
	line = betaHistoryReader.readline()
	historyLines = betaHistoryReader.readlines()
	for line in historyLines:
		s = line.split(";")
		d = int(s[0])
		b = float(s[1])
		g = float(s[2])
		e = float(s[3])
		dayHistory.append(d)
		betaHistory.append(b)
		gammaHistory.append(g)
		errorHistory.append(e)
except Exception:
	print('Beta history file not found. Will now estimate beta from start.')

print(f'beta history size: {len(betaHistory)}')

# Load real contagion data
print("Loading real contagion data...")
inputRealData = open(args['r'], "r")
expectedI = []
for expI in inputRealData:
	expectedI.append(int(expI))

print("Number of days in infection data:", len(expectedI))
nrDaysInData = len(expectedI)

# Load real vaccine data
print('Vaccination history will be read from file: ', args['v'])
inputVaccineData = open(args['v'], "r")
vaccine_data = list()
for v in inputVaccineData:
	vaccine_data.append(v)

print("Number of days in vaccine data:", len(vaccine_data))

'''
Parameters
'''
#how many steps each day has
days = 407
day_duration = 24
env_graph.routine_day_length = day_duration
beta_search = 20

## how many steps to run for, days * day_duration
simulation_steps = days * day_duration

starting_date = datetime.date.fromisoformat('2020-03-01')
vaccine_date = datetime.date.fromisoformat('2020-03-02')
#vaccine_date = datetime.date.fromisoformat('2021-01-19')
vaccination_multiplier = 1

'''
Load Plugins Examples
'''
###infection plugin
# infection mode 0 skips infection
if args['i'] != 0:
    inf_plugin = InfectionVaccinePlugin(env_graph, use_infect_move_pop=True, day_length = day_duration)
    inf_plugin.home_density, inf_plugin.bus_density, inf_plugin.home_density, inf_plugin.bus_density = 1, 1, 1.0, 1.0
    env_graph.LoadPlugin(inf_plugin)
    vaccine_values = {'node': 'healthcare',
					  'region_list' : env_graph.region_list,
					  'nu': 1,
					  'quantity': 0,
					  'population_template': PopTemplate()}
    vaccinate = TimeAction('vaccinate', vaccine_values)
    infect_values = { 'region_list' : env_graph.region_list,
					  'population_template': PopTemplate()}
    infect_city = TimeAction('infect_population', infect_values)


if args['m'] == 0:
    gather_pop = GatherPopulationPlugin(env_graph, isolation_rate = 0.8)
    gather_pop.iso_mode = 'quantity_correction'
    env_graph.LoadPlugin(gather_pop)
elif args['m'] == 1:
    social_distance = SocialIsolationPlugin(env_graph, social_table_path)
    social_distance.day_cycle = day_duration
    social_distance.iso_mode = 'quantity_correction'
    env_graph.LoadPlugin(social_distance)
elif args['m'] == 2:
    social_distance = ReverseSocialIsolationPlugin(env_graph, social_table_path, isolation_rate = 0.2)
    social_distance.day_cycle = day_duration
    social_distance.iso_mode = 'regular'
    env_graph.LoadPlugin(social_distance)
elif args['m'] == 3:
    walk = LevyWalkPlugin(env_graph)
    walk.distribution_scale = 100
    walk.distribution_location = 0
    walk.mobility_scale = 100
    env_graph.LoadPlugin(walk)
elif args['m'] == 4:
    walk = LevyWalkPlugin(env_graph)
    walk.distribution_scale = 50
    walk.distribution_location = 0
    walk.mobility_scale = 10
    walk.levy_probability = 0.2
    env_graph.LoadPlugin(walk)

    social_distance = ReverseSocialIsolationPlugin(env_graph, '', isolation_rate = 0.3)
    social_distance.day_cycle = day_duration
    social_distance.iso_mode = 'regular'
    env_graph.LoadPlugin(social_distance)


return_plugin = ReturnPopulationPlugin(env_graph)
env_graph.LoadPlugin(return_plugin)


'''
Logging
'''
basename = environment_path.split('\\')[-1].split('.')[0]

if args['i'] != 0:
    logger = SimulationLogger(f'{basename}-i{str(args["i"])}-m{str(args["m"])}', day_duration)
else:
    logger = SimulationLogger(f'{basename}-m{str(args["m"])}', day_duration)

logger.set_to_record('global')
logger.set_to_record('neighbourhood')

pop_temp = PopTemplate()
logger.pop_template = pop_temp

try:
	betaWriterPath = args['o']
	print("Writing beta to:", betaWriterPath)
	betaHistoryWriter = open(betaWriterPath, "w")
	betaHistoryWriter.write("day; bestBeta; bestGamma; Error; expTotalInf; simTotalInf; totalVac\n")
except Exception:
	print('Has to indicate valid output file and path. Use -o <filename> command line argument.')


'''
Simulation
'''
pop_template_suc = PopTemplate()
pop_template_suc.add_block('susceptible')
pop_template_inf = PopTemplate()
pop_template_inf.add_block('infected')
pop_template_rem = PopTemplate()
pop_template_rem.add_block('removed')
pop_template_vac = PopTemplate()
pop_template_vac.add_block('vaccinated')

t = time.time()

for i in range(simulation_steps):
    hour = i % day_duration
    day = int(i/day_duration)
    current_date = starting_date + datetime.timedelta(day)

    print(f'step:{i}\thour:{hour}\tday:{day}')

    if current_date >= vaccine_date and hour == 0 and len(vaccine_data) > 0:
        print("Começo de vacinação!")
        
        vaccine_quantity = int(vaccine_data.pop(0))
        print(f'vaccination_multiplier: {vaccination_multiplier}')
        vaccine_values['quantity'] = int(vaccine_quantity * vaccination_multiplier)
        print(f'vaccinate {vaccine_quantity} individuals.')
        
        print(f'Antes da vacinação:\nS:{env_graph.get_population_size(pop_template_suc)}')
        env_graph.consume_time_action(vaccinate, hour, i)
        print(f'Depois da vacinação:\nS:{env_graph.get_population_size(pop_template_suc)}')
        print(f'Total vacinado: {env_graph.total_vaccinated}')

    # Get estimated beta and gamma for today:
    if hour == 0:
        if len(betaHistory) > 0:
            inf_plugin.beta = betaHistory.pop(0)
            inf_plugin.gamma = gammaHistory.pop(0)
            error = errorHistory.pop(0)
            print(f'Read previously estimated beta ({inf_plugin.beta}) and gamma ({inf_plugin.gamma}).')
        else:
            error = EstimateBetaForToday(i, beta_search)
            print(f'Estimated values for beta ({inf_plugin.beta}) and gamma ({inf_plugin.gamma}).')

    betaHistoryWriter.write(f'{day}; {inf_plugin.beta}; {inf_plugin.gamma}; {error}; {expectedI[day]}; {inf_plugin.total_infected}; {inf_plugin.vaccinated}\n')
	# Routine/Repeating Global Action Invoke example
    # Updates Node Routines and Repeating Global Actions
    # These are defined in the input environment descriptor
    # print(f'{sum([region.get_population_size() for region in
    # env_graph.region_list])}\n\n') no one gets lost
    env_graph.update_time_step(hour, i)

    # records frame I data
    logger.record_frame(env_graph, i)


print(time.time() - t)

'''
Logging
# '''

logger.close()