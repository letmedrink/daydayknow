import { NextRequest, NextResponse } from 'next/server'
import { processDailyTerms } from '@/lib/batch/process-terms'
import { logger } from '@/lib/logger'

const log = logger.module('batch-api')

export async function POST(request: NextRequest) {
  const startTime = Date.now()
  
  try {
    log.info('收到批处理请求')
    
    // 检查授权
    const authHeader = request.headers.get('authorization')
    const cronSecret = process.env.CRON_SECRET || 'default-secret'
    
    if (authHeader !== `Bearer ${cronSecret}`) {
      log.warn('未授权的批处理请求')
      return NextResponse.json(
        { error: '未授权' },
        { status: 401 }
      )
    }
    
    // 获取请求体
    const body = await request.json().catch(() => ({}))
    const { userId, date } = body
    
    log.info('开始执行批处理', { userId, date })
    
    // 执行批处理
    const result = await processDailyTerms(userId, date)
    
    const duration = Date.now() - startTime
    
    if (result.success) {
      log.info('批处理完成', { 
        processed: result.processed, 
        skipped: result.skipped,
        duration: `${duration}ms` 
      })
      
      return NextResponse.json({
        message: '批处理完成',
        processed: result.processed,
        skipped: result.skipped,
        timestamp: new Date().toISOString()
      })
    } else {
      log.error('批处理失败', { error: result.error })
      return NextResponse.json(
        { error: '批处理失败', details: result.error },
        { status: 500 }
      )
    }
    
  } catch (error) {
    log.error('批处理API错误', error)
    return NextResponse.json(
      { error: '服务器内部错误' },
      { status: 500 }
    )
  }
}

// GET方法用于测试
export async function GET() {
  log.info('批处理API健康检查')
  
  return NextResponse.json({
    message: '批处理API端点',
    usage: 'POST /api/batch with Authorization header',
    timestamp: new Date().toISOString()
  })
}