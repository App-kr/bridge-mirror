const CACHE_NAME = 'bridge-v1'
const OFFLINE_URL = '/offline.html'
const PRECACHE = [OFFLINE_URL]

self.addEventListener('install', (e) => {
  e.waitUntil(
    caches.open(CACHE_NAME)
      .then(cache => cache.addAll(PRECACHE))
      .then(() => self.skipWaiting())
  )
})

self.addEventListener('activate', (e) => {
  e.waitUntil(
    caches.keys().then(keys =>
      Promise.all(keys.filter(k => k !== CACHE_NAME).map(k => caches.delete(k)))
    ).then(() => self.clients.claim())
  )
})

self.addEventListener('fetch', (e) => {
  const { request } = e
  const url = new URL(request.url)

  // Skip non-GET and API calls
  if (request.method !== 'GET') return
  if (url.pathname.startsWith('/api/')) return

  // Static assets: Cache First
  if (/\.(js|css|png|jpg|jpeg|svg|ico|woff2?)$/.test(url.pathname)) {
    e.respondWith(
      caches.match(request).then(cached => {
        if (cached) return cached
        return fetch(request).then(res => {
          if (res.ok) {
            const clone = res.clone()
            caches.open(CACHE_NAME).then(c => c.put(request, clone))
          }
          return res
        })
      })
    )
    return
  }

  // HTML: Network First -> Cache -> Offline
  e.respondWith(
    fetch(request)
      .then(res => {
        if (res.ok) {
          const clone = res.clone()
          caches.open(CACHE_NAME).then(c => c.put(request, clone))
        }
        return res
      })
      .catch(() => caches.match(request).then(cached => cached || caches.match(OFFLINE_URL)))
  )
})

// Push notification
self.addEventListener('push', (e) => {
  const data = e.data ? e.data.json() : {}
  const title = data.title || 'BRIDGE'
  const options = {
    body: data.body || 'New notification',
    icon: '/icon-192.png',
    badge: '/icon-192.png',
    data: { url: data.url || '/admin/m' },
    vibrate: [200, 100, 200],
  }
  e.waitUntil(self.registration.showNotification(title, options))
})

self.addEventListener('notificationclick', (e) => {
  e.notification.close()
  const url = e.notification.data?.url || '/admin/m'
  e.waitUntil(
    self.clients.matchAll({ type: 'window', includeUncontrolled: true })
      .then(clients => {
        const client = clients.find(c => c.url.includes('/admin'))
        if (client) return client.focus()
        return self.clients.openWindow(url)
      })
  )
})
