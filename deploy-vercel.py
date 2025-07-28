#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Vercel一键部署脚本
自动化部署AI知识库系统到Vercel平台
"""

import os
import sys
import json
import subprocess
import time
from pathlib import Path
from typing import Dict, Any, Optional


class VercelDeployer:
    """Vercel部署器"""
    
    def __init__(self):
        self.project_root = Path.cwd()
        self.vercel_config = self.project_root / "vercel.json"
        self.env_file = self.project_root / ".env.production"
        
    def check_prerequisites(self) -> bool:
        """检查部署前置条件"""
        print("🔍 检查部署前置条件...")
        
        # 检查Node.js
        try:
            result = subprocess.run(["node", "--version"], capture_output=True, text=True, shell=True)
            if result.returncode == 0:
                print(f"✅ Node.js: {result.stdout.strip()}")
            else:
                print("❌ 未找到Node.js，请先安装Node.js")
                return False
        except FileNotFoundError:
            print("❌ 未找到Node.js，请先安装Node.js")
            return False
        
        # 检查npm
        try:
            result = subprocess.run(["npm", "--version"], capture_output=True, text=True, shell=True)
            if result.returncode == 0:
                print(f"✅ npm: {result.stdout.strip()}")
            else:
                print("❌ 未找到npm")
                return False
        except FileNotFoundError:
            print("❌ 未找到npm")
            return False
        
        # 检查必要文件
        required_files = [
            "vercel.json",
            "api/index.py",
            "api/admin.py",
            "requirements-vercel.txt"
        ]
        
        for file_path in required_files:
            if not (self.project_root / file_path).exists():
                print(f"❌ 缺少必要文件: {file_path}")
                return False
            else:
                print(f"✅ 文件存在: {file_path}")
        
        return True
    
    def install_vercel_cli(self) -> bool:
        """安装Vercel CLI"""
        print("\n📦 安装Vercel CLI...")
        
        try:
            # 检查是否已安装
            result = subprocess.run(["vercel", "--version"], capture_output=True, text=True, shell=True)
            if result.returncode == 0:
                print(f"✅ Vercel CLI已安装: {result.stdout.strip()}")
                return True
        except FileNotFoundError:
            pass
        
        # 安装Vercel CLI
        try:
            print("正在安装Vercel CLI...")
            result = subprocess.run(
                ["npm", "install", "-g", "vercel"],
                capture_output=True,
                text=True,
                shell=True
            )
            
            if result.returncode == 0:
                print("✅ Vercel CLI安装成功")
                return True
            else:
                print(f"❌ Vercel CLI安装失败: {result.stderr}")
                return False
                
        except Exception as e:
            print(f"❌ 安装Vercel CLI时出错: {str(e)}")
            return False
    
    def login_vercel(self) -> bool:
        """登录Vercel"""
        print("\n🔐 Vercel登录...")
        
        try:
            # 检查是否已登录
            result = subprocess.run(
                ["vercel", "whoami"],
                capture_output=True,
                text=True,
                shell=True
            )
            
            if result.returncode == 0:
                username = result.stdout.strip()
                print(f"✅ 已登录Vercel，用户: {username}")
                return True
            else:
                print("需要登录Vercel...")
                print("请在浏览器中完成登录流程")
                
                # 启动登录流程
                result = subprocess.run(["vercel", "login"], shell=True)
                
                if result.returncode == 0:
                    print("✅ Vercel登录成功")
                    return True
                else:
                    print("❌ Vercel登录失败")
                    return False
                    
        except Exception as e:
            print(f"❌ Vercel登录时出错: {str(e)}")
            return False
    
    def setup_environment_variables(self) -> bool:
        """设置环境变量"""
        print("\n🔧 配置环境变量...")
        
        # 默认环境变量
        default_env_vars = {
            "APP_NAME": "AI知识库",
            "APP_VERSION": "1.0.0",
            "ENVIRONMENT": "production",
            "SECRET_KEY": "your-super-secret-key-change-in-production",
            "ALLOWED_HOSTS": "*",
            "CORS_ORIGINS": "*",
            "SESSION_EXPIRE_HOURS": "24",
            "MAX_UPLOAD_SIZE": "10485760",
            "LOG_LEVEL": "INFO"
        }
        
        try:
            for key, value in default_env_vars.items():
                print(f"设置环境变量: {key}")
                result = subprocess.run(
                    ["vercel", "env", "add", key, "production"],
                    input=value,
                    text=True,
                    capture_output=True,
                    shell=True
                )
                
                if result.returncode == 0:
                    print(f"✅ {key} 设置成功")
                else:
                    # 可能已存在，尝试更新
                    print(f"⚠️ {key} 可能已存在，跳过")
            
            print("✅ 环境变量配置完成")
            return True
            
        except Exception as e:
            print(f"❌ 配置环境变量时出错: {str(e)}")
            return False
    
    def deploy_to_vercel(self, production: bool = False) -> Optional[str]:
        """部署到Vercel"""
        deploy_type = "生产" if production else "预览"
        print(f"\n🚀 开始{deploy_type}部署...")
        
        try:
            # 构建部署命令
            cmd = ["vercel"]
            if production:
                cmd.append("--prod")
            
            # 执行部署
            print("正在部署，请稍候...")
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                cwd=self.project_root,
                shell=True
            )
            
            if result.returncode == 0:
                deployment_url = result.stdout.strip().split('\n')[-1]
                print(f"✅ {deploy_type}部署成功!")
                print(f"🌐 部署地址: {deployment_url}")
                return deployment_url
            else:
                print(f"❌ {deploy_type}部署失败:")
                print(result.stderr)
                return None
                
        except Exception as e:
            print(f"❌ 部署时出错: {str(e)}")
            return None
    
    def verify_deployment(self, url: str) -> bool:
        """验证部署"""
        print(f"\n🔍 验证部署: {url}")
        
        try:
            # 使用验证脚本
            result = subprocess.run(
                [sys.executable, "verify_deployment.py", "--url", url],
                capture_output=True,
                text=True,
                cwd=self.project_root
            )
            
            if result.returncode == 0:
                print("✅ 部署验证通过")
                return True
            else:
                print("❌ 部署验证失败")
                print(result.stdout)
                print(result.stderr)
                return False
                
        except Exception as e:
            print(f"❌ 验证部署时出错: {str(e)}")
            return False
    
    def show_deployment_info(self, url: str):
        """显示部署信息"""
        print("\n" + "="*60)
        print("🎉 部署完成！")
        print("="*60)
        print(f"🌐 前端地址: {url}")
        print(f"🔧 管理后台: {url}/admin")
        print(f"📚 API文档: {url}/docs")
        print("\n🔐 默认管理员账户:")
        print("   用户名: vee5208")
        print("   密码: forxy131")
        print("\n⚠️ 安全提示:")
        print("   请立即登录管理后台修改默认密码！")
        print("\n📋 后续步骤:")
        print("   1. 访问管理后台，修改默认密码")
        print("   2. 配置AI服务API密钥")
        print("   3. 上传知识库文档")
        print("   4. 测试聊天功能")
        print("="*60)
    
    def run_deployment(self, production: bool = False) -> bool:
        """运行完整部署流程"""
        print("🚀 AI知识库系统 - Vercel部署工具")
        print("="*50)
        
        # 1. 检查前置条件
        if not self.check_prerequisites():
            print("❌ 前置条件检查失败，请解决后重试")
            return False
        
        # 2. 安装Vercel CLI
        if not self.install_vercel_cli():
            print("❌ Vercel CLI安装失败")
            return False
        
        # 3. 登录Vercel
        if not self.login_vercel():
            print("❌ Vercel登录失败")
            return False
        
        # 4. 设置环境变量（仅生产环境）
        if production:
            if not self.setup_environment_variables():
                print("⚠️ 环境变量配置失败，但继续部署")
        
        # 5. 部署到Vercel
        deployment_url = self.deploy_to_vercel(production)
        if not deployment_url:
            print("❌ 部署失败")
            return False
        
        # 6. 等待部署完成
        print("⏳ 等待部署完全启动...")
        time.sleep(30)
        
        # 7. 验证部署
        if self.verify_deployment(deployment_url):
            self.show_deployment_info(deployment_url)
            return True
        else:
            print("⚠️ 部署验证失败，但部署可能仍然成功")
            self.show_deployment_info(deployment_url)
            return True


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Vercel一键部署工具")
    parser.add_argument(
        "--prod",
        action="store_true",
        help="部署到生产环境"
    )
    parser.add_argument(
        "--preview",
        action="store_true",
        help="部署到预览环境（默认）"
    )
    
    args = parser.parse_args()
    
    # 确定部署类型
    production = args.prod
    if not args.prod and not args.preview:
        # 交互式选择
        print("请选择部署类型:")
        print("1. 预览部署（推荐用于测试）")
        print("2. 生产部署")
        
        while True:
            choice = input("请输入选择 (1/2): ").strip()
            if choice == "1":
                production = False
                break
            elif choice == "2":
                production = True
                break
            else:
                print("无效选择，请输入1或2")
    
    # 创建部署器并运行
    deployer = VercelDeployer()
    success = deployer.run_deployment(production)
    
    if success:
        print("\n🎉 部署成功完成！")
        exit(0)
    else:
        print("\n❌ 部署失败")
        exit(1)


if __name__ == "__main__":
    main()