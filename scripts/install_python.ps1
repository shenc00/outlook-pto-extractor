<#
.SYNOPSIS
  Download and silently install Python (per-user) from python.org.

.DESCRIPTION
  Fallback used by setup.bat when winget is not available. Installs for the
  current user (no admin), adds python to PATH, and includes the py launcher
  and pip. Per-user install lands in %LOCALAPPDATA%\Programs\Python\Python312,
  which setup.bat's detector then finds.
#>
$ErrorActionPreference = "Stop"
$version   = "3.12.10"
$url       = "https://www.python.org/ftp/python/$version/python-$version-amd64.exe"
$installer = Join-Path $env:TEMP "python-$version-amd64.exe"

try {
    [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
    Write-Host "Downloading $url ..."
    Invoke-WebRequest -Uri $url -OutFile $installer -UseBasicParsing
    Write-Host "Installing Python $version (per-user, silent) ..."
    $p = Start-Process -FilePath $installer -Wait -PassThru -ArgumentList @(
        "/quiet", "InstallAllUsers=0", "PrependPath=1", "Include_launcher=1", "Include_pip=1"
    )
    if ($p.ExitCode -ne 0) { throw "installer exited with code $($p.ExitCode)" }
    Write-Host "Python install complete."
    exit 0
}
catch {
    Write-Host "ERROR: $_"
    exit 1
}
finally {
    if (Test-Path $installer) { Remove-Item $installer -Force -ErrorAction SilentlyContinue }
}
