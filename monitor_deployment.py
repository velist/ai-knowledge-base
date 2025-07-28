#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Vercel部署监控脚本
用于监控部署在Vercel上的AI知识库系统的健康状态
"""

import requests
import time
import json
import smtplib
from datetime import datetime
from email.mime.text import MimeText
from email.mime.multipart import MimeMultipart
from typing import Dict, List, Optional
import logging

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('deployment_monitor.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class DeploymentMonitor:
    """部署监控器"""
    
    def __init__(self, config_file: str = "monitor_config.json"):
        self.config = self.load_config(config_file)
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'AI-Knowledge-Base-Monitor/1.0'
        })
        
    def load_config(self, config_file: str) -> Dict:
        """加载配置文件"""
        default_config = {
            "deployment_url": "https://ai-knowledge-base.vercel.app",
            "check_interval": 300,  # 5分钟
            "timeout": 30,
            "max_retries": 3,
            "alert_email": {
                "enabled": False,
                "smtp_server": "smtp.gmail.com",
                "smtp_port": 587,
                "username": "",
                "password": "",
                "to_emails": []
            },
            "checks": {
                "frontend": True,
                "admin": True,
                "api": True,
                "health": True
            },
            "thresholds": {
                "response_time": 5.0,  # 秒
                "success_rate": 0.95   # 95%
            }
        }
        
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
                # 合并默认配置
                for key, value in default_config.items():
                    if key not in config:
                        config[key] = value
                return config
        except FileNotFoundError:
            logger.info(f"配置文件 {config_file} 不存在，使用默认配置")
            # 创建默认配置文件
            with open(config_file, 'w', encoding='utf-8') as f:
                json.dump(default_config, f, indent=2, ensure_ascii=False)
            return default_config
    
    def check_endpoint(self, url: str, name: str) -> Dict:
        """检查单个端点"""
        start_time = time.time()
        
        try:
            response = self.session.get(
                url,
                timeout=self.config['timeout']
            )
            response_time = time.time() - start_time
            
            return {
                "name": name,
                "url": url,
                "status_code": response.status_code,
                "response_time": response_time,
                "success": response.status_code == 200,
                "error": None,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            response_time = time.time() - start_time
            return {
                "name": name,
                "url": url,
                "status_code": None,
                "response_time": response_time,
                "success": False,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    def run_health_checks(self) -> Dict:
        """运行健康检查"""
        base_url = self.config['deployment_url']
        checks = []
        
        # 前端检查
        if self.config['checks']['frontend']:
            checks.append(self.check_endpoint(base_url, "前端首页"))
        
        # 管理后台检查
        if self.config['checks']['admin']:
            checks.append(self.check_endpoint(f"{base_url}/admin", "管理后台"))
        
        # API检查
        if self.config['checks']['api']:
            checks.append(self.check_endpoint(f"{base_url}/api/knowledge-bases", "API接口"))
        
        # 健康检查端点
        if self.config['checks']['health']:
            checks.append(self.check_endpoint(f"{base_url}/api/health", "健康检查"))
            checks.append(self.check_endpoint(f"{base_url}/admin/api/health", "管理后台健康检查"))
        
        # 统计结果
        total_checks = len(checks)
        successful_checks = sum(1 for check in checks if check['success'])
        success_rate = successful_checks / total_checks if total_checks > 0 else 0
        avg_response_time = sum(check['response_time'] for check in checks) / total_checks if total_checks > 0 else 0
        
        return {
            "timestamp": datetime.now().isoformat(),
            "total_checks": total_checks,
            "successful_checks": successful_checks,
            "success_rate": success_rate,
            "avg_response_time": avg_response_time,
            "checks": checks,
            "status": "healthy" if success_rate >= self.config['thresholds']['success_rate'] else "unhealthy"
        }
    
    def send_alert_email(self, subject: str, body: str):
        """发送告警邮件"""
        if not self.config['alert_email']['enabled']:
            return
        
        try:
            msg = MimeMultipart()
            msg['From'] = self.config['alert_email']['username']
            msg['Subject'] = subject
            
            msg.attach(MimeText(body, 'plain', 'utf-8'))
            
            server = smtplib.SMTP(self.config['alert_email']['smtp_server'], self.config['alert_email']['smtp_port'])
            server.starttls()
            server.login(self.config['alert_email']['username'], self.config['alert_email']['password'])
            
            for to_email in self.config['alert_email']['to_emails']:
                msg['To'] = to_email
                server.send_message(msg)
                del msg['To']
            
            server.quit()
            logger.info("告警邮件发送成功")
            
        except Exception as e:
            logger.error(f"发送告警邮件失败: {str(e)}")
    
    def check_and_alert(self, result: Dict):
        """检查结果并发送告警"""
        if result['status'] == 'unhealthy':
            subject = f"🚨 AI知识库系统健康检查告警 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            
            body = f"""
部署监控告警

时间: {result['timestamp']}
部署地址: {self.config['deployment_url']}
总检查项: {result['total_checks']}
成功检查项: {result['successful_checks']}
成功率: {result['success_rate']:.2%}
平均响应时间: {result['avg_response_time']:.2f}秒

失败的检查项:
"""
            
            for check in result['checks']:
                if not check['success']:
                    body += f"- {check['name']} ({check['url']}): {check.get('error', '状态码: ' + str(check['status_code']))}\n"
            
            body += "\n请及时检查部署状态并修复问题。"
            
            self.send_alert_email(subject, body)
            logger.warning(f"系统状态异常，成功率: {result['success_rate']:.2%}")
        else:
            logger.info(f"系统状态正常，成功率: {result['success_rate']:.2%}")
    
    def save_result(self, result: Dict):
        """保存检查结果"""
        log_file = f"health_check_{datetime.now().strftime('%Y%m%d')}.json"
        
        try:
            # 读取现有数据
            try:
                with open(log_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
            except FileNotFoundError:
                data = []
            
            # 添加新结果
            data.append(result)
            
            # 保持最近100条记录
            if len(data) > 100:
                data = data[-100:]
            
            # 保存数据
            with open(log_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
                
        except Exception as e:
            logger.error(f"保存检查结果失败: {str(e)}")
    
    def run_single_check(self):
        """运行单次检查"""
        logger.info("开始健康检查...")
        result = self.run_health_checks()
        
        # 显示结果
        print(f"\n📊 健康检查结果 - {result['timestamp']}")
        print(f"🌐 部署地址: {self.config['deployment_url']}")
        print(f"✅ 成功率: {result['success_rate']:.2%} ({result['successful_checks']}/{result['total_checks']})")
        print(f"⏱️ 平均响应时间: {result['avg_response_time']:.2f}秒")
        print(f"🏥 系统状态: {result['status']}")
        
        print("\n📋 详细检查结果:")
        for check in result['checks']:
            status = "✅" if check['success'] else "❌"
            print(f"  {status} {check['name']}: {check['response_time']:.2f}s")
            if not check['success']:
                print(f"     错误: {check.get('error', '状态码: ' + str(check['status_code']))}")
        
        # 保存结果
        self.save_result(result)
        
        # 检查告警
        self.check_and_alert(result)
        
        return result
    
    def run_continuous_monitoring(self):
        """运行持续监控"""
        logger.info(f"开始持续监控，检查间隔: {self.config['check_interval']}秒")
        
        try:
            while True:
                self.run_single_check()
                time.sleep(self.config['check_interval'])
                
        except KeyboardInterrupt:
            logger.info("监控已停止")
        except Exception as e:
            logger.error(f"监控过程中出错: {str(e)}")


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Vercel部署监控工具")
    parser.add_argument(
        "--config",
        default="monitor_config.json",
        help="配置文件路径"
    )
    parser.add_argument(
        "--once",
        action="store_true",
        help="只运行一次检查"
    )
    parser.add_argument(
        "--url",
        help="指定要监控的URL"
    )
    
    args = parser.parse_args()
    
    # 创建监控器
    monitor = DeploymentMonitor(args.config)
    
    # 如果指定了URL，覆盖配置
    if args.url:
        monitor.config['deployment_url'] = args.url
    
    print(f"🔍 AI知识库系统部署监控")
    print(f"📍 监控地址: {monitor.config['deployment_url']}")
    print("=" * 50)
    
    if args.once:
        # 单次检查
        result = monitor.run_single_check()
        exit(0 if result['status'] == 'healthy' else 1)
    else:
        # 持续监控
        monitor.run_continuous_monitoring()


if __name__ == "__main__":
    main()