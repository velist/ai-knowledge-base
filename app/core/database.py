"""数据库连接和初始化模块"""

from sqlalchemy import create_engine, MetaData
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from contextlib import asynccontextmanager
from typing import AsyncGenerator
from loguru import logger

from app.config import settings
from app.core.exceptions import DatabaseError

# 创建同步数据库引擎
engine = create_engine(
    settings.database_url_sync,
    pool_pre_ping=True,
    pool_recycle=300,
    echo=settings.debug
)

# 创建异步数据库引擎
async_engine = create_async_engine(
    settings.database_url_async,
    pool_pre_ping=True,
    pool_recycle=300,
    echo=settings.debug
)

# 创建会话工厂
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

# 创建异步会话工厂
AsyncSessionLocal = async_sessionmaker(
    async_engine,
    class_=AsyncSession,
    expire_on_commit=False
)

# 创建基础模型类
Base = declarative_base()

# 元数据
metadata = MetaData()

async def init_db():
    """初始化数据库"""
    try:
        # 导入所有模型以确保它们被注册
        from app.models import database_models
        
        # 创建所有表
        async with async_engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        
        logger.info("✅ 数据库初始化完成")
        
    except Exception as e:
        logger.error(f"❌ 数据库初始化失败: {str(e)}")
        raise DatabaseError(f"数据库初始化失败: {str(e)}")

async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    """获取异步数据库会话"""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception as e:
            await session.rollback()
            logger.error(f"数据库会话错误: {str(e)}")
            raise DatabaseError(f"数据库操作失败: {str(e)}")
        finally:
            await session.close()

def get_sync_session():
    """获取同步数据库会话"""
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception as e:
        db.rollback()
        logger.error(f"数据库会话错误: {str(e)}")
        raise DatabaseError(f"数据库操作失败: {str(e)}")
    finally:
        db.close()

@asynccontextmanager
async def get_db_session():
    """数据库会话上下文管理器"""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception as e:
            await session.rollback()
            logger.error(f"数据库事务错误: {str(e)}")
            raise DatabaseError(f"数据库事务失败: {str(e)}")
        finally:
            await session.close()

async def check_db_connection():
    """检查数据库连接"""
    try:
        async with async_engine.begin() as conn:
            await conn.execute("SELECT 1")
        logger.info("✅ 数据库连接正常")
        return True
    except Exception as e:
        logger.error(f"❌ 数据库连接失败: {str(e)}")
        return False

async def close_db_connections():
    """关闭数据库连接"""
    try:
        await async_engine.dispose()
        engine.dispose()
        logger.info("✅ 数据库连接已关闭")
    except Exception as e:
        logger.error(f"❌ 关闭数据库连接失败: {str(e)}")

# 导出
__all__ = [
    "Base",
    "engine", 
    "async_engine",
    "SessionLocal",
    "AsyncSessionLocal",
    "metadata",
    "init_db",
    "get_async_session",
    "get_sync_session",
    "get_db_session",
    "check_db_connection",
    "close_db_connections"
]