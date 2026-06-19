// Zenrex Play — Service Worker (CLEAN BUILD)
const SW_VERSION = 'zenrex-play-v4-antifraud-review';
const SHELL_CACHE = SW_VERSION + '-shell';

const SHELL = ['/play/manifest.webmanifest', '/play/icon-192.png', '/play/icon-512.png'];

self.addEventListener('install', e => {
  self.skipWaiting();
  e.waitUntil(caches.open(SHELL_CACHE).then(c => c.addAll(SHELL).catch(() => {})));
});

self.addEventListener('activate', e => {
  e.waitUntil(
    caches.keys().then(keys =>
      Promise.all(keys.filter(k => !k.startsWith(SW_VERSION)).map(k => caches.delete(k)))
    ).then(() => self.clients.claim())
  );
});

self.addEventListener('fetch', e => {
  const req = e.request;
  if (req.method !== 'GET') return;
  const url = new URL(req.url);

  // Media + audio files: DO NOT INTERCEPT (Range requests must hit network)
  if (url.pathname.startsWith('/api/freebuild-chat/media/file/') ||
      url.pathname.startsWith('/api/freebuild-chat/kids/audio/') ||
      url.pathname.startsWith('/api/freebuild-chat/kids/recordings/')) {
    return;
  }
  // All other API: network-only
  if (url.pathname.startsWith('/api/')) return;
  // /play HTML: network-first
  if (url.pathname === '/play' || url.pathname === '/play/') {
    e.respondWith(
      fetch(req).then(res => {
        if (res.ok) {
          const clone = res.clone();
          caches.open(SHELL_CACHE).then(c => c.put(req, clone)).catch(() => {});
        }
        return res;
      }).catch(() => caches.match(req).then(c => c || new Response('Offline', { status: 503 })))
    );
    return;
  }
  // /play/* shell assets: cache-first
  if (url.pathname.startsWith('/play/')) {
    e.respondWith(
      caches.match(req).then(c => {
        if (c) return c;
        return fetch(req).then(res => {
          if (res.ok) {
            const clone = res.clone();
            caches.open(SHELL_CACHE).then(cache => cache.put(req, clone)).catch(() => {});
          }
          return res;
        });
      })
    );
    return;
  }
});
