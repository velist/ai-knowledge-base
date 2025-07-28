#!/usr/bin/env python3
"""面向普通用户的前端界面"""

from fastapi import FastAPI
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import os

# 创建FastAPI应用
app = FastAPI(
    title="AI知识库助手",
    description="智能对话助手 - 与您的知识库进行自然对话",
    version="1.0.0",
    docs_url="/admin/docs",
    redoc_url="/admin/redoc"
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

# 用户前端HTML模板
USER_FRONTEND_TEMPLATE = """
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AI知识库助手</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'PingFang SC', 'Hiragino Sans GB', 'Microsoft YaHei', sans-serif;
            background: #f5f7fa;
            height: 100vh;
            display: flex;
            flex-direction: column;
        }
        
        /* 顶部导航栏 */
        .header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 15px 20px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }
        
        .logo {
            display: flex;
            align-items: center;
            font-size: 1.5em;
            font-weight: bold;
        }
        
        .logo-icon {
            margin-right: 10px;
            font-size: 1.8em;
        }
        
        .user-menu {
            display: flex;
            align-items: center;
            gap: 15px;
        }
        
        .btn {
            padding: 8px 16px;
            border: none;
            border-radius: 20px;
            cursor: pointer;
            font-size: 14px;
            transition: all 0.3s ease;
        }
        
        .btn-primary {
            background: rgba(255,255,255,0.2);
            color: white;
            border: 1px solid rgba(255,255,255,0.3);
        }
        
        .btn-primary:hover {
            background: rgba(255,255,255,0.3);
        }
        
        /* 主要内容区域 */
        .main-container {
            flex: 1;
            display: flex;
            max-width: 1200px;
            margin: 0 auto;
            width: 100%;
            gap: 20px;
            padding: 20px;
        }
        
        /* 侧边栏 */
        .sidebar {
            width: 280px;
            background: white;
            border-radius: 12px;
            box-shadow: 0 4px 20px rgba(0,0,0,0.08);
            padding: 20px;
            height: fit-content;
        }
        
        .sidebar h3 {
            color: #333;
            margin-bottom: 15px;
            font-size: 1.1em;
        }
        
        .knowledge-list {
            list-style: none;
        }
        
        .knowledge-item {
            padding: 12px;
            margin-bottom: 8px;
            background: #f8f9fa;
            border-radius: 8px;
            cursor: pointer;
            transition: all 0.3s ease;
            border-left: 3px solid transparent;
        }
        
        .knowledge-item:hover {
            background: #e3f2fd;
            border-left-color: #2196F3;
        }
        
        .knowledge-item.active {
            background: #e3f2fd;
            border-left-color: #2196F3;
        }
        
        .add-knowledge {
            width: 100%;
            padding: 12px;
            background: #667eea;
            color: white;
            border: none;
            border-radius: 8px;
            cursor: pointer;
            margin-top: 15px;
            font-size: 14px;
        }
        
        .add-knowledge:hover {
            background: #5a6fd8;
        }
        
        /* 聊天区域 */
        .chat-container {
            flex: 1;
            background: white;
            border-radius: 12px;
            box-shadow: 0 4px 20px rgba(0,0,0,0.08);
            display: flex;
            flex-direction: column;
            height: calc(100vh - 120px);
        }
        
        .chat-header {
            padding: 20px;
            border-bottom: 1px solid #eee;
            background: #fafafa;
            border-radius: 12px 12px 0 0;
        }
        
        .chat-title {
            font-size: 1.2em;
            color: #333;
            margin: 0;
        }
        
        .chat-subtitle {
            color: #666;
            font-size: 0.9em;
            margin-top: 5px;
        }
        
        .chat-messages {
            flex: 1;
            padding: 20px;
            overflow-y: auto;
            display: flex;
            flex-direction: column;
            gap: 15px;
        }
        
        .message {
            display: flex;
            gap: 12px;
            max-width: 80%;
        }
        
        .message.user {
            align-self: flex-end;
            flex-direction: row-reverse;
        }
        
        .message-avatar {
            width: 36px;
            height: 36px;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 1.2em;
            flex-shrink: 0;
        }
        
        .message.user .message-avatar {
            background: #667eea;
            color: white;
        }
        
        .message.assistant .message-avatar {
            background: #f0f0f0;
            color: #666;
        }
        
        .message-content {
            background: #f8f9fa;
            padding: 12px 16px;
            border-radius: 18px;
            line-height: 1.5;
        }
        
        .message.user .message-content {
            background: #667eea;
            color: white;
        }
        
        .welcome-message {
            text-align: center;
            color: #666;
            padding: 40px 20px;
        }
        
        .welcome-icon {
            font-size: 3em;
            margin-bottom: 15px;
        }
        
        /* 输入区域 */
        .chat-input {
            padding: 20px;
            border-top: 1px solid #eee;
            background: #fafafa;
            border-radius: 0 0 12px 12px;
        }
        
        .input-container {
            display: flex;
            gap: 10px;
            align-items: flex-end;
        }
        
        .message-input {
            flex: 1;
            border: 1px solid #ddd;
            border-radius: 20px;
            padding: 12px 16px;
            font-size: 14px;
            resize: none;
            max-height: 120px;
            min-height: 44px;
            outline: none;
            transition: border-color 0.3s ease;
        }
        
        .message-input:focus {
            border-color: #667eea;
        }
        
        .send-btn {
            width: 44px;
            height: 44px;
            background: #667eea;
            color: white;
            border: none;
            border-radius: 50%;
            cursor: pointer;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 1.2em;
            transition: background 0.3s ease;
        }
        
        .send-btn:hover {
            background: #5a6fd8;
        }
        
        .send-btn:disabled {
            background: #ccc;
            cursor: not-allowed;
        }
        
        /* 响应式设计 */
        @media (max-width: 768px) {
            .main-container {
                flex-direction: column;
                padding: 10px;
            }
            
            .sidebar {
                width: 100%;
                order: 2;
            }
            
            .chat-container {
                height: 60vh;
                order: 1;
            }
        }
        
        /* 加载动画 */
        .typing-indicator {
            display: flex;
            gap: 4px;
            padding: 12px 16px;
        }
        
        .typing-dot {
            width: 8px;
            height: 8px;
            background: #999;
            border-radius: 50%;
            animation: typing 1.4s infinite;
        }
        
        .typing-dot:nth-child(2) {
            animation-delay: 0.2s;
        }
        
        .typing-dot:nth-child(3) {
            animation-delay: 0.4s;
        }
        
        @keyframes typing {
            0%, 60%, 100% {
                transform: translateY(0);
            }
            30% {
                transform: translateY(-10px);
            }
        }
    </style>
</head>
<body>
    <!-- 顶部导航栏 -->
    <header class="header">
        <div class="logo">
            <span class="logo-icon">🤖</span>
            AI知识库助手
        </div>
        <div class="user-menu">
            <button class="btn btn-primary" onclick="showSettings()">⚙️ 设置</button>
            <button class="btn btn-primary" onclick="showProfile()">👤 个人中心</button>
            <button class="btn btn-primary" onclick="logout()">🚪 退出</button>
        </div>
    </header>

    <!-- 主要内容区域 -->
    <div class="main-container">
        <!-- 侧边栏 -->
        <aside class="sidebar">
            <h3>📚 我的知识库</h3>
            <ul class="knowledge-list" id="knowledgeList">
                <li class="knowledge-item active" onclick="selectKnowledge(this, 'general')">
                    <div>💡 通用知识库</div>
                    <small style="color: #666;">包含常见问题和基础知识</small>
                </li>
                <li class="knowledge-item" onclick="selectKnowledge(this, 'tech')">
                    <div>💻 技术文档</div>
                    <small style="color: #666;">编程和技术相关资料</small>
                </li>
                <li class="knowledge-item" onclick="selectKnowledge(this, 'business')">
                    <div>📊 业务资料</div>
                    <small style="color: #666;">公司业务和流程文档</small>
                </li>
            </ul>
            <button class="add-knowledge" onclick="addKnowledge()">➕ 添加知识库</button>
            
            <div style="margin-top: 30px;">
                <h3>📁 文档管理</h3>
                <button class="btn" style="width: 100%; margin-bottom: 10px; background: #f8f9fa; color: #333; border: 1px solid #ddd;" onclick="uploadDocument()">📤 上传文档</button>
                <button class="btn" style="width: 100%; background: #f8f9fa; color: #333; border: 1px solid #ddd;" onclick="manageDocuments()">📋 管理文档</button>
            </div>
        </aside>

        <!-- 聊天区域 -->
        <main class="chat-container">
            <div class="chat-header">
                <h2 class="chat-title">与AI助手对话</h2>
                <p class="chat-subtitle">基于您的知识库进行智能问答</p>
            </div>
            
            <div class="chat-messages" id="chatMessages">
                <div class="welcome-message">
                    <div class="welcome-icon">💬</div>
                    <h3>欢迎使用AI知识库助手！</h3>
                    <p>您可以向我提问任何关于您知识库的问题，我会基于您的文档内容为您提供准确的答案。</p>
                    <br>
                    <p><strong>试试问我：</strong></p>
                    <p>• "帮我总结一下技术文档的要点"</p>
                    <p>• "公司的业务流程是怎样的？"</p>
                    <p>• "有什么常见问题需要注意？"</p>
                </div>
            </div>
            
            <div class="chat-input">
                <div class="input-container">
                    <textarea 
                        class="message-input" 
                        id="messageInput" 
                        placeholder="输入您的问题..." 
                        rows="1"
                        onkeydown="handleKeyDown(event)"
                        oninput="autoResize(this)"
                    ></textarea>
                    <button class="send-btn" id="sendBtn" onclick="sendMessage()">
                        ➤
                    </button>
                </div>
            </div>
        </main>
    </div>

    <script>
        let currentKnowledge = 'general';
        let isTyping = false;

        // 自动调整输入框高度
        function autoResize(textarea) {
            textarea.style.height = 'auto';
            textarea.style.height = Math.min(textarea.scrollHeight, 120) + 'px';
        }

        // 处理键盘事件
        function handleKeyDown(event) {
            if (event.key === 'Enter' && !event.shiftKey) {
                event.preventDefault();
                sendMessage();
            }
        }

        // 发送消息
        function sendMessage() {
            const input = document.getElementById('messageInput');
            const message = input.value.trim();
            
            if (!message || isTyping) return;
            
            // 添加用户消息
            addMessage('user', message);
            input.value = '';
            input.style.height = 'auto';
            
            // 显示AI正在输入
            showTyping();
            
            // 模拟AI回复
            setTimeout(() => {
                hideTyping();
                const responses = [
                    '根据您的知识库内容，我找到了相关信息...',
                    '这是一个很好的问题！基于您的文档，我可以告诉您...',
                    '让我为您查找相关资料... 找到了以下信息：',
                    '根据您上传的文档分析，这个问题的答案是...',
                ];
                const response = responses[Math.floor(Math.random() * responses.length)];
                addMessage('assistant', response + '\n\n（这是演示回复，实际使用时会基于您的知识库内容生成准确答案）');
            }, 1500);
        }

        // 添加消息
        function addMessage(sender, content) {
            const messagesContainer = document.getElementById('chatMessages');
            const welcomeMessage = messagesContainer.querySelector('.welcome-message');
            
            if (welcomeMessage) {
                welcomeMessage.remove();
            }
            
            const messageDiv = document.createElement('div');
            messageDiv.className = `message ${sender}`;
            
            const avatar = sender === 'user' ? '👤' : '🤖';
            
            messageDiv.innerHTML = `
                <div class="message-avatar">${avatar}</div>
                <div class="message-content">${content.replace(/\n/g, '<br>')}</div>
            `;
            
            messagesContainer.appendChild(messageDiv);
            messagesContainer.scrollTop = messagesContainer.scrollHeight;
        }

        // 显示AI正在输入
        function showTyping() {
            isTyping = true;
            const messagesContainer = document.getElementById('chatMessages');
            const typingDiv = document.createElement('div');
            typingDiv.className = 'message assistant';
            typingDiv.id = 'typingIndicator';
            
            typingDiv.innerHTML = `
                <div class="message-avatar">🤖</div>
                <div class="message-content typing-indicator">
                    <div class="typing-dot"></div>
                    <div class="typing-dot"></div>
                    <div class="typing-dot"></div>
                </div>
            `;
            
            messagesContainer.appendChild(typingDiv);
            messagesContainer.scrollTop = messagesContainer.scrollHeight;
            
            document.getElementById('sendBtn').disabled = true;
        }

        // 隐藏AI正在输入
        function hideTyping() {
            isTyping = false;
            const typingIndicator = document.getElementById('typingIndicator');
            if (typingIndicator) {
                typingIndicator.remove();
            }
            document.getElementById('sendBtn').disabled = false;
        }

        // 选择知识库
        function selectKnowledge(element, knowledgeId) {
            document.querySelectorAll('.knowledge-item').forEach(item => {
                item.classList.remove('active');
            });
            element.classList.add('active');
            currentKnowledge = knowledgeId;
            
            // 更新聊天标题
            const titles = {
                'general': '通用知识库',
                'tech': '技术文档',
                'business': '业务资料'
            };
            document.querySelector('.chat-title').textContent = `与AI助手对话 - ${titles[knowledgeId]}`;
        }

        // 功能按钮（演示用）
        function addKnowledge() {
            alert('添加知识库功能（开发中）');
        }

        function uploadDocument() {
            alert('上传文档功能（开发中）');
        }

        function manageDocuments() {
            alert('文档管理功能（开发中）');
        }

        function showSettings() {
            alert('设置功能（开发中）');
        }

        function showProfile() {
            alert('个人中心功能（开发中）');
        }

        function logout() {
            if (confirm('确定要退出吗？')) {
                alert('退出功能（开发中）');
            }
        }
    </script>
</body>
</html>
"""

# 管理后台HTML模板
ADMIN_TEMPLATE = """
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AI知识库系统 - 管理后台</title>
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
        .user-link {
            background: #28a745;
            margin-top: 20px;
            display: inline-block;
        }
        .user-link:hover {
            background: #218838;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="logo">⚙️</div>
        <h1>管理后台</h1>
        <p class="subtitle">AI知识库系统管理控制台</p>
        
        <div class="status">✅ 系统运行正常</div>
        
        <div class="links">
            <a href="/admin/docs" class="link">📖 API文档</a>
            <a href="/admin/redoc" class="link">📋 ReDoc文档</a>
            <a href="/health" class="link">🏥 健康检查</a>
        </div>
        
        <a href="/" class="link user-link">👥 用户前端界面</a>
    </div>
</body>
</html>
"""

@app.get("/", response_class=HTMLResponse)
async def user_frontend():
    """用户前端界面"""
    return USER_FRONTEND_TEMPLATE

@app.get("/admin", response_class=HTMLResponse)
async def admin_backend():
    """管理后台界面"""
    return ADMIN_TEMPLATE

@app.get("/api/chat")
async def chat_api():
    """聊天API（演示）"""
    return {
        "message": "聊天API接口",
        "status": "available",
        "note": "实际使用时会连接到AI服务"
    }

@app.get("/api/knowledge")
async def knowledge_api():
    """知识库API（演示）"""
    return {
        "knowledge_bases": [
            {"id": "general", "name": "通用知识库", "documents": 15},
            {"id": "tech", "name": "技术文档", "documents": 8},
            {"id": "business", "name": "业务资料", "documents": 12}
        ]
    }

@app.get("/health")
async def health_check():
    """健康检查"""
    return {
        "status": "healthy",
        "service": "ai-knowledge-base",
        "version": "1.0.0",
        "frontend": "user-oriented",
        "backend": "admin-panel"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)