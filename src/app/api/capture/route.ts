import { NextRequest, NextResponse } from 'next/server'
import { db, generateUserId, isMockMode } from '@/lib/db'
import { llmJsonCompletion } from '@/lib/llm-client'
import { validateLLMConfig } from '@/lib/llm-config'
import { logger } from '@/lib/logger'

const log = logger.module('capture')

// 术语提取Prompt
const EXTRACTION_PROMPT = `从用户分享的句子中提取核心专业术语。
输出JSON: { "terms": ["术语1", "术语2"], "domain": "领域" }
不要提取日常用语。如果无法确定，domain 填 "unknown"。`

// 模拟术语提取（用于开发测试）
function mockExtractTerms(text: string): { terms: string[], domain: string } {
  log.debug('使用模拟模式提取术语', { text })
  
  const terms: string[] = []
  
  const mockTermsMap: { [key: string]: { terms: string[], domain: string } } = {
    '流动性陷阱': { terms: ['流动性陷阱'], domain: '宏观经济学' },
    '零利率下限': { terms: ['零利率下限'], domain: '宏观经济学' },
    '量化宽松': { terms: ['量化宽松'], domain: '宏观经济学' },
    '债务货币化': { terms: ['债务货币化'], domain: '宏观经济学' },
    '通货膨胀': { terms: ['通货膨胀'], domain: '宏观经济学' },
    '人工智能': { terms: ['人工智能'], domain: '计算机科学' },
    '机器学习': { terms: ['机器学习'], domain: '计算机科学' },
    '深度学习': { terms: ['深度学习'], domain: '计算机科学' },
  }
  
  for (const [term, data] of Object.entries(mockTermsMap)) {
    if (text.includes(term)) {
      terms.push(...data.terms)
      log.debug('匹配到模拟术语', { term, domain: data.domain })
      return { terms, domain: data.domain }
    }
  }
  
  log.debug('未匹配到已知术语，返回默认值')
  return { terms: ['未知术语'], domain: 'unknown' }
}

export async function POST(request: NextRequest) {
  const startTime = Date.now()
  
  try {
    const body = await request.json()
    const { raw_text } = body
    
    log.info('收到术语捕获请求', { raw_text: raw_text?.substring(0, 100) })
    
    if (!raw_text) {
      log.warn('缺少raw_text参数')
      return NextResponse.json(
        { error: '缺少raw_text参数' },
        { status: 400 }
      )
    }
    
    // 从请求头或查询参数获取用户ID
    const userId = request.headers.get('x-user-id') || 
                   request.nextUrl.searchParams.get('userId') ||
                   generateUserId()
    
    log.info('用户ID', { userId })
    
    let extractionResult: { terms: string[], domain: string }
    
    // 检查是否使用模拟模式或LLM配置是否完整
    const llmConfig = validateLLMConfig()
    const useMock = isMockMode || !llmConfig.valid
    
    log.info('模式选择', { 
      isMockMode, 
      llmConfigValid: llmConfig.valid, 
      useMock,
      llmProvider: process.env.LLM_PROVIDER
    })
    
    if (useMock) {
      extractionResult = mockExtractTerms(raw_text)
    } else {
      log.info('调用LLM提取术语', { provider: process.env.LLM_PROVIDER })
      extractionResult = await llmJsonCompletion({
        systemPrompt: EXTRACTION_PROMPT,
        userPrompt: raw_text,
        temperature: 0.3,
      })
      log.info('LLM提取结果', extractionResult)
    }
    
    // 将提取的术语存入数据库
    log.info('开始保存术语到数据库', { terms: extractionResult.terms })
    const savedTerms = []
    
    for (const term of extractionResult.terms) {
      const { data, error } = await db.from('terms').insert({
        user_id: userId,
        term: term,
        original_context: raw_text,
        domain: extractionResult.domain,
        confidence: 0.8,
        processed_status: 'pending',
        captured_at: new Date().toISOString()
      }).select().single()
      
      if (error) {
        log.error('保存术语失败', { term, error })
        continue
      }
      
      savedTerms.push(data)
      log.debug('术语保存成功', { termId: data.id, term })
    }
    
    const duration = Date.now() - startTime
    log.info('术语捕获完成', { 
      savedCount: savedTerms.length, 
      duration: `${duration}ms` 
    })
    
    return NextResponse.json({
      extracted_term: extractionResult.terms[0] || '未知术语',
      all_terms: extractionResult.terms,
      domain: extractionResult.domain,
      message: '已捕获，明早日报见',
      user_id: userId,
      saved_count: savedTerms.length
    })
    
  } catch (error) {
    log.error('术语提取错误', error)
    return NextResponse.json(
      { error: '术语提取失败' },
      { status: 500 }
    )
  }
}