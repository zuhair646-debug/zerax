# Zenrex Farm v0.6.0 - One-Click Installer
# ASCII-only to avoid PowerShell 5 encoding issues.
# Usage:
#   cd $env:USERPROFILE; iwr "https://ai-cinematic-hub-2.preview.emergentagent.com/api/desktop-agent/zenrex-farm/install.ps1" -OutFile install.ps1 -UseBasicParsing; powershell -ExecutionPolicy Bypass -File .\install.ps1

$ErrorActionPreference = "Stop"
$Tag = "[Zenrex]"
function S($m){ Write-Host "$Tag $m" -ForegroundColor Cyan }
function K($m){ Write-Host "$Tag [+] $m" -ForegroundColor Green }
function W($m){ Write-Host "$Tag [!] $m" -ForegroundColor Yellow }
function E($m){ Write-Host "$Tag [X] $m" -ForegroundColor Red }

Write-Host ""
Write-Host "==========================================" -ForegroundColor Magenta
Write-Host "  Zenrex Farm v0.6.0 - by Zuhair Abbas" -ForegroundColor Magenta
Write-Host "==========================================" -ForegroundColor Magenta
Write-Host ""

# 1) Install directory
$InstallDir = "$env:USERPROFILE\Zenrex-Farm"
S "Install dir: $InstallDir"
New-Item -ItemType Directory -Force -Path $InstallDir | Out-Null
Set-Location $InstallDir

# 2) Check Python
S "Checking Python..."
$PyVer = & python --version 2>&1
if ($LASTEXITCODE -ne 0) {
    E "Python not installed. Get it from https://python.org (3.11+)"
    E "IMPORTANT: tick 'Add Python to PATH' during install"
    exit 1
}
K "Python: $PyVer"

# 3) Install pip packages
S "Installing Python deps (may take 2-3 min)..."
$pkgs = @("fastapi", "uvicorn[standard]", "playwright",
          "pywebview", "pystray", "Pillow", "requests")
foreach ($p in $pkgs) {
    Write-Host "  -> $p"
    & python -m pip install --quiet --upgrade $p 2>&1 | Out-Null
}
K "All deps installed"

# 4) Playwright Chromium
S "Installing Chromium for Playwright (may take 1 min)..."
& python -m playwright install chromium 2>&1 | Out-Null
K "Chromium ready"

# 5) Download source files
$BaseUrl = if ($env:ZENREX_SOURCE_URL) { $env:ZENREX_SOURCE_URL }
           else { "https://ai-cinematic-hub-2.preview.emergentagent.com/api/desktop-agent/zenrex-farm" }
S "Downloading from: $BaseUrl"
foreach ($f in @("zenrex_farm.py", "zenrex_app.py")) {
    $dest = Join-Path $InstallDir $f
    try {
        Invoke-WebRequest -Uri "$BaseUrl/$f" -OutFile $dest -UseBasicParsing -TimeoutSec 30
        $size = (Get-Item $dest).Length
        K "Downloaded $f ($size bytes)"
    } catch {
        E "Failed to download $f"
        E ("  reason: " + $_.Exception.Message)
        exit 1
    }
}

# 6) Travian icon
$IconPath = Join-Path $InstallDir "zenrex_icon.ico"
S "Downloading Travian icon..."
$IconOk = $false
foreach ($url in @("https://www.travian.com/favicon.ico",
                   "https://lobby.legends.travian.com/favicon.ico")) {
    try {
        Invoke-WebRequest -Uri $url -OutFile $IconPath -UseBasicParsing -TimeoutSec 12
        if ((Get-Item $IconPath).Length -gt 500) { $IconOk = $true; break }
    } catch {}
}
if (-not $IconOk) {
    W "Icon download failed, generating fallback"
    $pyCode = "from PIL import Image, ImageDraw; img=Image.new('RGBA',(256,256),(15,20,35,255)); d=ImageDraw.Draw(img); d.ellipse([16,16,240,240],fill=(167,139,250,255)); img.save(r'$IconPath',sizes=[(256,256),(128,128),(64,64),(32,32),(16,16)])"
    python -c $pyCode 2>&1 | Out-Null
}
K "Icon: $IconPath"

# 7) Create desktop shortcut
S "Creating desktop shortcut..."
$Pythonw = (Get-Command pythonw -ErrorAction SilentlyContinue).Source
if (-not $Pythonw) { $Pythonw = (Get-Command python).Source }
$Launcher = Join-Path $InstallDir "zenrex_app.py"
$DesktopPath = [Environment]::GetFolderPath("Desktop")
$ShortcutPath = Join-Path $DesktopPath "Zenrex Farm.lnk"

$WSS = New-Object -ComObject WScript.Shell
$sc = $WSS.CreateShortcut($ShortcutPath)
$sc.TargetPath = $Pythonw
$sc.Arguments = "`"$Launcher`""
$sc.WorkingDirectory = $InstallDir
$sc.IconLocation = $IconPath
$sc.WindowStyle = 7
$sc.Description = "Zenrex Farm v0.6.0 - Travian Multi-Village Bot"
$sc.Save()
K "Shortcut: $ShortcutPath"

# 8) Start menu shortcut
$StartMenu = "$env:APPDATA\Microsoft\Windows\Start Menu\Programs\Zenrex Farm.lnk"
$sm = $WSS.CreateShortcut($StartMenu)
$sm.TargetPath = $Pythonw
$sm.Arguments = "`"$Launcher`""
$sm.WorkingDirectory = $InstallDir
$sm.IconLocation = $IconPath
$sm.WindowStyle = 7
$sm.Save()
K "Start menu entry added"

# 9) Done
Write-Host ""
Write-Host "==========================================" -ForegroundColor Yellow
Write-Host "  [+] Zenrex Farm v0.6.0 READY!" -ForegroundColor Yellow
Write-Host "==========================================" -ForegroundColor Yellow
Write-Host "  Path:  $InstallDir"
Write-Host "  Run:   Double-click 'Zenrex Farm' on Desktop"
Write-Host "  Or:    Search 'Zenrex' in Start menu"
Write-Host "==========================================" -ForegroundColor Yellow
Write-Host ""
$launch = Read-Host "Launch now? (Y/N)"
if ($launch -eq "Y" -or $launch -eq "y") {
    Start-Process $ShortcutPath
    Write-Host "[+] Launching... a Native window will open in a few seconds" -ForegroundColor Green
}
