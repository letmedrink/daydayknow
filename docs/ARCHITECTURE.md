# DayDayKnow（日知录）架构设计文档

> "把每次对话变成结构化知识资产"

## 一、产品定位

### 核心价值
DayDayKnow 是一个基于 AI Agent 架构的智能知识学习平台。核心差异在于：用户与 AI 的每次对话都会被自动提炼为结构化知识，沉淀为个人知识图谱，并基于用户画像实现个性化教学。

### 目标用户
通用型——任何想要获取和管理知识的人。

### 核心差异化
与 ChatGPT、Claude 等通用对话产品不同，DayDayKnow 的每次对话都不是"聊完就散"，而是：
- 自动提取对话中的概念和关系，更新知识图谱
- 分析用户理解程度，更新用户画像
- 下次对话注入画像信息，实现"因材施教"

---

## 二、功能模块

### 2.1 智能对话

- 用户可选择不同领域的专家角色（如 Python 专家、金融分析师），也支持交叉领域专家和通才型
- 每个对话窗口对应一次会话，可随时继续或新建
- 流式输出（打字机效果）
- 支持对话过程中实时检索补充知识

### 2.2 知识图谱

- **核心交互界面**，用户主动探索和浏览
- 节点 = 概念，边 = 概念间关系
- 知识来源：对话 + 外部内容导入

#### 节点提取策略（混合方案）
```
LLM 提取候选概念
  → Embedding 相似度匹配已有节点（快速过滤）
  → 相似度 0.7~0.85 灰色地带 → LLM 二次判断（是否合并）
  → 低于 0.7 → 直接新建节点
```

#### 边关系类型（18 种，8 大类）

| 大类 | 关系类型 | 说明 |
|------|----------|------|
| 分类 | `is-a`, `instance-of` | 继承/实例 |
| 组成 | `part-of`, `composed-of` | 部分/组成 |
| 因果 | `causes`, `enables`, `prevents` | 因果关系 |
| 顺序 | `precedes`, `evolves-to` | 先后/演化 |
| 相似/对比 | `similar-to`, `opposite-of`, `competes-with` | 类比/对立 |
| 依赖 | `requires`, `specializes` | 前置/专精 |
| 应用 | `applies-to`, `solves` | 应用场景 |
| 跨域 | `analogous-to`, `derived-from` | 类比借鉴 |
| 量化 | `improves-on`, `trade-off` | 改进/权衡 |

#### 图谱膨胀控制策略
- **数据层宽松**：只在对话中发现有语义关联时才创建边，不暴力枚举
- **展示层收敛**：N-hop 视图（只显示当前节点邻居）、分层抽象（领域→概念）、边强度评分、弱边定期剪枝

### 2.3 用户画像（12 维度）

| 维度 | 说明 | 更新方式 |
|------|------|----------|
| 知识水平 | 各领域掌握程度（0-100） | 对话自动评估 |
| 知识盲区 | 暴露但未深入的概念 | 对话中检测 |
| 前置缺失 | 基础薄弱点推断 | 依赖图谱推断 |
| 兴趣方向 | 近期关注主题及趋势 | 频率分析 |
| 学习风格 | 类比型/公式型/案例型/图解型 | 风格分析 |
| 认知模式 | 自顶向下 vs 自底向上 | 提问模式判断 |
| 学习节奏 | 快速/稳定/需要重复 | 掌握速度 |
| 深度偏好 | 浅尝辄止 vs 深挖 | 追问轮次 |
| 沟通偏好 | 简洁/详细/代码优先/图示优先 | 用户反馈 |
| 理解模式 | 常见误解类型 | 错误模式积累 |
| 学习目标 | 主动声明或推断的阶段目标 | 入口+推断 |
| 活跃时段 | 使用习惯 | 时间统计 |

**更新策略**：混合模式——Agent 自动评估为主 + 用户主动标记修正

### 2.4 外部内容导入

- **第一期**：纯文本 / Markdown 笔记
- **第二期**：PDF 文档
- **预留扩展**：代码文件、网页链接、图片 OCR
- 每条知识可追溯来源

### 2.5 复习与测验 *(Phase 2 可插拔)*

- 基于遗忘曲线的主动复习提醒
- Agent 自动生成测验题检验掌握程度
- 作为产品差异化亮点

### 2.6 社交

- 用户之间可分享知识图谱
- 不做实时多人协作

---

## 三、多 Agent 架构

### 3.1 Agent 清单

**Phase 1 — 核心 Agent（本次开发）：**

| Agent | 职责 | 触发时机 |
|-------|------|----------|
| **路由 Agent** | 入口，意图判断，分派到专家角色和其他 Agent | 每次用户输入 |
| **对话 Agent** | 主对话，根据画像调整讲解风格和深度 | 全程 |
| **知识提取 Agent** | 从对话/外部内容中抽取概念、关系，更新知识图谱 | 每 5-10 轮对话 / 对话结束 / 内容导入 |
| **画像 Agent** | 分析用户理解程度、学习风格，更新画像 | 每 5-10 轮对话 / 对话结束 |
| **冲突检测 Agent** | 新知识与图谱已有知识矛盾时触发 | 知识提取后 |
| **摘要 Agent** | 生成对话结构化摘要，回写知识图谱 | 对话结束 |
| **元评估 Agent** | 审查其他 Agent 输出质量，防止幻觉污染 | 其他 Agent输出后 |

**Phase 2 — 可插拔扩展 Agent（预留接口，不纳入第一期开发）：**

| Agent | 职责 | 触发时机 |
|-------|------|----------|
| 出题 Agent | 基于图谱+画像+遗忘曲线生成测验 | 复习触发 |
| 学习路径 Agent | 根据目标+知识状态规划学习顺序 | 用户设置目标 / 推断目标后 |
| 情绪感知 Agent | 检测困惑/挫败/无聊，调整响应策略 | 全程 |
| 目标追踪 Agent | 追踪学习目标完成进度 | 对话分析后 |
| 代码执行 Agent | 编程类对话时执行代码并返回结果 | 用户请求时 |

### 3.2 协作流程

#### 对话阶段（实时）

```
用户输入
  → 路由 Agent
      ├─ 意图分类：[对话 | 知识查询 | 图谱操作 | 设置]
      ├─ 专家匹配：根据上下文/用户选择确定专家角色
      └─ 注入上下文：用户画像摘要 + 相关知识图谱节点
          ↓
      对话 Agent（流式响应）
          ├─ 使用强模型（Claude/GPT-4）
          ├─ System Prompt = 专家人设 + 画像注入 + 图谱相关知识
          └─ 流式输出到前端
```

#### 间歇触发阶段（每 5-10 轮 / 对话结束）

```
┌──────────────────────────────────────────────────┐
│              间歇处理流水线                         │
│                                                   │
│  输入：最近 N 轮对话 + 本轮对话全文                  │
│                                                   │
│  Step 1: 知识提取 Agent（并行）                     │
│    ├─ 提取候选概念（LLM）                           │
│    ├─ Embedding 相似度匹配                          │
│    ├─ 新建/合并节点                                 │
│    └─ 提取节点间关系 → 创建边                        │
│                                                   │
│  Step 2: 画像 Agent（并行）                         │
│    ├─ 分析用户提问模式                              │
│    ├─ 评估理解程度                                  │
│    └─ 更新画像 JSONB                                │
│                                                   │
│  Step 3: 冲突检测 Agent（依赖 Step 1）              │
│    ├─ 比对新建知识与已有图谱                         │
│    └─ 冲突 → 标记 + 通知用户下次对话澄清             │
│                                                   │
│  Step 4: 元评估 Agent（依赖 Step 1 + Step 2）       │
│    ├─ 审查提取结果的准确性                           │
│    ├─ 审查画像更新的合理性                           │
│    └─ 不通过 → 打回重新处理 / 标记低置信度            │
│                                                   │
│  Step 5: 摘要 Agent（对话结束时触发）               │
│    ├─ 生成结构化摘要                                │
│    └─ 关联提取出的知识节点                           │
│                                                   │
│  输出：更新后的知识图谱 + 用户画像 + 对话摘要          │
└──────────────────────────────────────────────────┘
```

### 3.3 Agent 间通信协议

Agent 之间不直接调用，而是通过 **共享上下文 + 消息总线** 模式通信：

```python
# 每次编排的共享上下文
@dataclass
class AgentContext:
    conversation_id: str
    user_id: str
    recent_messages: list[Message]       # 最近 N 轮对话
    user_profile: dict                   # 当前画像快照
    related_nodes: list[KgNode]          # 相关图谱节点
    intermediate_results: dict           # Agent 间传递的中间结果
    errors: list[AgentError]             # 错误累积
    metadata: dict                       # 扩展字段
```

- **输入契约**：每个 Agent 定义自己需要的 Context 字段
- **输出契约**：每个 Agent 将结果写入 `intermediate_results` 的指定 key
- **错误传播**：错误写入 `errors`，后续 Agent 可选择跳过或降级处理

### 3.4 扩展性设计

- **Agent 基类**：所有 Agent 继承 `BaseAgent`，实现 `execute(context) -> AgentResult`
- **注册机制**：`AgentRegistry.register("agent_name", AgentClass)` 即可热注册
- **编排配置化**：Agent 流水线通过配置文件/数据驱动，不是硬编码
- **生命周期**：支持启用/停用/版本管理

---

## 四、核心交互流程

```
打开 App
  → 选择/继续对话窗口
  → 选择专家角色（可选）
  → 开始对话
    → 后台多 Agent 自动工作
  → 对话结束
    → 展示：摘要、新提取的知识点、画像变化
  → 回到主界面
    → 知识图谱更新、复习提醒、学习路径推荐
```

---

## 五、技术架构

### 5.1 技术选型

| 层 | 选型 | 说明 |
|---|------|------|
| Agent 编排 | LangGraph + 自研 Agent 抽象层 | 底层用 LangGraph 做图编排，上层自研注册/插件/可观测性 |
| 后端框架 | FastAPI (Python) | 异步支持好，与 LangGraph 生态兼容 |
| 前端框架 | Vite + React + TypeScript | 轻量 SPA，适合对话+图谱交互 |
| 数据库 | PostgreSQL (Supabase) + pgvector | 关系数据 + 向量搜索 |
| Embedding | 本地模型 bge-base-zh（768 维），API 降级 | 本地优先，免费无延迟 |
| 实时通信 | SSE（对话流式输出） | 轻量，单向推送足够 |
| 异步任务 | ARQ (Async Redis Queue) | 专为 FastAPI 设计，轻量有重试 |
| 缓存 | Redis | 与 ARQ 共用，缓存 LLM 响应和 Embedding |
| LLM 集成 | 模型路由抽象层 | 按 Agent 类型分配模型，对话用强模型，提取用便宜模型 |
| 认证 | Supabase Auth + 自定义封装 | 底层认证交 Supabase，上层自定义画像初始化/权限 |
| 文件存储 | Supabase Storage | 与 Supabase 生态统一，内置权限和 CDN |
| 部署 | Docker（多阶段构建） | 保持现有方案 |

### 5.2 系统架构图

```
┌──────────────────────────────────────────────────────────┐
│                   Frontend (Vite + React)                 │
│                                                          │
│  ┌──────────────┐  ┌──────────────┐  ┌───────────────┐  │
│  │   对话界面    │  │   知识图谱    │  │ 画像/复习/设置 │  │
│  │  (SSE 流式)   │  │ (Canvas 渲染) │  │               │  │
│  └──────┬───────┘  └──────┬───────┘  └───────┬───────┘  │
│         │                 │                   │          │
│         └─────────────────┼───────────────────┘          │
│                           │ REST + SSE                   │
└───────────────────────────┼──────────────────────────────┘
                            │
┌───────────────────────────┼──────────────────────────────┐
│                    Backend (FastAPI)                      │
│                           │                              │
│  ┌────────────────────────┴────────────────────────┐     │
│  │              API Gateway / 路由层                │     │
│  │     (JWT 验证 → 路由 Agent 意图分类)              │     │
│  └────────────────────────┬────────────────────────┘     │
│                           │                              │
│  ┌────────────────────────┴────────────────────────┐     │
│  │            LangGraph 编排引擎                    │     │
│  │                                                  │     │
│  │  Phase 1 核心：                                   │     │
│  │  ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐    │     │
│  │  │ 对话   │ │ 知识   │ │ 画像   │ │ 冲突   │    │     │
│  │  │ Agent  │ │ 提取   │ │ Agent  │ │ 检测   │    │     │
│  │  └────────┘ └────────┘ └────────┘ └────────┘    │     │
│  │  ┌────────┐ ┌────────┐ ┌────────┐               │     │
│  │  │ 摘要   │ │ 元评估 │ │ (预留) │               │     │
│  │  │ Agent  │ │ Agent  │ │        │               │     │
│  │  └────────┘ └────────┘ └────────┘               │     │
│  │                                                  │     │
│  │  Phase 2 可插拔扩展：                              │     │
│  │  出题Agent | 学习路径 | 情绪感知 | 目标追踪 | ...  │     │
│  └────────────────────────┬────────────────────────┘     │
│                           │                              │
│  ┌────────────────────────┴────────────────────────┐     │
│  │              模型路由抽象层                       │     │
│  │  ┌─────────────┐  ┌─────────────┐               │     │
│  │  │ 强模型路由   │  │ 弱模型路由   │               │     │
│  │  │ (对话Agent)  │  │ (提取/画像)  │               │     │
│  │  └─────────────┘  └─────────────┘               │     │
│  └────────────────────────┬────────────────────────┘     │
│                           │                              │
│  ┌────────────────────────┴────────────────────────┐     │
│  │                 服务层                           │     │
│  │  ┌───────────┐ ┌───────────┐ ┌───────────────┐  │     │
│  │  │ ARQ 任务  │ │  Redis    │ │  Embedding    │  │     │
│  │  │  队列     │ │  缓存     │ │  Service      │  │     │
│  │  └───────────┘ └───────────┘ └───────────────┘  │     │
│  │  ┌───────────┐ ┌───────────┐                    │     │
│  │  │ 文件处理   │ │ 可观测性  │                    │     │
│  │  │ Service   │ │ (日志/追踪)│                    │     │
│  │  └───────────┘ └───────────┘                    │     │
│  └────────────────────────┬────────────────────────┘     │
│                           │                              │
└───────────────────────────┼──────────────────────────────┘
                            │
┌───────────────────────────┼──────────────────────────────┐
│                       数据层                              │
│                                                          │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────┐  │
│  │ PostgreSQL  │  │  pgvector   │  │ Supabase        │  │
│  │ (Supabase)  │  │  (embedding │  │ Storage         │  │
│  │  业务数据    │  │   搜索)     │  │ (文件/PDF)      │  │
│  └─────────────┘  └─────────────┘  └─────────────────┘  │
│                                                          │
│  ┌─────────────┐  ┌─────────────┐                       │
│  │   Redis     │  │ Supabase    │                       │
│  │ (缓存+队列) │  │ Auth (JWT)  │                       │
│  └─────────────┘  └─────────────┘                       │
└──────────────────────────────────────────────────────────┘
```

### 5.3 项目目录结构

```
daydayknow/
├── docs/
│   ├── ARCHITECTURE.md              # 本文档
│   ├── API.md                       # API 接口文档
│   ├── AGENT_DESIGN.md              # Agent 设计详细文档
│   └── EDGE_CASES.md                # 边界情况与解决方案
│
├── frontend/                        # Vite + React + TypeScript
│   ├── public/
│   │   ├── manifest.json            # PWA 配置
│   │   └── sw.js                    # Service Worker
│   ├── src/
│   │   ├── app/
│   │   │   ├── layout.tsx           # 根布局
│   │   │   ├── page.tsx             # 首页（对话入口）
│   │   │   └── globals.css          # 全局样式
│   │   ├── features/
│   │   │   ├── chat/                # 对话功能模块
│   │   │   │   ├── ChatWindow.tsx   # 对话主窗口
│   │   │   │   ├── MessageList.tsx  # 消息列表
│   │   │   │   ├── MessageInput.tsx # 输入框
│   │   │   │   ├── ExpertSelector.tsx # 专家选择器
│   │   │   │   └── hooks/
│   │   │   │       ├── useChat.ts          # 对话状态管理
│   │   │   │       └── useSSE.ts           # SSE 流式连接
│   │   │   ├── knowledge-graph/     # 知识图谱功能模块
│   │   │   │   ├── GraphCanvas.tsx  # Canvas 图谱渲染
│   │   │   │   ├── NodeDetail.tsx   # 节点详情面板
│   │   │   │   ├── GraphControls.tsx # 缩放/筛选控制
│   │   │   │   └── hooks/
│   │   │   │       ├── useGraphData.ts     # 图谱数据获取
│   │   │   │       └── useGraphInteraction.ts # 交互逻辑
│   │   │   ├── profile/             # 用户画像功能模块
│   │   │   │   ├── ProfileDashboard.tsx # 画像总览
│   │   │   │   ├── ProfileDimension.tsx # 单维度展示
│   │   │   │   └── hooks/
│   │   │   │       └── useProfile.ts
│   │   │   └── import/              # 内容导入模块
│   │   │       ├── TextImport.tsx   # 文本导入
│   │   │       ├── FileUpload.tsx   # 文件上传
│   │   │       └── ImportResult.tsx # 导入结果
│   │   ├── components/              # 通用组件
│   │   │   ├── Layout.tsx           # 应用布局（侧边栏+主区域）
│   │   │   ├── Sidebar.tsx          # 侧边栏（对话列表+导航）
│   │   │   ├── Loading.tsx          # 加载状态
│   │   │   └── ErrorBoundary.tsx    # 错误边界
│   │   ├── lib/                     # 工具库
│   │   │   ├── api.ts               # API 客户端封装
│   │   │   ├── auth.ts              # 认证工具（Supabase Auth）
│   │   │   ├── sse.ts               # SSE 客户端
│   │   │   └── utils.ts             # 通用工具函数
│   │   ├── stores/                  # 状态管理
│   │   │   ├── chatStore.ts         # 对话状态
│   │   │   ├── graphStore.ts        # 图谱状态
│   │   │   └── profileStore.ts      # 画像状态
│   │   ├── types/                   # 类型定义
│   │   │   ├── agent.ts             # Agent 相关类型
│   │   │   ├── knowledge.ts         # 知识图谱类型
│   │   │   ├── profile.ts           # 画像类型
│   │   │   └── api.ts               # API 响应类型
│   │   └── main.tsx                 # 入口
│   ├── tests/                       # 前端测试
│   ├── vite.config.ts
│   ├── tailwind.config.ts
│   ├── tsconfig.json
│   └── package.json
│
├── backend/                         # FastAPI 后端
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py                  # FastAPI 入口 + 中间件
│   │   ├── config.py                # 配置管理（pydantic-settings）
│   │   │
│   │   ├── api/                     # API 路由层
│   │   │   ├── __init__.py
│   │   │   ├── deps.py              # 依赖注入（认证、DB 会话）
│   │   │   ├── chat.py              # 对话相关端点
│   │   │   ├── knowledge.py         # 知识图谱 CRUD 端点
│   │   │   ├── profile.py           # 画像查询/更新端点
│   │   │   ├── import_.py           # 内容导入端点
│   │   │   └── admin.py             # 管理端点（Agent 状态、任务监控）
│   │   │
│   │   ├── agents/                  # Agent 系统（核心）
│   │   │   ├── __init__.py
│   │   │   ├── base.py              # BaseAgent 抽象基类
│   │   │   ├── registry.py          # Agent 注册中心
│   │   │   ├── orchestrator.py      # LangGraph 编排器
│   │   │   ├── context.py           # AgentContext 共享上下文
│   │   │   ├── router_agent.py      # 路由 Agent
│   │   │   ├── chat_agent.py        # 对话 Agent
│   │   │   ├── extraction_agent.py  # 知识提取 Agent
│   │   │   ├── profile_agent.py     # 画像 Agent
│   │   │   ├── conflict_agent.py    # 冲突检测 Agent
│   │   │   ├── summary_agent.py     # 摘要 Agent
│   │   │   ├── evaluation_agent.py  # 元评估 Agent
│   │   │   ├── prompts/             # Agent Prompt 模板
│   │   │   │   ├── __init__.py
│   │   │   │   ├── chat.py
│   │   │   │   ├── extraction.py
│   │   │   │   ├── profile.py
│   │   │   │   ├── conflict.py
│   │   │   │   ├── summary.py
│   │   │   │   └── evaluation.py
│   │   │   └── plugins/             # Phase 2 可插拔 Agent（预留）
│   │   │       ├── __init__.py
│   │   │       ├── quiz_agent.py
│   │   │       ├── learning_path_agent.py
│   │   │       └── emotion_agent.py
│   │   │
│   │   ├── services/                # 业务服务层
│   │   │   ├── __init__.py
│   │   │   ├── llm/                 # LLM 服务
│   │   │   │   ├── __init__.py
│   │   │   │   ├── client.py        # LLM 客户端封装
│   │   │   │   ├── router.py        # 模型路由逻辑
│   │   │   │   ├── providers/       # 各供应商适配
│   │   │   │   │   ├── openai.py
│   │   │   │   │   ├── anthropic.py
│   │   │   │   │   ├── deepseek.py
│   │   │   │   │   └── ollama.py
│   │   │   │   └── cache.py         # LLM 响应缓存
│   │   │   ├── embedding/           # Embedding 服务
│   │   │   │   ├── __init__.py
│   │   │   │   ├── local.py         # 本地 bge 模型
│   │   │   │   ├── fallback.py      # API 降级
│   │   │   │   └── cache.py         # Embedding 缓存
│   │   │   ├── knowledge/           # 知识图谱服务
│   │   │   │   ├── __init__.py
│   │   │   │   ├── graph.py         # 图谱 CRUD
│   │   │   │   ├── similarity.py    # 相似度匹配
│   │   │   │   └── relationship.py  # 关系推理
│   │   │   ├── profile/             # 画像服务
│   │   │   │   ├── __init__.py
│   │   │   │   ├── scorer.py        # 画像评分算法
│   │   │   │   └── merger.py        # 画像合并（自动+手动）
│   │   │   ├── task/                # 任务服务
│   │   │   │   ├── __init__.py
│   │   │   │   ├── queue.py         # ARQ 队列封装
│   │   │   │   └── workers.py       # 异步 Worker
│   │   │   ├── file/                # 文件服务
│   │   │   │   ├── __init__.py
│   │   │   │   ├── upload.py        # 文件上传
│   │   │   │   ├── parser.py        # 文件解析（文本/PDF）
│   │   │   │   └── extractor.py     # 内容提取
│   │   │   └── auth/                # 认证服务
│   │   │       ├── __init__.py
│   │   │       ├── supabase_auth.py # Supabase Auth 封装
│   │   │       └── middleware.py    # JWT 中间件
│   │   │
│   │   ├── models/                  # 数据模型（Pydantic）
│   │   │   ├── __init__.py
│   │   │   ├── user.py              # 用户模型
│   │   │   ├── conversation.py      # 对话模型
│   │   │   ├── knowledge.py         # 知识图谱模型
│   │   │   ├── profile.py           # 画像模型
│   │   │   └── agent.py             # Agent 状态模型
│   │   │
│   │   ├── db/                      # 数据库
│   │   │   ├── __init__.py
│   │   │   ├── supabase.py          # Supabase 客户端
│   │   │   ├── queries/             # 查询封装
│   │   │   │   ├── __init__.py
│   │   │   │   ├── conversations.py
│   │   │   │   ├── knowledge.py
│   │   │   │   └── profiles.py
│   │   │   └── migrations/          # SQL 迁移文件
│   │   │       ├── 001_initial.sql
│   │   │       ├── 002_knowledge_graph.sql
│   │   │       └── 003_profiles.sql
│   │   │
│   │   └── utils/                   # 工具
│   │       ├── __init__.py
│   │       ├── logger.py            # 结构化日志
│   │       ├── metrics.py           # 指标收集
│   │       └── retry.py             # 重试装饰器
│   │
│   ├── tests/                       # 后端测试
│   │   ├── conftest.py              # 测试 fixtures
│   │   ├── test_agents/             # Agent 单元测试
│   │   ├── test_api/                # API 集成测试
│   │   ├── test_services/           # 服务层测试
│   │   └── test_integration/        # 端到端测试
│   │
│   ├── pyproject.toml
│   └── requirements.txt
│
├── docker/
│   ├── Dockerfile.frontend          # 前端多阶段构建
│   ├── Dockerfile.backend           # 后端多阶段构建
│   └── nginx.conf                   # Nginx 配置
│
├── docker-compose.yml               # 开发环境
├── docker-compose.prod.yml          # 生产环境
├── deploy-ecs.sh                    # ECS 部署脚本
│
├── scripts/
│   ├── setup.sh                     # 项目初始化脚本
│   ├── seed.py                      # 测试数据填充
│   └── migrate.py                   # 数据库迁移
│
├── .env.example                     # 环境变量模板
├── CLAUDE.md
└── README.md
```

### 5.4 数据库设计

#### 用户画像表 `user_profiles`

存储用户的 12 维度画像数据。使用 JSONB 存储灵活的画像结构，支持动态维度扩展而无需修改表结构。

```sql
CREATE TABLE user_profiles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,

    -- 12 维度画像数据，结构示例：
    -- {
    --   "knowledge_level": {"机器学习": 75, "深度学习": 40},
    --   "knowledge_gaps": [{"concept": "反向传播", "context": "对话中问了3次", "first_seen": "2024-01-15"}],
    --   "prerequisite_gaps": [{"domain": "深度学习", "missing": "线性代数", "confidence": 0.8}],
    --   "interests": [{"topic": "RAG", "weight": 0.9, "trend": "rising"}],
    --   "learning_style": "analogy",       -- analogy | formula | case_study | visual
    --   "cognitive_pattern": "top_down",   -- top_down | bottom_up
    --   "learning_pace": "steady",         -- fast | steady | needs_repetition
    --   "depth_preference": "deep",        -- shallow | moderate | deep
    --   "communication_pref": "detailed",  -- concise | detailed | code_first | visual
    --   "misconception_patterns": [{"type": "概念混淆", "examples": ["混淆LSTM和GRU"]}],
    --   "learning_goals": [{"goal": "掌握RAG", "source": "inferred", "progress": 0.3}],
    --   "active_hours": {"peak": "20:00-23:00", "avg_session_min": 45}
    -- }
    profile_data JSONB NOT NULL DEFAULT '{}',

    -- 画像版本号，每次更新 +1，用于乐观锁避免并发写冲突
    version INT NOT NULL DEFAULT 1,

    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),

    -- 每个用户只有一个画像记录
    UNIQUE(user_id)
);

-- 画像按用户快速查询
CREATE INDEX idx_profiles_user ON user_profiles(user_id);
-- JSONB 内字段查询（如按学习风格筛选）
CREATE INDEX idx_profiles_style ON user_profiles
    USING GIN (profile_data jsonb_path_ops);
```

#### 知识图谱节点表 `kg_nodes`

存储知识图谱的概念节点。每个节点包含向量表示用于语义相似度搜索，以及来源追踪用于知识溯源。

```sql
CREATE TABLE kg_nodes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,

    -- 概念名称，如 "注意力机制"、"反向传播"
    name TEXT NOT NULL,

    -- 所属领域，如 "机器学习"、"经济学"，用于图谱分层展示
    domain TEXT,

    -- 概念的简短描述（用户可读）
    description TEXT,

    -- 语义向量，bge-base-zh 输出 768 维
    -- 用于节点去重（相似度匹配）和语义搜索
    embedding VECTOR(768),

    -- 置信度 0~1，表示这个节点的可信程度
    -- 对话提取：0.7~0.9；手动导入：0.95；元评估打回：降低
    confidence FLOAT NOT NULL DEFAULT 0.8,

    -- 知识来源类型
    -- 'conversation': 从对话中提取
    -- 'import_text': 从文本导入
    -- 'import_pdf': 从 PDF 导入
    -- 'manual': 用户手动创建
    source_type TEXT NOT NULL DEFAULT 'conversation',

    -- 来源引用：对话 ID、文件路径、URL 等，用于追溯
    source_ref TEXT,

    -- 此节点在知识图谱中的层级（用于分层展示）
    -- 0 = 领域级（如"机器学习"）
    -- 1 = 概念级（如"注意力机制"）
    -- 2 = 细节级（如"多头注意力"）
    graph_level INT NOT NULL DEFAULT 1,

    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),

    -- 同一用户下概念名不能重复
    UNIQUE(user_id, name)
);

-- 向量相似度搜索索引（ivfflat 适合 < 10万 数据量）
CREATE INDEX idx_kg_nodes_embedding ON kg_nodes
    USING ivfflat (embedding vector_cosine_ops)
    WITH (lists = 100);

-- 常规查询索引
CREATE INDEX idx_kg_nodes_user ON kg_nodes(user_id);
CREATE INDEX idx_kg_nodes_domain ON kg_nodes(user_id, domain);
CREATE INDEX idx_kg_nodes_name ON kg_nodes(name);
```

#### 知识图谱边表 `kg_edges`

存储节点间的关系。边带强度评分用于展示层过滤，带来源用于追溯。

```sql
CREATE TABLE kg_edges (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,

    -- 起点/终点节点
    from_node_id UUID NOT NULL REFERENCES kg_nodes(id) ON DELETE CASCADE,
    to_node_id UUID NOT NULL REFERENCES kg_nodes(id) ON DELETE CASCADE,

    -- 关系类型，18 种预设关系之一
    -- is-a | instance-of | part-of | composed-of
    -- causes | enables | prevents | precedes | evolves-to
    -- similar-to | opposite-of | competes-with
    -- requires | specializes | applies-to | solves
    -- analogous-to | derived-from | improves-on | trade-off
    relation_type TEXT NOT NULL,

    -- 关系强度 0~1，用于展示层过滤
    -- 1.0 = 强关系（如 is-a）；0.3 = 弱推测关系
    strength FLOAT NOT NULL DEFAULT 1.0,

    -- 关系描述，可选，如 "CNN 是一种专门处理图像的神经网络"
    description TEXT,

    -- 关系来源：哪个对话/导入发现了这条边
    source_ref TEXT,

    -- 是否经过元评估 Agent 审查
    evaluated BOOLEAN NOT NULL DEFAULT false,

    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),

    -- 防止同一对节点创建重复的同类型边
    UNIQUE(user_id, from_node_id, to_node_id, relation_type),
    -- 防止自环
    CHECK (from_node_id != to_node_id)
);

-- 按用户查询
CREATE INDEX idx_kg_edges_user ON kg_edges(user_id);
-- 按起点/终点查询（图遍历核心索引）
CREATE INDEX idx_kg_edges_from ON kg_edges(from_node_id);
CREATE INDEX idx_kg_edges_to ON kg_edges(to_node_id);
-- 按关系类型筛选
CREATE INDEX idx_kg_edges_type ON kg_edges(relation_type);
```

#### 对话会话表 `conversations`

存储用户的每个对话窗口。关联专家角色，支持多会话并行。

```sql
CREATE TABLE conversations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,

    -- 对话使用的专家角色标识
    -- 'generalist' | 'python_expert' | 'finance_analyst' | ...
    -- NULL = 默认通才
    expert_role TEXT,

    -- 对话标题，可由摘要 Agent 自动生成
    title TEXT,

    -- 对话状态
    -- 'active' | 'archived' | 'deleted'
    status TEXT NOT NULL DEFAULT 'active',

    -- 消息轮次计数器（避免每次都 COUNT）
    message_count INT NOT NULL DEFAULT 0,

    -- 最后一次间歇提取的轮次号
    -- 用于判断是否到达 5-10 轮触发阈值
    last_extraction_at_round INT NOT NULL DEFAULT 0,

    -- 该对话关联的知识节点（摘要 Agent 填充）
    related_node_ids UUID[] DEFAULT '{}',

    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_convos_user ON conversations(user_id, status);
CREATE INDEX idx_convos_updated ON conversations(user_id, updated_at DESC);
```

#### 对话消息表 `messages`

存储对话中的每条消息。content 不做截断，超长对话通过上下文压缩策略处理（见边界情况章节）。

```sql
CREATE TABLE messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id UUID NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,

    -- 消息角色
    -- 'user': 用户输入
    -- 'assistant': AI 回复
    -- 'system': 系统消息（专家人设注入、画像上下文等）
    role TEXT NOT NULL CHECK (role IN ('user', 'assistant', 'system')),

    -- 消息内容，不做长度限制（由应用层控制）
    content TEXT NOT NULL,

    -- 消息序号，用于排序和判断是否触发间歇提取
    sequence_number INT NOT NULL,

    -- 元数据，记录该消息的 Agent 处理信息
    -- {
    --   "tokens_used": 1500,
    --   "model": "claude-sonnet-4-6",
    --   "agent_chain": ["router", "chat"],
    --   "retrieved_nodes": ["uuid1", "uuid2"],
    --   "processing_time_ms": 2300
    -- }
    metadata JSONB DEFAULT '{}',

    -- 如果是摘要后的压缩消息，标记为 true
    is_compressed BOOLEAN NOT NULL DEFAULT false,

    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_messages_conv ON messages(conversation_id, sequence_number);
CREATE INDEX idx_messages_created ON messages(conversation_id, created_at);
```

#### 对话摘要表 `conversation_summaries`

存储间歇提取和对话结束时生成的摘要。用于上下文压缩和知识图谱关联。

```sql
CREATE TABLE conversation_summaries (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id UUID NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,

    -- 摘要类型
    -- 'incremental': 间歇提取（每 5-10 轮）
    -- 'final': 对话结束的完整摘要
    summary_type TEXT NOT NULL CHECK (summary_type IN ('incremental', 'final')),

    -- 摘要文本
    summary TEXT NOT NULL,

    -- 该摘要覆盖的消息范围
    -- 如 [1, 15] 表示覆盖第 1~15 轮
    covers_range_start INT,
    covers_range_end INT,

    -- 本次提取出的知识节点 ID 列表
    extracted_node_ids UUID[] DEFAULT '{}',

    -- 本次创建的边 ID 列表
    extracted_edge_ids UUID[] DEFAULT '{}',

    -- 画像变更摘要
    -- {"knowledge_level_changes": [{"domain": "ML", "old": 60, "new": 70}]}
    profile_changes JSONB DEFAULT '{}',

    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_summaries_conv ON conversation_summaries(conversation_id);
CREATE INDEX idx_summaries_user ON conversation_summaries(user_id);
```

#### 学习目标表 `learning_goals`

存储用户的学习目标，可由用户手动设置或 Agent 自动推断。

```sql
CREATE TABLE learning_goals (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,

    -- 目标描述，如 "掌握 RAG 系统设计"
    goal_text TEXT NOT NULL,

    -- 目标来源
    -- 'manual': 用户主动设置
    -- 'inferred': Agent 从对话模式推断
    source TEXT NOT NULL CHECK (source IN ('manual', 'inferred')),

    -- 目标状态
    -- 'active': 进行中
    -- 'completed': 已完成
    -- 'paused': 暂停
    -- 'abandoned': 放弃
    status TEXT NOT NULL DEFAULT 'active',

    -- 推断此目标的依据（仅 source='inferred' 时有效）
    -- 如 ["最近 5 次对话都涉及 RAG", "知识图谱中 RAG 相关节点增长最快"]
    inference_evidence TEXT[],

    -- 相关的知识节点 ID
    related_node_ids UUID[] DEFAULT '{}',

    -- 进度 0~1（目标追踪 Agent 更新）
    progress FLOAT DEFAULT 0.0,

    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_goals_user ON learning_goals(user_id, status);
```

#### 复习记录表 `review_records`

存储每个知识节点的复习状态，基于遗忘曲线计算下次复习时间。

```sql
CREATE TABLE review_records (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    node_id UUID NOT NULL REFERENCES kg_nodes(id) ON DELETE CASCADE,

    -- 掌握程度 0~1，每次复习后更新
    mastery_level FLOAT NOT NULL DEFAULT 0.0,

    -- 遗忘曲线参数（SM-2 算法）
    -- 间隔天数：下次复习距今天数
    interval_days FLOAT NOT NULL DEFAULT 1.0,
    -- 难度因子：越难的因子越低，复习越频繁
    ease_factor FLOAT NOT NULL DEFAULT 2.5,

    -- 上次复习时间
    last_reviewed_at TIMESTAMPTZ,

    -- 下次应复习时间（由遗忘曲线算法计算）
    next_review_at TIMESTAMPTZ,

    -- 累计复习次数
    review_count INT NOT NULL DEFAULT 0,

    -- 最近一次复习的用户评分（1-5，用户标记"懂了/没懂"）
    last_rating INT CHECK (last_rating BETWEEN 1 AND 5),

    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),

    -- 每个节点每个用户只有一条复习记录
    UNIQUE(user_id, node_id)
);

-- 查找待复习的节点
CREATE INDEX idx_review_due ON review_records(user_id, next_review_at)
    WHERE next_review_at IS NOT NULL;
CREATE INDEX idx_review_node ON review_records(node_id);
```

#### 索引总结

| 表 | 索引 | 用途 |
|---|------|------|
| `user_profiles` | `user_id` | 按用户查画像 |
| `user_profiles` | `GIN(profile_data)` | JSONB 内字段查询 |
| `kg_nodes` | `ivfflat(embedding)` | 向量相似度搜索 |
| `kg_nodes` | `user_id, domain` | 按领域筛选节点 |
| `kg_edges` | `from_node_id` / `to_node_id` | 图遍历核心 |
| `kg_edges` | `relation_type` | 按关系类型筛选 |
| `conversations` | `user_id, status, updated_at` | 对话列表排序 |
| `messages` | `conversation_id, sequence_number` | 消息时序查询 |
| `review_records` | `user_id, next_review_at` | 待复习节点查询 |

---

## 六、边界情况与工程解决方案

> 这是 AI Agent 应用的工程核心。面试重点考察项。

### 6.1 对话上下文超长问题

**问题**：LLM 上下文窗口有限（Claude ~200K tokens，GPT-4 ~128K）。用户长时间对话会超出限制。

**解决方案：滑动窗口 + 分层摘要**

```
原始对话（100 轮）
  ↓
┌─────────────────────────────────────────────────────────────┐
│ 分层压缩策略                                                  │
│                                                              │
│ Layer 1: 最近 10 轮 — 原始消息，完整保留                        │
│                                                              │
│ Layer 2: 第 11~30 轮 — 压缩为详细摘要（保留关键问答对）          │
│                                                              │
│ Layer 3: 第 31~60 轮 — 压缩为中等摘要（只保留核心概念和结论）     │
│                                                              │
│ Layer 4: 第 61+ 轮 — 压缩为简短摘要（只保留主题和关键概念）       │
│                                                              │
│ Layer 0: 用户画像 + 知识图谱相关节点 — 始终注入                  │
└─────────────────────────────────────────────────────────────┘
  ↓
构建 System Prompt：Layer 0 + Layer 4 + Layer 3 + Layer 2 + Layer 1
  ↓
如果总 token 仍超限 → 继续压缩 Layer 2 → Layer 3 → 逐层降级
```

**实现细节**：
- 每 10 轮触发一次摘要 Agent，对"轮次 1~当前-10"生成压缩摘要
- 摘要存入 `conversation_summaries` 表，不再需要原始消息
- 构建 LLM 输入时，从摘要表读取历史 + 最近消息表读取原始消息
- Token 计数器实时监控，动态调整压缩粒度

**兜底策略**：如果即使压缩后仍超限，提示用户"当前对话较长，建议开启新对话窗口继续讨论"。

### 6.2 用户前后矛盾

**问题**：用户在对话中先说"A 概念是 B 的子集"，后来说"A 和 B 是并列关系"。

**解决方案：知识版本化 + 冲突标记**

```python
# 知识节点增加版本追踪
kg_nodes:
    current_version: 2
    # 历史版本存在 kg_node_versions 表

kg_node_versions:
    node_id: uuid
    version: 1
    description: "A 是 B 的子集"
    source_ref: "conversation_1, round_5"
    superseded_by: uuid (新版本节点 ID)
    superseded_reason: "用户后续更正"
```

**处理流程**：
1. 冲突检测 Agent 在知识提取后触发
2. 发现新建知识与已有知识矛盾
3. 不直接覆盖，而是：
   - 创建新版本节点
   - 在旧版本标记 `superseded_by`
   - 在边表中标记旧边为 `strength=0`（软删除）
   - 记录冲突原因
4. 如果置信度足够高（用户明确更正），自动切换
5. 如果不确定，在下次对话中注入："我注意到你之前提到 X，但刚才说的是 Y，你指的是哪种情况？"

### 6.3 Agent 间协作编排

**问题**：多个 Agent 需要按依赖关系有序执行，且有并行/串行、错误处理等复杂情况。

**解决方案：基于 LangGraph 的 DAG 编排**

```python
# LangGraph 定义编排图
from langgraph.graph import StateGraph, END

class OrchestratorState(TypedDict):
    context: AgentContext
    extraction_result: Optional[ExtractionResult]
    profile_result: Optional[ProfileResult]
    conflict_result: Optional[ConflictResult]
    evaluation_result: Optional[EvaluationResult]
    errors: list[AgentError]

# 构建 DAG
graph = StateGraph(OrchestratorState)

# 对话阶段：路由 → 对话（每次用户输入走这条线）
graph.add_node("route", router_agent.execute)
graph.add_node("chat", chat_agent.execute)
graph.add_edge("route", "chat")
graph.add_edge("chat", END)

# 间歇提取阶段：并行提取+画像 → 串行冲突检测 → 元评估
graph.add_node("extract", extraction_agent.execute)
graph.add_node("profile_update", profile_agent.execute)
graph.add_node("conflict_check", conflict_agent.execute)
graph.add_node("evaluate", evaluation_agent.execute)

# 并行：提取和画像可以同时进行
graph.add_edge("chat", "extract")       # 条件触发：满足 5-10 轮阈值
graph.add_edge("chat", "profile_update") # 条件触发

# 串行：提取完成后才能冲突检测
graph.add_edge("extract", "conflict_check")

# 汇聚：两个都完成后才能评估
graph.add_edge("conflict_check", "evaluate")
graph.add_edge("profile_update", "evaluate")

# 条件边：评估不通过 → 重试或标记低置信度
graph.add_conditional_edges(
    "evaluate",
    should_retry,
    {"retry": "extract", "accept": END, "fail": END}
)
```

**关键设计**：
- **并行执行**：知识提取和画像更新无依赖，可以并行
- **串行依赖**：冲突检测必须在知识提取之后
- **汇聚节点**：元评估需要等所有前置 Agent 完成
- **条件分支**：评估不通过可以重试或降级
- **错误隔离**：单个 Agent 失败不阻塞整个流水线，错误写入 context.errors

### 6.4 LLM 幻觉污染知识图谱

**问题**：LLM 可能生成不准确的知识，直接写入图谱会污染用户的知识体系。

**解决方案：三层防线**

```
防线 1: Prompt 约束
  → 知识提取 Prompt 要求"只提取对话中明确讨论的概念，不要推测"
  → 要求输出置信度评分

防线 2: 元评估 Agent
  → 审查提取结果的合理性
  → 检查概念是否在对话中确实出现过（可以对原文做 grep 验证）
  → 检查关系类型是否合理（如 A is-a B，但 A 和 B 在不同领域 → 标记可疑）
  → 不通过 → 打回重试或标记低置信度

防线 3: 用户确认
  → 新提取的知识在 UI 上标记为"待确认"
  → 用户可以一键确认/删除/修正
  → 确认后置信度提升，未确认的保持低置信度
```

### 6.5 LLM API 故障与降级

**问题**：LLM API 不稳定，可能超时、限流、返回错误。

**解决方案：多层降级策略**

```
第一级：重试
  → 指数退避重试（1s → 2s → 4s），最多 3 次

第二级：同供应商换模型
  → Claude Sonnet 失败 → 降级到 Claude Haiku

第三级：切换供应商
  → OpenAI 失败 → 切换到 DeepSeek
  → 模型路由层维护供应商优先级列表

第四级：本地降级
  → 对话 Agent：返回预设的"服务暂不可用，请稍后重试"
  → 知识提取/画像：跳过本轮，标记为 pending，下次重试

监控：
  → 每个供应商的成功率/延迟写入 Redis
  → 模型路由根据实时状态动态调整优先级
```

### 6.6 成本控制

**问题**：LLM 调用按 token 计费，多 Agent 架构可能成本失控。

**解决方案：Token 预算管理**

```python
class TokenBudget:
    # 每次对话的 token 预算上限
    per_conversation_limit: int = 500_000  # tokens
    # 每日每用户上限
    per_user_daily_limit: int = 2_000_000  # tokens
    # 各 Agent 的 token 分配
    agent_budgets: dict = {
        "chat": 0.60,        # 60% 给对话
        "extraction": 0.15,  # 15% 给知识提取
        "profile": 0.10,     # 10% 给画像
        "evaluation": 0.10,  # 10% 给元评估
        "reserve": 0.05,     # 5% 预留
    }
```

- 对话 Agent 用强模型（贵），提取/画像/评估用弱模型（便宜）
- Token 实时计数，超预算时降级（换便宜模型或跳过非关键 Agent）
- 缓存命中率监控：相同问题不重复调用 LLM

### 6.7 并发与一致性

**问题**：用户快速连续发送消息，或多个 Agent 并行修改知识图谱。

**解决方案**：
- **对话消息**：消息有 `sequence_number`，保证时序正确
- **知识图谱写入**：使用数据库事务 + 乐观锁（`version` 字段）
- **画像更新**：每个 Agent 更新画像的不同维度，通过 JSONB merge 而非整体覆盖
- **任务幂等性**：每个异步任务有唯一 ID，重复触发不会重复执行

### 6.8 Prompt 注入攻击

**问题**：用户在对话中嵌入恶意指令，试图操控 Agent 行为或污染知识图谱。

**解决方案**：
- 用户输入和 Agent Prompt 严格分层（system / user / assistant 角色隔离）
- 知识提取 Agent 的输入做清洗：过滤掉包含系统指令模式的文本
- 元评估 Agent 检测异常提取结果（如突然出现"删除所有数据"这类非知识概念）
- 写入图谱前做 schema 校验（名称、关系类型必须在白名单内）

### 6.9 状态恢复与容灾

**问题**：对话过程中后端崩溃，正在进行的 Agent 编排中断。

**解决方案**：
- LangGraph 支持 checkpoint——每一步状态变化持久化到 Redis
- 后端重启后从最近 checkpoint 恢复，不需要重新执行已完成的 Agent
- 对话消息实时写入数据库（不是等对话结束才批量写），保证消息不丢失
- 异步任务（ARQ）有持久化队列，Redis 重启后任务不丢失

### 6.10 Embedding 一致性

**问题**：本地 Embedding 模型更新（版本升级）后，已有节点的向量与新计算的向量不在同一空间。

**解决方案**：
- `kg_nodes` 表记录 `embedding_model_version` 字段
- 模型版本升级时，触发全量重建任务（后台异步执行）
- 重建期间新旧向量共存，查询时按版本过滤
- 提供"重建进度"管理端点

### 6.11 可观测性

**问题**：多 Agent 流水线黑盒化，出了问题难以定位。

**解决方案**：
- **结构化日志**：每个 Agent 执行时输出 input_hash、output_hash、duration_ms、token_usage
- **调用链追踪**：每次编排生成 trace_id，串联所有 Agent 调用
- **Agent 执行面板**：管理端点展示最近的 Agent 调用链、耗时、错误
- **指标埋点**：LLM 调用成功率、缓存命中率、Agent 平均耗时、token 消耗分布

---

## 七、测试策略

### TDD 分层

| 层 | 策略 |
|---|------|
| **严格 TDD** | Agent 注册/调度、知识图谱 CRUD、画像算法、API 契约、模型路由 |
| **结构断言** | LLM 输出测试——断言返回结构正确，不断言具体内容 |
| **手动验证** | 前端可视化、LLM 幻觉检测 |

### 测试框架
- 后端：pytest + pytest-asyncio
- 前端：Vitest + React Testing Library

---

## 八、技术演进路径

### Phase 1（当前）
- PostgreSQL + pgvector 存储知识图谱
- 关系表实现节点/边查询
- 本地 Embedding 模型
- 核心 7 个 Agent

### Phase 2（图遍历需求增强时）
- 引入 Apache AGE（PG 图扩展），支持 Cypher 查询
- 实现多跳路径发现（"A 到 B 的最短学习路径"）
- 新增可插拔 Agent（出题、学习路径、情绪感知）
- 不需要引入新数据库

### Phase 3（规模化时）
- 考虑 Neo4j 作为专用图数据库
- PG 保留业务数据，Neo4j 专注图查询
- 微服务拆分：图查询服务独立

### 前端演进
- Phase 1：Vite + React (PWA)
- Phase 2：同一 API 后端，新增 React Native 移动端
- Phase 3：Electron/Tauri 桌面端
- 后端完全不动，只开发新前端

---

## 九、部署架构

### 9.1 开发环境

```yaml
# docker-compose.yml (dev profile)
version: "3.9"

services:
  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile.dev
    ports:
      - "5173:5173"
    volumes:
      - ./frontend/src:/app/src          # 热更新
    environment:
      - VITE_API_URL=http://localhost:8000
      - VITE_SUPABASE_URL=${SUPABASE_URL}
      - VITE_SUPABASE_ANON_KEY=${SUPABASE_ANON_KEY}

  backend:
    build:
      context: ./backend
      dockerfile: Dockerfile.dev
    ports:
      - "8000:8000"
    volumes:
      - ./backend/app:/app/app           # 热更新
    environment:
      - DATABASE_URL=${DATABASE_URL}
      - REDIS_URL=redis://redis:6379
      - SUPABASE_URL=${SUPABASE_URL}
      - SUPABASE_SERVICE_KEY=${SUPABASE_SERVICE_KEY}
      - LLM_API_KEY=${LLM_API_KEY}
      - EMBEDDING_MODEL_PATH=/models/bge-base-zh
      - MOCK_MODE=false
    depends_on:
      - redis
      - postgres

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    command: redis-server --appendonly yes    # 持久化，防止任务丢失

  postgres:
    image: supabase/postgres:15.1.0          # 含 pgvector 扩展
    ports:
      - "5432:5432"
    environment:
      - POSTGRES_PASSWORD=${POSTGRES_PASSWORD}
      - POSTGRES_DB=daydayknow
    volumes:
      - pg_data:/var/lib/postgresql/data
      - ./backend/app/db/migrations:/docker-entrypoint-initdb.d  # 自动执行迁移

volumes:
  redis_data:
  pg_data:
```

### 9.2 生产环境

```yaml
# docker-compose.prod.yml
version: "3.9"

services:
  frontend:
    build:
      context: ./frontend
      dockerfile: ../docker/Dockerfile.frontend
    # 前端静态文件由 Nginx 提供，此容器只做构建
    volumes:
      - frontend_build:/app/dist

  backend:
    build:
      context: ./backend
      dockerfile: ../docker/Dockerfile.backend
    expose:
      - "8000"
    environment:
      - DATABASE_URL=${DATABASE_URL}
      - REDIS_URL=redis://redis:6379
      - SUPABASE_URL=${SUPABASE_URL}
      - SUPABASE_SERVICE_KEY=${SUPABASE_SERVICE_KEY}
      - LLM_API_KEY=${LLM_API_KEY}
      - EMBEDDING_MODEL_PATH=/models/bge-base-zh
      - MOCK_MODE=false
      - LOG_LEVEL=info
    deploy:
      replicas: 2                              # 多实例部署
      resources:
        limits:
          memory: 2G                           # 包含 Embedding 模型内存
    depends_on:
      - redis
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  redis:
    image: redis:7-alpine
    command: redis-server --appendonly yes --maxmemory 512mb --maxmemory-policy allkeys-lru
    volumes:
      - redis_data:/data
    deploy:
      resources:
        limits:
          memory: 512M

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./docker/nginx.conf:/etc/nginx/nginx.conf:ro
      - frontend_build:/usr/share/nginx/html:ro
      - /etc/letsencrypt:/etc/letsencrypt:ro     # SSL 证书
    depends_on:
      - frontend
      - backend

  # PostgreSQL: 使用 Supabase 云服务，不自建

  # 定时任务：每日批量处理 pending 状态的知识提取
  worker:
    build:
      context: ./backend
      dockerfile: ../docker/Dockerfile.backend
    command: arq app.utils.workers.WorkerSettings
    environment:
      - DATABASE_URL=${DATABASE_URL}
      - REDIS_URL=redis://redis:6379
      - LLM_API_KEY=${LLM_API_KEY}
    depends_on:
      - redis

volumes:
  redis_data:
  frontend_build:
```

### 9.3 Nginx 配置要点

```nginx
# docker/nginx.conf 核心配置

upstream backend {
    server backend:8000;
}

server {
    listen 80;
    server_name daydayknow.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl;
    server_name daydayknow.com;

    # SSL 配置
    ssl_certificate /etc/letsencrypt/live/daydayknow.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/daydayknow.com/privkey.pem;

    # 前端静态文件
    location / {
        root /usr/share/nginx/html;
        try_files $uri $uri/ /index.html;     # SPA 路由
        expires 7d;                            # 静态资源缓存
    }

    # API 代理
    location /api/ {
        proxy_pass http://backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;

        # SSE 支持（关键配置）
        proxy_buffering off;
        proxy_cache off;
        proxy_read_timeout 86400s;             # SSE 长连接
        proxy_set_header Connection "";
        chunked_transfer_encoding off;
    }

    # WebSocket（预留，Phase 2 如果需要）
    location /ws/ {
        proxy_pass http://backend;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
```

### 9.4 部署流程

```bash
# deploy-ecs.sh 核心步骤

# 1. 拉取最新代码
git pull origin main

# 2. 构建镜像
docker compose -f docker-compose.prod.yml build

# 3. 执行数据库迁移
docker compose -f docker-compose.prod.yml run --rm backend python -m scripts.migrate

# 4. 滚动更新（零停机）
docker compose -f docker-compose.prod.yml up -d --no-deps backend
docker compose -f docker-compose.prod.yml up -d --no-deps frontend

# 5. 健康检查
curl -f https://daydayknow.com/api/health || exit 1

# 6. 清理旧镜像
docker image prune -f
```

### 9.5 环境变量清单

| 变量 | 说明 | 开发/生产 |
|------|------|----------|
| `DATABASE_URL` | PostgreSQL 连接串 | 两者 |
| `REDIS_URL` | Redis 连接串 | 两者 |
| `SUPABASE_URL` | Supabase 项目 URL | 两者 |
| `SUPABASE_ANON_KEY` | Supabase 匿名 Key（前端用） | 两者 |
| `SUPABASE_SERVICE_KEY` | Supabase 服务端 Key | 两者 |
| `LLM_API_KEY` | 默认 LLM 供应商 Key | 两者 |
| `LLM_PROVIDER` | 默认 LLM 供应商 | 两者 |
| `EMBEDDING_MODEL_PATH` | 本地 Embedding 模型路径 | 两者 |
| `MOCK_MODE` | 是否启用 Mock 模式 | 仅开发 |
| `LOG_LEVEL` | 日志级别 | 生产默认 info |
| `CORS_ORIGINS` | 允许的跨域来源 | 两者 |
