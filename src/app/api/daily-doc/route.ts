import { NextRequest, NextResponse } from 'next/server'
import { db, generateUserId, isMockMode, initMockData } from '@/lib/db'
import { logger } from '@/lib/logger'

const log = logger.module('daily-doc')

export async function GET(request: NextRequest) {
  const startTime = Date.now()
  
  try {
    const { searchParams } = new URL(request.url)
    const date = searchParams.get('date') || new Date().toISOString().split('T')[0]
    const forceGenerate = searchParams.get('force') === 'true'
    
    log.info('收到日报获取请求', { date, forceGenerate })
    
    // 从请求头或查询参数获取用户ID
    const userId = request.headers.get('x-user-id') || 
                   request.nextUrl.searchParams.get('userId') ||
                   generateUserId()
    
    log.info('用户ID', { userId })
    
    // 初始化模拟数据（仅在模拟模式下）
    if (isMockMode) {
      const mockData = initMockData(userId)
      if (mockData) {
        log.info('初始化模拟数据', { userId })
        return NextResponse.json({
          doc_date: mockData.mockDailyDoc.doc_date,
          title: `昨日你收录了${mockData.mockDailyDoc.term_count}个术语`,
          cards: mockData.mockDailyDoc.cards,
          new_connections: [],
          generated_at: mockData.mockDailyDoc.generated_at
        })
      }
    }
    
    // 查询日报
    log.info('查询日报', { userId, date })
    const { data: dailyDoc, error } = await db
      .from('daily_docs')
      .select('*')
      .eq('user_id', userId)
      .eq('doc_date', date)
      .single()
    
    if (error) {
      log.debug('日报查询结果', { found: false, error: error.message })
    } else {
      log.debug('日报查询结果', { found: !!dailyDoc, termCount: dailyDoc?.term_count })
    }
    
    if (!dailyDoc) {
      // 查询该日期收集的术语
      log.info('日报不存在，查询收集的术语', { userId, date })
      
      const { data: terms, error: termsError } = await db
        .from('terms')
        .select('*')
        .eq('user_id', userId)
        .gte('captured_at', `${date}T00:00:00`)
        .lte('captured_at', `${date}T23:59:59`)
      
      if (termsError) {
        log.error('查询术语失败', termsError)
      }
      
      log.info('收集的术语', { count: terms?.length || 0 })
      
      const duration = Date.now() - startTime
      log.info('日报获取完成（未生成）', { duration: `${duration}ms` })
      
      return NextResponse.json({
        doc_date: date,
        title: '日报未生成',
        cards: [],
        new_connections: [],
        message: '今日日报尚未生成',
        terms_collected: terms?.map(t => ({
          id: t.id,
          term: t.term,
          domain: t.domain,
          captured_at: t.captured_at
        })) || [],
        terms_count: terms?.length || 0,
        can_generate: (terms?.length || 0) > 0
      })
    }
    
    // 查询相关的连线信息
    log.info('查询相关连线信息')
    let newConnections: any[] = []
    
    if (dailyDoc.cards && dailyDoc.cards.length > 0) {
      const termIds = dailyDoc.cards.map((card: any) => card.term_id)
      
      const { data: starNodes } = await db
        .from('star_nodes')
        .select('*')
        .eq('user_id', userId)
        .in('term_id', termIds)
      
      if (starNodes && starNodes.length > 0) {
        const nodeIds = starNodes.map((node: any) => node.id)
        const { data: edges } = await db
          .from('star_edges')
          .select('*')
          .eq('user_id', userId)
          .or(`from_node_id.in.(${nodeIds.join(',')}),to_node_id.in.(${nodeIds.join(',')})`)
        
        if (edges && edges.length > 0) {
          const nodeMap = new Map(starNodes.map((node: any) => [node.id, node]))
          
          newConnections = edges.map((edge: any) => {
            const fromNode = nodeMap.get(edge.from_node_id)
            const toNode = nodeMap.get(edge.to_node_id)
            
            return {
              from: fromNode?.term_name || '未知',
              to: toNode?.term_name || '未知',
              description: edge.description || '相关术语'
            }
          })
        }
      }
    }
    
    const duration = Date.now() - startTime
    log.info('日报获取完成', { 
      termCount: dailyDoc.term_count, 
      connectionsCount: newConnections.length,
      duration: `${duration}ms` 
    })
    
    return NextResponse.json({
      doc_date: dailyDoc.doc_date,
      title: `昨日你收录了${dailyDoc.term_count}个术语`,
      cards: dailyDoc.cards || [],
      new_connections: newConnections,
      generated_at: dailyDoc.generated_at
    })
    
  } catch (error) {
    log.error('获取日报错误', error)
    return NextResponse.json(
      { error: '获取日报失败' },
      { status: 500 }
    )
  }
}