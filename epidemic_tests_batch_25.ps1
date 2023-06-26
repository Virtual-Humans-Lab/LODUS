$procs = $(
Start-Process python ".\TOMACS_simulation.py --e epidemic_tests/R0-2.6-Mov25" -PassThru;
Start-Process python ".\TOMACS_simulation.py --e epidemic_tests/R0-2.6-VaccA-Mov25" -PassThru;
Start-Process python ".\TOMACS_simulation.py --e epidemic_tests/R0-2.6-VaccB-Mov25" -PassThru;
Start-Process python ".\TOMACS_simulation.py --e epidemic_tests/R0-2.6-VaccC-Mov25" -PassThru;;
Start-Process python ".\TOMACS_simulation.py --e epidemic_tests/R0-2.6-VaccD-Mov25" -PassThru;;
Start-Process python ".\TOMACS_simulation.py --e epidemic_tests/R0-2.6-VaccE-Mov25" -PassThru;;
Start-Process python ".\TOMACS_simulation.py --e epidemic_tests/R0-2.6-VaccF-Mov25" -PassThru;)

$procs | Wait-Process
cd misc_scripts

python .\experiment_global_population.py --p epidemic_tests --e R0-2.6-VaccA-Mov25 --c Susceptible Infected Removed
python .\experiment_global_population.py --p epidemic_tests --e R0-2.6-VaccB-Mov25 --c Susceptible Infected Removed
python .\experiment_global_population.py --p epidemic_tests --e R0-2.6-VaccC-Mov25 --c Susceptible Infected Removed

python .\experiment_infection_sum.py --p epidemic_tests --e R0-2.6-VaccA-Mov25
python .\experiment_infection_sum.py --p epidemic_tests --e R0-2.6-VaccB-Mov25
python .\experiment_infection_sum.py --p epidemic_tests --e R0-2.6-VaccC-Mov25


Read-Host -Prompt "Press Enter to continue"
