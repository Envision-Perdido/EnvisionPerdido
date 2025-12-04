# Setup Guide: Automated Event Calendar Management
# Run this script as Administrator to create scheduled tasks

$ErrorActionPreference = "Stop"

# Configuration
$RepoRoot = "c:\Users\scott\UWF-Code\EnvisionPerdido"

# Auto-detect PowerShell 7 location
$PwshPath = (Get-Command pwsh -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Source)

if (-not $PwshPath) {
    Write-Error "PowerShell 7 (pwsh) not found in PATH. Please install PowerShell 7."
    exit 1
}

Write-Host "Found PowerShell 7 at: $PwshPath" -ForegroundColor Gray

# Verify repo exists
if (-not (Test-Path $RepoRoot)) {
    Write-Error "Repository not found at $RepoRoot"
    exit 1
}

Write-Host "Creating scheduled tasks for Event Calendar automation..." -ForegroundColor Cyan
Write-Host ""

# Task 1: Health Check (Every 3 days)
$HealthCheckAction = New-ScheduledTaskAction `
    -Execute $PwshPath `
    -Argument "-NoProfile -ExecutionPolicy Bypass -File `"$RepoRoot\scripts\windows\run_health_check.ps1`"" `
    -WorkingDirectory $RepoRoot

$HealthCheckTrigger = New-ScheduledTaskTrigger `
    -Daily `
    -At "6:30 AM" `
    -DaysInterval 3

$HealthCheckSettings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -WakeToRun `
    -StartWhenAvailable `
    -ExecutionTimeLimit (New-TimeSpan -Hours 1)

$HealthCheckPrincipal = New-ScheduledTaskPrincipal `
    -UserId "$env:USERDOMAIN\$env:USERNAME" `
    -LogonType S4U `
    -RunLevel Limited

Register-ScheduledTask `
    -TaskName "EnvisionPerdido_HealthCheck" `
    -Description "Runs health check for Envision Perdido calendar every 3 days at 6:30 AM" `
    -Action $HealthCheckAction `
    -Trigger $HealthCheckTrigger `
    -Settings $HealthCheckSettings `
    -Principal $HealthCheckPrincipal `
    -Force

Write-Host "✓ Created: EnvisionPerdido_HealthCheck (every 3 days at 6:30 AM)" -ForegroundColor Green

# Task 2: Monthly Pipeline (1st of each month)
# Using schtasks.exe for monthly trigger (simpler than CIM classes)
$PipelineTaskName = "EnvisionPerdido_MonthlyPipeline"
$PipelineScript = "$RepoRoot\scripts\windows\run_pipeline.ps1"

# Delete existing task if present
schtasks.exe /Delete /TN $PipelineTaskName /F 2>$null

# Create monthly task using schtasks
$schtasksArgs = @(
    "/Create"
    "/TN", $PipelineTaskName
    "/TR", "`"$PwshPath`" -NoProfile -ExecutionPolicy Bypass -File `"$PipelineScript`""
    "/SC", "MONTHLY"
    "/D", "1"
    "/ST", "02:30"
    "/RU", "$env:USERDOMAIN\$env:USERNAME"
    "/RL", "LIMITED"
    "/F"
)

$result = & schtasks.exe $schtasksArgs 2>&1

if ($LASTEXITCODE -eq 0) {
    # Now modify settings for wake and battery options using PowerShell
    $task = Get-ScheduledTask -TaskName $PipelineTaskName
    $settings = $task.Settings
    $settings.WakeToRun = $true
    $settings.DisallowStartIfOnBatteries = $false
    $settings.StopIfGoingOnBatteries = $false
    $settings.StartWhenAvailable = $true
    $settings.ExecutionTimeLimit = "PT2H"
    Set-ScheduledTask -TaskName $PipelineTaskName -Settings $settings | Out-Null
    
    Write-Host "✓ Created: EnvisionPerdido_MonthlyPipeline (1st of month at 2:30 AM)" -ForegroundColor Green
} else {
    Write-Error "Failed to create monthly pipeline task"
}

Write-Host "✓ Created: EnvisionPerdido_MonthlyPipeline (1st of month at 2:30 AM)" -ForegroundColor Green

Write-Host ""
Write-Host "Tasks created successfully!" -ForegroundColor Green
Write-Host ""
Write-Host "Schedule Summary:" -ForegroundColor Cyan
Write-Host "  Health Check:    Every 3 days at 6:30 AM"
Write-Host "  Pipeline Upload: 1st of month at 2:30 AM"
Write-Host ""
Write-Host "Important Notes:" -ForegroundColor Yellow
Write-Host "  • Computer will wake from sleep to run these tasks"
Write-Host "  • Computer must be ON or in Sleep mode (not Shutdown/Hibernate)"
Write-Host "  • Logs saved to: $RepoRoot\output\logs"
Write-Host "  • Email notifications configured via env.ps1"
Write-Host ""
Write-Host "To view/manage tasks:" -ForegroundColor Cyan
Write-Host "  1. Open Task Scheduler (taskschd.msc)"
Write-Host "  2. Look for 'EnvisionPerdido_HealthCheck' and 'EnvisionPerdido_MonthlyPipeline'"
Write-Host ""
Write-Host "To test tasks manually:" -ForegroundColor Cyan
Write-Host "  Get-ScheduledTask -TaskName 'EnvisionPerdido_*' | Start-ScheduledTask"
Write-Host ""
