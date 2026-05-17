'use client'

import { useEffect } from 'react'

export default function PWARegister() {
  useEffect(() => {
    if (typeof window !== 'undefined' && 'serviceWorker' in navigator) {
      // 注册 Service Worker
      navigator.serviceWorker
        .register('/sw.js')
        .then((registration) => {
          console.log('Service Worker 注册成功:', registration.scope)
          
          // 检查更新
          registration.addEventListener('updatefound', () => {
            const newWorker = registration.installing
            if (newWorker) {
              newWorker.addEventListener('statechange', () => {
                if (newWorker.state === 'activated') {
                  // 新版本激活，刷新页面
                  window.location.reload()
                }
              })
            }
          })
        })
        .catch((error) => {
          console.log('Service Worker 注册失败:', error)
        })
      
      // 监听 Service Worker 控制变化
      navigator.serviceWorker.addEventListener('controllerchange', () => {
        console.log('Service Worker 控制变化，刷新页面')
        window.location.reload()
      })
    }
  }, [])

  return null
}