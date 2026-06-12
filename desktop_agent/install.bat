@echo off
REM Zenrex Desktop Agent — installer for Windows.
setlocal
cd /d "%~dp0"

echo ═══════════════════════════════════════════════════════════
echo   Zenrex Desktop Agent  Installer (Windows)
echo ═══════════════════════════════════════════════════════════

where python >nul 2>&1
if errorlevel 1 (
    echo Python not found in PATH.
    echo Install from https://www.python.org/downloads/  (check "Add to PATH").
    pause
    exit /b 1
)

if not exist ".venv" (
    echo Creating virtual environment...
    python -m venv .venv
)

echo Installing dependencies...
call ".venv\Scripts\python.exe" -m pip install --quiet --upgrade pip
call ".venv\Scripts\python.exe" -m pip install --quiet -r requirements.txt

echo.
echo Installation complete.
echo.
echo Next steps:
echo   1. In your Zenrex chat ask: "اربط جهازي"  ^(you'll get a 6-char code^)
echo   2. Run:  run.bat
echo   3. Paste the code when prompted.
echo.
pause
