#encoding: utf-8
'''
without config:
python simulator.py --i 3 --s 2 --f .\DataInput\Push_94_P0Centro_3cpd.json

with config (default config.json file)
python simulator.py --i 3 --s 2

with config (arbitrary filename.json)
python simulator.py --i 3 --s 2 --conf filename.json

'''
import sys
sys.path.append('./Plugins/')
import winsound

import argparse

import environment
from util import *
from data_parse_util import *
import population

import io
import copy
import gc
import pickle
import numpy as np
import time
import datetime

from AgentBasedPlugin import AgentBasedPlugin
from PlaySoccerPlugin import PlaySoccerPlugin
#from VaccinePlugin import VaccinePlugin
from InfectionPlugin import InfectionPlugin
from SocialIsolationPlugin import SocialIsolationPlugin
from GatherPopulationPlugin import GatherPopulationPlugin
from ReverseSocialIsolationPlugin import ReverseSocialIsolationPlugin

from Loggers.population_count_logger import PopulationCountLogger
import new_random
import random
from config_module import config

def ComputeErrorForToday(_gamma, _beta, _step):
	testGamma = _gamma

	#_test_env = copy.deepcopy(env_graph)
	with open(snapName, "rb") as input_file:
		print("Reading simulation snapshot...", snapName)
		_test_env = pickle.load(input_file)

	useRandom = copy.deepcopy(envRandom)
	new_random.new_random.set_random_instance(useRandom, "useRandom")

	susceptible = _test_env.get_population_size(pop_template_suc)
	print("(before)currS: %d - expS[%d]: %d" % (susceptible, day, expectedI[day]))
	infected = _test_env.total_infected
	print("(before)Infected: %d - expS[%d]: %d" % (infected, day, expectedI[day]))
	vaccinated = _test_env.total_vaccinated
	print("(before)Vaccinated: %d - expS[%d]: %d" % (vaccinated, day, expectedI[day]))

	# Set testBeta
	test_inf = InfectionPlugin(_test_env, infect_mode=args['i'], use_infect_move_pop=config.use_infect_move_pop)
	test_inf.day_length = config.day_duration

	test_inf.gamma = testGamma
	test_inf.beta = _beta
	_test_env.LoadPlugin(test_inf)

	for event in range(config.day_duration):
		_test_env.update_time_step(event, _step + event)

	susceptible = _test_env.get_population_size(pop_template_suc)
	print("(after)currS: %d - expS[%d]: %d" % (susceptible, day, expectedI[day]))
	infected = _test_env.total_infected
	print("(after)Infected: %d - expS[%d]: %d" % (infected, day, expectedI[day]))
	vaccinated = _test_env.total_vaccinated
	print("(after)Vaccinated: %d - expS[%d]: %d" % (vaccinated, day, expectedI[day]))

	#error = susceptible - expectedS[day]
	error = infected - expectedI[day]
	_sqrError = error * error
	del _test_env
	del test_inf
	gc.collect()
	new_random.new_random.set_random_instance(envRandom, "envRandom")

	return _sqrError

#config.LoadConfigFile('config.json')
#config.SaveConfigFile("config.json")
#input("file saved!")



startTime = time.time()
print("Start time:", startTime)

arg_parser = argparse.ArgumentParser(description="Population Dynamics Simulation.")
arg_parser.add_argument('-infection_mode', '--i', metavar='I', type=int, default = 0, help='The type of infection module to use. 0 is rate based, 1 is day based.')
arg_parser.add_argument('-isolation_mode', '--s', metavar="S", type=int, default = 0, help='Social isolation. Reduces movement according to a table. 0 is no social isolation. 1 is table based social isolation.')
arg_parser.add_argument('--f', metavar="F", type=str, default = '', help='Simulation file.')
arg_parser.add_argument('--b', metavar="B", type=str, default = '', help='Estimated beta history file (.csv)')
arg_parser.add_argument('-occupation', '--oc', metavar="OC", type=float, default = 0, help='Occupation of the stadium for the soccer match. Zero stands for empty stadium, and 1 stands for full stadium.')
arg_parser.add_argument('--conf', metavar="C", type=str, default = 'config.json', help='Configuration file.')
args = vars(arg_parser.parse_args())

print(args)

if 'conf' in args:
	config.LoadConfigFile(args['conf'])
	print("loaded config file:", args['conf'])


nr_days = datetime.date.fromisoformat('2021-04-12') - config.vaccine_date
end_date = config.starting_date + datetime.timedelta(config.simulation_days)
black_flag_date = datetime.date.fromisoformat('2021-02-27')
matchDate = datetime.date.fromisoformat('2020-09-16')
print("start date:", config.starting_date.isoformat())
print("Number of days:", config.simulation_days)
print("vaccine date:", config.vaccine_date.isoformat())
print("end date:", end_date.isoformat())
print("black flag date:", black_flag_date)
black_flag_day = black_flag_date - config.starting_date
print("black flag day:", black_flag_day)
match_day = matchDate - config.starting_date
print("match day:", match_day)
october_1st = datetime.date.fromisoformat('2020-10-01') - config.starting_date
print("october 1st:", october_1st)
#input("press key!")

'''
Parameters
'''

print("Random seed:", config.randomSeed)
envRandom = random.Random()
envRandom.seed(config.randomSeed)
matchRandom = random.Random()
matchSeed = int(time.time())
print("matchSeed:", matchSeed)
matchRandom.seed(matchSeed)

#new_random.new_random.start_log()
new_random.new_random.set_random_instance(envRandom, "envRandom")
new_random.new_random.set_seed(config.randomSeed)


'''
fazer:
-> gamma = 1 / (14*24) -> result: contagio gigante, explodiu o sistema
-> Recalcular beta: 
	-> computar gamma para cada beta, considerando Rx = 1,67
	-> computar gamma para cada beta, considerando Rx variando conforme site: https://wp.ufpel.edu.br/fentransporte/2020/04/09/a-evolucao-epidemica-do-covid-19-modelo
'''

if config.compute_gamma_Rx:
	print("Use compute gamma from Rx!")
else:
	print("Do not compute gamma from Rx!")

'''
Data Loading stuff
'''

env_graph = generate_EnvironmentGraph(config.environment_path)
print(config.social_table_path)

# This is to load real contagion data.
# The model will then try to follow these numbers adjusting beta for each day.

print('Beta history will be read from file: ', config.beta_history_input_file)

betaHistory = list()
dayHistory = list()
errorHistory = list()
gammaHistory = list()
try:
	betaHistoryReader = open(config.beta_history_input_file, "r")
	line = betaHistoryReader.readline()
	historyLines = betaHistoryReader.readlines()
	for line in historyLines:
		s = line.split(";")
		d = int(s[0])
		v = float(s[1])
		g = float(s[2])
		e = float(s[3])
		dayHistory.append(d)
		betaHistory.append(v)
		gammaHistory.append(g)
		errorHistory.append(e)
except Exception:
	print('Beta history file not found. Will now estimated beta from start.')

'''
Load Plugins
'''
###infection plugin
# infection mode 2 skips infection
if args['i'] != 2:
	inf_plugin = InfectionPlugin(env_graph, infect_mode=args['i'], use_infect_move_pop=config.use_infect_move_pop, default_beta=0.0, default_gamma=config.gamma)
	inf_plugin.day_length = config.day_duration
	inf_plugin.home_density = 1.0
	inf_plugin.bus_density = 1.0
	inf_plugin.gamma = config.gamma
	env_graph.LoadPlugin(inf_plugin)
	vaccine_values = {'node': 'healthcare',
					  'region_list' : env_graph.region_list,
					  'nu': config.nu,
					  'quantity': config.vaccination_amount,
					  'population_template': PopTemplate()}
	vaccinate = TimeAction('vaccinate', vaccine_values)
	infect_values = { 'region_list' : env_graph.region_list,
					  'population_template': PopTemplate()}
	infect_city = TimeAction('infect_population', infect_values)

if args['s'] == 0:
	gather_pop = GatherPopulationPlugin(env_graph, isolation_rate = 0.8)
	gather_pop.isolation_mode = 'quantity_correction'
	env_graph.LoadPlugin(gather_pop)
elif args['s'] == 1:
	social_distance = SocialIsolationPlugin(env_graph, config.social_table_path)
	social_distance.day_cycle = config.day_duration
	social_distance.iso_mode = 'quantity_correction'
	env_graph.LoadPlugin(social_distance)
elif args['s'] == 2:
	social_distance = ReverseSocialIsolationPlugin(env_graph, config.social_table_path, isolation_rate=config.isolation_rate)
	social_distance.day_cycle = config.day_duration
	social_distance.iso_mode = 'regular'
	env_graph.LoadPlugin(social_distance)

'''
		SOCCER GAME
'''
soccer = PlaySoccerPlugin(env_graph, isolation_rate = 0.0)
soccer.iso_mode = 'regular'
env_graph.LoadPlugin(soccer)

jogar_futebol = TimeAction('play_soccer', config.soccer_values)


'''
Logging
'''
basename = config.environment_path.split('/')[-1].split('.')[0]
argsName = ''
for arg, val in args.items():
	argsName = argsName + '-' + arg + str(val)
filename = f'{config.basename}{argsName}'
logger = PopulationCountLogger(f'{config.basename}-infection_data-i{str(args["i"])}-s{str(args["s"])}', config.day_duration)

logger.set_data_to_record('global')
logger.set_data_to_record('neighbourhood')
#logger.set_to_record('graph')

betaWriterPath = config.beta_history_output_file
print("Writing beta to:", betaWriterPath)
betaHistoryWriter = open(betaWriterPath, "w")
betaHistoryWriter.write("day; bestBeta; gamma; sqrError; matchSeed; expTotalInf; simTotalInf; staticTotalInf; staticTotalVac\n")

'''
Simulation
'''
pop_template_suc = PopTemplate()
pop_template_suc.add_block('susceptible')
pop_template_inf = PopTemplate()
pop_template_inf.add_block('infected')
pop_template_rem = PopTemplate()
pop_template_rem.add_block('removed')

S = env_graph.get_population_size(pop_template_suc)
I = env_graph.get_population_size(pop_template_inf)
R = env_graph.get_population_size(pop_template_rem)
N0 = S + I + R

print("N0:", N0, " S:", S, " I:", I, " R:", R)

# Load real contagion data
N = N0
expectedI = list()
inputRealData = open(config.infection_data_file, "r")
expectedS = list()
for expI in inputRealData:
	expectedI.append(int(expI))
	N = N0 - int(expI)
	expectedS.append(N)

print("Number of days in infection data:", len(expectedS))
nrDaysInData = len(expectedS)

# Load real vaccine data
inputVaccineData = open(config.vaccine_data_file, "r")
vaccine_data = list()
for v in inputVaccineData:
	vaccine_data.append(v)

print("Number of days in vaccine data:", len(vaccine_data))

print(f'Begin simulation of {config.simulation_days} days!')
for i in range(config.simulation_steps):

	day = int(i / config.day_duration)
	current_date = config.starting_date + datetime.timedelta(day)
	hour = i % config.day_duration
	print(f'date:{current_date.isoformat()}\thour: {hour}\tstep: {i}')

	if config.vaccinate and current_date >= config.vaccine_date and hour == 0 and len(vaccine_data) > 0:
		print("Começo de vacinação!")

		new_quantity = int(vaccine_data.pop(0))
		print(f'vaccination_multiplier: {config.vaccination_multiplier}')
		vaccine_values['quantity'] = int(new_quantity * config.vaccination_multiplier)
		print(f'vaccinate {new_quantity} individuals.')
		print(f'Antes da vacinação:\nS:{env_graph.get_population_size(pop_template_suc)}')
		env_graph.consume_time_action(vaccinate, hour, i)
		print(f'Depois da vacinação:\nS:{env_graph.get_population_size(pop_template_suc)}')
		print(f'Total vacinado: {env_graph.total_vaccinated}')
		#input("press key!")

	#print("Gamma:", inf_plugin.gamma)
	# Estimate bestBeta
	if((hour == 0) and (day < len(expectedS))):
		minError = sys.float_info.max
		bestBeta = 0.0
		index = day

		if(len(betaHistory) > 0):
			print("Read precomputed beta")
			bestBeta = betaHistory.pop(0)
			bestGamma = gammaHistory.pop(0)
			print("bestGamma:", bestGamma)
			minError = errorHistory.pop(0)
		elif(len(betaHistory) <= 0):
			print("Estimate beta!\n")
			snapName = f'snap_{config.basename}.pickle'
			with open(snapName, "wb") as output_file:
				print("Generating snapshot of simulation.", snapName)
				pickle.dump(env_graph, output_file)


			print("Entering beta search loop...")
			bestGamma = config.gamma
			maxBeta = 1.0
			minBeta = 0.0
			oldMinBeta = -1.0
			oldMidBeta = -1.0
			oldMaxBeta = -1.0
			oldMinBetaError = sys.float_info.max
			oldMidBetaError = sys.float_info.max
			oldMaxBetaError = sys.float_info.max
			for x in config.beta_search:
				midBeta = (maxBeta + minBeta) / 2

				print("minBeta: ", minBeta)
				print("midBeta: ", midBeta)
				print("maxBeta: ", maxBeta)

				if(minBeta == oldMinBeta):
					sqrMinError = oldMinBetaError
				elif(minBeta == oldMidBeta):
					sqrMinError = oldMidBetaError
				else:
					sqrMinError = ComputeErrorForToday(config.gamma, minBeta, i)

				oldMinBeta = minBeta
				oldMinBetaError = sqrMinError
				print("sqrMinError: ", sqrMinError)
				if(sqrMinError == 0):
					minError = sqrMinError
					bestBeta = minBeta
					break

				if(maxBeta == oldMaxBeta):
					sqrMaxError = oldMaxBetaError
				elif(maxBeta == oldMidBeta):
					sqrMaxError = oldMidBetaError
				else:
					sqrMaxError = ComputeErrorForToday(config.gamma, maxBeta, i)

				oldMaxBeta = maxBeta
				oldMaxBetaError = sqrMaxError
				print("sqrMaxError: ", sqrMaxError)
				if(sqrMaxError == 0):
					minError = sqrMaxError
					bestBeta = maxBeta
					break

				sqrMidError = ComputeErrorForToday(config.gamma, midBeta, i)
				oldMidBeta = midBeta
				oldMidBetaError = sqrMidError
				print("sqrMidError: ", sqrMidError)
				if(sqrMidError == 0):
					minError = sqrMidError
					bestBeta = midBeta
					break

				if(minError > sqrMinError):
					minError = sqrMinError
					bestBeta = minBeta
					print("best minBeta!")
				if(minError > sqrMidError):
					minError = sqrMidError
					bestBeta = midBeta
					print("best midBeta!")
				if(minError > sqrMaxError):
					minError = sqrMaxError
					bestBeta = maxBeta
					print("best maxBeta!")

				if(sqrMinError >= sqrMidError) and (sqrMinError >= sqrMaxError):
					minBeta = midBeta
				if(sqrMaxError >= sqrMidError) and (sqrMaxError >= sqrMinError):
					maxBeta = midBeta
				if(maxBeta == minBeta):
					print("maxBeta and minBeta are the same!")
					print("bestBeta:", bestBeta)
					#input("break!")
					break

				#input("test")

			print(" ... finish!")

		# Save bestBeta and Error
		currS = env_graph.get_population_size(pop_template_suc)
		expTotalInf = N0 - expectedS[day]
		simTotalInf = N0 - currS
		print("minError:%f \t bestBeta:%f" % (minError, bestBeta))
		# Set bestBeta in simulation
		inf_plugin.beta = bestBeta
		if config.compute_gamma_Rx == True:
			inf_plugin.gamma = bestBeta / config.Rx
		else:
			inf_plugin.gamma = bestGamma
		env_graph.LoadPlugin(inf_plugin)

		betaHistoryWriter.write("%d; %f; %f; %f; %d; %d; %d; %d; %d\n" % (day, bestBeta, inf_plugin.gamma, minError, matchSeed, expTotalInf, simTotalInf, env_graph.total_infected, env_graph.total_vaccinated))


	'''
	for y in range(5):
		print(useRandom.random(), end=" ")
		print("-----")
	'''

	old_beta = 0.0
	# Vai pro jogo
	if(day==config.match_day and hour == config.match_start_time):
		print("Vai pro jogo!")
		#matchRandom = copy.deepcopy(envRandom)
		new_random.new_random.set_random_instance(matchRandom, "matchRandom")
		old_beta = inf_plugin.beta
		inf_plugin.beta = 1.0
		#input("pressione uma tecla!")
		env_graph.consume_time_action(jogar_futebol, hour, i)
		inf_plugin.beta = old_beta
		env_graph.LoadPlugin(inf_plugin)
		new_random.new_random.set_random_instance(envRandom, "envRandom")

	# Simulate with last estimated beta
	env_graph.update_time_step(hour, i)

	if current_date > datetime.date.fromisoformat('2021-02-27'):
		env_graph.consume_time_action(infect_city, hour, i)
	
	# durante o jogo
	if(day==config.match_day and hour >= config.match_start_time and hour <= config.match_end_time):
		print("Jogando futebol e torcendo!")
		#matchRandom = copy.deepcopy(envRandom)
		new_random.new_random.set_random_instance(matchRandom, "matchRandom")
		old_beta = inf_plugin.beta
		inf_plugin.beta = 1.0
		#input("pressione uma tecla!")
		inf_stadium_values = {'region': config.match_region, 'node': 'stadium', 'beta' : 1.0, 'gamma' : inf_plugin.gamma, 'mu' : 0.0, 'nu' : 0.0, 'population_template': PopTemplate()}
		infectar_no_estadio = TimeAction('infect', inf_stadium_values)
		env_graph.consume_time_action(infectar_no_estadio, hour, i)
		inf_plugin.beta = old_beta
		new_random.new_random.set_random_instance(envRandom, "envRandom")
		print("done!")


	# Volta do jogo
	if(day==config.match_day and hour == config.match_end_time):
		print("Volta do jogo!")
		#matchRandom = copy.deepcopy(envRandom)
		new_random.new_random.set_random_instance(matchRandom, "matchRandom")
		old_beta = inf_plugin.beta
		inf_plugin.beta = 1.0
		#input("pressione uma tecla!")
		for region in env_graph.region_list:
			return_values = {'region': region.name, 'node':'home', 'population_template':PopTemplate()}
			return_action = TimeAction('return_population_home', return_values)
			env_graph.consume_time_action(return_action, config.match_end_time, config.day_duration*config.match_day + config.match_end_time)

		inf_plugin.beta = old_beta
		new_random.new_random.set_random_instance(envRandom, "envRandom")

	logger.log_simulation_step(env_graph, i)


'''
Logging
'''

logger.close()

frequency = 2500  # Set Frequency To 2500 Hertz
duration = 1000  # Set Duration To 1000 ms == 1 second
#winsound.Beep(frequency, duration)

endTime = time.time()
print("Start time:", startTime)
print("End time:", endTime)
print("Time elapsed:", endTime - startTime)
