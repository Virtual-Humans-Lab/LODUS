# Same BinWidth, different Scales, no stadiums
python .\movement_displacement_comparison.py --p levy_parameter_tests_94 --e WorkSchool94-BW_250-S_250 WorkSchool94-BW_250-S_500 WorkSchool94-BW_250-S_750
python .\movement_displacement_comparison.py --p levy_parameter_tests_94 --e WorkSchool94-BW_500-S_500 WorkSchool94-BW_500-S_1000 WorkSchool94-BW_500-S_1500
python .\movement_displacement_comparison.py --p levy_parameter_tests_94 --e WorkSchool94-BW_1000-S_1000 WorkSchool94-BW_1000-S_2000 WorkSchool94-BW_1000-S_3000


# BinWidth = 250, different Scales, with stadiums
python .\movement_displacement_comparison.py --p levy_parameter_tests_94 --e WorkSchool94-BW_250-S_250 WorkSchool94-BW_250-S_250_StadiumDistance WorkSchool94-BW_250-S_250_StadiumPopulation
python .\movement_displacement_comparison.py --p levy_parameter_tests_94 --e WorkSchool94-BW_250-S_500 WorkSchool94-BW_250-S_500_StadiumDistance WorkSchool94-BW_250-S_500_StadiumPopulation
python .\movement_displacement_comparison.py --p levy_parameter_tests_94 --e WorkSchool94-BW_250-S_750 WorkSchool94-BW_250-S_750_StadiumDistance WorkSchool94-BW_250-S_750_StadiumPopulation

# BinWidth = 500, different Scales, with stadiums
python .\movement_displacement_comparison.py --p levy_parameter_tests_94 --e WorkSchool94-BW_500-S_500 WorkSchool94-BW_500-S_500_StadiumDistance WorkSchool94-BW_500-S_500_StadiumPopulation
python .\movement_displacement_comparison.py --p levy_parameter_tests_94 --e WorkSchool94-BW_500-S_1000 WorkSchool94-BW_500-S_1000_StadiumDistance WorkSchool94-BW_500-S_1000_StadiumPopulation
python .\movement_displacement_comparison.py --p levy_parameter_tests_94 --e WorkSchool94-BW_500-S_1500 WorkSchool94-BW_500-S_1500_StadiumDistance WorkSchool94-BW_500-S_1500_StadiumPopulation

# BinWidth = 1000, different Scales, with stadiums
python .\movement_displacement_comparison.py --p levy_parameter_tests_94 --e WorkSchool94-BW_1000-S_1000 WorkSchool94-BW_1000-S_1000_StadiumDistance WorkSchool94-BW_1000-S_1000_StadiumPopulation
python .\movement_displacement_comparison.py --p levy_parameter_tests_94 --e WorkSchool94-BW_1000-S_2000 WorkSchool94-BW_1000-S_2000_StadiumDistance WorkSchool94-BW_1000-S_2000_StadiumPopulation
python .\movement_displacement_comparison.py --p levy_parameter_tests_94 --e WorkSchool94-BW_1000-S_3000 WorkSchool94-BW_1000-S_3000_StadiumDistance WorkSchool94-BW_1000-S_3000_StadiumPopulation

Read-Host -Prompt "Press Enter to continue"