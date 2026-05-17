// 本地模拟Supabase客户端（用于开发测试）
// 当没有真实Supabase数据库时使用

interface MockDatabase {
  terms: any[]
  daily_docs: any[]
  star_nodes: any[]
  star_edges: any[]
}

// 内存数据库
const mockDb: MockDatabase = {
  terms: [],
  daily_docs: [],
  star_nodes: [],
  star_edges: []
}

// 生成UUID
function generateId(): string {
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function(c) {
    const r = Math.random() * 16 | 0
    const v = c === 'x' ? r : (r & 0x3 | 0x8)
    return v.toString(16)
  })
}

// 模拟Supabase查询构建器
class MockQueryBuilder {
  private table: keyof MockDatabase
  private filters: any[] = []
  private selectFields: string = '*'

  constructor(table: keyof MockDatabase) {
    this.table = table
  }

  select(fields: string = '*') {
    this.selectFields = fields
    return this
  }

  insert(data: any) {
    const newItem = { ...data, id: data.id || generateId() }
    mockDb[this.table].push(newItem)
    return {
      select: () => ({
        single: () => Promise.resolve({ data: newItem, error: null })
      })
    }
  }

  update(data: any) {
    return {
      eq: (field: string, value: any) => {
        const index = mockDb[this.table].findIndex((item: any) => item[field] === value)
        if (index !== -1) {
          mockDb[this.table][index] = { ...mockDb[this.table][index], ...data }
          return Promise.resolve({ data: mockDb[this.table][index], error: null })
        }
        return Promise.resolve({ data: null, error: { message: 'Not found' } })
      }
    }
  }

  eq(field: string, value: any) {
    this.filters.push({ field, value, operator: 'eq' })
    return this
  }

  gte(field: string, value: any) {
    this.filters.push({ field, value, operator: 'gte' })
    return this
  }

  lte(field: string, value: any) {
    this.filters.push({ field, value, operator: 'lte' })
    return this
  }

  in(field: string, values: any[]) {
    this.filters.push({ field, value: values, operator: 'in' })
    return this
  }

  neq(field: string, value: any) {
    this.filters.push({ field, value, operator: 'neq' })
    return this
  }

  or(conditions: string) {
    // 简化处理，实际应该解析条件
    return this
  }

  order(field: string, options: { ascending: boolean }) {
    return this
  }

  limit(count: number) {
    return this
  }

  single() {
    const data = this.executeFilters()
    return Promise.resolve({ data: data[0] || null, error: data[0] ? null : { message: 'Not found' } })
  }

  then(resolve: (value: { data: any[], error: null }) => void) {
    const data = this.executeFilters()
    resolve({ data, error: null })
    return { data, error: null }
  }

  private executeFilters() {
    let data = [...mockDb[this.table]]
    
    for (const filter of this.filters) {
      switch (filter.operator) {
        case 'eq':
          data = data.filter((item: any) => item[filter.field] === filter.value)
          break
        case 'gte':
          data = data.filter((item: any) => item[filter.field] >= filter.value)
          break
        case 'lte':
          data = data.filter((item: any) => item[filter.field] <= filter.value)
          break
        case 'in':
          data = data.filter((item: any) => filter.value.includes(item[filter.field]))
          break
        case 'neq':
          data = data.filter((item: any) => item[filter.field] !== filter.value)
          break
        // 'or'操作符简化处理，实际应该解析条件
      }
    }
    
    return data
  }
}

// 模拟Supabase客户端
export const mockSupabase = {
  from: (table: keyof MockDatabase) => new MockQueryBuilder(table)
}

// 记录已初始化的用户
const initializedUsers = new Set<string>()

// 模拟数据生成函数（用于测试）
export function generateMockData(userId: string) {
  // 检查是否已经初始化过该用户
  if (initializedUsers.has(userId)) {
    return null
  }
  
  initializedUsers.add(userId)
  
  // 添加一些测试术语
  const mockTerms = [
    {
      id: generateId(),
      user_id: userId,
      term: '流动性陷阱',
      original_context: '日本经济长期陷入流动性陷阱',
      domain: '宏观经济学',
      confidence: 0.9,
      processed_status: 'done' as const,
      captured_at: new Date().toISOString()
    },
    {
      id: generateId(),
      user_id: userId,
      term: '零利率下限',
      original_context: '央行面临零利率下限的约束',
      domain: '宏观经济学',
      confidence: 0.85,
      processed_status: 'done' as const,
      captured_at: new Date().toISOString()
    }
  ]

  // 添加测试日报
  const mockDailyDoc = {
    id: generateId(),
    user_id: userId,
    doc_date: new Date().toISOString().split('T')[0],
    cards: [
      {
        term_id: mockTerms[0].id,
        term: '流动性陷阱',
        context: '日本经济长期陷入流动性陷阱',
        simple: '央行撒钱，但大家都不敢花',
        deep: '流动性陷阱是指当利率降到极低水平时，人们预期利率只会上升，因此宁愿持有现金也不愿投资或消费，导致货币政策失效的情况。这时央行增加货币供应量也无法刺激经济增长。',
        case: '日本1990年代泡沫破裂后，央行将利率降到接近零，但企业和个人仍不愿借贷消费，经济长期低迷，这就是典型的流动性陷阱。',
        related: ['零利率下限', '量化宽松', '货币政策'],
        source: '维基百科'
      }
    ],
    term_count: 1,
    generated_at: new Date().toISOString()
  }

  mockDb.terms.push(...mockTerms)
  mockDb.daily_docs.push(mockDailyDoc)

  return { mockTerms, mockDailyDoc }
}