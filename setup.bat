@echo off
setlocal enabledelayedexpansion
cd /d "%~dp0"

echo ==========================================
echo   Outlook PTO Extractor - One-click setup
echo ==========================================
echo.

REM --- 1. Locate a Python 3.11+ interpreter (skips the Microsoft Store stub) ---
call :detect_python
if defined PYEXE goto have_python

REM --- 1b. None found: auto-install via winget (user scope, silent) ---
echo [..] No Python 3.11+ found. Attempting automatic install via winget ...
where winget >nul 2>&1
if errorlevel 1 (
  echo [ERROR] winget is not available, so Python cannot be auto-installed.
  echo         Install Python 3.11+ from https://www.python.org/downloads/
  echo         ^(tick "Add python.exe to PATH"^), then re-run this script.
  echo.
  pause
  exit /b 1
)
winget install --id Python.Python.3.12 --scope user --silent --accept-source-agreements --accept-package-agreements
echo [..] Re-checking for Python ...
call :detect_python
if defined PYEXE goto have_python

echo [ERROR] Python still not found after the install attempt.
echo         Open a NEW terminal and run setup.bat again, or install
echo         manually from https://www.python.org/downloads/
echo.
pause
exit /b 1

:have_python
echo [OK] Using Python: !PYEXE!
!PYEXE! --version
echo.

REM --- 2. Create the virtual environment ---
if exist ".venv\Scripts\python.exe" (
  echo [OK] .venv already exists - skipping creation.
) else (
  echo [..] Creating virtual environment in .venv ...
  !PYEXE! -m venv .venv
  if errorlevel 1 (
    echo [ERROR] Failed to create the virtual environment.
    pause
    exit /b 1
  )
  echo [OK] Virtual environment created.
)
echo.

REM --- 3. Install dependencies ---
echo [..] Upgrading pip ...
".venv\Scripts\python.exe" -m pip install --upgrade pip
echo [..] Installing requirements ...
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 (
  echo [ERROR] Dependency installation failed.
  pause
  exit /b 1
)
echo.

echo ==========================================
echo   [OK] Setup complete.
echo ==========================================
echo.
echo Next steps:
echo   1. In Outlook, add the shared team calendar (Other Calendars).
echo   2. Edit config.yaml  -^>  set calendar owner / folder_name.
echo   3. Activate the venv in PowerShell:
echo        .\.venv\Scripts\Activate.ps1
echo   4. Run the spike to confirm the connection:
echo        python scripts\spike_read_calendar.py --start 2026-06-01 --end 2026-12-31
echo.
pause
exit /b 0

REM --- helper: find a Python 3.11+ interpreter, set PYEXE ---
:detect_python
set "PYEXE="
call :try_python "py -3"
if defined PYEXE goto :eof
for /d %%D in ("%LOCALAPPDATA%\Programs\Python\Python3*") do (
  call :try_python "%%D\python.exe"
  if defined PYEXE goto :eof
)
call :try_python "python"
goto :eof

REM --- helper: set PYEXE if %~1 is a working Python 3.11+ interpreter ---
:try_python
%~1 -c "import sys; sys.exit(0 if sys.version_info >= (3, 11) else 1)" >nul 2>&1
if not errorlevel 1 set "PYEXE=%~1"
goto :eof
