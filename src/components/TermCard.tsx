'use client'

import { useState } from 'react'
import { fetchAPI } from '@/lib/api'

interface DailyDocCard {
  term_id: string
  term: string
  context: string
  simple: string
  deep: string
  case: string
  history?: string
  related: string[]
  controversy?: string
  source: string
}

interface TermCardProps {
  card: DailyDocCard
  onConfirm: (termId: string) => void
}

export default function TermCard({ card, onConfirm }: TermCardProps) {
  const [isExpanded, setIsExpanded] = useState(false)
  const [isConfirming, setIsConfirming] = useState(false)
  const [isConfirmed, setIsConfirmed] = useState(false)
  const [swipeStartX, setSwipeStartX] = useState(0)
  const [swipeOffset, setSwipeOffset] = useState(0)

  const handleTouchStart = (e: React.TouchEvent) => {
    setSwipeStartX(e.touches[0].clientX)
  }

  const handleTouchMove = (e: React.TouchEvent) => {
    const currentX = e.touches[0].clientX
    const diff = swipeStartX - currentX
    
    if (diff > 0) {
      setSwipeOffset(Math.min(diff, 150))
    }
  }

  const handleTouchEnd = () => {
    if (swipeOffset > 80) {
      handleConfirm()
    }
    setSwipeOffset(0)
  }

  const handleConfirm = async () => {
    if (isConfirming || isConfirmed) return
    
    setIsConfirming(true)
    try {
      let userId = localStorage.getItem('daydayknow_user_id')
      if (!userId) {
        userId = 'user_' + Math.random().toString(36).substr(2, 9)
        localStorage.setItem('daydayknow_user_id', userId)
      }
      
      await fetchAPI(`/api/terms/${card.term_id}/confirm`, {
        method: 'POST',
        headers: {
          'x-user-id': userId
        }
      })
      
      setIsConfirmed(true)
      onConfirm(card.term_id)
    } catch (error) {
      console.error('确认失败:', error)
    } finally {
      setIsConfirming(false)
    }
  }

  // 格式化文本，支持换行
  const formatText = (text: string) => {
    if (!text) return null
    return text.split('\n').map((line, i) => (
      <span key={i}>
        {line}
        {i < text.split('\n').length - 1 && <br />}
      </span>
    ))
  }

  return (
    <div 
      className="relative bg-white rounded-2xl shadow-lg overflow-hidden transition-all duration-300"
      style={{
        transform: `translateX(-${swipeOffset}px)`,
        opacity: swipeOffset > 0 ? 1 - (swipeOffset / 300) : 1
      }}
      onTouchStart={handleTouchStart}
      onTouchMove={handleTouchMove}
      onTouchEnd={handleTouchEnd}
    >
      {/* 射箭提示 */}
      {swipeOffset > 0 && (
        <div 
          className="absolute right-0 top-0 bottom-0 flex items-center justify-center bg-gradient-to-l from-yellow-400/20 to-transparent"
          style={{ width: `${swipeOffset}px` }}
        >
          <div className="text-yellow-600 font-bold text-sm">
            {swipeOffset > 80 ? '松手射箭！' : '← 向左滑动'}
          </div>
        </div>
      )}
      
      {/* 卡片内容 */}
      <div className="p-6">
        {/* 术语标题 */}
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-xl font-bold text-gray-900">{card.term}</h3>
          {isConfirmed && (
            <span className="px-3 py-1 bg-green-100 text-green-800 text-sm rounded-full">
              ✓ 已掌握
            </span>
          )}
        </div>
        
        {/* 一句话解释 */}
        <p className="text-gray-600 mb-4 text-lg">{card.simple}</p>
        
        {/* 上下文 */}
        <div className="bg-gray-50 rounded-lg p-4 mb-4">
          <p className="text-sm text-gray-500 mb-1">原文语境：</p>
          <p className="text-gray-700">{card.context}</p>
        </div>
        
        {/* 展开/收起按钮 */}
        <button
          onClick={() => setIsExpanded(!isExpanded)}
          className="w-full py-2 text-blue-600 hover:text-blue-800 transition-colors"
        >
          {isExpanded ? '收起' : '展开看更多'}
        </button>
        
        {/* 展开内容 */}
        {isExpanded && (
          <div className="mt-4 space-y-4">
            {/* 深入解释 */}
            <div>
              <h4 className="font-semibold text-gray-900 mb-2">📖 深入解释</h4>
              <div className="text-gray-700 whitespace-pre-line">{formatText(card.deep)}</div>
            </div>
            
            {/* 案例 */}
            <div>
              <h4 className="font-semibold text-gray-900 mb-2">💡 具体案例</h4>
              <div className="text-gray-700 whitespace-pre-line">{formatText(card.case)}</div>
            </div>
            
            {/* 历史 */}
            {card.history && (
              <div>
                <h4 className="font-semibold text-gray-900 mb-2">📜 历史渊源</h4>
                <div className="text-gray-700 whitespace-pre-line">{formatText(card.history)}</div>
              </div>
            )}
            
            {/* 争议 */}
            {card.controversy && (
              <div>
                <h4 className="font-semibold text-gray-900 mb-2">⚡ 争议与观点</h4>
                <div className="text-gray-700 whitespace-pre-line">{formatText(card.controversy)}</div>
              </div>
            )}
            
            {/* 相关术语 */}
            <div>
              <h4 className="font-semibold text-gray-900 mb-2">🔗 相关术语</h4>
              <div className="flex flex-wrap gap-2">
                {card.related.map((term, index) => (
                  <span
                    key={index}
                    className="px-3 py-1 bg-blue-100 text-blue-800 text-sm rounded-full"
                  >
                    {term}
                  </span>
                ))}
              </div>
            </div>
            
            {/* 来源 */}
            <div className="text-sm text-gray-500 pt-2 border-t">
              参考来源：{card.source}
            </div>
          </div>
        )}
      </div>
      
      {/* 射箭确认按钮 */}
      {!isConfirmed && (
        <div className="px-6 pb-4">
          <button
            onClick={handleConfirm}
            disabled={isConfirming}
            className="w-full py-3 bg-gradient-to-r from-yellow-400 to-orange-500 text-white font-semibold rounded-lg hover:from-yellow-500 hover:to-orange-600 transition-all disabled:opacity-50"
          >
            {isConfirming ? '确认中...' : '已掌握，点亮星图'}
          </button>
        </div>
      )}
    </div>
  )
}