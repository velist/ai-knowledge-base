# Vercel部署入口文件 - 用户前端
from fastapi import FastAPI, Request, HTTPException, Form, Depends
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
import os
import json
from datetime import datetime
from typing import Optional, List, Dict, Any
import hashlib
import secrets

# 创建FastAPI应用
app = FastAPI(
    title="AI知识库系统",
    description="智能知识库管理系统 - 用户前端",
    version="1.0.0"
)

# CORS配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 模拟数据存储
knowledge_bases = [
    {
        "id": 1,
        "name": "技术文档库",
        "description": "包含各种技术文档和API参考",
        "document_count": 156,
        "created_at": "2024-01-15",
        "status": "active"
    },
    {
        "id": 2,
        "name": "产品手册",
        "description": "产品使用说明和操作指南",
        "document_count": 89,
        "created_at": "2024-01-20",
        "status": "active"
    },
    {
        "id": 3,
        "name": "FAQ知识库",
        "description": "常见问题解答集合",
        "document_count": 234,
        "created_at": "2024-01-25",
        "status": "active"
    }
]

conversations = []

@app.get("/", response_class=HTMLResponse)
async def home():
    """主页"""
    return """
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
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                min-height: 100vh;
                display: flex;
                align-items: center;
                justify-content: center;
            }
            
            .container {
                background: white;
                border-radius: 20px;
                box-shadow: 0 20px 40px rgba(0,0,0,0.1);
                padding: 3rem;
                text-align: center;
                max-width: 500px;
                width: 90%;
            }
            
            .logo {
                font-size: 3rem;
                margin-bottom: 1rem;
            }
            
            h1 {
                color: #333;
                margin-bottom: 1rem;
                font-size: 2.5rem;
                font-weight: 700;
            }
            
            .subtitle {
                color: #666;
                margin-bottom: 2rem;
                font-size: 1.1rem;
                line-height: 1.6;
            }
            
            .features {
                display: grid;
                grid-template-columns: 1fr 1fr;
                gap: 1rem;
                margin-bottom: 2rem;
            }
            
            .feature {
                background: #f8f9fa;
                padding: 1rem;
                border-radius: 10px;
                border: 2px solid transparent;
                transition: all 0.3s ease;
            }
            
            .feature:hover {
                border-color: #667eea;
                transform: translateY(-2px);
            }
            
            .feature-icon {
                font-size: 2rem;
                margin-bottom: 0.5rem;
            }
            
            .feature-title {
                font-weight: 600;
                color: #333;
                margin-bottom: 0.25rem;
            }
            
            .feature-desc {
                font-size: 0.9rem;
                color: #666;
            }
            
            .btn {
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                border: none;
                padding: 1rem 2rem;
                border-radius: 50px;
                font-size: 1.1rem;
                font-weight: 600;
                cursor: pointer;
                transition: all 0.3s ease;
                text-decoration: none;
                display: inline-block;
                margin: 0.5rem;
            }
            
            .btn:hover {
                transform: translateY(-2px);
                box-shadow: 0 10px 20px rgba(102, 126, 234, 0.3);
            }
            
            .status {
                background: #e8f5e8;
                color: #2d5a2d;
                padding: 0.5rem 1rem;
                border-radius: 20px;
                font-size: 0.9rem;
                margin-top: 1rem;
                display: inline-block;
            }
            
            @media (max-width: 600px) {
                .features {
                    grid-template-columns: 1fr;
                }
                
                h1 {
                    font-size: 2rem;
                }
                
                .container {
                    padding: 2rem;
                }
            }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="logo">🧠</div>
            <h1>AI知识库系统</h1>
            <p class="subtitle">智能化知识管理平台，让信息检索更简单高效</p>
            
            <div class="features">
                <div class="feature">
                    <div class="feature-icon">💬</div>
                    <div class="feature-title">智能对话</div>
                    <div class="feature-desc">自然语言交互</div>
                </div>
                <div class="feature">
                    <div class="feature-icon">📚</div>
                    <div class="feature-title">知识库</div>
                    <div class="feature-desc">海量文档管理</div>
                </div>
                <div class="feature">
                    <div class="feature-icon">🔍</div>
                    <div class="feature-title">智能搜索</div>
                    <div class="feature-desc">精准内容检索</div>
                </div>
                <div class="feature">
                    <div class="feature-icon">⚡</div>
                    <div class="feature-title">快速响应</div>
                    <div class="feature-desc">毫秒级查询</div>
                </div>
            </div>
            
            <a href="/chat" class="btn">开始对话</a>
            <a href="/knowledge-base" class="btn">浏览知识库</a>
            <a href="/status" class="btn">系统状态</a>
            
            <div class="status">✅ 系统运行正常 - Vercel部署</div>
        </div>
    </body>
    </html>
    """

@app.get("/chat", response_class=HTMLResponse)
async def chat_page():
    """聊天页面"""
    return """
    <!DOCTYPE html>
    <html lang="zh-CN">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>AI对话 - AI知识库系统</title>
        <style>
            * {
                margin: 0;
                padding: 0;
                box-sizing: border-box;
            }
            
            body {
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                background: #f5f7fa;
                height: 100vh;
                display: flex;
                flex-direction: column;
            }
            
            .header {
                background: white;
                padding: 1rem 2rem;
                border-bottom: 1px solid #e1e8ed;
                display: flex;
                align-items: center;
                justify-content: space-between;
            }
            
            .logo {
                display: flex;
                align-items: center;
                font-size: 1.5rem;
                font-weight: 700;
                color: #333;
            }
            
            .chat-container {
                flex: 1;
                display: flex;
                flex-direction: column;
                max-width: 800px;
                margin: 0 auto;
                width: 100%;
                padding: 2rem;
            }
            
            .messages {
                flex: 1;
                overflow-y: auto;
                padding: 1rem;
                background: white;
                border-radius: 10px;
                margin-bottom: 1rem;
                box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            }
            
            .message {
                margin-bottom: 1rem;
                display: flex;
                align-items: flex-start;
            }
            
            .message.user {
                justify-content: flex-end;
            }
            
            .message-content {
                max-width: 70%;
                padding: 1rem;
                border-radius: 18px;
                line-height: 1.4;
            }
            
            .message.user .message-content {
                background: #007bff;
                color: white;
            }
            
            .message.assistant .message-content {
                background: #f1f3f4;
                color: #333;
            }
            
            .input-area {
                display: flex;
                gap: 1rem;
                background: white;
                padding: 1rem;
                border-radius: 10px;
                box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            }
            
            .message-input {
                flex: 1;
                border: 1px solid #ddd;
                border-radius: 25px;
                padding: 1rem 1.5rem;
                font-size: 1rem;
                outline: none;
                resize: none;
                min-height: 50px;
                max-height: 150px;
            }
            
            .send-btn {
                background: #007bff;
                color: white;
                border: none;
                border-radius: 50%;
                width: 50px;
                height: 50px;
                cursor: pointer;
                display: flex;
                align-items: center;
                justify-content: center;
                font-size: 1.2rem;
            }
            
            .send-btn:hover {
                background: #0056b3;
            }
            
            .welcome {
                text-align: center;
                color: #666;
                padding: 2rem;
            }
            
            .back-btn {
                background: #6c757d;
                color: white;
                border: none;
                padding: 0.5rem 1rem;
                border-radius: 5px;
                text-decoration: none;
                font-size: 0.9rem;
            }
        </style>
    </head>
    <body>
        <div class="header">
            <div class="logo">🧠 AI知识库对话</div>
            <a href="/" class="back-btn">返回首页</a>
        </div>
        
        <div class="chat-container">
            <div class="messages" id="messages">
                <div class="welcome">
                    <h3>👋 欢迎使用AI知识库对话系统</h3>
                    <p>您可以向我询问任何问题，我会基于知识库为您提供准确的答案</p>
                </div>
            </div>
            
            <div class="input-area">
                <textarea 
                    id="messageInput" 
                    class="message-input" 
                    placeholder="输入您的问题..."
                    rows="1"
                ></textarea>
                <button class="send-btn" onclick="sendMessage()">📤</button>
            </div>
        </div>
        
        <script>
            function addMessage(content, isUser = false) {
                const messagesDiv = document.getElementById('messages');
                const messageDiv = document.createElement('div');
                messageDiv.className = `message ${isUser ? 'user' : 'assistant'}`;
                
                const contentDiv = document.createElement('div');
                contentDiv.className = 'message-content';
                contentDiv.textContent = content;
                
                messageDiv.appendChild(contentDiv);
                messagesDiv.appendChild(messageDiv);
                
                messagesDiv.scrollTop = messagesDiv.scrollHeight;
            }
            
            async function sendMessage() {
                const input = document.getElementById('messageInput');
                const message = input.value.trim();
                
                if (!message) return;
                
                addMessage(message, true);
                input.value = '';
                
                try {
                    const response = await fetch('/api/chat', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                        },
                        body: JSON.stringify({ message: message })
                    });
                    
                    const data = await response.json();
                    addMessage(data.response);
                } catch (error) {
                    addMessage('抱歉，服务暂时不可用，请稍后再试。');
                }
            }
            
            document.getElementById('messageInput').addEventListener('keypress', function(e) {
                if (e.key === 'Enter' && !e.shiftKey) {
                    e.preventDefault();
                    sendMessage();
                }
            });
        </script>
    </body>
    </html>
    """

@app.get("/knowledge-base", response_class=HTMLResponse)
async def knowledge_base_page():
    """知识库页面"""
    return """
    <!DOCTYPE html>
    <html lang="zh-CN">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>知识库 - AI知识库系统</title>
        <style>
            * {
                margin: 0;
                padding: 0;
                box-sizing: border-box;
            }
            
            body {
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                background: #f5f7fa;
                min-height: 100vh;
            }
            
            .header {
                background: white;
                padding: 1rem 2rem;
                border-bottom: 1px solid #e1e8ed;
                display: flex;
                align-items: center;
                justify-content: space-between;
            }
            
            .logo {
                display: flex;
                align-items: center;
                font-size: 1.5rem;
                font-weight: 700;
                color: #333;
            }
            
            .container {
                max-width: 1200px;
                margin: 0 auto;
                padding: 2rem;
            }
            
            .page-title {
                font-size: 2rem;
                color: #333;
                margin-bottom: 2rem;
                text-align: center;
            }
            
            .knowledge-grid {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(350px, 1fr));
                gap: 2rem;
            }
            
            .knowledge-card {
                background: white;
                border-radius: 10px;
                padding: 2rem;
                box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                transition: transform 0.3s ease;
            }
            
            .knowledge-card:hover {
                transform: translateY(-5px);
            }
            
            .card-header {
                display: flex;
                align-items: center;
                margin-bottom: 1rem;
            }
            
            .card-icon {
                font-size: 2rem;
                margin-right: 1rem;
            }
            
            .card-title {
                font-size: 1.3rem;
                font-weight: 600;
                color: #333;
            }
            
            .card-description {
                color: #666;
                margin-bottom: 1.5rem;
                line-height: 1.6;
            }
            
            .card-stats {
                display: flex;
                justify-content: space-between;
                margin-bottom: 1.5rem;
                font-size: 0.9rem;
                color: #888;
            }
            
            .card-actions {
                display: flex;
                gap: 1rem;
            }
            
            .btn {
                padding: 0.5rem 1rem;
                border: none;
                border-radius: 5px;
                cursor: pointer;
                text-decoration: none;
                font-size: 0.9rem;
                transition: all 0.3s ease;
            }
            
            .btn-primary {
                background: #007bff;
                color: white;
            }
            
            .btn-secondary {
                background: #6c757d;
                color: white;
            }
            
            .btn:hover {
                opacity: 0.8;
            }
            
            .back-btn {
                background: #6c757d;
                color: white;
                border: none;
                padding: 0.5rem 1rem;
                border-radius: 5px;
                text-decoration: none;
                font-size: 0.9rem;
            }
        </style>
    </head>
    <body>
        <div class="header">
            <div class="logo">📚 知识库管理</div>
            <a href="/" class="back-btn">返回首页</a>
        </div>
        
        <div class="container">
            <h1 class="page-title">知识库列表</h1>
            
            <div class="knowledge-grid" id="knowledgeGrid">
                <!-- 知识库卡片将通过JavaScript动态加载 -->
            </div>
        </div>
        
        <script>
            async function loadKnowledgeBases() {
                try {
                    const response = await fetch('/api/knowledge-bases');
                    const data = await response.json();
                    
                    const grid = document.getElementById('knowledgeGrid');
                    grid.innerHTML = '';
                    
                    data.knowledge_bases.forEach(kb => {
                        const card = document.createElement('div');
                        card.className = 'knowledge-card';
                        card.innerHTML = `
                            <div class="card-header">
                                <div class="card-icon">📖</div>
                                <div class="card-title">${kb.name}</div>
                            </div>
                            <div class="card-description">${kb.description}</div>
                            <div class="card-stats">
                                <span>📄 ${kb.document_count} 个文档</span>
                                <span>📅 ${kb.created_at}</span>
                            </div>
                            <div class="card-actions">
                                <button class="btn btn-primary" onclick="viewKnowledgeBase(${kb.id})">查看详情</button>
                                <button class="btn btn-secondary" onclick="searchInKB(${kb.id})">搜索文档</button>
                            </div>
                        `;
                        grid.appendChild(card);
                    });
                } catch (error) {
                    console.error('加载知识库失败:', error);
                }
            }
            
            function viewKnowledgeBase(id) {
                alert(`查看知识库 ${id} 的详细信息`);
            }
            
            function searchInKB(id) {
                alert(`在知识库 ${id} 中搜索文档`);
            }
            
            // 页面加载时获取知识库列表
            loadKnowledgeBases();
        </script>
    </body>
    </html>
    """

@app.post("/api/chat")
async def chat_api(request: dict):
    """聊天API"""
    message = request.get("message", "")
    
    # 模拟AI回复
    responses = [
        f"您好！您询问的是：{message}。基于我们的知识库，我为您提供以下信息...",
        f"关于 '{message}' 这个问题，我在知识库中找到了相关内容。",
        f"根据知识库检索，关于 '{message}' 的答案如下：这是一个很好的问题...",
        f"让我为您查询 '{message}' 相关的信息。根据文档显示..."
    ]
    
    import random
    response = random.choice(responses)
    
    # 保存对话记录
    conversation = {
        "id": len(conversations) + 1,
        "user_message": message,
        "ai_response": response,
        "timestamp": datetime.now().isoformat()
    }
    conversations.append(conversation)
    
    return {"response": response}

@app.get("/api/knowledge-bases")
async def get_knowledge_bases():
    """获取知识库列表"""
    return {"knowledge_bases": knowledge_bases}

@app.get("/status", response_class=HTMLResponse)
async def status_page():
    """系统状态页面"""
    return """
    <!DOCTYPE html>
    <html lang="zh-CN">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>系统状态 - AI知识库系统</title>
        <style>
            * {
                margin: 0;
                padding: 0;
                box-sizing: border-box;
            }
            
            body {
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                background: #f5f7fa;
                min-height: 100vh;
            }
            
            .header {
                background: white;
                padding: 1rem 2rem;
                border-bottom: 1px solid #e1e8ed;
                display: flex;
                align-items: center;
                justify-content: space-between;
            }
            
            .logo {
                display: flex;
                align-items: center;
                font-size: 1.5rem;
                font-weight: 700;
                color: #333;
            }
            
            .container {
                max-width: 800px;
                margin: 0 auto;
                padding: 2rem;
            }
            
            .status-card {
                background: white;
                border-radius: 10px;
                padding: 2rem;
                box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                margin-bottom: 2rem;
            }
            
            .status-header {
                display: flex;
                align-items: center;
                margin-bottom: 2rem;
            }
            
            .status-icon {
                font-size: 3rem;
                margin-right: 1rem;
            }
            
            .status-title {
                font-size: 2rem;
                color: #333;
            }
            
            .status-grid {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
                gap: 1.5rem;
            }
            
            .status-item {
                background: #f8f9fa;
                padding: 1.5rem;
                border-radius: 8px;
                border-left: 4px solid #28a745;
            }
            
            .status-item.warning {
                border-left-color: #ffc107;
            }
            
            .status-item.error {
                border-left-color: #dc3545;
            }
            
            .status-label {
                font-weight: 600;
                color: #333;
                margin-bottom: 0.5rem;
            }
            
            .status-value {
                font-size: 1.1rem;
                color: #666;
            }
            
            .back-btn {
                background: #6c757d;
                color: white;
                border: none;
                padding: 0.5rem 1rem;
                border-radius: 5px;
                text-decoration: none;
                font-size: 0.9rem;
            }
        </style>
    </head>
    <body>
        <div class="header">
            <div class="logo">📊 系统状态</div>
            <a href="/" class="back-btn">返回首页</a>
        </div>
        
        <div class="container">
            <div class="status-card">
                <div class="status-header">
                    <div class="status-icon">✅</div>
                    <div class="status-title">系统运行正常</div>
                </div>
                
                <div class="status-grid">
                    <div class="status-item">
                        <div class="status-label">服务状态</div>
                        <div class="status-value">运行中</div>
                    </div>
                    <div class="status-item">
                        <div class="status-label">部署平台</div>
                        <div class="status-value">Vercel</div>
                    </div>
                    <div class="status-item">
                        <div class="status-label">版本</div>
                        <div class="status-value">1.0.0</div>
                    </div>
                    <div class="status-item">
                        <div class="status-label">环境</div>
                        <div class="status-value">生产环境</div>
                    </div>
                    <div class="status-item">
                        <div class="status-label">知识库数量</div>
                        <div class="status-value">3 个</div>
                    </div>
                    <div class="status-item">
                        <div class="status-label">总文档数</div>
                        <div class="status-value">479 个</div>
                    </div>
                </div>
            </div>
        </div>
    </body>
    </html>
    """

@app.get("/health")
async def health_check():
    """健康检查"""
    return {
        "status": "healthy",
        "service": "AI知识库系统 - 用户前端",
        "timestamp": datetime.now().isoformat(),
        "version": "1.0.0",
        "environment": "production",
        "platform": "Vercel"
    }

# Vercel处理函数
handler = app