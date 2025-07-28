"""API路由模块"""

from fastapi import APIRouter

from app.api.v1 import auth, users, knowledge_bases, files, search, chat, admin

# 创建API路由器
api_router = APIRouter()

# 注册v1版本的路由
api_router.include_router(
    auth.router,
    prefix="/v1/auth",
    tags=["认证"]
)

api_router.include_router(
    users.router,
    prefix="/v1/users",
    tags=["用户"]
)

api_router.include_router(
    knowledge_bases.router,
    prefix="/v1/knowledge-bases",
    tags=["知识库"]
)

api_router.include_router(
    files.router,
    prefix="/v1/files",
    tags=["文件"]
)

api_router.include_router(
    search.router,
    prefix="/v1/search",
    tags=["搜索"]
)

api_router.include_router(
    chat.router,
    prefix="/v1/chat",
    tags=["对话"]
)

api_router.include_router(
    admin.router,
    prefix="/v1/admin",
    tags=["管理"]
)

# 导出
__all__ = ["api_router"]