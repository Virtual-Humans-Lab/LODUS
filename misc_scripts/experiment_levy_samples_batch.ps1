python .\experiment_levy_samples.py --e LevyWalk13-Workers
python .\experiment_levy_samples.py --e LevyWalk94-Workers

python .\experiment_levy_samples.py --e LevyWalk13-WorkSchool
python .\experiment_levy_samples.py --e LevyWalk94-WorkSchool

python .\experiment_levy_samples.py --e WorkSchool13-StadiumDistance
python .\experiment_levy_samples.py --e WorkSchool13-StadiumPopulation

python .\experiment_levy_samples.py --e WorkSchool94-StadiumDistance
python .\experiment_levy_samples.py --e WorkSchool94-StadiumPopulation

Write-Host -NoNewLine 'Press any key to continue...';
$null = $Host.UI.RawUI.ReadKey('NoEcho,IncludeKeyDown');