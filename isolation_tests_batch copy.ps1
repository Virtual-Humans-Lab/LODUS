python .\TOMACS_simulation.py --e isolation_tests/Baseline
python .\TOMACS_simulation.py --e isolation_tests/Baseline-Iso_25
python .\TOMACS_simulation.py --e isolation_tests/Baseline-Iso_50
python .\TOMACS_simulation.py --e isolation_tests/Baseline-Iso_75
python .\TOMACS_simulation.py --e isolation_tests/Baseline-Iso_100

cd misc_scripts

python .\experiment_movement_displacement.py --p isolation_tests --e Baseline
python .\experiment_movement_displacement.py --p isolation_tests --e Baseline-Iso_25
python .\experiment_movement_displacement.py --p isolation_tests --e Baseline-Iso_50
python .\experiment_movement_displacement.py --p isolation_tests --e Baseline-Iso_75
python .\experiment_movement_displacement.py --p isolation_tests --e Baseline-Iso_100

python .\movement_displacement_comparison.py --p isolation_tests --b 500 --e Baseline Baseline-Iso_25 Baseline-Iso_50 Baseline-Iso_75 Baseline-Iso_100 --l Baseline "Restriction = 0.25" "Restriction = 0.50" "Restriction = 0.75" "Restriction = 1.00" --x 25000

Read-Host -Prompt "Press Enter to continue"
