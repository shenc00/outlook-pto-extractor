<#
.SYNOPSIS
  Install a portable Python (no MSI, no admin) from the NuGet redistributable.

.DESCRIPTION
  Last-resort fallback used by setup.bat when MSI installs are blocked by policy
  (Windows Installer error 1625). The NuGet "python" package is a full CPython
  (pip + venv capable) shipped as a plain .nupkg (a zip), so it sidesteps the
  installer entirely. Extracted into %LOCALAPPDATA%\Programs\Python\Python312
  so setup.bat's detector finds it.

  NOTE: if execution itself is locked down (AppLocker / WDAC blocking exes from
  user-writable folders) this will also fail -- then Python must be installed by
  IT (e.g. via Company Portal / Software Center).
#>
$ErrorActionPreference = "Stop"
$version = "3.12.10"
$dest = Join-Path $env:LOCALAPPDATA "Programs\Python\Python312"
$zip  = Join-Path $env:TEMP "python.$version.nupkg.zip"
$tmp  = Join-Path $env:TEMP "python_portable_$version"

try {
    if (Test-Path (Join-Path $dest "python.exe")) {
        Write-Host "Portable Python already present at $dest"
        exit 0
    }
    [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
    $url = "https://api.nuget.org/v3-flatcontainer/python/$version/python.$version.nupkg"
    Write-Host "Downloading portable Python from $url ..."
    Invoke-WebRequest -Uri $url -OutFile $zip -UseBasicParsing

    if (Test-Path $tmp) { Remove-Item $tmp -Recurse -Force }
    Write-Host "Extracting ..."
    Expand-Archive -Path $zip -DestinationPath $tmp -Force

    $tools = Join-Path $tmp "tools"
    if (-not (Test-Path (Join-Path $tools "python.exe"))) {
        throw "python.exe not found in the package (looked in $tools)"
    }
    New-Item -ItemType Directory -Force -Path $dest | Out-Null
    Copy-Item -Path (Join-Path $tools "*") -Destination $dest -Recurse -Force

    $py = Join-Path $dest "python.exe"
    Write-Host "Bootstrapping pip ..."
    & $py -m ensurepip --upgrade | Out-Null
    Write-Host "Portable Python ready:"
    & $py --version
    exit 0
}
catch {
    Write-Host "ERROR: $_"
    exit 1
}
finally {
    if (Test-Path $zip) { Remove-Item $zip -Force -ErrorAction SilentlyContinue }
    if (Test-Path $tmp) { Remove-Item $tmp -Recurse -Force -ErrorAction SilentlyContinue }
}
