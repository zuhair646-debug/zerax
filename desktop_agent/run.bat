@echo off
REM Zenrex Desktop Agent — runner for Windows.
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
    echo Virtual environment missing. Run install.bat first.
    pause
    exit /b 1
)
".venv\Scripts\python.exe" zenrex_agent.py %*
