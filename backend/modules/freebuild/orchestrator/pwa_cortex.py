"""
📱 PWA Deep Cortex — service worker + manifest + offline-first + push.

Generates production-ready PWA assets:
  - manifest.json
  - service-worker.js (with cache strategies)
  - offline.html
  - install prompt JS
  - push notification setup (with VAPID keys)
"""
from __future__ import annotations

import json
from typing import Any, Dict, List, Optional


def build_manifest(
    name: str,
    short_name: str,
    description: str,
    theme_color: str = "#0a0a0a",
    background_color: str = "#ffffff",
    start_url: str = "/",
    display: str = "standalone",
    lang: str = "ar",
    icon_url: str = "/icons/icon-512.png",
) -> str:
    manifest = {
        "name": name,
        "short_name": short_name,
        "description": description,
        "start_url": start_url,
        "display": display,
        "theme_color": theme_color,
        "background_color": background_color,
        "lang": lang,
        "dir": "rtl" if lang.startswith("ar") else "ltr",
        "icons": [
            {"src": "/icons/icon-72.png", "sizes": "72x72", "type": "image/png"},
            {"src": "/icons/icon-96.png", "sizes": "96x96", "type": "image/png"},
            {"src": "/icons/icon-128.png", "sizes": "128x128", "type": "image/png"},
            {"src": "/icons/icon-192.png", "sizes": "192x192", "type": "image/png", "purpose": "any maskable"},
            {"src": "/icons/icon-512.png", "sizes": "512x512", "type": "image/png", "purpose": "any maskable"},
        ],
        "categories": ["productivity"],
        "orientation": "portrait-primary",
    }
    return json.dumps(manifest, ensure_ascii=False, indent=2)


def build_service_worker(cache_version: str = "v1", static_assets: Optional[List[str]] = None) -> str:
    """Generate a service worker with cache-first for assets + network-first for HTML."""
    assets = static_assets or ["/", "/offline.html", "/manifest.json"]
    return f"""// 🛡️ Service Worker — cache version: {cache_version}
const CACHE_VERSION = '{cache_version}';
const CACHE_NAME = `app-cache-${{CACHE_VERSION}}`;
const STATIC_ASSETS = {json.dumps(assets)};
const OFFLINE_PAGE = '/offline.html';

self.addEventListener('install', (event) => {{
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => cache.addAll(STATIC_ASSETS))
  );
  self.skipWaiting();
}});

self.addEventListener('activate', (event) => {{
  event.waitUntil(
    caches.keys().then((names) =>
      Promise.all(names.filter((n) => n !== CACHE_NAME).map((n) => caches.delete(n)))
    )
  );
  self.clients.claim();
}});

self.addEventListener('fetch', (event) => {{
  const req = event.request;
  if (req.method !== 'GET') return;
  const url = new URL(req.url);

  // HTML → network-first, fallback to cache, then offline page
  if (req.headers.get('accept')?.includes('text/html')) {{
    event.respondWith(
      fetch(req).then((res) => {{
        const copy = res.clone();
        caches.open(CACHE_NAME).then((c) => c.put(req, copy));
        return res;
      }}).catch(() => caches.match(req).then((c) => c || caches.match(OFFLINE_PAGE)))
    );
    return;
  }}

  // Static assets → cache-first
  event.respondWith(
    caches.match(req).then((c) => c || fetch(req).then((res) => {{
      const copy = res.clone();
      if (res.ok) caches.open(CACHE_NAME).then((cc) => cc.put(req, copy));
      return res;
    }}))
  );
}});

// Push notification handler
self.addEventListener('push', (event) => {{
  const data = event.data?.json() || {{}};
  event.waitUntil(self.registration.showNotification(data.title || 'إشعار جديد', {{
    body: data.body || '',
    icon: '/icons/icon-192.png',
    badge: '/icons/icon-72.png',
    data: data.url || '/',
  }}));
}});

self.addEventListener('notificationclick', (event) => {{
  event.notification.close();
  event.waitUntil(clients.openWindow(event.notification.data || '/'));
}});
"""


def build_offline_page(brand_name: str = "Zenrex", color: str = "#0a0a0a") -> str:
    return f"""<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
  <meta charset="UTF-8">
  <title>غير متصل — {brand_name}</title>
  <style>
    body {{ display:flex; align-items:center; justify-content:center; height:100vh; margin:0; background:{color}; color:white; font-family:Cairo,sans-serif; }}
    .box {{ text-align:center; padding:40px; }}
    h1 {{ font-size:2rem; margin:0 0 10px; }}
    button {{ margin-top:20px; padding:12px 24px; background:white; color:{color}; border:none; border-radius:8px; cursor:pointer; font-size:1rem; }}
  </style>
</head>
<body>
  <div class="box">
    <h1>📡 لا يوجد اتصال</h1>
    <p>تأكد من اتصالك بالإنترنت ثم حاول مرة أخرى.</p>
    <button onclick="location.reload()">إعادة المحاولة</button>
  </div>
</body>
</html>"""


def install_prompt_snippet() -> str:
    """JS snippet to handle PWA install prompt."""
    return """// Show install button when PWA is installable
let deferredPrompt;
window.addEventListener('beforeinstallprompt', (e) => {
  e.preventDefault();
  deferredPrompt = e;
  const btn = document.getElementById('install-pwa-btn');
  if (btn) {
    btn.style.display = 'inline-flex';
    btn.addEventListener('click', async () => {
      btn.style.display = 'none';
      deferredPrompt.prompt();
      const { outcome } = await deferredPrompt.userChoice;
      console.log('PWA install:', outcome);
      deferredPrompt = null;
    });
  }
});

// Register service worker
if ('serviceWorker' in navigator) {
  window.addEventListener('load', () => {
    navigator.serviceWorker.register('/service-worker.js').catch(console.error);
  });
}"""


def push_setup_snippet(vapid_public_key: str = "REPLACE_WITH_VAPID_PUBLIC_KEY") -> str:
    return f"""// Push notification subscription
async function subscribeToPush() {{
  const reg = await navigator.serviceWorker.ready;
  const sub = await reg.pushManager.subscribe({{
    userVisibleOnly: true,
    applicationServerKey: urlBase64ToUint8Array('{vapid_public_key}')
  }});
  await fetch('/api/push/subscribe', {{
    method: 'POST',
    headers: {{ 'Content-Type': 'application/json' }},
    body: JSON.stringify(sub),
  }});
}}

function urlBase64ToUint8Array(base64String) {{
  const padding = '='.repeat((4 - base64String.length % 4) % 4);
  const base64 = (base64String + padding).replace(/-/g, '+').replace(/_/g, '/');
  const raw = atob(base64);
  const out = new Uint8Array(raw.length);
  for (let i = 0; i < raw.length; ++i) out[i] = raw.charCodeAt(i);
  return out;
}}"""
