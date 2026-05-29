# 知微 POC 技术验证进度

## 执行状态

| 阶段 | 状态 | 测试数 | 提交 |
|------|------|--------|------|
| Phase 1: LLM 供应商抽象层 | ✅ 完成 | 16 passed | `154639b` |
| Phase 2: Agent 系统 | ✅ 完成 | 16 passed | `04cfd9d` |
| Phase 3: 图谱存储 | ✅ 完成 | 11 passed | `d2842df` |
| Phase 4: API 层 SSE 端点 | ✅ 完成 | 6 passed | `90594df` |
| Phase 5: 最小前端 | ✅ 完成 | TypeScript 编译 + Vite 构建通过 | `8044cbe` |
| Phase 6: 联调归档 | ✅ 完成 | 全量 67 tests passed | `5e8917e` |
| Phase 7: 对话持久化 | ✅ 完成 | +22 tests → 89 passed | `2ff5028` |
| Phase 8: 对话历史侧边栏 | ✅ 完成 | TypeScript 编译 + Vite 构建通过 | `0e99c65` |
| Phase 9: 知识图谱可视化 | ✅ 完成 | 89 tests + Vite 构建通过 | `0cebb88` |
| Phase 10: 用户画像 Agent | ✅ 完成 | +9 tests → 95 passed | `d752197` |
| Phase 11: 上下文窗口管理 | ✅ 完成 | +6 tests → 101 passed | `706ccf5` |
| Phase 12: 遗留代码清理 | ✅ 完成 | 86 tests（-18 遗留） | `3d53368` |
| Phase 13: 图谱独立页面 | ✅ 完成 | 86 tests + Vite 构建通过 | `6681887` |
| Phase 14: 三栏导航 + 图谱交互 | ✅ 完成 | 86 tests + Vite 构建通过 | `6334815` |
| Phase 15: 莫兰迪色系 + 更名知微 | ✅ 完成 | 86 tests + Vite 构建通过 | `5991fa2` |
| Phase 16: 路由Agent + 专家角色 | ✅ 完成 | +4 tests → 92 passed | |
| Phase 17: 画像注入对话 | ✅ 完成 | +6 tests → 98 passed | |
| Phase 18: 内容导入 | ✅ 完成 | +1 test → 99 passed | |
| Phase 19: 图谱交互增强 | ✅ 完成 | 99 tests + Vite 构建通过 | |
| Phase 20: 冲突检测 Agent | ✅ 完成 | +12 tests → 111 passed | |
| Phase 21: 摘要 Agent | ✅ 完成 | +7 tests → 118 passed | |
| Phase 22: 元评估 Agent | ✅ 完成 | +5 tests → 123 passed | |
| Phase 23: LangGraph 编排 | ✅ 完成 | +4 tests → 127 passed | |
| Phase 24: PostgreSQL 持久化 | ✅ 完成 | 127 tests + Alembic 迁移 | |
| **总计** | | **127 passed, 0 failed** | |

## 验证链路

```
用户输入 → POST /api/chat (SSE)
  → 创建/加载 Conversation 记录
  → 保存用户消息
  → RouterAgent → 意图分类(explore/explain/quiz) + 专家匹配(generalist/teacher/analyst) + 深度(quick/deep)
  → truncate_messages() 双重限制 (max_messages=20, max_tokens=6000)
  → ChatAgent.stream() (带专家 System Prompt + 用户画像注入 + depth 控制 token)
  → LLMProvider.chat_stream() → 逐字产出
  → SSE chunk 事件推送到前端
  → 流式完成 → SSE done 事件
  → 保存助手回复
  → LangGraph 后处理编排 (PostProcessOrchestrator)
    ├── extract (并行) → conflict_check → evaluate
    └── profile_update (并行) ─────────────→ evaluate
  → evaluate: accept/retry/fail
  → SSE extraction/conflict/profile 事件
  → 前端展示本轮提取图谱（可折叠）+ 独立图谱页可查看全量
  → GET /api/conversations → 对话侧栏刷新

内容导入 → POST /api/import
  → ExtractionAgent.execute() → 提取概念
  → InMemoryGraphStore.store_extraction() → 存储
  → 返回 nodes/edges
```

## 新增文件清单

### 后端新增
```
backend/app/
  services/llm/
    __init__.py          # LLM 包入口
    base.py              # LLMProvider ABC (chat/chat_stream/chat_json)
    mock.py              # MockLLMProvider (测试用)
    deepseek.py          # DeepSeek 供应商
    openai_provider.py   # OpenAI 供应商
    anthropic_provider.py # Anthropic 供应商
    router.py            # ModelRouter 单例
  agents/
    __init__.py          # Agent 包入口
    base.py              # BaseAgent ABC + AgentResult
    context.py           # AgentContext + Message
    registry.py          # AgentRegistry 装饰器注册
    chat_agent.py        # ChatAgent (execute + stream, truncate_messages, 专家 prompt + 画像注入)
    extraction_agent.py  # ExtractionAgent (概念提取)
    profile_agent.py     # ProfileAgent (12 维度用户画像分析)
    router_agent.py      # RouterAgent (意图分类 + 专家角色匹配)
    conflict_agent.py    # ConflictAgent (知识一致性检测)
    summary_agent.py     # SummaryAgent (分层对话压缩)
    evaluation_agent.py  # EvaluationAgent (元评估提取质量)
    orchestrator.py      # PostProcessOrchestrator (LangGraph StateGraph 编排)
  api/
    __init__.py
    chat.py              # POST /api/chat SSE + GET /api/knowledge (含路由调用 + 画像注入)
    conversations.py     # GET/DELETE /api/conversations
    import_.py           # POST /api/import (内容导入)
  models/
    knowledge.py         # KgNode, KgEdge, ExtractionResult
  db/
    __init__.py
    graph_store.py       # InMemoryGraphStore (节点/边/对话/消息)
    models.py            # SQLAlchemy 声明式模型 (7 张表)
    postgres_store.py    # PostgresGraphStore (与 InMemory 接口对齐)
    factory.py           # get_graph_store() 工厂 (按配置切换)

backend/tests/
  test_llm/              # 11 tests
  test_agents/           # 46 tests (chat + extraction + profile + router + conflict + summary + evaluation + orchestrator)
  test_db/               # 36 tests (graph + conversation + profile + versioning)
  test_api/              # 34 tests (chat + 对话 + 导入 + 端到端)
```

### 前端新增
```
frontend/
  package.json           # React 19 + Vite 6 + react-router-dom + react-force-graph-2d
  vite.config.ts
  tsconfig.json
  index.html             # 标题: 知微 - AI 知识学习
  src/
    main.tsx             # 入口
    App.tsx              # 三栏布局: NavRail + ConversationPanel + Routes (含 /import)
    types/index.ts       # TypeScript 类型（Message, Conversation, KgNode, KgEdge, UserProfile）
    lib/api.ts           # SSE 客户端 + 对话/图谱/画像 API
    hooks/
      useChat.ts         # 对话状态管理（loadMessages, reset, extractionNodes/Edges）
      useConversations.ts # 对话列表管理
    components/
      NavRail.tsx        # 左侧导航栏 (对话/图谱/画像/导入)
      Sidebar.tsx        # 对话列表面板 (ConversationPanel)
      ChatWindow.tsx     # 对话界面（Markdown 渲染 + 本轮提取图谱）
      GraphPage.tsx      # 独立知识图谱页面 (/graph，含筛选 + N-hop 高亮)
      ProfilePage.tsx    # 独立学习画像页面 (/profile)
      ImportPanel.tsx    # 内容导入页面 (/import)
      KnowledgeGraph.tsx # 力导向图谱可视化（悬停提示 + 边界钳位 + N-hop BFS）
```

## 未纳入 POC 的功能（Phase 2+）

- LangGraph 编排（Agent 目前串行调用）
- 冲突检测 Agent
- pgvector embedding（按名称去重）
- 真实认证（Supabase Auth）
- Redis / ARQ 异步任务队列
- 本地 Embedding 模型
- PostgreSQL 持久化（当前 InMemory，schema 已对齐）

## Demo 启动方式

```bash
# Terminal 1: 后端
cd backend
source .venv/bin/activate
uvicorn app.main:app --reload --port 8000

# Terminal 2: 前端
cd frontend
npm run dev

# 浏览器 http://localhost:5173
```

## 面试讲点

1. **供应商抽象**：ABC 模式，每个供应商用原生 SDK，system 消息分离（Anthropic 特殊处理）
2. **stream() 不在 BaseAgent 上**：只有对话 Agent 需要流式，避免强制所有 Agent 实现
3. **InMemory ↔ Postgres 零切换成本**：工厂模式 + 相同方法签名，DATABASE_URL 为空自动降级
4. **TDD + MockProvider**：127 个测试全用 Mock，零 API Key 依赖
5. **LangGraph 编排**：并行提取+画像、串行冲突检测、条件重试，Agent 代码零修改
6. **冲突检测 + 知识版本化**：superseded_by 追踪、strength=0 软删除边
7. **分层摘要压缩**：详细/中等/简短三级压缩，保持长对话上下文窗口可控
8. **SQLAlchemy async + Alembic**：asyncpg 驱动、声明式模型、版本化迁移
9. **PostgresGraphStore 返回 dict**：调用方零修改，ORM 对象不泄漏到业务层
5. **SSE 实现**：ReadableStream API 解析，非 EventSource（因为 SSE 只支持 GET）
6. **上下文窗口管理**：双限制滑动窗口（max_messages + max_tokens），保留 system 消息
7. **用户画像智能合并**：dict 递归合并、list 去重、null 跳过，支持增量演化
8. **遗留代码清理**：1685 行删除，Agent 架构完全替代旧路由
9. **SSE 实际数据传输**：extraction 事件发送完整节点/边而非计数，前端零额外请求即可渲染
10. **图谱交互**：graph2ScreenCoords 坐标转换 + 容器边界钳位，防止 tooltip 溢出
11. **三栏导航架构**：NavRail(64px) + Panel(240px) + Content 区域分离，路由驱动面板显隐
