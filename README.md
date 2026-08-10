# llmwiki

通过 AI 对话、文档摄入和 Deep Research 构建个人 Markdown Wiki 与知识图谱。

## Stack

- React 19 + TypeScript + Vite
- FastAPI + Uvicorn
- JSON + Markdown/YAML frontmatter 文件存储
- OpenAI-compatible 与 Anthropic Messages LLM 协议
- REST + Server-Sent Events

## Local development

```bash
cd frontend
npm install
npm run dev
```

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload --port 8000
```

Vite 开发服务器运行在 `http://localhost:5173`，FastAPI 运行在 `http://localhost:8000`。开发环境可在 `frontend/.env` 设置 `VITE_API_URL=http://localhost:8000`。

## Docker

复制并填写 `backend/.env.example`：

```bash
cp backend/.env.example backend/.env
docker compose up --build
```

访问 `http://localhost:3000`。Nginx 提供前端并将 `/api` 与 `/health` 代理到后端。应用数据保存在 `llmwiki-data` volume。

## API layout

- 全局：`/api/projects`、`/api/settings`、`/api/profile`
- 项目：`/api/projects/{project_id}/chat|conversations|wiki|ingest|reviews|research`
- 健康检查：`/health`

聊天、摄入和研究使用 SSE。错误响应统一为 `{ success: false, error, code }`。

## Data layout

```text
data/
├── settings.json
├── projects.json
├── profile/profile.json
└── projects/{project_id}/
    ├── conversations/
    ├── reviews.json
    ├── ingest-cache.json
    ├── page-history/
    └── wiki/
```

摄入测试语料位于 `examples/fixtures/`，不会复制进生产镜像。架构细节见 `docs/ARCHITECTURE.md`。
