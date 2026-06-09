/**
 * Zerax Companion — Service Worker
 * Registers for PWA install + basic offline shell + notification display.
 */
const CACHE_VERSION = 'zerax-companion-v1';
const SHELL = [
  '/companion',
  '/avatars/f1_zara.png',
  '/avatars/f2_layla.png',
];

self.addEventListener('install', (e) => {
  e.waitUntil((async () => {
    try {
      const cache = await caches.open(CACHE_VERSION);
      await cache.addAll(SHELL.filter(Boolean));
    } catch (_) { /* ignore */ }
    self.skipWaiting();
  })());
});

self.addEventListener('activate', (e) => {
  e.waitUntil((async () => {
    const keys = await caches.keys();
    await Promise.all(keys.filter(k => k !== CACHE_VERSION).map(k => caches.delete(k)));
    self.clients.claim();
  })());
});

// Network-first for API, cache-first for assets
self.addEventListener('fetch', (e) => {
  const url = new URL(e.request.url);
  if (url.pathname.startsWith('/api/')) return; // let the browser handle API
  if (e.request.method !== 'GET') return;
  e.respondWith((async () => {
    try {
      const resp = await fetch(e.request);
      return resp;
    } catch (_) {
      const cached = await caches.match(e.request);
      if (cached) return cached;
      throw _;
    }
  })());
});

// Notification click → focus existing tab or open
self.addEventListener('notificationclick', (e) => {
  e.notification.close();
  e.waitUntil((async () => {
    const all = await self.clients.matchAll({ type: 'window', includeUncontrolled: true });
    for (const c of all) {
      if (c.url.includes('/companion')) { c.focus(); return; }
    }
    await self.clients.openWindow('/companion');
  })());
});
