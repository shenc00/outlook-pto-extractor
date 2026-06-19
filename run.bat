@echo off
setlocal enabledelayedexpansion
cd /d "%~dp0"

echo ==========================================
echo   Outlook PTO Extractor - Generate report
echo ==========================================
echo.

REM --- Ensure the environment is set up ---
if not exist ".venv\Scripts\python.exe" (
  echo [!] Virtual environment not found.
  echo     Run setup.bat first, then try again.
  echo.
  pause
  exit /b 1
)

REM --- Default date range = the current calendar year ---
for /f %%y in ('powershell -NoProfile -Command "Get-Date -Format yyyy"') do set "YEAR=%%y"
set "START=%YEAR%-01-01"
set "END=%YEAR%-12-31"

set /p "START=Start date (YYYY-MM-DD) [%START%]: "
set /p "END=End date   (YYYY-MM-DD) [%END%]: "

set "OUT=pto_report.xlsx"
echo.
echo [..] Generating %OUT% for %START% to %END% ...
echo.

".venv\Scripts\python.exe" -m src.main --start %START% --end %END% --out "%OUT%"
if errorlevel 1 (
  echo.
  echo [ERROR] Report generation failed - see the message above.
  echo         Common causes: Outlook is closed, the shared calendar is
  echo         not added, or %OUT% is open in Excel. Close it and retry.
  echo.
  pause
  exit /b 1
)

echo.
echo [OK] Done. Opening %OUT% ...
start "" "%OUT%"
exit /b 0
