# 知微 (DayDayKnow)

格物致知，见微知著 — AI 知识学习平台。

通过自然对话自动提取知识概念，构建个人知识图谱。

## 功能特性

- **多 Agent 对话**：Router 意图分类 → 专家角色匹配 → 流式对话
- **知识提取**：对话结束后自动提取概念和关系，存入知识图谱
- **知识图谱**：可视化展示概念关联，支持领域筛选、置信度过滤、N 跳邻居
- **对话管理**：创建 / 重命名 / 删除 / 搜索 / 导出对话
- **内容导入**：文本 / JSON / CSV 文件批量导入知识
- **用户画像**：从对话中分析学习风格、认知模式、知识水平
- **多 LLM 支持**：OpenAI / Claude / DeepSeek / 通义千问 / Ollama
- **Docker 部署**：PostgreSQL (pgvector) + Redis + ARQ Worker 一键启动

## 技术栈

- **前端**：React 19 + TypeScript + Vite + React Router
- **后端**：FastAPI + Uvicorn + SQLAlchemy (async)
- **数据库**：PostgreSQL + pgvector / InMemory（开发模式）
- **任务队列**：ARQ + Redis（降级为内联执行）
- **LLM**：OpenAI 兼容接口，支持多厂商切换
- **测试**：Pytest（236 个测试）
- **部署**：Docker Compose + Nginx

## 快速开始

### 1. 克隆项目

```bash
git clone <repository-url>
cd daydayknow
```

### 2. 安装依赖

```bash
# 前端
cd frontend && npm install && cd ..

# 后端
cd backend && pip install -r requirements.txt && cd ..
```

### 3. 配置环境变量

**后端**：复制 `backend/.env.example` 为 `backend/.env`

```env
# 模拟模式（无需外部服务）
MOCK_MODE=true

# 或使用真实 LLM
MOCK_MODE=false
LLM_PROVIDER=deepseek
LLM_API_KEY=your_api_key

# 可选：PostgreSQL
DATABASE_URL=postgresql+asyncpg://user:pass@host/db

# 可选：Redis（ARQ 任务队列）
REDIS_URL=redis://localhost:6379
```

**前端**：`frontend/.env`

```env
VITE_API_URL=http://localhost:8000
```

### 4. 启动

```bash
# 后端（端口 8000）
cd backend && uvicorn app.main:app --reload --port 8000

# 前端（端口 5173）
cd frontend && npm run dev
```

访问 http://localhost:5173

## 项目结构

```
├── frontend/                   # React 前端 (Vite)
│   └── src/
│       ├── components/
│       │   ├── ChatWindow.tsx      # 对话界面
│       │   ├── GraphPage.tsx       # 知识图谱页
│       │   ├── KnowledgeGraph.tsx  # 图谱可视化
│       │   ├── ImportPanel.tsx     # 内容导入
│       │   ├── ProfilePage.tsx     # 用户画像
│       │   ├── Sidebar.tsx         # 对话列表
│       │   └── NavRail.tsx         # 导航栏
│       ├── hooks/
│       │   ├── useChat.ts          # 对话状态管理
│       │   └── useConversations.ts # 对话列表管理
│       ├── lib/
│       │   └── api.ts              # API 请求封装
│       └── types/
│           └── index.ts            # 类型定义
│
├── backend/                    # FastAPI 后端
│   └── app/
│       ├── main.py             # 应用入口 + 中间件
│       ├── config.py           # 环境变量配置
│       ├── dependencies.py     # 依赖注入（用户认证）
│       ├── errors.py           # 统一错误处理
│       ├── api/                # API 路由
│       │   ├── chat.py         # 对话 + 知识图谱 CRUD
│       │   ├── conversations.py # 对话管理
│       │   └── import_.py      # 内容导入
│       ├── agents/             # 多 Agent 系统
│       │   ├── router_agent.py # 意图分类路由
│       │   ├── chat_agent.py   # 对话 Agent（流式）
│       │   ├── extraction_agent.py # 知识提取
│       │   ├── profile_agent.py # 用户画像分析
│       │   ├── conflict_agent.py # 知识冲突检测
│       │   └── orchestrator.py # 后处理编排
│       ├── db/
│       │   ├── graph_store.py      # InMemory 存储
│       │   ├── postgres_store.py   # PostgreSQL 存储
│       │   └── factory.py          # 存储工厂（单例）
│       ├── services/
│       │   ├── llm/            # LLM 供应商
│       │   ├── embedding/      # 向量嵌入
│       │   └── auth.py         # JWT 认证
│       ├── tasks/
│       │   ├── queue.py        # ARQ 任务队列
│       │   └── worker.py       # 后台 Worker
│       ├── models/
│       │   └── responses.py    # Pydantic 响应模型
│       └── utils/
│           └── logger.py       # 结构化日志
│
├── docker-compose.yml          # Docker 编排
└── backend/tests/              # Pytest 测试 (236)
```

## API 接口

启动后访问 http://localhost:8000/docs 查看 Swagger 文档。

| 接口 | 方法 | 说明 |
|------|------|------|
| `/api/chat` | POST | SSE 流式对话 |
| `/api/conversations` | GET | 对话列表 |
| `/api/conversations/{id}` | GET | 对话详情 + 消息 |
| `/api/conversations/{id}` | PATCH | 重命名对话 |
| `/api/search` | POST | 搜索知识节点 |
| `/api/knowledge/{user_id}` | GET | 获取知识图谱 |
| `/api/knowledge/node/{id}` | GET | 节点详情 + 邻居 |
| `/api/import` | POST | 文本导入 |
| `/api/import/batch` | POST | 文件批量导入 |
| `/api/stats/{user_id}` | GET | 图谱统计 |
| `/api/profile/{user_id}` | GET | 用户画像 |
| `/health` | GET | 健康检查 |

## 测试

```bash
cd backend && python -m pytest tests/ -v
```

## 部署

### Docker

```bash
# 开发环境
docker compose --profile dev up

# 生产环境
docker compose --profile prod up

# 生产 + Nginx
docker compose --profile prod-nginx up
```

## 许可证

MIT License
