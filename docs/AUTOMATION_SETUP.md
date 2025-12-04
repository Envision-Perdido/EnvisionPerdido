# Envision Perdido Calendar Automation Setup

## Overview
Automated event calendar management with:
- **Monthly Pipeline**: Scrapes, classifies, and uploads events (1st of each month)
- **Health Check**: Monitors calendar health every 3 days

## Quick Setup

### 1. One-Time Setup (Windows Task Scheduler)

Run as Administrator:
```powershell
cd c:\Users\scott\UWF-Code\EnvisionPerdido
pwsh -ExecutionPolicy Bypass -File .\scripts\windows\setup_scheduled_tasks.ps1
```

This creates two scheduled tasks:
- `EnvisionPerdido_HealthCheck` - Every 3 days at 6:30 AM
- `EnvisionPerdido_MonthlyPipeline` - 1st of month at 2:30 AM

### 2. Verify Tasks

Open Task Scheduler:
```powershell
taskschd.msc
```

Look for the two tasks listed above.

### 3. Test Tasks Manually

```powershell
# Test health check
Get-ScheduledTask -TaskName 'EnvisionPerdido_HealthCheck' | Start-ScheduledTask

# Test pipeline
Get-ScheduledTask -TaskName 'EnvisionPerdido_MonthlyPipeline' | Start-ScheduledTask
```

## How It Works

### Computer Sleep vs. Shutdown
- **Sleep Mode**: ✅ Tasks will wake computer and run
- **Hibernate**: ⚠️ Tasks may not run (depends on BIOS settings)
- **Shutdown**: ❌ Tasks will NOT run

**Recommendation**: Use Sleep mode overnight

### Monthly Pipeline (2:30 AM on 1st)
1. Scrapes chamber calendar for current + next month
2. Classifies events as community/non-community
3. Filters out long-duration events (>60 days)
4. Exports to CSV with correct Central Time
5. Auto-uploads to WordPress (if `AUTO_UPLOAD=true`)
6. Sends email notification with results

### Health Check (Every 3 days at 6:30 AM)
1. Tests WordPress API connection
2. Counts upcoming events
3. Verifies calendar page loads
4. Sends email if issues detected
5. Optional: Email on success if `HEALTH_SEND_OK=true`

### Logs
All runs logged to: `c:\Users\scott\UWF-Code\EnvisionPerdido\output\logs\`
- `pipeline_YYYYMMDD_HHMMSS.log`
- `healthcheck_YYYYMMDD_HHMMSS.log`

## Alternative Options

### Option 1: Cloud VM (Always-On)
**Pros**: Never miss a scheduled run
**Cons**: Monthly cost (~$5-20/month)
- Azure VM, AWS EC2, or DigitalOcean Droplet
- Install Python + dependencies
- Use cron (Linux) or Task Scheduler (Windows)

### Option 2: GitHub Actions (Free)
**Pros**: Free, cloud-based, no local machine needed
**Cons**: Requires code changes, public repo (or paid private)
- Add `.github/workflows/monthly-pipeline.yml`
- Schedule with cron syntax
- Store credentials as GitHub Secrets

### Option 3: Power Automate Desktop (GUI)
**Pros**: User-friendly, already covered in earlier setup
**Cons**: Requires Power Automate license for unattended runs
- Cloud flow triggers desktop flow
- Can run on your machine or cloud-hosted machine

## Recommended: Task Scheduler (This Setup)

Best for your use case because:
- ✅ Free (no cloud costs)
- ✅ Runs on your existing machine
- ✅ Computer can sleep (doesn't need 24/7)
- ✅ Simple setup and monitoring
- ✅ Email notifications built-in

**Just keep your computer in Sleep mode overnight instead of shutting down.**

## BIOS Settings (Optional - For Wake from Sleep)

If tasks don't wake your computer:
1. Restart → Enter BIOS/UEFI (usually Del, F2, or F12)
2. Find "Power Management" or "ACPI"
3. Enable "Wake on RTC" or "Wake on Alarm"
4. Save and exit

Most modern Windows PCs have this enabled by default.

## Troubleshooting

### Tasks not running?
```powershell
# Check task status
Get-ScheduledTask -TaskName 'EnvisionPerdido_*' | Get-ScheduledTaskInfo

# View last run result
Get-ScheduledTask -TaskName 'EnvisionPerdido_*' | Select-Object TaskName, State, LastRunTime, LastTaskResult
```

### Check logs
```powershell
# View latest logs
cd c:\Users\scott\UWF-Code\EnvisionPerdido\output\logs
Get-ChildItem -Filter *.log | Sort-Object LastWriteTime -Descending | Select-Object -First 5
```

### Test manually
```powershell
# Health check
.\scripts\windows\run_health_check.ps1

# Pipeline
.\scripts\windows\run_pipeline.ps1
```

## Modify Schedule

To change timing, re-run setup script or edit in Task Scheduler GUI.

### Example: Change health check to weekly
```powershell
$Trigger = New-ScheduledTaskTrigger -Weekly -DaysOfWeek Monday -At "7:00 AM"
Set-ScheduledTask -TaskName "EnvisionPerdido_HealthCheck" -Trigger $Trigger
```

### Example: Change pipeline to 15th of month
Edit the task in Task Scheduler:
- Right-click task → Properties
- Triggers tab → Edit
- Change to run on day 15

## Uninstall Tasks

```powershell
Unregister-ScheduledTask -TaskName "EnvisionPerdido_HealthCheck" -Confirm:$false
Unregister-ScheduledTask -TaskName "EnvisionPerdido_MonthlyPipeline" -Confirm:$false
```
