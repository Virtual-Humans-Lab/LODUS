# Configuration
$experiments = @("Baseline", "Baseline-Iso_25", "Baseline-Iso_50", "Baseline-Iso_75", "Baseline-Iso_100")
$numberOfRuns = 5  # Change this to run TOMACS simulations N times

Write-Host "Starting TOMACS experiment suite..." -ForegroundColor Green
Write-Host "Total runs: $numberOfRuns`n" -ForegroundColor Cyan

# Run TOMACS simulations N times
for ($run = 1; $run -le $numberOfRuns; $run++) {
    Write-Host "========== RUN $run/$numberOfRuns ==========" -ForegroundColor Magenta
    
    foreach ($exp in $experiments) {
        Write-Host "Running: $exp" -ForegroundColor Yellow
        $stopwatch = Measure-Command {
            python .\TOMACS_simulation.py --e "isolation_tests/$exp" | Out-Null
        }
        Write-Host "  Completed in $($stopwatch.TotalSeconds.ToString('F2')) seconds`n"
    }
    
    Write-Host "Run $run/$numberOfRuns completed`n" -ForegroundColor Green
}

# Run analysis scripts once after all simulations
Write-Host "All TOMACS simulations completed. Running analysis scripts..." -ForegroundColor Cyan

# Switch to misc_scripts directory for analysis
cd misc_scripts

Write-Host "Running analysis scripts..." -ForegroundColor Green

# Movement displacement analysis
foreach ($exp in $experiments) {
    python .\experiment_movement_displacement.py --p isolation_tests --e $exp | Out-Null
    Write-Host "Processed: $exp" -ForegroundColor Cyan
}

# Comparison plot
python .\movement_displacement_comparison.py --p isolation_tests --b 500 --e Baseline Baseline-Iso_25 Baseline-Iso_50 Baseline-Iso_75 Baseline-Iso_100 --l Baseline "Restriction = 0.25" "Restriction = 0.50" "Restriction = 0.75" "Restriction = 1.00" --x 25000

Write-Host "Analysis complete!" -ForegroundColor Green
Read-Host -Prompt "Press Enter to continue"