python .\experiment_movement_displacement.py --e LevyWalk13-Workers --b 0.00125
python .\experiment_movement_displacement.py --e LevyWalk94-Workers

python .\experiment_movement_displacement.py --e LevyWalk13-WorkSchool --b 0.00125
python .\experiment_movement_displacement.py --e LevyWalk94-WorkSchool

python .\experiment_movement_displacement.py --e WorkSchool13-StadiumDistance --b 0.00125
python .\experiment_movement_displacement.py --e WorkSchool13-StadiumPopulation --b 0.00125

python .\experiment_movement_displacement.py --e WorkSchool94-StadiumDistance
python .\experiment_movement_displacement.py --e WorkSchool94-StadiumPopulation

Write-Host -NoNewLine 'Press any key to continue...';
$null = $Host.UI.RawUI.ReadKey('NoEcho,IncludeKeyDown');