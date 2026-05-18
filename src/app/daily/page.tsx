'use client'

import { useState, useEffect, useCallback } from 'react'
import TermCard from '@/components/TermCard'
import { fetchAPI } from '@/lib/api'

interface DailyDocCard {
  term_id: string
  term: string
  context: string
  simple: string
  deep: string
  case: string
  related: string[]
  source: string
}

interface CollectedTerm {
  id: string
  term: string
  domain: string
  captured_at: string
}

interface DailyDocData {
  doc_date: string
  title: string
  cards: DailyDocCard[]
  new_connections: Array<{
    from: string
    to: string
    description: string
  }>
  generated_at?: string
  terms_collected?: CollectedTerm[]
  terms_count?: number
  can_generate?: boolean
}

interface GenerateProgress {
  task_id: string
  status: string
  progress: number
  total: number
  current_step: string
  percent: number
}

export default function DailyPage() {
  const [dailyDoc, setDailyDoc] = useState<DailyDocData | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [selectedDate, setSelectedDate] = useState(new Date().toISOString().split('T')[0])
  const [generating, setGenerating] = useState(false)
  const [generateProgress, setGenerateProgress] = useState<GenerateProgress | null>(null)

  const fetchDailyDoc = useCallback(async (date: string) => {
    try {
      setLoading(true)
      setError(null)
      
      // 获取用户ID
      let userId = localStorage.getItem('daydayknow_user_id')
      if (!userId) {
        userId = 'user_' + Math.random().toString(36).substr(2, 9)
        localStorage.setItem('daydayknow_user_id', userId)
      }
      
      const data = await fetchAPI(`/api/daily-doc?date=${date}`, {
        headers: {
          'x-user-id': userId
        }
      })
      setDailyDoc(data)
    } catch (err) {
      setError(err instanceof Error ? err.message : '未知错误')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchDailyDoc(selectedDate)
  }, [selectedDate, fetchDailyDoc])

  const handleDateChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setSelectedDate(e.target.value)
  }

  const handlePrevDay = () => {
    const date = new Date(selectedDate)
    date.setDate(date.getDate() - 1)
    setSelectedDate(date.toISOString().split('T')[0])
  }

  const handleNextDay = () => {
    const date = new Date(selectedDate)
    date.setDate(date.getDate() + 1)
    const today = new Date().toISOString().split('T')[0]
    if (date.toISOString().split('T')[0] <= today) {
      setSelectedDate(date.toISOString().split('T')[0])
    }
  }

  const pollTaskProgress = async (taskId: string, userId: string) => {
    const maxAttempts = 120 // 最多轮询120次（约2分钟）
    for (let i = 0; i < maxAttempts; i++) {
      try {
        const taskStatus = await fetchAPI(`/api/daily-doc/task/${taskId}`, {
          headers: { 'x-user-id': userId }
        })
        
        setGenerateProgress({
          task_id: taskStatus.task_id,
          status: taskStatus.status,
          progress: taskStatus.progress || 0,
          total: taskStatus.total || 0,
          current_step: taskStatus.current_step || '',
          percent: taskStatus.percent || 0
        })
        
        if (taskStatus.status === 'completed') {
          return true
        }
        if (taskStatus.status === 'failed') {
          setError(taskStatus.error || '生成失败')
          return false
        }
        
        // 等待500ms再轮询
        await new Promise(resolve => setTimeout(resolve, 500))
      } catch (err) {
        console.error('轮询进度失败:', err)
        // 继续轮询，不中断
        await new Promise(resolve => setTimeout(resolve, 1000))
      }
    }
    return false
  }

  const handleGenerate = async () => {
    try {
      setGenerating(true)
      setGenerateProgress(null)
      
      let userId = localStorage.getItem('daydayknow_user_id')
      if (!userId) {
        userId = 'user_' + Math.random().toString(36).substr(2, 9)
        localStorage.setItem('daydayknow_user_id', userId)
      }
      
      const result = await fetchAPI('/api/daily-doc/generate', {
        method: 'POST',
        headers: { 'x-user-id': userId },
        body: JSON.stringify({ date: selectedDate })
      })
      
      if (result.task_id) {
        // 立即显示初始进度
        setGenerateProgress({
          task_id: result.task_id,
          status: 'running',
          progress: 0,
          total: 0,
          current_step: '准备中...',
          percent: 0
        })
        // 等待一小段时间让后台任务启动
        await new Promise(resolve => setTimeout(resolve, 200))
        // 异步任务，轮询进度
        const success = await pollTaskProgress(result.task_id, userId)
        if (success) {
          await fetchDailyDoc(selectedDate)
        }
      } else {
        // 日报已存在，直接刷新
        await fetchDailyDoc(selectedDate)
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : '生成失败')
    } finally {
      setGenerating(false)
      setGenerateProgress(null)
    }
  }

  const isToday = selectedDate === new Date().toISOString().split('T')[0]
  const isFuture = selectedDate > new Date().toISOString().split('T')[0]

  if (loading) {
    return (
      <div className="min-h-screen bg-gradient-to-b from-blue-50 to-white flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
          <p className="text-gray-600">加载日报中...</p>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="min-h-screen bg-gradient-to-b from-blue-50 to-white flex items-center justify-center">
        <div className="text-center">
          <div className="text-red-500 text-6xl mb-4">⚠️</div>
          <h2 className="text-xl font-semibold text-gray-900 mb-2">加载失败</h2>
          <p className="text-gray-600 mb-4">{error}</p>
          <button
            onClick={() => fetchDailyDoc(selectedDate)}
            className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
          >
            重试
          </button>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gradient-to-b from-blue-50 to-white">
      {/* 头部 */}
      <header className="bg-white shadow-sm">
        <div className="max-w-lg mx-auto px-4 py-4">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h1 className="text-2xl font-bold text-gray-900">日知录</h1>
              <p className="text-sm text-gray-500">
                {dailyDoc?.title || '查看日报'}
              </p>
            </div>
            <div className="text-right">
              <div className="text-2xl">📚</div>
              <div className="text-xs text-gray-500">
                {dailyDoc?.cards?.length || 0} 个术语
              </div>
            </div>
          </div>
          
          {/* 日期选择器 */}
          <div className="flex items-center justify-between bg-gray-50 rounded-lg p-2">
            <button
              onClick={handlePrevDay}
              className="px-3 py-1 text-gray-600 hover:text-blue-600 transition-colors"
            >
              ◀
            </button>
            
            <div className="flex items-center space-x-2">
              <input
                type="date"
                value={selectedDate}
                onChange={handleDateChange}
                max={new Date().toISOString().split('T')[0]}
                className="px-3 py-1 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
              {isToday && (
                <span className="px-2 py-1 bg-blue-100 text-blue-800 text-xs rounded-full">
                  今天
                </span>
              )}
            </div>
            
            <button
              onClick={handleNextDay}
              disabled={isFuture}
              className="px-3 py-1 text-gray-600 hover:text-blue-600 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              ▶
            </button>
          </div>
        </div>
      </header>

      {/* 主要内容 */}
      <main className="max-w-lg mx-auto px-4 py-6">
        {dailyDoc?.cards && dailyDoc.cards.length > 0 ? (
          /* 日报卡片列表 */
          <div className="space-y-6">
            {dailyDoc.cards.map((card) => (
              <TermCard
                key={card.term_id}
                card={card}
                onConfirm={() => {}}
              />
            ))}
            
            {/* 新发现的连线 */}
            {dailyDoc.new_connections && dailyDoc.new_connections.length > 0 && (
              <div className="bg-gradient-to-r from-purple-50 to-blue-50 rounded-2xl p-6">
                <h3 className="text-lg font-semibold text-gray-900 mb-4">
                  🔗 新发现的联系
                </h3>
                <div className="space-y-3">
                  {dailyDoc.new_connections.map((connection, index) => (
                    <div
                      key={index}
                      className="flex items-center space-x-3 bg-white rounded-lg p-3"
                    >
                      <span className="font-medium text-purple-600">
                        {connection.from}
                      </span>
                      <span className="text-gray-400">→</span>
                      <span className="font-medium text-blue-600">
                        {connection.to}
                      </span>
                      <span className="text-sm text-gray-500 ml-auto">
                        {connection.description}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        ) : dailyDoc?.terms_collected && dailyDoc.terms_collected.length > 0 ? (
          /* 有收集的术语但未生成日报 */
          <div className="space-y-6">
            <div className="bg-yellow-50 border border-yellow-200 rounded-2xl p-6">
              <div className="flex items-center mb-4">
                <span className="text-2xl mr-3">📝</span>
                <div>
                  <h3 className="font-semibold text-yellow-800">日报未生成</h3>
                  <p className="text-sm text-yellow-600">
                    收集了 {dailyDoc.terms_count} 个术语，可以立即生成日报
                  </p>
                </div>
              </div>
              
              <button
                onClick={handleGenerate}
                disabled={generating}
                className="w-full py-3 bg-gradient-to-r from-yellow-400 to-orange-500 text-white font-semibold rounded-lg hover:from-yellow-500 hover:to-orange-600 transition-all disabled:opacity-50"
              >
                {generating ? (
                  <span className="flex items-center justify-center">
                    <span className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></span>
                    {generateProgress?.current_step || '启动中...'}
                    {generateProgress && generateProgress.total > 0 && (
                      <span className="ml-1">({generateProgress.percent}%)</span>
                    )}
                  </span>
                ) : '立即生成日报'}
              </button>
              
              {/* 进度条 */}
              {generating && generateProgress && (
                <div className="mt-3">
                  {generateProgress.total > 0 ? (
                    <>
                      <div className="w-full bg-gray-200 rounded-full h-2">
                        <div 
                          className="bg-gradient-to-r from-yellow-400 to-orange-500 h-2 rounded-full transition-all duration-300"
                          style={{ width: `${generateProgress.percent}%` }}
                        ></div>
                      </div>
                      <p className="text-xs text-gray-500 mt-1 text-center">
                        {generateProgress.progress}/{generateProgress.total} 术语已处理
                      </p>
                    </>
                  ) : (
                    <p className="text-xs text-gray-500 text-center">
                      正在查询术语...
                    </p>
                  )}
                </div>
              )}
            </div>
            
            {/* 收集的术语列表 */}
            <div className="bg-white rounded-2xl shadow-lg p-6">
              <h3 className="text-lg font-semibold text-gray-900 mb-4">
                已收集的术语
              </h3>
              <div className="space-y-3">
                {dailyDoc.terms_collected.map((term) => (
                  <div
                    key={term.id}
                    className="flex items-center justify-between p-3 bg-gray-50 rounded-lg"
                  >
                    <div>
                      <span className="font-medium text-gray-900">{term.term}</span>
                      <span className="ml-2 px-2 py-1 bg-blue-100 text-blue-800 text-xs rounded-full">
                        {term.domain}
                      </span>
                    </div>
                    <span className="text-xs text-gray-500">
                      {new Date(term.captured_at).toLocaleTimeString()}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        ) : (
          /* 空状态 */
          <div className="text-center py-12">
            <div className="text-6xl mb-4">🌅</div>
            <h2 className="text-xl font-semibold text-gray-900 mb-2">
              暂无日报
            </h2>
            <p className="text-gray-600 mb-6">
              这一天没有收集到术语
            </p>
            <button
              onClick={() => window.location.href = '/'}
              className="px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
            >
              去捕获术语
            </button>
          </div>
        )}
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
              className="flex flex-col items-center py-2 text-blue-600"
            >
              <span className="text-xl">📰</span>
              <span className="text-xs mt-1">日报</span>
            </button>
            <button
              onClick={() => window.location.href = '/'}
              className="flex flex-col items-center py-2 text-gray-500 hover:text-blue-600 transition-colors"
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