# Zenrex Farm — One-Click Installer (v0.6.0)
# ═════════════════════════════════════════════════════
# تثبيت كامل من الصفر — يخلق مجلد جديد ويحط شورت كت بأيقونة Travian
#
# الاستخدام (PowerShell كـ Admin):
#   iwr -uri "<URL>/install.ps1" -outfile install.ps1; .\install.ps1
#
# أو محلياً: .\install.ps1

$ErrorActionPreference = "Stop"
$LogPrefix = "[Zenrex]"
function Write-Step($msg){ Write-Host "$LogPrefix $msg" -ForegroundColor Cyan }
function Write-Ok($msg)  { Write-Host "$LogPrefix ✓ $msg" -ForegroundColor Green }
function Write-Warn($msg){ Write-Host "$LogPrefix ⚠ $msg" -ForegroundColor Yellow }
function Write-Err($msg) { Write-Host "$LogPrefix ✗ $msg" -ForegroundColor Red }

# ─── 1) Install directory ────────────────────────────────────────────────────
$InstallDir = "$env:USERPROFILE\Zenrex-Farm"
Write-Step "مجلد التثبيت: $InstallDir"
New-Item -ItemType Directory -Force -Path $InstallDir | Out-Null
Set-Location $InstallDir

# ─── 2) Python check ────────────────────────────────────────────────────────
Write-Step "فحص Python..."
$PyVer = & python --version 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Err "Python غير منصّب. حمّله من https://python.org (3.11 أو أحدث)"
    Write-Err "مهم: علّم خانة 'Add Python to PATH' أثناء التثبيت"
    exit 1
}
Write-Ok "Python موجود: $PyVer"

# ─── 3) Install pip packages ────────────────────────────────────────────────
Write-Step "تثبيت تبعيات Python..."
$pkgs = @(
    "fastapi", "uvicorn[standard]", "playwright",
    "pywebview", "pystray", "Pillow", "requests"
)
foreach ($p in $pkgs) {
    Write-Host "  → $p"
    & python -m pip install --quiet --upgrade $p 2>&1 | Out-Null
}
Write-Ok "كل التبعيات مثبّتة"

# ─── 4) Playwright Chromium ─────────────────────────────────────────────────
Write-Step "تثبيت Chromium لـ Playwright (قد يأخذ دقيقة)..."
& python -m playwright install chromium 2>&1 | Out-Null
Write-Ok "Chromium جاهز"

# ─── 5) Download Zenrex source files ────────────────────────────────────────
$BaseUrl = if ($env:ZENREX_SOURCE_URL) { $env:ZENREX_SOURCE_URL }
           else { "https://ai-cinematic-hub-2.preview.emergentagent.com/api/desktop-agent/zenrex-farm" }
Write-Step "تحميل ملفات Zenrex من السحابة..."
Write-Host "  → URL: $BaseUrl"
foreach ($f in @("zenrex_farm.py", "zenrex_app.py")) {
    $dest = Join-Path $InstallDir $f
    try {
        Invoke-WebRequest -Uri "$BaseUrl/$f" -OutFile $dest -UseBasicParsing -TimeoutSec 30
        $size = (Get-Item $dest).Length
        Write-Ok "نُزّل $f ($size bytes)"
    } catch {
        Write-Err "تعذّر تحميل $f من $BaseUrl/$f"
        Write-Err "  السبب: $($_.Exception.Message)"
        # Fallback: look in same dir as installer
        $InstallerDir = Split-Path -Parent $MyInvocation.MyCommand.Path
        $src = Join-Path $InstallerDir $f
        if (Test-Path $src) {
            Copy-Item $src $dest -Force
            Write-Ok "نُسخ من المجلد المحلي بدلاً"
        } else {
            exit 1
        }
    }
}

# ─── 6) Download Travian icon ───────────────────────────────────────────────
$IconPath = Join-Path $InstallDir "zenrex_icon.ico"
Write-Step "تحميل أيقونة Travian Legends..."
$IconSources = @(
    "https://www.travian.com/favicon.ico",
    "https://lobby.legends.travian.com/favicon.ico"
)
$IconOk = $false
foreach ($url in $IconSources) {
    try {
        Invoke-WebRequest -Uri $url -OutFile $IconPath -UseBasicParsing -TimeoutSec 12
        if ((Get-Item $IconPath).Length -gt 500) { $IconOk = $true; break }
    } catch {}
}
if (-not $IconOk) {
    Write-Warn "تعذّر التحميل — سأنشئ أيقونة بديلة"
    python -c "from PIL import Image, ImageDraw; img=Image.new('RGBA',(256,256),(15,20,35,255)); d=ImageDraw.Draw(img); d.ellipse([16,16,240,240],fill=(167,139,250,255)); img.save(r'$IconPath',sizes=[(256,256),(128,128),(64,64),(32,32),(16,16)])"
}
Write-Ok "الأيقونة: $IconPath"

# ─── 7) Create desktop shortcut ─────────────────────────────────────────────
Write-Step "إنشاء شورت كت على سطح المكتب..."
$Pythonw = (Get-Command pythonw -ErrorAction SilentlyContinue).Source
if (-not $Pythonw) { $Pythonw = (Get-Command python).Source }
$Launcher = Join-Path $InstallDir "zenrex_app.py"
$DesktopPath = [Environment]::GetFolderPath("Desktop")
$ShortcutPath = Join-Path $DesktopPath "Zenrex Farm.lnk"

$WScriptShell = New-Object -ComObject WScript.Shell
$Shortcut = $WScriptShell.CreateShortcut($ShortcutPath)
$Shortcut.TargetPath = $Pythonw
$Shortcut.Arguments = "`"$Launcher`""
$Shortcut.WorkingDirectory = $InstallDir
$Shortcut.IconLocation = $IconPath
$Shortcut.WindowStyle = 7
$Shortcut.Description = "Zenrex Farm — مزرعة قرى Travian (v0.6.0)"
$Shortcut.Save()
Write-Ok "شورت كت: $ShortcutPath"

# ─── 8) Start menu shortcut (bonus) ─────────────────────────────────────────
$StartMenu = "$env:APPDATA\Microsoft\Windows\Start Menu\Programs\Zenrex Farm.lnk"
$sm = $WScriptShell.CreateShortcut($StartMenu)
$sm.TargetPath = $Pythonw
$sm.Arguments = "`"$Launcher`""
$sm.WorkingDirectory = $InstallDir
$sm.IconLocation = $IconPath
$sm.WindowStyle = 7
$sm.Save()

# ─── 9) Done ────────────────────────────────────────────────────────────────
Write-Host ""
Write-Host "═══════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host " 🏰 Zenrex Farm v0.6.0 جاهز!" -ForegroundColor Yellow
Write-Host "   📁 المسار: $InstallDir" -ForegroundColor White
Write-Host "   🚀 شغّل: دبل كلك على 'Zenrex Farm' على سطح المكتب" -ForegroundColor White
Write-Host "   💡 أو ابحث 'Zenrex' في قائمة Start" -ForegroundColor White
Write-Host "═══════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""
$launch = Read-Host "تبي أشغّله الحين؟ (Y/N)"
if ($launch -eq "Y" -or $launch -eq "y") {
    Start-Process $ShortcutPath
}
