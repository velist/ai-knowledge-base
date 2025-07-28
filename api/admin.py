# Vercel部署入口文件 - 管理后台
from fastapi import FastAPI, Request, HTTPException, Form, Depends, status
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
import hashlib
import secrets
import jwt
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
import json

# 创建FastAPI应用
app = FastAPI(
    title="AI知识库管理后台",
    description="AI知识库系统管理后台 - Vercel部署版本",
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

# 安全配置
SECRET_KEY = "ai-knowledge-base-vercel-secret-2024"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 480

security = HTTPBearer()

# 管理员账户
ADMIN_USERS = {
    "vee5208": {
        "username": "vee5208",
        "password_hash": hashlib.md5("forxy131".encode()).hexdigest(),
        "role": "admin",
        "created_at": "2024-01-01"
    }
}

# 模拟数据
system_stats = {
    "total_users": 1247,
    "total_documents": 8934,
    "total_knowledge_bases": 23,
    "total_conversations": 15678,
    "system_uptime": "15天 8小时 32分钟",
    "cpu_usage": 23.5,
    "memory_usage": 67.8,
    "disk_usage": 45.2
}

recent_activities = [
    {"time": "2024-01-30 14:30", "action": "用户登录", "user": "user123", "status": "成功"},
    {"time": "2024-01-30 14:25", "action": "文档上传", "user": "user456", "status": "成功"},
    {"time": "2024-01-30 14:20", "action": "知识库查询", "user": "user789", "status": "成功"},
    {"time": "2024-01-30 14:15", "action": "系统备份", "user": "system", "status": "完成"},
    {"time": "2024-01-30 14:10", "action": "用户注册", "user": "newuser", "status": "成功"}
]

users_data = [
    {
        "id": 1,
        "username": "user001",
        "email": "user001@example.com",
        "role": "user",
        "status": "active",
        "created_at": "2024-01-15",
        "last_login": "2024-01-30 10:30"
    },
    {
        "id": 2,
        "username": "user002",
        "email": "user002@example.com",
        "role": "user",
        "status": "active",
        "created_at": "2024-01-20",
        "last_login": "2024-01-29 15:45"
    }
]

system_logs = [
    {
        "id": 1,
        "timestamp": "2024-01-30 14:30:25",
        "level": "INFO",
        "module": "auth",
        "message": "用户登录成功",
        "ip": "192.168.1.100"
    },
    {
        "id": 2,
        "timestamp": "2024-01-30 14:25:10",
        "level": "INFO",
        "module": "upload",
        "message": "文档上传完成",
        "ip": "192.168.1.101"
    }
]

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """创建访问令牌"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """验证令牌"""
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise HTTPException(status_code=401, detail="无效的认证凭据")
        return username
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="无效的认证凭据")

@app.get("/", response_class=HTMLResponse)
async def admin_login_page():
    """管理员登录页面"""
    return """
    <!DOCTYPE html>
    <html lang="zh-CN">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>管理后台登录 - AI知识库系统</title>
        <style>
            * {
                margin: 0;
                padding: 0;
                box-sizing: border-box;
            }
            
            body {
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%);
                min-height: 100vh;
                display: flex;
                align-items: center;
                justify-content: center;
            }
            
            .login-container {
                background: white;
                border-radius: 15px;
                box-shadow: 0 20px 40px rgba(0,0,0,0.1);
                padding: 3rem;
                width: 100%;
                max-width: 400px;
            }
            
            .logo {
                text-align: center;
                font-size: 3rem;
                margin-bottom: 1rem;
            }
            
            .title {
                text-align: center;
                color: #333;
                margin-bottom: 0.5rem;
                font-size: 1.8rem;
                font-weight: 700;
            }
            
            .subtitle {
                text-align: center;
                color: #666;
                margin-bottom: 2rem;
                font-size: 0.9rem;
            }
            
            .form-group {
                margin-bottom: 1.5rem;
            }
            
            .form-group label {
                display: block;
                margin-bottom: 0.5rem;
                color: #333;
                font-weight: 500;
            }
            
            .form-group input {
                width: 100%;
                padding: 1rem;
                border: 2px solid #e1e8ed;
                border-radius: 8px;
                font-size: 1rem;
                transition: border-color 0.3s ease;
            }
            
            .form-group input:focus {
                outline: none;
                border-color: #1e3c72;
            }
            
            .login-btn {
                width: 100%;
                background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%);
                color: white;
                border: none;
                padding: 1rem;
                border-radius: 8px;
                font-size: 1rem;
                font-weight: 600;
                cursor: pointer;
                transition: all 0.3s ease;
            }
            
            .login-btn:hover {
                transform: translateY(-2px);
                box-shadow: 0 10px 20px rgba(30, 60, 114, 0.3);
            }
            
            .error-message {
                background: #fee;
                color: #c33;
                padding: 1rem;
                border-radius: 8px;
                margin-bottom: 1rem;
                text-align: center;
                display: none;
            }
            
            .platform-info {
                text-align: center;
                margin-top: 2rem;
                padding-top: 1rem;
                border-top: 1px solid #eee;
                color: #666;
                font-size: 0.8rem;
            }
        </style>
    </head>
    <body>
        <div class="login-container">
            <div class="logo">🔐</div>
            <h1 class="title">管理后台</h1>
            <p class="subtitle">AI知识库系统 - Vercel部署版</p>
            
            <div id="errorMessage" class="error-message"></div>
            
            <form id="loginForm">
                <div class="form-group">
                    <label for="username">用户名</label>
                    <input type="text" id="username" name="username" required>
                </div>
                
                <div class="form-group">
                    <label for="password">密码</label>
                    <input type="password" id="password" name="password" required>
                </div>
                
                <button type="submit" class="login-btn">登录</button>
            </form>
            
            <div class="platform-info">
                <div>🌐 Vercel云端部署</div>
                <div>默认账户: vee5208 / forxy131</div>
            </div>
        </div>
        
        <script>
            document.getElementById('loginForm').addEventListener('submit', async function(e) {
                e.preventDefault();
                
                const username = document.getElementById('username').value;
                const password = document.getElementById('password').value;
                const errorDiv = document.getElementById('errorMessage');
                
                try {
                    const response = await fetch('/login', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/x-www-form-urlencoded',
                        },
                        body: `username=${encodeURIComponent(username)}&password=${encodeURIComponent(password)}`
                    });
                    
                    const data = await response.json();
                    
                    if (response.ok) {
                        localStorage.setItem('admin_token', data.access_token);
                        window.location.href = '/dashboard';
                    } else {
                        errorDiv.textContent = data.detail || '登录失败';
                        errorDiv.style.display = 'block';
                    }
                } catch (error) {
                    errorDiv.textContent = '网络错误，请稍后重试';
                    errorDiv.style.display = 'block';
                }
            });
        </script>
    </body>
    </html>
    """

@app.post("/login")
async def login(username: str = Form(...), password: str = Form(...)):
    """管理员登录"""
    password_hash = hashlib.md5(password.encode()).hexdigest()
    
    if username in ADMIN_USERS and ADMIN_USERS[username]["password_hash"] == password_hash:
        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"sub": username}, expires_delta=access_token_expires
        )
        return {"access_token": access_token, "token_type": "bearer"}
    else:
        raise HTTPException(status_code=401, detail="用户名或密码错误")

@app.get("/dashboard", response_class=HTMLResponse)
async def admin_dashboard():
    """管理后台仪表板"""
    return """
    <!DOCTYPE html>
    <html lang="zh-CN">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>管理后台 - AI知识库系统</title>
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
            
            .user-info {
                display: flex;
                align-items: center;
                gap: 1rem;
            }
            
            .container {
                max-width: 1200px;
                margin: 0 auto;
                padding: 2rem;
            }
            
            .stats-grid {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
                gap: 1.5rem;
                margin-bottom: 2rem;
            }
            
            .stat-card {
                background: white;
                border-radius: 10px;
                padding: 1.5rem;
                box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            }
            
            .stat-header {
                display: flex;
                align-items: center;
                justify-content: space-between;
                margin-bottom: 1rem;
            }
            
            .stat-title {
                color: #666;
                font-size: 0.9rem;
            }
            
            .stat-icon {
                font-size: 1.5rem;
            }
            
            .stat-value {
                font-size: 2rem;
                font-weight: 700;
                color: #333;
            }
            
            .content-grid {
                display: grid;
                grid-template-columns: 2fr 1fr;
                gap: 2rem;
            }
            
            .panel {
                background: white;
                border-radius: 10px;
                padding: 1.5rem;
                box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            }
            
            .panel-title {
                font-size: 1.2rem;
                font-weight: 600;
                color: #333;
                margin-bottom: 1rem;
                display: flex;
                align-items: center;
                gap: 0.5rem;
            }
            
            .activity-item {
                display: flex;
                justify-content: space-between;
                align-items: center;
                padding: 0.75rem 0;
                border-bottom: 1px solid #f0f0f0;
            }
            
            .activity-item:last-child {
                border-bottom: none;
            }
            
            .activity-info {
                flex: 1;
            }
            
            .activity-action {
                font-weight: 500;
                color: #333;
            }
            
            .activity-user {
                font-size: 0.9rem;
                color: #666;
            }
            
            .activity-time {
                font-size: 0.8rem;
                color: #999;
            }
            
            .status-success {
                color: #28a745;
                font-size: 0.8rem;
            }
            
            .nav-menu {
                display: flex;
                gap: 1rem;
                margin-bottom: 2rem;
            }
            
            .nav-item {
                padding: 0.5rem 1rem;
                background: white;
                border: none;
                border-radius: 5px;
                cursor: pointer;
                text-decoration: none;
                color: #666;
                transition: all 0.3s ease;
            }
            
            .nav-item:hover, .nav-item.active {
                background: #007bff;
                color: white;
            }
            
            .logout-btn {
                background: #dc3545;
                color: white;
                border: none;
                padding: 0.5rem 1rem;
                border-radius: 5px;
                cursor: pointer;
                text-decoration: none;
            }
            
            .platform-badge {
                background: #28a745;
                color: white;
                padding: 0.25rem 0.5rem;
                border-radius: 3px;
                font-size: 0.7rem;
                margin-left: 0.5rem;
            }
        </style>
    </head>
    <body>
        <div class="header">
            <div class="logo">
                🔧 AI知识库管理后台
                <span class="platform-badge">Vercel</span>
            </div>
            <div class="user-info">
                <span>👤 管理员: vee5208</span>
                <button class="logout-btn" onclick="logout()">退出登录</button>
            </div>
        </div>
        
        <div class="container">
            <div class="nav-menu">
                <a href="#" class="nav-item active">📊 仪表板</a>
                <a href="#" class="nav-item" onclick="showUsers()">👥 用户管理</a>
                <a href="#" class="nav-item" onclick="showLogs()">📋 系统日志</a>
                <a href="#" class="nav-item" onclick="showSettings()">⚙️ 系统设置</a>
            </div>
            
            <div class="stats-grid" id="statsGrid">
                <!-- 统计卡片将通过JavaScript动态加载 -->
            </div>
            
            <div class="content-grid">
                <div class="panel">
                    <div class="panel-title">📈 系统监控</div>
                    <div id="systemMonitor">
                        <!-- 系统监控内容 -->
                    </div>
                </div>
                
                <div class="panel">
                    <div class="panel-title">🕒 最近活动</div>
                    <div id="recentActivities">
                        <!-- 最近活动将通过JavaScript动态加载 -->
                    </div>
                </div>
            </div>
        </div>
        
        <script>
            // 检查登录状态
            function checkAuth() {
                const token = localStorage.getItem('admin_token');
                if (!token) {
                    window.location.href = '/';
                    return false;
                }
                return true;
            }
            
            // 退出登录
            function logout() {
                localStorage.removeItem('admin_token');
                window.location.href = '/';
            }
            
            // 加载统计数据
            async function loadStats() {
                try {
                    const response = await fetch('/api/stats');
                    const data = await response.json();
                    
                    const statsGrid = document.getElementById('statsGrid');
                    statsGrid.innerHTML = `
                        <div class="stat-card">
                            <div class="stat-header">
                                <div class="stat-title">总用户数</div>
                                <div class="stat-icon">👥</div>
                            </div>
                            <div class="stat-value">${data.total_users}</div>
                        </div>
                        <div class="stat-card">
                            <div class="stat-header">
                                <div class="stat-title">总文档数</div>
                                <div class="stat-icon">📄</div>
                            </div>
                            <div class="stat-value">${data.total_documents}</div>
                        </div>
                        <div class="stat-card">
                            <div class="stat-header">
                                <div class="stat-title">知识库数</div>
                                <div class="stat-icon">📚</div>
                            </div>
                            <div class="stat-value">${data.total_knowledge_bases}</div>
                        </div>
                        <div class="stat-card">
                            <div class="stat-header">
                                <div class="stat-title">对话次数</div>
                                <div class="stat-icon">💬</div>
                            </div>
                            <div class="stat-value">${data.total_conversations}</div>
                        </div>
                    `;
                    
                    // 系统监控
                    const systemMonitor = document.getElementById('systemMonitor');
                    systemMonitor.innerHTML = `
                        <div style="margin-bottom: 1rem;">
                            <div style="display: flex; justify-content: space-between; margin-bottom: 0.5rem;">
                                <span>CPU使用率</span>
                                <span>${data.cpu_usage}%</span>
                            </div>
                            <div style="background: #f0f0f0; height: 8px; border-radius: 4px;">
                                <div style="background: #007bff; height: 100%; width: ${data.cpu_usage}%; border-radius: 4px;"></div>
                            </div>
                        </div>
                        <div style="margin-bottom: 1rem;">
                            <div style="display: flex; justify-content: space-between; margin-bottom: 0.5rem;">
                                <span>内存使用率</span>
                                <span>${data.memory_usage}%</span>
                            </div>
                            <div style="background: #f0f0f0; height: 8px; border-radius: 4px;">
                                <div style="background: #28a745; height: 100%; width: ${data.memory_usage}%; border-radius: 4px;"></div>
                            </div>
                        </div>
                        <div>
                            <div style="display: flex; justify-content: space-between; margin-bottom: 0.5rem;">
                                <span>磁盘使用率</span>
                                <span>${data.disk_usage}%</span>
                            </div>
                            <div style="background: #f0f0f0; height: 8px; border-radius: 4px;">
                                <div style="background: #ffc107; height: 100%; width: ${data.disk_usage}%; border-radius: 4px;"></div>
                            </div>
                        </div>
                        <div style="margin-top: 1rem; padding-top: 1rem; border-top: 1px solid #f0f0f0;">
                            <div style="color: #666; font-size: 0.9rem;">系统运行时间: ${data.system_uptime}</div>
                        </div>
                    `;
                } catch (error) {
                    console.error('加载统计数据失败:', error);
                }
            }
            
            // 加载最近活动
            async function loadActivities() {
                try {
                    const response = await fetch('/api/recent-activities');
                    const data = await response.json();
                    
                    const activitiesDiv = document.getElementById('recentActivities');
                    activitiesDiv.innerHTML = data.activities.map(activity => `
                        <div class="activity-item">
                            <div class="activity-info">
                                <div class="activity-action">${activity.action}</div>
                                <div class="activity-user">用户: ${activity.user}</div>
                            </div>
                            <div>
                                <div class="activity-time">${activity.time}</div>
                                <div class="status-success">${activity.status}</div>
                            </div>
                        </div>
                    `).join('');
                } catch (error) {
                    console.error('加载活动数据失败:', error);
                }
            }
            
            function showUsers() {
                alert('用户管理功能');
            }
            
            function showLogs() {
                alert('系统日志功能');
            }
            
            function showSettings() {
                alert('系统设置功能');
            }
            
            // 页面加载时检查认证并加载数据
            if (checkAuth()) {
                loadStats();
                loadActivities();
            }
        </script>
    </body>
    </html>
    """

@app.get("/api/stats")
async def get_stats(current_user: str = Depends(verify_token)):
    """获取系统统计数据"""
    return system_stats

@app.get("/api/recent-activities")
async def get_recent_activities(current_user: str = Depends(verify_token)):
    """获取最近活动"""
    return {"activities": recent_activities}

@app.get("/api/users")
async def get_users(current_user: str = Depends(verify_token)):
    """获取用户列表"""
    return {"users": users_data}

@app.get("/api/logs")
async def get_logs(current_user: str = Depends(verify_token)):
    """获取系统日志"""
    return {"logs": system_logs}

@app.get("/health")
async def health_check():
    """健康检查"""
    return {
        "status": "healthy",
        "service": "AI知识库系统 - 管理后台",
        "timestamp": datetime.now().isoformat(),
        "version": "1.0.0",
        "environment": "production",
        "platform": "Vercel"
    }

# Vercel处理函数
handler = app