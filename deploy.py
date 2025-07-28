#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI知识库系统 - 生产环境部署启动脚本
"""

import os
import sys
import subprocess
import time
import signal
from multiprocessing import Process

def start_user_frontend():
    """启动用户前端服务"""
    print("🚀 启动用户前端服务 (端口 8000)...")
    os.system("uvicorn main_user_frontend:app --host 0.0.0.0 --port 8000 --workers 4")

def start_admin_backend():
    """启动管理后台服务"""
    print("🔧 启动管理后台服务 (端口 8003)...")
    os.system("uvicorn admin_backend:app --host 0.0.0.0 --port 8003 --workers 2")

def signal_handler(signum, frame):
    """信号处理器"""
    print("\n🛑 收到停止信号，正在关闭服务...")
    sys.exit(0)

def main():
    """主函数"""
    print("="*60)
    print("🧠 AI知识库系统 - 生产环境部署")
    print("="*60)
    
    # 注册信号处理器
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # 检查环境
    print("📋 检查运行环境...")
    
    # 创建必要目录
    os.makedirs("logs", exist_ok=True)
    os.makedirs("uploads", exist_ok=True)
    os.makedirs("static", exist_ok=True)
    
    print("✅ 环境检查完成")
    
    # 启动服务进程
    print("\n🚀 启动服务...")
    
    try:
        # 创建进程
        frontend_process = Process(target=start_user_frontend)
        backend_process = Process(target=start_admin_backend)
        
        # 启动进程
        frontend_process.start()
        time.sleep(2)  # 等待前端服务启动
        backend_process.start()
        
        print("\n✅ 服务启动完成!")
        print("📱 用户前端: http://localhost:8000")
        print("🔧 管理后台: http://localhost:8003")
        print("\n管理员账户:")
        print("  用户名: vee5208")
        print("  密码: forxy131")
        print("\n按 Ctrl+C 停止服务")
        print("="*60)
        
        # 等待进程结束
        frontend_process.join()
        backend_process.join()
        
    except KeyboardInterrupt:
        print("\n🛑 正在停止服务...")
        if 'frontend_process' in locals():
            frontend_process.terminate()
        if 'backend_process' in locals():
            backend_process.terminate()
        print("✅ 服务已停止")
    except Exception as e:
        print(f"❌ 启动失败: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()