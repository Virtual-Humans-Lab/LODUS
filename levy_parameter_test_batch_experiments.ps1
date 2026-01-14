# Improved batch experiment runner with error handling, progress tracking, and resume capability

$ErrorActionPreference = "Stop"

# Configuration
$experiments = @(
    "WorkSchool94-BW_250-S_250",
    "WorkSchool94-BW_250-S_500",
    "WorkSchool94-BW_250-S_750",
    "WorkSchool94-BW_500-S_250",
    "WorkSchool94-BW_500-S_500",
    "WorkSchool94-BW_500-S_1000",
    "WorkSchool94-BW_500-S_1500",
    "WorkSchool94-BW_500-S_2500",
    "WorkSchool94-BW_500-S_5000",
    "WorkSchool94-BW_1000-S_1000",
    "WorkSchool94-BW_1000-S_2000",
    "WorkSchool94-BW_1000-S_3000",
    "WorkSchool94-BW_3000-S_3000",
    "WorkSchool94-BW_3000-S_6000",
    "WorkSchool94-BW_3000-S_9000",
    "WorkSchool94-BW_250-S_250_StadiumDistance",
    "WorkSchool94-BW_250-S_500_StadiumDistance",
    "WorkSchool94-BW_250-S_750_StadiumDistance",
    "WorkSchool94-BW_500-S_500_StadiumDistance",
    "WorkSchool94-BW_500-S_1000_StadiumDistance",
    "WorkSchool94-BW_500-S_1500_StadiumDistance",
    "WorkSchool94-BW_1000-S_1000_StadiumDistance",
    "WorkSchool94-BW_1000-S_2000_StadiumDistance",
    "WorkSchool94-BW_1000-S_3000_StadiumDistance",
    "WorkSchool94-BW_3000-S_3000_StadiumDistance",
    "WorkSchool94-BW_3000-S_6000_StadiumDistance",
    "WorkSchool94-BW_3000-S_9000_StadiumDistance",
    "WorkSchool94-BW_250-S_250_StadiumPopulation",
    "WorkSchool94-BW_250-S_500_StadiumPopulation",
    "WorkSchool94-BW_250-S_750_StadiumPopulation",
    "WorkSchool94-BW_500-S_500_StadiumPopulation",
    "WorkSchool94-BW_500-S_1000_StadiumPopulation",
    "WorkSchool94-BW_500-S_1500_StadiumPopulation",
    "WorkSchool94-BW_1000-S_1000_StadiumPopulation",
    "WorkSchool94-BW_1000-S_2000_StadiumPopulation",
    "WorkSchool94-BW_1000-S_3000_StadiumPopulation",
    "WorkSchool94-BW_3000-S_3000_StadiumPopulation",
    "WorkSchool94-BW_3000-S_6000_StadiumPopulation",
    "WorkSchool94-BW_3000-S_9000_StadiumPopulation"
)

# Create output folder for logs
$outputFolder = "batch_logs"
if (-not (Test-Path $outputFolder)) {
    New-Item -ItemType Directory -Path $outputFolder | Out-Null
}

$completedFile = "$outputFolder\completed_simulations.txt"
$logFile = "$outputFolder\simulation_log_$(Get-Date -Format 'yyyyMMdd_HHmmss').txt"
$errorLogFile = "$outputFolder\simulation_errors_$(Get-Date -Format 'yyyyMMdd_HHmmss').txt"

# Load previously completed experiments
$completed = @()
if (Test-Path $completedFile) {
    $completed = Get-Content $completedFile
    Write-Host "Found $($completed.Count) previously completed simulations" -ForegroundColor Green
}

# Filter out already completed experiments
$remainingExperiments = $experiments | Where-Object { $completed -notcontains $_ }
$total = $remainingExperiments.Count

if ($total -eq 0) {
    Write-Host "All experiments already completed!" -ForegroundColor Green
    Read-Host -Prompt "Press Enter to exit"
    exit 0
}

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Starting batch experiment run" -ForegroundColor Cyan
Write-Host "Total experiments: $total" -ForegroundColor Cyan
Write-Host "Log file: $logFile" -ForegroundColor Cyan
Write-Host "========================================`n" -ForegroundColor Cyan

$startTime = Get-Date
$successCount = 0
$failureCount = 0

for ($i = 0; $i -lt $total; $i++) {
    $exp = $remainingExperiments[$i]
    $progress = [math]::Round((($i + 1) / $total) * 100, 2)
    $expPath = ".\experiments\levy_parameter_tests_94\$exp.json"
    $expLodusPath = ".\levy_parameter_tests_94\$exp"

    # Progress header
    Write-Host "`n========================================" -ForegroundColor Cyan
    Write-Host "[$($i+1)/$total - $progress%] $exp" -ForegroundColor Cyan
    Write-Host "========================================" -ForegroundColor Cyan
    
    # Check if experiment file exists
    if (-not (Test-Path $expPath)) {
        $errorMsg = "ERROR: File not found: $expPath"
        Write-Host $errorMsg -ForegroundColor Red
        "$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') - $errorMsg" | Out-File -Append $errorLogFile
        $failureCount++
        continue
    }
    
    # Log start
    $logEntry = "$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') - Starting: $exp"
    $logEntry | Out-File -Append $logFile
    
    # Run simulation
    $simStartTime = Get-Date
    try {
        python .\TOMACS_simulation.py --e $expLodusPath
        
        if ($LASTEXITCODE -ne 0) {
            throw "Python script exited with code $LASTEXITCODE"
        }
        
        $simDuration = (Get-Date) - $simStartTime
        $successMsg = "SUCCESS - Duration: $($simDuration.ToString('hh\:mm\:ss'))"
        Write-Host $successMsg -ForegroundColor Green
        
        # Log completion
        "$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') - Completed: $exp ($successMsg)" | Out-File -Append $logFile
        
        # Mark as completed
        $exp | Out-File -Append $completedFile
        $successCount++
        
    } catch {
        $errorMsg = "ERROR: $($_.Exception.Message)"
        Write-Host $errorMsg -ForegroundColor Red
        "$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') - Failed: $exp - $errorMsg" | Out-File -Append $errorLogFile
        "$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') - Failed: $exp - $errorMsg" | Out-File -Append $logFile
        $failureCount++
        
        # Ask user whether to continue
        $response = Read-Host "Continue with remaining experiments? (Y/N)"
        if ($response -ne 'Y' -and $response -ne 'y') {
            Write-Host "Batch execution stopped by user" -ForegroundColor Yellow
            break
        }
    }
    
    # Time estimation
    $elapsed = (Get-Date) - $startTime
    $avgTime = $elapsed.TotalSeconds / ($i + 1)
    $remaining = $avgTime * ($total - $i - 1)
    $estimatedCompletion = (Get-Date).AddSeconds($remaining)
    
    Write-Host "`nProgress Summary:" -ForegroundColor Yellow
    Write-Host "  Completed: $($i+1)/$total ($progress%)" -ForegroundColor Yellow
    Write-Host "  Successful: $successCount | Failed: $failureCount" -ForegroundColor Yellow
    Write-Host "  Elapsed time: $($elapsed.ToString('hh\:mm\:ss'))" -ForegroundColor Yellow
    Write-Host "  Est. remaining: $([TimeSpan]::FromSeconds($remaining).ToString('hh\:mm\:ss'))" -ForegroundColor Yellow
    Write-Host "  Est. completion: $($estimatedCompletion.ToString('yyyy-MM-dd HH:mm:ss'))" -ForegroundColor Yellow
}

# Final summary
$totalDuration = (Get-Date) - $startTime
Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "Batch Execution Complete!" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Total experiments processed: $($successCount + $failureCount)" -ForegroundColor White
Write-Host "Successful: $successCount" -ForegroundColor Green
Write-Host "Failed: $failureCount" -ForegroundColor $(if ($failureCount -gt 0) { "Red" } else { "Green" })
Write-Host "Total duration: $($totalDuration.ToString('hh\:mm\:ss'))" -ForegroundColor White
Write-Host "Log file: $logFile" -ForegroundColor White
if ($failureCount -gt 0) {
    Write-Host "Error log: $errorLogFile" -ForegroundColor Red
}
Write-Host "========================================`n" -ForegroundColor Cyan

Read-Host -Prompt "Press Enter to exit"