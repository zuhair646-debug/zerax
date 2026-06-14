# Zenrex Farm — Desktop App Installer
# ═══════════════════════════════════════
# 1) ينصّب التبعيات (pywebview + pystray + Pillow)
# 2) يحمّل أيقونة Travian Legends
# 3) ينشئ شورت كت على سطح المكتب باسم "Zenrex Farm" بالأيقونة
# 4) شغّل من سطح المكتب → نافذة Native بدون terminal أسود

$ErrorActionPreference = "Stop"
$Here = Split-Path -Parent $MyInvocation.MyCommand.Path
$LogPrefix = "[Zenrex Installer]"

function Write-Step($msg) { Write-Host "$LogPrefix $msg" -ForegroundColor Cyan }
function Write-Ok($msg)   { Write-Host "$LogPrefix ✓ $msg" -ForegroundColor Green }
function Write-Warn($msg) { Write-Host "$LogPrefix ⚠ $msg" -ForegroundColor Yellow }

Write-Step "تثبيت تبعيات Python..."
$pkgs = @("fastapi", "uvicorn", "playwright", "pywebview", "pystray", "Pillow")
foreach ($p in $pkgs) {
    Write-Host "  → $p"
    python -m pip install --quiet --upgrade $p 2>&1 | Out-Null
}
Write-Ok "كل التبعيات مثبّتة"

# Playwright Chromium (idempotent)
Write-Step "ضمان وجود Chromium لـ Playwright..."
python -m playwright install chromium 2>&1 | Out-Null
Write-Ok "Chromium جاهز"

# تحميل أيقونة Travian
$IconPath = Join-Path $Here "zenrex_icon.ico"
$PngPath  = Join-Path $Here "zenrex_icon.png"
if (-not (Test-Path $IconPath)) {
    Write-Step "تحميل أيقونة Travian Legends..."
    $sources = @(
        "https://www.travian.com/favicon.ico",
        "https://lobby.legends.travian.com/favicon.ico"
    )
    $ok = $false
    foreach ($url in $sources) {
        try {
            Invoke-WebRequest -Uri $url -OutFile $IconPath -UseBasicParsing -TimeoutSec 12
            if ((Get-Item $IconPath).Length -gt 500) { $ok = $true; break }
        } catch {}
    }
    if (-not $ok) {
        Write-Warn "تعذّر التحميل — سأنشئ أيقونة محلية بسيطة"
        python -c @"
from PIL import Image, ImageDraw
img = Image.new('RGBA', (256, 256), (15, 20, 35, 255))
d = ImageDraw.Draw(img)
d.ellipse([16, 16, 240, 240], fill=(167, 139, 250, 255))
d.text((90, 90), 'ZX', fill=(15, 20, 35, 255))
img.save(r'$PngPath')
img.save(r'$IconPath', sizes=[(256,256),(128,128),(64,64),(32,32),(16,16)])
"@
    } else {
        # Generate matching .png from the .ico
        python -c @"
from PIL import Image
im = Image.open(r'$IconPath')
im.save(r'$PngPath')
"@ 2>&1 | Out-Null
    }
    Write-Ok "أيقونة جاهزة: $IconPath"
}

# تحديد مسار pythonw
$Pythonw = (Get-Command pythonw -ErrorAction SilentlyContinue).Source
if (-not $Pythonw) { $Pythonw = (Get-Command python).Source }
Write-Ok "Python: $Pythonw"

# ملف launcher
$Launcher = Join-Path $Here "zenrex_app.py"
if (-not (Test-Path $Launcher)) {
    Write-Warn "ما لقيت zenrex_app.py في $Here — تأكد إنك سحبت الملفات كلها"
    exit 1
}

# إنشاء shortcut على سطح المكتب
Write-Step "إنشاء شورت كت على سطح المكتب..."
$DesktopPath = [Environment]::GetFolderPath("Desktop")
$ShortcutPath = Join-Path $DesktopPath "Zenrex Farm.lnk"

$WScriptShell = New-Object -ComObject WScript.Shell
$Shortcut = $WScriptShell.CreateShortcut($ShortcutPath)
$Shortcut.TargetPath = $Pythonw
$Shortcut.Arguments = "`"$Launcher`""
$Shortcut.WorkingDirectory = $Here
$Shortcut.IconLocation = $IconPath
$Shortcut.WindowStyle = 7   # minimized — لا نوافذ سوداء
$Shortcut.Description = "Zenrex Farm — مزرعة قرى Travian (multi-village automation)"
$Shortcut.Save()

Write-Ok "✅ تم إنشاء '$ShortcutPath'"
Write-Host ""
Write-Host "═══════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host " 🏰 Zenrex Farm جاهز!" -ForegroundColor Yellow
Write-Host "   • اضغط دبل كلك على 'Zenrex Farm' على سطح المكتب" -ForegroundColor White
Write-Host "   • التطبيق يفتح كنافذة Native (مش شاشة سوداء)" -ForegroundColor White
Write-Host "   • للخروج: اضغط ❌ في النافذة، أو من system tray" -ForegroundColor White
Write-Host "═══════════════════════════════════════════════════════" -ForegroundColor Cyan
