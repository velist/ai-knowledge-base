from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
import time
import uvicorn
from loguru import logger
import sys
from pathlib import Path

from app.config import settings
from app.core.exceptions import (
    AIServiceError, 
    RateLimitError, 
    ValidationError,
    AuthenticationError,
    AuthorizationError
)
from app.api.v1.router import api_router
from app.core.database import init_db
from app.core.redis_client import init_redis
from app.services.ai_service import ai_service_manager

# 配置日志
logger.remove()
logger.add(
    sys.stdout,
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
    level=settings.log_level
)
logger.add(
    settings.log_file,
    format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
    level=settings.log_level,
    rotation="10 MB",
    retention="30 days"
)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时执行
    logger.info("🚀 启动AI知识库应用...")
    
    try:
        # 初始化数据库
        logger.info("📊 初始化数据库连接...")
        await init_db()
        
        # 初始化Redis
        logger.info("🔴 初始化Redis连接...")
        await init_redis()
        
        # 测试AI服务连接
        logger.info("🤖 测试AI服务连接...")
        # 这里可以添加AI服务连接测试
        
        logger.info("✅ 应用启动完成")
        
    except Exception as e:
        logger.error(f"❌ 应用启动失败: {str(e)}")
        raise
    
    yield
    
    # 关闭时执行
    logger.info("🛑 关闭AI知识库应用...")
    logger.info("✅ 应用关闭完成")

# 创建FastAPI应用实例
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="AI驱动的智能知识库系统，支持对话式交互和智能内容处理",
    docs_url="/docs" if settings.debug else None,
    redoc_url="/redoc" if settings.debug else None,
    lifespan=lifespan
)

# 添加CORS中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 添加受信任主机中间件（生产环境）
if not settings.debug:
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=["localhost", "127.0.0.1", "*.yourdomain.com"]
    )

# 请求处理时间中间件
@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    """添加请求处理时间头"""
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    
    # 记录慢请求
    if process_time > 5.0:  # 超过5秒的请求
        logger.warning(
            f"慢请求: {request.method} {request.url.path} - {process_time:.2f}s"
        )
    
    return response

# 请求日志中间件
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """记录请求日志"""
    # 获取客户端IP
    client_ip = request.client.host if request.client else "unknown"
    
    # 记录请求开始
    logger.info(
        f"📥 {request.method} {request.url.path} - IP: {client_ip} - UA: {request.headers.get('user-agent', 'unknown')}"
    )
    
    try:
        response = await call_next(request)
        
        # 记录响应
        logger.info(
            f"📤 {request.method} {request.url.path} - Status: {response.status_code}"
        )
        
        return response
        
    except Exception as e:
        logger.error(
            f"❌ {request.method} {request.url.path} - Error: {str(e)}"
        )
        raise

# 全局异常处理器
@app.exception_handler(AIServiceError)
async def ai_service_exception_handler(request: Request, exc: AIServiceError):
    """AI服务异常处理"""
    logger.error(f"AI服务错误: {str(exc)}")
    return JSONResponse(
        status_code=503,
        content={
            "success": False,
            "message": "AI服务暂时不可用",
            "error": str(exc),
            "error_type": "ai_service_error"
        }
    )

@app.exception_handler(RateLimitError)
async def rate_limit_exception_handler(request: Request, exc: RateLimitError):
    """频率限制异常处理"""
    logger.warning(f"频率限制: {str(exc)}")
    return JSONResponse(
        status_code=429,
        content={
            "success": False,
            "message": "请求过于频繁，请稍后重试",
            "error": str(exc),
            "error_type": "rate_limit_error"
        }
    )

@app.exception_handler(AuthenticationError)
async def authentication_exception_handler(request: Request, exc: AuthenticationError):
    """认证异常处理"""
    logger.warning(f"认证失败: {str(exc)}")
    return JSONResponse(
        status_code=401,
        content={
            "success": False,
            "message": "认证失败，请重新登录",
            "error": str(exc),
            "error_type": "authentication_error"
        }
    )

@app.exception_handler(AuthorizationError)
async def authorization_exception_handler(request: Request, exc: AuthorizationError):
    """授权异常处理"""
    logger.warning(f"授权失败: {str(exc)}")
    return JSONResponse(
        status_code=403,
        content={
            "success": False,
            "message": "权限不足",
            "error": str(exc),
            "error_type": "authorization_error"
        }
    )

@app.exception_handler(ValidationError)
async def validation_exception_handler(request: Request, exc: ValidationError):
    """验证异常处理"""
    logger.warning(f"验证错误: {str(exc)}")
    return JSONResponse(
        status_code=422,
        content={
            "success": False,
            "message": "请求参数验证失败",
            "error": str(exc),
            "error_type": "validation_error"
        }
    )

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """HTTP异常处理"""
    logger.warning(f"HTTP异常: {exc.status_code} - {exc.detail}")
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "message": exc.detail,
            "error_type": "http_error"
        }
    )

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """通用异常处理"""
    logger.error(f"未处理的异常: {type(exc).__name__} - {str(exc)}")
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "message": "服务器内部错误" if not settings.debug else str(exc),
            "error_type": "internal_error"
        }
    )

# 健康检查端点
@app.get("/health")
async def health_check():
    """健康检查"""
    return {
        "status": "healthy",
        "app_name": settings.app_name,
        "version": settings.app_version,
        "timestamp": time.time()
    }

# 系统信息端点
@app.get("/info")
async def system_info():
    """系统信息"""
    return {
        "app_name": settings.app_name,
        "version": settings.app_version,
        "debug": settings.debug,
        "features": {
            "ai_service": True,
            "file_upload": True,
            "search": True,
            "visualization": True,
            "multi_user": True
        },
        "supported_file_types": settings.allowed_extensions,
        "tier_limits": {
            "free": settings.get_tier_limits("free"),
            "pro": settings.get_tier_limits("pro"),
            "enterprise": settings.get_tier_limits("enterprise")
        }
    }

# 根路径
@app.get("/")
async def root():
    """根路径"""
    return {
        "message": f"欢迎使用{settings.app_name}",
        "version": settings.app_version,
        "docs": "/docs" if settings.debug else "文档已禁用",
        "health": "/health"
    }

# 挂载静态文件（如果需要）
if Path("static").exists():
    app.mount("/static", StaticFiles(directory="static"), name="static")

# 挂载上传文件目录
if Path(settings.upload_dir).exists():
    app.mount("/uploads", StaticFiles(directory=settings.upload_dir), name="uploads")

# 包含API路由
app.include_router(api_router, prefix="/api/v1")

# 开发环境启动配置
if __name__ == "__main__":
    logger.info(f"🚀 启动开发服务器: http://{settings.host}:{settings.port}")
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        log_level=settings.log_level.lower(),
        access_log=True
    )