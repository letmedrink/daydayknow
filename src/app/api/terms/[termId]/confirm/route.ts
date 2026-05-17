import { NextRequest, NextResponse } from 'next/server'
import { db, generateUserId, isMockMode } from '@/lib/db'

// 生成UUID
function generateId(): string {
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function(c) {
    const r = Math.random() * 16 | 0
    const v = c === 'x' ? r : (r & 0x3 | 0x8)
    return v.toString(16)
  })
}

export async function POST(
  request: NextRequest,
  { params }: { params: Promise<{ termId: string }> }
) {
  try {
    const { termId } = await params
    
    if (!termId) {
      return NextResponse.json(
        { error: '缺少termId参数' },
        { status: 400 }
      )
    }
    
    // 从请求头或查询参数获取用户ID
    const userId = request.headers.get('x-user-id') || 
                   request.nextUrl.searchParams.get('userId') ||
                   generateUserId()
    
    // 查询术语信息
    const { data: term, error: termError } = await db
      .from('terms')
      .select('*')
      .eq('id', termId)
      .eq('user_id', userId)
      .single()
    
    if (termError || !term) {
      return NextResponse.json(
        { error: '术语不存在' },
        { status: 404 }
      )
    }
    
    // 更新术语状态为已处理
    const { error: updateError } = await db
      .from('terms')
      .update({ processed_status: 'done' })
      .eq('id', termId)
    
    if (updateError) {
      console.error('更新术语状态失败:', updateError)
    }
    
    // 创建星图节点
    const starNode = {
      id: generateId(),
      user_id: userId,
      term_id: termId,
      term_name: term.term,
      domain: term.domain,
      x: Math.random() * 100, // 随机坐标，前端会重新计算
      y: Math.random() * 100,
      confirmed_at: new Date().toISOString()
    }
    
    const { data: savedNode, error: nodeError } = await db
      .from('star_nodes')
      .insert(starNode)
      .select()
      .single()
    
    if (nodeError) {
      console.error('创建星图节点失败:', nodeError)
      return NextResponse.json(
        { error: '创建星图节点失败' },
        { status: 500 }
      )
    }
    
    // 检测并创建连线（同领域术语自动连线）
    const newConnections = []
    
    // 查询同领域的其他星图节点
    const { data: sameDomainNodes } = await db
      .from('star_nodes')
      .select('*')
      .eq('user_id', userId)
      .eq('domain', term.domain)
      .neq('id', savedNode.id)
    
    if (sameDomainNodes && sameDomainNodes.length > 0) {
      // 为每个同领域节点创建连线
      for (const otherNode of sameDomainNodes) {
        const edge = {
          id: generateId(),
          user_id: userId,
          from_node_id: savedNode.id,
          to_node_id: otherNode.id,
          relation_type: 'same_domain',
          description: `同属${term.domain}领域`,
          discovered_at: new Date().toISOString()
        }
        
        const { data: savedEdge, error: edgeError } = await db
          .from('star_edges')
          .insert(edge)
          .select()
          .single()
        
        if (!edgeError && savedEdge) {
          newConnections.push({
            from: term.term,
            to: otherNode.term_name,
            description: `同属${term.domain}领域`
          })
        }
      }
    }
    
    // 返回结果
    return NextResponse.json({
      message: '已点亮星图',
      star_node_id: savedNode.id,
      new_connections: newConnections,
      term_name: term.term,
      domain: term.domain
    })
    
  } catch (error) {
    console.error('射箭确认错误:', error)
    return NextResponse.json(
      { error: '射箭确认失败' },
      { status: 500 }
    )
  }
}