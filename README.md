# llmwiki v2

AI-powered knowledge wiki platform — 通过 AI 对话自动构建个人知识图谱。

## 功能特性

- **AI 对话**：流式对话，自动注入 wiki 上下文 + 1-hop 图谱邻居扩展
- **知识图谱**：从对话和文档中自动提取概念，支持加权边、社区检测、意外连接发现、知识缺口分析
- **文档摄入**：上传 PDF/PPTX/DOCX/TXT/MD，AI 自动解析并生成结构化 wiki 页面
- **Deep Research**：联网搜索 + LLM 综合分析，产出研究型 wiki 页面
- **Wiki 浏览器**：树形目录浏览、全文搜索、图谱可视化、图谱洞察
- **审阅系统**：摄入产生的 contradictions / duplicates / suggestions 待审阅流程
- **用户画像**：学习风格、认知模式、兴趣领域的个性化上下文注入
- **多模型支持**：OpenAI / Claude / DeepSeek / Qwen / Kimi / Ollama 等（OpenAI 兼容 + Anthropic 协议）
- **多项目隔离**：独立的项目空间，不同知识库互不干扰
- **零数据库依赖**：纯 JSON + Markdown 文件存储，无需 PostgreSQL/Redis

## 技术栈

- **前端**：React 19 + TypeScript + Vite
- **后端**：FastAPI + Uvicorn
- **存储**：JSON（对话/设置/审阅项）+ Markdown + YAML frontmatter（wiki 页面）
- **LLM**：OpenAI 兼容接口 + Anthropic Messages API，支持多厂商动态切换
- **协议**：SSE（流式对话 / 摄入进度 / 研究进度）

## 快速开始

### 1. 安装依赖

```bash
# 前端
cd frontend && npm install && cd ..

# 后端
cd backend && pip install -r requirements.txt && cd ..
```

### 2. 配置环境变量

复制 `backend/.env.example` 为 `backend/.env`（或创建 `.env.local`）：

```env
# LLM 配置（至少填一个 API Key）
LLM_API_KEY=your_api_key
LLM_BASE_URL=https://api.openai.com/v1
LLM_MODEL=gpt-4o-mini

# Deep Research 搜索 API（可选）
SEARCH_API_PROVIDER=tavily
SEARCH_API_KEY=your_tavily_key

# 数据目录（默认 backend/data/）
DATA_DIR=./data
```

也可以启动后在设置页面动态配置 LLM（配置保存在 `data/settings.json`）。

**前端**：`frontend/.env`

```env
VITE_API_URL=http://localhost:8000
```

### 3. 启动

```bash
# 后端（端口 8000）
cd backend && uvicorn app.main:app --reload --port 8000

# 前端（端口 5173）
cd frontend && npm run dev
```

访问 http://localhost:5173

## 项目结构

```
├── frontend/                       # React 前端 (Vite)
│   └── src/
│       ├── components/
│       │   ├── ChatWindow.tsx          # 对话界面（流式 + 推理展示）
│       │   ├── GraphPage.tsx           # 知识图谱页
│       │   ├── KnowledgeGraph.tsx      # D3 图谱可视化（力导向布局）
│       │   ├── GraphInsights.tsx       # 图谱洞察面板
│       │   ├── WikiBrowser.tsx         # Wiki 页面浏览器
│       │   ├── WikiTree.tsx            # Wiki 目录树
│       │   ├── IngestPanel.tsx         # 文档摄入面板
│       │   ├── ReviewPanel.tsx         # 审阅项面板
│       │   ├── DeepResearchPanel.tsx   # 深度研究面板
│       │   ├── SettingsPanel.tsx       # 设置（LLM/搜索配置）
│       │   ├── ProjectHome.tsx         # 项目首页
│       │   ├── PreviewPanel.tsx        # 页面预览面板
│       │   ├── ContentNav.tsx          # 内容导航
│       │   └── GuidedOptions.tsx       # 引导选项组件
│       ├── contexts/
│       │   ├── PreviewContext.tsx       # 预览面板状态
│       │   └── ProjectContext.tsx       # 项目上下文
│       ├── hooks/
│       │   ├── useChat.ts              # 对话状态管理
│       │   └── useConversations.ts     # 对话列表管理
│       ├── lib/
│       │   ├── api.ts                  # API 请求封装（SSE + REST）
│       │   └── theme.ts               # 主题变量
│       └── types/
│           └── index.ts                # TypeScript 类型定义
│
├── backend/                        # FastAPI 后端
│   └── app/
│       ├── main.py                 # 应用入口 + 中间件（CORS/RequestID）
│       ├── config.py               # 环境变量配置
│       ├── dependencies.py         # 依赖注入（项目路由/存储）
│       ├── errors.py               # 统一错误处理
│       ├── llm.py                  # LLM 调用层（多 provider/流式适配）
│       ├── api/
│       │   ├── chat.py             # 对话 API（SSE 流式 + CRUD）
│       │   ├── wiki.py             # Wiki API（页面/图谱/搜索/媒体）
│       │   ├── ingest.py           # 文档摄入 API（SSE 进度）
│       │   ├── reviews.py          # 审阅项 API
│       │   ├── research.py         # Deep Research API（SSE 进度）
│       │   ├── projects.py         # 项目管理 API
│       │   └── settings.py         # 设置/用户画像/LLM 连接测试 API
│       ├── agents/
│       │   └── chat_agent.py       # 对话 Agent（wiki 检索 + 引导选项）
│       ├── storage/
│       │   ├── file_store.py       # JSON 文件存储（对话/设置/审阅/缓存）
│       │   ├── wiki_store.py       # Wiki .md 文件存储 + 图谱构建
│       │   └── project_store.py    # 项目管理
│       ├── ingest/
│       │   ├── pipeline.py         # 摄入主流程（10 步）+ FILE/REVIEW 解析
│       │   ├── file_parser.py      # 文档解析器（PDF/PPTX/DOCX/TXT/MD）
│       │   ├── image_extractor.py  # 嵌入图片提取
│       │   ├── image_caption.py    # 多模态图片描述生成
│       │   └── prompts.py          # 两阶段 LLM prompt 模板
│       ├── research/
│       │   └── deep_research.py    # Deep Research 流程（6 步）
│       ├── wiki/
│       │   └── context_budget.py   # 上下文预算分配器
│       ├── models/
│       │   └── responses.py        # Pydantic 响应/数据模型
│       └── utils/
│           └── logger.py           # 结构化日志
│
└── docker-compose.yml              # Docker 编排（开发/生产）
```

## 数据存储

所有数据存储在 `DATA_DIR`（默认 `backend/data/`）下：

```
data/
├── settings.json                   # LLM 配置（多 provider）
├── reviews.json                    # 待审阅项
├── ingest-cache.json               # 摄入缓存（SHA-256 幂等）
├── image-caption-cache.json        # 图片描述缓存
├── projects.json                   # 项目列表
├── profile/
│   └── profile.json                # 用户画像
├── conversations/
│   ├── index.json                  # 对话列表索引
│   └── {conv_id}/
│       └── messages.json           # 对话消息
├── page-history/                   # wiki 页面修改历史备份
├── wiki/
│   ├── entities/                   # 实体页（人物/组织/产品）
│   ├── concepts/                   # 概念页（理论/方法/技术）
│   ├── sources/                    # 源文档摘要页
│   ├── queries/                    # 研究查询记录
│   ├── comparisons/                # 对比分析页
│   ├── synthesis/                  # 综合分析页
│   ├── findings/                   # 发现页
│   ├── thesis/                     # 论点页
│   ├── methodology/                # 方法论页
│   └── media/                      # 嵌入图片
└── projects/                       # 多项目数据（每个项目独立目录）
    └── {project_id}/
        └── wiki/...
```

## API 接口

启动后访问 http://localhost:8000/docs 查看 Swagger 文档。

| 接口 | 方法 | 说明 |
|------|------|------|
| `/api/chat` | POST | SSE 流式对话 |
| `/api/conversations` | GET | 对话列表 |
| `/api/conversations/{id}` | GET | 对话详情 + 消息 |
| `/api/conversations/{id}` | PATCH | 重命名对话 |
| `/api/conversations/{id}` | DELETE | 删除对话 |
| `/api/wiki/pages` | GET | wiki 页面树 + 列表 |
| `/api/wiki/page` | GET | 读取 wiki 页面 |
| `/api/wiki/page` | DELETE | 删除 wiki 页面 |
| `/api/wiki/graph` | GET | 知识图谱（节点 + 边 + 社区） |
| `/api/wiki/graph/insights` | GET | 图谱洞察（意外连接 + 知识缺口） |
| `/api/wiki/graph/search` | GET | 搜索图谱节点 |
| `/api/wiki/search` | GET | 搜索 wiki 页面 |
| `/api/ingest` | POST | 上传文件摄入（SSE 进度） |
| `/api/ingest/batch` | POST | 批量文件摄入 |
| `/api/reviews` | GET | 审阅项列表 |
| `/api/reviews/{id}/resolve` | POST | 处理审阅项 |
| `/api/research` | POST | Deep Research（SSE 进度） |
| `/api/projects` | GET/POST | 项目列表 / 创建 |
| `/api/projects/{id}` | DELETE | 删除项目 |
| `/api/settings` | GET/PATCH | 全局设置 |
| `/api/settings/test-connection` | POST | 测试 LLM 连接 |
| `/api/settings/profile` | GET/PATCH | 用户画像 |
| `/health` | GET | 健康检查 |

### 项目隔离

所有数据 API 支持 `?project_id=` 查询参数路由到不同项目的数据目录。未指定时使用全局默认目录。

## 核心设计

### 知识图谱

- **节点**：9 种页面类型（entity / concept / source / comparison / synthesis / finding / thesis / methodology / query）
- **边**：4 维信号复合评分（直接 wikilink + 共享来源 + Adamic-Adar 共邻 + 类型亲和度）
- **社区**：加权连通分量检测，计算内聚度
- **洞察**：意外连接（跨社区/跨类型/桥接节点）+ 知识缺口（孤立节点/稀疏社区/桥接节点）

### 摄入 Pipeline（10 步）

0. 解析文件 → 纯文本；1. SHA-256 缓存检查；2. 图片提取；3. 图片描述（多模态）；4. 构建 wiki 索引；5. LLM 分析文档；6. LLM 生成 wiki 页面（FILE/REVIEW 块）；7. 解析 FILE 块写入 .md；8. Safety-net 图片注入；9. 解析 REVIEW 块；10. 保存缓存

### 对话上下文预算

根据模型上下文窗口动态分配字符预算：索引摘要 5% + wiki 页面 50% + 历史/系统 prompt 30% + 回复预留 15%

## 许可证

MIT License
