const CACHE_NAME = 'expense-tracker-v2';
const STATIC_ASSETS = [
  '/static/style.css',
  '/static/theme.css',
  '/static/theme.js',
  '/static/pwa.js',
  '/static/manifest.json'
];

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then((cache) => cache.addAll(STATIC_ASSETS))
      .then(() => self.skipWaiting())
  );
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys()
      .then((keys) => Promise.all(
        keys.filter((key) => key !== CACHE_NAME).map((key) => caches.delete(key))
      ))
      .then(() => self.clients.claim())
  );
});

self.addEventListener('fetch', (event) => {
  const request = event.request;

  // Never cache POST/PUT/DELETE requests or application pages.
  if (request.method !== 'GET' || request.mode === 'navigate') {
    return;
  }

  const url = new URL(request.url);
  if (url.origin !== self.location.origin) {
    return;
  }

  // Cache-first only for static assets; dynamic financial data always comes from the server.
  if (url.pathname.startsWith('/static/')) {
    event.respondWith(
      caches.match(request).then((cached) => cached || fetch(request))
    );
  }
});
