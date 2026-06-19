<#
.SYNOPSIS
  Register a Windows scheduled task that refreshes the PTO report every weekday.

.DESCRIPTION
  Creates a task that runs publish_to_sharepoint.ps1 Mon-Fri at the given time,
  in the INTERACTIVE logged-on session. Interactive (not "run whether logged on
  or not") is REQUIRED -- Outlook COM does not work from session 0. Pair this
  with VM auto-logon so a session is always present.

  Run this script once, from an elevated PowerShell, on the VM:
      powershell -ExecutionPolicy Bypass -File scripts\register_scheduled_task.ps1 -At 06:00

.PARAMETER At        Time of day (HH:mm). Default 06:00.
.PARAMETER TaskName  Scheduled task name. Default "PTO Report Daily Refresh".
.PARAMETER OutFile   Optional .xlsx output path passed through to the job.
#>
param(
    [string]$At = "06:00",
    [string]$TaskName = "PTO Report Daily Refresh",
    [string]$OutFile,
    [string]$ProjectDir = (Split-Path -Parent $PSScriptRoot)
)

$script = Join-Path $ProjectDir "scripts\publish_to_sharepoint.ps1"
if (-not (Test-Path $script)) { throw "Cannot find $script" }

$inner = "-NoProfile -ExecutionPolicy Bypass -File `"$script`""
if ($OutFile) { $inner += " -OutFile `"$OutFile`"" }

$action  = New-ScheduledTaskAction -Execute "powershell.exe" -Argument $inner -WorkingDirectory $ProjectDir
$trigger = New-ScheduledTaskTrigger -Weekly -DaysOfWeek Monday,Tuesday,Wednesday,Thursday,Friday -At $At
$settings = New-ScheduledTaskSettingsSet `
    -StartWhenAvailable `
    -ExecutionTimeLimit (New-TimeSpan -Hours 1) `
    -MultipleInstances IgnoreNew
# Interactive token of the current user => runs in the live desktop session
# where Outlook is signed in. RunLevel Limited (no admin needed for the job).
$principal = New-ScheduledTaskPrincipal -UserId "$env:USERDOMAIN\$env:USERNAME" `
    -LogonType Interactive -RunLevel Limited

Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger `
    -Settings $settings -Principal $principal -Force | Out-Null

Write-Host "Registered task '$TaskName' - weekdays at $At (interactive session)."
Write-Host "Test it now with:  Start-ScheduledTask -TaskName '$TaskName'"
Write-Host "Then check the newest file in: $ProjectDir\logs"
