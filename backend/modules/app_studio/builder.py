"""
App Studio — Build Engine
Generates the actual code package for a project based on its type, features
and imports. Produces a downloadable bundle (a directory + zip).

Output package layouts:
  • pwa        → /index.html + /manifest.json + /sw.js + /icons/
  • hybrid     → pwa/ + capacitor.config.json + android+ios scaffolding hints
  • native     → ios/SwiftUI scaffold + android/Kotlin Jetpack Compose scaffold
  • fullstack  → frontend/ (pwa) + backend/ (FastAPI) + admin/ + marketing/

All artefacts are written under
    /app/backend/static/app_studio_builds/{project_id}/
and served via the /api/app-studio/build/{project_id}/{path} route.
"""
from __future__ import annotations
import os
import io
import json
import logging
import shutil
import zipfile
from datetime import datetime, timezone
from typing import Any, Dict, List

logger = logging.getLogger(__name__)

BUILD_ROOT = "/app/backend/static/app_studio_builds"
os.makedirs(BUILD_ROOT, exist_ok=True)


def project_build_dir(project_id: str) -> str:
    p = os.path.join(BUILD_ROOT, project_id)
    os.makedirs(p, exist_ok=True)
    return p


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _safe_color(c: str, default: str = "#6366f1") -> str:
    if not isinstance(c, str) or not c.startswith("#"):
        return default
    return c[:7]


# ════════════════════════════════════════════════════════════════════════
# PWA HTML (single-file SPA shell) — used by pwa / hybrid / fullstack
# ════════════════════════════════════════════════════════════════════════
def _build_pwa_html(project: Dict[str, Any], features: List[Dict[str, Any]],
                    imported_html: str = "") -> str:
    title = project.get("title") or "تطبيقي"
    desc = project.get("description") or "تطبيق تم توليده عبر زيتاكس"
    color = _safe_color(project.get("primary_color"))
    audience = project.get("target_audience") or ""
    brief = project.get("design_brief") or {}
    brief_palette = [c for c in (brief.get("palette") or []) if isinstance(c, str) and c.startswith("#")]
    if brief.get("primary_color"):
        color = _safe_color(brief["primary_color"], color)
    accent = brief_palette[1] if len(brief_palette) > 1 else color
    bg_dark = brief_palette[2] if len(brief_palette) > 2 else "#0b0d12"
    brief_screens = [s for s in (brief.get("screens") or []) if isinstance(s, str)]

    feat_ids = {f.get("feature_id") for f in features}
    has_auth = "auth_basic" in feat_ids or "auth_social" in feat_ids
    has_chat = "screen_chat" in feat_ids
    has_search = "screen_search" in feat_ids
    has_settings = "screen_settings" in feat_ids
    has_map = "screen_map" in feat_ids

    # If a FreeBuild site was imported, embed its body as a launch screen.
    embedded_section = ""
    if imported_html and "<body" in imported_html.lower():
        # Strip outer html/head, keep body inner
        try:
            lower = imported_html.lower()
            bs = lower.index("<body")
            bs = imported_html.index(">", bs) + 1
            be = lower.rindex("</body>")
            inner = imported_html[bs:be]
            embedded_section = f'<section data-screen="legacy" hidden><div class="legacy-embed">{inner[:120000]}</div></section>'
        except Exception:
            pass

    tabs = ['<button class="tab active" data-target="home">الرئيسية</button>']
    screens = []
    screens.append(_screen_home(title, desc, audience, brief))
    if has_search:
        tabs.append('<button class="tab" data-target="search">بحث</button>')
        screens.append(_screen_search())
    if has_chat:
        tabs.append('<button class="tab" data-target="chat">شات</button>')
        screens.append(_screen_chat())
    if has_map:
        tabs.append('<button class="tab" data-target="map">خريطة</button>')
        screens.append(_screen_map())
    if has_settings:
        tabs.append('<button class="tab" data-target="settings">إعدادات</button>')
        screens.append(_screen_settings())
    if has_auth:
        tabs.append('<button class="tab" data-target="auth">حسابي</button>')
        screens.append(_screen_auth())

    # Inject extra screens from design brief (custom names the user gave us)
    for i, sname in enumerate(brief_screens[:6]):
        sid = f"brief{i+1}"
        # avoid colliding with the default screens already added
        if sname in ("الرئيسية", "بحث", "شات", "خريطة", "إعدادات", "حسابي"):
            continue
        tabs.append(f'<button class="tab" data-target="{sid}">{sname[:14]}</button>')
        screens.append(_screen_brief(sid, sname, brief))

    screens_html = "\n".join(screens) + embedded_section
    tabs_html = "\n      ".join(tabs)
    brief_meta = ""
    if brief:
        brief_meta = f"<!-- Design Brief honoured: layout={brief.get('layout_style')}; nav={brief.get('navigation')}; typo={brief.get('typography')} -->"

    return f"""<!doctype html>
<html lang="ar" dir="rtl">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover" />
<meta name="theme-color" content="{color}" />
<title>{title}</title>
{brief_meta}
<link rel="manifest" href="manifest.json" />
<link rel="apple-touch-icon" href="icons/icon-192.png" />
<style>
*{{box-sizing:border-box;margin:0;padding:0}}
body{{font-family:'Tajawal','Cairo',system-ui,sans-serif;background:{bg_dark};color:#f1f5f9;min-height:100vh;display:flex;flex-direction:column}}
header{{background:linear-gradient(135deg,{color} 0%,{accent} 100%);padding:48px 20px 24px;text-align:center;color:#fff}}
header h1{{font-size:28px;font-weight:800;margin-bottom:8px}}
header p{{opacity:.9;font-size:14px;line-height:1.7}}
main{{flex:1;padding:24px 16px 100px;max-width:600px;margin:0 auto;width:100%}}
section[data-screen]:not(.active){{display:none}}
.card{{background:#12161e;border:1px solid #1f2937;border-radius:18px;padding:18px;margin-bottom:14px}}
.card h2{{font-size:18px;margin-bottom:8px;color:{accent}}}
.card p{{color:#94a3b8;font-size:14px;line-height:1.8}}
.btn{{display:inline-block;background:{color};color:#fff;padding:12px 20px;border-radius:12px;text-decoration:none;border:none;font-weight:700;font-family:inherit;cursor:pointer;font-size:14px;width:100%;margin-top:8px}}
.btn.outline{{background:transparent;border:1px solid {color};color:{color}}}
.btn.accent{{background:{accent}}}
.grid{{display:grid;grid-template-columns:1fr 1fr;gap:12px}}
.stat{{background:#1a1f2c;border-radius:14px;padding:16px;text-align:center}}
.stat b{{color:{color};font-size:22px;display:block}}
.stat span{{font-size:11px;color:#64748b}}
input,textarea{{background:#1a1f2c;border:1px solid #1f2937;border-radius:12px;padding:12px;color:#f1f5f9;font-family:inherit;font-size:14px;width:100%}}
.chat-msg{{background:#1a1f2c;border-radius:14px;padding:12px;margin-bottom:8px;font-size:14px}}
.chat-msg.me{{background:{color}33;text-align:left}}
.legacy-embed{{transform:scale(.5);transform-origin:top right;width:200%;height:200vh;overflow:hidden}}
nav.tabbar{{position:fixed;bottom:0;left:0;right:0;background:#0e1118;border-top:1px solid #1f2937;display:flex;justify-content:space-around;padding:12px env(safe-area-inset-right) calc(12px + env(safe-area-inset-bottom)) env(safe-area-inset-left);z-index:50;overflow-x:auto}}
.tab{{background:transparent;border:0;color:#64748b;font-family:inherit;font-size:12px;font-weight:600;padding:6px 10px;cursor:pointer;border-radius:8px;white-space:nowrap}}
.tab.active{{background:{color}22;color:{color}}}
.palette-strip{{display:flex;gap:6px;margin-top:10px}}
.palette-strip span{{flex:1;height:24px;border-radius:6px}}
</style>
</head>
<body>
<header>
  <h1>{title}</h1>
  <p>{desc}</p>
</header>
<main id="app">
  {screens_html}
</main>
<nav class="tabbar">
  {tabs_html}
</nav>
<script>
const tabs = document.querySelectorAll('.tab');
const screens = document.querySelectorAll('section[data-screen]');
function show(name){{
  tabs.forEach(t=>t.classList.toggle('active', t.dataset.target===name));
  screens.forEach(s=>{{ s.classList.toggle('active', s.dataset.screen===name); s.hidden = s.dataset.screen!==name; }});
}}
tabs.forEach(t=>t.addEventListener('click',()=>show(t.dataset.target)));
show(document.querySelector('section[data-screen]').dataset.screen);
let deferredPrompt;
window.addEventListener('beforeinstallprompt', e=>{{ e.preventDefault(); deferredPrompt = e; }});
if ('serviceWorker' in navigator) {{
  navigator.serviceWorker.register('sw.js').catch(console.error);
}}
</script>
</body>
</html>"""


def _screen_home(title, desc, audience, brief=None):
    brief = brief or {}
    palette = (brief.get("palette") or [])[:5]
    palette_html = ""
    if palette:
        spans = "".join(f'<span style="background:{c}"></span>' for c in palette)
        palette_html = f'<div class="palette-strip" title="palette من تصاميمك">{spans}</div>'
    layout_note = ""
    if brief.get("layout_style"):
        layout_note = f'<p style="margin-top:8px;color:#94a3b8;font-size:12px">🎨 ستايل التصميم: {brief["layout_style"]}</p>'
    return f"""<section data-screen="home" class="active">
  <div class="card">
    <h2>👋 أهلاً بك في {title}</h2>
    <p>{desc}</p>
    {('<p style="margin-top:8px;color:#94a3b8">الجمهور المستهدف: '+audience+'</p>') if audience else ''}
    {layout_note}
    {palette_html}
  </div>
  <div class="grid">
    <div class="stat"><b>0</b><span>المستخدمون</span></div>
    <div class="stat"><b>0</b><span>المشتركون</span></div>
    <div class="stat"><b>4.9★</b><span>التقييم</span></div>
    <div class="stat"><b>قريباً</b><span>المتجر</span></div>
  </div>
  <div class="card" style="margin-top:14px">
    <h2>ابدأ الآن</h2>
    <p>هذا تطبيق مبدئي مُولّد من زيتاكس بناءً على {('التصاميم اللي رفعتها' if brief else 'مواصفاتك')}. كل صفحة في الـtabs قابلة للتعديل.</p>
    <button class="btn" onclick="alert('متاح بعد الربط مع backend')">إنشاء حساب</button>
  </div>
</section>"""


def _screen_brief(sid, sname, brief=None):
    brief = brief or {}
    return f"""<section data-screen="{sid}">
  <div class="card">
    <h2>{sname}</h2>
    <p>هذه الشاشة مستخرجة من التصميم اللي رفعته. {('ستايل: ' + brief.get('layout_style','')) if brief.get('layout_style') else ''}</p>
    <div class="grid" style="margin-top:12px">
      <div class="stat"><b>—</b><span>عنصر 1</span></div>
      <div class="stat"><b>—</b><span>عنصر 2</span></div>
    </div>
    <button class="btn accent" style="margin-top:12px">إجراء رئيسي</button>
  </div>
</section>"""


def _screen_search():
    return """<section data-screen="search">
  <div class="card">
    <h2>🔎 بحث</h2>
    <input placeholder="ابحث…" oninput="document.getElementById('searchResults').textContent='نتائج لـ: '+this.value" />
    <p id="searchResults" style="margin-top:12px"></p>
  </div>
</section>"""


def _screen_chat():
    return """<section data-screen="chat">
  <div class="card">
    <h2>💬 شات</h2>
    <div id="msgs">
      <div class="chat-msg">مرحباً 👋 كيف نقدر نخدمك؟</div>
    </div>
    <input id="msgIn" placeholder="اكتب رسالتك…" />
    <button class="btn" onclick="(()=>{const v=document.getElementById('msgIn').value;if(!v)return;const d=document.createElement('div');d.className='chat-msg me';d.textContent=v;document.getElementById('msgs').appendChild(d);document.getElementById('msgIn').value='';})()">إرسال</button>
  </div>
</section>"""


def _screen_map():
    return """<section data-screen="map">
  <div class="card">
    <h2>🗺️ خريطة</h2>
    <p>اربط Google Maps أو Mapbox API key لعرض الخريطة الحقيقية.</p>
    <div style="background:#1a1f2c;height:240px;border-radius:12px;display:flex;align-items:center;justify-content:center;color:#64748b">معاينة الخريطة</div>
  </div>
</section>"""


def _screen_settings():
    return """<section data-screen="settings">
  <div class="card">
    <h2>⚙️ إعدادات</h2>
    <p>إشعارات، اللغة، الحساب، الخصوصية.</p>
    <button class="btn outline">تغيير اللغة</button>
    <button class="btn outline" style="margin-top:8px">تسجيل الخروج</button>
  </div>
</section>"""


def _screen_auth():
    return """<section data-screen="auth">
  <div class="card">
    <h2>👤 الحساب</h2>
    <input placeholder="البريد الإلكتروني" />
    <input placeholder="كلمة السر" type="password" style="margin-top:8px" />
    <button class="btn">دخول</button>
    <button class="btn outline" style="margin-top:8px">إنشاء حساب</button>
  </div>
</section>"""


# ════════════════════════════════════════════════════════════════════════
# PWA support files
# ════════════════════════════════════════════════════════════════════════
def _manifest(project: Dict[str, Any]) -> str:
    color = _safe_color(project.get("primary_color"))
    return json.dumps({
        "name": project.get("title") or "Zerax App",
        "short_name": (project.get("title") or "App")[:12],
        "description": project.get("description") or "",
        "start_url": ".",
        "display": "standalone",
        "background_color": "#0b0d12",
        "theme_color": color,
        "icons": [
            {"src": "icons/icon-192.png", "sizes": "192x192", "type": "image/png"},
            {"src": "icons/icon-512.png", "sizes": "512x512", "type": "image/png"},
        ],
        "lang": "ar",
        "dir": "rtl",
    }, ensure_ascii=False, indent=2)


def _service_worker() -> str:
    return """const CACHE='zerax-app-v1';
const ASSETS=['./','./index.html','./manifest.json'];
self.addEventListener('install',e=>{e.waitUntil(caches.open(CACHE).then(c=>c.addAll(ASSETS)));self.skipWaiting();});
self.addEventListener('activate',e=>{e.waitUntil(self.clients.claim());});
self.addEventListener('fetch',e=>{
  if(e.request.method!=='GET')return;
  e.respondWith(caches.match(e.request).then(r=>r||fetch(e.request).then(res=>{
    const clone=res.clone();caches.open(CACHE).then(c=>c.put(e.request,clone));return res;
  }).catch(()=>caches.match('./index.html'))));
});
"""


def _icon_svg(label: str, color: str, size: int = 512) -> bytes:
    """Return a simple SVG-as-PNG-ish data via plain SVG bytes (browsers accept svg manifest icons fine,
    but we write actual .png placeholder using a 1x1 PNG fallback if Pillow missing). For real PNG, use Pillow."""
    try:
        from PIL import Image, ImageDraw, ImageFont
        img = Image.new("RGB", (size, size), color)
        d = ImageDraw.Draw(img)
        text = (label or "Z")[:1].upper()
        try:
            font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", int(size * 0.6))
        except Exception:
            font = ImageFont.load_default()
        try:
            bbox = d.textbbox((0, 0), text, font=font)
            w, h = bbox[2] - bbox[0], bbox[3] - bbox[1]
            d.text(((size - w) / 2 - bbox[0], (size - h) / 2 - bbox[1]), text, fill="white", font=font)
        except Exception:
            d.text((size / 3, size / 4), text, fill="white", font=font)
        buf = io.BytesIO()
        img.save(buf, "PNG")
        return buf.getvalue()
    except Exception:
        # Minimal 1x1 transparent PNG
        import base64
        return base64.b64decode(
            "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAusB9R6kK5wAAAAASUVORK5CYII="
        )


# ════════════════════════════════════════════════════════════════════════
# Capacitor (Hybrid) extras
# ════════════════════════════════════════════════════════════════════════
def _capacitor_config(project: Dict[str, Any]) -> str:
    app_id = "com.zerax." + "".join(c for c in (project.get("title") or "app").lower() if c.isalnum())[:20] or "myapp"
    return json.dumps({
        "appId": app_id,
        "appName": project.get("title") or "MyApp",
        "webDir": "www",
        "bundledWebRuntime": False,
        "server": {"androidScheme": "https"},
        "ios": {"contentInset": "always"},
        "android": {"allowMixedContent": False},
    }, indent=2)


def _capacitor_readme(project: Dict[str, Any]) -> str:
    return f"""# {project.get('title') or 'My App'} — Hybrid (Capacitor)

## التشغيل المحلي
```bash
yarn install
npx cap sync
npx cap open ios       # يحتاج Xcode
npx cap open android   # يحتاج Android Studio
```

## النشر للمتاجر
- **App Store**: حساب Apple Developer ($99/سنة)
- **Google Play**: حساب Google Play Console ($25 لمرة واحدة)

تم التوليد عبر زيتاكس · {datetime.now(timezone.utc).strftime('%Y-%m-%d')}
"""


def _capacitor_package_json(project: Dict[str, Any]) -> str:
    return json.dumps({
        "name": "".join(c for c in (project.get("title") or "app").lower() if c.isalnum())[:20] or "myapp",
        "version": "1.0.0",
        "private": True,
        "scripts": {
            "sync": "cap sync",
            "ios": "cap open ios",
            "android": "cap open android",
        },
        "dependencies": {
            "@capacitor/core": "^6.0.0",
            "@capacitor/ios": "^6.0.0",
            "@capacitor/android": "^6.0.0",
        },
        "devDependencies": {
            "@capacitor/cli": "^6.0.0",
        },
    }, indent=2)


# ════════════════════════════════════════════════════════════════════════
# Native scaffolding (Swift / Kotlin)
# ════════════════════════════════════════════════════════════════════════
def _swift_app(project: Dict[str, Any]) -> str:
    name = project.get("title") or "MyApp"
    return f"""import SwiftUI

@main
struct {name.replace(' ', '')}App: App {{
    var body: some Scene {{
        WindowGroup {{
            ContentView()
        }}
    }}
}}

struct ContentView: View {{
    var body: some View {{
        NavigationView {{
            VStack(spacing: 16) {{
                Text("{name}")
                    .font(.largeTitle)
                    .bold()
                Text("{(project.get('description') or '')}")
                    .foregroundColor(.secondary)
                    .multilineTextAlignment(.center)
                    .padding()
                Spacer()
            }}
            .padding()
            .navigationTitle("{name}")
        }}
    }}
}}
"""


def _kotlin_app(project: Dict[str, Any]) -> str:
    name = project.get("title") or "MyApp"
    return f"""package com.zerax.app
import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.foundation.layout.*
import androidx.compose.material3.*
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp

class MainActivity : ComponentActivity() {{
    override fun onCreate(savedInstanceState: Bundle?) {{
        super.onCreate(savedInstanceState)
        setContent {{
            MaterialTheme {{
                Surface {{
                    Column(modifier = Modifier.padding(24.dp)) {{
                        Text(text = "{name}", style = MaterialTheme.typography.headlineLarge)
                        Spacer(modifier = Modifier.height(8.dp))
                        Text(text = "{(project.get('description') or '')}")
                    }}
                }}
            }}
        }}
    }}
}}
"""


# ════════════════════════════════════════════════════════════════════════
# Backend scaffolding (FullStack)
# ════════════════════════════════════════════════════════════════════════
def _fastapi_main() -> str:
    return """from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from datetime import datetime, timezone
import uuid

app = FastAPI(title="App Backend")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

USERS = {}
ITEMS = {}

class UserIn(BaseModel):
    email: str
    name: str = ""

class ItemIn(BaseModel):
    title: str
    body: str = ""

@app.get("/api/health")
def health():
    return {"ok": True, "ts": datetime.now(timezone.utc).isoformat()}

@app.post("/api/users")
def create_user(u: UserIn):
    uid = uuid.uuid4().hex
    USERS[uid] = {"id": uid, **u.model_dump(), "created_at": datetime.now(timezone.utc).isoformat()}
    return USERS[uid]

@app.get("/api/users")
def list_users():
    return list(USERS.values())

@app.post("/api/items")
def create_item(it: ItemIn):
    iid = uuid.uuid4().hex
    ITEMS[iid] = {"id": iid, **it.model_dump(), "created_at": datetime.now(timezone.utc).isoformat()}
    return ITEMS[iid]

@app.get("/api/items")
def list_items():
    return list(ITEMS.values())
"""


def _admin_html(project: Dict[str, Any]) -> str:
    title = (project.get("title") or "App") + " — لوحة التحكم"
    color = _safe_color(project.get("primary_color"))
    return f"""<!doctype html><html lang="ar" dir="rtl"><head>
<meta charset="utf-8"/><meta name="viewport" content="width=device-width,initial-scale=1"/>
<title>{title}</title>
<style>
body{{font-family:Tajawal,system-ui;background:#0b0d12;color:#f1f5f9;margin:0}}
header{{background:{color};padding:20px;color:#fff;font-weight:700;font-size:20px}}
main{{padding:20px;max-width:900px;margin:auto}}
.row{{display:grid;grid-template-columns:repeat(auto-fill,minmax(220px,1fr));gap:14px}}
.box{{background:#12161e;border:1px solid #1f2937;border-radius:14px;padding:16px}}
.box h3{{color:{color};margin-bottom:6px}}
.box p{{color:#94a3b8;font-size:13px;line-height:1.6}}
table{{width:100%;border-collapse:collapse;margin-top:16px}}
th,td{{padding:10px;border-bottom:1px solid #1f2937;text-align:right}}
</style></head><body>
<header>{title}</header>
<main>
<div class="row">
 <div class="box"><h3 id="u">0</h3><p>المستخدمون</p></div>
 <div class="box"><h3 id="i">0</h3><p>العناصر</p></div>
 <div class="box"><h3>API</h3><p id="api">…</p></div>
</div>
<h2 style="margin-top:24px">أحدث المستخدمين</h2>
<table id="utable"><thead><tr><th>الاسم</th><th>البريد</th><th>تاريخ</th></tr></thead><tbody></tbody></table>
<script>
const API='http://localhost:8000';
fetch(API+'/api/health').then(r=>r.json()).then(d=>document.getElementById('api').textContent='شغّال '+d.ts).catch(()=>document.getElementById('api').textContent='غير متصل — شغّل backend');
fetch(API+'/api/users').then(r=>r.json()).then(list=>{{
  document.getElementById('u').textContent=list.length;
  const tb=document.querySelector('#utable tbody');
  list.forEach(u=>{{const tr=document.createElement('tr');tr.innerHTML='<td>'+u.name+'</td><td>'+u.email+'</td><td>'+u.created_at+'</td>';tb.appendChild(tr);}});
}}).catch(()=>{{}});
fetch(API+'/api/items').then(r=>r.json()).then(list=>document.getElementById('i').textContent=list.length).catch(()=>{{}});
</script>
</main></body></html>"""


def _marketing_html(project: Dict[str, Any]) -> str:
    title = project.get("title") or "App"
    desc = project.get("description") or ""
    color = _safe_color(project.get("primary_color"))
    return f"""<!doctype html><html lang="ar" dir="rtl"><head>
<meta charset="utf-8"/><meta name="viewport" content="width=device-width,initial-scale=1"/>
<title>{title}</title>
<style>
*{{box-sizing:border-box;margin:0;padding:0}}
body{{font-family:Tajawal,system-ui;background:#0b0d12;color:#f1f5f9;line-height:1.7}}
.hero{{background:linear-gradient(135deg,{color} 0%,#000 100%);padding:80px 24px;text-align:center;color:#fff}}
.hero h1{{font-size:48px;font-weight:900;margin-bottom:14px}}
.hero p{{font-size:18px;opacity:.95;max-width:600px;margin:auto}}
.cta{{display:inline-block;background:#fff;color:{color};padding:14px 32px;border-radius:14px;text-decoration:none;font-weight:700;margin-top:24px}}
section.f{{padding:60px 24px;max-width:1100px;margin:auto}}
section.f h2{{font-size:32px;margin-bottom:8px}}
.cards{{display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:18px;margin-top:32px}}
.card{{background:#12161e;border:1px solid #1f2937;border-radius:18px;padding:24px}}
.card h3{{color:{color};margin-bottom:8px}}
footer{{padding:30px;text-align:center;color:#64748b;border-top:1px solid #1f2937;margin-top:60px}}
</style></head><body>
<div class="hero">
  <h1>{title}</h1>
  <p>{desc}</p>
  <a class="cta" href="#download">حمّل التطبيق</a>
</div>
<section class="f">
  <h2>لماذا {title}؟</h2>
  <p style="color:#94a3b8">حلّ جذري وأنيق لمشكلة حقيقية يعيشها جمهورك.</p>
  <div class="cards">
    <div class="card"><h3>⚡ سريع</h3><p>تجربة مستخدم خفيفة على كل الأجهزة.</p></div>
    <div class="card"><h3>🔒 آمن</h3><p>بياناتك محميّة بأعلى المعايير.</p></div>
    <div class="card"><h3>🎯 موثوق</h3><p>دعم فني عربي + تحديثات مستمرة.</p></div>
  </div>
</section>
<footer>© {datetime.now(timezone.utc).year} — {title}. مولّد عبر زيتاكس.</footer>
</body></html>"""


# ════════════════════════════════════════════════════════════════════════
# MAIN BUILD ORCHESTRATOR
# ════════════════════════════════════════════════════════════════════════
def build_project(project: Dict[str, Any], features: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Build the project on disk under BUILD_ROOT/{project_id}/.
    Returns a manifest dict describing the files that were generated.
    """
    pid = project["id"]
    bdir = project_build_dir(pid)
    # wipe previous build
    for name in os.listdir(bdir):
        p = os.path.join(bdir, name)
        if os.path.isdir(p):
            shutil.rmtree(p, ignore_errors=True)
        else:
            try:
                os.remove(p)
            except Exception:
                pass

    ptype = project.get("type") or "pwa"
    imports = project.get("imports") or []
    imported_html = ""
    for im in imports:
        if im.get("kind") == "freebuild_site" and im.get("html_snapshot"):
            imported_html = im["html_snapshot"]
            break

    files: List[Dict[str, str]] = []
    color = _safe_color(project.get("primary_color"))

    def _write(rel: str, content):
        full = os.path.join(bdir, rel)
        os.makedirs(os.path.dirname(full), exist_ok=True)
        mode = "wb" if isinstance(content, (bytes, bytearray)) else "w"
        with open(full, mode, encoding=None if mode == "wb" else "utf-8") as f:
            f.write(content)
        files.append({"path": rel, "size": os.path.getsize(full)})

    # ── PWA base (pwa / hybrid / fullstack) ───────────────────────────
    if ptype in ("pwa", "hybrid", "fullstack"):
        prefix = "" if ptype == "pwa" else ("www/" if ptype == "hybrid" else "frontend/")
        _write(f"{prefix}index.html", _build_pwa_html(project, features, imported_html))
        _write(f"{prefix}manifest.json", _manifest(project))
        _write(f"{prefix}sw.js", _service_worker())
        _write(f"{prefix}icons/icon-192.png", _icon_svg(project.get("title", "Z"), color, 192))
        _write(f"{prefix}icons/icon-512.png", _icon_svg(project.get("title", "Z"), color, 512))

    # ── Hybrid extras ─────────────────────────────────────────────────
    if ptype == "hybrid":
        _write("capacitor.config.json", _capacitor_config(project))
        _write("package.json", _capacitor_package_json(project))
        _write("README.md", _capacitor_readme(project))

    # ── Native scaffolding ────────────────────────────────────────────
    if ptype == "native":
        _write("ios/App.swift", _swift_app(project))
        _write("android/app/src/main/java/com/zerax/app/MainActivity.kt", _kotlin_app(project))
        _write("README.md", f"""# {project.get('title')} — Native scaffold

## iOS
- افتح `ios/` في Xcode، أنشئ مشروع SwiftUI جديد، الصق `App.swift`.
- يحتاج: macOS + Xcode 15+.

## Android
- افتح `android/` في Android Studio.
- يحتاج: Kotlin 1.9+ + Jetpack Compose.

## ملاحظة
هذا هيكل ابتدائي. أكمل الميزات يدوياً أو ارجع إلى زيتاكس لطلب توسيع.
""")

    # ── FullStack extras ──────────────────────────────────────────────
    if ptype == "fullstack":
        _write("backend/main.py", _fastapi_main())
        _write("backend/requirements.txt", "fastapi\nuvicorn[standard]\npydantic\n")
        _write("backend/README.md", "## تشغيل\n`pip install -r requirements.txt && uvicorn main:app --reload`\n")
        _write("admin/index.html", _admin_html(project))
        _write("marketing/index.html", _marketing_html(project))
        _write("README.md", f"""# {project.get('title')} — Full-Stack

- `frontend/` — تطبيق PWA جاهز للنشر على Vercel/Netlify
- `backend/` — FastAPI ينشر على Railway (`pip install -r requirements.txt && uvicorn main:app`)
- `admin/` — لوحة تحكم مالك
- `marketing/` — موقع تسويقي

تم التوليد عبر زيتاكس · {datetime.now(timezone.utc).strftime('%Y-%m-%d')}
""")

    # ── ZIP bundle ────────────────────────────────────────────────────
    zip_path = os.path.join(bdir, "bundle.zip")
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for root, _, fnames in os.walk(bdir):
            for fn in fnames:
                if fn == "bundle.zip":
                    continue
                abs_p = os.path.join(root, fn)
                arc = os.path.relpath(abs_p, bdir)
                zf.write(abs_p, arc)

    return {
        "ok": True,
        "project_id": pid,
        "type": ptype,
        "built_at": _now(),
        "files": files,
        "bundle_size": os.path.getsize(zip_path),
        "preview_url": f"/api/app-studio/build/{pid}/index.html"
                       if ptype in ("pwa",)
                       else (f"/api/app-studio/build/{pid}/www/index.html" if ptype == "hybrid"
                             else (f"/api/app-studio/build/{pid}/frontend/index.html" if ptype == "fullstack" else None)),
        "zip_url": f"/api/app-studio/build/{pid}/bundle.zip",
    }
