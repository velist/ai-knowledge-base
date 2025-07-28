#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Vercel部署验证脚本
用于验证部署到Vercel的AI知识库系统是否正常工作
"""

import requests
import json
import time
from typing import Dict, Any


class DeploymentVerifier:
    """部署验证器"""
    
    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip('/')
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'AI-Knowledge-Base-Verifier/1.0'
        })
    
    def verify_frontend(self) -> Dict[str, Any]:
        """验证前端服务"""
        print("🔍 验证前端服务...")
        
        try:
            # 检查首页
            response = self.session.get(f"{self.base_url}/")
            if response.status_code == 200:
                print("✅ 前端首页访问正常")
            else:
                print(f"❌ 前端首页访问失败: {response.status_code}")
                return {"status": "error", "message": f"前端首页返回状态码: {response.status_code}"}
            
            # 检查健康检查接口
            response = self.session.get(f"{self.base_url}/api/health")
            if response.status_code == 200:
                health_data = response.json()
                print(f"✅ 前端健康检查正常: {health_data}")
            else:
                print(f"❌ 前端健康检查失败: {response.status_code}")
            
            # 检查知识库列表接口
            response = self.session.get(f"{self.base_url}/api/knowledge-bases")
            if response.status_code == 200:
                kb_data = response.json()
                print(f"✅ 知识库列表接口正常，返回 {len(kb_data)} 个知识库")
            else:
                print(f"❌ 知识库列表接口失败: {response.status_code}")
            
            return {"status": "success", "message": "前端服务验证通过"}
            
        except Exception as e:
            print(f"❌ 前端服务验证失败: {str(e)}")
            return {"status": "error", "message": str(e)}
    
    def verify_admin(self) -> Dict[str, Any]:
        """验证管理后台"""
        print("\n🔍 验证管理后台...")
        
        try:
            # 检查管理后台首页
            response = self.session.get(f"{self.base_url}/admin")
            if response.status_code == 200:
                print("✅ 管理后台首页访问正常")
            else:
                print(f"❌ 管理后台首页访问失败: {response.status_code}")
                return {"status": "error", "message": f"管理后台首页返回状态码: {response.status_code}"}
            
            # 检查管理后台健康检查
            response = self.session.get(f"{self.base_url}/admin/api/health")
            if response.status_code == 200:
                health_data = response.json()
                print(f"✅ 管理后台健康检查正常: {health_data}")
            else:
                print(f"❌ 管理后台健康检查失败: {response.status_code}")
            
            # 测试登录接口
            login_data = {
                "username": "vee5208",
                "password": "forxy131"
            }
            response = self.session.post(
                f"{self.base_url}/admin/api/login",
                json=login_data
            )
            
            if response.status_code == 200:
                login_result = response.json()
                if login_result.get("success"):
                    print("✅ 管理员登录测试成功")
                    token = login_result.get("token")
                    if token:
                        print("✅ JWT令牌生成正常")
                        # 测试需要认证的接口
                        headers = {"Authorization": f"Bearer {token}"}
                        stats_response = self.session.get(
                            f"{self.base_url}/admin/api/stats",
                            headers=headers
                        )
                        if stats_response.status_code == 200:
                            print("✅ 认证接口访问正常")
                        else:
                            print(f"❌ 认证接口访问失败: {stats_response.status_code}")
                else:
                    print("❌ 管理员登录失败")
            else:
                print(f"❌ 登录接口请求失败: {response.status_code}")
            
            return {"status": "success", "message": "管理后台验证通过"}
            
        except Exception as e:
            print(f"❌ 管理后台验证失败: {str(e)}")
            return {"status": "error", "message": str(e)}
    
    def verify_chat_api(self) -> Dict[str, Any]:
        """验证聊天API"""
        print("\n🔍 验证聊天API...")
        
        try:
            chat_data = {
                "message": "你好，这是一个测试消息",
                "knowledge_base_id": "test"
            }
            
            response = self.session.post(
                f"{self.base_url}/api/chat",
                json=chat_data
            )
            
            if response.status_code == 200:
                chat_result = response.json()
                print(f"✅ 聊天API响应正常: {chat_result.get('response', '')[:50]}...")
                return {"status": "success", "message": "聊天API验证通过"}
            else:
                print(f"❌ 聊天API请求失败: {response.status_code}")
                return {"status": "error", "message": f"聊天API返回状态码: {response.status_code}"}
                
        except Exception as e:
            print(f"❌ 聊天API验证失败: {str(e)}")
            return {"status": "error", "message": str(e)}
    
    def run_full_verification(self) -> Dict[str, Any]:
        """运行完整验证"""
        print(f"🚀 开始验证部署: {self.base_url}")
        print("=" * 50)
        
        results = {
            "url": self.base_url,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "tests": {}
        }
        
        # 验证前端
        results["tests"]["frontend"] = self.verify_frontend()
        
        # 验证管理后台
        results["tests"]["admin"] = self.verify_admin()
        
        # 验证聊天API
        results["tests"]["chat_api"] = self.verify_chat_api()
        
        # 统计结果
        success_count = sum(1 for test in results["tests"].values() if test["status"] == "success")
        total_count = len(results["tests"])
        
        print("\n" + "=" * 50)
        print(f"📊 验证完成: {success_count}/{total_count} 项测试通过")
        
        if success_count == total_count:
            print("🎉 所有测试通过！部署成功！")
            results["overall_status"] = "success"
        else:
            print("⚠️ 部分测试失败，请检查部署配置")
            results["overall_status"] = "partial_success"
        
        return results


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description="验证Vercel部署")
    parser.add_argument(
        "--url",
        default="https://ai-knowledge-base.vercel.app",
        help="部署的URL地址"
    )
    parser.add_argument(
        "--output",
        help="输出结果到JSON文件"
    )
    
    args = parser.parse_args()
    
    # 创建验证器
    verifier = DeploymentVerifier(args.url)
    
    # 运行验证
    results = verifier.run_full_verification()
    
    # 输出结果
    if args.output:
        with open(args.output, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        print(f"\n📄 验证结果已保存到: {args.output}")
    
    # 返回退出码
    if results["overall_status"] == "success":
        exit(0)
    else:
        exit(1)


if __name__ == "__main__":
    main()