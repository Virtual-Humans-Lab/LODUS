$procs = $(
Start-Process python ".\TOMACS_simulation.py --e infection_tests/R0-2.6" -PassThru;
Start-Process python ".\TOMACS_simulation.py --e infection_tests/R0-2.6_HI-0.3" -PassThru;
Start-Process python ".\TOMACS_simulation.py --e infection_tests/R0-2.6_HI-0.5" -PassThru;
Start-Process python ".\TOMACS_simulation.py --e infection_tests/R0-2.6_HI-0.65" -PassThru;
Start-Process python ".\TOMACS_simulation.py --e infection_tests/R0-3.07" -PassThru;
Start-Process python ".\TOMACS_simulation.py --e infection_tests/R0-3.07_HI-0.3" -PassThru;
Start-Process python ".\TOMACS_simulation.py --e infection_tests/R0-3.07_HI-0.65" -PassThru;
Start-Process python ".\TOMACS_simulation.py --e infection_tests/R0-6.0" -PassThru;
Start-Process python ".\TOMACS_simulation.py --e infection_tests/R0-6.0_HI-0.3" -PassThru;
Start-Process python ".\TOMACS_simulation.py --e infection_tests/R0-6.0_HI-0.65" -PassThru;)

$procs | Wait-Process
cd misc_scripts

python .\experiment_global_population.py --p infection_tests --e R0-2.6 --c Susceptible Infected Removed
python .\experiment_global_population.py --p infection_tests --e R0-2.6_HI-0.3 --c Susceptible Infected Removed
python .\experiment_global_population.py --p infection_tests --e R0-2.6_HI-0.65 --c Susceptible Infected Removed
python .\experiment_global_population.py --p infection_tests --e R0-3.07 --c Susceptible Infected Removed
python .\experiment_global_population.py --p infection_tests --e R0-3.07_HI-0.3 --c Susceptible Infected Removed
python .\experiment_global_population.py --p infection_tests --e R0-3.07_HI-0.65 --c Susceptible Infected Removed
python .\experiment_global_population.py --p infection_tests --e R0-6.0 --c Susceptible Infected Removed
python .\experiment_global_population.py --p infection_tests --e R0-6.0_HI-0.3 --c Susceptible Infected Removed
python .\experiment_global_population.py --p infection_tests --e R0-6.0_HI-0.65 --c Susceptible Infected Removed

python .\experiment_infection_sum.py --p infection_tests --e R0-2.6
python .\experiment_infection_sum.py --p infection_tests --e R0-2.6_HI-0.3
python .\experiment_infection_sum.py --p infection_tests --e R0-2.6_HI-0.65
python .\experiment_infection_sum.py --p infection_tests --e R0-3.07
python .\experiment_infection_sum.py --p infection_tests --e R0-3.07_HI-0.3
python .\experiment_infection_sum.py --p infection_tests --e R0-3.07_HI-0.65
python .\experiment_infection_sum.py --p infection_tests --e R0-6.0
python .\experiment_infection_sum.py --p infection_tests --e R0-6.0_HI-0.3
python .\experiment_infection_sum.py --p infection_tests --e R0-6.0_HI-0.65

python .\infection_sum_comparison.py --p infection_tests --e R0-2.6 R0-2.6_HI-0.3 R0-2.6_HI-0.65
python .\infection_sum_comparison.py --p infection_tests --e R0-3.07 R0-3.07_HI-0.3 R0-3.07_HI-0.65
python .\infection_sum_comparison.py --p infection_tests --e R0-6.0 R0-6.0_HI-0.3 R0-6.0_HI-0.65

python .\infection_sum_comparison.py --p infection_tests --e R0-2.6 R0-3.07 R0-6.0
python .\infection_sum_comparison.py --p infection_tests --e R0-2.6_HI-0.3 R0-3.07_HI-0.3 R0-6.0_HI-0.3
python .\infection_sum_comparison.py --p infection_tests --e R0-2.6_HI-0.65 R0-3.07_HI-0.65 R0-6.0_HI-0.65
python .\infection_sum_comparison.py --p infection_tests --e R0-2.6 R0-3.07 R0-6.0 R0-2.6_HI-0.3 R0-2.6_HI-0.5 R0-3.07_HI-0.3 R0-6.0_HI-0.3 R0-2.6_HI-0.65 R0-3.07_HI-0.65 R0-6.0_HI-0.65

Read-Host -Prompt "Press Enter to continue"
