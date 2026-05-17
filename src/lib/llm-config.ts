// LLM配置 - 支持多厂商
// 通过修改base_url和api_key即可切换不同厂商

export interface LLMConfig {
  provider: string
  baseUrl: string
  apiKey: string
  model: string
  maxTokens: number
  temperature: number
}

// 预设的厂商配置
export const LLM_PROVIDERS = {
  // OpenAI（默认）
  openai: {
    baseUrl: 'https://api.openai.com/v1',
    models: {
      fast: 'gpt-4o-mini',
      standard: 'gpt-4o',
      premium: 'gpt-4-turbo'
    }
  },
  // Claude (Anthropic)
  claude: {
    baseUrl: 'https://api.anthropic.com/v1',
    models: {
      fast: 'claude-3-haiku-20240307',
      standard: 'claude-3-sonnet-20240229',
      premium: 'claude-3-opus-20240229'
    }
  },
  // 通义千问（阿里）
  qwen: {
    baseUrl: 'https://dashscope.aliyuncs.com/compatible-mode/v1',
    models: {
      fast: 'qwen-turbo',
      standard: 'qwen-plus',
      premium: 'qwen-max'
    }
  },
  // 智谱AI
  zhipu: {
    baseUrl: 'https://open.bigmodel.cn/api/paas/v4',
    models: {
      fast: 'glm-4-flash',
      standard: 'glm-4',
      premium: 'glm-4-plus'
    }
  },
  // DeepSeek
  deepseek: {
    baseUrl: 'https://api.deepseek.com/v1',
    models: {
      fast: 'deepseek-chat',
      standard: 'deepseek-chat',
      premium: 'deepseek-reasoner'
    }
  },
  // 本地部署（Ollama等）
  local: {
    baseUrl: 'http://localhost:11434/v1',
    models: {
      fast: 'qwen2.5:7b',
      standard: 'qwen2.5:14b',
      premium: 'qwen2.5:72b'
    }
  }
}

// 获取LLM配置
export function getLLMConfig(): LLMConfig {
  const provider = process.env.LLM_PROVIDER || 'openai'
  const modelLevel = process.env.LLM_MODEL_LEVEL || 'fast'
  
  const providerConfig = LLM_PROVIDERS[provider as keyof typeof LLM_PROVIDERS]
  
  if (!providerConfig) {
    throw new Error(`不支持的LLM厂商: ${provider}，支持的厂商: ${Object.keys(LLM_PROVIDERS).join(', ')}`)
  }
  
  return {
    provider,
    baseUrl: process.env.LLM_BASE_URL || providerConfig.baseUrl,
    apiKey: process.env.LLM_API_KEY || process.env.OPENAI_API_KEY || '',
    model: process.env.LLM_MODEL || providerConfig.models[modelLevel as keyof typeof providerConfig.models] || providerConfig.models.fast,
    maxTokens: parseInt(process.env.LLM_MAX_TOKENS || '2000'),
    temperature: parseFloat(process.env.LLM_TEMPERATURE || '0.7')
  }
}

// 检查LLM配置是否完整
export function validateLLMConfig(): { valid: boolean; errors: string[] } {
  const errors: string[] = []
  
  const apiKey = process.env.LLM_API_KEY || process.env.OPENAI_API_KEY
  if (!apiKey) {
    errors.push('缺少LLM_API_KEY或OPENAI_API_KEY环境变量')
  }
  
  const provider = process.env.LLM_PROVIDER || 'openai'
  if (!LLM_PROVIDERS[provider as keyof typeof LLM_PROVIDERS]) {
    errors.push(`不支持的LLM厂商: ${provider}`)
  }
  
  return {
    valid: errors.length === 0,
    errors
  }
}