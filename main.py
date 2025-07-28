"""AI知识库应用主入口"""

import uvicorn
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
import os
import logging

from app.config import settings
from app.core.database import init_database, close_database
from app.core.redis_client import init_redis, close_redis
from app.services.ai_service import ai_service_manager
from app.api import api_router
from app.core.exceptions import (
    BaseCustomException, ValidationError, AuthenticationError,
    AuthorizationError, AIServiceError, RateLimitError
)

# 配置日志
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper(), logging.INFO),
    format="%(asctime)s | %(levelname)s | %(name)s:%(funcName)s:%(lineno)d | %(message)s",
    handlers=[
        logging.FileHandler(settings.log_file, encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时初始化
    logger.info("正在启动AI知识库应用...")
    
    try:
        # 初始化数据库
        logger.info("初始化数据库连接...")
        await init_database()
        
        # 初始化Redis
        logger.info("初始化Redis连接...")
        await init_redis()
        
        # 创建上传目录
        os.makedirs(settings.upload_dir, exist_ok=True)
        logger.info(f"上传目录已准备: {settings.upload_dir}")
        
        # 验证AI服务
        if settings.siliconflow_api_key:
            logger.info("AI服务已配置")
        else:
            logger.warning("AI服务未配置，某些功能可能不可用")
        
        logger.info("应用启动完成")
        
    except Exception as e:
        logger.error(f"应用启动失败: {str(e)}")
        raise
    
    yield
    
    # 关闭时清理
    logger.info("正在关闭应用...")
    
    try:
        # 关闭数据库连接
        await close_database()
        logger.info("数据库连接已关闭")
        
        # 关闭Redis连接
        await close_redis()
        logger.info("Redis连接已关闭")
        
        logger.info("应用已安全关闭")
        
    except Exception as e:
        logger.error(f"应用关闭时出错: {str(e)}")

# 创建FastAPI应用
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="基于AI的智能知识库管理系统",
    docs_url="/docs" if settings.debug else None,
    redoc_url="/redoc" if settings.debug else None,
    lifespan=lifespan
)

# 添加CORS中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.get_cors_origins(),
    allow_credentials=getattr(settings, 'cors_allow_credentials', True),
    allow_methods=getattr(settings, 'cors_allow_methods', ["*"]),
    allow_headers=getattr(settings, 'cors_allow_headers', ["*"]),
)

# 添加可信主机中间件（生产环境）
if not settings.debug:
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=["*"]  # 生产环境中应该配置具体的域名
    )

# 静态文件服务
if os.path.exists("static"):
    app.mount("/static", StaticFiles(directory="static"), name="static")

# 上传文件服务
if os.path.exists(settings.upload_dir):
    app.mount("/uploads", StaticFiles(directory=settings.upload_dir), name="uploads")

# 全局异常处理器
@app.exception_handler(BaseCustomException)
async def custom_exception_handler(request: Request, exc: BaseCustomException):
    """自定义异常处理"""
    logger.error(f"自定义异常: {exc.message} - {request.url}")
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.error_code,
            "message": exc.message,
            "details": exc.details
        }
    )

@app.exception_handler(ValidationError)
async def validation_exception_handler(request: Request, exc: ValidationError):
    """验证错误处理"""
    logger.warning(f"验证错误: {exc.message} - {request.url}")
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={
            "error": "validation_error",
            "message": exc.message
        }
    )

@app.exception_handler(AuthenticationError)
async def authentication_exception_handler(request: Request, exc: AuthenticationError):
    """认证错误处理"""
    logger.warning(f"认证错误: {exc.message} - {request.url}")
    return JSONResponse(
        status_code=status.HTTP_401_UNAUTHORIZED,
        content={
            "error": "authentication_error",
            "message": exc.message
        }
    )

@app.exception_handler(AuthorizationError)
async def authorization_exception_handler(request: Request, exc: AuthorizationError):
    """授权错误处理"""
    logger.warning(f"授权错误: {exc.message} - {request.url}")
    return JSONResponse(
        status_code=status.HTTP_403_FORBIDDEN,
        content={
            "error": "authorization_error",
            "message": exc.message
        }
    )

@app.exception_handler(AIServiceError)
async def ai_service_exception_handler(request: Request, exc: AIServiceError):
    """AI服务错误处理"""
    logger.error(f"AI服务错误: {exc.message} - {request.url}")
    return JSONResponse(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        content={
            "error": "ai_service_error",
            "message": exc.message
        }
    )

@app.exception_handler(RateLimitError)
async def rate_limit_exception_handler(request: Request, exc: RateLimitError):
    """速率限制错误处理"""
    logger.warning(f"速率限制: {exc.message} - {request.url}")
    return JSONResponse(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        content={
            "error": "rate_limit_error",
            "message": exc.message
        }
    )

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """通用异常处理"""
    logger.error(f"未处理的异常: {str(exc)} - {request.url}")
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "internal_server_error",
            "message": "服务器内部错误" if not settings.debug else str(exc)
        }
    )

# 健康检查端点
@app.get("/health", tags=["健康检查"])
async def health_check():
    """健康检查"""
    try:
        # 检查数据库连接
        from app.core.database import check_database_connection
        db_status = await check_database_connection()
        
        # 检查Redis连接
        from app.core.redis_client import get_redis
        redis_client = get_redis()
        redis_status = await redis_client.ping() if redis_client else False
        
        # 检查AI服务
        ai_status = bool(settings.siliconflow_api_key)
        
        return {
            "status": "healthy",
            "timestamp": "2024-01-01T00:00:00Z",
            "version": settings.app_version,
            "services": {
                "database": "ok" if db_status else "error",
                "redis": "ok" if redis_status else "error",
                "ai_service": "ok" if ai_status else "not_configured"
            }
        }
    except Exception as e:
        logger.error(f"健康检查失败: {str(e)}")
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                "status": "unhealthy",
                "error": str(e)
            }
        )

# 根路径
@app.get("/", tags=["根路径"])
async def root():
    """根路径"""
    return {
        "message": f"欢迎使用{settings.app_name}",
        "version": settings.app_version,
        "docs": "/docs" if settings.debug else "文档在生产环境中不可用",
        "health": "/health"
    }

# 包含API路由
app.include_router(api_router, prefix="/api")

# 中间件：请求日志
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """记录请求日志"""
    import time
    start_time = time.time()
    logger.info(f"请求开始: {request.method} {request.url}")
    
    response = await call_next(request)
    
    process_time = time.time() - start_time
    logger.info(f"请求完成: {request.method} {request.url} - {response.status_code} - {process_time:.3f}s")
    
    return response

if __name__ == "__main__":
    # 开发环境直接运行
    uvicorn.run(
        "main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        log_level=settings.log_level.lower(),
        access_log=True
    )