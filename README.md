# AI知识库系统

基于FastAPI和硅基流动API的智能知识库管理系统，支持文档上传、智能搜索、AI对话等功能。

## 🌟 功能特性

### 🚀 核心功能
- **文档管理**: 支持PDF、DOCX、PPTX、XLSX、TXT等多种格式文档上传和管理
- **智能搜索**: 基于Elasticsearch和向量搜索的混合搜索引擎
- **AI对话**: 集成硅基流动API，支持基于知识库的智能问答
- **用户管理**: 完整的用户注册、登录、权限管理系统
- **多租户**: 支持个人和团队知识库，灵活的权限控制
- **云端部署**: 支持Vercel、Docker等多种部署方式

### 🎯 技术特性
- **异步架构**: 基于FastAPI的高性能异步Web框架
- **AI集成**: 集成硅基流动API，支持对话、嵌入、重排序等功能
- **搜索引擎**: Elasticsearch + Qdrant向量数据库的混合搜索
- **缓存系统**: Redis缓存提升响应速度
- **文件处理**: 自动提取文档内容，生成向量嵌入
- **速率限制**: 基于用户等级的API调用限制

### 👥 用户等级
- **免费版**: 3个知识库，50个文件，500MB存储
- **专业版**: 20个知识库，500个文件，5GB存储
- **企业版**: 无限制使用

## 🚀 在线演示

- **用户前端**: [https://ai-knowledge-base.vercel.app](https://ai-knowledge-base.vercel.app)
- **管理后台**: [https://ai-knowledge-base.vercel.app/admin](https://ai-knowledge-base.vercel.app/admin)
- **默认管理员**: `vee5208` / `forxy131`

## 📦 部署方式

### 🌐 Vercel云端部署（推荐）

[![Deploy with Vercel](https://vercel.com/button)](https://vercel.com/new/clone?repository-url=https://github.com/your-username/ai-knowledge-base)

1. **一键部署**
   - 点击上方按钮
   - 连接GitHub账户
   - 配置环境变量
   - 自动部署完成

2. **手动部署**
   ```bash
   # 安装Vercel CLI
   npm i -g vercel
   
   # 登录并部署
   vercel login
   vercel --prod
   ```

详见：[Vercel部署指南](VERCEL_DEPLOYMENT.md)

### 🐳 Docker部署

```bash
# 使用Docker Compose
docker-compose up -d

# 或使用单独的Docker
docker build -t ai-knowledge-base .
docker run -p 8000:8000 -p 8003:8003 ai-knowledge-base
```

### 💻 本地开发

#### 环境要求
- Python 3.8+
- Redis
- PostgreSQL (可选，默认使用SQLite)
- Elasticsearch (可选)
- Qdrant (可选)

#### 安装步骤

1. **克隆项目**
   ```bash
   git clone <repository-url>
   cd ai-knowledge-base
   ```

2. **安装依赖**
   ```bash
   pip install -r requirements.txt
   ```

3. **配置环境**
   ```bash
   cp .env.example .env
   # 编辑 .env 文件
   ```

   创建 `.env` 文件：
   ```env
   # 应用配置
   APP_NAME=AI知识库
   DEBUG=true
   SECRET_KEY=your-secret-key

   # 数据库配置
   DATABASE_URL=sqlite:///./ai_knowledge_base.db
   REDIS_URL=redis://localhost:6379/0

   # AI服务配置
   SILICONFLOW_API_KEY=sk-zxujtfllwsoftjelqgzbdwfxmneaoifsvlzvzluntpigkgkr
   SILICONFLOW_BASE_URL=https://api.siliconflow.cn/v1
   SILICONFLOW_MODEL=deepseek-chat

   # 搜索服务配置
   ELASTICSEARCH_URL=http://localhost:9200
   QDRANT_URL=http://localhost:6333
   ```

4. **启动服务**
   ```bash
   # Windows
   start.bat
   
   # Linux/Mac
   chmod +x start.sh
   ./start.sh
   
   # 或手动启动
   python deploy.py
   ```

   或者直接运行：
   ```bash
   python main.py
   ```

## 🌍 访问地址

### 本地开发
- 用户前端: http://localhost:8000
- 管理后台: http://localhost:8003
- API文档: http://localhost:8000/docs
- 健康检查: http://localhost:8000/health

### 生产环境
- 用户前端: https://your-domain.com
- 管理后台: https://your-domain.com/admin
- API文档: https://your-domain.com/docs

## 🔐 默认账户

**管理员账户**:
- 用户名: `vee5208`
- 密码: `forxy131`

> ⚠️ **安全提示**: 部署后请立即修改默认密码！

## API文档

### 认证相关
- `POST /api/v1/auth/register` - 用户注册
- `POST /api/v1/auth/login` - 用户登录
- `POST /api/v1/auth/refresh` - 刷新令牌
- `POST /api/v1/auth/logout` - 用户登出

### 知识库管理
- `GET /api/v1/knowledge-bases` - 获取知识库列表
- `POST /api/v1/knowledge-bases` - 创建知识库
- `GET /api/v1/knowledge-bases/{kb_id}` - 获取知识库详情
- `PUT /api/v1/knowledge-bases/{kb_id}` - 更新知识库
- `DELETE /api/v1/knowledge-bases/{kb_id}` - 删除知识库

### 文件管理
- `POST /api/v1/files/upload` - 上传文件
- `GET /api/v1/files` - 获取文件列表
- `GET /api/v1/files/{file_id}` - 获取文件详情
- `DELETE /api/v1/files/{file_id}` - 删除文件

### 搜索功能
- `POST /api/v1/search/knowledge-base` - 搜索知识库
- `GET /api/v1/search/suggestions` - 获取搜索建议
- `POST /api/v1/search/ai-enhanced` - AI增强搜索

### 对话功能
- `POST /api/v1/chat/conversations` - 创建对话
- `GET /api/v1/chat/conversations` - 获取对话列表
- `POST /api/v1/chat/conversations/{conv_id}/chat` - 发送消息
- `GET /api/v1/chat/conversations/{conv_id}/messages` - 获取消息历史

## 项目结构

```
ai-knowledge-base/
├── app/
│   ├── api/                    # API路由
│   │   ├── __init__.py
│   │   └── v1/
│   │       ├── auth.py         # 认证相关API
│   │       ├── users.py        # 用户管理API
│   │       ├── knowledge_bases.py  # 知识库API
│   │       ├── files.py        # 文件管理API
│   │       ├── search.py       # 搜索API
│   │       ├── chat.py         # 对话API
│   │       └── admin.py        # 管理员API
│   ├── core/                   # 核心模块
│   │   ├── auth.py            # 认证和授权
│   │   ├── database.py        # 数据库连接
│   │   ├── redis_client.py    # Redis客户端
│   │   └── exceptions.py      # 自定义异常
│   ├── models/                # 数据模型
│   │   ├── database.py        # SQLAlchemy模型
│   │   └── schemas.py         # Pydantic模型
│   ├── services/              # 业务服务
│   │   ├── ai_service.py      # AI服务管理
│   │   ├── file_service.py    # 文件处理服务
│   │   └── search_service.py  # 搜索服务
│   └── config.py              # 配置管理
├── main.py                    # 应用入口
├── run.py                     # 启动脚本
├── requirements.txt           # 依赖包
└── README.md                  # 项目文档
```

## 配置说明

### 数据库配置

**SQLite (默认)**
```env
DATABASE_URL=sqlite:///./ai_knowledge_base.db
```

**PostgreSQL**
```env
DATABASE_URL=postgresql://username:password@localhost:5432/ai_knowledge_base
```

### AI服务配置

系统已配置硅基流动API密钥，支持以下功能：
- 对话生成 (deepseek-chat)
- 文本嵌入 (BAAI/bge-large-zh-v1.5)
- 文档重排序 (BAAI/bge-reranker-large)

### 搜索服务配置

**Elasticsearch (可选)**
```env
ELASTICSEARCH_URL=http://localhost:9200
```

**Qdrant向量数据库 (可选)**
```env
QDRANT_URL=http://localhost:6333
```

## 使用示例

### 1. 用户注册和登录

```python
import httpx

# 注册用户
response = httpx.post("http://localhost:8000/api/v1/auth/register", json={
    "username": "testuser",
    "email": "test@example.com",
    "password": "password123",
    "full_name": "测试用户"
})

# 登录获取令牌
response = httpx.post("http://localhost:8000/api/v1/auth/login", data={
    "username": "testuser",
    "password": "password123"
})
token = response.json()["access_token"]
```

### 2. 创建知识库

```python
headers = {"Authorization": f"Bearer {token}"}

response = httpx.post(
    "http://localhost:8000/api/v1/knowledge-bases",
    headers=headers,
    json={
        "name": "我的知识库",
        "description": "这是一个测试知识库",
        "is_public": False
    }
)
kb_id = response.json()["knowledge_base_id"]
```

### 3. 上传文件

```python
with open("document.pdf", "rb") as f:
    files = {"file": f}
    data = {"knowledge_base_id": kb_id}
    
    response = httpx.post(
        "http://localhost:8000/api/v1/files/upload",
        headers=headers,
        files=files,
        data=data
    )
```

### 4. 搜索知识库

```python
response = httpx.post(
    "http://localhost:8000/api/v1/search/knowledge-base",
    headers=headers,
    json={
        "query": "人工智能的发展历史",
        "knowledge_base_ids": [kb_id],
        "search_type": "hybrid",
        "limit": 10
    }
)
results = response.json()["results"]
```

### 5. AI对话

```python
# 创建对话
response = httpx.post(
    "http://localhost:8000/api/v1/chat/conversations",
    headers=headers,
    json={
        "title": "AI咨询",
        "knowledge_base_ids": [kb_id]
    }
)
conv_id = response.json()["conversation_id"]

# 发送消息
response = httpx.post(
    f"http://localhost:8000/api/v1/chat/conversations/{conv_id}/chat",
    headers=headers,
    json={
        "content": "请介绍一下人工智能的发展历史",
        "use_knowledge_base": True
    }
)
ai_response = response.json()["ai_response"]
```

## 开发指南

### 添加新的API端点

1. 在 `app/api/v1/` 目录下创建或修改路由文件
2. 在 `app/api/__init__.py` 中注册新路由
3. 添加相应的数据模型到 `app/models/schemas.py`
4. 实现业务逻辑到 `app/services/` 目录

### 添加新的AI功能

1. 在 `app/services/ai_service.py` 中添加新方法
2. 配置相应的模型和参数
3. 在API路由中调用新功能

### 数据库迁移

```bash
# 生成迁移文件
alembic revision --autogenerate -m "描述变更"

# 执行迁移
alembic upgrade head
```

## 部署指南

### Docker部署

```dockerfile
FROM python:3.9-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
EXPOSE 8000

CMD ["python", "run.py"]
```

### 生产环境配置

```env
DEBUG=false
DATABASE_URL=postgresql://user:pass@db:5432/ai_kb
REDIS_URL=redis://redis:6379/0
SECRET_KEY=your-production-secret-key
```

## 故障排除

### 常见问题

1. **AI服务调用失败**
   - 检查API密钥是否正确
   - 确认网络连接正常
   - 查看日志文件获取详细错误信息

2. **文件上传失败**
   - 检查文件大小是否超过限制
   - 确认文件格式是否支持
   - 检查上传目录权限

3. **搜索功能异常**
   - 确认Elasticsearch服务运行正常
   - 检查索引是否创建成功
   - 验证向量数据库连接

### 日志查看

```bash
# 查看应用日志
tail -f logs/app.log

# 查看错误日志
grep ERROR logs/app.log
```

## 📚 文档

- [部署指南](DEPLOYMENT.md) - 详细的部署说明
- [Vercel部署](VERCEL_DEPLOYMENT.md) - Vercel云端部署
- [API文档](http://localhost:8000/docs) - 接口文档
- [管理后台](http://localhost:8003) - 后台管理

## 🤝 贡献指南

1. Fork 项目
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 创建 Pull Request

## 📄 许可证

MIT License - 详见 [LICENSE](LICENSE) 文件

## 🆘 技术支持

- 📧 邮箱: support@example.com
- 💬 QQ群: 123456789
- 🐛 问题反馈: [GitHub Issues](https://github.com/your-username/ai-knowledge-base/issues)

---

**⭐ 如果这个项目对您有帮助，请给我们一个星标！**

**注意**: 本项目已配置硅基流动API密钥，可直接使用AI功能。请妥善保管API密钥，避免泄露。