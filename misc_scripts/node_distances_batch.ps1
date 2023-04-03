python .\node_distances.py --e NodeDistances13 --y 2000
python .\node_distances.py --e NodeDistances13 --d 2 --b 500 --y 2000
python .\node_distances.py --e NodeDistances13 --d 3 --b 500 --y 2000

python .\node_distances.py --e NodeDistances94 --y 16000
python .\node_distances.py --e NodeDistances94 --d 2 --b 500 --y 16000
python .\node_distances.py --e NodeDistances94 --d 3 --b 500 --y 16000

Write-Host -NoNewLine 'Press any key to continue...';
$null = $Host.UI.RawUI.ReadKey('NoEcho,IncludeKeyDown');