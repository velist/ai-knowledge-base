#!/bin/bash

# AI知识库系统启动脚本

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 打印带颜色的消息
print_message() {
    echo -e "${2}${1}${NC}"
}

# 检查命令是否存在
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# 检查端口是否被占用
check_port() {
    if lsof -Pi :$1 -sTCP:LISTEN -t >/dev/null ; then
        return 0
    else
        return 1
    fi
}

# 主函数
main() {
    print_message "🧠 AI知识库系统启动脚本" "$BLUE"
    echo "=========================================="
    
    # 检查Python
    if ! command_exists python3; then
        print_message "❌ Python3 未安装" "$RED"
        exit 1
    fi
    
    # 检查pip
    if ! command_exists pip3; then
        print_message "❌ pip3 未安装" "$RED"
        exit 1
    fi
    
    print_message "✅ Python环境检查通过" "$GREEN"
    
    # 检查依赖
    if [ ! -f "requirements.txt" ]; then
        print_message "❌ requirements.txt 文件不存在" "$RED"
        exit 1
    fi
    
    # 安装依赖
    print_message "📦 检查并安装依赖..." "$YELLOW"
    pip3 install -r requirements.txt --quiet
    
    # 创建必要目录
    mkdir -p logs uploads static
    
    # 检查端口占用
    if check_port 8000; then
        print_message "⚠️  端口 8000 已被占用" "$YELLOW"
    fi
    
    if check_port 8003; then
        print_message "⚠️  端口 8003 已被占用" "$YELLOW"
    fi
    
    # 选择启动模式
    echo ""
    print_message "请选择启动模式:" "$BLUE"
    echo "1) 开发模式 (带热重载)"
    echo "2) 生产模式 (多进程)"
    echo "3) Docker模式"
    echo "4) 仅启动用户前端"
    echo "5) 仅启动管理后台"
    read -p "请输入选择 (1-5): " choice
    
    case $choice in
        1)
            print_message "🚀 启动开发模式..." "$GREEN"
            echo "用户前端: http://localhost:8000"
            echo "管理后台: http://localhost:8003"
            echo "按 Ctrl+C 停止服务"
            echo ""
            
            # 后台启动用户前端
            uvicorn main_user_frontend:app --host 0.0.0.0 --port 8000 --reload &
            FRONTEND_PID=$!
            
            # 等待2秒
            sleep 2
            
            # 启动管理后台
            uvicorn admin_backend:app --host 0.0.0.0 --port 8003 --reload &
            BACKEND_PID=$!
            
            # 等待进程结束
            wait $FRONTEND_PID $BACKEND_PID
            ;;
        2)
            print_message "🚀 启动生产模式..." "$GREEN"
            python3 deploy.py
            ;;
        3)
            if ! command_exists docker; then
                print_message "❌ Docker 未安装" "$RED"
                exit 1
            fi
            
            if ! command_exists docker-compose; then
                print_message "❌ Docker Compose 未安装" "$RED"
                exit 1
            fi
            
            print_message "🐳 启动Docker模式..." "$GREEN"
            docker-compose up --build
            ;;
        4)
            print_message "🚀 启动用户前端..." "$GREEN"
            echo "用户前端: http://localhost:8000"
            uvicorn main_user_frontend:app --host 0.0.0.0 --port 8000 --reload
            ;;
        5)
            print_message "🚀 启动管理后台..." "$GREEN"
            echo "管理后台: http://localhost:8003"
            echo "管理员账户: vee5208 / forxy131"
            uvicorn admin_backend:app --host 0.0.0.0 --port 8003 --reload
            ;;
        *)
            print_message "❌ 无效选择" "$RED"
            exit 1
            ;;
    esac
}

# 信号处理
trap 'print_message "\n🛑 正在停止服务..." "$YELLOW"; kill $FRONTEND_PID $BACKEND_PID 2>/dev/null; exit 0' INT TERM

# 运行主函数
main "$@"