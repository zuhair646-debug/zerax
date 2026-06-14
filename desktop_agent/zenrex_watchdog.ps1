# Zenrex Watchdog - keeps Desktop Agent + Farm Bot alive.
# Runs every 2 min via Task Scheduler. Hidden. No UI.
#
# Reads paths and pair code from $env:USERPROFILE\Zenrex-Agent\watchdog.cfg
# (key=value lines: AgentDir, FarmDir, Code, FarmPort)

$ErrorActionPreference = 'SilentlyContinue'

$CfgPath = Join-Path $env:USERPROFILE 'Zenrex-Agent\watchdog.cfg'
if (-not (Test-Path $CfgPath)) { exit 0 }

# Parse cfg
$cfg = @{}
Get-Content $CfgPath | ForEach-Object {
    if ($_ -match '^\s*([A-Za-z]+)\s*=\s*(.*)$') {
        $cfg[$Matches[1]] = $Matches[2].Trim()
    }
}
$AgentDir = $cfg['AgentDir']
$FarmDir  = $cfg['FarmDir']
$Code     = $cfg['Code']
$FarmPort = [int]($cfg['FarmPort'])
if (-not $AgentDir -or -not $FarmDir -or -not $Code -or -not $FarmPort) { exit 0 }

$LogFile = Join-Path $AgentDir 'watchdog.log'
function Log($m) {
    $line = '[' + (Get-Date -Format 'yyyy-MM-dd HH:mm:ss') + '] ' + $m
    Add-Content -Path $LogFile -Value $line
}

# Find pythonw (prefer hidden), fall back to python
$Py = (Get-Command pythonw -ErrorAction SilentlyContinue).Source
if (-not $Py) { $Py = (Get-Command python -ErrorAction SilentlyContinue).Source }
if (-not $Py) { Log 'ERR python not in PATH'; exit }

# 1) Desktop Agent alive?
$agentAlive = Get-CimInstance Win32_Process -Filter "Name='pythonw.exe' OR Name='python.exe'" |
    Where-Object { $_.CommandLine -match 'zenrex_agent\.py' }
if (-not $agentAlive) {
    Log 'agent dead, starting'
    Start-Process -FilePath $Py `
        -ArgumentList @((Join-Path $AgentDir 'zenrex_agent.py'), '--code', $Code) `
        -WorkingDirectory $AgentDir -WindowStyle Hidden
} else {
    Log 'agent ok'
}

# 2) Farm Bot port alive?
$portUp = $false
try {
    $tcp = New-Object System.Net.Sockets.TcpClient
    $iar = $tcp.BeginConnect('127.0.0.1', $FarmPort, $null, $null)
    if ($iar.AsyncWaitHandle.WaitOne(800)) {
        $tcp.EndConnect($iar); $portUp = $true; $tcp.Close()
    }
} catch {}

if (-not $portUp) {
    Log "farm port $FarmPort dead, starting zenrex_app.py"
    Start-Process -FilePath $Py `
        -ArgumentList @((Join-Path $FarmDir 'zenrex_app.py')) `
        -WorkingDirectory $FarmDir -WindowStyle Hidden `
        -RedirectStandardOutput (Join-Path $FarmDir 'app.stdout.log') `
        -RedirectStandardError (Join-Path $FarmDir 'app.stderr.log')
} else {
    Log 'farm ok'
}

# Trim log
if ((Test-Path $LogFile) -and ((Get-Item $LogFile).Length -gt 200000)) {
    Get-Content $LogFile -Tail 200 | Set-Content $LogFile
}
