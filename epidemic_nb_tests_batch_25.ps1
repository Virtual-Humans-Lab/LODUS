$procs = $(
Start-Process python ".\TOMACS_simulation.py --e epidemic_nb_tests/R0-2.6-Mov25" -PassThru;
Start-Process python ".\TOMACS_simulation.py --e epidemic_nb_tests/R0-2.6-VaccA-Mov25" -PassThru;
Start-Process python ".\TOMACS_simulation.py --e epidemic_nb_tests/R0-2.6-VaccB-Mov25" -PassThru;
Start-Process python ".\TOMACS_simulation.py --e epidemic_nb_tests/R0-2.6-VaccC-Mov25" -PassThru;;
Start-Process python ".\TOMACS_simulation.py --e epidemic_nb_tests/R0-2.6-VaccD-Mov25" -PassThru;;
Start-Process python ".\TOMACS_simulation.py --e epidemic_nb_tests/R0-2.6-VaccE-Mov25" -PassThru;;
Start-Process python ".\TOMACS_simulation.py --e epidemic_nb_tests/R0-2.6-VaccF-Mov25" -PassThru;)

$procs | Wait-Process
cd misc_scripts

python .\experiment_global_population.py --p epidemic_nb_tests --e R0-2.6-VaccA-Mov25 --c Susceptible Infected Removed
python .\experiment_global_population.py --p epidemic_nb_tests --e R0-2.6-VaccB-Mov25 --c Susceptible Infected Removed
python .\experiment_global_population.py --p epidemic_nb_tests --e R0-2.6-VaccC-Mov25 --c Susceptible Infected Removed
python .\experiment_global_population.py --p epidemic_nb_tests --e R0-2.6-VaccD-Mov25 --c Susceptible Infected Removed
python .\experiment_global_population.py --p epidemic_nb_tests --e R0-2.6-VaccE-Mov25 --c Susceptible Infected Removed
python .\experiment_global_population.py --p epidemic_nb_tests --e R0-2.6-VaccF-Mov25 --c Susceptible Infected Removed

python .\experiment_infection_sum.py --p epidemic_nb_tests --e R0-2.6-VaccA-Mov25
python .\experiment_infection_sum.py --p epidemic_nb_tests --e R0-2.6-VaccB-Mov25
python .\experiment_infection_sum.py --p epidemic_nb_tests --e R0-2.6-VaccC-Mov25
python .\experiment_infection_sum.py --p epidemic_nb_tests --e R0-2.6-VaccD-Mov25
python .\experiment_infection_sum.py --p epidemic_nb_tests --e R0-2.6-VaccE-Mov25
python .\experiment_infection_sum.py --p epidemic_nb_tests --e R0-2.6-VaccF-Mov25

python .\infection_sum_comparison.py --p epidemic_nb_tests --e R0-2.6-Mov25 R0-2.6-VaccA-Mov25 R0-2.6-VaccB-Mov25 R0-2.6-VaccC-Mov25 R0-2.6-VaccD-Mov25 R0-2.6-VaccE-Mov25 R0-2.6-VaccF-Mov25 --s 0 --x "Time / Simulation Days" --y "Total Infected Population"



Read-Host -Prompt "Press Enter to continue"
