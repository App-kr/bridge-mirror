/**
 * BRIDGE Service Worker — Self-unregister
 * 캐시 문제 해결을 위해 모든 캐시를 삭제하고 자기 자신을 해제합니다.
 * 안정화 후 실제 SW로 교체 가능.
 */
self.addEventListener('install', () => self.skipWaiting());
self.addEventListener('activate', (e) => {
  e.waitUntil(
    caches.keys()
      .then((keys) => Promise.all(keys.map((k) => caches.delete(k))))
      .then(() => self.registration.unregister())
      .then(() => self.clients.matchAll())
      .then((clients) => clients.forEach((c) => c.navigate(c.url)))
  );
});
