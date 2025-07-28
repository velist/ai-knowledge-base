@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

REM AI知识库系统启动脚本 (Windows)

echo.
echo 🧠 AI知识库系统启动脚本
echo ==========================================

REM 检查Python
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Python 未安装或未添加到PATH
    pause
    exit /b 1
)

REM 检查pip
pip --version >nul 2>&1
if errorlevel 1 (
    echo ❌ pip 未安装
    pause
    exit /b 1
)

echo ✅ Python环境检查通过

REM 检查依赖文件
if not exist "requirements.txt" (
    echo ❌ requirements.txt 文件不存在
    pause
    exit /b 1
)

REM 安装依赖
echo 📦 检查并安装依赖...
pip install -r requirements.txt --quiet

REM 创建必要目录
if not exist "logs" mkdir logs
if not exist "uploads" mkdir uploads
if not exist "static" mkdir static

REM 检查端口占用
netstat -an | find ":8000" >nul
if not errorlevel 1 (
    echo ⚠️  端口 8000 可能已被占用
)

netstat -an | find ":8003" >nul
if not errorlevel 1 (
    echo ⚠️  端口 8003 可能已被占用
)

echo.
echo 请选择启动模式:
echo 1) 开发模式 (带热重载)
echo 2) 生产模式 (多进程)
echo 3) 仅启动用户前端
echo 4) 仅启动管理后台
echo 5) 查看帮助
set /p choice=请输入选择 (1-5): 

if "%choice%"=="1" goto dev_mode
if "%choice%"=="2" goto prod_mode
if "%choice%"=="3" goto frontend_only
if "%choice%"=="4" goto backend_only
if "%choice%"=="5" goto show_help

echo ❌ 无效选择
pause
exit /b 1

:dev_mode
echo.
echo 🚀 启动开发模式...
echo 用户前端: http://localhost:8000
echo 管理后台: http://localhost:8003
echo 管理员账户: vee5208 / forxy131
echo 按 Ctrl+C 停止服务
echo.

REM 启动用户前端（后台）
start "用户前端" cmd /c "uvicorn main_user_frontend:app --host 0.0.0.0 --port 8000 --reload"

REM 等待2秒
timeout /t 2 /nobreak >nul

REM 启动管理后台
start "管理后台" cmd /c "uvicorn admin_backend:app --host 0.0.0.0 --port 8003 --reload"

echo 服务已启动，请查看新打开的命令行窗口
echo 关闭窗口即可停止对应服务
pause
goto end

:prod_mode
echo.
echo 🚀 启动生产模式...
python deploy.py
goto end

:frontend_only
echo.
echo 🚀 启动用户前端...
echo 用户前端: http://localhost:8000
uvicorn main_user_frontend:app --host 0.0.0.0 --port 8000 --reload
goto end

:backend_only
echo.
echo 🚀 启动管理后台...
echo 管理后台: http://localhost:8003
echo 管理员账户: vee5208 / forxy131
uvicorn admin_backend:app --host 0.0.0.0 --port 8003 --reload
goto end

:show_help
echo.
echo 📖 AI知识库系统帮助
echo ==========================================
echo.
echo 🌐 访问地址:
echo   用户前端: http://localhost:8000
echo   管理后台: http://localhost:8003
echo.
echo 👤 默认管理员账户:
echo   用户名: vee5208
echo   密码: forxy131
echo.
echo 📁 重要目录:
echo   logs/     - 日志文件
echo   uploads/  - 上传文件
echo   static/   - 静态资源
echo.
echo 🔧 配置文件:
echo   .env.production - 生产环境配置
echo   docker-compose.yml - Docker配置
echo   nginx.conf - Nginx配置
echo.
echo 📚 更多信息请查看 DEPLOYMENT.md
echo.
pause
goto end

:end
echo.
echo 感谢使用 AI知识库系统！
pause