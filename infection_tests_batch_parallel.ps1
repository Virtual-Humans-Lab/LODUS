param(
    [int]$N = 5,              # Number of times to run each simulation
    [int]$MaxParallel = 3     # Max experiments to run in parallel
)

$RepoRoot = Split-Path -Parent $PSCommandPath

$experiments = @(
    "infection_tests/R0-2.6",
    "infection_tests/R0-3.07",
    "infection_tests/R0-6.0"
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

# ...existing code...
Set-Location misc_scripts

# Experiments for infection analysis
$infectionExperiments = @(
    "R0-2.6",
    "R0-3.07",
    "R0-6.0"
)

# Global population analysis
foreach ($exp in $infectionExperiments) {
    Write-Host "Analyzing global population for $exp" -ForegroundColor Cyan
    python .\experiment_global_population.py --p infection_tests --e $exp --c Susceptible Infected Removed
}

# Infection sum analysis
foreach ($exp in $infectionExperiments) {
    Write-Host "Analyzing infection sum for $exp" -ForegroundColor Cyan
    python .\experiment_infection_sum.py --p infection_tests --e $exp
}

# Infection sum comparison
Write-Host "Comparing infection sums" -ForegroundColor Cyan
$args = @(".\infection_sum_comparison.py", "--p", "infection_tests", "--e") + $infectionExperiments
python @args

Set-Location ..

Write-Host "`nRunning memory profiles for all experiments in parallel..." -ForegroundColor Green
$memoryJobs = @()
foreach ($experiment in $experiments) {
    # Throttle
    while (($memoryJobs | Where-Object { $_.State -eq 'Running' }).Count -ge $MaxParallel) {
        Wait-Job -Any $memoryJobs | Out-Null
        $memoryJobs = $memoryJobs | Where-Object { $_.State -eq 'Running' -or $_.State -eq 'NotStarted' }
    }

    $jobName = ("mem_" + ($experiment -replace '[^A-Za-z0-9_-]', '_'))

    $job = Start-Job -Name $jobName -ArgumentList $experiment, $RepoRoot -ScriptBlock {
        param($exp, $root)
        Set-Location $root

        Write-Host "Running memory profile for $exp" -ForegroundColor Cyan
        python .\misc_scripts\run_memory_profiles.py -e $exp --runs 5
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