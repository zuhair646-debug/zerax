/* Zenrex Service Worker — PWA (v13 — credits packs + custom amount + AI deduction fix) */
/* eslint-disable no-restricted-globals */
const CACHE_VERSION = 'zenrex-pwa-v30-2026-02-no-free-tier';
const STATIC_CACHE = `${CACHE_VERSION}-static`;
const RUNTIME_CACHE = `${CACHE_VERSION}-runtime`;

const PRECACHE_URLS = [
  '/manifest.json',
  '/zenrex-logo.png',
  '/zenrex-logo-sm.png',
  '/icons/icon-192.png',
  '/icons/icon-512.png',
];

// Install — precache the bare minimum (no HTML, no JS, no CSS).
self.addEventListener('install', (e) => {
  e.waitUntil(
    caches.open(STATIC_CACHE)
      .then((c) => c.addAll(PRECACHE_URLS))
      .then(() => self.skipWaiting())
  );
});

// Activate — purge ALL old caches and take over open tabs immediately.
self.addEventListener('activate', (e) => {
  e.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(
        keys
          .filter((k) => !k.startsWith(CACHE_VERSION))
          .map((k) => caches.delete(k))
      )
    ).then(() => self.clients.claim())
  );
});

// Fetch strategy — ALWAYS network-first for HTML / JS / CSS so users see
// the latest deployment instantly. Cache-first kept for images/fonts only.
self.addEventListener('fetch', (event) => {
  const { request } = event;
  if (request.method !== 'GET') return;

  const url = new URL(request.url);

  // Never touch API or websocket.
  if (url.pathname.startsWith('/api/') || url.pathname.startsWith('/ws')) return;

  // Network-first for HTML pages — always fresh.
  if (request.mode === 'navigate' || request.destination === 'document') {
    event.respondWith(
      fetch(request, { cache: 'no-store' })
        .catch(() => caches.match(request).then((r) => r || caches.match('/')))
    );
    return;
  }

  // Network-first for JS/CSS — hashed file names already give us cache busting
  // but we also want the HTML→JS reference to never go stale.
  if (request.destination === 'script' || request.destination === 'style') {
    event.respondWith(
      fetch(request)
        .then((resp) => {
          if (resp && resp.status === 200) {
            const copy = resp.clone();
            caches.open(RUNTIME_CACHE).then((c) => c.put(request, copy));
          }
          return resp;
        })
        .catch(() => caches.match(request))
    );
    return;
  }

  // Cache-first for images / fonts (these rarely change and are heavy).
  if (request.destination === 'image' || request.destination === 'font') {
    event.respondWith(
      caches.match(request).then((cached) => {
        const fetchPromise = fetch(request)
          .then((resp) => {
            if (resp && resp.status === 200) {
              const copy = resp.clone();
              caches.open(RUNTIME_CACHE).then((c) => c.put(request, copy));
            }
            return resp;
          })
          .catch(() => cached);
        return cached || fetchPromise;
      })
    );
    return;
  }

  // Default — try network, fall back to cache.
  event.respondWith(fetch(request).catch(() => caches.match(request)));
});

// Allow page to force an update.
self.addEventListener('message', (event) => {
  if (event.data && event.data.type === 'SKIP_WAITING') self.skipWaiting();
  if (event.data && event.data.type === 'CLEAR_CACHE') {
    caches.keys().then((keys) => keys.forEach((k) => caches.delete(k)));
  }
});
