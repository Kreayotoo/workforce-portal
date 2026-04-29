// Kreayotoo HR Portal Service Worker
// Strategy:
//   - HTML/navigation: network-first with 4s timeout, falls back to cache only if offline
//   - Static assets (icons, logos): cache-first for fast loads
//   - External APIs (Supabase, CDNs, EmailJS): bypass SW entirely
//   - Old caches cleaned on activate; clients claimed immediately
const CACHE_VERSION = 'v8-2026-04-29-empid-on-signup';
const CACHE_NAME = `kreayotoo-${CACHE_VERSION}`;
const NETWORK_TIMEOUT_MS = 4000; // give up on network after 4s and serve cache

const ASSETS = [
  '/manifest.json',
  '/icon-192.png',
  '/icon-512.png',
  '/icon-maskable.png',
  '/kreayotoo-logo.png',
  '/kreayotoo-portal.apk'
];

self.addEventListener('install', (event) => {
  // Pre-cache static assets only. DO NOT pre-cache HTML — we want it always fresh.
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => {
      return Promise.all(
        ASSETS.map((url) =>
          cache.add(url).catch((err) => {
            console.warn('[SW] precache failed for', url, err);
          })
        )
      );
    })
  );
  // Activate immediately — don't wait for old SW to die
  self.skipWaiting();
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    (async () => {
      // Delete every old cache except the current one
      const keys = await caches.keys();
      await Promise.all(
        keys.filter((k) => k !== CACHE_NAME).map((k) => caches.delete(k))
      );
      // Take control of all open pages immediately
      await self.clients.claim();
      console.log('[SW] activated:', CACHE_VERSION);
    })()
  );
});

// Helper: race a fetch against a timeout
function fetchWithTimeout(req, ms) {
  return new Promise((resolve, reject) => {
    const timer = setTimeout(() => reject(new Error('network-timeout')), ms);
    fetch(req).then(
      (res) => {
        clearTimeout(timer);
        resolve(res);
      },
      (err) => {
        clearTimeout(timer);
        reject(err);
      }
    );
  });
}

self.addEventListener('fetch', (event) => {
  const req = event.request;
  if (req.method !== 'GET') return;

  const url = new URL(req.url);

  // BYPASS: external APIs and CDNs handle their own caching
  if (
    url.hostname.includes('supabase.co') ||
    url.hostname.includes('emailjs.com') ||
    url.hostname.includes('cdn.jsdelivr.net') ||
    url.hostname.includes('cdnjs.cloudflare.com') ||
    url.hostname.includes('unpkg.com') ||
    url.hostname.includes('nominatim.openstreetmap.org') ||
    url.hostname.includes('googleapis.com')
  ) {
    return;
  }

  // NAVIGATION / HTML: network-first with timeout, cache fallback only if offline
  const isHTML =
    req.mode === 'navigate' ||
    req.destination === 'document' ||
    (url.pathname.endsWith('.html'));

  if (isHTML) {
    event.respondWith(
      (async () => {
        try {
          // Try network with a hard timeout so slow networks don't hang
          const res = await fetchWithTimeout(req, NETWORK_TIMEOUT_MS);
          if (res && res.ok) {
            // Update cache in background — don't await
            const copy = res.clone();
            caches.open(CACHE_NAME).then((c) => c.put(req, copy)).catch(() => {});
            return res;
          }
          // Server returned non-OK — try cache as fallback
          throw new Error('non-ok-response');
        } catch (err) {
          // Network failed or timed out — serve cached HTML if we have it
          const cached = await caches.match(req);
          if (cached) {
            console.log('[SW] HTML from cache (network failed):', req.url);
            return cached;
          }
          // Last-resort: try cached root
          const fallback = await caches.match('/') || await caches.match('/workforce-portal.html');
          if (fallback) return fallback;
          // Nothing cached — re-throw so browser shows its own offline page
          throw err;
        }
      })()
    );
    return;
  }

  // STATIC ASSETS: cache-first, network only if not cached
  event.respondWith(
    caches.match(req).then((cached) => {
      if (cached) return cached;
      return fetch(req).then((res) => {
        // Only cache successful, basic responses
        if (res && res.ok && res.type === 'basic') {
          const copy = res.clone();
          caches.open(CACHE_NAME).then((c) => c.put(req, copy)).catch(() => {});
        }
        return res;
      });
    })
  );
});

self.addEventListener('message', (event) => {
  if (event.data && event.data.type === 'SKIP_WAITING') {
    self.skipWaiting();
  }
  if (event.data && event.data.type === 'CLEAR_CACHES') {
    event.waitUntil(
      caches.keys().then((keys) => Promise.all(keys.map((k) => caches.delete(k))))
    );
  }
});
