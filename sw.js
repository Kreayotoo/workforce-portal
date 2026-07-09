// KSPL Workforce Portal service worker — v268 KILL-SWITCH + network-first
// Purpose: replace any wedged old service worker on employee devices, purge every
// stale cache, and force open tabs onto the live bundle. Browsers fetch THIS file
// from the network on their own schedule (every navigation / max 24h), bypassing
// the old SW entirely — so even devices stuck since ~v250 pick this up with zero
// user action beyond reopening the app.

const CACHE = 'kspl-v268';

self.addEventListener('install', () => {
  // Don't wait for old tabs to close — take over immediately
  self.skipWaiting();
});

self.addEventListener('activate', (e) => {
  e.waitUntil((async () => {
    // 1) Purge EVERY cache from every previous version
    try {
      const keys = await caches.keys();
      await Promise.all(keys.filter(k => k !== CACHE).map(k => caches.delete(k)));
    } catch (_) {}
    // 2) Take control of all open tabs right now
    await self.clients.claim();
    // 3) Force any tab still running an old bundle to reload onto the live one
    try {
      const tabs = await self.clients.matchAll({ type: 'window' });
      tabs.forEach(t => { try { t.navigate(t.url); } catch (_) {} });
    } catch (_) {}
  })());
});

self.addEventListener('fetch', (e) => {
  const req = e.request;
  if (req.method !== 'GET') return;                    // never touch writes
  const url = new URL(req.url);
  if (url.origin !== self.location.origin) return;     // never touch Supabase/CDN

  // APP SHELL (any navigation / the HTML): NETWORK FIRST.
  // Live version always wins; cache is only an offline fallback.
  // This is what makes a stale bundle permanently impossible.
  if (req.mode === 'navigate' || url.pathname === '/' || url.pathname.endsWith('.html')) {
    e.respondWith((async () => {
      try {
        const fresh = await fetch(req);
        if (fresh && fresh.ok) {
          try { const c = await caches.open(CACHE); c.put(req, fresh.clone()); } catch (_) {}
        }
        return fresh;
      } catch (_) {
        const cached = await caches.match(req, { ignoreSearch: true });
        return cached || Response.error();
      }
    })());
    return;
  }

  // Static assets (logo, apk, icons): cache-first with network fill
  e.respondWith((async () => {
    const cached = await caches.match(req);
    if (cached) return cached;
    try {
      const fresh = await fetch(req);
      if (fresh && fresh.ok) {
        try { const c = await caches.open(CACHE); c.put(req, fresh.clone()); } catch (_) {}
      }
      return fresh;
    } catch (_) {
      return Response.error();
    }
  })());
});
