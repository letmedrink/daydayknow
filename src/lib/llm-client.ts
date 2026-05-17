import OpenAI from 'openai'
import { getLLMConfig, LLMConfig } from './llm-config'

// 创建OpenAI兼容客户端
// 大多数厂商都支持OpenAI兼容的API格式
function createClient(config: LLMConfig): OpenAI {
  return new OpenAI({
    baseURL: config.baseUrl,
    apiKey: config.apiKey,
  })
}

// 统一的LLM调用接口
export async function llmChatCompletion(params: {
  systemPrompt: string
  userPrompt: string
  responseFormat?: { type: 'json_object' | 'text' }
  temperature?: number
  maxTokens?: number
}): Promise<string> {
  const config = getLLMConfig()
  const client = createClient(config)
  
  const completion = await client.chat.completions.create({
    model: config.model,
    messages: [
      { role: 'system', content: params.systemPrompt },
      { role: 'user', content: params.userPrompt }
    ],
    response_format: params.responseFormat,
    temperature: params.temperature ?? config.temperature,
    max_tokens: params.maxTokens ?? config.maxTokens,
  })
  
  const content = completion.choices[0]?.message?.content
  if (!content) {
    throw new Error('LLM返回空内容')
  }
  
  return content
}

// JSON格式输出的LLM调用
export async function llmJsonCompletion<T = any>(params: {
  systemPrompt: string
  userPrompt: string
  temperature?: number
}): Promise<T> {
  const content = await llmChatCompletion({
    ...params,
    responseFormat: { type: 'json_object' },
    temperature: params.temperature ?? 0.3,
  })
  
  return JSON.parse(content)
}

// 获取当前LLM配置信息（用于日志）
export function getLLMInfo(): { provider: string; model: string; baseUrl: string } {
  const config = getLLMConfig()
  return {
    provider: config.provider,
    model: config.model,
    baseUrl: config.baseUrl
  }
}