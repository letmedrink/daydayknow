import { NextRequest, NextResponse } from 'next/server'
import { db, generateUserId, isMockMode } from '@/lib/db'
import { logger } from '@/lib/logger'

const log = logger.module('star-map-api')

export async function GET(request: NextRequest) {
  const startTime = Date.now()
  
  try {
    log.info('收到星图数据请求')
    
    // 从请求头或查询参数获取用户ID
    const userId = request.headers.get('x-user-id') || 
                   request.nextUrl.searchParams.get('userId') ||
                   generateUserId()
    
    log.info('用户ID', { userId })
    
    // 查询星图节点
    log.info('查询星图节点', { userId })
    const { data: nodes, error: nodesError } = await db
      .from('star_nodes')
      .select('*')
      .eq('user_id', userId)
      .order('confirmed_at', { ascending: false })
    
    if (nodesError) {
      log.error('查询星图节点失败', nodesError)
      return NextResponse.json(
        { error: '查询星图节点失败' },
        { status: 500 }
      )
    }
    
    log.info('查询到星图节点', { count: nodes?.length || 0 })
    
    // 查询星图连线
    log.info('查询星图连线', { userId })
    const { data: edges, error: edgesError } = await db
      .from('star_edges')
      .select('*')
      .eq('user_id', userId)
    
    if (edgesError) {
      log.error('查询星图连线失败', edgesError)
      return NextResponse.json(
        { error: '查询星图连线失败' },
        { status: 500 }
      )
    }
    
    log.info('查询到星图连线', { count: edges?.length || 0 })
    
    // 计算节点位置（简单的力导向布局）
    const nodesWithPosition = (nodes || []).map((node, index) => {
      // 如果节点没有位置信息，使用简单的圆形布局
      if (!node.x || !node.y) {
        const angle = (index / (nodes?.length || 1)) * 2 * Math.PI
        const radius = 150
        return {
          ...node,
          x: 250 + radius * Math.cos(angle),
          y: 250 + radius * Math.sin(angle)
        }
      }
      return node
    })
    
    const duration = Date.now() - startTime
    log.info('星图数据获取完成', { 
      nodesCount: nodesWithPosition.length, 
      edgesCount: edges?.length || 0,
      duration: `${duration}ms` 
    })
    
    return NextResponse.json({
      nodes: nodesWithPosition,
      edges: edges || [],
      stats: {
        total_nodes: nodesWithPosition.length,
        total_edges: edges?.length || 0,
        domains: [...new Set(nodesWithPosition.map(n => n.domain))]
      }
    })
    
  } catch (error) {
    log.error('获取星图数据错误', error)
    return NextResponse.json(
      { error: '获取星图数据失败' },
      { status: 500 }
    )
  }
}