from fastapi import FastAPI, HTTPException, Depends, Request, Form, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import hashlib
import datetime
from typing import Optional, Dict, Any
import json
import os
import uuid

app = FastAPI(title="AI知识库后台管理系统", description="专业的后台管理界面")

# CORS配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Session配置
SECRET_KEY = "ai-knowledge-base-secret-key-2024"
SESSION_EXPIRE_MINUTES = 480

# 存储活跃会话
active_sessions = {}

# 初始管理员账户
ADMIN_USERS = {
    "vee5208": {
        "password": hashlib.md5("forxy131".encode()).hexdigest(),
        "role": "admin",
        "name": "系统管理员"
    }
}

# 模拟数据 - 仅包含合规的用户和系统数据
SYSTEM_STATS = {
    "total_users": 1248,
    "paid_users": 456,
    "total_queries": 15432,
    "active_sessions": 89,
    "monthly_revenue": "¥12,580",
    "cpu_usage": 45,
    "memory_usage": 67,
    "uptime": "15天 8小时 32分钟"
}

RECENT_ACTIVITIES = [
    {"time": "2024-01-15 14:30", "user": "用户***3", "action": "订阅付费服务", "detail": "专业版套餐"},
    {"time": "2024-01-15 14:25", "user": "用户***4", "action": "查询知识库", "detail": "AI技术相关"},
    {"time": "2024-01-15 14:20", "user": "用户***5", "action": "账户充值", "detail": "充值¥100"},
    {"time": "2024-01-15 14:15", "user": "用户***6", "action": "修改个人信息", "detail": "更新联系方式"},
    {"time": "2024-01-15 14:10", "user": "管理员", "action": "系统配置", "detail": "更新服务参数"}
]

class LoginRequest(BaseModel):
    username: str
    password: str

def create_session_token(username: str):
    session_id = str(uuid.uuid4())
    expire_time = datetime.datetime.utcnow() + datetime.timedelta(minutes=SESSION_EXPIRE_MINUTES)
    active_sessions[session_id] = {
        "username": username,
        "expire_time": expire_time
    }
    return session_id

def verify_session(request: Request):
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="缺少认证令牌")
    
    session_id = auth_header.replace("Bearer ", "")
    
    if session_id not in active_sessions:
        raise HTTPException(status_code=401, detail="无效的会话")
    
    session = active_sessions[session_id]
    if datetime.datetime.utcnow() > session["expire_time"]:
        del active_sessions[session_id]
        raise HTTPException(status_code=401, detail="会话已过期")
    
    return session["username"]

@app.get("/", response_class=HTMLResponse)
async def admin_login_page():
    return """
    <!DOCTYPE html>
    <html lang="zh-CN">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>AI知识库 - 后台管理登录</title>
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
            
            .login-container {
                background: white;
                padding: 40px;
                border-radius: 20px;
                box-shadow: 0 20px 40px rgba(0,0,0,0.1);
                width: 100%;
                max-width: 400px;
                text-align: center;
            }
            
            .logo {
                font-size: 2.5em;
                color: #667eea;
                margin-bottom: 10px;
                font-weight: bold;
            }
            
            .subtitle {
                color: #666;
                margin-bottom: 30px;
                font-size: 1.1em;
            }
            
            .form-group {
                margin-bottom: 20px;
                text-align: left;
            }
            
            label {
                display: block;
                margin-bottom: 8px;
                color: #333;
                font-weight: 500;
            }
            
            input[type="text"], input[type="password"] {
                width: 100%;
                padding: 12px 16px;
                border: 2px solid #e1e5e9;
                border-radius: 10px;
                font-size: 16px;
                transition: border-color 0.3s;
            }
            
            input[type="text"]:focus, input[type="password"]:focus {
                outline: none;
                border-color: #667eea;
            }
            
            .login-btn {
                width: 100%;
                padding: 14px;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                border: none;
                border-radius: 10px;
                font-size: 16px;
                font-weight: 600;
                cursor: pointer;
                transition: transform 0.2s;
            }
            
            .login-btn:hover {
                transform: translateY(-2px);
            }
            
            .error-message {
                color: #e74c3c;
                margin-top: 10px;
                display: none;
            }
            
            .demo-info {
                margin-top: 20px;
                padding: 15px;
                background: #f8f9fa;
                border-radius: 10px;
                font-size: 14px;
                color: #666;
            }
        </style>
    </head>
    <body>
        <div class="login-container">
            <div class="logo">🧠 AI知识库</div>
            <div class="subtitle">后台管理系统</div>
            
            <form id="loginForm">
                <div class="form-group">
                    <label for="username">用户名</label>
                    <input type="text" id="username" name="username" required>
                </div>
                
                <div class="form-group">
                    <label for="password">密码</label>
                    <input type="password" id="password" name="password" required>
                </div>
                
                <button type="submit" class="login-btn">登录管理后台</button>
                <div class="error-message" id="errorMessage"></div>
            </form>
            
            <div class="demo-info">
                <strong>演示账户:</strong><br>
                用户名: vee5208<br>
                密码: forxy131
            </div>
        </div>
        
        <script>
            document.getElementById('loginForm').addEventListener('submit', async (e) => {
                e.preventDefault();
                
                const username = document.getElementById('username').value;
                const password = document.getElementById('password').value;
                const errorDiv = document.getElementById('errorMessage');
                
                try {
                    const response = await fetch('/login', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                        },
                        body: JSON.stringify({ username, password })
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
                    errorDiv.textContent = '网络错误，请重试';
                    errorDiv.style.display = 'block';
                }
            });
        </script>
    </body>
    </html>
    """

@app.post("/login")
async def login(login_data: LoginRequest):
    username = login_data.username
    password = hashlib.md5(login_data.password.encode()).hexdigest()
    
    if username in ADMIN_USERS and ADMIN_USERS[username]["password"] == password:
        session_token = create_session_token(username)
        return {"access_token": session_token, "token_type": "bearer"}
    
    raise HTTPException(status_code=401, detail="用户名或密码错误")

@app.get("/dashboard", response_class=HTMLResponse)
async def admin_dashboard():
    return """
    <!DOCTYPE html>
    <html lang="zh-CN">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>AI知识库 - 管理仪表盘</title>
        <style>
            * {
                margin: 0;
                padding: 0;
                box-sizing: border-box;
            }
            
            body {
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                background: #f5f7fa;
                color: #333;
            }
            
            .header {
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                padding: 1rem 2rem;
                display: flex;
                justify-content: space-between;
                align-items: center;
                box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            }
            
            .logo {
                font-size: 1.5em;
                font-weight: bold;
            }
            
            .user-info {
                display: flex;
                align-items: center;
                gap: 1rem;
            }
            
            .logout-btn {
                background: rgba(255,255,255,0.2);
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 6px;
                cursor: pointer;
                transition: background 0.3s;
            }
            
            .logout-btn:hover {
                background: rgba(255,255,255,0.3);
            }
            
            .container {
                max-width: 1200px;
                margin: 0 auto;
                padding: 2rem;
            }
            
            .dashboard-grid {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
                gap: 1.5rem;
                margin-bottom: 2rem;
            }
            
            .stat-card {
                background: white;
                padding: 1.5rem;
                border-radius: 12px;
                box-shadow: 0 4px 6px rgba(0,0,0,0.05);
                border-left: 4px solid #667eea;
                transition: transform 0.2s;
            }
            
            .stat-card:hover {
                transform: translateY(-2px);
            }
            
            .stat-card h3 {
                color: #666;
                font-size: 0.9em;
                margin-bottom: 0.5rem;
                text-transform: uppercase;
                letter-spacing: 0.5px;
            }
            
            .stat-value {
                font-size: 2em;
                font-weight: bold;
                color: #333;
                margin-bottom: 0.5rem;
            }
            
            .stat-change {
                font-size: 0.8em;
                color: #27ae60;
            }
            
            .main-content {
                display: grid;
                grid-template-columns: 2fr 1fr;
                gap: 2rem;
            }
            
            .content-card {
                background: white;
                border-radius: 12px;
                box-shadow: 0 4px 6px rgba(0,0,0,0.05);
                overflow: hidden;
            }
            
            .card-header {
                background: #f8f9fa;
                padding: 1rem 1.5rem;
                border-bottom: 1px solid #e9ecef;
                font-weight: 600;
                color: #333;
            }
            
            .card-content {
                padding: 1.5rem;
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
            
            .activity-user {
                font-weight: 600;
                color: #333;
            }
            
            .activity-action {
                color: #666;
                font-size: 0.9em;
            }
            
            .activity-time {
                color: #999;
                font-size: 0.8em;
            }
            
            .nav-menu {
                display: flex;
                gap: 1rem;
                margin-bottom: 2rem;
            }
            
            .nav-item {
                background: white;
                padding: 0.75rem 1.5rem;
                border-radius: 8px;
                text-decoration: none;
                color: #333;
                font-weight: 500;
                box-shadow: 0 2px 4px rgba(0,0,0,0.05);
                transition: all 0.2s;
            }
            
            .nav-item:hover {
                background: #667eea;
                color: white;
                transform: translateY(-1px);
            }
            
            .progress-bar {
                width: 100%;
                height: 8px;
                background: #e9ecef;
                border-radius: 4px;
                overflow: hidden;
                margin-top: 0.5rem;
            }
            
            .progress-fill {
                height: 100%;
                background: linear-gradient(90deg, #667eea, #764ba2);
                transition: width 0.3s;
            }
        </style>
    </head>
    <body>
        <div class="header">
            <div class="logo">🧠 AI知识库管理后台</div>
            <div class="user-info">
                <span>欢迎，系统管理员</span>
                <button class="logout-btn" onclick="logout()">退出登录</button>
            </div>
        </div>
        
        <div class="container">
            <div class="nav-menu">
                <a href="/dashboard" class="nav-item">📊 仪表盘</a>
                <a href="/users" class="nav-item">👥 用户管理</a>
                <a href="/documents" class="nav-item">📚 文档管理</a>
                <a href="/billing" class="nav-item">💰 付费管理</a>
                <a href="/analytics" class="nav-item">📈 数据分析</a>
                <a href="/settings" class="nav-item">⚙️ 系统设置</a>
                <a href="/logs" class="nav-item">📋 系统日志</a>
            </div>
            
            <div class="dashboard-grid">
                <div class="stat-card">
                    <h3>总用户数</h3>
                    <div class="stat-value" id="totalUsers">1,248</div>
                    <div class="stat-change">↗ +12% 本月</div>
                </div>
                
                <div class="stat-card">
                    <h3>付费用户</h3>
                    <div class="stat-value" id="paidUsers">456</div>
                    <div class="stat-change">↗ +18% 本月</div>
                </div>
                
                <div class="stat-card">
                    <h3>月度收入</h3>
                    <div class="stat-value" id="monthlyRevenue">¥12,580</div>
                    <div class="stat-change">↗ +25% 本月</div>
                </div>
                
                <div class="stat-card">
                    <h3>活跃会话</h3>
                    <div class="stat-value" id="activeSessions">89</div>
                    <div class="stat-change">↗ 实时数据</div>
                </div>
            </div>
            
            <div class="main-content">
                <div class="content-card">
                    <div class="card-header">📈 系统性能监控</div>
                    <div class="card-content">
                        <div style="margin-bottom: 1.5rem;">
                            <div style="display: flex; justify-content: space-between; margin-bottom: 0.5rem;">
                                <span>CPU使用率</span>
                                <span>45%</span>
                            </div>
                            <div class="progress-bar">
                                <div class="progress-fill" style="width: 45%;"></div>
                            </div>
                        </div>
                        
                        <div style="margin-bottom: 1.5rem;">
                            <div style="display: flex; justify-content: space-between; margin-bottom: 0.5rem;">
                                <span>内存使用率</span>
                                <span>67%</span>
                            </div>
                            <div class="progress-bar">
                                <div class="progress-fill" style="width: 67%;"></div>
                            </div>
                        </div>
                        
                        <div>
                            <div style="display: flex; justify-content: space-between; margin-bottom: 0.5rem;">
                                <span>网络带宽</span>
                                <span>45 Mbps</span>
                            </div>
                            <div class="progress-bar">
                                <div class="progress-fill" style="width: 45%;"></div>
                            </div>
                        </div>
                        
                        <div style="margin-top: 1.5rem; padding-top: 1.5rem; border-top: 1px solid #e9ecef;">
                            <strong>系统运行时间:</strong> 15天 8小时 32分钟
                        </div>
                    </div>
                </div>
                
                <div class="content-card">
                    <div class="card-header">📋 最近活动</div>
                    <div class="card-content">
                        <div id="recentActivities">
                            <!-- 活动列表将通过JavaScript加载 -->
                        </div>
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
            
            // 加载最近活动
            async function loadRecentActivities() {
                try {
                    const token = localStorage.getItem('admin_token');
                    const response = await fetch('/api/recent-activities', {
                        headers: {
                            'Authorization': `Bearer ${token}`
                        }
                    });
                    
                    if (response.ok) {
                        const activities = await response.json();
                        const container = document.getElementById('recentActivities');
                        
                        container.innerHTML = activities.map(activity => `
                            <div class="activity-item">
                                <div class="activity-info">
                                    <div class="activity-user">${activity.user}</div>
                                    <div class="activity-action">${activity.action}: ${activity.detail}</div>
                                </div>
                                <div class="activity-time">${activity.time}</div>
                            </div>
                        `).join('');
                    }
                } catch (error) {
                    console.error('加载活动失败:', error);
                }
            }
            
            // 页面初始化
            if (checkAuth()) {
                loadRecentActivities();
                
                // 定时刷新数据
                setInterval(() => {
                    loadRecentActivities();
                }, 30000); // 30秒刷新一次
            }
        </script>
    </body>
    </html>
    """

@app.get("/api/recent-activities")
async def get_recent_activities(request: Request, username: str = Depends(verify_session)):
    return RECENT_ACTIVITIES

@app.get("/billing", response_class=HTMLResponse)
async def billing_management():
    return """
    <!DOCTYPE html>
    <html lang="zh-CN">
    <head>
        <meta charset="UTF-8">
        <title>付费管理 - AI知识库后台</title>
        <style>
            body { font-family: 'Segoe UI', sans-serif; background: #f5f7fa; margin: 0; padding: 20px; }
            .container { max-width: 1200px; margin: 0 auto; }
            .header { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 1rem 2rem; border-radius: 10px; margin-bottom: 20px; }
            .content-card { background: white; border-radius: 10px; padding: 20px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); margin-bottom: 20px; }
            .stats-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; margin-bottom: 20px; }
            .stat-item { background: #f8f9fa; padding: 20px; border-radius: 8px; text-align: center; }
            .stat-value { font-size: 2em; font-weight: bold; color: #667eea; }
            .billing-table { width: 100%; border-collapse: collapse; }
            .billing-table th, .billing-table td { padding: 12px; text-align: left; border-bottom: 1px solid #eee; }
            .billing-table th { background: #f8f9fa; font-weight: 600; }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>💰 付费管理</h1>
                <p>管理用户订阅和付费信息</p>
            </div>
            <div class="stats-grid">
                <div class="stat-item">
                    <div class="stat-value">¥12,580</div>
                    <div>本月收入</div>
                </div>
                <div class="stat-item">
                    <div class="stat-value">456</div>
                    <div>付费用户</div>
                </div>
                <div class="stat-item">
                    <div class="stat-value">36.5%</div>
                    <div>付费转化率</div>
                </div>
            </div>
            <div class="content-card">
                <h3>最近订阅记录</h3>
                <table class="billing-table">
                    <thead>
                        <tr>
                            <th>订单ID</th>
                            <th>用户</th>
                            <th>套餐类型</th>
                            <th>金额</th>
                            <th>订阅时间</th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr>
                            <td>ORD***001</td>
                            <td>用户***003</td>
                            <td>专业版</td>
                            <td>¥99/月</td>
                            <td>2024-01-15 14:30</td>
                        </tr>
                        <tr>
                            <td>ORD***002</td>
                            <td>用户***005</td>
                            <td>企业版</td>
                            <td>¥299/月</td>
                            <td>2024-01-15 13:20</td>
                        </tr>
                    </tbody>
                </table>
            </div>
        </div>
    </body>
    </html>
    """

@app.get("/analytics", response_class=HTMLResponse)
async def analytics_page():
    return """
    <!DOCTYPE html>
    <html lang="zh-CN">
    <head>
        <meta charset="UTF-8">
        <title>数据分析 - AI知识库后台</title>
        <style>
            body { font-family: 'Segoe UI', sans-serif; background: #f5f7fa; margin: 0; padding: 20px; }
            .container { max-width: 1200px; margin: 0 auto; }
            .header { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 1rem 2rem; border-radius: 10px; margin-bottom: 20px; }
            .content-card { background: white; border-radius: 10px; padding: 20px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); margin-bottom: 20px; }
            .chart-placeholder { height: 300px; background: #f8f9fa; border-radius: 8px; display: flex; align-items: center; justify-content: center; color: #666; }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>📈 数据分析</h1>
                <p>系统使用情况和趋势分析</p>
            </div>
            <div class="content-card">
                <h3>用户增长趋势</h3>
                <div class="chart-placeholder">📊 用户增长图表</div>
            </div>
            <div class="content-card">
                <h3>收入统计</h3>
                <div class="chart-placeholder">💰 收入趋势图表</div>
            </div>
        </div>
    </body>
    </html>
    """

@app.get("/settings", response_class=HTMLResponse)
async def settings_page():
    return """
    <!DOCTYPE html>
    <html lang="zh-CN">
    <head>
        <meta charset="UTF-8">
        <title>系统设置 - AI知识库后台</title>
        <style>
            body { font-family: 'Segoe UI', sans-serif; background: #f5f7fa; margin: 0; padding: 20px; }
            .container { max-width: 1200px; margin: 0 auto; }
            .header { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 1rem 2rem; border-radius: 10px; margin-bottom: 20px; }
            .content-card { background: white; border-radius: 10px; padding: 20px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); margin-bottom: 20px; }
            .form-group { margin-bottom: 15px; }
            .form-group label { display: block; margin-bottom: 5px; font-weight: 600; }
            .form-group input, .form-group select { width: 100%; padding: 8px; border: 1px solid #ddd; border-radius: 4px; }
            .btn { padding: 10px 20px; background: #667eea; color: white; border: none; border-radius: 4px; cursor: pointer; }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>⚙️ 系统设置</h1>
                <p>配置系统参数和选项</p>
            </div>
            <div class="content-card">
                <h3>基本设置</h3>
                <div class="form-group">
                    <label>系统名称</label>
                    <input type="text" value="AI知识库系统" />
                </div>
                <div class="form-group">
                    <label>最大用户数</label>
                    <input type="number" value="10000" />
                </div>
                <button class="btn">保存设置</button>
            </div>
        </div>
    </body>
    </html>
    """

@app.get("/logs", response_class=HTMLResponse)
async def logs_page():
    return """
    <!DOCTYPE html>
    <html lang="zh-CN">
    <head>
        <meta charset="UTF-8">
        <title>系统日志 - AI知识库后台</title>
        <style>
            body { font-family: 'Segoe UI', sans-serif; background: #f5f7fa; margin: 0; padding: 20px; }
            .container { max-width: 1200px; margin: 0 auto; }
            .header { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 1rem 2rem; border-radius: 10px; margin-bottom: 20px; }
            .content-card { background: white; border-radius: 10px; padding: 20px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
            .log-entry { padding: 10px; border-bottom: 1px solid #eee; font-family: monospace; }
            .log-info { color: #2563eb; }
            .log-warning { color: #d97706; }
            .log-error { color: #dc2626; }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>📋 系统日志</h1>
                <p>查看系统运行日志和错误信息</p>
            </div>
            <div class="content-card">
                <h3>最近日志</h3>
                <div class="log-entry log-info">[2024-01-15 14:30:25] INFO: 用户登录成功 - 用户***003</div>
                <div class="log-entry log-info">[2024-01-15 14:29:15] INFO: 系统备份完成</div>
                <div class="log-entry log-warning">[2024-01-15 14:28:05] WARN: CPU使用率较高 - 67%</div>
                <div class="log-entry log-info">[2024-01-15 14:27:30] INFO: 新用户注册 - 用户***007</div>
            </div>
        </div>
    </body>
    </html>
    """

@app.get("/api/system-stats")
async def get_system_stats(request: Request, username: str = Depends(verify_session)):
    return SYSTEM_STATS

@app.get("/users", response_class=HTMLResponse)
async def users_management():
    return """
    <!DOCTYPE html>
    <html lang="zh-CN">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>用户管理 - AI知识库</title>
        <style>
            * { margin: 0; padding: 0; box-sizing: border-box; }
            body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background: #f5f7fa; }
            .header { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 1rem 2rem; display: flex; justify-content: space-between; align-items: center; }
            .container { max-width: 1200px; margin: 0 auto; padding: 2rem; }
            .page-title { font-size: 2em; margin-bottom: 1rem; color: #333; }
            .content-card { background: white; border-radius: 12px; box-shadow: 0 4px 6px rgba(0,0,0,0.05); overflow: hidden; }
            .card-header { background: #f8f9fa; padding: 1rem 1.5rem; border-bottom: 1px solid #e9ecef; display: flex; justify-content: space-between; align-items: center; }
            .btn { padding: 0.5rem 1rem; border: none; border-radius: 6px; cursor: pointer; font-weight: 500; }
            .btn-primary { background: #667eea; color: white; }
            .table { width: 100%; border-collapse: collapse; }
            .table th, .table td { padding: 1rem; text-align: left; border-bottom: 1px solid #e9ecef; }
            .table th { background: #f8f9fa; font-weight: 600; }
            .status-active { color: #27ae60; font-weight: 600; }
            .status-inactive { color: #e74c3c; font-weight: 600; }
        </style>
    </head>
    <body>
        <div class="header">
            <div>🧠 AI知识库管理后台</div>
            <button onclick="window.location.href='/dashboard'" style="background: rgba(255,255,255,0.2); color: white; border: none; padding: 8px 16px; border-radius: 6px; cursor: pointer;">返回仪表盘</button>
        </div>
        <div class="container">
            <h1 class="page-title">👥 用户管理</h1>
            <div class="content-card">
                <div class="card-header">
                    <span>用户列表</span>
                    <button class="btn btn-primary">+ 添加用户</button>
                </div>
                <table class="table">
                    <thead>
                        <tr><th>用户ID</th><th>用户名</th><th>邮箱</th><th>注册时间</th><th>状态</th><th>操作</th></tr>
                    </thead>
                    <tbody>
                        <tr><td>001</td><td>张三</td><td>zhangsan@example.com</td><td>2024-01-10</td><td><span class="status-active">活跃</span></td><td><button class="btn">编辑</button></td></tr>
                        <tr><td>002</td><td>李四</td><td>lisi@example.com</td><td>2024-01-08</td><td><span class="status-active">活跃</span></td><td><button class="btn">编辑</button></td></tr>
                        <tr><td>003</td><td>王五</td><td>wangwu@example.com</td><td>2024-01-05</td><td><span class="status-inactive">禁用</span></td><td><button class="btn">编辑</button></td></tr>
                    </tbody>
                </table>
            </div>
        </div>
    </body>
    </html>
    """

@app.get("/documents", response_class=HTMLResponse)
async def documents_management():
    return """
    <!DOCTYPE html>
    <html lang="zh-CN">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>文档管理 - AI知识库</title>
        <style>
            * { margin: 0; padding: 0; box-sizing: border-box; }
            body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background: #f5f7fa; }
            .header { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 1rem 2rem; display: flex; justify-content: space-between; align-items: center; }
            .container { max-width: 1200px; margin: 0 auto; padding: 2rem; }
            .page-title { font-size: 2em; margin-bottom: 1rem; color: #333; }
            .content-card { background: white; border-radius: 12px; box-shadow: 0 4px 6px rgba(0,0,0,0.05); overflow: hidden; }
            .card-header { background: #f8f9fa; padding: 1rem 1.5rem; border-bottom: 1px solid #e9ecef; display: flex; justify-content: space-between; align-items: center; }
            .btn { padding: 0.5rem 1rem; border: none; border-radius: 6px; cursor: pointer; font-weight: 500; }
            .btn-primary { background: #667eea; color: white; }
            .table { width: 100%; border-collapse: collapse; }
            .table th, .table td { padding: 1rem; text-align: left; border-bottom: 1px solid #e9ecef; }
            .table th { background: #f8f9fa; font-weight: 600; }
            .file-type { padding: 0.25rem 0.5rem; border-radius: 4px; font-size: 0.8em; font-weight: 600; }
            .file-pdf { background: #fee; color: #c53030; }
            .file-doc { background: #e6f3ff; color: #2b6cb0; }
            .file-txt { background: #f0fff4; color: #38a169; }
        </style>
    </head>
    <body>
        <div class="header">
            <div>🧠 AI知识库管理后台</div>
            <button onclick="window.location.href='/dashboard'" style="background: rgba(255,255,255,0.2); color: white; border: none; padding: 8px 16px; border-radius: 6px; cursor: pointer;">返回仪表盘</button>
        </div>
        <div class="container">
            <h1 class="page-title">📚 文档管理</h1>
            <div class="content-card">
                <div class="card-header">
                    <span>文档列表</span>
                    <button class="btn btn-primary">+ 上传文档</button>
                </div>
                <table class="table">
                    <thead>
                        <tr><th>文档名称</th><th>类型</th><th>大小</th><th>上传时间</th><th>上传者</th><th>操作</th></tr>
                    </thead>
                    <tbody>
                        <tr><td>技术规范.pdf</td><td><span class="file-type file-pdf">PDF</span></td><td>2.3MB</td><td>2024-01-15</td><td>张三</td><td><button class="btn">下载</button> <button class="btn">删除</button></td></tr>
                        <tr><td>项目文档.docx</td><td><span class="file-type file-doc">DOC</span></td><td>1.8MB</td><td>2024-01-14</td><td>李四</td><td><button class="btn">下载</button> <button class="btn">删除</button></td></tr>
                        <tr><td>说明文档.txt</td><td><span class="file-type file-txt">TXT</span></td><td>156KB</td><td>2024-01-13</td><td>王五</td><td><button class="btn">下载</button> <button class="btn">删除</button></td></tr>
                    </tbody>
                </table>
            </div>
        </div>
    </body>
    </html>
    """

@app.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.datetime.now().isoformat()}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8002)