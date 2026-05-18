#!/bin/bash
# 阿里云 ECS 一键部署脚本

set -e

echo "=== DayDayKnow ECS 部署 ==="
echo ""

# 检查是否为 root 用户
if [ "$EUID" -ne 0 ]; then
    echo "请使用 root 用户运行此脚本"
    echo "sudo bash deploy-ecs.sh"
    exit 1
fi

# 安装 Docker
if ! command -v docker &> /dev/null; then
    echo "正在安装 Docker..."
    curl -fsSL https://get.docker.com | bash
    systemctl start docker
    systemctl enable docker
    echo "Docker 安装完成"
fi

# 安装 Docker Compose
if ! command -v docker-compose &> /dev/null; then
    echo "正在安装 Docker Compose..."
    curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
    chmod +x /usr/local/bin/docker-compose
    echo "Docker Compose 安装完成"
fi

# 创建部署目录
DEPLOY_DIR="/opt/daydayknow"
mkdir -p $DEPLOY_DIR
cd $DEPLOY_DIR

# 克隆代码（如果不存在）
if [ ! -d ".git" ]; then
    echo "正在克隆代码..."
    read -p "请输入 Git 仓库地址: " REPO_URL
    git clone $REPO_URL .
fi

# 检查环境变量文件
if [ ! -f "backend/.env" ]; then
    echo ""
    echo "请创建后端环境变量文件:"
    echo "cp backend/.env.example backend/.env"
    echo "然后编辑 backend/.env 填入实际配置"
    echo ""
    echo "必填配置:"
    echo "  - SUPABASE_URL"
    echo "  - SUPABASE_ANON_KEY"
    echo "  - LLM_API_KEY"
    echo "  - CRON_SECRET"
    echo ""
    read -p "是否现在创建 backend/.env 文件? (y/n): " create_env
    if [ "$create_env" = "y" ]; then
        cp backend/.env.example backend/.env
        echo "请编辑 /opt/daydayknow/backend/.env 文件"
        nano backend/.env
    fi
fi

# 构建并启动服务
echo ""
echo "正在构建并启动服务..."
docker-compose -f docker-compose.prod.yml up -d --build

echo ""
echo "=== 部署完成 ==="
echo ""
echo "服务状态:"
docker-compose -f docker-compose.prod.yml ps
echo ""
echo "访问地址:"
echo "  前端: http://$(curl -s ifconfig.me):3000"
echo "  后端: http://$(curl -s ifconfig.me):8000"
echo "  API 文档: http://$(curl -s ifconfig.me):8000/docs"
echo ""
echo "常用命令:"
echo "  查看日志: docker-compose -f docker-compose.prod.yml logs -f"
echo "  重启服务: docker-compose -f docker-compose.prod.yml restart"
echo "  停止服务: docker-compose -f docker-compose.prod.yml down"
echo "  更新部署: git pull && docker-compose -f docker-compose.prod.yml up -d --build"