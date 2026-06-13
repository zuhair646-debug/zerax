@echo off
REM ════════════════════════════════════════════════════════════════════
REM  Zenrex Desktop Agent  —  one-time .exe builder.
REM  Produces:  ZenrexDesktopAgent.exe  on the Desktop.
REM ════════════════════════════════════════════════════════════════════
setlocal
cd /d "%~dp0"

echo ════════════════════════════════════════════════════════════════════
echo   Building Zenrex Desktop Agent (.exe)
echo ════════════════════════════════════════════════════════════════════

if not exist ".venv\Scripts\python.exe" (
    echo Creating venv...
    python -m venv .venv
)

call ".venv\Scripts\python.exe" -m pip install --quiet --upgrade pip
call ".venv\Scripts\python.exe" -m pip install --quiet -r requirements.txt
call ".venv\Scripts\python.exe" -m pip install --quiet pyinstaller

echo.
echo Bundling into single .exe (this takes 1-2 minutes)...
call ".venv\Scripts\python.exe" -m PyInstaller ^
    --noconfirm ^
    --onefile ^
    --windowed ^
    --name "ZenrexDesktopAgent" ^
    --clean ^
    --hidden-import "pygetwindow" ^
    --hidden-import "mss" ^
    --hidden-import "websockets" ^
    --hidden-import "pyautogui" ^
    --hidden-import "PIL" ^
    --hidden-import "pyperclip" ^
    --collect-all "mss" ^
    --collect-all "websockets" ^
    --collect-all "pyautogui" ^
    zenrex_gui.pyw

if not exist "dist\ZenrexDesktopAgent.exe" (
    echo.
    echo BUILD FAILED. Check the messages above.
    pause
    exit /b 1
)

REM Move .exe to Desktop and clean up build artifacts
copy /Y "dist\ZenrexDesktopAgent.exe" "%USERPROFILE%\Desktop\ZenrexDesktopAgent.exe" >nul

echo.
echo ════════════════════════════════════════════════════════════════════
echo   DONE!  Your standalone app:
echo     %USERPROFILE%\Desktop\ZenrexDesktopAgent.exe
echo   Just double-click it — no Python or PowerShell needed anymore.
echo ════════════════════════════════════════════════════════════════════
echo.
pause
