# 阿里云 ECS 部署指南

## 前置条件

- 阿里云 ECS 实例（推荐 2核4G 以上）
- Ubuntu 20.04+ 或 CentOS 7+
- 安全组开放 3000、8000 端口

## 快速部署

### 1. 上传代码到服务器

```bash
scp -r /path/to/daydayknow root@your-ecs-ip:/opt/
```

### 2. SSH 登录服务器

```bash
ssh root@your-ecs-ip
```

### 3. 配置后端环境变量

```bash
cd /opt/daydayknow
cp backend/.env.example backend/.env
nano backend/.env
```

必填配置：

```env
MOCK_MODE=false

# LLM 配置（选一个）
LLM_PROVIDER=deepseek
LLM_API_KEY=your-deepseek-api-key

# 可选：PostgreSQL
DATABASE_URL=postgresql+asyncpg://postgres:postgres@postgres:5432/daydayknow

# 可选：Redis（ARQ 任务队列）
REDIS_URL=redis://redis:6379

# 应用配置
LOG_LEVEL=info
```

### 4. 构建并启动服务

```bash
docker compose --profile prod up -d --build
```

### 5. 配置安全组

在阿里云控制台 → ECS → 安全组，添加入方向规则：

| 端口范围 | 协议 | 授权对象 |
|----------|------|----------|
| 3000/3000 | TCP | 0.0.0.0/0 |
| 8000/8000 | TCP | 0.0.0.0/0 |

### 6. 访问

- 前端: `http://your-ecs-ip:3000`
- 后端: `http://your-ecs-ip:8000`
- API 文档: `http://your-ecs-ip:8000/docs`

## 手动部署

### 1. 安装 Docker

```bash
# Ubuntu
apt update
apt install -y docker.io docker-compose

# CentOS
yum install -y docker docker-compose

# 启动 Docker
systemctl start docker
systemctl enable docker
```

### 2. 克隆代码

```bash
mkdir -p /opt/daydayknow
cd /opt/daydayknow
git clone https://github.com/letmedrink/daydayknow.git .
```

### 3. 配置环境变量

```bash
cp backend/.env.example backend/.env
nano backend/.env
```

### 4. 构建并启动

```bash
docker compose --profile prod up -d --build
```

## 常用命令

```bash
# 查看服务状态
docker compose --profile prod ps

# 查看所有日志
docker compose --profile prod logs -f

# 查看后端日志
docker compose --profile prod logs -f backend-prod

# 查看前端日志
docker compose --profile prod logs -f app-prod

# 重启服务
docker compose --profile prod restart

# 停止服务
docker compose --profile prod down

# 更新部署（只改代码时）
git pull
docker compose --profile prod up -d

# 只重新构建后端
docker compose --profile prod up -d --build backend-prod

# 只重新构建前端
docker compose --profile prod up -d --build app-prod
```

## 防火墙配置

如果服务器开启了防火墙，需要放行端口：

```bash
# Ubuntu (ufw)
ufw allow 3000
ufw allow 8000

# CentOS (firewalld)
firewall-cmd --permanent --add-port=3000/tcp
firewall-cmd --permanent --add-port=8000/tcp
firewall-cmd --reload
```

## 故障排查

### 1. 服务无法启动

```bash
# 查看日志
docker compose --profile prod logs

# 检查端口占用
netstat -tlnp | grep -E '3000|8000'
```

### 2. LLM 调用失败

检查 API Key 是否有效：

```bash
docker compose --profile prod exec backend-prod env | grep LLM
```

### 3. 前端访问后端失败（CORS）

确保 `VITE_API_URL` 指向正确的后端地址：

```bash
# 检查前端环境变量
docker compose --profile prod exec app-prod env | grep VITE
```

如果地址错误，修改 `frontend/.env` 后重新构建前端：

```bash
docker compose --profile prod up -d --build app-prod
```

### 4. 数据库连接失败

```bash
docker compose --profile prod exec backend-prod env | grep DATABASE
```

确保 PostgreSQL 容器已启动：

```bash
docker compose --profile prod ps postgres
```

## 备份和恢复

### 备份

```bash
# 备份 PostgreSQL 数据
docker compose --profile prod exec postgres pg_dump -U postgres daydayknow > backup.sql

# 备份代码和配置
tar -czf daydayknow-backup.tar.gz /opt/daydayknow
```

### 恢复

```bash
# 恢复代码
tar -xzf daydayknow-backup.tar.gz -C /

# 恢复数据库
docker compose --profile prod exec -T postgres psql -U postgres daydayknow < backup.sql

# 重启服务
cd /opt/daydayknow
docker compose --profile prod up -d --build
```
