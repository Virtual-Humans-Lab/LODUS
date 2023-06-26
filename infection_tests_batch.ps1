$procs = $(
Start-Process python ".\TOMACS_simulation.py --e infection_tests/R0-2.6" -PassThru;
Start-Process python ".\TOMACS_simulation.py --e infection_tests/R0-3.07" -PassThru;
Start-Process python ".\TOMACS_simulation.py --e infection_tests/R0-6.0" -PassThru;)

$procs | Wait-Process
cd misc_scripts

python .\experiment_global_population.py --p infection_tests --e R0-2.6 --c Susceptible Infected Removed
python .\experiment_global_population.py --p infection_tests --e R0-3.07 --c Susceptible Infected Removed
python .\experiment_global_population.py --p infection_tests --e R0-6.0 --c Susceptible Infected Removed
python .\experiment_infection_sum.py --p infection_tests --e R0-2.6
python .\experiment_infection_sum.py --p infection_tests --e R0-3.07
python .\experiment_infection_sum.py --p infection_tests --e R0-6.0

python .\infection_sum_comparison.py --p infection_tests --e R0-2.6 R0-3.07 R0-6.0

Read-Host -Prompt "Press Enter to continue"
