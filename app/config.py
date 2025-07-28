from pydantic import BaseSettings
from typing import List, Optional
import os
from pathlib import Path

class Settings(BaseSettings):
    """应用配置类"""
    
    # 应用基础配置
    app_name: str = "AI知识库"
    app_version: str = "1.0.0"
    debug: bool = True
    secret_key: str = "ai-knowledge-base-secret-key-2024"
    
    # 服务器配置
    host: str = "0.0.0.0"
    port: int = 8000
    
    # 数据库配置
    database_url: str = "postgresql://postgres:password@localhost:5432/ai_knowledge_base"
    redis_url: str = "redis://localhost:6379/0"
    
    # Elasticsearch配置
    elasticsearch_url: str = "http://localhost:9200"
    elasticsearch_index: str = "knowledge_base"
    
    # Qdrant向量数据库配置
    qdrant_url: str = "http://localhost:6333"
    qdrant_collection: str = "knowledge_vectors"
    
    # 硅基流动API配置
    siliconflow_api_key: str = "sk-zxujtfllwsoftjelqgzbdwfxmneaoifsvlzvzluntpigkgkr"
    siliconflow_base_url: str = "https://api.siliconflow.cn/v1"
    siliconflow_model: str = "deepseek-chat"
    
    # OpenAI API配置（备用）
    openai_api_key: Optional[str] = None
    openai_base_url: str = "https://api.openai.com/v1"
    openai_model: str = "gpt-3.5-turbo"
    
    # 文件存储配置
    upload_dir: str = "./uploads"
    max_file_size: int = 104857600  # 100MB
    allowed_extensions: str = ".pdf,.docx,.pptx,.xlsx,.txt,.md,.jpg,.png,.gif"
    
    # 用量限制配置
    free_tier_daily_limit: int = 50
    pro_tier_daily_limit: int = 500
    enterprise_tier_daily_limit: int = -1  # 无限制
    free_tier_file_size_mb: int = 10
    pro_tier_file_size_mb: int = 100
    enterprise_tier_file_size_mb: int = 1000
    
    # JWT配置
    jwt_secret_key: str = "jwt-secret-key-ai-knowledge-base-2024"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 1440  # 24小时
    
    # 邮件配置
    smtp_host: Optional[str] = None
    smtp_port: int = 587
    smtp_user: Optional[str] = None
    smtp_password: Optional[str] = None
    
    # 日志配置
    log_level: str = "INFO"
    log_file: str = "./logs/app.log"
    
    # CORS配置
    cors_origins: str = "http://localhost:3000,http://localhost:3001,http://127.0.0.1:3000,http://127.0.0.1:3001"
    
    # AI服务配置
    ai_request_timeout: int = 30  # 30秒超时
    ai_max_retries: int = 3
    ai_cache_ttl: int = 3600  # 1小时缓存
    
    # 批量处理配置
    batch_size: int = 10
    batch_timeout: int = 5  # 5秒
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # 确保上传目录存在
        Path(self.upload_dir).mkdir(parents=True, exist_ok=True)
        # 确保日志目录存在
        Path(self.log_file).parent.mkdir(parents=True, exist_ok=True)
    
    @property
    def database_url_sync(self) -> str:
        """同步数据库连接URL"""
        return self.database_url.replace("postgresql://", "postgresql+psycopg2://")
    
    @property
    def database_url_async(self) -> str:
        """异步数据库连接URL"""
        return self.database_url.replace("postgresql://", "postgresql+asyncpg://")
    
    def get_tier_limits(self, tier: str) -> dict:
        """获取用户等级限制"""
        limits = {
            "free": {
                "daily_requests": self.free_tier_daily_limit,
                "file_size_mb": self.free_tier_file_size_mb,
                "storage_gb": 1,
                "features": ["basic_analysis", "simple_search", "basic_chat"]
            },
            "pro": {
                "daily_requests": self.pro_tier_daily_limit,
                "file_size_mb": self.pro_tier_file_size_mb,
                "storage_gb": 50,
                "features": [
                    "advanced_analysis", "semantic_search", "advanced_chat",
                    "mind_map", "custom_classification", "batch_processing"
                ]
            },
            "enterprise": {
                "daily_requests": self.enterprise_tier_daily_limit,
                "file_size_mb": self.enterprise_tier_file_size_mb,
                "storage_gb": -1,  # 无限制
                "features": [
                    "all_features", "api_access", "custom_models",
                    "team_collaboration", "advanced_analytics", "priority_support"
                ]
            }
        }
        return limits.get(tier, limits["free"])
    
    def is_file_allowed(self, filename: str) -> bool:
        """检查文件扩展名是否允许"""
        ext = Path(filename).suffix.lower()
        extensions = self.allowed_extensions.split(',') if isinstance(self.allowed_extensions, str) else self.allowed_extensions
        return ext in extensions
    
    def get_cors_origins(self) -> List[str]:
        """获取CORS源列表"""
        if isinstance(self.cors_origins, str):
            return [origin.strip() for origin in self.cors_origins.split(',')]
        return self.cors_origins
    
    def get_ai_provider_config(self, provider: str = "siliconflow") -> dict:
        """获取AI服务提供商配置"""
        configs = {
            "siliconflow": {
                "api_key": self.siliconflow_api_key,
                "base_url": self.siliconflow_base_url,
                "model": self.siliconflow_model,
                "timeout": self.ai_request_timeout,
                "max_retries": self.ai_max_retries
            },
            "openai": {
                "api_key": self.openai_api_key,
                "base_url": self.openai_base_url,
                "model": self.openai_model,
                "timeout": self.ai_request_timeout,
                "max_retries": self.ai_max_retries
            }
        }
        return configs.get(provider, configs["siliconflow"])

# 创建全局设置实例
settings = Settings()

# 导出常用配置
__all__ = ["settings", "Settings"]