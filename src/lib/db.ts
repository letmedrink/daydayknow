import { supabase } from './supabase'
import { mockSupabase, generateMockData } from './mock-supabase'

// 模拟模式开关
// MOCK_MODE=true: 使用内存数据库，无需外部服务
// MOCK_MODE=false: 使用真实Supabase数据库
const isMockMode = process.env.MOCK_MODE === 'true'

// 数据库实例
export const db = isMockMode ? mockSupabase : supabase

// 初始化模拟数据（仅在模拟模式下）
export function initMockData(userId: string) {
  if (isMockMode) {
    return generateMockData(userId)
  }
  return null
}

// 生成用户ID（匿名用户）
export function generateUserId(): string {
  if (typeof window !== 'undefined') {
    // 客户端：从localStorage获取或生成新的
    let userId = localStorage.getItem('daydayknow_user_id')
    if (!userId) {
      userId = 'user_' + Math.random().toString(36).substr(2, 9)
      localStorage.setItem('daydayknow_user_id', userId)
    }
    return userId
  }
  // 服务端：生成临时ID
  return 'user_' + Math.random().toString(36).substr(2, 9)
}

export { isMockMode }