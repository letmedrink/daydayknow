# 阿里云 ECS 部署指南

## 前置条件

- 阿里云 ECS 实例（推荐 2核4G 以上）
- Ubuntu 20.04+ 或 CentOS 7+
- 安全组开放 80、443、3000、8000 端口

## 快速部署

### 1. SSH 登录服务器

```bash
ssh root@your-ecs-ip
```

### 2. 一键部署

```bash
# 下载部署脚本
curl -O https://raw.githubusercontent.com/your-repo/daydayknow/main/deploy-ecs.sh

# 执行部署
bash deploy-ecs.sh
```

### 3. 配置环境变量

```bash
cd /opt/daydayknow
cp .env.example .env
nano .env
```

填入以下配置：

```env
# Supabase 配置
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_ANON_KEY=your-supabase-anon-key

# LLM 配置
LLM_PROVIDER=deepseek
LLM_API_KEY=your-deepseek-api-key

# 应用配置
CRON_SECRET=your-random-secret
LOG_LEVEL=info
```

### 4. 启动服务

```bash
docker-compose -f docker-compose.prod.yml up -d
```

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
git clone https://github.com/your-repo/daydayknow.git .
```

### 3. 配置环境变量

```bash
cp .env.example .env
# 编辑 .env 文件
```

### 4. 构建并启动

```bash
docker-compose -f docker-compose.prod.yml up -d --build
```

## 访问地址

- 前端: `http://your-ecs-ip:3000`
- 后端: `http://your-ecs-ip:8000`
- API 文档: `http://your-ecs-ip:8000/docs`

## 常用命令

```bash
# 查看服务状态
docker-compose -f docker-compose.prod.yml ps

# 查看日志
docker-compose -f docker-compose.prod.yml logs -f

# 重启服务
docker-compose -f docker-compose.prod.yml restart

# 停止服务
docker-compose -f docker-compose.prod.yml down

# 更新部署
git pull
docker-compose -f docker-compose.prod.yml up -d --build
```

## 配置 Nginx 反向代理（可选）

### 1. 启动 Nginx 服务

```bash
docker-compose -f docker-compose.prod.yml --profile nginx up -d
```

### 2. 配置 SSL 证书

```bash
# 安装 certbot
apt install -y certbot

# 获取证书
certbot certonly --standalone -d your-domain.com

# 复制证书
mkdir -p deploy/nginx/ssl
cp /etc/letsencrypt/live/your-domain.com/fullchain.pem deploy/nginx/ssl/
cp /etc/letsencrypt/live/your-domain.com/privkey.pem deploy/nginx/ssl/
```

### 3. 更新 Nginx 配置

编辑 `deploy/nginx/nginx.conf`，添加 SSL 配置。

## 配置域名

### 1. 添加 DNS 解析

在阿里云 DNS 控制台添加 A 记录：

| 主机记录 | 记录类型 | 记录值 |
|----------|----------|--------|
| @ | A | your-ecs-ip |
| www | A | your-ecs-ip |

### 2. 更新 Nginx 配置

将 `server_name _;` 改为 `server_name your-domain.com;`

## 监控和日志

### 查看容器资源使用

```bash
docker stats
```

### 查看日志

```bash
# 实时日志
docker-compose -f docker-compose.prod.yml logs -f

# 指定服务日志
docker-compose -f docker-compose.prod.yml logs -f backend
```

### 健康检查

```bash
curl http://localhost:8000/health
```

## 故障排查

### 1. 服务无法启动

```bash
# 查看日志
docker-compose -f docker-compose.prod.yml logs

# 检查端口占用
netstat -tlnp | grep -E '3000|8000'
```

### 2. 数据库连接失败

检查环境变量是否正确：

```bash
docker-compose -f docker-compose.prod.yml exec backend env | grep SUPABASE
```

### 3. LLM 调用失败

检查 API Key 是否有效：

```bash
docker-compose -f docker-compose.prod.yml exec backend env | grep LLM
```

## 备份和恢复

### 备份

```bash
# 备份代码
tar -czf daydayknow-backup.tar.gz /opt/daydayknow

# 备份环境变量
cp /opt/daydayknow/.env /opt/daydayknow/.env.backup
```

### 恢复

```bash
# 恢复代码
tar -xzf daydayknow-backup.tar.gz -C /

# 恢复环境变量
cp /opt/daydayknow/.env.backup /opt/daydayknow/.env

# 重启服务
cd /opt/daydayknow
docker-compose -f docker-compose.prod.yml up -d --build
```