#!/usr/bin/env python3
"""带有Web界面的FastAPI应用"""

from fastapi import FastAPI
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import os

# 创建FastAPI应用
app = FastAPI(
    title="AI知识库系统",
    description="基于FastAPI和SiliconFlow的智能知识库管理系统",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# 添加CORS中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 创建静态文件目录
os.makedirs("static", exist_ok=True)
os.makedirs("uploads", exist_ok=True)

# 挂载静态文件
app.mount("/static", StaticFiles(directory="static"), name="static")

# HTML模板
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AI知识库系统</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
        }
        .container {
            background: white;
            border-radius: 20px;
            padding: 40px;
            box-shadow: 0 20px 40px rgba(0,0,0,0.1);
            text-align: center;
            max-width: 600px;
            width: 90%;
        }
        .logo {
            font-size: 3em;
            margin-bottom: 20px;
            color: #667eea;
        }
        h1 {
            color: #333;
            margin-bottom: 10px;
            font-size: 2.5em;
        }
        .subtitle {
            color: #666;
            margin-bottom: 30px;
            font-size: 1.2em;
        }
        .status {
            background: #4CAF50;
            color: white;
            padding: 10px 20px;
            border-radius: 25px;
            display: inline-block;
            margin-bottom: 30px;
            font-weight: bold;
        }
        .features {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }
        .feature {
            background: #f8f9fa;
            padding: 20px;
            border-radius: 10px;
            border-left: 4px solid #667eea;
        }
        .feature h3 {
            color: #333;
            margin-bottom: 10px;
        }
        .feature p {
            color: #666;
            font-size: 0.9em;
        }
        .links {
            display: flex;
            gap: 15px;
            justify-content: center;
            flex-wrap: wrap;
        }
        .link {
            background: #667eea;
            color: white;
            padding: 12px 24px;
            text-decoration: none;
            border-radius: 25px;
            transition: all 0.3s ease;
            font-weight: bold;
        }
        .link:hover {
            background: #5a6fd8;
            transform: translateY(-2px);
            box-shadow: 0 5px 15px rgba(102, 126, 234, 0.3);
        }
        .api-info {
            background: #e3f2fd;
            padding: 20px;
            border-radius: 10px;
            margin-top: 30px;
            border-left: 4px solid #2196F3;
        }
        .version {
            color: #999;
            font-size: 0.9em;
            margin-top: 20px;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="logo">🤖</div>
        <h1>AI知识库系统</h1>
        <p class="subtitle">基于FastAPI和SiliconFlow的智能知识库管理系统</p>
        
        <div class="status">✅ 系统运行正常</div>
        
        <div class="features">
            <div class="feature">
                <h3>📚 文档管理</h3>
                <p>智能文档上传、存储和管理</p>
            </div>
            <div class="feature">
                <h3>🔍 智能搜索</h3>
                <p>基于AI的语义搜索和检索</p>
            </div>
            <div class="feature">
                <h3>💬 AI对话</h3>
                <p>与知识库进行智能问答</p>
            </div>
            <div class="feature">
                <h3>👥 用户管理</h3>
                <p>多用户权限和访问控制</p>
            </div>
        </div>
        
        <div class="links">
            <a href="/docs" class="link">📖 API文档</a>
            <a href="/redoc" class="link">📋 ReDoc文档</a>
            <a href="/health" class="link">🏥 健康检查</a>
            <a href="/api/test" class="link">🧪 测试API</a>
        </div>
        
        <div class="api-info">
            <h3>🔗 API端点</h3>
            <p><strong>基础URL:</strong> http://localhost:8000</p>
            <p><strong>文档地址:</strong> http://localhost:8000/docs</p>
            <p><strong>健康检查:</strong> http://localhost:8000/health</p>
        </div>
        
        <div class="version">版本 1.0.0 | 技术栈: FastAPI + SiliconFlow + Redis + PostgreSQL</div>
    </div>
</body>
</html>
"""

@app.get("/", response_class=HTMLResponse)
async def root():
    """根路径 - 返回HTML界面"""
    return HTML_TEMPLATE

@app.get("/api")
async def api_info():
    """API信息"""
    return {
        "message": "欢迎使用AI知识库系统API",
        "version": "1.0.0",
        "docs": "/docs",
        "status": "running",
        "endpoints": {
            "root": "/",
            "api_info": "/api",
            "health": "/health",
            "test": "/api/test",
            "docs": "/docs",
            "redoc": "/redoc"
        }
    }

@app.get("/health")
async def health_check():
    """健康检查"""
    return {
        "status": "healthy",
        "service": "ai-knowledge-base",
        "version": "1.0.0",
        "timestamp": "2024-01-01T00:00:00Z",
        "components": {
            "web_server": "running",
            "api": "available",
            "static_files": "mounted"
        }
    }

@app.get("/api/test")
async def test_api():
    """测试API"""
    return {
        "message": "API正常工作",
        "timestamp": "2024-01-01T00:00:00Z",
        "test_data": {
            "string": "Hello, World!",
            "number": 42,
            "boolean": True,
            "array": [1, 2, 3, 4, 5],
            "object": {
                "nested": "value",
                "count": 100
            }
        }
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)