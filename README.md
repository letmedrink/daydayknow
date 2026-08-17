# llmwiki

llmwiki 是一个面向可信本机单用户的 AI 知识库：通过文档摄入、对话和 Deep Research 生成可直接编辑的 Markdown Wiki，并自动建立知识图谱。

## 功能

- 将 PDF、PPTX、DOCX、TXT、Markdown、CSV 和 JSON 整理为结构化 Wiki
- 在写入前预览、接受或拒绝 AI 生成的页面，支持取消、重试和强制重新摄入
- 基于项目 Wiki 进行带引用的流式对话
- 浏览、搜索和直接编辑 Markdown 页面，查看页面历史与知识图谱
- 使用 Tavily 或 SerpApi 执行 Deep Research，并在接受后写入 Wiki
- 支持 OpenAI-compatible 与 Anthropic Messages 协议
- 所有业务数据保存在本地 JSON、Markdown 和 YAML frontmatter 文件中

## 技术栈

- React 19 + TypeScript + Vite
- FastAPI + Uvicorn
- JSON + Markdown/YAML frontmatter 文件存储
- REST + Server-Sent Events（SSE）
- Docker Compose + Nginx

## 快速开始（推荐）

### 使用 Docker

需要 Docker Desktop 或 Docker Engine，并支持 Docker Compose v2。

```bash
git clone https://github.com/letmedrink/llmwiki.git
cd llmwiki
docker compose up --build
```

打开 `http://localhost:3000`。首次使用时：

1. 创建项目。
2. 进入“设置”，添加 LLM Provider，填写协议、模型、Base URL 和 API Key。
3. 测试连接并保存，然后选择该 Provider。
4. 进入“摄入”，上传文档；预览生成结果后选择接受或拒绝。
5. 在 Wiki、图谱或对话页面继续探索内容。

Docker 启动不要求预先创建 `.env`。如需通过环境变量提供默认配置，可执行：

```bash
cp backend/.env.example backend/.env
docker compose up --build
```

常用运维命令：

```bash
docker compose ps
docker compose logs -f backend frontend
curl http://localhost:3000/health
docker compose down
```

应用数据保存在 `llmwiki-data` volume，普通 `docker compose down` 不会删除数据。`docker compose down -v` 会永久删除该 volume 及其中的项目数据，请谨慎使用。

### 本地开发

需要 Node.js 20+、npm，以及 Python 3.11+。

启动后端：

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload --port 8000
```

Windows PowerShell 激活虚拟环境时使用 `.venv\Scripts\Activate.ps1`。

另开终端启动前端：

```bash
cd frontend
cp .env.example .env
npm install
npm run dev
```

打开 `http://localhost:5173`。本地开发时 `frontend/.env` 中的 `VITE_API_URL=http://localhost:8000` 是必需的；Vite 开发服务器本身不代理后端请求。

## 配置

推荐在设置页管理 Provider。后端也支持以下环境变量：

| 变量 | 默认值 | 用途 |
| --- | --- | --- |
| `DATA_DIR` | `./data` | 全局配置和项目数据目录 |
| `LLM_PROVIDER` | `openai` | 默认协议，支持 `openai` 或 `anthropic` |
| `LLM_API_KEY` | 空 | 默认 LLM API Key |
| `LLM_BASE_URL` | OpenAI API 地址 | 默认 LLM Base URL |
| `LLM_MODEL` | `gpt-4o-mini` | 默认文本模型 |
| `LLM_MAX_TOKENS` | `4096` | 默认最大输出 token 数 |
| `LLM_TEMPERATURE` | `0.7` | 默认采样温度 |
| `MULTIMODAL_MODEL` | 空 | 图片描述模型；未配置时跳过图片描述 |
| `SEARCH_API_PROVIDER` | 空 | Deep Research 搜索服务：`tavily` 或 `serpapi` |
| `SEARCH_API_KEY` | 空 | 搜索服务 API Key |
| `MAX_UPLOAD_BYTES` | `26214400` | 单文件上传上限，默认 25 MiB |
| `LOG_LEVEL` | `info` | 后端日志级别 |

读取设置的 API 不会返回已保存的 API Key，只返回 `has_api_key`。密钥仍以明文保存在本地数据目录，请限制该目录的文件权限，不要提交真实 `.env` 或运行数据。

## 核心工作流

### 文档摄入

摄入任务先解析原文和图片，再由 LLM 按项目已有页面与生成规则产出暂存 Wiki。前端展示预览后，只有“接受”才会原子写入正式 Wiki；“拒绝”会丢弃暂存结果。相同原文默认命中带 pipeline 版本的缓存，确认重新导入时会发送 `force=true` 绕过缓存。

最终质量主要取决于模型的长文本理解和结构化输出能力、摄入提示词、源文档质量，以及项目中已有 Wiki 的结构。建议先用小文档验证模型配置和页面规则，再处理大文档。

### 对话与研究

聊天、摄入和研究通过 SSE 返回进度。聊天的 `done` 事件表示完整回复已经持久化；上游断流、空响应、客户端取消或写盘失败不会留下空对话。

Deep Research 需要配置 Tavily 或 SerpApi。未配置、全部搜索失败或没有结果时任务会终止，不会让 LLM 在无来源情况下生成 Wiki。研究结果同样需要预览并接受后才写入。

## API 概览

- 全局：`/api/projects`、`/api/settings`、`/api/profile`
- 项目：`/api/projects/{project_id}/chat|conversations|wiki|ingest|reviews|research`
- 健康检查：`/health`

成功响应和错误响应采用统一结构；错误格式为 `{ "success": false, "error": "...", "code": "..." }`。SSE 事件包括 `reasoning`、`chunk`、`references`、`options`、`done` 和 `error`。

## 数据布局

```text
data/
├── settings.json
├── projects.json
├── profile/profile.json
└── projects/{project_id}/
    ├── conversations/
    ├── reviews.json
    ├── ingest-cache.json
    ├── ingest-jobs/
    ├── research-jobs/
    ├── page-history/
    └── wiki/
```

Markdown/JSON 是唯一事实来源，内存索引和图谱缓存均可重建。项目的普通删除只从项目列表移除并保留磁盘数据；应用创建的托管项目可在输入项目名确认后永久删除。绑定自定义外部目录的项目只能从列表移除。

摄入测试语料位于 `examples/fixtures/`，不会复制进生产镜像。详细设计见 [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md)。

## 测试与检查

后端：

```bash
cd backend
source .venv/bin/activate
pytest
```

前端：

```bash
cd frontend
npm test
npm run typecheck
npm run build
```

部署配置：

```bash
docker compose config
```

## 当前边界

- 面向可信本机单用户，不包含认证、授权和租户隔离；不要直接暴露到公网。
- 文件锁只保证单个 Uvicorn 进程内的并发安全，不支持多个后端实例共享同一数据目录。
- 适合单机约 1 万个 Wiki 页面；更大规模尚无服务等级保证。
- API Key 明文保存在本地数据目录；研究摘要和相关 Wiki 上下文会发送给所配置的 LLM 服务商。
- 文档解析和生成效果受文件质量、模型能力、上下文窗口及提示规则影响，复杂排版和扫描件可能需要预处理。

## 排错

- 页面能打开但 API 返回 HTML：确认本地开发的 `frontend/.env` 已设置 `VITE_API_URL=http://localhost:8000`，然后重启 Vite。
- Provider 鉴权失败：不要把 `<your-api-key>` 一类占位文本当作 Key；在设置页重新填写并测试连接。
- Docker 前端未就绪：运行 `docker compose ps`，再用 `docker compose logs -f backend frontend` 查看健康检查和启动日志。
- 摄入没有产生正式页面：检查任务是否仍在等待审阅；生成结果必须被接受后才会写入 Wiki。

## 参与开发

提交变更前请至少运行相关测试、TypeScript 类型检查和生产构建。Bug 报告请包含复现步骤、预期行为、实际行为和已脱敏的日志；不要在 Issue、提交或截图中包含 API Key、真实 `.env` 或私有文档内容。

## 许可证

本项目使用 [MIT License](LICENSE)。
