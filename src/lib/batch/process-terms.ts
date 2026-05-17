import { db, isMockMode } from '../db'
import { llmChatCompletion, llmJsonCompletion } from '../llm-client'
import { validateLLMConfig } from '../llm-config'
import { logger } from '../logger'

const log = logger.module('batch-processor')

// 假设文档生成Prompt
const HYDE_PROMPT = `你是一个知识渊博的学者。针对给定的术语，生成一篇500字的详细解释文档，用于辅助搜索。

文档结构要求：
1. 定义与起源：术语的准确定义、首次出现的时间和背景
2. 核心原理：详细解释其工作机制、理论基础
3. 实际应用：在现实中的应用场景、典型案例
4. 争议与局限：学术界或业界对此的不同看法
5. 相关概念：与其他术语的关联和区别

要求：
- 内容翔实，有具体数据和案例支持
- 允许推测性描述，但需标注为推测
- 这篇文档用户不会看到，仅用于检索参考`

// 最终解释生成Prompt
const FINAL_PROMPT = `你是一个善于用通俗语言解释复杂概念的朋友。基于检索到的资料，为用户生成一份详细且易懂的术语解释卡片。

输出JSON格式：
{
  "simple": "一句话白话解释，让小学生也能听懂，20字以内",
  "deep": "深入浅出的详细解释，包含：1)概念定义 2)工作原理 3)为什么重要，200-300字",
  "case": "至少1-2个具体案例，包含时间、地点、数据等细节，让概念更具体，150-200字",
  "history": "术语的起源和发展历程，100-150字",
  "related": ["3-5个相关术语，便于用户扩展学习"],
  "controversy": "学术界或业界对此的不同观点或争议（如有），100字",
  "source": "参考来源"
}

铁律：
- 每一条事实必须来自检索资料，不得编造
- 语气像知识渊博的朋友在讲解，亲切易懂
- 尽量使用类比和生活化的例子
- 如果某些字段信息不足，可以留空字符串`

// 模拟术语解释生成
function generateMockExplanation(term: string, domain: string) {
  const mockExplanations: { [key: string]: any } = {
    '流动性陷阱': {
      simple: '央行撒钱，但大家都不敢花',
      deep: '流动性陷阱是宏观经济学中的一个重要概念，由经济学家凯恩斯提出。当利率降到极低水平时，人们预期未来利率只会上升（债券价格下跌），因此宁愿持有现金也不愿投资或消费。这时央行增加货币供应量也无法刺激经济增长，货币政策失效。\n\n简单来说：就像你给小朋友发糖果，但小朋友觉得明天糖果会更便宜，所以今天都不吃，留着等明天。结果你发再多糖果也没用。',
      case: '日本"失去的三十年"：1990年日本泡沫经济破裂后，央行将利率降到接近零，但企业和个人仍不愿借贷消费。1999-2000年日本首次实施零利率政策，2016年甚至实施负利率，但经济仍长期低迷。这是全球最典型的流动性陷阱案例。\n\n另一个案例是2008年金融危机后的美国，美联储将利率降至0-0.25%，并实施多轮量化宽松，但经济复苏缓慢。',
      history: '流动性陷阱概念最早由凯恩斯在1936年《就业、利息和货币通论》中提出，用来描述货币政策失效的情况。2008年全球金融危机后，这一概念重新受到关注。',
      related: ['零利率下限', '量化宽松', '货币政策', '凯恩斯主义', '通货紧缩'],
      controversy: '部分经济学家认为流动性陷阱只是理论假设，现实中很少真正出现。也有学者认为即使利率为零，央行仍可通过前瞻性指引等工具影响预期。',
      source: '维基百科、美联储官网'
    },
    '零利率下限': {
      simple: '利率不能再降了，已经到底了',
      deep: '零利率下限（Zero Lower Bound，ZLB）是指名义利率无法降至零以下的约束。当经济陷入衰退时，央行通常会降低利率来刺激经济，但当利率降到零时，就无法继续降低。\n\n为什么会这样？因为如果利率为负，人们宁愿把钱存在家里（至少是0%），也不愿意存银行还要倒贴钱。这限制了传统货币政策的效果。',
      case: '2008年金融危机后，美联储将利率降至0-0.25%的区间，无法进一步降低，这就是零利率下限的体现。\n\n日本央行2016年尝试实施-0.1%的负利率，但效果有限，且引发争议。欧洲央行也尝试过负利率，但存款便利利率仅降至-0.5%。',
      history: '零利率下限问题在大萧条时期就被提出，但直到2008年金融危机后才真正成为全球央行面临的现实挑战。',
      related: ['流动性陷阱', '量化宽松', '负利率', '货币政策', '非常规货币政策'],
      controversy: '部分经济学家认为可以通过废除现金来突破零利率下限，但这会引发隐私和自由方面的争议。',
      source: '经济学原理、美联储研究'
    },
    '量化宽松': {
      simple: '央行买债券，往市场里灌钱',
      deep: '量化宽松（Quantitative Easing，QE）是指当利率降到零附近时，央行通过购买长期国债、企业债等资产，向市场注入大量流动性的非常规货币政策。\n\n操作方式：央行用新印的钱从银行手里买债券，银行拿到钱后有更多资金放贷，从而刺激经济。目的是降低长期利率，推高资产价格，促进投资和消费。',
      case: '2008年金融危机后，美联储实施了三轮QE：\n- QE1（2008-2010）：购买1.75万亿美元资产\n- QE2（2010-2011）：购买6000亿美元国债\n- QE3（2012-2014）：每月购买850亿美元\n\n日本央行2013年实施"安倍经济学"下的超级QE，每年购买80万亿日元国债。',
      history: 'QE最早由日本央行在2001年应对通缩时使用，2008年后被美联储、欧央行等广泛采用。',
      related: ['零利率下限', '流动性陷阱', '货币政策', '央行资产负债表', '资产购买'],
      controversy: '批评者认为QE加剧贫富差距（推高资产价格，富人受益），可能引发通胀和资产泡沫。支持者认为QE在危机时期避免了更严重的衰退。',
      source: '美联储官网、日本央行'
    }
  }

  if (mockExplanations[term]) {
    return mockExplanations[term]
  }

  return {
    simple: `${term}是一个${domain}领域的专业术语`,
    deep: `${term}是${domain}领域的一个重要概念。它通常指的是...\n\n（模拟模式：实际使用时会调用LLM生成详细解释）`,
    case: `关于${term}的具体案例...（模拟模式：实际使用时会调用LLM生成具体案例）`,
    history: `${term}的起源和发展...（模拟模式）`,
    related: ['相关术语1', '相关术语2', '相关术语3'],
    controversy: '',
    source: '模拟来源'
  }
}

// 批处理主函数
export async function processDailyTerms(userId?: string, targetDate?: string) {
  const startTime = Date.now()
  log.info('开始凌晨批处理', { userId, targetDate })
  
  try {
    // 1. 确定处理日期
    const date = targetDate || (() => {
      const yesterday = new Date()
      yesterday.setDate(yesterday.getDate() - 1)
      return yesterday.toISOString().split('T')[0]
    })()
    
    log.info('处理日期', { date })
    
    // 2. 读取pending术语
    let query = db
      .from('terms')
      .select('*')
      .eq('processed_status', 'pending')
      .gte('captured_at', `${date}T00:00:00`)
      .lte('captured_at', `${date}T23:59:59`)
    
    if (userId) {
      query = query.eq('user_id', userId)
    }
    
    const { data: pendingTerms, error: fetchError } = await query
    
    if (fetchError) {
      log.error('获取pending术语失败', fetchError)
      throw new Error(`获取pending术语失败: ${fetchError.message}`)
    }
    
    if (!pendingTerms || pendingTerms.length === 0) {
      log.info('没有需要处理的术语')
      return { success: true, processed: 0, skipped: 0 }
    }
    
    log.info('找到待处理术语', { count: pendingTerms.length })
    
    // 3. 按用户分组处理
    const termsByUser = pendingTerms.reduce((acc: any, term: any) => {
      if (!acc[term.user_id]) {
        acc[term.user_id] = []
      }
      acc[term.user_id].push(term)
      return acc
    }, {})
    
    let totalProcessed = 0
    let totalSkipped = 0
    
    // 4. 处理每个用户的术语
    for (const [uid, userTerms] of Object.entries(termsByUser)) {
      const terms = userTerms as any[]
      log.info('处理用户术语', { userId: uid, termsCount: terms.length })
      
      // 5. 检查日报是否已生成
      const { data: existingDoc } = await db
        .from('daily_docs')
        .select('*')
        .eq('user_id', uid)
        .eq('doc_date', date)
        .single()
      
      if (existingDoc) {
        log.info('日报已存在，跳过生成', { userId: uid, date })
        totalSkipped += terms.length
        continue
      }
      
      // 6. 领域消歧
      const processedTerms = terms.map(term => ({
        ...term,
        domain: term.domain || 'unknown'
      }))
      
      // 7. 生成解释
      const llmConfig = validateLLMConfig()
      const useMock = isMockMode || !llmConfig.valid
      
      log.info('生成术语解释', { useMock, termsCount: processedTerms.length })
      
      const cards = []
      
      for (const term of processedTerms) {
        let explanation
        
        if (useMock) {
          explanation = generateMockExplanation(term.term, term.domain)
        } else {
          try {
            const hydeDoc = await llmChatCompletion({
              systemPrompt: HYDE_PROMPT,
              userPrompt: term.term,
              temperature: 0.7,
            })
            
            explanation = await llmJsonCompletion({
              systemPrompt: FINAL_PROMPT,
              userPrompt: `术语：${term.term}\n领域：${term.domain}\n资料：${hydeDoc}`,
              temperature: 0.3,
            })
          } catch (error) {
            log.error(`LLM调用失败: ${term.term}`, error)
            explanation = generateMockExplanation(term.term, term.domain)
          }
        }
        
        cards.push({
          term_id: term.id,
          term: term.term,
          context: term.original_context,
          ...explanation
        })
        
        log.debug('术语解释生成完成', { term: term.term })
      }
      
      // 8. 保存日报
      log.info('保存日报', { userId: uid, date, cardsCount: cards.length })
      
      const insertResult = await db
        .from('daily_docs')
        .insert({
          user_id: uid,
          doc_date: date,
          cards: cards,
          term_count: cards.length,
          generated_at: new Date().toISOString()
        })
      
      const insertError = insertResult && 'error' in insertResult ? insertResult.error : null
      
      if (insertError) {
        log.error('保存日报失败', insertError)
        continue
      }
      
      // 9. 更新术语状态
      log.info('更新术语状态为已处理', { count: terms.length })
      
      for (const term of terms) {
        await db
          .from('terms')
          .update({ processed_status: 'done' })
          .eq('id', term.id)
      }
      
      totalProcessed += terms.length
      log.info('用户处理完成', { userId: uid, processed: terms.length })
    }
    
    const duration = Date.now() - startTime
    log.info('批处理完成', { 
      processed: totalProcessed, 
      skipped: totalSkipped,
      duration: `${duration}ms` 
    })
    
    return { success: true, processed: totalProcessed, skipped: totalSkipped }
    
  } catch (error) {
    log.error('批处理失败', error)
    return { success: false, error: (error as Error).message, processed: 0, skipped: 0 }
  }
}