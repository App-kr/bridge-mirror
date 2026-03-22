if ('serviceWorker' in navigator) {
  window.addEventListener('load', function () {
    navigator.serviceWorker.register('/sw.js')
      .then(function (reg) {
        console.log('[SW] registered:', reg.scope)
        setInterval(function () { reg.update() }, 60 * 60 * 1000)
        reg.addEventListener('updatefound', function () {
          var nw = reg.installing
          if (!nw) return
          nw.addEventListener('statechange', function () {
            if (nw.state === 'activated' && navigator.serviceWorker.controller) {
              console.log('[SW] New version available')
            }
          })
        })
      })
      .catch(function (err) {
        console.error('[SW] registration failed:', err)
      })
  })
}
