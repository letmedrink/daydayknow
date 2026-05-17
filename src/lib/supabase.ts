import { createClient } from '@supabase/supabase-js'

const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL!
const supabaseAnonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!

export const supabase = createClient(supabaseUrl, supabaseAnonKey)

// 数据库类型定义
export interface Term {
  id: string
  user_id: string
  term: string
  original_context: string
  domain: string
  confidence: number
  processed_status: 'pending' | 'done'
  captured_at: string
}

export interface DailyDoc {
  id: string
  user_id: string
  doc_date: string
  cards: DailyDocCard[]
  term_count: number
  generated_at: string
}

export interface DailyDocCard {
  term_id: string
  term: string
  context: string
  simple: string
  deep: string
  case: string
  related: string[]
  source: string
}

export interface StarNode {
  id: string
  user_id: string
  term_id: string
  term_name: string
  domain: string
  x: number
  y: number
  confirmed_at: string
}

export interface StarEdge {
  id: string
  user_id: string
  from_node_id: string
  to_node_id: string
  relation_type: string
  description: string
  discovered_at: string
}