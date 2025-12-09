const CACHE_VERSION = 1;
const CACHE_NAME = `hf-sms-v${CACHE_VERSION}`;
const APP_SHELL = [
  '/',
  '/static/manifest.json',
  '/static/icons/icon-192.svg',
  '/static/icons/icon-512.svg',
  '/static/offline.html'
];

// Check for updates every time the service worker activates
self.addEventListener('install', event => {
  event.waitUntil(
    caches.open(CACHE_NAME).then(cache => cache.addAll(APP_SHELL))
  );
  self.skipWaiting();
});

self.addEventListener('activate', event => {
  event.waitUntil(
    caches.keys().then(keys => Promise.all(
      keys.filter(k => k !== CACHE_NAME).map(k => caches.delete(k))
    ))
  );
  self.clients.claim();
  
  // Notify all clients about the new service worker
  self.clients.matchAll().then(clients => {
    clients.forEach(client => {
      client.postMessage({
        type: 'SERVICE_WORKER_UPDATED',
        version: CACHE_VERSION,
        timestamp: new Date().toISOString()
      });
    });
  });
});

self.addEventListener('fetch', event => {
  // navigation requests: network-first, fallback to offline
  if (event.request.mode === 'navigate') {
    event.respondWith(
      fetch(event.request).then(resp => {
        return resp;
      }).catch(() => caches.match('/static/offline.html'))
    );
    return;
  }

  // other requests: cache-first
  event.respondWith(
    caches.match(event.request).then(cached => cached || fetch(event.request))
  );
});
