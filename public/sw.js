// Service Worker for 日知录 PWA - 开发模式（禁用缓存）

// 安装事件 - 跳过等待
self.addEventListener('install', (event) => {
  self.skipWaiting()
})

// 激活事件 - 立即控制
self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((cacheNames) => {
      // 清除所有缓存
      return Promise.all(
        cacheNames.map((cacheName) => {
          return caches.delete(cacheName)
        })
      )
    }).then(() => {
      return self.clients.claim()
    })
  )
})

// 拦截请求 - 直接使用网络，不缓存
self.addEventListener('fetch', (event) => {
  // 直接使用网络请求，不缓存
  event.respondWith(
    fetch(event.request).catch(() => {
      // 如果网络请求失败，返回离线页面或错误
      return new Response('网络错误，请检查网络连接', {
        status: 503,
        statusText: 'Service Unavailable'
      })
    })
  )
})