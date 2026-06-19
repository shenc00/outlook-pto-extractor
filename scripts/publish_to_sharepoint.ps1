<#
.SYNOPSIS
  Generate the PTO report and place it in the OneDrive-synced SharePoint folder.

.DESCRIPTION
  Designed to be run unattended by Windows Task Scheduler in the *interactive*
  logged-on session (so Outlook COM works). It runs the extractor, writing the
  workbook to the synced SharePoint location; the OneDrive client then uploads
  it. All output is logged to .\logs\refresh_<timestamp>.log.

  The output path comes from config (output.path) -- set it in config.local.yaml
  to your synced folder, e.g.:
      output:
        path: "C:/Users/<vmuser>/OneDrive - BD/.../DELIVER Domain/pto_report.xlsx"
  ...or override here with -OutFile.

.PARAMETER OutFile
  Optional .xlsx output path. Overrides config.output.path.
#>
param(
    [string]$OutFile,
    [string]$ProjectDir = (Split-Path -Parent $PSScriptRoot)
)

$ErrorActionPreference = "Stop"
$logDir = Join-Path $ProjectDir "logs"
New-Item -ItemType Directory -Force -Path $logDir | Out-Null
$logFile = Join-Path $logDir ("refresh_{0:yyyyMMdd_HHmmss}.log" -f (Get-Date))

Start-Transcript -Path $logFile | Out-Null
$exit = 0
try {
    Set-Location $ProjectDir
    $py = Join-Path $ProjectDir ".venv\Scripts\python.exe"
    if (-not (Test-Path $py)) { throw "venv python not found at $py - run setup.bat first." }

    $cliArgs = @("-m", "src.main")
    if ($OutFile) { $cliArgs += @("--out", $OutFile) }

    Write-Host "[$(Get-Date -Format s)] Running: $py $($cliArgs -join ' ')"
    & $py @cliArgs
    if ($LASTEXITCODE -ne 0) { throw "report generation failed (exit $LASTEXITCODE)" }

    Write-Host "[$(Get-Date -Format s)] OK - report written; OneDrive will sync it to SharePoint."
}
catch {
    Write-Host "[$(Get-Date -Format s)] ERROR: $_"
    $exit = 1
}
finally {
    Stop-Transcript | Out-Null
}
exit $exit
