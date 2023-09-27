python .\experiment_movement_displacement.py --p large_scale_event --e Baseline
python .\experiment_movement_displacement.py --p large_scale_event --e Baseline+A_Dist
python .\experiment_movement_displacement.py --p large_scale_event --e Baseline+A_Pop
python .\experiment_movement_displacement.py --p large_scale_event --e Baseline+B_Dist
python .\experiment_movement_displacement.py --p large_scale_event --e Baseline+B_Pop
python .\experiment_movement_displacement.py --p large_scale_event --e Baseline+C_Dist
python .\experiment_movement_displacement.py --p large_scale_event --e Baseline+C_Pop
python .\experiment_movement_displacement.py --p large_scale_event --e Baseline+P_Dist
python .\experiment_movement_displacement.py --p large_scale_event --e Baseline+P_Pop

python .\experiment_movement_displacement.py --p large_scale_event --e Baseline+AB_Dist
python .\experiment_movement_displacement.py --p large_scale_event --e Baseline+AB_Pop
python .\experiment_movement_displacement.py --p large_scale_event --e Baseline+AC_Dist
python .\experiment_movement_displacement.py --p large_scale_event --e Baseline+AC_Pop
python .\experiment_movement_displacement.py --p large_scale_event --e Baseline+AP_Dist
python .\experiment_movement_displacement.py --p large_scale_event --e Baseline+AP_Pop
python .\experiment_movement_displacement.py --p large_scale_event --e Baseline+BC_Dist
python .\experiment_movement_displacement.py --p large_scale_event --e Baseline+BC_Pop
python .\experiment_movement_displacement.py --p large_scale_event --e Baseline+BP_Dist
python .\experiment_movement_displacement.py --p large_scale_event --e Baseline+BP_Pop
python .\experiment_movement_displacement.py --p large_scale_event --e Baseline+CP_Dist
python .\experiment_movement_displacement.py --p large_scale_event --e Baseline+CP_Pop

python .\experiment_movement_displacement.py --p large_scale_event --e Baseline+ABC_Dist
python .\experiment_movement_displacement.py --p large_scale_event --e Baseline+ABC_Pop
python .\experiment_movement_displacement.py --p large_scale_event --e Baseline+ABP_Dist
python .\experiment_movement_displacement.py --p large_scale_event --e Baseline+ABP_Pop
python .\experiment_movement_displacement.py --p large_scale_event --e Baseline+ACP_Dist
python .\experiment_movement_displacement.py --p large_scale_event --e Baseline+ACP_Pop
python .\experiment_movement_displacement.py --p large_scale_event --e Baseline+BCP_Dist
python .\experiment_movement_displacement.py --p large_scale_event --e Baseline+BCP_Pop

python .\experiment_movement_displacement.py --p large_scale_event --e Baseline+ABCP_Dist
python .\experiment_movement_displacement.py --p large_scale_event --e Baseline+ABCP_Pop
python .\experiment_movement_displacement.py --p large_scale_event --e Baseline+DiffStep_ACP_Dist
python .\experiment_movement_displacement.py --p large_scale_event --e Baseline+DiffStep_ACP_Pop
python .\experiment_movement_displacement.py --p large_scale_event --e Baseline+DiffStep_ABCP_Dist
python .\experiment_movement_displacement.py --p large_scale_event --e Baseline+DiffStep_ABCP_Pop


python .\movement_displacement_comparison.py --p large_scale_event --b 500 --e Baseline Baseline+A_Dist Baseline+B_Dist --l Baseline Baseline+A Baseline+B

python .\movement_displacement_comparison.py --p large_scale_event --b 500 --e Baseline Baseline+A_Dist Baseline+B_Dist Baseline+AB_Dist --l Baseline Baseline+A Baseline+B Baseline+AB

python .\movement_displacement_comparison.py --p large_scale_event --b 500 --e Baseline Baseline+A_Dist Baseline+AB_Dist Baseline+ABC_Dist Baseline+ABCP_Dist --l Baseline Baseline+A Baseline+AB Baseline+ABC Baseline+ABCD


python .\movement_displacement_comparison.py --p large_scale_event --b 500 --e Baseline Baseline+ABCP_Dist Baseline+ABCP_Pop --l Baseline Baseline+ABCD+Dist Baseline+ABCD+Pop


python .\movement_displacement_comparison.py --p large_scale_event --b 500 --e Baseline Baseline+ABCP_Dist Baseline+DiffStep_ABCP_Dist --l Baseline Baseline+ABCD Baseline+ABCD+DiffStep

python .\movement_displacement_comparison.py --p large_scale_event --b 500 --e Baseline Baseline+ABCP_Pop Baseline+DiffStep_ABCP_Pop --l Baseline Baseline+ABCD Baseline+ABCD+DiffStepP


python .\movement_displacement_comparison.py --p large_scale_event --b 500 --e Baseline Baseline+DiffStep_ABCP_Dist Baseline+DiffStep_ABCP_Pop --l Baseline Baseline+ABCD+DiffStep+Dist Baseline+ABCD+DiffStep+Pop


Read-Host -Prompt "Press Enter to continue"