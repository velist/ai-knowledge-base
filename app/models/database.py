"""数据库模型定义"""

from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, Float, JSON, ForeignKey, Index
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from datetime import datetime
from typing import Optional
import uuid

from app.models.schemas import UserTier, RequestType, FileType

Base = declarative_base()

class User(Base):
    """用户模型"""
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String(36), unique=True, index=True, default=lambda: str(uuid.uuid4()))
    username = Column(String(50), unique=True, index=True, nullable=False)
    email = Column(String(100), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    full_name = Column(String(100))
    avatar_url = Column(String(500))
    tier = Column(String(20), default=UserTier.FREE.value, nullable=False)
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    last_login = Column(DateTime(timezone=True))
    
    # 关系
    knowledge_bases = relationship("KnowledgeBase", back_populates="owner", cascade="all, delete-orphan")
    files = relationship("File", back_populates="owner", cascade="all, delete-orphan")
    conversations = relationship("Conversation", back_populates="user", cascade="all, delete-orphan")
    usage_stats = relationship("UsageStats", back_populates="user", cascade="all, delete-orphan")
    
    # 索引
    __table_args__ = (
        Index('idx_user_tier_active', 'tier', 'is_active'),
        Index('idx_user_created', 'created_at'),
    )

class KnowledgeBase(Base):
    """知识库模型"""
    __tablename__ = "knowledge_bases"
    
    id = Column(Integer, primary_key=True, index=True)
    kb_id = Column(String(36), unique=True, index=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(100), nullable=False)
    description = Column(Text)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    is_public = Column(Boolean, default=False)
    file_count = Column(Integer, default=0)
    total_size = Column(Integer, default=0)  # 字节
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # 关系
    owner = relationship("User", back_populates="knowledge_bases")
    files = relationship("File", back_populates="knowledge_base", cascade="all, delete-orphan")
    conversations = relationship("Conversation", back_populates="knowledge_base", cascade="all, delete-orphan")
    
    # 索引
    __table_args__ = (
        Index('idx_kb_owner_public', 'owner_id', 'is_public'),
        Index('idx_kb_created', 'created_at'),
    )

class File(Base):
    """文件模型"""
    __tablename__ = "files"
    
    id = Column(Integer, primary_key=True, index=True)
    file_id = Column(String(36), unique=True, index=True, default=lambda: str(uuid.uuid4()))
    filename = Column(String(255), nullable=False)
    original_filename = Column(String(255), nullable=False)
    file_path = Column(String(500), nullable=False)
    file_type = Column(String(20), nullable=False)
    file_size = Column(Integer, nullable=False)  # 字节
    mime_type = Column(String(100))
    
    # 处理状态
    is_processed = Column(Boolean, default=False)
    processing_status = Column(String(20), default="pending")  # pending, processing, completed, failed
    processing_error = Column(Text)
    
    # 内容信息
    content_preview = Column(Text)  # 前500字符预览
    page_count = Column(Integer)
    word_count = Column(Integer)
    language = Column(String(10))
    
    # 向量化信息
    vector_count = Column(Integer, default=0)
    embedding_model = Column(String(50))
    
    # 关联
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    knowledge_base_id = Column(Integer, ForeignKey("knowledge_bases.id"), nullable=False)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # 关系
    owner = relationship("User", back_populates="files")
    knowledge_base = relationship("KnowledgeBase", back_populates="files")
    
    # 索引
    __table_args__ = (
        Index('idx_file_owner_kb', 'owner_id', 'knowledge_base_id'),
        Index('idx_file_type_status', 'file_type', 'processing_status'),
        Index('idx_file_created', 'created_at'),
    )

class Conversation(Base):
    """对话模型"""
    __tablename__ = "conversations"
    
    id = Column(Integer, primary_key=True, index=True)
    conversation_id = Column(String(36), unique=True, index=True, default=lambda: str(uuid.uuid4()))
    title = Column(String(200))
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    knowledge_base_id = Column(Integer, ForeignKey("knowledge_bases.id"))
    
    # 对话配置
    model_name = Column(String(50))
    temperature = Column(Float, default=0.7)
    max_tokens = Column(Integer, default=2000)
    
    # 统计信息
    message_count = Column(Integer, default=0)
    total_tokens = Column(Integer, default=0)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # 关系
    user = relationship("User", back_populates="conversations")
    knowledge_base = relationship("KnowledgeBase", back_populates="conversations")
    messages = relationship("Message", back_populates="conversation", cascade="all, delete-orphan")
    
    # 索引
    __table_args__ = (
        Index('idx_conv_user_kb', 'user_id', 'knowledge_base_id'),
        Index('idx_conv_updated', 'updated_at'),
    )

class Message(Base):
    """消息模型"""
    __tablename__ = "messages"
    
    id = Column(Integer, primary_key=True, index=True)
    message_id = Column(String(36), unique=True, index=True, default=lambda: str(uuid.uuid4()))
    conversation_id = Column(Integer, ForeignKey("conversations.id"), nullable=False)
    
    # 消息内容
    role = Column(String(20), nullable=False)  # user, assistant, system
    content = Column(Text, nullable=False)
    content_type = Column(String(20), default="text")  # text, image, file
    
    # AI相关信息
    model_name = Column(String(50))
    prompt_tokens = Column(Integer)
    completion_tokens = Column(Integer)
    total_tokens = Column(Integer)
    
    # 检索相关
    retrieved_chunks = Column(JSON)  # 检索到的文档片段
    similarity_scores = Column(JSON)  # 相似度分数
    
    # 元数据
    metadata = Column(JSON)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # 关系
    conversation = relationship("Conversation", back_populates="messages")
    
    # 索引
    __table_args__ = (
        Index('idx_msg_conv_role', 'conversation_id', 'role'),
        Index('idx_msg_created', 'created_at'),
    )

class UsageStats(Base):
    """使用统计模型"""
    __tablename__ = "usage_stats"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    date = Column(DateTime(timezone=True), nullable=False)
    
    # API调用统计
    api_calls = Column(Integer, default=0)
    chat_requests = Column(Integer, default=0)
    embedding_requests = Column(Integer, default=0)
    
    # Token使用统计
    prompt_tokens = Column(Integer, default=0)
    completion_tokens = Column(Integer, default=0)
    total_tokens = Column(Integer, default=0)
    
    # 文件处理统计
    files_uploaded = Column(Integer, default=0)
    files_processed = Column(Integer, default=0)
    storage_used = Column(Integer, default=0)  # 字节
    
    # 搜索统计
    search_requests = Column(Integer, default=0)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # 关系
    user = relationship("User", back_populates="usage_stats")
    
    # 索引
    __table_args__ = (
        Index('idx_usage_user_date', 'user_id', 'date'),
        Index('idx_usage_date', 'date'),
    )

class APIKey(Base):
    """API密钥模型"""
    __tablename__ = "api_keys"
    
    id = Column(Integer, primary_key=True, index=True)
    key_id = Column(String(36), unique=True, index=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    name = Column(String(100), nullable=False)
    key_hash = Column(String(255), nullable=False)  # 哈希后的密钥
    key_prefix = Column(String(10), nullable=False)  # 密钥前缀，用于显示
    
    # 权限和限制
    permissions = Column(JSON)  # 权限列表
    rate_limit = Column(Integer)  # 每分钟请求限制
    
    # 状态
    is_active = Column(Boolean, default=True)
    last_used = Column(DateTime(timezone=True))
    usage_count = Column(Integer, default=0)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    expires_at = Column(DateTime(timezone=True))
    
    # 索引
    __table_args__ = (
        Index('idx_apikey_user_active', 'user_id', 'is_active'),
        Index('idx_apikey_hash', 'key_hash'),
    )

class SystemConfig(Base):
    """系统配置模型"""
    __tablename__ = "system_configs"
    
    id = Column(Integer, primary_key=True, index=True)
    key = Column(String(100), unique=True, nullable=False)
    value = Column(JSON, nullable=False)
    description = Column(Text)
    category = Column(String(50))
    is_public = Column(Boolean, default=False)  # 是否可以通过API获取
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # 索引
    __table_args__ = (
        Index('idx_config_category', 'category'),
        Index('idx_config_public', 'is_public'),
    )

class AuditLog(Base):
    """审计日志模型"""
    __tablename__ = "audit_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    action = Column(String(50), nullable=False)
    resource_type = Column(String(50))
    resource_id = Column(String(100))
    
    # 请求信息
    ip_address = Column(String(45))
    user_agent = Column(String(500))
    request_method = Column(String(10))
    request_path = Column(String(500))
    
    # 详细信息
    details = Column(JSON)
    status = Column(String(20))  # success, failed, error
    error_message = Column(Text)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # 索引
    __table_args__ = (
        Index('idx_audit_user_action', 'user_id', 'action'),
        Index('idx_audit_resource', 'resource_type', 'resource_id'),
        Index('idx_audit_created', 'created_at'),
        Index('idx_audit_status', 'status'),
    )

# 导出所有模型
__all__ = [
    "Base",
    "User",
    "KnowledgeBase",
    "File",
    "Conversation",
    "Message",
    "UsageStats",
    "APIKey",
    "SystemConfig",
    "AuditLog"
]