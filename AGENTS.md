# AGENTS.md

本文件供进入仓库的 Codex、Claude Code 或其他编码 Agent 快速接管项目。开始工作前先读本文件，再按任务需要阅读 `README.md`、`docs/ARCHITECTURE.md` 和相关源码。

## 1. 先确认你在正确的仓库

不要只相信工具提供的当前目录。过去曾出现另一个同名但内容为空的 `llmwiki` 目录。

开始时执行：

```bash
pwd
git rev-parse --show-toplevel
git remote -v
git status --short --branch
```

正确仓库根目录至少包含：

```text
backend/
frontend/
docs/
examples/
docker-compose.yml
README.md
```

远端仓库应为 `letmedrink/llmwiki`。如果目录结构或远端不符，停止写入并重新确认路径。

工作树可能包含用户尚未提交的功能改动。不要 reset、checkout、覆盖或顺手整理不属于当前任务的文件。

## 2. 项目一句话模型

llmwiki 是一个面向可信本机单用户的 Local-first AI Knowledge Engine：把 PDF、PPTX、DOCX、TXT、Markdown、CSV 和 JSON 转换为可直接编辑的 Markdown Wiki，并在此基础上提供知识库对话、人工审阅、Deep Research、任务恢复和知识图谱。

核心闭环：

```text
Document / Web Source
  → Parse and Analyze
  → Persist Immutable Raw Source
  → Generate Typed Wiki Proposals
  → Human Review
  → Transactional Commit
  → Incremental Search Index and Knowledge Graph
  → Retrieval-grounded Chat
```

这不是数据库或向量库项目。Markdown/JSON 是唯一事实来源，内存索引和图谱缓存均可重建。

## 3. 当前架构基线

不要重新引入已清理的 Next.js、Supabase、PostgreSQL、Redis、ARQ、Alembic、LangGraph 或独立 Worker，除非用户明确要求改变架构。

### 前端

- React 19 + TypeScript + Vite。
- `frontend/src/App.tsx`：项目工作区和路由分支；重型页面使用 `lazy()`。
- `frontend/src/lib/api.ts`：全部 HTTP/SSE 客户端。
- `frontend/src/contexts/ProjectContext.tsx`：项目选择。
- `frontend/src/contexts/PreviewContext.tsx`：Wiki 页面预览状态。
- `frontend/src/hooks/useChat.ts`：流式聊天状态。
- `frontend/src/components/`：对话、摄入、Wiki、图谱、审阅、研究、任务和设置 UI。
- 本地开发时浏览器使用 `VITE_API_URL` 直连后端；Vite 本身不代理 API。
- Docker 部署时由 Nginx 提供 SPA fallback，并把 `/api`、`/health` 代理到 FastAPI。

### 后端

- FastAPI + Pydantic + Uvicorn，Python 3.11+。
- `backend/app/main.py`：应用入口、中间件、错误响应、路由和 lifespan。
- `backend/app/dependencies.py`：全局 Store 与项目 Runtime 注入。
- `backend/app/api/`：项目、聊天、Wiki、摄入、审阅、研究和全局设置接口。
- `backend/app/agents/chat_agent.py`：Wiki 召回、上下文组装、流式聊天和引导选项。
- `backend/app/ingest/pipeline.py`：文档摄入编排和 FILE/REVIEW 解析。
- `backend/app/ingest/prompts.py`：两阶段摄入生成规则。
- `backend/app/research/deep_research.py`：搜索、网页抓取、证据绑定和研究生成。
- `backend/app/llm.py`：OpenAI-compatible 与 Anthropic Messages 适配器。
- `backend/app/wiki/context_budget.py`：聊天窗口预算分配。
- `backend/app/storage/file_store.py`：JSON、对话、任务、审阅和缓存。
- `backend/app/storage/wiki_store.py`：Markdown、历史、索引、检索和图谱。
- `backend/app/storage/schema_store.py`：项目级 Schema 默认值、校验和版本。
- `backend/app/storage/source_store.py`：内容寻址 Raw Sources 与版本化解析文本。
- `backend/app/wiki/change_pipeline.py`：问答回写与 Wiki Lint 提案。
- `backend/app/storage/project_store.py`：项目索引、路径解析、Runtime 复用和项目删除。

### 部署

- `docker-compose.yml` 只有 `frontend` 和 `backend` 两个服务。
- 前端是唯一外部入口，默认映射 `3000:80`。
- 后端只在 Compose 内部暴露 `8000`。
- 数据保存在 `llmwiki-data` volume。
- 后端容器使用非 root 用户。

## 4. 数据边界

### 全局数据

```text
data/settings.json
data/projects.json
data/profile/profile.json
```

包括 LLM Providers、搜索配置、用户画像和项目索引。

### 项目数据

```text
data/projects/{project_id}/
├── conversations/
├── reviews.json
├── ingest-cache.json
├── ingest-jobs/
├── research-jobs/
├── change-jobs/
├── schema.json
├── schema.md
├── raw/sources/
├── page-history/
└── wiki/
```

Wiki、对话、摄入、审阅、研究、媒体和页面历史必须严格按项目隔离。

`backend/data/` 是本地运行数据且被 Git 忽略。不要读取、打印、提交或覆盖真实 API Key；排查设置时只输出 Provider ID、协议、模型和 `has_api_key` 等非敏感信息。

## 5. 必须保持的系统语义

### API

- 项目接口统一位于 `/api/projects/{project_id}/...`。
- 全局接口只有 `/api/projects`、`/api/settings`、`/api/profile` 和 `/health` 等明确边界。
- 普通成功响应使用 `{ "success": true, "data": ... }`。
- 普通错误响应使用 `{ "success": false, "error": "...", "code": "..." }`。
- SSE 使用 JSON `data:` 帧；聊天事件包括 `reasoning`、`chunk`、`references`、`options`、`done`、`error`，任务还使用 `progress`。
- `done` 表示聊天响应已经完整持久化，而不只是上游停止输出。

### 聊天

- 新对话先生成候选 ID；只有完整非空回答成功后才创建并写入一整轮消息。
- 指定不存在的 `conversation_id` 必须返回 404。
- 上游错误、空响应、流中断、客户端取消或持久化失败不得留下空对话。
- Wiki 召回受 Context Budget 控制，直接页面可扩展最多 3 个一跳 WikiLink 邻居。
- 历史同时按最近消息数量和字符预算裁剪。

### 摄入

- 缓存 Hash 必须基于未注入图片描述的原始解析文本，并包含 `PIPELINE_VERSION`。
- `force=true` 明确绕过缓存。
- 原始字节必须先写入不可变 Raw Source；相同内容复用 source ID，解析升级新增 extraction 版本。
- 长文档按标题和字符预算覆盖全文分析，再根据事实和实体检索候选旧页面。
- 生成必须注入项目 Schema、稳定 source ID 和候选页实际正文，并返回完整目标页。
- 生成结果默认进入持久化 Staging Job；没有用户 Accept 不得修改正式 Wiki。
- 新提案使用 `create|update`、`baseSha256`、`schemaVersion`、`sourceIds` 和完整内容；旧任务格式继续兼容。
- 接受时只允许提交原任务中存在的 Proposal Path。
- 接受更新前必须校验 `baseSha256`；`index.md` 和 `log.md` 只能由后端维护。
- 媒体必须写入当前项目的 Wiki 路径，不得使用全局 DATA_DIR 定位项目文件。

### 存储可靠性

- JSON read-modify-write 必须在同一个 per-path `RLock` 内完成。
- 单文件写入必须使用同目录临时文件、`flush`、`fsync` 和 `os.replace`。
- 临时写入失败必须保留旧文件并清理临时文件。
- `WikiStore.commit_pages()` 在第一笔写入前快照全部目标；任一页面失败时恢复所有目标。
- 这只是单进程 best-effort filesystem transaction，不得描述成完整 ACID。
- Markdown 替换前应保留页面历史，写入后必须失效对应页面索引和图谱缓存。

### 设置和密钥

- `GET /api/settings` 不得返回实际 API Key，只返回空值和 `has_api_key`。
- PATCH 中空白或缺失 Key 表示保留现有值。
- 清除 Key 必须使用显式 `clear_api_key` 语义。
- 连接测试既支持临时新 Key，也支持按 Provider ID 使用已保存 Key。
- 错误、日志和健康检查不得泄露 Key、完整上游正文或真实数据目录。

### 项目删除

- `DELETE /api/projects/{id}` 只从索引移除，不删除磁盘数据。
- `DELETE /api/projects/{id}/data` 只有项目名确认一致时才能永久删除托管目录。
- 自定义外部路径项目禁止永久删除，只能移除索引。

### Deep Research

- 没有搜索配置、没有搜索结果或没有可用来源时 fail closed。
- URL 必须规范化和去重。
- 抓取前及每次重定向后必须拒绝 loopback、private、link-local、reserved、multicast 地址。
- 结论与来源使用稳定 `[S<n>]` 引用。
- 研究页面同样 review-before-commit。

## 6. 索引、检索和图谱模型

### 文件指纹

`WikiStore` 使用 `relative path + mtime_ns + size` 检测页面变化：

- 内部写入立即失效单页缓存。
- 外部 Markdown 修改在下一次访问时发现。
- 只重新解析变化页面，但当前仍需扫描 Wiki 文件并执行 `stat`。

### 检索

- 英文按 token，中文按 bigram。
- 标题匹配权重 3，正文匹配权重 1。
- `hybrid_search()` 将倒排索引得分与字符 Dice 相似度融合。
- Title/Slug lookup 用于一跳邻居解析，避免每个 WikiLink 再遍历全部页面。

### Context Budget

- 默认最大窗口为 32,768 字符。
- 策略定义：Index 约 5%、Pages 约 50%、History/System 约 30%、Response Reserve 约 15%。
- 当前 Chat 路径实际硬约束页面总量、单页上限、历史字符数和回复预留。

### 图谱

- 节点来自 Wiki 页面和 Frontmatter。
- 边来自正文 `[[WikiLink]]` 与 Frontmatter `related`。
- 边会去重并计算权重，节点会计算 linkCount。
- 图谱包含加权社区、Surprising Connections 和 Knowledge Gaps。
- 图谱按页面 generation 缓存；页面变化后重建。

## 7. 本地开发

要求：Node.js 20+、npm、Python 3.11+。

### 后端

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload --port 8000
```

### 前端

```bash
cd frontend
cp .env.example .env
npm install
npm run dev
```

`frontend/.env` 需要：

```text
VITE_API_URL=http://localhost:8000
```

如果 `8000` 被其他本地项目占用，可以选择其他后端端口，并通过启动环境变量同步修改：

```bash
VITE_API_URL=http://127.0.0.1:8001 npm run dev -- --host 127.0.0.1 --port 5173
```

不要为了本地启动强制要求 Docker；Docker 和本地双进程都是受支持的运行方式。

## 8. 验证命令

按改动范围选择最小充分验证；交付较大功能前运行完整集合。

### 后端

```bash
cd backend
./.venv/bin/python -m pytest -q
```

### 前端

```bash
cd frontend
npm test
npm run typecheck
npm run build
```

### E2E

```bash
cd frontend
npm run test:e2e
```

本机已有 Chrome 时可设置：

```bash
PLAYWRIGHT_CHROME_PATH='/Applications/Google Chrome.app/Contents/MacOS/Google Chrome' npm run test:e2e
```

E2E 使用独立的 `backend/data-e2e`、后端 `8011` 和前端 `5174`，不得连接或清理真实数据目录。

### 部署

```bash
docker compose config
docker compose build
```

### 清理检查

```bash
git diff --check
rg -n 'Next\.js|Supabase|Alembic|PostgreSQL|Redis|ARQ|LangGraph|worker\.py' . \
  -g '!frontend/node_modules/**' -g '!backend/.venv/**' -g '!docs/INTERVIEW_GUIDE.md'
```

文档会讨论被排除的旧技术，因此检查遗留运行引用时不要把说明文档中的文字当成有效代码。

## 9. 性能数据口径

`backend/tests/test_performance.py` 会生成 10,000 个临时 Markdown 页面，验证：

- 指定页面可以被召回。
- 图谱包含 10,000 个节点。
- 第二次图谱请求复用缓存对象。

该测试只做规模正确性回归，不记录耗时。

`docs/INTERVIEW_GUIDE.md` 中的 1.33 秒冷索引、3.32 秒冷图谱、165 ms P50 等数字来自一次本机临时合成 benchmark，并非 CI Benchmark 或生产 SLA。引用这些数字时必须说明：

- 单机、单进程。
- 页面很短，图谱是稀疏合成结构。
- 没有记录统一硬件配置。
- 没有覆盖并发、内存峰值、密集图和真实查询质量。

不要把这些数字扩大解释为生产性能保证。

## 10. 当前已知边界和待优化点

- 可信本机单用户，无认证、授权和多租户隔离，不能直接公开暴露。
- 锁只保证单个 Uvicorn 进程，不支持多 Worker 共享数据目录。
- 每次索引刷新仍需对全部 Markdown 执行目录遍历和 `stat`；约 10,000 页时热路径主要耗时在指纹验证。
- 当前检索没有 Embedding/Vector DB，对抽象同义语义的召回弱于向量检索。
- Chat options 只严格解析 `OPTIONS:` 行；持久化历史会剥离该行，后续模型可能因历史示例缺失而退化到默认选项。修复时应考虑历史重建、宽松解析或独立结构化生成。
- 跨 Markdown、媒体、JSON 的提交属于 best-effort rollback，不具备数据库 WAL 级别的断电原子性。
- Deep Research 的引用绑定提升了可追溯性，但不能自动证明来源本身真实或高质量。

## 11. Git 和协作约束

- 开始前必须查看当前分支和工作树。
- 新功能使用 feature 分支；不要直接在 main 上堆积未验证改动。
- 不要自动 commit、squash、rebase、push 或 force-push，除非用户明确要求。
- 历史重写前必须创建本地备份分支。
- 用户要求 main 历史保持简洁，提交作者只能是用户本人；创建提交前确认 author/committer 配置。
- 推送重写历史只能使用 `--force-with-lease`，禁止无保护 force push。
- 提交前检查 diff 不包含 API Key、真实 `.env`、`backend/data`、构建产物或测试运行数据。
- 不要修改或删除用户无关的未提交改动。

## 12. 编码原则

- 优先修复根因，并为失败路径补测试，不只覆盖 happy path。
- 后端路径操作必须 resolve 后验证仍位于项目根目录。
- LLM 输出一律视为不可信输入：验证格式、类型、路径、状态和大小。
- 新的长任务必须持久化状态，并明确 pending/running/awaiting_review/accepted/rejected/failed/cancelled/interrupted 等语义。
- 新增 SSE 流时处理客户端取消、上游断流、空响应和代理缓冲。
- 前端隐藏页面应真正卸载，避免不可见组件继续发请求。
- 前端 API 路径只通过 `frontend/src/lib/api.ts` 构造，避免组件内散落 URL。
- 不要把 API Key 放入前端状态回显、日志或错误消息。
- 不要把可重建缓存当作事实来源。
- 修改公共接口时同步更新前端、测试、README 和架构文档。

## 13. 推荐阅读顺序

第一次接管项目时按以下顺序阅读：

1. `README.md`：产品能力、启动方式和边界。
2. `docs/ARCHITECTURE.md`：整体数据与请求流。
3. `backend/app/main.py`、`dependencies.py`：应用入口和 Runtime。
4. `backend/app/storage/project_store.py`、`file_store.py`、`wiki_store.py`：数据模型与一致性。
5. `backend/app/agents/chat_agent.py`、`wiki/context_budget.py`：聊天召回链路。
6. `backend/app/ingest/pipeline.py`、`prompts.py`、`api/ingest.py`：摄入与审阅前提交。
7. `backend/app/research/deep_research.py`、`api/research.py`：研究和证据链。
8. `backend/app/llm.py`：Provider 协议适配。
9. `frontend/src/App.tsx`、`lib/api.ts`、`hooks/useChat.ts`：前端主链路。
10. `backend/tests/`、`frontend/src/**/*.test.ts*`、`frontend/e2e/`：实际行为契约。
11. `docs/INTERVIEW_GUIDE.md`：设计取舍、面试话术和性能数据口径。

## 14. 交付时应该说明什么

最终回复至少包含：

- 改了哪些用户可见行为。
- 涉及哪些关键文件。
- 运行了哪些测试以及结果。
- 是否还有已知边界或未覆盖验证。
- 是否提交、切分支或推送；没有做也要明确。

如果服务仍在运行，说明前后端 URL 和非默认端口原因；不要把其他项目占用的端口误认为 llmwiki 服务。
