python .\TOMACS_simulation.py --e large_scale_event/Baseline
python .\TOMACS_simulation.py --e large_scale_event/Baseline+A_Dist
python .\TOMACS_simulation.py --e large_scale_event/Baseline+A_Pop
python .\TOMACS_simulation.py --e large_scale_event/Baseline+B_Dist
python .\TOMACS_simulation.py --e large_scale_event/Baseline+B_Pop
python .\TOMACS_simulation.py --e large_scale_event/Baseline+AB_Dist
python .\TOMACS_simulation.py --e large_scale_event/Baseline+AB_Pop
python .\TOMACS_simulation.py --e large_scale_event/Baseline+ABC_Dist
python .\TOMACS_simulation.py --e large_scale_event/Baseline+ABC_Pop
python .\TOMACS_simulation.py --e large_scale_event/Baseline+ABCP_Dist
python .\TOMACS_simulation.py --e large_scale_event/Baseline+ABCP_Pop

python .\TOMACS_simulation.py --e large_scale_event/Baseline+DiffStep_ACP_Dist
python .\TOMACS_simulation.py --e large_scale_event/Baseline+DiffStep_ACP_Pop
python .\TOMACS_simulation.py --e large_scale_event/Baseline+DiffStep_ABCP_Dist
python .\TOMACS_simulation.py --e large_scale_event/Baseline+DiffStep_ABCP_Pop

cd misc_scripts

python .\experiment_movement_displacement.py --p large_scale_event --e Baseline
python .\experiment_movement_displacement.py --p large_scale_event --e Baseline+A_Dist
python .\experiment_movement_displacement.py --p large_scale_event --e Baseline+A_Pop
python .\experiment_movement_displacement.py --p large_scale_event --e Baseline+B_Dist
python .\experiment_movement_displacement.py --p large_scale_event --e Baseline+B_Pop
python .\experiment_movement_displacement.py --p large_scale_event --e Baseline+AB_Dist
python .\experiment_movement_displacement.py --p large_scale_event --e Baseline+AB_Pop
python .\experiment_movement_displacement.py --p large_scale_event --e Baseline+ABC_Dist
python .\experiment_movement_displacement.py --p large_scale_event --e Baseline+ABC_Pop
python .\experiment_movement_displacement.py --p large_scale_event --e Baseline+ABCP_Dist
python .\experiment_movement_displacement.py --p large_scale_event --e Baseline+ABCP_Pop

python .\experiment_movement_displacement.py --p large_scale_event --e Baseline+DiffStep_ACP_Dist
python .\experiment_movement_displacement.py --p large_scale_event --e Baseline+DiffStep_ACP_Pop
python .\experiment_movement_displacement.py --p large_scale_event --e Baseline+DiffStep_ABCP_Dist
python .\experiment_movement_displacement.py --p large_scale_event --e Baseline+DiffStep_ABCP_Pop

python .\movement_displacement_comparison.py --p large_scale_event --b 500 --e Baseline Baseline+A_Dist Baseline+B_Dist
python .\movement_displacement_comparison.py --p large_scale_event --b 500 --e Baseline Baseline+A_Dist Baseline+B_Dist Baseline+AB_Dist
python .\movement_displacement_comparison.py --p large_scale_event --b 500 --e Baseline Baseline+A_Dist Baseline+AB_Dist Baseline+ABC_Dist
python .\movement_displacement_comparison.py --p large_scale_event --b 500 --e Baseline Baseline+A_Dist Baseline+AB_Dist Baseline+ABC_Dist Baseline+ABCP_Dist
python .\movement_displacement_comparison.py --p large_scale_event --b 500 --e Baseline Baseline+ABCP_Dist

python .\movement_displacement_comparison.py --p large_scale_event --b 500 --e Baseline Baseline+A_Pop Baseline+B_Pop
python .\movement_displacement_comparison.py --p large_scale_event --b 500 --e Baseline Baseline+A_Pop Baseline+B_Pop Baseline+AB_Pop
python .\movement_displacement_comparison.py --p large_scale_event --b 500 --e Baseline Baseline+A_Pop Baseline+AB_Pop Baseline+ABC_Pop
python .\movement_displacement_comparison.py --p large_scale_event --b 500 --e Baseline Baseline+A_Pop Baseline+AB_Pop Baseline+ABC_Pop Baseline+ABCP_Pop
python .\movement_displacement_comparison.py --p large_scale_event --b 500 --e Baseline Baseline+ABCP_Pop

python .\movement_displacement_comparison.py --p large_scale_event --b 500 --e Baseline Baseline+DiffStep_ACP_Dist Baseline+DiffStep_ABCP_Dist
python .\movement_displacement_comparison.py --p large_scale_event --b 500 --e Baseline Baseline+DiffStep_ACP_Pop Baseline+DiffStep_ABCP_Pop

python .\movement_displacement_comparison.py --p large_scale_event --b 500 --e Baseline Baseline+ABCP_Dist Baseline+DiffStep_ABCP_Dist
python .\movement_displacement_comparison.py --p large_scale_event --b 500 --e Baseline Baseline+ABCP_Pop Baseline+DiffStep_ABCP_Pop

Read-Host -Prompt "Press Enter to continue"
