param(
    [int]$N = 5,              # Number of times to run each simulation
    [int]$MaxParallel = 5     # Max experiments to run in parallel
)

$RepoRoot = Split-Path -Parent $PSCommandPath

$experiments = @(
    "large_scale_event/Baseline",
    "large_scale_event/Baseline+A_Dist",
    "large_scale_event/Baseline+A_Pop",
    "large_scale_event/Baseline+B_Dist",
    "large_scale_event/Baseline+B_Pop",
    "large_scale_event/Baseline+C_Dist",
    "large_scale_event/Baseline+C_Pop",
    "large_scale_event/Baseline+P_Dist",
    "large_scale_event/Baseline+P_Pop",
    "large_scale_event/Baseline+AB_Dist",
    "large_scale_event/Baseline+AB_Pop",
    "large_scale_event/Baseline+AC_Dist",
    "large_scale_event/Baseline+AC_Pop",
    "large_scale_event/Baseline+AP_Dist",
    "large_scale_event/Baseline+AP_Pop",
    "large_scale_event/Baseline+BC_Dist",
    "large_scale_event/Baseline+BC_Pop",
    "large_scale_event/Baseline+BP_Dist",
    "large_scale_event/Baseline+BP_Pop",
    "large_scale_event/Baseline+CP_Dist",
    "large_scale_event/Baseline+CP_Pop",
    "large_scale_event/Baseline+ABC_Dist",
    "large_scale_event/Baseline+ABC_Pop",
    "large_scale_event/Baseline+ABP_Dist",
    "large_scale_event/Baseline+ABP_Pop",
    "large_scale_event/Baseline+ACP_Dist",
    "large_scale_event/Baseline+ACP_Pop",
    "large_scale_event/Baseline+BCP_Dist",
    "large_scale_event/Baseline+BCP_Pop",
    "large_scale_event/Baseline+ABCP_Dist",
    "large_scale_event/Baseline+ABCP_Pop",
    "large_scale_event/Baseline+DiffStep_ACP_Dist",
    "large_scale_event/Baseline+DiffStep_ACP_Pop",
    "large_scale_event/Baseline+DiffStep_ABCP_Dist",
    "large_scale_event/Baseline+DiffStep_ABCP_Pop"
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

# Experiments for movement displacement analysis
$movementDisplacementExperiments = @(
    "Baseline",
    "Baseline+A_Dist",
    "Baseline+A_Pop",
    "Baseline+B_Dist",
    "Baseline+B_Pop",
    "Baseline+AB_Dist",
    "Baseline+AB_Pop",
    "Baseline+ABC_Dist",
    "Baseline+ABC_Pop",
    "Baseline+ABCP_Dist",
    "Baseline+ABCP_Pop",
    "Baseline+DiffStep_ACP_Dist",
    "Baseline+DiffStep_ACP_Pop",
    "Baseline+DiffStep_ABCP_Dist",
    "Baseline+DiffStep_ABCP_Pop"
)

foreach ($exp in $movementDisplacementExperiments) {
    python .\experiment_movement_displacement.py --p large_scale_event --e $exp
}

# Movement displacement comparison groups
$comparisonGroups = @(
    @("Baseline", "Baseline+A_Dist", "Baseline+B_Dist"),
    @("Baseline", "Baseline+A_Dist", "Baseline+B_Dist", "Baseline+AB_Dist"),
    @("Baseline", "Baseline+A_Dist", "Baseline+AB_Dist", "Baseline+ABC_Dist"),
    @("Baseline", "Baseline+A_Dist", "Baseline+AB_Dist", "Baseline+ABC_Dist", "Baseline+ABCP_Dist"),
    @("Baseline", "Baseline+ABCP_Dist"),
    @("Baseline", "Baseline+A_Pop", "Baseline+B_Pop"),
    @("Baseline", "Baseline+A_Pop", "Baseline+B_Pop", "Baseline+AB_Pop"),
    @("Baseline", "Baseline+A_Pop", "Baseline+AB_Pop", "Baseline+ABC_Pop"),
    @("Baseline", "Baseline+A_Pop", "Baseline+AB_Pop", "Baseline+ABC_Pop", "Baseline+ABCP_Pop"),
    @("Baseline", "Baseline+ABCP_Pop"),
    @("Baseline", "Baseline+DiffStep_ACP_Dist", "Baseline+DiffStep_ABCP_Dist"),
    @("Baseline", "Baseline+DiffStep_ACP_Pop", "Baseline+DiffStep_ABCP_Pop"),
    @("Baseline", "Baseline+ABCP_Dist", "Baseline+DiffStep_ABCP_Dist"),
    @("Baseline", "Baseline+ABCP_Pop", "Baseline+DiffStep_ABCP_Pop")
)

foreach ($group in $comparisonGroups) {
    $args = @(".\movement_displacement_comparison.py", "--p", "large_scale_event", "--b", "500", "--e") + $group
    python @args
}

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