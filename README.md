# 日知录 (DayDayKnow)

把昨天遇到的陌生术语，变成今晨一份专属扫盲日报。

## 功能特性

- **术语捕获**：从文章中选中句子，分享给日知录
- **智能提取**：使用LLM自动提取专业术语
- **日报生成**：次日生成专属扫盲日报（HyDE技术增强）
- **射箭确认**：滑动卡片确认已掌握
- **知识星图**：可视化展示术语关联，支持双指缩放和拖拽
- **多LLM支持**：OpenAI / Claude / 通义千问 / 智谱 / DeepSeek / Ollama
- **PWA支持**：可安装到主屏幕，离线可用
- **Docker部署**：支持开发/生产环境一键部署

## 技术栈

- **前端**：Next.js 16 + React 19 + TypeScript + Tailwind CSS v4
- **后端**：FastAPI (Python) + Uvicorn
- **数据库**：Supabase (PostgreSQL + pgvector)
- **LLM**：OpenAI兼容接口，支持多厂商切换
- **部署**：Docker + Nginx
- **测试**：Pytest (后端)
- **PWA**：Service Worker + Web App Manifest

## 快速开始

### 1. 克隆项目

```bash
git clone <repository-url>
cd daydayknow
```

### 2. 安装依赖

```bash
# 前端依赖
npm install

# 后端依赖
cd backend && pip install -r requirements.txt && cd ..
```

### 3. 配置环境变量

**前端**：复制 `.env.example` 为 `.env.local`，填入配置：

```env
# Supabase配置
NEXT_PUBLIC_SUPABASE_URL=your_supabase_url
NEXT_PUBLIC_SUPABASE_ANON_KEY=your_supabase_anon_key

# 后端API地址
NEXT_PUBLIC_API_URL=http://localhost:8000

# 应用配置
NEXT_PUBLIC_APP_URL=http://localhost:3000
```

**后端**：复制 `backend/.env.example` 为 `backend/.env.local`，填入配置：

```env
# Supabase配置
SUPABASE_URL=your_supabase_url
SUPABASE_ANON_KEY=your_supabase_anon_key

# LLM配置
LLM_PROVIDER=deepseek
LLM_API_KEY=your_api_key

# 应用配置
CRON_SECRET=your_cron_secret
```

### 4. 模拟模式

暂时没有Supabase？设置 `MOCK_MODE=true` 即可使用内存数据库体验全部功能。

### 5. 启动

```bash
# 启动后端 (端口 8000)
cd backend && uvicorn app.main:app --reload --port 8000

# 启动前端 (端口 3000)
npm run dev
```

访问 http://localhost:3000

## 项目结构

```
├── src/                        # Next.js 前端
│   ├── app/                    # App Router
│   │   ├── daily/             # 日报阅读页
│   │   ├── star-map/          # 星图可视化页
│   │   ├── layout.tsx         # 根布局
│   │   └── page.tsx           # 主页（捕获页）
│   ├── components/            # React组件
│   │   ├── TermCard.tsx       # 术语卡片组件
│   │   └── PWARegister.tsx    # PWA注册组件
│   └── lib/                   # 工具库
│       ├── api.ts             # API请求封装
│       ├── supabase.ts        # Supabase客户端
│       └── ...
├── backend/                    # FastAPI 后端
│   ├── app/
│   │   ├── main.py            # FastAPI 应用入口
│   │   ├── config.py          # 环境变量配置
│   │   ├── dependencies.py    # 依赖注入
│   │   ├── models/schemas.py  # Pydantic数据模型
│   │   ├── routers/           # API路由
│   │   │   ├── capture.py     # 术语捕获
│   │   │   ├── daily_doc.py   # 日报获取/生成
│   │   │   ├── star_map.py    # 星图数据
│   │   │   ├── terms.py       # 射箭确认
│   │   │   └── batch.py       # 批处理
│   │   ├── services/          # 业务逻辑
│   │   │   ├── supabase_client.py
│   │   │   ├── mock_supabase.py
│   │   │   ├── llm_client.py
│   │   │   └── batch_processor.py
│   │   └── utils/logger.py    # 日志系统
│   ├── tests/                 # Pytest测试用例
│   ├── requirements.txt
│   └── Dockerfile
├── docker-compose.yml          # Docker编排
└── ...
```

## API接口

后端由 FastAPI 提供服务，启动后访问 http://localhost:8000/docs 查看自动生成的 API 文档。

| 接口 | 方法 | 说明 |
|------|------|------|
| `/api/capture` | POST | 捕获并提取术语 |
| `/api/daily-doc` | GET | 获取日报内容 |
| `/api/daily-doc/generate` | POST | 手动触发日报生成 |
| `/api/terms/{id}/confirm` | POST | 确认掌握，点亮星图 |
| `/api/star-map` | GET | 获取星图数据 |
| `/api/batch` | GET | 批处理健康检查 |
| `/api/batch` | POST | 批量处理术语（Cron） |

### 运行测试

```bash
cd backend && python -m pytest tests/ -v
```

## 部署

### Docker

```bash
# 开发环境（前端 + 后端）
docker compose --profile dev up

# 生产环境（前端 + 后端）
docker compose --profile prod up

# 生产环境 + Nginx反向代理
docker compose --profile prod-nginx up
```

## 待开发功能 (TODO)

- [ ] 用户认证系统（邮箱/手机号登录，替代匿名用户ID）
- [ ] 术语导入（批量导入历史术语）
- [ ] 星图节点搜索和筛选（按领域/时间）
- [ ] 术语复习提醒（基于遗忘曲线）
- [ ] 术语关联手动标注（自定义连线关系）
- [ ] 日报分享功能（生成图片/PDF）
- [ ] 术语详情页（完整学习记录和关联术语）
- [ ] 星图布局优化（力导向布局算法）
- [ ] 多语言支持（中英文切换）
- [ ] 数据导出（JSON/CSV格式）
- [ ] 深色/浅色主题切换
- [ ] 移动端手势优化（长按菜单、滑动翻页）
- [ ] 通知推送（每日日报提醒）
- [ ] 社交功能（好友星图对比、术语推荐）

## 贡献指南

1. Fork项目
2. 创建功能分支 (`git checkout -b feature/xxx`)
3. 提交更改 (`git commit -m 'feat: add xxx'`)
4. 推送到分支 (`git push origin feature/xxx`)
5. 创建Pull Request

## 许可证

MIT License
