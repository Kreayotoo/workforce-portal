// Kreayotoo HR Portal — Service Worker
// Bump CACHE_VERSION on every deploy to invalidate old caches
const CACHE_VERSION = 'v1';
const CACHE_NAME = `kreayotoo-${CACHE_VERSION}`;

// Files to cache for offline use (only static shell — data always fresh from network)
const STATIC_FILES = [
  '/',
  '/workforce-portal.html',
  '/kreayotoo-logo.png',
  '/icon-192.png',
  '/icon-512.png',
  '/manifest.json'
];

// Install event — pre-cache shell
self.addEventListener('install', event => {
  self.skipWaiting();
  event.waitUntil(
    caches.open(CACHE_NAME).then(cache => cache.addAll(STATIC_FILES))
      .catch(err => console.warn('SW install cache failed', err))
  );
});

// Activate event — clean up old caches
self.addEventListener('activate', event => {
  event.waitUntil(
    caches.keys().then(keys =>
      Promise.all(keys.filter(k => k !== CACHE_NAME).map(k => caches.delete(k)))
    ).then(() => self.clients.claim())
  );
});

// Fetch handler — network-first for HTML/API, cache-first for static assets
self.addEventListener('fetch', event => {
  const url = new URL(event.request.url);

  // Never cache Supabase/API calls — always fetch fresh
  if (url.hostname.includes('supabase.co') ||
      url.hostname.includes('googleapis.com') ||
      url.pathname.includes('/rest/v1/')) {
    return; // let browser handle normally
  }

  // For HTML: network-first (so users get fresh HTML on each refresh)
  if (event.request.mode === 'navigate' || event.request.destination === 'document') {
    event.respondWith(
      fetch(event.request).then(res => {
        const copy = res.clone();
        caches.open(CACHE_NAME).then(cache => cache.put(event.request, copy));
        return res;
      }).catch(() => caches.match(event.request).then(r => r || caches.match('/workforce-portal.html')))
    );
    return;
  }

  // For static assets (images, JSON): cache-first with network fallback
  if (url.pathname.endsWith('.png') || url.pathname.endsWith('.json') ||
      url.pathname.endsWith('.jpg') || url.pathname.endsWith('.svg')) {
    event.respondWith(
      caches.match(event.request).then(cached => {
        if (cached) return cached;
        return fetch(event.request).then(res => {
          const copy = res.clone();
          caches.open(CACHE_NAME).then(cache => cache.put(event.request, copy));
          return res;
        });
      })
    );
    return;
  }

  // Everything else: network-first
  event.respondWith(
    fetch(event.request).catch(() => caches.match(event.request))
  );
});
