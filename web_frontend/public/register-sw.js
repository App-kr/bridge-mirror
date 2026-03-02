/**
 * BRIDGE — Service Worker cleanup
 * 기존 서비스워커를 해제하고 모든 캐시를 삭제합니다.
 * dev 환경에서 캐시 꼬임 방지.
 */
if ('serviceWorker' in navigator) {
  navigator.serviceWorker.getRegistrations().then(function (regs) {
    regs.forEach(function (r) { r.unregister(); });
  });
  if ('caches' in window) {
    caches.keys().then(function (keys) {
      keys.forEach(function (k) { caches.delete(k); });
    });
  }
}
