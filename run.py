#!/usr/bin/env python3
"""应用启动脚本"""

import os
import sys
import asyncio
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from app.config import settings
from loguru import logger

def setup_environment():
    """设置环境"""
    # 创建必要的目录
    directories = [
        settings.upload_dir,
        "logs",
        "static"
    ]
    
    for directory in directories:
        os.makedirs(directory, exist_ok=True)
        logger.info(f"目录已准备: {directory}")

def check_dependencies():
    """检查依赖"""
    required_packages = [
        "fastapi",
        "uvicorn",
        "sqlalchemy",
        "redis",
        "httpx",
        "loguru"
    ]
    
    missing_packages = []
    
    for package in required_packages:
        try:
            __import__(package)
        except ImportError:
            missing_packages.append(package)
    
    if missing_packages:
        logger.error(f"缺少依赖包: {', '.join(missing_packages)}")
        logger.info("请运行: pip install -r requirements.txt")
        return False
    
    logger.info("所有依赖包已安装")
    return True

async def test_services():
    """测试服务连接"""
    logger.info("测试服务连接...")
    
    # 测试AI服务
    if settings.siliconflow_api_key:
        try:
            from app.services.ai_service import SiliconFlowProvider
            provider = SiliconFlowProvider(settings.siliconflow_api_key)
            
            # 简单的测试调用
            test_messages = [{"role": "user", "content": "Hello"}]
            response = await provider.chat_completion(test_messages, max_tokens=10)
            
            if response:
                logger.info("✓ AI服务连接正常")
            else:
                logger.warning("⚠ AI服务响应异常")
                
        except Exception as e:
            logger.error(f"✗ AI服务连接失败: {str(e)}")
    else:
        logger.warning("⚠ AI服务未配置")
    
    # 测试Redis连接
    try:
        import redis.asyncio as redis
        redis_client = redis.from_url(settings.redis_url)
        await redis_client.ping()
        await redis_client.close()
        logger.info("✓ Redis连接正常")
    except Exception as e:
        logger.warning(f"⚠ Redis连接失败: {str(e)}")
    
    logger.info("服务测试完成")

def main():
    """主函数"""
    logger.info("=" * 50)
    logger.info(f"启动 {settings.app_name} v{settings.app_version}")
    logger.info("=" * 50)
    
    # 检查配置
    logger.info("配置加载完成")
    
    # 设置环境
    setup_environment()
    
    # 检查依赖
    if not check_dependencies():
        sys.exit(1)
    
    # 测试服务
    try:
        asyncio.run(test_services())
    except Exception as e:
        logger.error(f"服务测试失败: {str(e)}")
    
    # 启动应用
    logger.info("启动Web服务器...")
    logger.info(f"服务地址: http://{settings.host}:{settings.port}")
    logger.info(f"API文档: http://{settings.host}:{settings.port}/docs")
    logger.info(f"健康检查: http://{settings.host}:{settings.port}/health")
    
    try:
        import uvicorn
        uvicorn.run(
            "main:app",
            host=settings.host,
            port=settings.port,
            reload=settings.debug,
            log_level=settings.log_level.lower(),
            access_log=True
        )
    except KeyboardInterrupt:
        logger.info("收到停止信号，正在关闭...")
    except Exception as e:
        logger.error(f"启动失败: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()