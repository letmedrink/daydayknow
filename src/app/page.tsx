'use client'

import { useState } from 'react'

export default function HomePage() {
  const [rawText, setRawText] = useState('')
  const [isCapturing, setIsCapturing] = useState(false)
  const [captureResult, setCaptureResult] = useState<{
    extracted_term: string
    message: string
  } | null>(null)

  const handleCapture = async () => {
    if (!rawText.trim()) return

    setIsCapturing(true)
    try {
      // 获取用户ID
      let userId = localStorage.getItem('daydayknow_user_id')
      if (!userId) {
        userId = 'user_' + Math.random().toString(36).substr(2, 9)
        localStorage.setItem('daydayknow_user_id', userId)
      }
      
      const response = await fetch('/api/capture', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'x-user-id': userId
        },
        body: JSON.stringify({ raw_text: rawText })
      })

      if (!response.ok) {
        throw new Error('捕获失败')
      }

      const result = await response.json()
      setCaptureResult(result)
      setRawText('')
    } catch (error) {
      console.error('捕获错误:', error)
      alert('捕获失败，请重试')
    } finally {
      setIsCapturing(false)
    }
  }

  return (
    <div className="min-h-screen bg-gradient-to-b from-blue-50 to-white">
      {/* 头部 */}
      <header className="bg-white shadow-sm">
        <div className="max-w-lg mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-2xl font-bold text-gray-900">日知录</h1>
              <p className="text-sm text-gray-500">
                把昨天遇到的陌生术语，变成今晨一份专属扫盲日报
              </p>
            </div>
            <div className="text-right">
              <div className="text-2xl">📚</div>
            </div>
          </div>
        </div>
      </header>

      {/* 主要内容 */}
      <main className="max-w-lg mx-auto px-4 py-6">
        {/* 捕获区域 */}
        <div className="bg-white rounded-2xl shadow-lg p-6 mb-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">
            捕获陌生术语
          </h2>
          
          <textarea
            value={rawText}
            onChange={(e) => setRawText(e.target.value)}
            placeholder="在这里粘贴或输入包含陌生术语的句子...&#10;&#10;例如：日本经济长期陷入流动性陷阱"
            className="w-full h-32 p-4 border border-gray-200 rounded-xl resize-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          />
          
          <button
            onClick={handleCapture}
            disabled={isCapturing || !rawText.trim()}
            className="w-full mt-4 py-3 bg-gradient-to-r from-blue-600 to-purple-600 text-white font-semibold rounded-xl hover:from-blue-700 hover:to-purple-700 transition-all disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {isCapturing ? '捕获中...' : '捕获术语'}
          </button>
        </div>

        {/* 捕获结果 */}
        {captureResult && (
          <div className="bg-green-50 border border-green-200 rounded-2xl p-6 mb-6">
            <div className="flex items-center mb-3">
              <span className="text-2xl mr-3">✅</span>
              <div>
                <h3 className="font-semibold text-green-800">
                  捕获成功！
                </h3>
                <p className="text-sm text-green-600">
                  {captureResult.message}
                </p>
              </div>
            </div>
            
            <div className="bg-white rounded-lg p-4">
              <p className="text-sm text-gray-500 mb-1">提取的术语：</p>
              <p className="text-lg font-medium text-gray-900">
                {captureResult.extracted_term}
              </p>
            </div>
          </div>
        )}

        {/* 使用说明 */}
        <div className="bg-gradient-to-r from-purple-50 to-blue-50 rounded-2xl p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">
            📖 使用说明
          </h3>
          
          <div className="space-y-4">
            <div className="flex items-start">
              <span className="bg-purple-100 text-purple-800 text-sm font-medium px-2.5 py-0.5 rounded-full mr-3 mt-0.5">
                1
              </span>
              <div>
                <p className="font-medium text-gray-900">遇到陌生术语</p>
                <p className="text-sm text-gray-600">
                  在阅读文章时，看到不懂的专业术语
                </p>
              </div>
            </div>
            
            <div className="flex items-start">
              <span className="bg-purple-100 text-purple-800 text-sm font-medium px-2.5 py-0.5 rounded-full mr-3 mt-0.5">
                2
              </span>
              <div>
                <p className="font-medium text-gray-900">选中句子分享</p>
                <p className="text-sm text-gray-600">
                  选中包含术语的句子，分享给日知录
                </p>
              </div>
            </div>
            
            <div className="flex items-start">
              <span className="bg-purple-100 text-purple-800 text-sm font-medium px-2.5 py-0.5 rounded-full mr-3 mt-0.5">
                3
              </span>
              <div>
                <p className="font-medium text-gray-900">次日查看日报</p>
                <p className="text-sm text-gray-600">
                  第二天早上，打开日知录查看专属扫盲日报
                </p>
              </div>
            </div>
          </div>
        </div>
      </main>

      {/* 底部导航 */}
      <nav className="fixed bottom-0 left-0 right-0 bg-white border-t border-gray-200">
        <div className="max-w-lg mx-auto px-4 py-2">
          <div className="flex justify-around">
            <button
              onClick={() => window.location.href = '/star-map'}
              className="flex flex-col items-center py-2 text-gray-500 hover:text-blue-600 transition-colors"
            >
              <span className="text-xl">⭐</span>
              <span className="text-xs mt-1">星图</span>
            </button>
            <button
              onClick={() => window.location.href = '/daily'}
              className="flex flex-col items-center py-2 text-gray-500 hover:text-blue-600 transition-colors"
            >
              <span className="text-xl">📰</span>
              <span className="text-xs mt-1">日报</span>
            </button>
            <button
              onClick={() => window.location.href = '/'}
              className="flex flex-col items-center py-2 text-blue-600"
            >
              <span className="text-xl">🎯</span>
              <span className="text-xs mt-1">捕获</span>
            </button>
          </div>
        </div>
      </nav>

      {/* 底部留白 */}
      <div className="h-20"></div>
    </div>
  )
}