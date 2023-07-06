$procs = $(
Start-Process python ".\TOMACS_simulation.py --e epidemic_nb_tests/R0-2.6-VaccA-Mov100" -PassThru;
Start-Process python ".\TOMACS_simulation.py --e epidemic_nb_tests/R0-2.6-VaccB-Mov100" -PassThru;
Start-Process python ".\TOMACS_simulation.py --e epidemic_nb_tests/R0-2.6-VaccC-Mov100" -PassThru;
Start-Process python ".\TOMACS_simulation.py --e epidemic_nb_tests/R0-2.6-VaccD-Mov100" -PassThru;
Start-Process python ".\TOMACS_simulation.py --e epidemic_nb_tests/R0-2.6-VaccE-Mov100" -PassThru;
Start-Process python ".\TOMACS_simulation.py --e epidemic_nb_tests/R0-2.6-VaccF-Mov100" -PassThru;)

$procs | Wait-Process
cd misc_scripts

python .\experiment_global_population.py --p epidemic_nb_tests --e R0-2.6-VaccA-Mov100 --c Susceptible Infected Removed
python .\experiment_global_population.py --p epidemic_nb_tests --e R0-2.6-VaccB-Mov100 --c Susceptible Infected Removed
python .\experiment_global_population.py --p epidemic_nb_tests --e R0-2.6-VaccC-Mov100 --c Susceptible Infected Removed
python .\experiment_global_population.py --p epidemic_nb_tests --e R0-2.6-VaccD-Mov100 --c Susceptible Infected Removed
python .\experiment_global_population.py --p epidemic_nb_tests --e R0-2.6-VaccE-Mov100 --c Susceptible Infected Removed
python .\experiment_global_population.py --p epidemic_nb_tests --e R0-2.6-VaccF-Mov100 --c Susceptible Infected Removed

python .\experiment_infection_sum.py --p epidemic_nb_tests --e R0-2.6-VaccA-Mov100 
python .\experiment_infection_sum.py --p epidemic_nb_tests --e R0-2.6-VaccB-Mov100 
python .\experiment_infection_sum.py --p epidemic_nb_tests --e R0-2.6-VaccC-Mov100 
python .\experiment_infection_sum.py --p epidemic_nb_tests --e R0-2.6-VaccD-Mov100 
python .\experiment_infection_sum.py --p epidemic_nb_tests --e R0-2.6-VaccE-Mov100 
python .\experiment_infection_sum.py --p epidemic_nb_tests --e R0-2.6-VaccF-Mov100 

python .\infection_sum_comparison.py --p epidemic_nb_tests --e R0-2.6-VaccA-Mov100 R0-2.6-VaccB-Mov100 R0-2.6-VaccC-Mov100 R0-2.6-VaccD-Mov100 R0-2.6-VaccE-Mov100 R0-2.6-VaccF-Mov100 --s 0 --x "Time / Simulation Days" --y "Total Infected Population"

# python .\infection_sum_comparison.py --p epidemic_nb_tests --e R0-2.6 R0-2.6-VaccA-Mov100 R0-2.6-VaccB-Mov100 R0-2.6-VaccC-Mov100 R0-2.6-VaccD-Mov100 --s 0 --x "Simulation Cycle (Day)" --y "Cumulative Infected Population" --l "Baseline" "VaccinationA" "VaccinationB" "VaccinationC" "VaccinationD"

# python .\infection_sum_comparison.py --p epidemic_nb_tests --e R0-2.6 R0-2.6-VaccA-Mov100 R0-2.6-VaccB-Mov100 R0-2.6-VaccC-Mov100 R0-2.6-VaccD-Mov100 R0-2.6-Mov25 R0-2.6-VaccA-Mov25 R0-2.6-VaccB-Mov25 R0-2.6-VaccC-Mov25 R0-2.6-VaccD-Mov25 --s 0 --x "Simulation Cycle (Day)" --y "Cumulative Infected Population" 

# python .\infection_sum_comparison.py --p epidemic_nb_tests --e R0-2.6 R0-2.6-VaccA-Mov100 R0-2.6-VaccB-Mov100 R0-2.6-Mov50 R0-2.6-VaccA-Mov50 R0-2.6-VaccB-Mov50 R0-2.6-Mov25 R0-2.6-VaccA-Mov25 R0-2.6-VaccB-Mov25 --s 0 --x "Simulation Cycle (Day)" --y "Cumulative Infected Population" 

# python .\infection_sum_comparison.py --p epidemic_nb_tests --e R0-2.6 R0-2.6-Mov50 R0-2.6-Mov25 R0-2.6-VaccC-Mov100 R0-2.6-VaccC-Mov50 R0-2.6-VaccC-Mov25 --s 0 --x "Simulation Cycle (Day)" --y "Cumulative Infected Population" --l "Baseline" "Restriction = 0.5" "Restriction = 0.75" "VaccC" "VaccC + Restr = 0.5" "VaccC + Restr = 0.75" 

Read-Host -Prompt "Press Enter to continue"
