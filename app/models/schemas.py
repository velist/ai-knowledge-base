from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Any, Union
from datetime import datetime
from enum import Enum

class UserTier(str, Enum):
    """用户等级枚举"""
    FREE = "free"
    PRO = "pro"
    ENTERPRISE = "enterprise"

class RequestType(str, Enum):
    """请求类型枚举"""
    CONTENT_ANALYSIS = "content_analysis"
    CLASSIFICATION = "classification"
    SUMMARIZATION = "summarization"
    QA_RESPONSE = "qa_response"
    TRANSLATION = "translation"
    CREATIVE_WRITING = "creative_writing"
    CODE_GENERATION = "code_generation"
    MIND_MAP = "mind_map"
    KNOWLEDGE_GRAPH = "knowledge_graph"

class FileType(str, Enum):
    """文件类型枚举"""
    PDF = "pdf"
    DOCX = "docx"
    PPTX = "pptx"
    XLSX = "xlsx"
    TXT = "txt"
    MD = "md"
    IMAGE = "image"
    URL = "url"

# 用户相关模型
class UserBase(BaseModel):
    """用户基础模型"""
    email: str = Field(..., description="用户邮箱")
    username: str = Field(..., min_length=3, max_length=50, description="用户名")
    full_name: Optional[str] = Field(None, max_length=100, description="全名")
    tier: UserTier = Field(UserTier.FREE, description="用户等级")
    is_active: bool = Field(True, description="是否激活")

class UserCreate(UserBase):
    """创建用户模型"""
    password: str = Field(..., min_length=6, description="密码")

class UserUpdate(BaseModel):
    """更新用户模型"""
    username: Optional[str] = Field(None, min_length=3, max_length=50)
    full_name: Optional[str] = Field(None, max_length=100)
    tier: Optional[UserTier] = None
    is_active: Optional[bool] = None

class User(UserBase):
    """用户模型"""
    id: int
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

class UserLogin(BaseModel):
    """用户登录模型"""
    email: str = Field(..., description="邮箱")
    password: str = Field(..., description="密码")

# AI请求相关模型
class AIRequest(BaseModel):
    """AI请求模型"""
    user_id: str = Field(..., description="用户ID")
    user_tier: UserTier = Field(..., description="用户等级")
    request_type: RequestType = Field(..., description="请求类型")
    content: str = Field(..., min_length=1, max_length=10000, description="请求内容")
    system_prompt: Optional[str] = Field(None, max_length=1000, description="系统提示")
    temperature: float = Field(0.7, ge=0.0, le=2.0, description="温度参数")
    max_tokens: int = Field(2000, ge=1, le=4000, description="最大token数")
    context: Optional[Dict[str, Any]] = Field(None, description="上下文信息")
    
    @validator('temperature')
    def validate_temperature(cls, v):
        if not 0.0 <= v <= 2.0:
            raise ValueError('温度参数必须在0.0到2.0之间')
        return v

class AIResponse(BaseModel):
    """AI响应模型"""
    content: str = Field(..., description="响应内容")
    provider: str = Field(..., description="服务提供商")
    tokens_used: int = Field(0, description="使用的token数")
    request_type: RequestType = Field(..., description="请求类型")
    processing_time: Optional[float] = Field(None, description="处理时间（秒）")
    error: Optional[str] = Field(None, description="错误信息")
    metadata: Optional[Dict[str, Any]] = Field(None, description="元数据")

# 文件相关模型
class FileBase(BaseModel):
    """文件基础模型"""
    filename: str = Field(..., description="文件名")
    file_type: FileType = Field(..., description="文件类型")
    file_size: int = Field(..., ge=0, description="文件大小（字节）")
    title: Optional[str] = Field(None, max_length=200, description="文件标题")
    description: Optional[str] = Field(None, max_length=1000, description="文件描述")
    tags: List[str] = Field(default_factory=list, description="标签列表")
    category: Optional[str] = Field(None, max_length=100, description="分类")

class FileCreate(FileBase):
    """创建文件模型"""
    content: Optional[str] = Field(None, description="文件内容")
    url: Optional[str] = Field(None, description="文件URL")
    
class FileUpdate(BaseModel):
    """更新文件模型"""
    title: Optional[str] = Field(None, max_length=200)
    description: Optional[str] = Field(None, max_length=1000)
    tags: Optional[List[str]] = None
    category: Optional[str] = Field(None, max_length=100)
    content: Optional[str] = None

class File(FileBase):
    """文件模型"""
    id: int
    user_id: int
    file_path: str
    content_hash: Optional[str] = None
    processed: bool = False
    ai_summary: Optional[str] = None
    ai_keywords: List[str] = Field(default_factory=list)
    ai_category: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

# 知识库相关模型
class KnowledgeBase(BaseModel):
    """知识库模型"""
    id: int
    user_id: int
    name: str
    description: Optional[str] = None
    is_public: bool = False
    file_count: int = 0
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

class KnowledgeBaseCreate(BaseModel):
    """创建知识库模型"""
    name: str = Field(..., min_length=1, max_length=100, description="知识库名称")
    description: Optional[str] = Field(None, max_length=500, description="知识库描述")
    is_public: bool = Field(False, description="是否公开")

class KnowledgeBaseUpdate(BaseModel):
    """更新知识库模型"""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    is_public: Optional[bool] = None

# 对话相关模型
class ConversationBase(BaseModel):
    """对话基础模型"""
    title: Optional[str] = Field(None, max_length=200, description="对话标题")
    context: Optional[Dict[str, Any]] = Field(None, description="对话上下文")

class ConversationCreate(ConversationBase):
    """创建对话模型"""
    knowledge_base_id: Optional[int] = Field(None, description="关联的知识库ID")

class Conversation(ConversationBase):
    """对话模型"""
    id: int
    user_id: int
    knowledge_base_id: Optional[int] = None
    message_count: int = 0
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

class MessageBase(BaseModel):
    """消息基础模型"""
    content: str = Field(..., min_length=1, max_length=10000, description="消息内容")
    role: str = Field(..., description="角色：user或assistant")
    message_type: Optional[str] = Field("text", description="消息类型")
    metadata: Optional[Dict[str, Any]] = Field(None, description="元数据")

class MessageCreate(MessageBase):
    """创建消息模型"""
    conversation_id: int = Field(..., description="对话ID")

class Message(MessageBase):
    """消息模型"""
    id: int
    conversation_id: int
    tokens_used: int = 0
    processing_time: Optional[float] = None
    created_at: datetime
    
    class Config:
        from_attributes = True

# 搜索相关模型
class SearchRequest(BaseModel):
    """搜索请求模型"""
    query: str = Field(..., min_length=1, max_length=500, description="搜索查询")
    knowledge_base_id: Optional[int] = Field(None, description="知识库ID")
    file_types: Optional[List[FileType]] = Field(None, description="文件类型过滤")
    categories: Optional[List[str]] = Field(None, description="分类过滤")
    tags: Optional[List[str]] = Field(None, description="标签过滤")
    limit: int = Field(10, ge=1, le=100, description="返回结果数量")
    offset: int = Field(0, ge=0, description="偏移量")
    search_type: str = Field("hybrid", description="搜索类型：semantic, keyword, hybrid")

class SearchResult(BaseModel):
    """搜索结果模型"""
    file_id: int
    filename: str
    title: Optional[str] = None
    content_snippet: str
    score: float
    file_type: FileType
    category: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    created_at: datetime
    highlight: Optional[str] = None

class SearchResponse(BaseModel):
    """搜索响应模型"""
    results: List[SearchResult]
    total: int
    query: str
    search_type: str
    processing_time: float
    suggestions: Optional[List[str]] = None

# 分析相关模型
class ContentAnalysisRequest(BaseModel):
    """内容分析请求模型"""
    content: str = Field(..., min_length=1, description="待分析内容")
    analysis_types: List[str] = Field(
        default_factory=lambda: ["summary", "keywords", "category"],
        description="分析类型列表"
    )
    language: str = Field("zh", description="内容语言")

class ContentAnalysisResponse(BaseModel):
    """内容分析响应模型"""
    summary: Optional[str] = None
    keywords: List[str] = Field(default_factory=list)
    category: Optional[str] = None
    sentiment: Optional[str] = None
    entities: List[Dict[str, Any]] = Field(default_factory=list)
    topics: List[str] = Field(default_factory=list)
    language: str = "zh"
    confidence: float = 0.0

# 可视化相关模型
class MindMapNode(BaseModel):
    """思维导图节点模型"""
    id: str
    text: str
    level: int = 0
    children: List['MindMapNode'] = Field(default_factory=list)
    metadata: Optional[Dict[str, Any]] = None

class MindMapResponse(BaseModel):
    """思维导图响应模型"""
    root: MindMapNode
    title: str
    description: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.now)

class KnowledgeGraphNode(BaseModel):
    """知识图谱节点模型"""
    id: str
    label: str
    type: str
    properties: Dict[str, Any] = Field(default_factory=dict)

class KnowledgeGraphEdge(BaseModel):
    """知识图谱边模型"""
    source: str
    target: str
    relation: str
    weight: float = 1.0
    properties: Dict[str, Any] = Field(default_factory=dict)

class KnowledgeGraphResponse(BaseModel):
    """知识图谱响应模型"""
    nodes: List[KnowledgeGraphNode]
    edges: List[KnowledgeGraphEdge]
    title: str
    description: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.now)

# 用量统计模型
class UsageStats(BaseModel):
    """用量统计模型"""
    user_id: int
    date: datetime
    requests_count: int = 0
    tokens_used: int = 0
    files_processed: int = 0
    storage_used: int = 0  # 字节
    provider_usage: Dict[str, int] = Field(default_factory=dict)

class UsageSummary(BaseModel):
    """用量汇总模型"""
    daily_requests: int
    daily_tokens: int
    monthly_requests: int
    monthly_tokens: int
    storage_used: int
    tier_limits: Dict[str, Any]
    remaining_requests: int
    remaining_tokens: int

# API响应模型
class APIResponse(BaseModel):
    """通用API响应模型"""
    success: bool = True
    message: str = "操作成功"
    data: Optional[Any] = None
    error: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.now)

class PaginatedResponse(BaseModel):
    """分页响应模型"""
    items: List[Any]
    total: int
    page: int
    size: int
    pages: int

# Token相关模型
class Token(BaseModel):
    """Token模型"""
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: User

class TokenData(BaseModel):
    """Token数据模型"""
    user_id: Optional[int] = None
    email: Optional[str] = None

# 更新MindMapNode的前向引用
MindMapNode.model_rebuild()

# 导出所有模型
__all__ = [
    # 枚举
    "UserTier", "RequestType", "FileType",
    # 用户模型
    "UserBase", "UserCreate", "UserUpdate", "User", "UserLogin",
    # AI相关模型
    "AIRequest", "AIResponse",
    # 文件模型
    "FileBase", "FileCreate", "FileUpdate", "File",
    # 知识库模型
    "KnowledgeBase", "KnowledgeBaseCreate", "KnowledgeBaseUpdate",
    # 对话模型
    "ConversationBase", "ConversationCreate", "Conversation",
    "MessageBase", "MessageCreate", "Message",
    # 搜索模型
    "SearchRequest", "SearchResult", "SearchResponse",
    # 分析模型
    "ContentAnalysisRequest", "ContentAnalysisResponse",
    # 可视化模型
    "MindMapNode", "MindMapResponse",
    "KnowledgeGraphNode", "KnowledgeGraphEdge", "KnowledgeGraphResponse",
    # 用量模型
    "UsageStats", "UsageSummary",
    # 通用模型
    "APIResponse", "PaginatedResponse", "Token", "TokenData"
]