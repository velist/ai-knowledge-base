#!/usr/bin/env python3
"""简化的应用启动脚本"""

import os
import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def setup_environment():
    """设置环境"""
    # 创建必要的目录
    directories = [
        "uploads",
        "logs",
        "static"
    ]
    
    for directory in directories:
        os.makedirs(directory, exist_ok=True)
        print(f"目录已准备: {directory}")

def main():
    """主函数"""
    print("=" * 50)
    print("启动 AI知识库系统")
    print("=" * 50)
    
    # 设置环境
    setup_environment()
    
    # 启动应用
    print("启动Web服务器...")
    print("服务地址: http://localhost:8000")
    print("API文档: http://localhost:8000/docs")
    print("健康检查: http://localhost:8000/health")
    
    try:
        import uvicorn
        uvicorn.run(
            "main:app",
            host="0.0.0.0",
            port=8000,
            reload=True,
            log_level="info"
        )
    except ImportError:
        print("错误: 缺少uvicorn依赖")
        print("请运行: pip install uvicorn")
        sys.exit(1)
    except KeyboardInterrupt:
        print("收到停止信号，正在关闭...")
    except Exception as e:
        print(f"启动失败: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()