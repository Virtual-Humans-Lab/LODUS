param(
    [int]$N = 5,              # Number of times to run each simulation,
    [int]$MemoryRuns = 1,     # Number of times to run each memory profiling simulation
    [int]$MaxParallel = 5     # Max experiments to run in parallel
)

$RepoRoot = Split-Path -Parent $PSCommandPath

$experiments = @(
    "epidemic_nb_tests/R0-2.6",
    "epidemic_nb_tests/R0-2.6-Mov25.json",
    "epidemic_nb_tests/R0-2.6-Mov50.json",
    "epidemic_nb_tests/R0-2.6-VaccA-Mov100",
    "epidemic_nb_tests/R0-2.6-VaccB-Mov100",
    "epidemic_nb_tests/R0-2.6-VaccC-Mov100",
    "epidemic_nb_tests/R0-2.6-VaccD-Mov100",
    "epidemic_nb_tests/R0-2.6-VaccC-Mov25",
    "epidemic_nb_tests/R0-2.6-VaccC-Mov50"
)

# Launch experiment jobs with throttling
$jobs = @()
foreach ($experiment in $experiments) {
    # Throttle
    while (($jobs | Where-Object { $_.State -eq 'Running' }).Count -ge $MaxParallel) {
        Wait-Job -Any $jobs | Out-Null
        $jobs = $jobs | Where-Object { $_.State -eq 'Running' -or $_.State -eq 'NotStarted' }
    }

    $jobName = ($experiment -replace '[^A-Za-z0-9_-]', '_')

    $job = Start-Job -Name $jobName -ArgumentList $experiment, $N, $RepoRoot -ScriptBlock {
        param($exp, $runs, $root)
        Set-Location $root

        for ($i = 1; $i -le $runs; $i++) {
            Write-Host "[$exp] Running iteration $i of $runs" -ForegroundColor Cyan
            python .\TOMACS_simulation.py --e $exp
        }

        Write-Host "[$exp] Parsing outputs" -ForegroundColor Green
        python .\misc_scripts\parse_simulation_outputs.py $exp
    }

    $jobs += $job
}

# Wait for all jobs to finish and collect output
Write-Host "Waiting for all experiment jobs to complete..." -ForegroundColor Yellow
Wait-Job -Job $jobs | Out-Null
Receive-Job -Job $jobs
$failed = $jobs | Where-Object { $_.State -ne 'Completed' }
if ($failed) {
    Write-Host "Warning: Some jobs failed:" -ForegroundColor Red
    $failed | ForEach-Object { Write-Host (" - {0}: {1}" -f $_.Name, $_.State) -ForegroundColor Red }
}
Remove-Job -Job $jobs -Force


Write-Host "`nRunning memory profiles for all experiments in parallel..." -ForegroundColor Green
$memoryJobs = @()
foreach ($experiment in $experiments) {
    # Throttle
    while (($memoryJobs | Where-Object { $_.State -eq 'Running' }).Count -ge $MaxParallel) {
        Wait-Job -Any $memoryJobs | Out-Null
        $memoryJobs = $memoryJobs | Where-Object { $_.State -eq 'Running' -or $_.State -eq 'NotStarted' }
    }

    $jobName = ("mem_" + ($experiment -replace '[^A-Za-z0-9_-]', '_'))

    $job = Start-Job -Name $jobName -ArgumentList $experiment, $RepoRoot, $MemoryRuns -ScriptBlock {
        param($exp, $root, $memoryRuns)
        Set-Location $root

        Write-Host "Running memory profile for $exp" -ForegroundColor Cyan
        python .\misc_scripts\run_memory_profiles.py -e $exp --runs $memoryRuns
    }

    $memoryJobs += $job
}

# Wait for all memory profiling jobs to complete
Write-Host "Waiting for all memory profiling jobs to complete..." -ForegroundColor Yellow
Wait-Job -Job $memoryJobs | Out-Null
Receive-Job -Job $memoryJobs
$failedMem = $memoryJobs | Where-Object { $_.State -ne 'Completed' }
if ($failedMem) {
    Write-Host "Warning: Some memory profiling jobs failed:" -ForegroundColor Red
    $failedMem | ForEach-Object { Write-Host (" - {0}: {1}" -f $_.Name, $_.State) -ForegroundColor Red }
}
Remove-Job -Job $memoryJobs -Force

Write-Host "`nParsing memory profiles for all experiments..." -ForegroundColor Green
foreach ($experiment in $experiments) {
    Write-Host "Parsing memory profile for $experiment" -ForegroundColor Cyan
    python .\misc_scripts\parse_memory_profiles.py $experiment
}

Read-Host -Prompt "Press Enter to continue"