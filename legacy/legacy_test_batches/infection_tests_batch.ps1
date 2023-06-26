$procs = $(
Start-Process python ".\TOMACS_simulation.py --e infection_tests/Beta25_Mov25" -PassThru;
Start-Process python ".\TOMACS_simulation.py --e infection_tests/Beta25_Mov50" -PassThru;
Start-Process python ".\TOMACS_simulation.py --e infection_tests/Beta25_Mov75" -PassThru;
Start-Process python ".\TOMACS_simulation.py --e infection_tests/Beta25_Mov100" -PassThru;
Start-Process python ".\TOMACS_simulation.py --e infection_tests/Beta50_Mov25" -PassThru;
Start-Process python ".\TOMACS_simulation.py --e infection_tests/Beta50_Mov50" -PassThru;
Start-Process python ".\TOMACS_simulation.py --e infection_tests/Beta50_Mov75" -PassThru;
Start-Process python ".\TOMACS_simulation.py --e infection_tests/Beta50_Mov100" -PassThru;
Start-Process python ".\TOMACS_simulation.py --e infection_tests/Beta75_Mov25" -PassThru;
Start-Process python ".\TOMACS_simulation.py --e infection_tests/Beta75_Mov50" -PassThru;
Start-Process python ".\TOMACS_simulation.py --e infection_tests/Beta75_Mov75" -PassThru;
Start-Process python ".\TOMACS_simulation.py --e infection_tests/Beta75_Mov100" -PassThru;)

$procs | Wait-Process
cd misc_scripts

python .\experiment_global_population.py --p infection_tests --e Beta25_Mov25 --c Susceptible Infected Removed
python .\experiment_global_population.py --p infection_tests --e Beta25_Mov50 --c Susceptible Infected Removed
python .\experiment_global_population.py --p infection_tests --e Beta25_Mov75 --c Susceptible Infected Removed
python .\experiment_global_population.py --p infection_tests --e Beta25_Mov100 --c Susceptible Infected Removed
python .\experiment_global_population.py --p infection_tests --e Beta50_Mov25 --c Susceptible Infected Removed
python .\experiment_global_population.py --p infection_tests --e Beta50_Mov50 --c Susceptible Infected Removed
python .\experiment_global_population.py --p infection_tests --e Beta50_Mov75 --c Susceptible Infected Removed
python .\experiment_global_population.py --p infection_tests --e Beta50_Mov100 --c Susceptible Infected Removed
python .\experiment_global_population.py --p infection_tests --e Beta75_Mov25 --c Susceptible Infected Removed
python .\experiment_global_population.py --p infection_tests --e Beta75_Mov50 --c Susceptible Infected Removed
python .\experiment_global_population.py --p infection_tests --e Beta75_Mov75 --c Susceptible Infected Removed
python .\experiment_global_population.py --p infection_tests --e Beta75_Mov100 --c Susceptible Infected Removed

python .\experiment_infection_sum.py --p infection_tests --e Beta25_Mov25
python .\experiment_infection_sum.py --p infection_tests --e Beta25_Mov50
python .\experiment_infection_sum.py --p infection_tests --e Beta25_Mov75
python .\experiment_infection_sum.py --p infection_tests --e Beta25_Mov100
python .\experiment_infection_sum.py --p infection_tests --e Beta50_Mov25
python .\experiment_infection_sum.py --p infection_tests --e Beta50_Mov50
python .\experiment_infection_sum.py --p infection_tests --e Beta50_Mov75
python .\experiment_infection_sum.py --p infection_tests --e Beta50_Mov100
python .\experiment_infection_sum.py --p infection_tests --e Beta75_Mov25
python .\experiment_infection_sum.py --p infection_tests --e Beta75_Mov50
python .\experiment_infection_sum.py --p infection_tests --e Beta75_Mov75
python .\experiment_infection_sum.py --p infection_tests --e Beta75_Mov100

python .\infection_sum_comparison.py --p infection_tests --e Beta25_Mov100 Beta25_Mov75 Beta25_Mov50 Beta25_Mov25
python .\infection_sum_comparison.py --p infection_tests --e Beta50_Mov100 Beta50_Mov75 Beta50_Mov50 Beta50_Mov25
python .\infection_sum_comparison.py --p infection_tests --e Beta75_Mov100 Beta75_Mov75 Beta75_Mov50 Beta75_Mov25
python .\infection_sum_comparison.py --p infection_tests --e Beta25_Mov100 Beta50_Mov100 Beta75_Mov100
python .\infection_sum_comparison.py --p infection_tests --e Beta25_Mov75 Beta50_Mov75 Beta75_Mov75
python .\infection_sum_comparison.py --p infection_tests --e Beta25_Mov50 Beta50_Mov50 Beta75_Mov50
python .\infection_sum_comparison.py --p infection_tests --e Beta25_Mov25 Beta50_Mov25 Beta75_Mov25
python .\infection_sum_comparison.py --p infection_tests --e Beta25_Mov100 Beta25_Mov25 Beta75_Mov100 Beta75_Mov25
python .\infection_sum_comparison.py --p infection_tests --e Beta25_Mov100 Beta25_Mov25 Beta50_Mov100 Beta50_Mov25 Beta75_Mov100 Beta75_Mov25

Read-Host -Prompt "Press Enter to continue"
