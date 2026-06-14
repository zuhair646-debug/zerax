# Zenrex Desktop Agent - Full Reset + Install
# ================================================
# This script:
#   1. KILLS every running Python/Zenrex process
#   2. DELETES the old Zenrex-Farm folder (full clean)
#   3. Installs Desktop Agent (gives me remote control of your PC)
#   4. Asks you for a pairing code (you get it from me after this runs)
#
# Usage (PowerShell, no admin needed):
#   cd $env:USERPROFILE; iwr "https://ai-cinematic-hub-2.preview.emergentagent.com/api/desktop-agent/zenrex-farm/install_desktop_agent.ps1" -OutFile reset.ps1 -UseBasicParsing; powershell -ExecutionPolicy Bypass -File .\reset.ps1

$ErrorActionPreference = "Continue"
$Tag = "[Zenrex-Reset]"
function S($m){ Write-Host "$Tag $m" -ForegroundColor Cyan }
function K($m){ Write-Host "$Tag [+] $m" -ForegroundColor Green }
function W($m){ Write-Host "$Tag [!] $m" -ForegroundColor Yellow }

Write-Host ""
Write-Host "==========================================" -ForegroundColor Magenta
Write-Host "  Zenrex Desktop Agent - Full Reset" -ForegroundColor Magenta
Write-Host "==========================================" -ForegroundColor Magenta
Write-Host ""

# 1) Kill ALL Python processes
S "Killing every Python/Zenrex process..."
Stop-Process -Name pythonw,python -Force -ErrorAction SilentlyContinue
Start-Sleep -Seconds 2
K "Done"

# 2) Delete old Zenrex-Farm folder
$OldFolder = "$env:USERPROFILE\Zenrex-Farm"
if (Test-Path $OldFolder) {
    S "Deleting old folder: $OldFolder"
    Remove-Item -Recurse -Force $OldFolder -ErrorAction SilentlyContinue
    K "Removed"
}

# Remove old shortcut(s)
$Desktops = @(
    [Environment]::GetFolderPath("Desktop"),
    "$env:USERPROFILE\OneDrive\Desktop",
    "$env:USERPROFILE\OneDrive\Desktop_AR"
)
foreach ($d in $Desktops) {
    $lnk = Join-Path $d "Zenrex Farm.lnk"
    if (Test-Path $lnk) { Remove-Item -Force $lnk; K "Removed shortcut: $lnk" }
}
$startLnk = "$env:APPDATA\Microsoft\Windows\Start Menu\Programs\Zenrex Farm.lnk"
if (Test-Path $startLnk) { Remove-Item -Force $startLnk }

# 3) Fresh install dir
$InstallDir = "$env:USERPROFILE\Zenrex-Agent"
New-Item -ItemType Directory -Force -Path $InstallDir | Out-Null
Set-Location $InstallDir
S "Install dir: $InstallDir"

# 4) Python check
$PyVer = & python --version 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "[X] Python NOT installed. Get it from https://python.org" -ForegroundColor Red
    Write-Host "    IMPORTANT: tick 'Add Python to PATH'" -ForegroundColor Yellow
    exit 1
}
K "Python: $PyVer"

# 5) Install deps for Desktop Agent
S "Installing Python deps (pyautogui, mss, pillow, websockets)..."
$pkgs = @("pyautogui", "mss", "Pillow", "websockets", "requests")
foreach ($p in $pkgs) {
    Write-Host "  -> $p"
    & python -m pip install --quiet --upgrade $p 2>&1 | Out-Null
}
K "Deps installed"

# 6) Download Desktop Agent
$AgentUrl = "https://ai-cinematic-hub-2.preview.emergentagent.com/api/desktop-agent/agent-source"
$AgentPath = Join-Path $InstallDir "zenrex_agent.py"
S "Downloading Desktop Agent..."
try {
    Invoke-WebRequest -Uri $AgentUrl -OutFile $AgentPath -UseBasicParsing -TimeoutSec 30
    $size = (Get-Item $AgentPath).Length
    K "Downloaded zenrex_agent.py ($size bytes)"
} catch {
    Write-Host "[X] Failed: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}

# 7) Write config.json with the right server URL
$Config = @{
    server_ws = "wss://ai-cinematic-hub-2.preview.emergentagent.com/api/desktop-agent/ws"
} | ConvertTo-Json
Set-Content -Path (Join-Path $InstallDir "config.json") -Value $Config -Encoding UTF8
K "Config saved"

# 8) Ask for pairing code
Write-Host ""
Write-Host "==========================================" -ForegroundColor Yellow
Write-Host "  PAIRING CODE NEEDED" -ForegroundColor Yellow
Write-Host "==========================================" -ForegroundColor Yellow
Write-Host "  Send a message to me (Zenrex AI) saying:" -ForegroundColor White
Write-Host "    'give me a pairing code'" -ForegroundColor Cyan
Write-Host "  I will generate one and reply." -ForegroundColor White
Write-Host "  Then paste it below." -ForegroundColor White
Write-Host "==========================================" -ForegroundColor Yellow
Write-Host ""
$Code = Read-Host "Pairing code (e.g. ABC123)"
if (-not $Code) {
    Write-Host "[X] No code entered. Run the script again when you have one." -ForegroundColor Red
    exit 1
}

# 9) Create startup launcher (.bat) so it auto-runs on every boot (optional)
$LauncherBat = Join-Path $InstallDir "start_agent.bat"
$BatContent = @"
@echo off
cd /d "$InstallDir"
start "" pythonw zenrex_agent.py --code $Code
"@
Set-Content -Path $LauncherBat -Value $BatContent -Encoding ASCII

# 10) Desktop shortcut
$DesktopPath = [Environment]::GetFolderPath("Desktop")
$ShortcutPath = Join-Path $DesktopPath "Zenrex Agent.lnk"
$WSS = New-Object -ComObject WScript.Shell
$sc = $WSS.CreateShortcut($ShortcutPath)
$sc.TargetPath = $LauncherBat
$sc.WorkingDirectory = $InstallDir
$sc.WindowStyle = 7
$sc.Description = "Zenrex Desktop Agent - connects to Zenrex AI"
$sc.Save()
K "Shortcut: $ShortcutPath"

# 11) Start it now
S "Starting Desktop Agent with code $Code..."
Start-Process -FilePath "pythonw" -ArgumentList "zenrex_agent.py","--code",$Code -WorkingDirectory $InstallDir -WindowStyle Hidden
Start-Sleep -Seconds 3

# Verify connection
S "Verifying connection..."
Start-Sleep -Seconds 5
try {
    $r = Invoke-WebRequest -Uri "https://ai-cinematic-hub-2.preview.emergentagent.com/api/desktop-agent/active-list" -UseBasicParsing
    Write-Host $r.Content
} catch {
    W "Could not verify; check by asking Zenrex AI to check connection."
}

Write-Host ""
Write-Host "==========================================" -ForegroundColor Green
Write-Host "  [+] Desktop Agent ACTIVE!" -ForegroundColor Green
Write-Host "==========================================" -ForegroundColor Green
Write-Host "  Path:       $InstallDir"
Write-Host "  Started:    pythonw zenrex_agent.py --code $Code"
Write-Host "  Reconnect:  Double-click 'Zenrex Agent' on Desktop"
Write-Host "==========================================" -ForegroundColor Green
Write-Host ""
Write-Host "  Now tell Zenrex AI: 'I'm connected, do the work'" -ForegroundColor Cyan
