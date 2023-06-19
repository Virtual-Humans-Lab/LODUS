$procs = $(
Start-Process python ".\TOMACS_simulation.py --e epidemic_tests/R0-2.6-Mov50" -PassThru;
Start-Process python ".\TOMACS_simulation.py --e epidemic_tests/R0-2.6-VaccA-Mov50" -PassThru;
Start-Process python ".\TOMACS_simulation.py --e epidemic_tests/R0-2.6-VaccB-Mov50" -PassThru;
Start-Process python ".\TOMACS_simulation.py --e epidemic_tests/R0-2.6-VaccC-Mov50" -PassThru;
Start-Process python ".\TOMACS_simulation.py --e epidemic_tests/R0-2.6-VaccD-Mov50" -PassThru;
Start-Process python ".\TOMACS_simulation.py --e epidemic_tests/R0-2.6-VaccE-Mov50" -PassThru;;
Start-Process python ".\TOMACS_simulation.py --e epidemic_tests/R0-2.6-VaccF-Mov50" -PassThru;)

$procs | Wait-Process
cd misc_scripts

python .\experiment_global_population.py --p epidemic_tests --e R0-2.6-VaccA-Mov50 --c Susceptible Infected Removed
python .\experiment_global_population.py --p epidemic_tests --e R0-2.6-VaccB-Mov50 --c Susceptible Infected Removed
python .\experiment_global_population.py --p epidemic_tests --e R0-2.6-VaccC-Mov50 --c Susceptible Infected Removed

python .\experiment_infection_sum.py --p epidemic_tests --e R0-2.6-VaccA-Mov50
python .\experiment_infection_sum.py --p epidemic_tests --e R0-2.6-VaccB-Mov50
python .\experiment_infection_sum.py --p epidemic_tests --e R0-2.6-VaccC-Mov50


Read-Host -Prompt "Press Enter to continue"
