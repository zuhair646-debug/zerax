# Zenrex Super Install v1.0 - All-in-One Self-Healing Installer
# ================================================================
# What this does (one-shot, then leaves your PC running it forever):
#   1) Kills every old Zenrex process cleanly
#   2) Downloads the latest Desktop Agent (zenrex_agent.py)
#      + the Farm Bot (zenrex_farm.py v0.8.3 + zenrex_app.py)
#   3) Installs all Python deps and the Playwright Chromium browser
#   4) Saves your pairing code for auto-reconnect
#   5) Creates a Windows Scheduled Task that runs every 2 minutes:
#        - If the Desktop Agent crashed, restart it
#        - If the Farm Bot crashed (port 7870 dead), restart it
#        - All hidden in the background (no terminal windows)
#   6) Also creates an "At-Logon" trigger so it survives reboots
#   7) Launches both immediately and opens the dashboard at http://127.0.0.1:7870
#
# USAGE (PowerShell, NO admin needed):
#   cd $env:USERPROFILE; iwr "https://ai-cinematic-hub-2.preview.emergentagent.com/api/desktop-agent/zenrex-farm/zenrex_super_install.ps1" -OutFile super.ps1 -UseBasicParsing; powershell -ExecutionPolicy Bypass -File .\super.ps1

$ErrorActionPreference = "Continue"
$ProgressPreference = "SilentlyContinue"
$Tag = "[Zenrex-Super]"
function S($m){ Write-Host "$Tag $m" -ForegroundColor Cyan }
function K($m){ Write-Host "$Tag [OK] $m" -ForegroundColor Green }
function W($m){ Write-Host "$Tag [!] $m" -ForegroundColor Yellow }
function E($m){ Write-Host "$Tag [X] $m" -ForegroundColor Red }

Write-Host ""
Write-Host "===========================================" -ForegroundColor Magenta
Write-Host "  Zenrex SUPER Installer - Self-Healing" -ForegroundColor Magenta
Write-Host "  Agent + Farm + Watchdog (one click)" -ForegroundColor Magenta
Write-Host "===========================================" -ForegroundColor Magenta
Write-Host ""

# Configuration
$BaseUrl   = "https://ai-cinematic-hub-2.preview.emergentagent.com/api/desktop-agent"
$AgentDir  = "$env:USERPROFILE\Zenrex-Agent"
$FarmDir   = "$env:USERPROFILE\Zenrex-Farm"
$WsUrl     = "wss://ai-cinematic-hub-2.preview.emergentagent.com/api/desktop-agent/ws"
$FarmPort  = 7870

# 1) Kill old processes (gentle - only matching ones)
S "Stopping any old Zenrex processes..."
Get-CimInstance Win32_Process -Filter "Name='pythonw.exe' OR Name='python.exe'" -ErrorAction SilentlyContinue |
    Where-Object { $_.CommandLine -match "zenrex_(agent|app|farm)" } |
    ForEach-Object {
        Write-Host ("  kill PID " + $_.ProcessId)
        Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue
    }
Start-Sleep -Seconds 2
K "Cleaned"

# 2) Ensure dirs exist
New-Item -ItemType Directory -Force -Path $AgentDir | Out-Null
New-Item -ItemType Directory -Force -Path $FarmDir  | Out-Null

# 3) Check Python
S "Checking Python..."
$PyVer = & python --version 2>&1
if ($LASTEXITCODE -ne 0) {
    E "Python NOT installed. Install Python 3.11+ from https://python.org"
    E "IMPORTANT: tick 'Add Python to PATH' during install."
    Read-Host "Press Enter to exit"
    exit 1
}
K "Python: $PyVer"

# 4) Install deps for BOTH agent and farm
S "Installing Python packages (may take 1-3 min the first time)..."
$pkgs = @("pyautogui","mss","Pillow","websockets","requests","pyperclip","pygetwindow",
          "fastapi","uvicorn[standard]","httpx","playwright","pywebview","pystray")
foreach ($p in $pkgs) {
    Write-Host "  -> $p"
    & python -m pip install --quiet --upgrade --no-input $p 2>&1 | Out-Null
}
K "All Python deps ready"

S "Installing Playwright Chromium browser (skip if already done)..."
& python -m playwright install chromium 2>&1 | Out-Null
K "Chromium ready"

# 5) Download latest source files
S "Downloading latest sources..."
$downloads = @(
    @{ url = "$BaseUrl/agent-source";              dst = "$AgentDir\zenrex_agent.py" },
    @{ url = "$BaseUrl/zenrex-farm/zenrex_farm.py"; dst = "$FarmDir\zenrex_farm.py" },
    @{ url = "$BaseUrl/zenrex-farm/zenrex_app.py";  dst = "$FarmDir\zenrex_app.py"  }
)
foreach ($d in $downloads) {
    try {
        Invoke-WebRequest -Uri $d.url -OutFile $d.dst -UseBasicParsing -TimeoutSec 45
        $sz = (Get-Item $d.dst).Length
        K ("Downloaded " + (Split-Path $d.dst -Leaf) + " ($sz bytes)")
    } catch {
        E ("Download failed: " + (Split-Path $d.dst -Leaf) + " => " + $_.Exception.Message)
        Read-Host "Press Enter to exit"
        exit 1
    }
}

# 6) Save agent server config
$Config = @{ server_ws = $WsUrl } | ConvertTo-Json
Set-Content -Path (Join-Path $AgentDir "config.json") -Value $Config -Encoding UTF8

# 7) Ask for pairing code (use cached if present)
$CodeFile = Join-Path $AgentDir "pair_code.txt"
$Code = $null
if (Test-Path $CodeFile) {
    $Code = (Get-Content $CodeFile -Raw).Trim()
    if ($Code) { K "Reusing saved pairing code: $Code" }
}
if (-not $Code) {
    Write-Host ""
    Write-Host "  PAIRING CODE NEEDED" -ForegroundColor Yellow
    Write-Host "  Tell Zenrex AI in chat: 'give me a pairing code'" -ForegroundColor White
    Write-Host "  Then paste the 6-char code below." -ForegroundColor White
    $Code = (Read-Host "  Pairing code").Trim()
    if (-not $Code) { E "No code entered. Exiting."; exit 1 }
    Set-Content -Path $CodeFile -Value $Code -Encoding ASCII
    K "Code saved to $CodeFile"
}

# 8) Write the watchdog script
$WatchdogPath = Join-Path $AgentDir "zenrex_watchdog.ps1"
$WatchdogContent = @"
# Zenrex Watchdog - runs every 2 min via Task Scheduler.
# Keeps both Desktop Agent and Farm Bot alive. Hidden, no UI.
`$ErrorActionPreference = 'SilentlyContinue'

`$AgentDir = '$AgentDir'
`$FarmDir  = '$FarmDir'
`$Code     = '$Code'
`$FarmPort = $FarmPort
`$LogFile  = Join-Path `$AgentDir 'watchdog.log'

function Log(`$m) {
    `$line = ('[' + (Get-Date -Format 'yyyy-MM-dd HH:mm:ss') + '] ' + `$m)
    Add-Content -Path `$LogFile -Value `$line
}

# Find pythonw (prefer hidden), fall back to python
`$Py = (Get-Command pythonw -ErrorAction SilentlyContinue).Source
if (-not `$Py) { `$Py = (Get-Command python -ErrorAction SilentlyContinue).Source }
if (-not `$Py) { Log 'ERR: python not in PATH'; exit }

# 1) Desktop Agent alive?
`$agentAlive = Get-CimInstance Win32_Process -Filter `"Name='pythonw.exe' OR Name='python.exe'`" |
    Where-Object { `$_.CommandLine -match 'zenrex_agent\.py' }
if (-not `$agentAlive) {
    Log 'Agent dead, starting...'
    Start-Process -FilePath `$Py -ArgumentList @((Join-Path `$AgentDir 'zenrex_agent.py'), '--code', `$Code) -WorkingDirectory `$AgentDir -WindowStyle Hidden
} else {
    Log 'Agent OK'
}

# 2) Farm Bot port 7870 alive?
`$portUp = `$false
try {
    `$tcp = New-Object System.Net.Sockets.TcpClient
    `$iar = `$tcp.BeginConnect('127.0.0.1', `$FarmPort, `$null, `$null)
    if (`$iar.AsyncWaitHandle.WaitOne(800)) {
        `$tcp.EndConnect(`$iar); `$portUp = `$true; `$tcp.Close()
    }
} catch {}

if (-not `$portUp) {
    Log 'Farm port 7870 dead, starting zenrex_app.py...'
    Start-Process -FilePath `$Py -ArgumentList @((Join-Path `$FarmDir 'zenrex_app.py')) -WorkingDirectory `$FarmDir -WindowStyle Hidden -RedirectStandardOutput (Join-Path `$FarmDir 'app.stdout.log') -RedirectStandardError (Join-Path `$FarmDir 'app.stderr.log')
} else {
    Log 'Farm OK'
}

# Trim log if huge
if ((Test-Path `$LogFile) -and ((Get-Item `$LogFile).Length -gt 200000)) {
    Get-Content `$LogFile -Tail 200 | Set-Content `$LogFile
}
"@
Set-Content -Path $WatchdogPath -Value $WatchdogContent -Encoding ASCII
K "Watchdog: $WatchdogPath"

# 9) Register Scheduled Task: at logon + every 2 min
S "Registering Scheduled Task 'ZenrexWatchdog' (runs every 2 min)..."
try {
    Unregister-ScheduledTask -TaskName "ZenrexWatchdog" -Confirm:$false -ErrorAction SilentlyContinue
    $taskAction = New-ScheduledTaskAction -Execute "powershell.exe" `
        -Argument "-NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File `"$WatchdogPath`""
    $t1 = New-ScheduledTaskTrigger -AtLogOn -User "$env:USERNAME"
    $t2 = New-ScheduledTaskTrigger -Once (Get-Date).AddMinutes(1) `
        -RepetitionInterval (New-TimeSpan -Minutes 2)
    $settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -DontStopOnIdleEnd `
        -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -MultipleInstances IgnoreNew
    Register-ScheduledTask -TaskName "ZenrexWatchdog" `
        -Action $taskAction -Trigger @($t1, $t2) `
        -Settings $settings -User "$env:USERNAME" -RunLevel Limited -Force | Out-Null
    K "Scheduled Task registered"
} catch {
    W ("Task register failed: " + $_.Exception.Message)
    W "Falling back to Startup folder shortcut"
    $startup = [Environment]::GetFolderPath("Startup")
    $bat = Join-Path $AgentDir "start_watchdog.bat"
    Set-Content -Path $bat -Value "@echo off`r`nstart `"`" /min powershell -NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File `"$WatchdogPath`"" -Encoding ASCII
    Copy-Item $bat (Join-Path $startup "ZenrexWatchdog.bat") -Force
    K "Startup fallback installed"
}

# 10) Desktop shortcuts (clickable manual start)
$DesktopPath = [Environment]::GetFolderPath("Desktop")
$AgentLnk = Join-Path $DesktopPath "Zenrex Agent.lnk"
$DashLnk  = Join-Path $DesktopPath "Zenrex Dashboard.url"
$WSS = New-Object -ComObject WScript.Shell
$sc = $WSS.CreateShortcut($AgentLnk)
$sc.TargetPath = "powershell.exe"
$sc.Arguments = "-NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File `"$WatchdogPath`""
$sc.WorkingDirectory = $AgentDir
$sc.WindowStyle = 7
$sc.Description = "Run Zenrex Watchdog (starts agent + farm)"
$sc.Save()
"[InternetShortcut]`r`nURL=http://127.0.0.1:$FarmPort/" | Set-Content -Path $DashLnk -Encoding ASCII
K "Desktop shortcuts created"

# 11) Trigger watchdog now (in background)
S "Starting watchdog NOW..."
Start-Process -FilePath "powershell.exe" `
    -ArgumentList @("-NoProfile","-WindowStyle","Hidden","-ExecutionPolicy","Bypass","-File",$WatchdogPath) `
    -WindowStyle Hidden

# Run it twice to ensure both processes get started (2nd pass picks up the farm if first only launched agent)
Start-Sleep -Seconds 6
Start-Process -FilePath "powershell.exe" `
    -ArgumentList @("-NoProfile","-WindowStyle","Hidden","-ExecutionPolicy","Bypass","-File",$WatchdogPath) `
    -WindowStyle Hidden

# 12) Wait for things to come up
S "Waiting for services to start (up to 30s)..."
$ready = $false
for ($i = 0; $i -lt 15; $i++) {
    Start-Sleep -Seconds 2
    try {
        $r = Invoke-WebRequest -Uri "http://127.0.0.1:$FarmPort/api/health" -UseBasicParsing -TimeoutSec 2
        if ($r.StatusCode -eq 200) { $ready = $true; break }
    } catch {}
}
if ($ready) {
    K "Farm dashboard is UP on http://127.0.0.1:$FarmPort"
} else {
    W "Farm dashboard not responding yet — watchdog will retry every 2 min."
    W "Check log: $AgentDir\watchdog.log"
}

# 13) Open dashboard
Start-Process "http://127.0.0.1:$FarmPort/"

Write-Host ""
Write-Host "===========================================" -ForegroundColor Green
Write-Host "  [DONE] Zenrex SUPER install complete." -ForegroundColor Green
Write-Host "===========================================" -ForegroundColor Green
Write-Host "  Agent dir:  $AgentDir"
Write-Host "  Farm dir:   $FarmDir"
Write-Host "  Watchdog:   runs every 2 min (Task Scheduler)"
Write-Host "  Dashboard:  http://127.0.0.1:$FarmPort/"
Write-Host "  Pair code:  $Code  (saved at $CodeFile)"
Write-Host ""
Write-Host "  From now on: even if your PC sleeps/restarts,"
Write-Host "  both services will come back automatically."
Write-Host "===========================================" -ForegroundColor Green
