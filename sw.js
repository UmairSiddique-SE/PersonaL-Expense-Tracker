const CACHE_NAME = 'expense-tracker-v1';
const ASSETS = [
  '/',
  '/index.html',
  '/style.css',
  // Agar aapki koi JS file hai to uska naam yahan likhein
];

// 1. Install event: Files ko cache mein save karega
self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => {
      return cache.addAll(ASSETS);
    })
  );
});

// 2. Fetch event: Files ko network ke bajaye cache se load karega
self.addEventListener('fetch', (event) => {
  event.respondWith(
    caches.match(event.request).then((response) => {
      return response || fetch(event.request);
    })
  );
});

// 3. Activate event: Purana cache delete karega (optional)
self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((keys) => {
      return Promise.all(
        keys.filter((key) => key !== CACHE_NAME).map((key) => caches.delete(key))
      );
    })
  );
});