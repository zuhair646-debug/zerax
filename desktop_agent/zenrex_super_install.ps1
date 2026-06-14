# Zenrex Super Install v2 - All-in-One Self-Healing Installer
# No embedded here-strings. Watchdog is downloaded as a separate file.
#
# USAGE (PowerShell, NO admin):
#   cd $env:USERPROFILE; iwr "https://ai-cinematic-hub-2.preview.emergentagent.com/api/desktop-agent/zenrex-farm/zenrex_super_install.ps1" -OutFile super.ps1 -UseBasicParsing; powershell -ExecutionPolicy Bypass -File .\super.ps1

$ErrorActionPreference = "Continue"
$ProgressPreference = "SilentlyContinue"
function S($m){ Write-Host "[Zenrex] $m" -ForegroundColor Cyan }
function K($m){ Write-Host "[Zenrex] [OK] $m" -ForegroundColor Green }
function W($m){ Write-Host "[Zenrex] [!]  $m" -ForegroundColor Yellow }
function E($m){ Write-Host "[Zenrex] [X]  $m" -ForegroundColor Red }

Write-Host ""
Write-Host "==========================================="
Write-Host "  Zenrex SUPER Installer - Self-Healing"
Write-Host "  Agent + Farm + Watchdog (one click)"
Write-Host "==========================================="
Write-Host ""

$BaseUrl   = "https://ai-cinematic-hub-2.preview.emergentagent.com/api/desktop-agent"
$AgentDir  = Join-Path $env:USERPROFILE "Zenrex-Agent"
$FarmDir   = Join-Path $env:USERPROFILE "Zenrex-Farm"
$WsUrl     = "wss://ai-cinematic-hub-2.preview.emergentagent.com/api/desktop-agent/ws"
$FarmPort  = 7870

# 1) Kill old zenrex python processes
S "Stopping any old Zenrex processes..."
Get-CimInstance Win32_Process -Filter "Name='pythonw.exe' OR Name='python.exe'" -ErrorAction SilentlyContinue |
    Where-Object { $_.CommandLine -match "zenrex_(agent|app|farm)" } |
    ForEach-Object {
        Write-Host ("  kill PID " + $_.ProcessId)
        Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue
    }
Start-Sleep -Seconds 2
K "Cleaned"

# 2) Dirs
New-Item -ItemType Directory -Force -Path $AgentDir | Out-Null
New-Item -ItemType Directory -Force -Path $FarmDir  | Out-Null

# 3) Python check
S "Checking Python..."
$PyVer = & python --version 2>&1
if ($LASTEXITCODE -ne 0) {
    E "Python NOT installed. Install Python 3.11+ from https://python.org"
    E "IMPORTANT: tick 'Add Python to PATH' during install."
    Read-Host "Press Enter to exit"
    exit 1
}
K ("Python: " + $PyVer)

# 4) Install deps
S "Installing Python packages (1-3 min)..."
$pkgs = @("pyautogui","mss","Pillow","websockets","requests","pyperclip","pygetwindow",
          "fastapi","uvicorn[standard]","httpx","playwright","pywebview","pystray")
foreach ($p in $pkgs) {
    Write-Host ("  -> " + $p)
    & python -m pip install --quiet --upgrade --no-input $p 2>&1 | Out-Null
}
K "All Python deps ready"

S "Installing Playwright Chromium..."
& python -m playwright install chromium 2>&1 | Out-Null
K "Chromium ready"

# 5) Download source files
S "Downloading latest sources..."
$downloads = @(
    @{ url = ($BaseUrl + "/agent-source");                  dst = (Join-Path $AgentDir "zenrex_agent.py") },
    @{ url = ($BaseUrl + "/zenrex-farm/zenrex_farm.py");    dst = (Join-Path $FarmDir  "zenrex_farm.py") },
    @{ url = ($BaseUrl + "/zenrex-farm/zenrex_app.py");     dst = (Join-Path $FarmDir  "zenrex_app.py")  },
    @{ url = ($BaseUrl + "/zenrex-farm/zenrex_watchdog.ps1"); dst = (Join-Path $AgentDir "zenrex_watchdog.ps1") }
)
foreach ($d in $downloads) {
    try {
        Invoke-WebRequest -Uri $d.url -OutFile $d.dst -UseBasicParsing -TimeoutSec 45
        $sz = (Get-Item $d.dst).Length
        K ("Downloaded " + (Split-Path $d.dst -Leaf) + " (" + $sz + " bytes)")
    } catch {
        E ("Download failed: " + (Split-Path $d.dst -Leaf) + " => " + $_.Exception.Message)
        Read-Host "Press Enter to exit"
        exit 1
    }
}

# 6) Agent config.json (server URL)
$Config = @{ server_ws = $WsUrl } | ConvertTo-Json
Set-Content -Path (Join-Path $AgentDir "config.json") -Value $Config -Encoding UTF8

# 7) Pair code (reuse saved if present, else ask)
$CodeFile = Join-Path $AgentDir "pair_code.txt"
$Code = $null
if (Test-Path $CodeFile) {
    $Code = (Get-Content $CodeFile -Raw).Trim()
    if ($Code) { K ("Reusing saved pairing code: " + $Code) }
}
if (-not $Code) {
    Write-Host ""
    Write-Host "  PAIRING CODE NEEDED"
    Write-Host "  Tell Zenrex AI in chat: 'give me a pairing code'"
    Write-Host "  Then paste the 6-char code below."
    $Code = (Read-Host "  Pairing code").Trim()
    if (-not $Code) { E "No code entered."; exit 1 }
    Set-Content -Path $CodeFile -Value $Code -Encoding ASCII
    K ("Code saved to " + $CodeFile)
}

# 8) Write watchdog.cfg (consumed by zenrex_watchdog.ps1)
$cfgLines = @(
    ("AgentDir=" + $AgentDir),
    ("FarmDir="  + $FarmDir),
    ("Code="     + $Code),
    ("FarmPort=" + $FarmPort)
)
Set-Content -Path (Join-Path $AgentDir "watchdog.cfg") -Value ($cfgLines -join "`r`n") -Encoding ASCII
K "watchdog.cfg written"

# 9) Register Scheduled Task
S "Registering Scheduled Task 'ZenrexWatchdog'..."
$WatchdogPath = Join-Path $AgentDir "zenrex_watchdog.ps1"
try {
    Unregister-ScheduledTask -TaskName "ZenrexWatchdog" -Confirm:$false -ErrorAction SilentlyContinue
    $taskAction = New-ScheduledTaskAction -Execute "powershell.exe" -Argument ("-NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File `"" + $WatchdogPath + "`"")
    $t1 = New-ScheduledTaskTrigger -AtLogOn -User $env:USERNAME
    $t2 = New-ScheduledTaskTrigger -Once (Get-Date).AddMinutes(1) -RepetitionInterval (New-TimeSpan -Minutes 2)
    $settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -DontStopOnIdleEnd -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -MultipleInstances IgnoreNew
    Register-ScheduledTask -TaskName "ZenrexWatchdog" -Action $taskAction -Trigger @($t1, $t2) -Settings $settings -User $env:USERNAME -RunLevel Limited -Force | Out-Null
    K "Scheduled Task registered"
} catch {
    W ("Task register failed: " + $_.Exception.Message)
    W "Falling back to Startup folder shortcut"
    $startup = [Environment]::GetFolderPath("Startup")
    $bat = Join-Path $AgentDir "start_watchdog.bat"
    $batLines = @(
        "@echo off",
        ("start `"`" /min powershell -NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File `"" + $WatchdogPath + "`"")
    )
    Set-Content -Path $bat -Value ($batLines -join "`r`n") -Encoding ASCII
    Copy-Item $bat (Join-Path $startup "ZenrexWatchdog.bat") -Force
    K "Startup fallback installed"
}

# 10) Desktop shortcuts
$DesktopPath = [Environment]::GetFolderPath("Desktop")
$AgentLnk = Join-Path $DesktopPath "Zenrex Agent.lnk"
$DashLnk  = Join-Path $DesktopPath "Zenrex Dashboard.url"
$WSS = New-Object -ComObject WScript.Shell
$sc = $WSS.CreateShortcut($AgentLnk)
$sc.TargetPath = "powershell.exe"
$sc.Arguments = ("-NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File `"" + $WatchdogPath + "`"")
$sc.WorkingDirectory = $AgentDir
$sc.WindowStyle = 7
$sc.Description = "Run Zenrex Watchdog (starts agent + farm)"
$sc.Save()
$urlLines = @("[InternetShortcut]", ("URL=http://127.0.0.1:" + $FarmPort + "/"))
Set-Content -Path $DashLnk -Value ($urlLines -join "`r`n") -Encoding ASCII
K "Desktop shortcuts created"

# 11) Run watchdog NOW (twice with a small gap to start both services)
S "Starting watchdog NOW..."
Start-Process -FilePath "powershell.exe" -ArgumentList @("-NoProfile","-WindowStyle","Hidden","-ExecutionPolicy","Bypass","-File",$WatchdogPath) -WindowStyle Hidden
Start-Sleep -Seconds 6
Start-Process -FilePath "powershell.exe" -ArgumentList @("-NoProfile","-WindowStyle","Hidden","-ExecutionPolicy","Bypass","-File",$WatchdogPath) -WindowStyle Hidden

# 12) Wait for farm to come up
S "Waiting for services (up to 40s)..."
$ready = $false
for ($i = 0; $i -lt 20; $i++) {
    Start-Sleep -Seconds 2
    try {
        $r = Invoke-WebRequest -Uri ("http://127.0.0.1:" + $FarmPort + "/api/health") -UseBasicParsing -TimeoutSec 2
        if ($r.StatusCode -eq 200) { $ready = $true; break }
    } catch {}
}
if ($ready) {
    K ("Farm dashboard UP on http://127.0.0.1:" + $FarmPort)
} else {
    W "Farm not responding yet - watchdog will retry every 2 min."
    W ("Log: " + (Join-Path $AgentDir "watchdog.log"))
}

# 13) Open dashboard
Start-Process ("http://127.0.0.1:" + $FarmPort + "/")

Write-Host ""
Write-Host "==========================================="
Write-Host "  [DONE] Zenrex SUPER install complete."
Write-Host "==========================================="
Write-Host ("  Agent dir: " + $AgentDir)
Write-Host ("  Farm dir:  " + $FarmDir)
Write-Host "  Watchdog:  every 2 min (Task Scheduler)"
Write-Host ("  Dashboard: http://127.0.0.1:" + $FarmPort + "/")
Write-Host ("  Pair code: " + $Code)
Write-Host ""
Write-Host "  Even after sleep/restart, services auto-recover."
Write-Host "==========================================="
